from __future__ import annotations

import math
import unittest

from canonical.runtime import aa_briefcase_trace_scorer_nonidentifiability_v1 as cut


class AATraceScorerNonidentifiabilityV1Tests(unittest.TestCase):
    def test_eta_half_flat_probability(self):
        for rating in (-10000, 0, 1000, 2000, 10000):
            self.assertAlmostEqual(
                cut.crowd_bt_probability(rating, eta=0.5),
                0.5,
                places=12,
            )

    def test_eta_half_public_contract_does_not_imply_unique_fit(self):
        out = cut.public_contract_implies_unique_subject_rating(eta=0.5)
        self.assertFalse(out["public_contract_implies_unique_subject_rating"])
        self.assertEqual(
            out["status"],
            "COUNTEREXAMPLE_NONUNIQUE_FLAT_LIKELIHOOD",
        )

    def test_all_wins_likelihood_strictly_increases_for_eta_above_half(self):
        values = [
            cut.all_wins_log_likelihood(
                rating,
                eta=0.8,
                comparison_count=5,
            )
            for rating in (-1000, 0, 1000, 2000, 5000)
        ]
        self.assertEqual(values, sorted(values))
        self.assertTrue(all(b > a for a, b in zip(values, values[1:])))

    def test_all_wins_public_contract_has_no_finite_mle_counterexample(self):
        out = cut.public_contract_implies_unique_subject_rating(eta=0.8)
        self.assertFalse(out["public_contract_implies_unique_subject_rating"])
        self.assertEqual(out["status"], "COUNTEREXAMPLE_NO_FINITE_MLE_ALL_WINS")

    def test_eta_below_half_reverses_signal(self):
        weak = cut.crowd_bt_probability(500, eta=0.25)
        strong = cut.crowd_bt_probability(1500, eta=0.25)
        self.assertLess(strong, weak)

    def test_two_hidden_traces_share_public_state_but_differ(self):
        out = cut.two_trace_countermodel({
            "task_count": 91,
            "project_count": 4,
            "judge_panel_size": 3,
        })
        self.assertTrue(out["same_public_state"])
        self.assertTrue(out["trace_digests_differ"])
        self.assertFalse(out["public_state_determines_complete_score_trace"])

    def test_score_trace_route_still_reports_two_missing_premises(self):
        out = cut.evaluate_internal_score_trace_route({
            "public_contract_bound": True,
            "reference_1822_bound": True,
            "complete_trace_equivalence_proved": False,
            "scorer_unique_or_equivariant_proved": False,
        })
        self.assertEqual(
            out["missing"],
            [
                "COMPLETE_REFERENCE_CANDIDATE_TRACE_EQUIVALENCE",
                "SCORER_IMPLEMENTATION_EQUIVARIANCE_OR_UNIQUE_FIT",
            ],
        )
        self.assertFalse(out["threshold_1822_proved"])

    def test_route_passes_only_when_both_remaining_premises_are_bound(self):
        out = cut.evaluate_internal_score_trace_route({
            "public_contract_bound": True,
            "reference_1822_bound": True,
            "complete_trace_equivalence_proved": True,
            "scorer_unique_or_equivariant_proved": True,
        })
        self.assertEqual(out["status"], "PASS_ROUTE_PREMISES")
        self.assertTrue(out["threshold_1822_proved"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
