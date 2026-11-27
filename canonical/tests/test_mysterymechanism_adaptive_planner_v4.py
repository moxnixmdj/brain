from __future__ import annotations

import math
import unittest

from canonical.runtime import mysterymechanism_adaptive_planner_v4 as v4


class MysteryMechanismAdaptivePlannerV4Tests(unittest.TestCase):
    def test_exact_synthetic_log_power_is_structurally_admitted(self):
        rows = []
        for x, z in [
            (0.2, 0.03), (1.0, 0.1), (4.0, 0.25), (15.0, 0.8),
            (60.0, 0.05), (250.0, 0.5), (900.0, 0.2),
        ]:
            rows.append({"x1": x, "x2": z, "out": 0.013 * x**0.47 * z**0.81})
        out = v4.finalize(
            rows,
            bounds={"x1": [0.1, 1000.0], "x2": [0.01, 1.0]},
            target="out",
        )
        self.assertEqual(
            out["status"],
            "CANDIDATE_READY__STRUCTURALLY_CONSTRAINED__PRIVATE_UNVERIFIED",
            out,
        )
        self.assertEqual(out["route"], "LOG_POWER")
        self.assertFalse(out["private_score_claimed"])
        self.assertEqual(out["acceptance_credit_delta"], 0)

    def test_public_churchill_walkthrough_is_not_false_positive(self):
        rows = [
            {"x1": 63.5657, "x2": 1.2799, "out": 3.3766},
            {"x1": 4615.6906, "x2": 5.3388, "out": 76.4846},
            {"x1": 1.0, "x2": 0.2, "out": 0.1004},
            {"x1": 300000.0, "x2": 0.2, "out": 277.5832},
            {"x1": 1.0, "x2": 10.0, "out": -1.1800},
            {"x1": 300000.0, "x2": 10.0, "out": 1263.4885},
            {"x1": 547.7226, "x2": 1.4142, "out": 13.5045},
        ]
        out = v4.finalize(
            rows,
            bounds={"x1": [1.0, 300000.0], "x2": [0.2, 10.0]},
            target="out",
        )
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__STRUCTURAL_IDENTIFIABILITY_NOT_PROVED",
            out,
        )
        self.assertTrue(out["old_v3_candidate_quarantined"])
        self.assertIsNone(out["candidate"])

    def test_public_viscosity_walkthrough_remains_ambiguous(self):
        rows = [
            {"x1": 0.5944, "x2": 1.9188, "out": 12.2245},
            {"x1": 0.5044, "x2": 0.2068, "out": 10.3732},
            {"x1": 0.05, "x2": 0.05, "out": 4.3715},
            {"x1": 0.70, "x2": 0.05, "out": 30.6686},
            {"x1": 0.05, "x2": 30.0, "out": 2.3912},
            {"x1": 0.70, "x2": 30.0, "out": 16.3743},
            {"x1": 0.375, "x2": 1.225, "out": 5.7241},
        ]
        product = v4.structured_product_discover(
            rows,
            bounds={"x1": [0.05, 0.70], "x2": [0.05, 30.0]},
            target="out",
        )
        cand = product["candidate"]
        self.assertIsNotNone(cand, product)
        self.assertGreater(
            cand["max_plausible_prediction_disagreement_nrmse"], 0.01, cand
        )
        out = v4.finalize(
            rows,
            bounds={"x1": [0.05, 0.70], "x2": [0.05, 30.0]},
            target="out",
        )
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__STRUCTURAL_IDENTIFIABILITY_NOT_PROVED",
            out,
        )

    def test_v3_experiment_budget_and_zero_credit_are_preserved(self):
        out = v4.next_experiment(
            [{"x": 0.2, "z": 0.3, "out": 1.0}, {"x": 0.8, "z": 0.7, "out": 2.0}],
            bounds={"x": [0, 1], "z": [0, 1]},
            active_experiments_used=5,
        )
        self.assertEqual(out["status"], "ACTIVE_BUDGET_EXHAUSTED")
        self.assertIsNone(out["point"])
        self.assertEqual(out["active_budget"], 5)
        self.assertEqual(out["acceptance_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)