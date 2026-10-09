import unittest
from canonical.runtime.coding_v5_positive_adequacy_certificate_gate_v1 import evaluate

SHA = "1" * 40

def receipt():
    return {
        "verified": True,
        "independent": True,
        "source_path": "canonical/verification/example.json",
        "source_sha": SHA,
    }

def base():
    return {
        "policy_id": "ADVANCED_AGENTIC_SOFTWARE_ENGINEERING_MINI_SWE_SUPERPOWERS_V1",
        "policy_binding": {
            "path": "canonical/capabilities/internalized/software_engineering/mini_swe_superpowers_v1/COMPOSED_CONFIGURATION_V1.json",
            "git_blob_sha": SHA,
            "exact_v5_completion_contract": True,
            "transitive_policy_pins_complete": True,
        },
        "target_predicates": ["CODING_CURSORBENCH_GE_57_8"],
        "policy_condition": {
            "predicate_id": "CODING_CELL_PREEXEC_V1",
            "membership_phase": "PRE_EXECUTION",
            "depends_on_acceptance_outcome": False,
            "decision_basis_sound": True,
            "target_relevance_proved": True,
            "target_relevance_receipt": receipt(),
        },
        "resource_admissibility": {"proved": True, "receipt": receipt()},
        "load_bearing_constraints": {"preserved": True, "receipt": receipt()},
        "adequacy_proof": {
            "mode": "FORMAL_ALL_MEMBERS",
            "empirical_generalization_used": False,
            "adequate_for_every_member": True,
            "membership_rule_total_for_declared_cell": True,
            "theorem_receipt": receipt(),
        },
    }

class Tests(unittest.TestCase):
    def test_formal_all_members_candidate_passes_shape_gate(self):
        out = evaluate(base())
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["promotion_authority"])

    def test_one_success_generalization_is_rejected(self):
        p = base()
        p["adequacy_proof"] = {
            "mode": "FINITE_COMPLETE_CELL",
            "empirical_generalization_used": True,
            "member_count": 100,
            "verified_member_count": 1,
            "cell_membership_complete": False,
            "all_members_independently_verified_success": False,
            "exact_v5_identity_on_every_member": True,
            "cell_completeness_receipt": receipt(),
            "member_results_receipt": receipt(),
        }
        out = evaluate(p)
        self.assertFalse(out["pass"])
        self.assertIn("EMPIRICAL_GENERALIZATION_FORBIDDEN", out["errors"])
        self.assertIn("FINITE_CELL_COMPLETENESS_UNPROVED", out["errors"])
        self.assertIn("FINITE_CELL_VERIFIED_MEMBER_COUNT_MISMATCH", out["errors"])

    def test_posthoc_acceptance_outcome_cell_is_rejected(self):
        p = base()
        p["policy_condition"]["membership_phase"] = "POST_EXECUTION"
        p["policy_condition"]["depends_on_acceptance_outcome"] = True
        out = evaluate(p)
        self.assertFalse(out["pass"])
        self.assertIn("POLICY_CONDITION_NOT_PRE_EXECUTION", out["errors"])
        self.assertIn("POSTHOC_ACCEPTANCE_OUTCOME_CONDITION_FORBIDDEN", out["errors"])

    def test_complete_finite_cell_can_pass(self):
        p = base()
        p["adequacy_proof"] = {
            "mode": "FINITE_COMPLETE_CELL",
            "empirical_generalization_used": False,
            "member_count": 3,
            "verified_member_count": 3,
            "cell_membership_complete": True,
            "all_members_independently_verified_success": True,
            "exact_v5_identity_on_every_member": True,
            "cell_completeness_receipt": receipt(),
            "member_results_receipt": receipt(),
        }
        out = evaluate(p)
        self.assertTrue(out["pass"], out)

    def test_current_one_wal_pass_shape_fails_closed(self):
        p = base()
        p["adequacy_proof"] = {
            "mode": "FINITE_COMPLETE_CELL",
            "empirical_generalization_used": False,
            "member_count": 1,
            "verified_member_count": 1,
            "cell_membership_complete": False,
            "all_members_independently_verified_success": True,
            "exact_v5_identity_on_every_member": True,
            "cell_completeness_receipt": receipt(),
            "member_results_receipt": receipt(),
        }
        out = evaluate(p)
        self.assertFalse(out["pass"])
        self.assertIn("FINITE_CELL_COMPLETENESS_UNPROVED", out["errors"])

    def test_unknown_proof_mode_rejected(self):
        p = base()
        p["adequacy_proof"]["mode"] = "OBSERVED_SUCCESS_GENERALIZATION"
        out = evaluate(p)
        self.assertFalse(out["pass"])
        self.assertIn("ADEQUACY_PROOF_MODE_INVALID", out["errors"])

    def test_transitive_policy_pins_are_load_bearing(self):
        p = base()
        p["policy_binding"]["transitive_policy_pins_complete"] = False
        out = evaluate(p)
        self.assertFalse(out["pass"])
        self.assertIn("TRANSITIVE_POLICY_PINS_NOT_PROVED_COMPLETE", out["errors"])

    def test_independent_receipt_required(self):
        p = base()
        p["adequacy_proof"]["theorem_receipt"]["independent"] = False
        out = evaluate(p)
        self.assertFalse(out["pass"])
        self.assertIn("FORMAL_ADEQUACY_THEOREM_RECEIPT_NOT_INDEPENDENT", out["errors"])

if __name__ == "__main__":
    unittest.main()
