from __future__ import annotations

import unittest

from canonical.runtime.matched_statistical_acceptance import PROOF_MODE, evaluate


def base(scores, target=0.80, alpha=0.01):
    return {
        "proof_mode": PROOF_MODE,
        "brain_case_scores": scores,
        "frozen_opus_acceptance_bound": target,
        "alpha": alpha,
        "population_frozen_before_results": True,
        "selection_rule_frozen_before_results": True,
        "scorer_frozen_before_results": True,
        "candidate_frozen_before_results": True,
        "independent_acceptance": True,
        "case_scores_independent_conditionally_on_frozen_population": True,
        "zero_case_replacement": True,
        "zero_adaptive_selection": True,
        "zero_tuning_replay": True,
        "zero_incremental_spend": True,
    }


class MatchedStatisticalAcceptanceTests(unittest.TestCase):
    def test_large_perfect_population_can_clear_bound(self):
        out = evaluate(base([1.0] * 400, target=0.90, alpha=0.01))
        self.assertTrue(out["pass"])
        self.assertGreaterEqual(out["brain_one_sided_lower_bound"], 0.90)

    def test_small_perfect_population_does_not_fake_certainty(self):
        out = evaluate(base([1.0] * 10, target=0.90, alpha=0.01))
        self.assertFalse(out["pass"])

    def test_mean_above_target_can_still_fail_lower_bound(self):
        out = evaluate(base([1.0] * 90 + [0.0] * 10, target=0.85, alpha=0.01))
        self.assertGreater(out["brain_mean_score"], 0.85)
        self.assertFalse(out["pass"])

    def test_adaptive_selection_fails_closed(self):
        payload = base([1.0] * 400, target=0.90)
        payload["zero_adaptive_selection"] = False
        out = evaluate(payload)
        self.assertFalse(out["pass"])
        self.assertIn("ZERO_ADAPTIVE_SELECTION_NOT_TRUE", out["errors"])

    def test_out_of_range_score_fails_closed(self):
        out = evaluate(base([1.0, 1.1]))
        self.assertFalse(out["pass"])
        self.assertIn("SCORE_OUT_OF_RANGE:1", out["errors"])


if __name__ == "__main__":
    unittest.main()
