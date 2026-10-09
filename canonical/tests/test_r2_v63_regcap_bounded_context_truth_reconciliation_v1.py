from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
ROOT59 = ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V59.json"
TERM = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
REC = ROOT / "canonical/governance/R2_REGCAP_BOUNDED_CONTEXT_TRUTH_RECONCILIATION_20261009_V1.json"
VERIFY = ROOT / "canonical/verification/REGCAP_BOUNDED_CONTEXT_TRUTH_VERIFY_20261009_V1.json"

SUBREGION = "REGCAP_AUTHENTICATED_THREE_RIVAL_BOUNDED_CONTEXT_LOGICAL_EQUIVALENCE"
OLD_WAKE_1 = "NEW_SCOPE_COMPLETE_SOUND_FINANCE_INTERPRETATION_OR_CONSTRAINT_BOUND"
NEW_WAKE_1 = "NEW_SCOPE_COMPLETE_SOUND_FINANCE_INTERPRETATION_OR_CONSTRAINT_BOUND_OUTSIDE_VERIFIED_REGCAP_CCOB_CCYB_TLAC_BOUNDED_RIVAL_CONTEXT_SCOPE"
OLD_WAKE_2 = "NEW_AUTHENTICATED_CONTEXT_OR_RELATION_EVIDENCE_THAT_DISCRIMINATES_SURVIVING_SENSES"
NEW_WAKE_2 = "NEW_AUTHENTICATED_CONTEXT_OR_RELATION_EVIDENCE_THAT_DISCRIMINATES_SURVIVING_SENSES_OUTSIDE_VERIFIED_REGCAP_CCOB_CCYB_TLAC_BOUNDED_RIVAL_CONTEXT_SCOPE"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r2 = load(R2)
        cls.root = load(ROOT59)
        cls.term = load(TERM)
        cls.rec = load(REC)
        cls.verify = load(VERIFY)

    def test_root2_v59_preserves_scheduler_population(self):
        self.assertEqual(self.root["schema"], "PROJECT_BRAIN_ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V59")
        self.assertEqual(
            self.root["supersedes"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V58.json",
        )
        sched = self.root["scheduler_result"]
        self.assertEqual(sched["direct_route_count"], 39)
        self.assertEqual(sched["bounded_family_count"], 36)
        self.assertEqual(
            sched["primary_internal_unsolved_pending_acquisition_or_experiment_cell_count"],
            1,
        )
        self.assertEqual(sched["dormant_alternative_route_cell_count"], 1)

    def test_only_exact_regcap_subregion_is_subtracted(self):
        law = self.root["residual_recompute_law"]
        self.assertEqual(law["before_active_wake_count"], 11)
        self.assertEqual(law["after_active_wake_count"], 11)
        self.assertEqual(law["unsolved_cell_count_before"], 1)
        self.assertEqual(law["unsolved_cell_count_after"], 1)
        self.assertIn(SUBREGION, law["subtracted_verified_subregions"])
        self.assertTrue(law["no_externality_reclassification"])
        self.assertTrue(law["no_terminal_credit"])

    def test_finance_wakes_are_refined_not_deleted(self):
        finance = self.root["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        wakes = finance["wake_on"]
        self.assertNotIn(OLD_WAKE_1, wakes)
        self.assertNotIn(OLD_WAKE_2, wakes)
        self.assertIn(NEW_WAKE_1, wakes)
        self.assertIn(NEW_WAKE_2, wakes)
        self.assertEqual(finance["state"], "INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT")
        self.assertTrue(
            any(
                isinstance(x, dict) and x.get("id") == SUBREGION
                for x in finance["verified_positive_subregions"]
            )
        )

    def test_gdpval_remains_dormant(self):
        gdp = self.root["current_cell_classifications"]["GDPVAL_AA_OWNER_LAYER"]
        self.assertIn("DORMANT", gdp["state"])

    def test_current_r2_v63_binds_exact_v59_blob(self):
        self.assertIn("ACTIVE_CURRENT_R2_AUTHORITY__V63__", self.r2["status"])
        self.assertEqual(
            self.r2["scheduler_cut"]["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V59.json",
        )
        self.assertEqual(self.r2["scheduler_cut"]["git_blob_sha"], git_blob(ROOT59))
        self.assertEqual(self.r2["direct_adequacy"]["current_route_count"], 39)
        self.assertEqual(self.r2["direct_adequacy"]["bounded_family_count"], 36)
        self.assertTrue(
            self.r2["fixed_point_information_policy"]["authenticated_bounded_regcap_context_truth_bound"]
        )
        self.assertFalse(
            self.r2["fixed_point_information_policy"]["bounded_regcap_context_truth_global_identity_authority"]
        )

    def test_terminal_revision_113_projects_v63_v59(self):
        self.assertEqual(self.term["pointer_revision"], 113)
        self.assertIn("CURRENT_R2_V63", self.term["status"])
        cur = self.term["authoritative_sources"]["current_r2_decision_intelligence"]
        self.assertEqual(cur["status"], self.r2["status"])
        self.assertEqual(cur["scheduler_cut"]["git_blob_sha"], git_blob(ROOT59))
        self.assertEqual(
            self.term["live_truth"]["current_r2_scheduler_cut"],
            "ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V59",
        )
        self.assertEqual(
            self.term["live_truth"]["current_r2_pointer_git_blob_sha"],
            git_blob(R2),
        )

    def test_terminal_projection_preserves_global_nonclaims(self):
        live = self.term["live_truth"]
        self.assertTrue(live["r2_regcap_authenticated_bounded_context_truth_bound"])
        self.assertFalse(live["r2_regcap_bounded_context_truth_global_semantic_identity_authority"])
        self.assertFalse(live["r2_regcap_bounded_context_truth_open_world_candidate_universe_complete"])
        self.assertTrue(self.term["r2_v63_regcap_bounded_context_truth_reconciliation"]["terminal_remains_false"])

    def test_reconciliation_is_content_addressed_and_zero_credit(self):
        self.assertEqual(self.rec["successor"]["current_r2_blob_sha"], git_blob(R2))
        self.assertEqual(self.rec["successor"]["root2_blob_sha"], git_blob(ROOT59))
        self.assertEqual(self.rec["successor"]["current_terminal_blob_sha"], git_blob(TERM))
        self.assertEqual(self.rec["successor"]["terminal_pointer_revision"], 113)
        self.assertFalse(self.rec["semantic_delta"]["finance_tail_closed"])
        self.assertFalse(self.rec["semantic_delta"]["global_semantic_identity_closed"])
        self.assertFalse(self.rec["semantic_delta"]["open_world_ontology_mapping_closed"])
        self.assertEqual(self.rec["accounting"]["acceptance_credit_delta"], 0)
        self.assertEqual(self.rec["accounting"]["terminal_credit_delta"], 0)

    def test_capability_verification_receipt_still_zero_credit(self):
        self.assertIn("54_OF_54", self.verify["status"])
        self.assertEqual(self.verify["accounting"]["acceptance_credit_delta"], 0)
        self.assertEqual(self.verify["accounting"]["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
