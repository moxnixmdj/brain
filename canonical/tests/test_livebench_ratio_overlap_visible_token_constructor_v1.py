import unittest

from canonical.runtime.livebench_ratio_overlap_visible_token_constructor_v1 import (
    RatioOverlapConstructionError,
    construct,
    exact_checker_overlap,
)


class RatioOverlapVisibleTokenConstructorTests(unittest.TestCase):
    def test_exact_formula_hits_mid_band(self):
        out = construct("induction", 72)
        self.assertEqual(out["status"], "PASS_UNDER_EXPLICIT_REFERENCE_ASSUMPTIONS")
        self.assertGreaterEqual(out["guaranteed_overlap_percent"], 70)
        self.assertLessEqual(out["guaranteed_overlap_percent"], 74)

    def test_high_target_uses_single_novel_trigram(self):
        out = construct("3.Theoretical", 93)
        self.assertEqual(out["novel_trigram_count"], 1)
        self.assertGreaterEqual(out["guaranteed_overlap_percent"], 91)
        self.assertLessEqual(out["guaranteed_overlap_percent"], 95)

    def test_exact_checker_matches_guaranteed_score_when_assumptions_hold(self):
        reference = "prefix induction suffix"
        out = construct("induction", 72)
        score = exact_checker_overlap(out["response"], reference)
        self.assertAlmostEqual(score, out["guaranteed_overlap_percent"])

    def test_whitespace_reformatting_of_reference_is_irrelevant_for_token(self):
        reference_a = "alpha Transformational beta"
        reference_b = "alpha\nTransformational\n beta"
        out = construct("Transformational", 93)
        self.assertAlmostEqual(
            exact_checker_overlap(out["response"], reference_a),
            exact_checker_overlap(out["response"], reference_b),
        )

    def test_low_target(self):
        out = construct("Describe", 11)
        self.assertGreaterEqual(out["guaranteed_overlap_percent"], 9)
        self.assertLessEqual(out["guaranteed_overlap_percent"], 13)

    def test_rejects_whitespace_token(self):
        with self.assertRaises(RatioOverlapConstructionError):
            construct("two words", 50)

    def test_fail_closed_if_granularity_cannot_hit_band(self):
        out = construct("abc", 93, max_novel_trigrams=100)
        self.assertEqual(out["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
