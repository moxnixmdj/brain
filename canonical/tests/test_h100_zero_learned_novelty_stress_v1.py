from __future__ import annotations

import json
import math
import unittest

from canonical.runtime.h100_zero_learned_novelty_stress_v1 import (
    PREEXPOSURE,
    THRESHOLD,
    _nrmse,
    truth,
)


class H100ZeroLearnedNoveltyStressTests(unittest.TestCase):
    def test_preexposure_is_frozen_and_has_exact_denominators(self):
        doc = json.loads(PREEXPOSURE.read_text())
        self.assertEqual(doc["status"], "FROZEN_BEFORE_OUTCOMES__PUBLIC_SYNTHETIC_NONTERMINAL__ZERO_CREDIT")
        self.assertEqual(doc["population"]["task_count"], 12)
        self.assertEqual(len(doc["population"]["tasks"]), 12)
        self.assertEqual(len(doc["frozen_routes"]), 3)
        self.assertEqual(doc["outcome_definition"]["exact_route_task_pairs"], 36)

    def test_truth_functions_are_finite_on_all_preexposed_points(self):
        doc = json.loads(PREEXPOSURE.read_text())
        for task in doc["population"]["tasks"]:
            fid = task["formula_id"]
            if task["arity"] == 1:
                xs = doc["population"]["single_input_training_x"] + doc["population"]["single_input_holdout_x"]
                vals = [truth(fid, float(x)) for x in xs]
            else:
                pairs = doc["population"]["two_input_training_pairs"] + doc["population"]["two_input_holdout_pairs"]
                vals = [truth(fid, float(x), float(z)) for x,z in pairs]
            self.assertTrue(all(math.isfinite(v) for v in vals), task)

    def test_nrmse_zero_for_identical_vectors(self):
        actual = [1.0, -2.0, 4.0, 9.0]
        self.assertEqual(_nrmse(actual, list(actual)), 0.0)

    def test_holdout_threshold_is_frozen(self):
        doc = json.loads(PREEXPOSURE.read_text())
        self.assertEqual(doc["outcome_definition"]["useful_candidate"], "ROUTE_RETURNS_A_CANDIDATE_WITH_HOLDOUT_NRMSE_LE_1E_MINUS_7_ON_ALL_PREEXPOSED_HOLDOUT_POINTS")
        self.assertEqual(THRESHOLD, 1e-7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
