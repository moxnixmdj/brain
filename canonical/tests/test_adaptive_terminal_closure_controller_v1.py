from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.adaptive_terminal_closure_controller_v1 import compile_controller

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class AdaptiveTerminalClosureControllerV1Tests(unittest.TestCase):
    def live(self):
        return (
            load("canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json"),
            load("canonical/governance/CURRENT_27_INFORMATION_DOMINANCE_V1.json"),
            load("canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json"),
            load("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"),
        )

    def test_live_v10_policy_compiles_zero_credit(self):
        sched, dominance, matched, matrix = self.live()
        out = compile_controller(sched, dominance, matched, matrix)
        self.assertTrue(out["status"].startswith("PASS"), out)
        self.assertEqual(out["current_scheduling_authority"], "V10_INDEPENDENT_PASS")
        self.assertEqual(out["live_world"]["unresolved_predicates"], 27)
        self.assertEqual(out["live_world"]["nondominated_certificates"], 16)
        self.assertEqual(out["live_world"]["unique_zero_reality_requirements"], 19)
        self.assertEqual(out["live_world"]["matched_primitive_child_facts"], 16)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])
        self.assertEqual(out["acceptance_credit"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertEqual(out["ownership_credit_delta"], 0)

    def test_unknown_probabilities_are_not_invented(self):
        sched, dominance, matched, matrix = self.live()
        out = compile_controller(sched, dominance, matched, matrix)
        rows = out["parallel_lanes"]["nondominated_zero_reality_certificates"]
        self.assertTrue(rows)
        self.assertTrue(all(r["probability_status"] == "UNKNOWN_NOT_INVENTED" for r in rows))
        self.assertTrue(all(r["posterior_mean"] is None for r in rows))
        self.assertTrue(all(r["empirical_expected_value_per_second"] is None for r in rows))

    def test_empirical_probability_changes_resource_order_only(self):
        sched, dominance, matched, matrix = self.live()
        empirical = {
            "SHARED_PUBLIC_BENCHMARK_ABI_ROUTE_CERTIFICATE": {
                "successes": 9,
                "failures": 1,
                "expected_latency_s": 10,
            },
            "MATCHED_SCOPE_BINDING_CERTIFICATE": {
                "successes": 1,
                "failures": 9,
                "expected_latency_s": 100,
            },
        }
        out = compile_controller(sched, dominance, matched, matrix, empirical)
        rows = out["parallel_lanes"]["nondominated_zero_reality_certificates"]
        by_id = {r["certificate_id"]: r for r in rows}
        self.assertGreater(
            by_id["SHARED_PUBLIC_BENCHMARK_ABI_ROUTE_CERTIFICATE"]["empirical_expected_value_per_second"],
            by_id["MATCHED_SCOPE_BINDING_CERTIFICATE"]["empirical_expected_value_per_second"],
        )
        self.assertTrue(all(r["parallel"] for r in rows))
        self.assertFalse(out["execution_authority"])
        self.assertEqual(out["acceptance_credit"], 0)

    def test_matched_lane_is_exact_16_target_specific_facts(self):
        sched, dominance, matched, matrix = self.live()
        out = compile_controller(sched, dominance, matched, matrix)
        facts = out["parallel_lanes"]["matched_scope_child_fact_race"]["child_facts"]
        self.assertEqual(len(facts), 16)
        targets = {x["target_predicate"] for x in facts}
        self.assertEqual(len(targets), 8)
        for target in targets:
            self.assertEqual(sum(1 for x in facts if x["target_predicate"] == target), 2)

    def test_accepted_unowned_ownership_lane_is_live_now(self):
        sched, dominance, matched, matrix = self.live()
        out = compile_controller(sched, dominance, matched, matrix)
        families = out["parallel_lanes"]["ownership_reconciliation"]["accepted_but_not_verified_owned_families"]
        self.assertIn("SELF_VERIFICATION_DEBUGGING_AND_RECOVERY", families)
        self.assertIn("SUBAGENT_DELEGATION_AND_COORDINATION", families)
        self.assertNotIn("EXACT_SYMBOLIC_COMPUTATION", families)
        self.assertNotIn("LONG_HORIZON_MEMORY_AND_CONTINUITY", families)

    def test_stale_scheduler_fails_closed(self):
        sched, dominance, matched, matrix = self.live()
        sched = json.loads(json.dumps(sched))
        sched["status"] = "ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V9_CURRENT"
        out = compile_controller(sched, dominance, matched, matrix)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("CURRENT_SCHEDULING_AUTHORITY_NOT_V10_INDEPENDENT_PASS", out["errors"])

    def test_fresh_reality_flip_fails_closed(self):
        sched, dominance, matched, matrix = self.live()
        sched = json.loads(json.dumps(sched))
        sched["fresh_reality_authority"] = True
        out = compile_controller(sched, dominance, matched, matrix)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("CURRENT_AUTHORITY_FRESH_REALITY_NOT_FALSE", out["errors"])

    def test_invalid_empirical_observation_rejected(self):
        sched, dominance, matched, matrix = self.live()
        with self.assertRaises(ValueError):
            compile_controller(
                sched,
                dominance,
                matched,
                matrix,
                {
                    "MATCHED_SCOPE_BINDING_CERTIFICATE": {
                        "successes": -1,
                        "failures": 0,
                        "expected_latency_s": 1,
                    }
                },
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
