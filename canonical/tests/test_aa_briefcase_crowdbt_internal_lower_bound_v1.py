from __future__ import annotations

import unittest

from canonical.runtime import aa_briefcase_crowdbt_internal_lower_bound_v1 as cut


class AACrowdBTInternalLowerBoundV1Tests(unittest.TestCase):
    def test_eta_half_erases_all_true_preference_signal(self):
        for p in (0.0, 0.1, 0.5, 0.9, 1.0):
            self.assertAlmostEqual(cut.crowd_bt_observed_preference(p, 0.5), 0.5)

    def test_signal_slope_sign(self):
        self.assertLess(cut.signal_slope(0.25), 0.0)
        self.assertEqual(cut.signal_slope(0.5), 0.0)
        self.assertGreater(cut.signal_slope(0.75), 0.0)

    def test_finite_all_loss_probability_positive_below_certainty(self):
        self.assertGreater(cut.all_loss_probability(0.999, 91), 0.0)

    def test_perfect_expected_preference_requires_perfect_signal_for_certainty(self):
        self.assertLess(cut.crowd_bt_observed_preference(1.0, 0.99), 1.0)
        self.assertEqual(cut.crowd_bt_observed_preference(1.0, 1.0), 1.0)

    def test_current_internal_state_fails_closed(self):
        out = cut.internal_only_lower_bound_cut({
            "task_scope_complete": False,
            "universal_material_top_support": False,
            "frozen_judge_quality_lower_bound": None,
            "frozen_realized_outcomes_bound": False,
            "frozen_scorer_monotonicity_bound": False,
        })
        self.assertEqual(out["status"], "NO_INTERNAL_FINITE_ELO_LOWER_BOUND")
        self.assertFalse(out["threshold_1822_certified"])
        self.assertEqual(len(out["blockers"]), 5)

    def test_scope_and_top_support_alone_still_insufficient(self):
        out = cut.internal_only_lower_bound_cut({
            "task_scope_complete": True,
            "universal_material_top_support": True,
            "frozen_judge_quality_lower_bound": None,
            "frozen_realized_outcomes_bound": False,
            "frozen_scorer_monotonicity_bound": False,
        })
        self.assertEqual(out["status"], "NO_INTERNAL_FINITE_ELO_LOWER_BOUND")
        self.assertIn(
            "CROWD_BT_JUDGE_SIGNAL_LOWER_BOUND_NOT_STRICTLY_ABOVE_HALF",
            out["blockers"],
        )

    def test_eta_lower_bound_equal_half_is_still_insufficient(self):
        out = cut.internal_only_lower_bound_cut({
            "task_scope_complete": True,
            "universal_material_top_support": True,
            "frozen_judge_quality_lower_bound": 0.5,
            "frozen_realized_outcomes_bound": True,
            "frozen_scorer_monotonicity_bound": True,
        })
        self.assertEqual(out["status"], "NO_INTERNAL_FINITE_ELO_LOWER_BOUND")

    def test_information_cut_clears_only_after_all_information_classes_bound(self):
        out = cut.internal_only_lower_bound_cut({
            "task_scope_complete": True,
            "universal_material_top_support": True,
            "frozen_judge_quality_lower_bound": 0.75,
            "frozen_realized_outcomes_bound": True,
            "frozen_scorer_monotonicity_bound": True,
        })
        self.assertEqual(
            out["status"],
            "PREMISES_SUFFICIENT_TO_ATTEMPT_NUMERIC_LOWER_BOUND",
        )
        self.assertFalse(out["threshold_1822_certified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
