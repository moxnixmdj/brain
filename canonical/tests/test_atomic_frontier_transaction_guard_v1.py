from __future__ import annotations

import unittest

from canonical.runtime.atomic_frontier_transaction_guard_v1 import (
    classify_snapshot,
    paths_overlap,
)


class AtomicFrontierTransactionGuardTests(unittest.TestCase):
    def test_path_overlap_exact_and_tree(self):
        self.assertTrue(paths_overlap("canonical/runtime/a.py", "canonical/runtime/a.py"))
        self.assertTrue(paths_overlap("canonical/runtime", "canonical/runtime/a.py"))
        self.assertTrue(paths_overlap("./canonical/runtime/a.py", "canonical/runtime"))
        self.assertFalse(paths_overlap("canonical/runtime/a.py", "canonical/tests/a.py"))

    def test_exact_current_passes(self):
        out = classify_snapshot(
            base_sha="a" * 40,
            current_sha="a" * 40,
            expected_authority_epoch="1" * 64,
            base_authority_epoch="1" * 64,
            current_authority_epoch="1" * 64,
            intervening_paths=[],
            mutation_paths=["canonical/runtime/a.py"],
        )
        self.assertTrue(out["pass"])
        self.assertEqual(out["status"], "PASS__EXACT_CURRENT")
        self.assertFalse(out["verification_reuse_allowed"])

    def test_unrelated_main_advance_preserves_verified_work(self):
        out = classify_snapshot(
            base_sha="a" * 40,
            current_sha="b" * 40,
            expected_authority_epoch="1" * 64,
            base_authority_epoch="1" * 64,
            current_authority_epoch="1" * 64,
            intervening_paths=["canonical/research/unrelated.json"],
            mutation_paths=["canonical/runtime/a.py"],
            dependency_paths=["canonical/governance/ATOMIC_FRONTIER_TRANSACTION_V1.json"],
        )
        self.assertTrue(out["pass"])
        self.assertEqual(
            out["status"],
            "PASS__SEMANTICALLY_CURRENT__NONCONFLICTING_MAIN_ADVANCE",
        )
        self.assertTrue(out["verification_reuse_allowed"])
        self.assertEqual(
            out["integration_mode"],
            "REBIND_ON_CURRENT_MAIN__PRESERVE_UNCHANGED_VERIFICATION",
        )

    def test_authority_epoch_change_fails_closed(self):
        out = classify_snapshot(
            base_sha="a" * 40,
            current_sha="b" * 40,
            expected_authority_epoch="1" * 64,
            base_authority_epoch="1" * 64,
            current_authority_epoch="2" * 64,
            intervening_paths=[],
            mutation_paths=["canonical/runtime/a.py"],
        )
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_EPOCH_CHANGED", out["errors"])

    def test_declared_path_conflict_fails_closed(self):
        out = classify_snapshot(
            base_sha="a" * 40,
            current_sha="b" * 40,
            expected_authority_epoch="1" * 64,
            base_authority_epoch="1" * 64,
            current_authority_epoch="1" * 64,
            intervening_paths=["canonical/runtime/a.py"],
            mutation_paths=["canonical/runtime/a.py"],
        )
        self.assertFalse(out["pass"])
        self.assertIn("INTERVENING_PATH_CONFLICT", out["errors"])
        self.assertEqual(out["conflicting_paths"], ["canonical/runtime/a.py"])

    def test_dependency_tree_conflict_fails_closed(self):
        out = classify_snapshot(
            base_sha="a" * 40,
            current_sha="b" * 40,
            expected_authority_epoch="1" * 64,
            base_authority_epoch="1" * 64,
            current_authority_epoch="1" * 64,
            intervening_paths=["canonical/governance/x.json"],
            mutation_paths=["canonical/runtime/a.py"],
            dependency_paths=["canonical/governance"],
        )
        self.assertFalse(out["pass"])
        self.assertIn("INTERVENING_PATH_CONFLICT", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
