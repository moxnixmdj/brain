from __future__ import annotations
import unittest

from canonical.runtime.benchmark_output_information_equivalence_gate_v1 import (
    GateError,
    evaluate_route,
)

def base():
    return {
        "terminal_predicate": {
            "type": "CAPABILITY_RELATION",
            "decision_output": "BRAIN_GE_REFERENCE_CAPABILITY",
            "goal_substitution_allowed": False,
        },
        "route": {
            "type": "PROOF_CARRYING_STRONGER_CERTIFICATE",
            "uses_target_output_leakage": False,
            "reconstructs_private_answers_or_hidden_task_identity": False,
            "proxy_metric_substitution": False,
            "decision_sufficient_statistic_proved": False,
            "strictly_stronger_entailment_proved": True,
            "minimal_information_cut_proved": True,
        },
    }

class Tests(unittest.TestCase):
    def test_capability_relation_stronger_certificate_deletes_native_benchmark(self):
        out = evaluate_route(base())
        self.assertTrue(out["native_benchmark_deletable_for_this_terminal_predicate"])

    def test_exact_statistic_rejects_latent_capability_only(self):
        spec = base()
        spec["terminal_predicate"]["type"] = "EXACT_BENCHMARK_STATISTIC"
        with self.assertRaisesRegex(GateError, "EXACT_STATISTIC_BRIDGE_REQUIRED"):
            evaluate_route(spec)

    def test_exact_statistic_accepts_exact_sufficient_statistic_bridge(self):
        spec = base()
        spec["terminal_predicate"]["type"] = "EXACT_BENCHMARK_STATISTIC"
        spec["route"]["decision_sufficient_statistic_proved"] = True
        spec["route"]["strictly_stronger_entailment_proved"] = False
        spec["route"]["exact_statistic_bridge_proved"] = True
        spec["route"]["frozen_scorer_state_bound"] = True
        out = evaluate_route(spec)
        self.assertEqual(out["information_relation"], "EXACT_SUFFICIENT_STATISTIC")

    def test_proxy_metric_is_rejected(self):
        spec = base()
        spec["route"]["proxy_metric_substitution"] = True
        with self.assertRaisesRegex(GateError, "PROXY_METRIC_SUBSTITUTION_NOT_EXCLUDED"):
            evaluate_route(spec)

    def test_private_answer_reconstruction_is_rejected(self):
        spec = base()
        spec["route"]["reconstructs_private_answers_or_hidden_task_identity"] = True
        with self.assertRaisesRegex(GateError, "PRIVATE_TARGET_RECONSTRUCTION_NOT_EXCLUDED"):
            evaluate_route(spec)

    def test_native_benchmark_is_valid_when_identity_and_scoring_are_bound(self):
        spec = base()
        spec["route"] = {
            "type": "NATIVE_BENCHMARK",
            "uses_target_output_leakage": False,
            "reconstructs_private_answers_or_hidden_task_identity": False,
            "proxy_metric_substitution": False,
            "native_identity_bound": True,
            "native_scoring_semantics_bound": True,
            "minimal_information_cut_proved": True,
        }
        out = evaluate_route(spec)
        self.assertEqual(out["information_relation"], "NATIVE_MEASUREMENT")

    def test_non_native_route_without_entailment_is_rejected(self):
        spec = base()
        spec["route"]["strictly_stronger_entailment_proved"] = False
        with self.assertRaisesRegex(GateError, "DECISION_INFORMATION_EQUIVALENCE_NOT_PROVED"):
            evaluate_route(spec)

    def test_minimum_information_cut_is_mandatory(self):
        spec = base()
        spec["route"]["minimal_information_cut_proved"] = False
        with self.assertRaisesRegex(GateError, "MINIMAL_INFORMATION_CUT_NOT_PROVED"):
            evaluate_route(spec)

if __name__ == "__main__":
    unittest.main(verbosity=2)
