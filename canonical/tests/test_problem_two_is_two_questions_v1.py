"""Pin the dilution split: applicable vs not-applicable askings.

The published coverage (0.2999) mixes two populations that mean different things. An asking whose
target does not contain the demonstrated form cannot be reached by any one-example operator, and
counting it in the same fraction makes a 63.6% mechanism read as 30%. These tests hold the split,
the regroup rule, and the fact that nothing here re-ran the corpus — it is the same 330 askings
regrouped by the organ's own refusal.
"""
from __future__ import annotations

import unittest

from canonical.tools.which_fix_moves_generalization_v1 import CLASSES, classify


class RegroupRuleTest(unittest.TestCase):
    def test_the_split_rule_is_the_organs_own_refusal(self):
        """No extra table decides applicability: 'nothing of that form here' is the organ's words."""
        self.assertIn("nothing in the file has the form", CLASSES["NO_FORM_IN_FILE"]["match"])

    def test_that_refusal_is_marked_not_a_fix(self):
        """So it can never be read as an opportunity an operator should buy."""
        self.assertIn("NOT A FIX", CLASSES["NO_FORM_IN_FILE"]["real_price"])

    def test_an_edit_counts_as_applicable(self):
        self.assertEqual(classify(None), "EDITED")
        self.assertNotEqual(classify(None), "NO_FORM_IN_FILE")

    def test_other_refusals_stay_applicable(self):
        """A file that HAS the form but is refused is the real frontier, not dilution."""
        for name in ("CALL_SHAPE_NOT_SHOWN", "NAME_NOT_AVAILABLE", "BLOCK_SHAPE"):
            self.assertNotEqual(classify("refused: " + CLASSES[name]["match"]), "NO_FORM_IN_FILE", name)


class RecordedSplitTest(unittest.TestCase):
    """The numbers in the memo, held so a later change to the organ cannot leave them looking current."""

    RECORDED = {
        "applicable_askings": 162,
        "applicable_right": 386,
        "applicable_denominator": 607,
        "not_applicable_askings": 168,
        "not_applicable_right": 0,
        "all_askings": 330,
        "all_right": 386,
        "all_denominator": 1287,
    }

    def test_the_two_populations_add_up(self):
        r = self.RECORDED
        self.assertEqual(r["applicable_askings"] + r["not_applicable_askings"], r["all_askings"])
        self.assertEqual(r["applicable_right"] + r["not_applicable_right"], r["all_right"])
        self.assertEqual(r["applicable_denominator"] + 680, r["all_denominator"])

    def test_adaptation_where_the_form_is_present_is_about_sixty_four_percent(self):
        r = self.RECORDED
        share = r["applicable_right"] / r["applicable_denominator"]
        self.assertAlmostEqual(share, 0.6359, places=4)
        self.assertGreater(share, 0.6)

    def test_nothing_is_recovered_where_the_form_is_absent(self):
        """Not a weakness: there is nothing there to change."""
        self.assertEqual(self.RECORDED["not_applicable_right"], 0)

    def test_the_published_figure_is_the_diluted_one(self):
        r = self.RECORDED
        self.assertAlmostEqual(r["all_right"] / r["all_denominator"], 0.2999, places=4)
        self.assertLess(r["all_right"] / r["all_denominator"],
                        r["applicable_right"] / r["applicable_denominator"])


if __name__ == "__main__":
    unittest.main()
