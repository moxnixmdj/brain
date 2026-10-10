from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

from canonical.runtime import r2_semantic_residual_ledger_v1 as residual_ledger

ROOT = Path(__file__).resolve().parents[2]
R2_PATH = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
REC_PATH = ROOT / "canonical/governance/R2_V75_BOUNDED_SEMANTIC_POSITIVE_RECONCILIATION_20261010_V1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class R2V75BoundedSemanticPositiveReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r2 = load(R2_PATH)
        cls.rec = load(REC_PATH)
        cls.cell = cls.r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]

    def test_version_advances_only_positive_reuse_authority(self):
        self.assertIn("__V75__", self.r2["status"])
        self.assertIn("REGCAP_DEFINITE_BUFFER_REFERENCE_LIVE_BOUND", self.r2["status"])
        self.assertIn("SPREAD_RELATION_IDENTITY_LIVE_BOUND", self.r2["status"])
        self.assertFalse(self.r2["global_open_world_closure_claimed"])
        self.assertIn("ONE_PRIMARY_FINANCE_SEMANTIC_RESIDUAL", self.r2["status"])
        self.assertEqual(
            self.r2["primary_primitive_state"],
            self.rec["predecessor"]["primary_primitive_state"],
        )

    def test_open_residual_boundary_is_exactly_preserved(self):
        self.assertFalse(self.rec["scheduler_invariance"]["remaining_boundary_changed"])
        self.assertEqual(
            self.cell["remaining_boundary"],
            self.rec["predecessor"]["remaining_boundary"],
        )
        self.assertEqual(
            self.r2["remaining_hard_frontier"],
            self.rec["predecessor"]["remaining_boundary"],
        )
        self.assertFalse(
            self.r2["r2_v75_bounded_semantic_positive_reconciliation"][
                "remaining_boundary_changed"
            ]
        )

    def test_scheduler_counts_and_one_primary_unsolved_are_preserved(self):
        sched = self.r2["scheduler_result"]
        self.assertEqual(sched["direct_route_count"], 40)
        self.assertEqual(sched["bounded_family_count"], 36)
        self.assertEqual(
            sched["primary_internal_unsolved_pending_acquisition_or_experiment_cell_count"],
            1,
        )
        delta = self.r2["r2_v75_bounded_semantic_positive_reconciliation"]
        self.assertEqual(delta["positive_subregion_count_delta"], 2)
        self.assertEqual(delta["direct_route_count_delta"], 0)
        self.assertEqual(delta["bounded_family_count_delta"], 0)
        self.assertEqual(delta["primary_internal_unsolved_count_delta"], 0)
        self.assertEqual(delta["terminal_credit_delta"], 0)

    def test_reconciliation_blob_is_exactly_bound(self):
        delta = self.r2["r2_v75_bounded_semantic_positive_reconciliation"]
        self.assertEqual(
            git_blob(ROOT / delta["reconciliation_path"]),
            delta["reconciliation_git_blob_sha"],
        )

    def test_definite_buffer_binding_is_exact_and_bounded(self):
        row = self.r2["regcap_definite_buffer_reference_live_binding"]
        for path_key, sha_key in (
            ("runtime_path", "runtime_git_blob_sha"),
            ("truth_certificate_path", "truth_certificate_git_blob_sha"),
            ("dispatcher_path", "dispatcher_git_blob_sha"),
            ("verification_path", "verification_git_blob_sha"),
        ):
            self.assertEqual(git_blob(ROOT / row[path_key]), row[sha_key])
        self.assertFalse(row["general_coreference_closed"])
        self.assertFalse(row["global_alias_authority"])
        self.assertFalse(row["policy_adequacy_authority"])
        self.assertFalse(row["terminal_authority"])

    def test_spread_binding_is_exact_and_bounded(self):
        row = self.r2["spread_relation_identity_live_binding"]
        for path_key, sha_key in (
            ("runtime_path", "runtime_git_blob_sha"),
            ("truth_certificate_path", "truth_certificate_git_blob_sha"),
            ("dispatcher_path", "dispatcher_git_blob_sha"),
            ("verification_path", "verification_git_blob_sha"),
        ):
            self.assertEqual(git_blob(ROOT / row[path_key]), row[sha_key])
        self.assertEqual(
            set(row["supported_concept_ids"]),
            {
                "FINANCE::BID_ASK_SPREAD",
                "FINANCE::CORPORATE_BOND_TREASURY_YIELD_SPREAD",
            },
        )
        self.assertFalse(row["bare_spread_unique_sense_authority"])
        self.assertFalse(row["global_word_sense_authority"])
        self.assertFalse(row["policy_adequacy_authority"])
        self.assertFalse(row["terminal_authority"])

    def test_positive_subregions_preserve_ambiguity_and_open_world_boundaries(self):
        rows = {
            row.get("id"): row
            for row in self.cell["verified_positive_subregions"]
            if isinstance(row, dict) and row.get("id")
        }
        buffer_row = rows["REGCAP_DEFINITE_BUFFER_REFERENCE_IDENTITY_LIVE_TRUTH_DISPATCH"]
        spread_row = rows["SPREAD_RELATION_ENDPOINT_IDENTITY_LIVE_TRUTH_DISPATCH"]
        self.assertTrue(
            buffer_row["state"].endswith(
                "MULTIPLE_DISTINCT_CANDIDATES_PRESERVE_AMBIGUITY"
            )
        )
        self.assertFalse(buffer_row["global_buffer_alias_authority"])
        self.assertFalse(buffer_row["open_world_coreference_complete"])
        self.assertIn("BARE_SPREAD", spread_row["state"])
        self.assertFalse(spread_row["bare_spread_unique_sense_authority"])
        self.assertFalse(spread_row["open_world_finance_semantics_complete"])

    def test_current_dispatch_contains_all_four_live_semantic_families(self):
        dispatch = (
            ROOT / "canonical/runtime/semantic_truth_dispatch_v1.py"
        ).read_text(encoding="utf-8")
        for kind in (
            "MARGIN_CONTEXT_IDENTITY",
            "REGCAP_FACET_ROLE",
            "REGCAP_BUFFER_REFERENCE_IDENTITY",
            "SPREAD_RELATION_IDENTITY",
        ):
            self.assertIn(f'kind == "{kind}"', dispatch)

    def test_shared_cause_ledger_is_unchanged_by_positive_reconciliation(self):
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
