from __future__ import annotations

import unittest

from canonical.runtime.benchmark_execution_admission_v1 import evaluate


def native_capability_spec(action_kind: str = "BENCHMARK_EXECUTION"):
    return {
        "action_kind": action_kind,
        "incremental_spend_usd": 0,
        "fresh_target_reality_units": 0,
        "uses_target_output_leakage": False,
        "reconstructs_private_answers_or_hidden_task_identity": False,
        "current_minimum_information_cut_member": False,
        "route_nondominated_proved": False,
        "terminal_predicate": {
            "type": "CAPABILITY_RELATION",
            "decision_output": "BRAIN_CAPABILITY_GE_REFERENCE_CAPABILITY",
            "goal_substitution_allowed": False,
        },
        "route": {
            "type": "NATIVE_BENCHMARK",
            "uses_target_output_leakage": False,
            "reconstructs_private_answers_or_hidden_task_identity": False,
            "proxy_metric_substitution": False,
            "native_identity_bound": True,
            "native_scoring_semantics_bound": True,
            "minimal_information_cut_proved": True,
        },
    }


class BenchmarkExecutionAdmissionV1Tests(unittest.TestCase):
    def test_native_benchmark_is_held_until_current_cut_membership_is_proved(self):
        out = evaluate(native_capability_spec())
        self.assertFalse(out["execution_admission"])
        self.assertEqual(out["reason"], "NOT_PROVED_MEMBER_OF_CURRENT_MINIMUM_INFORMATION_CUT")

    def test_native_benchmark_is_held_until_nondominance_is_proved(self):
        spec = native_capability_spec()
        spec["current_minimum_information_cut_member"] = True
        out = evaluate(spec)
        self.assertFalse(out["execution_admission"])
        self.assertEqual(out["reason"], "ROUTE_NONDOMINANCE_UNPROVED")

    def test_provider_ui_does_not_prove_self_service_access(self):
        spec = native_capability_spec("PROVIDER_ACCESS_ACQUISITION")
        spec["current_minimum_information_cut_member"] = True
        spec["route_nondominated_proved"] = True
        spec["self_service_provisioning_verified"] = False
        spec["existing_authorized_credential_verified"] = False
        out = evaluate(spec)
        self.assertFalse(out["execution_admission"])
        self.assertEqual(out["reason"], "PROVIDER_ACCESS_NOT_VERIFIED_IMMEDIATELY_EXECUTABLE")

    def test_verified_self_service_provider_route_can_be_admitted_when_minimal(self):
        spec = native_capability_spec("PROVIDER_ACCESS_ACQUISITION")
        spec["current_minimum_information_cut_member"] = True
        spec["route_nondominated_proved"] = True
        spec["self_service_provisioning_verified"] = True
        out = evaluate(spec)
        self.assertTrue(out["execution_admission"])

    def test_zero_reality_stronger_certificate_development_is_admitted_without_credit(self):
        out = evaluate(
            {
                "action_kind": "STRONGER_CERTIFICATE_DEVELOPMENT",
                "incremental_spend_usd": 0,
                "fresh_target_reality_units": 0,
                "uses_target_output_leakage": False,
                "reconstructs_private_answers_or_hidden_task_identity": False,
                "goal_preserving": True,
            }
        )
        self.assertTrue(out["execution_admission"])
        self.assertEqual(out["status"], "ADMIT__ZERO_REALITY_PROOF_DEVELOPMENT")
        self.assertEqual(out["capability_credit_delta"], 0)

    def test_proof_development_with_fresh_target_reality_fails_closed(self):
        out = evaluate(
            {
                "action_kind": "EQUIVALENCE_PROOF_DEVELOPMENT",
                "incremental_spend_usd": 0,
                "fresh_target_reality_units": 1,
                "uses_target_output_leakage": False,
                "reconstructs_private_answers_or_hidden_task_identity": False,
                "goal_preserving": True,
            }
        )
        self.assertFalse(out["execution_admission"])
        self.assertEqual(out["reason"], "PROOF_DEVELOPMENT_MUST_BE_ZERO_TARGET_REALITY")

    def test_exact_statistic_native_route_still_requires_current_cut(self):
        spec = native_capability_spec()
        spec["terminal_predicate"]["type"] = "EXACT_BENCHMARK_STATISTIC"
        out = evaluate(spec)
        self.assertFalse(out["execution_admission"])
        self.assertEqual(out["reason"], "NOT_PROVED_MEMBER_OF_CURRENT_MINIMUM_INFORMATION_CUT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
