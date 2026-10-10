from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

from canonical.runtime import r2_semantic_residual_ledger_v1 as residual_ledger

ROOT = Path(__file__).resolve().parents[2]
R2_PATH = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
REC_PATH = ROOT / "canonical/governance/R2_V74_BOUNDED_SEMANTIC_POSITIVE_RECONCILIATION_20261010_V1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class R2V74BoundedSemanticPositiveReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r2 = load(R2_PATH)
        cls.rec = load(REC_PATH)
        cls.cell = cls.r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]

    def test_version_advanced_without_claiming_global_closure(self):
        self.assertIn("__V74__", self.r2["status"])
        self.assertIn("MARGIN_CONTEXT_IDENTITY_LIVE_BOUND", self.r2["status"])
        self.assertIn("REGCAP_FACET_ROLE_LIVE_BOUND", self.r2["status"])
        self.assertFalse(self.r2["global_open_world_closure_claimed"])
        self.assertIn("ONE_PRIMARY_FINANCE_SEMANTIC_RESIDUAL", self.r2["status"])
        self.assertEqual(
            self.r2["primary_primitive_state"],
            self.rec["predecessor"]["primary_primitive_state"],
        )

    def test_open_residual_boundary_is_exactly_preserved(self):
        self.assertTrue(self.rec["preservation"]["remaining_boundary_must_equal_predecessor"])
        self.assertEqual(
            self.cell["remaining_boundary"],
            self.rec["predecessor"]["remaining_boundary"],
        )
        self.assertEqual(
            self.r2["r2_v74_bounded_semantic_positive_reconciliation"]["remaining_boundary_changed"],
            False,
        )

    def test_scheduler_counts_and_primary_unsolved_count_are_preserved(self):
        sched = self.r2["scheduler_result"]
        self.assertEqual(
            sched["direct_route_count"],
            self.rec["predecessor"]["direct_route_count"],
        )
        self.assertEqual(
            sched["bounded_family_count"],
            self.rec["predecessor"]["bounded_family_count"],
        )
        self.assertEqual(
            sched["primary_internal_unsolved_pending_acquisition_or_experiment_cell_count"],
            1,
        )
        delta = self.r2["r2_v74_bounded_semantic_positive_reconciliation"]
        self.assertEqual(delta["direct_route_count_delta"], 0)
        self.assertEqual(delta["bounded_family_count_delta"], 0)
        self.assertEqual(delta["primary_internal_unsolved_count_delta"], 0)
        self.assertEqual(delta["terminal_credit_delta"], 0)

    def test_margin_context_truth_binding_is_exact_and_bounded(self):
        row = self.r2["margin_context_identity_live_binding"]
        self.assertEqual(
            git_blob(ROOT / row["truth_certificate_path"]),
            row["truth_certificate_git_blob_sha"],
        )
        self.assertEqual(
            git_blob(ROOT / row["dispatcher_path"]),
            row["dispatcher_git_blob_sha"],
        )
        self.assertEqual(
            git_blob(ROOT / row["verification_path"]),
            row["verification_git_blob_sha"],
        )
        self.assertFalse(row["bare_margin_unique_sense_authority"])
        self.assertFalse(row["global_word_sense_authority"])
        self.assertFalse(row["policy_adequacy_authority"])
        self.assertFalse(row["terminal_authority"])

    def test_regcap_facet_role_binding_is_exact_and_nonexclusive(self):
        row = self.r2["regcap_facet_role_live_binding"]
        self.assertEqual(
            git_blob(ROOT / row["projection_path"]),
            row["projection_git_blob_sha"],
        )
        self.assertEqual(
            git_blob(ROOT / row["truth_certificate_path"]),
            row["truth_certificate_git_blob_sha"],
        )
        self.assertEqual(
            git_blob(ROOT / row["dispatcher_path"]),
            row["dispatcher_git_blob_sha"],
        )
        self.assertEqual(
            git_blob(ROOT / row["verification_path"]),
            row["verification_git_blob_sha"],
        )
        self.assertFalse(row["exclusive_single_facet_authority"])
        self.assertFalse(row["concept_identity_authority"])
        self.assertFalse(row["policy_adequacy_authority"])
        self.assertFalse(row["terminal_authority"])

    def test_positive_subregions_are_recorded_without_open_world_upgrade(self):
        rows = {
            row.get("id"): row
            for row in self.cell["verified_positive_subregions"]
            if isinstance(row, dict) and row.get("id")
        }
        margin = rows["MARGIN_CONTEXT_IDENTITY_LIVE_TRUTH_DISPATCH"]
        facet = rows["REGCAP_TYPED_FACET_ROLE_LIVE_TRUTH_DISPATCH"]
        self.assertFalse(margin["bare_margin_unique_sense_closed"])
        self.assertFalse(margin["open_world_finance_semantics_complete"])
        self.assertFalse(facet["exclusive_single_facet_authority"])
        self.assertFalse(facet["concept_identity_authority"])
        self.assertFalse(facet["open_world_finance_semantics_complete"])

    def test_live_dispatch_contains_both_truth_families(self):
        dispatch = (
            ROOT / "canonical/runtime/semantic_truth_dispatch_v1.py"
        ).read_text(encoding="utf-8")
        self.assertIn('kind == "MARGIN_CONTEXT_IDENTITY"', dispatch)
        self.assertIn('kind == "REGCAP_FACET_ROLE"', dispatch)

    def test_shared_cause_ledger_still_classifies_current_residual(self):
        ledger = residual_ledger.load_current_ledger()
        self.assertTrue(ledger["classification_complete"], ledger)
        self.assertEqual(
            ledger["highest_fanout_shared_cause"],
            "SEMANTIC_SCOPE_AUTHORITY",
        )
        shared = {row["cause_id"]: row for row in ledger["shared_causes"]}
        self.assertEqual(shared["SEMANTIC_SCOPE_AUTHORITY"]["fanout_clause_count"], 5)
        self.assertEqual(shared["POLICY_CHANGING_OBSERVABILITY"]["fanout_clause_count"], 4)
        self.assertEqual(shared["DOCUMENT_EFFECT_AUTHORITY"]["fanout_clause_count"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
