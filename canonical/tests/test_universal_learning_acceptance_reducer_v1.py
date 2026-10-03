from __future__ import annotations

import unittest

from canonical.runtime import universal_learning_acceptance_reducer_v1 as reducer


def bindings():
    return {
        "claims": [
            {"predicate_id": "TOOL_LEARNING_SECOND_TASK_TRANSFER", "state": "PROVED"},
            {"predicate_id": "TOOL_LEARNING_NO_UNSUPPORTED_PROMOTION", "state": "PROVED"},
        ]
    }


def verification():
    return {
        "independent_runner": {"conclusion": "success"},
        "verified": {
            "unknown_capture_total": True,
            "only_verified_coverage_uses_known_route": True,
            "learning_channels_complete": True,
            "candidate_requires_verification_before_trust": True,
            "promotion_requires_verified_state": True,
            "environment_change_invalidates_to_unknown": True,
            "finite_control_product_exhaustively_checked": True,
            "actual_component_bindings_exact": True,
        },
    }


class UniversalLearningAcceptanceReducerV1Tests(unittest.TestCase):
    def test_structural_theorem_leaves_only_empirical_residual(self):
        out = reducer.reduce(
            contract_verification=verification(),
            evidence_bindings=bindings(),
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "STRUCTURAL_NOVELTY_SCOPE_CLOSED__EMPIRICAL_NONINFERIORITY_REMAINS_OPEN",
        )
        self.assertFalse(out["separate_environment_enumeration_required"])
        self.assertEqual(
            out["remaining_residuals"],
            ["MATCHED_EMPIRICAL_LEARNING_EFFECTIVENESS_NONINFERIORITY"],
        )
        self.assertFalse(out["target_predicate_discharge_candidate"])
        self.assertEqual(out["acceptance_credit_delta"], 0)

    def test_missing_structural_fact_fails_closed(self):
        v = verification()
        v["verified"]["actual_component_bindings_exact"] = False
        out = reducer.reduce(
            contract_verification=v,
            evidence_bindings=bindings(),
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_existing_transfer_and_promotion_atoms_are_load_bearing(self):
        for predicate in (
            "TOOL_LEARNING_SECOND_TASK_TRANSFER",
            "TOOL_LEARNING_NO_UNSUPPORTED_PROMOTION",
        ):
            b = bindings()
            for row in b["claims"]:
                if row["predicate_id"] == predicate:
                    row["state"] = "OPEN"
            out = reducer.reduce(
                contract_verification=verification(),
                evidence_bindings=b,
            )
            self.assertFalse(out["pass"], predicate)

    def test_empirical_pass_can_only_create_candidate_not_credit(self):
        empirical = {
            "target_predicate": reducer.TARGET,
            "independent": True,
            "matched_distribution_frozen": True,
            "brain_lcb_ge_opus_ucb_minus_delta": True,
            "contamination_controls_pass": True,
        }
        out = reducer.reduce(
            contract_verification=verification(),
            evidence_bindings=bindings(),
            empirical_noninferiority=empirical,
        )
        self.assertTrue(out["target_predicate_discharge_candidate"], out)
        self.assertEqual(
            out["status"],
            "CANDIDATE_FULL_PREDICATE_DISCHARGE__SEPARATE_ACCEPTANCE_PROMOTION_REQUIRED",
        )
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])

    def test_empirical_shortcut_missing_controls_does_not_close(self):
        empirical = {
            "target_predicate": reducer.TARGET,
            "independent": True,
            "matched_distribution_frozen": True,
            "brain_lcb_ge_opus_ucb_minus_delta": True,
            "contamination_controls_pass": False,
        }
        out = reducer.reduce(
            contract_verification=verification(),
            evidence_bindings=bindings(),
            empirical_noninferiority=empirical,
        )
        self.assertFalse(out["target_predicate_discharge_candidate"], out)
        self.assertEqual(
            out["remaining_residuals"],
            ["MATCHED_EMPIRICAL_LEARNING_EFFECTIVENESS_NONINFERIORITY"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
