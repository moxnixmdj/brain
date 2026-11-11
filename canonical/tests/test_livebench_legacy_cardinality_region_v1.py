import unittest

from canonical.runtime.livebench_legacy_cardinality_region_v1 import (
    compile_cardinality_regions,
    parse_small_number,
)


def region(prompt, family, selector):
    out = compile_cardinality_regions(prompt)
    matches = [
        x for x in out["regions"]
        if x["family"] == family and x["selector"] == selector
    ]
    if len(matches) != 1:
        raise AssertionError((prompt, family, selector, out))
    return matches[0]


class LegacyCardinalityRegionTests(unittest.TestCase):
    def test_number_words(self):
        self.assertEqual(parse_small_number("six"), 6)
        self.assertEqual(parse_small_number("twenty-five"), 25)
        self.assertEqual(parse_small_number("600"), 600)

    def test_word_closed_range(self):
        got = region(
            "Answer in 600 to 700 words.",
            "length_constraints:number_words",
            "response_words",
        )
        self.assertEqual((got["lower"], got["upper"]), (600, 700))

    def test_sentence_closed_range(self):
        got = region(
            "The response should contain 20 to 25 sentences.",
            "length_constraints:number_sentences",
            "response_sentences",
        )
        self.assertEqual((got["lower"], got["upper"]), (20, 25))

    def test_sentence_exact(self):
        got = region(
            "Answer with exactly one sentence.",
            "length_constraints:number_sentences",
            "response_sentences",
        )
        self.assertEqual((got["lower"], got["upper"]), (1, 1))

    def test_line_sentence_equivalence(self):
        got = region(
            "Write a 30-line poem. Each line should contain exactly one sentence.",
            "length_constraints:number_sentences",
            "response_sentences",
        )
        self.assertEqual((got["lower"], got["upper"]), (30, 30))

    def test_keyword_distinct_selectors_are_not_deduplicated(self):
        out = compile_cardinality_regions(
            "Use the word war at least 8 times, and the word peace at least 10 times."
        )
        got = {
            (x["family"], x["selector"]): (x["lower"], x["upper"])
            for x in out["regions"]
        }
        self.assertEqual(got[("keywords:frequency", "war")], (8, None))
        self.assertEqual(got[("keywords:frequency", "peace")], (10, None))

    def test_keyword_range_becomes_one_feasible_region(self):
        got = region(
            'The word "fake" should appear 6 or 7 times.',
            "keywords:frequency",
            "fake",
        )
        self.assertEqual((got["lower"], got["upper"]), (6, 7))

    def test_keyword_at_most_once(self):
        got = region(
            "The word 'future' should appear at most once.",
            "keywords:frequency",
            "future",
        )
        self.assertEqual((got["lower"], got["upper"]), (None, 1))

    def test_capital_frequency_conjunction(self):
        got = region(
            "Use some words in all caps, but make sure that all-caps words appear less than 10 times.",
            "change_case:capital_word_frequency",
            "all_capital_words",
        )
        self.assertEqual((got["lower"], got["upper"]), (1, 9))

    def test_capital_closed_range(self):
        got = region(
            "There should be 5 to 10 capitalized words.",
            "change_case:capital_word_frequency",
            "all_capital_words",
        )
        self.assertEqual((got["lower"], got["upper"]), (5, 10))

    def test_surface_off_by_one_is_not_needed(self):
        got = region(
            "Respond with at most 150 words.",
            "length_constraints:number_words",
            "response_words",
        )
        self.assertEqual((got["lower"], got["upper"]), (None, 150))


if __name__ == "__main__":
    unittest.main()
