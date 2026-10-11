from __future__ import annotations

import unittest

from canonical.runtime.aa_briefcase_internal_proof_route_completeness_v1 import (
    RouteError,
    classify_hidden_threshold_proof,
)


class AAProofRouteCompletenessV1Tests(unittest.TestCase):
    def test_identified_passing_world_closes_by_identification(self):
        out = classify_hidden_threshold_proof(
            hidden_worlds=["w0", "w1"],
            threshold_truth_by_world={"w0": False, "w1": True},
            identified_world="w1",
        )
        self.assertTrue(out["proved"])
        self.assertEqual(out["status"], "IDENTIFICATION_ROUTE")

    def test_identified_failing_world_does_not_prove_threshold(self):
        out = classify_hidden_threshold_proof(
            hidden_worlds=["w0", "w1"],
            threshold_truth_by_world={"w0": False, "w1": True},
            identified_world="w0",
        )
        self.assertFalse(out["proved"])

    def test_all_consistent_worlds_pass_closes_robustly(self):
        out = classify_hidden_threshold_proof(
            hidden_worlds=["w0", "w1", "w2"],
            threshold_truth_by_world={"w0": True, "w1": True, "w2": True},
        )
        self.assertTrue(out["proved"])
        self.assertEqual(out["status"], "ROBUST_ROUTE")

    def test_all_consistent_worlds_fail_is_robust_failure(self):
        out = classify_hidden_threshold_proof(
            hidden_worlds=["w0", "w1"],
            threshold_truth_by_world={"w0": False, "w1": False},
        )
        self.assertFalse(out["proved"])
        self.assertEqual(out["status"], "ROBUST_FAILURE")

    def test_mixed_unidentified_worlds_generate_countermodel_pair(self):
        out = classify_hidden_threshold_proof(
            hidden_worlds=["fail", "pass"],
            threshold_truth_by_world={"fail": False, "pass": True},
        )
        self.assertFalse(out["proved"])
        self.assertEqual(out["status"], "UNIDENTIFIED_AND_NONROBUST")
        self.assertEqual(out["countermodel_pair"], ["fail", "pass"])

    def test_world_map_must_be_complete(self):
        with self.assertRaisesRegex(RouteError, "THRESHOLD_WORLD_MAP_MISMATCH"):
            classify_hidden_threshold_proof(
                hidden_worlds=["w0", "w1"],
                threshold_truth_by_world={"w0": True},
            )

    def test_duplicate_worlds_rejected(self):
        with self.assertRaisesRegex(RouteError, "HIDDEN_WORLDS_INVALID"):
            classify_hidden_threshold_proof(
                hidden_worlds=["w0", "w0"],
                threshold_truth_by_world={"w0": True},
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
