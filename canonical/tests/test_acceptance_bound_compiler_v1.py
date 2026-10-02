from __future__ import annotations
import unittest
from canonical.runtime.acceptance_bound_compiler_v1 import evaluate


class Tests(unittest.TestCase):
    def test_tb4_conservative_cut(self):
        out = evaluate({
            "metric_semantics_frozen": True,
            "population_frozen": True,
            "worst_case_assignment_admissible": True,
            "metric_type": "BINARY_RATE",
            "total_slots": 330,
            "executable_slots": 270,
            "observed_successes": 0,
            "observed_failures": 0,
            "threshold_percent": 66.4,
        })
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["proof_route_ready"], out)
        self.assertEqual(out["required_successes"], 220)
        self.assertEqual(out["decision"], "UNRESOLVED")

    def test_binary_rate_pass_lock(self):
        out = evaluate({
            "metric_semantics_frozen": True,
            "population_frozen": True,
            "worst_case_assignment_admissible": True,
            "metric_type": "BINARY_RATE",
            "total_slots": 330,
            "executable_slots": 270,
            "observed_successes": 220,
            "observed_failures": 0,
            "threshold_percent": 66.4,
        })
        self.assertEqual(out["decision"], "PASS_LOCKED")

    def test_binary_rate_fail_lock(self):
        out = evaluate({
            "metric_semantics_frozen": True,
            "population_frozen": True,
            "worst_case_assignment_admissible": True,
            "metric_type": "BINARY_RATE",
            "total_slots": 330,
            "executable_slots": 270,
            "observed_successes": 100,
            "observed_failures": 151,
            "threshold_percent": 66.4,
        })
        self.assertEqual(out["decision"], "FAIL_LOCKED")

    def test_unsupported_metric_fails_closed(self):
        out = evaluate({
            "metric_semantics_frozen": True,
            "population_frozen": True,
            "worst_case_assignment_admissible": True,
            "metric_type": "ELO",
        })
        self.assertFalse(out["pass"])
        self.assertIn("UNSUPPORTED_METRIC_TYPE", out["errors"])

    def test_bounded_mean(self):
        out = evaluate({
            "metric_semantics_frozen": True,
            "population_frozen": True,
            "worst_case_assignment_admissible": True,
            "metric_type": "BOUNDED_MEAN",
            "total_items": 10,
            "observed_items": 8,
            "known_sum": 8,
            "item_min": 0,
            "item_max": 1,
            "threshold": 0.7,
            "direction": "HIGHER_IS_BETTER",
        })
        self.assertEqual(out["decision"], "PASS_LOCKED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
