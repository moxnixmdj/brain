from __future__ import annotations

import unittest

from canonical.runtime import aa_briefcase_capability_information_reduction_v1 as r


class AABriefcaseCapabilityInformationReductionV1Tests(unittest.TestCase):
    def test_contract_accepts_capability_primary_literal_audit(self):
        r.validate_target_contract({
            "benchmark": "AA-Briefcase",
            "version": "1.1",
            "literal_audit_threshold_elo": 1822,
            "literal_score_is_primary": False,
            "capability_comparison_is_primary": True,
            "score_bearing_dimensions": ["RUBRIC", "ANALYTICAL_QUALITY", "PRESENTATION"],
            "literal_score_backpropagation_forbidden": True,
        })

    def test_literal_score_cannot_be_primary(self):
        with self.assertRaisesRegex(r.ReductionError, "LITERAL_SCORE_MUST_BE_AUDIT_ONLY"):
            r.validate_target_contract({
                "benchmark": "AA-Briefcase",
                "version": "1.1",
                "literal_audit_threshold_elo": 1822,
                "literal_score_is_primary": True,
                "capability_comparison_is_primary": True,
                "score_bearing_dimensions": ["RUBRIC", "ANALYTICAL_QUALITY", "PRESENTATION"],
                "literal_score_backpropagation_forbidden": True,
            })

    def test_one_integrated_certificate_is_minimum_when_complete(self):
        out = r.minimum_sufficient_basis([{
            "id": "INTEGRATED",
            "verified": True,
            "causal": True,
            "generalization_bound": True,
            "subject_bound": True,
            "reference_bound": True,
            "eliminates_failure_classes": sorted(r.FAILURE_CLASSES),
            "action_cost": 1,
        }])
        self.assertTrue(out["capability_noninferiority_proved"])
        self.assertEqual(out["selected_certificate_ids"], ["INTEGRATED"])
        self.assertFalse(out["literal_aa_elo_ge_1822_proved"])

    def test_exact_minimum_cost_basis_selected(self):
        def c(cid, cover, cost):
            return {
                "id": cid, "verified": True, "causal": True,
                "generalization_bound": True, "subject_bound": True,
                "reference_bound": True,
                "eliminates_failure_classes": cover, "action_cost": cost,
            }
        out = r.minimum_sufficient_basis([
            c("EXPENSIVE_ALL", sorted(r.FAILURE_CLASSES), 10),
            c("RAP", ["RUBRIC_INFERIORITY", "ANALYTICAL_QUALITY_INFERIORITY", "PRESENTATION_INFERIORITY"], 1),
            c("EXEC", ["EXECUTION_INTERFACE_FAILURE"], 1),
        ])
        self.assertEqual(out["selected_certificate_ids"], ["EXEC", "RAP"])
        self.assertEqual(out["total_action_cost"], 2)

    def test_unverified_candidate_rejected(self):
        out = r.minimum_sufficient_basis([{
            "id": "BAD",
            "verified": False,
            "causal": True,
            "generalization_bound": True,
            "subject_bound": True,
            "reference_bound": True,
            "eliminates_failure_classes": sorted(r.FAILURE_CLASSES),
            "action_cost": 0,
        }])
        self.assertFalse(out["capability_noninferiority_proved"])
        self.assertEqual(out["status"], "OPEN__NO_COMPLETE_ADMISSIBLE_BASIS")
        self.assertEqual(out["rejected_candidates"][0]["id"], "BAD")

    def test_reference_binding_is_mandatory(self):
        out = r.minimum_sufficient_basis([{
            "id": "NOREF",
            "verified": True,
            "causal": True,
            "generalization_bound": True,
            "subject_bound": True,
            "reference_bound": False,
            "eliminates_failure_classes": sorted(r.FAILURE_CLASSES),
            "action_cost": 0,
        }])
        self.assertFalse(out["capability_noninferiority_proved"])
        self.assertIn("NOREF", out["rejected_candidates"][0]["reason"])

    def test_current_evidence_fails_closed(self):
        out = r.current_evidence_probe()
        self.assertEqual(out["status"], "OPEN__NO_COMPLETE_ADMISSIBLE_BASIS")
        self.assertFalse(out["capability_noninferiority_proved"])
        self.assertFalse(out["literal_aa_elo_ge_1822_proved"])
        self.assertEqual(set(out["missing_failure_classes"]), set(r.FAILURE_CLASSES))

    def test_capability_pass_never_backpropagates_literal_elo(self):
        out = r.minimum_sufficient_basis([{
            "id": "ALL",
            "verified": True,
            "causal": True,
            "generalization_bound": True,
            "subject_bound": True,
            "reference_bound": True,
            "eliminates_failure_classes": sorted(r.FAILURE_CLASSES),
            "action_cost": 0,
        }])
        self.assertTrue(out["capability_noninferiority_proved"])
        self.assertFalse(out["literal_aa_elo_ge_1822_proved"])
        self.assertIn("DOES_NOT_IMPLY_LITERAL_REALIZED_AA_ELO", out["hard_nonclaim"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
