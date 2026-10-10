from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
ROOT63 = ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V63.json"
TERM = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
REC = ROOT / "canonical/governance/R2_V69_REGCAP_NO_DESCRIPTOR_CONTEXT_RECONCILIATION_20261010_V1.json"
VERIFY = ROOT / "canonical/verification/REGCAP_NO_DESCRIPTOR_CONTEXT_TRUTH_VERIFY_20261010_V1.json"

SUBREGION = "REGCAP_AUTHENTICATED_THREE_RIVAL_DIRECT_SIGNATURE_CONTEXT_WITHOUT_DESCRIPTOR_LOGICAL_EQUIVALENCE"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r2 = load(R2)
        cls.root = load(ROOT63)
        cls.term = load(TERM)
        cls.rec = load(REC)
        cls.verify = load(VERIFY)

    def test_root_v63_preserves_scheduler_population(self):
        self.assertEqual(
            self.root["schema"],
            "PROJECT_BRAIN_ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V63",
        )
        self.assertEqual(
            self.root["supersedes"]["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V62.json",
        )
        sched = self.root["scheduler_result"]
        self.assertEqual(sched["direct_route_count"], 40)
        self.assertEqual(sched["bounded_family_count"], 36)
        self.assertEqual(
            sched["primary_internal_unsolved_pending_acquisition_or_experiment_cell_count"],
            1,
        )
        self.assertEqual(sched["dormant_alternative_route_cell_count"], 1)

    def test_only_new_bounded_subregion_is_added(self):
        law = self.root["residual_recompute_law"]
        self.assertIn(SUBREGION, law["subtracted_verified_subregions"])
        self.assertEqual(law["unsolved_cell_count_before"], 1)
        self.assertEqual(law["unsolved_cell_count_after"], 1)
        self.assertTrue(law["no_externality_reclassification"])
        self.assertTrue(law["no_terminal_credit"])

    def test_finance_tail_remains_open_and_contains_new_subregion(self):
        finance = self.r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        self.assertEqual(
            finance["state"],
            "INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
        )
        rows = [
            x for x in finance["verified_positive_subregions"]
            if isinstance(x, dict) and x.get("id") == SUBREGION
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertFalse(row["literal_descriptor_required"])
        self.assertTrue(row["candidate_set_complete_only_for_authenticated_scope"])
        self.assertFalse(row["global_semantic_identity_authority"])
        self.assertFalse(row["open_world_candidate_universe_complete"])

    def test_current_r2_v69_binds_exact_root_v63(self):
        self.assertIn("ACTIVE_CURRENT_R2_AUTHORITY__V69__", self.r2["status"])
        self.assertEqual(
            self.r2["scheduler_cut"]["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V63.json",
        )
        self.assertEqual(self.r2["scheduler_cut"]["git_blob_sha"], git_blob(ROOT63))
        self.assertEqual(self.r2["direct_adequacy"]["current_route_count"], 39)
        self.assertEqual(self.r2["direct_adequacy"]["bounded_family_count"], 36)
        policy = self.r2["fixed_point_information_policy"]
        self.assertTrue(
            policy["authenticated_bounded_regcap_no_descriptor_direct_signature_context_truth_bound"]
        )
        self.assertFalse(
            policy["bounded_regcap_no_descriptor_context_global_identity_authority"]
        )

    def test_terminal_revision_126_projects_v69_v63(self):
        self.assertEqual(self.term["pointer_revision"], 126)
        self.assertIn("CURRENT_R2_V69", self.term["status"])
        cur = self.term["authoritative_sources"]["current_r2_decision_intelligence"]
        self.assertEqual(cur["status"], self.r2["status"])
        self.assertEqual(cur["scheduler_cut"]["git_blob_sha"], git_blob(ROOT63))
        self.assertEqual(
            self.term["live_truth"]["current_r2_scheduler_cut"],
            "ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V63",
        )
        self.assertEqual(
            self.term["live_truth"]["current_r2_pointer_git_blob_sha"],
            git_blob(R2),
        )

    def test_terminal_projection_preserves_global_nonclaims(self):
        live = self.term["live_truth"]
        self.assertTrue(live["r2_regcap_no_descriptor_direct_signature_context_truth_bound"])
        self.assertFalse(
            live["r2_regcap_no_descriptor_context_global_semantic_identity_authority"]
        )
        self.assertFalse(
            live["r2_regcap_no_descriptor_context_open_world_candidate_universe_complete"]
        )
        reconciled = self.term["r2_v69_regcap_no_descriptor_context_truth_reconciliation"]
        self.assertFalse(reconciled["terminal"])
        self.assertFalse(reconciled["finance_tail_closed"])
        self.assertFalse(reconciled["global_semantic_identity_closed"])

    def test_reconciliation_is_content_addressed_and_zero_credit(self):
        self.assertEqual(self.rec["successor"]["current_r2_blob_sha"], git_blob(R2))
        self.assertEqual(self.rec["successor"]["root2_blob_sha"], git_blob(ROOT63))
        self.assertEqual(self.rec["successor"]["current_terminal_blob_sha"], git_blob(TERM))
        self.assertEqual(self.rec["successor"]["terminal_pointer_revision"], 126)
        self.assertFalse(self.rec["semantic_delta"]["finance_tail_closed"])
        self.assertFalse(self.rec["semantic_delta"]["global_semantic_identity_closed"])
        self.assertFalse(self.rec["semantic_delta"]["open_world_ontology_mapping_closed"])
        self.assertEqual(self.rec["accounting"]["acceptance_credit_delta"], 0)
        self.assertEqual(self.rec["accounting"]["terminal_credit_delta"], 0)

    def test_capability_receipt_proves_real_new_scope_and_zero_credit(self):
        self.assertIn("45_OF_45", self.verify["status"])
        self.assertIn("3_OF_3_LIVE_PRIMARY_SOURCE_REPLAY", self.verify["status"])
        self.assertEqual(self.verify["accounting"]["acceptance_credit_delta"], 0)
        self.assertEqual(self.verify["accounting"]["terminal_credit_delta"], 0)

    def test_descriptor_present_prior_subregion_is_preserved(self):
        finance = self.r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        ids = {
            x.get("id") for x in finance["verified_positive_subregions"]
            if isinstance(x, dict)
        }
        self.assertIn(
            "REGCAP_AUTHENTICATED_THREE_RIVAL_BOUNDED_CONTEXT_LOGICAL_EQUIVALENCE",
            ids,
        )
        self.assertIn(SUBREGION, ids)

    def test_gdpval_and_primary_counts_are_unchanged(self):
        gdp = self.r2["current_cell_classifications"]["GDPVAL_AA_OWNER_LAYER"]
        self.assertIn("DORMANT", gdp["state"])
        self.assertEqual(
            self.root["scheduler_result"][
                "primary_internal_unsolved_pending_acquisition_or_experiment_cell_count"
            ],
            1,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
