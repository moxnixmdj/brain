from __future__ import annotations

import unittest

from canonical.runtime.atomic_frontier_transaction_guard_v2 import (
    _group_field_dependencies,
    classify_snapshot_v2,
)


def field_result(*, stale=False):
    return {
        "source_path":"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
        "stale":stale,
        "changed_dependencies":[] if not stale else [{"pointer":"/x","reason":"VALUE_CHANGED"}],
    }


class AtomicFrontierTransactionGuardV2Tests(unittest.TestCase):
    def base_args(self):
        return dict(
            base_sha="a"*40,
            current_sha="b"*40,
            expected_authority_epoch="1"*64,
            base_authority_epoch="1"*64,
            current_authority_epoch="1"*64,
            intervening_paths=["canonical/research/unrelated.json"],
            mutation_paths=["canonical/runtime/new_candidate.py"],
            dependency_paths=[],
        )

    def test_global_epoch_change_can_be_nonloadbearing_for_zero_credit(self):
        args=self.base_args()
        args["current_authority_epoch"]="2"*64
        out=classify_snapshot_v2(
            **args,
            field_dependency_results=[field_result(stale=False)],
            allow_field_scoped_epoch_rebase=True,
        )
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["field_scoped_epoch_override_used"])
        self.assertTrue(out["zero_credit_preparation_only"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertTrue(out["outer_epoch_recheck_required_before_authority_boundary"])

    def test_epoch_change_without_field_manifest_fails_closed(self):
        args=self.base_args()
        args["current_authority_epoch"]="2"*64
        out=classify_snapshot_v2(
            **args,
            field_dependency_results=[],
            allow_field_scoped_epoch_rebase=True,
        )
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_EPOCH_CHANGED",out["errors"])

    def test_changed_field_dependency_fails_closed(self):
        args=self.base_args()
        args["current_authority_epoch"]="2"*64
        out=classify_snapshot_v2(
            **args,
            field_dependency_results=[field_result(stale=True)],
            allow_field_scoped_epoch_rebase=True,
        )
        self.assertFalse(out["pass"])
        self.assertIn("FIELD_SCOPED_DEPENDENCY_CHANGED",out["errors"])
        self.assertIn("AUTHORITY_EPOCH_CHANGED",out["errors"])

    def test_declared_mutation_conflict_still_fails_closed(self):
        args=self.base_args()
        args["current_authority_epoch"]="2"*64
        args["intervening_paths"]=["canonical/runtime/new_candidate.py"]
        out=classify_snapshot_v2(
            **args,
            field_dependency_results=[field_result(stale=False)],
            allow_field_scoped_epoch_rebase=True,
        )
        self.assertFalse(out["pass"])
        self.assertIn("INTERVENING_PATH_CONFLICT",out["errors"])

    def test_same_epoch_nonconflicting_advance_preserves_v1_behavior(self):
        out=classify_snapshot_v2(
            **self.base_args(),
            field_dependency_results=[],
            allow_field_scoped_epoch_rebase=False,
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(
            out["status"],
            "PASS__SEMANTICALLY_CURRENT__NONCONFLICTING_MAIN_ADVANCE",
        )
        self.assertTrue(out["verification_reuse_allowed"])

    def test_field_specs_group_by_source(self):
        out=_group_field_dependencies([
            "canonical/governance/A.json#/x",
            "canonical/governance/B.json#/z",
            "canonical/governance/A.json#/y",
        ])
        self.assertEqual(
            out,
            {
                "canonical/governance/A.json":["/x","/y"],
                "canonical/governance/B.json":["/z"],
            },
        )

    def test_duplicate_field_spec_fails_closed(self):
        with self.assertRaises(Exception):
            _group_field_dependencies([
                "canonical/governance/A.json#/x",
                "canonical/governance/A.json#/x",
            ])


if __name__=="__main__":
    unittest.main(verbosity=2)
