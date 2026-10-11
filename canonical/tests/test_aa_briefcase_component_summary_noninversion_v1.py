from __future__ import annotations

import unittest

from canonical.runtime import aa_briefcase_component_summary_noninversion_v1 as cut


class AAComponentSummaryNoninversionV1Tests(unittest.TestCase):
    def test_same_scope_one_rate_in_both_worlds(self):
        self.assertEqual(3 / 4, 9 / 12)

    def test_same_scope_two_rate_in_both_worlds(self):
        self.assertEqual(1 / 4, 1 / 4)

    def test_same_per_scope_elo_summaries(self):
        out = cut.counterexample()
        self.assertTrue(out["component_summaries_identical"])
        self.assertAlmostEqual(
            out["published_component_summary"]["scope_1_elo"],
            cut.elo_from_win_rate(9 / 12),
            places=12,
        )
        self.assertAlmostEqual(
            out["published_component_summary"]["scope_2_elo"],
            cut.elo_from_win_rate(1 / 4),
            places=12,
        )

    def test_world_a_combined_elo_is_anchor(self):
        out = cut.counterexample()
        self.assertAlmostEqual(out["world_a"]["combined_elo"], 1000.0, places=12)

    def test_world_b_combined_elo_is_higher(self):
        out = cut.counterexample()
        self.assertGreater(out["world_b"]["combined_elo"], 1000.0)
        self.assertAlmostEqual(
            out["world_b"]["combined_elo"],
            1000.0 + 400.0 * __import__("math").log10(5.0 / 3.0),
            places=12,
        )

    def test_identical_component_summaries_different_combined_elo(self):
        out = cut.counterexample()
        self.assertTrue(out["combined_elo_differs"])
        self.assertGreater(out["difference_elo"], 0.0)

    def test_invalid_probability_rejected(self):
        for p in (0.0, 1.0, -0.1, 1.1):
            with self.assertRaisesRegex(ValueError, "P_OUT_OF_RANGE"):
                cut.elo_from_win_rate(p)

    def test_noninterior_or_invalid_counts_rejected(self):
        bad = [
            dict(wins_1=0, total_1=4, wins_2=1, total_2=4),
            dict(wins_1=4, total_1=4, wins_2=1, total_2=4),
            dict(wins_1=3, total_1=0, wins_2=1, total_2=4),
            dict(wins_1=3, total_1=4, wins_2=4, total_2=4),
        ]
        for kwargs in bad:
            with self.assertRaisesRegex(ValueError, "INTERIOR_BINOMIAL_COUNTS_REQUIRED"):
                cut.combined_elo_from_two_binomial_scopes(**kwargs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
