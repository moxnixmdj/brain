from __future__ import annotations

import math
import unittest

from canonical.runtime.paired_anytime_noninferiority import PROOF_MODE, evaluate


def base(brain, opus, checkpoints=None, alpha=0.05):
    n = len(brain)
    return {
        "proof_mode": PROOF_MODE,
        "brain_case_scores": brain,
        "opus_case_scores": opus,
        "alpha": alpha,
        "checkpoint_schedule": checkpoints or [n],
        "population_frozen_before_results": True,
        "selection_rule_frozen_before_results": True,
        "case_order_frozen_before_results": True,
        "scorer_frozen_before_results": True,
        "brain_candidate_frozen_before_results": True,
        "opus_model_configuration_frozen_before_results": True,
        "checkpoint_schedule_frozen_before_results": True,
        "independent_acceptance": True,
        "case_pairs_independent_conditionally_on_frozen_population": True,
        "same_case_pairing": True,
        "zero_case_replacement": True,
        "zero_adaptive_case_selection": True,
        "zero_tuning_replay": True,
        "zero_incremental_spend": True,
    }


class PairedAnytimeNoninferiorityTests(unittest.TestCase):
    def test_perfect_paired_advantage_can_pass_early(self):
        out = evaluate(base([1.0] * 8, [0.0] * 8, checkpoints=[8, 16, 32]))
        self.assertTrue(out["pass"])
        self.assertEqual(out["checkpoint_index"], 1)
        self.assertGreaterEqual(out["paired_advantage_one_sided_lower_bound"], 0.0)

    def test_equal_systems_do_not_fake_noninferiority_at_small_n(self):
        out = evaluate(base([0.5] * 8, [0.5] * 8, checkpoints=[8, 16]))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "NO_PASS_YET")

    def test_current_prefix_must_end_on_predeclared_checkpoint(self):
        out = evaluate(base([1.0] * 7, [0.0] * 7, checkpoints=[8, 16]))
        self.assertFalse(out["pass"])
        self.assertIn("CURRENT_SAMPLE_COUNT_NOT_PREDECLARED_CHECKPOINT", out["errors"])

    def test_paired_lengths_must_match(self):
        out = evaluate(base([1.0] * 8, [0.0] * 7, checkpoints=[8]))
        self.assertFalse(out["pass"])
        self.assertIn("PAIRED_SCORE_LENGTH_MISMATCH", out["errors"])

    def test_out_of_range_score_fails_closed(self):
        out = evaluate(base([1.0] * 7 + [1.1], [0.0] * 8, checkpoints=[8]))
        self.assertFalse(out["pass"])
        self.assertIn("BRAIN_CASE_SCORES_OUT_OF_RANGE:7", out["errors"])

    def test_adaptive_case_selection_fails_closed(self):
        payload = base([1.0] * 8, [0.0] * 8, checkpoints=[8])
        payload["zero_adaptive_case_selection"] = False
        out = evaluate(payload)
        self.assertFalse(out["pass"])
        self.assertIn("ZERO_ADAPTIVE_CASE_SELECTION_NOT_TRUE", out["errors"])

    def test_second_checkpoint_uses_smaller_alpha_slice(self):
        out1 = evaluate(base([1.0] * 8, [0.0] * 8, checkpoints=[8, 16]))
        out2 = evaluate(base([1.0] * 16, [0.0] * 16, checkpoints=[8, 16]))
        self.assertLess(out2["checkpoint_alpha"], out1["checkpoint_alpha"])
        expected = 0.05 * 6.0 / (math.pi**2 * 4.0)
        self.assertAlmostEqual(out2["checkpoint_alpha"], expected)

    def test_alpha_spending_never_exceeds_total_budget(self):
        checkpoints = [4, 8, 16, 32, 64, 128]
        out = evaluate(base([1.0] * 128, [0.0] * 128, checkpoints=checkpoints))
        self.assertLessEqual(out["cumulative_alpha_spend"], 0.05)

    def test_same_case_pairing_is_mandatory(self):
        payload = base([1.0] * 8, [0.0] * 8, checkpoints=[8])
        payload["same_case_pairing"] = False
        out = evaluate(payload)
        self.assertFalse(out["pass"])
        self.assertIn("SAME_CASE_PAIRING_NOT_TRUE", out["errors"])


if __name__ == "__main__":
    unittest.main()
