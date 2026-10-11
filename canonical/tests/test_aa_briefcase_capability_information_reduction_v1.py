from __future__ import annotations

import unittest

from canonical.runtime import aa_briefcase_capability_information_reduction_v1 as r


SUBJECT = "a" * 64


def candidate(cid, cover, cost=1, subject=SUBJECT):
    return {
        "id": cid,
        "verified": True,
        "causal": True,
        "generalization_bound": True,
        "subject_bound": True,
        "reference_bound": True,
        "reference_id": r.REFERENCE_ID,
        "subject_sha256": subject,
        "eliminates_failure_classes": cover,
        "action_cost": cost,
    }


class AABriefcaseCapabilityInformationReductionV1Tests(unittest.TestCase):
    def test_contract_accepts_capability_primary_literal_audit(self):
        r.validate_target_contract({
            "benchmark": "AA-Briefcase",
            "version": "1.1",
            "literal_audit_threshold_elo": 1822,
            "reference_id": r.REFERENCE_ID,
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
                "reference_id": r.REFERENCE_ID,
                "literal_score_is_primary": True,
                "capability_comparison_is_primary": True,
                "score_bearing_dimensions": ["RUBRIC", "ANALYTICAL_QUALITY", "PRESENTATION"],
                "literal_score_backpropagation_forbidden": True,
            })

    def test_one_integrated_certificate_is_minimum_when_complete(self):
        out = r.minimum_sufficient_basis([
            candidate("INTEGRATED", sorted(r.FAILURE_CLASSES), 1)
        ])
        self.assertTrue(out["capability_noninferiority_proved"])
        self.assertEqual(out["selected_certificate_ids"], ["INTEGRATED"])
        self.assertEqual(out["subject_sha256"], SUBJECT)
        self.assertFalse(out["literal_aa_elo_ge_1822_proved"])

    def test_exact_minimum_cost_basis_selected(self):
        out = r.minimum_sufficient_basis([
            candidate("EXPENSIVE_ALL", sorted(r.FAILURE_CLASSES), 10),
            candidate("RAP", ["RUBRIC_INFERIORITY", "ANALYTICAL_QUALITY_INFERIORITY", "PRESENTATION_INFERIORITY"], 1),
            candidate("EXEC", ["EXECUTION_INTERFACE_FAILURE"], 1),
        ])
        self.assertEqual(out["selected_certificate_ids"], ["EXEC", "RAP"])
        self.assertEqual(out["total_action_cost"], 2)

    def test_mixed_subject_certificates_cannot_be_composed(self):
        out = r.minimum_sufficient_basis([
            candidate("RAP", ["RUBRIC_INFERIORITY", "ANALYTICAL_QUALITY_INFERIORITY", "PRESENTATION_INFERIORITY"], 1, "a" * 64),
            candidate("EXEC", ["EXECUTION_INTERFACE_FAILURE"], 1, "b" * 64),
        ])
        self.assertFalse(out["capability_noninferiority_proved"])
        self.assertEqual(out["status"], "OPEN__NO_COMPLETE_SAME_SUBJECT_ADMISSIBLE_BASIS")

    def test_unverified_candidate_rejected(self):
        bad = candidate("BAD", sorted(r.FAILURE_CLASSES), 0)
        bad["verified"] = False
        out = r.minimum_sufficient_basis([bad])
        self.assertFalse(out["capability_noninferiority_proved"])
        self.assertEqual(out["rejected_candidates"][0]["id"], "BAD")

    def test_reference_binding_is_mandatory(self):
        bad = candidate("NOREF", sorted(r.FAILURE_CLASSES), 0)
        bad["reference_bound"] = False
        out = r.minimum_sufficient_basis([bad])
        self.assertFalse(out["capability_noninferiority_proved"])
        self.assertIn("NOREF", out["rejected_candidates"][0]["reason"])

    def test_current_evidence_fails_closed(self):
        out = r.current_evidence_probe()
        self.assertEqual(out["status"], "OPEN__NO_COMPLETE_SAME_SUBJECT_ADMISSIBLE_BASIS")
        self.assertFalse(out["capability_noninferiority_proved"])
        self.assertFalse(out["literal_aa_elo_ge_1822_proved"])
        self.assertEqual(set(out["missing_failure_classes"]), set(r.FAILURE_CLASSES))

    def test_capability_pass_never_backpropagates_literal_elo(self):
        out = r.minimum_sufficient_basis([
            candidate("ALL", sorted(r.FAILURE_CLASSES), 0)
        ])
        self.assertTrue(out["capability_noninferiority_proved"])
        self.assertFalse(out["literal_aa_elo_ge_1822_proved"])
        self.assertIn("DOES_NOT_IMPLY_LITERAL_REALIZED_AA_ELO", out["hard_nonclaim"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
