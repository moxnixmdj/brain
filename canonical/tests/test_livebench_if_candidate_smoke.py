from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.evaluation.livebench_if_candidate import adapter


class LiveBenchIFCandidateSmokeTests(unittest.TestCase):
    def test_registry_has_expected_58_checkers(self):
        self.assertEqual(len(adapter.instructions_registry.INSTRUCTION_DICT), 58)

    def test_word_count_range_good_bad_boundary(self):
        c = adapter.instructions.WordCountRangeChecker("count:word_count_range")
        c.build_description(min_words=2, max_words=3)
        self.assertTrue(c.check_following("one two"))
        self.assertTrue(c.check_following("one two three"))
        self.assertFalse(c.check_following("one"))

    def test_stopword_percentage_uses_local_only_resource(self):
        c = adapter.instructions.StopWordPercentageChecker("ratio:stop_words")
        c.build_description(percentage=50)
        self.assertTrue(c.check_following("cat dog"))
        self.assertTrue(c.check_following("the cat"))
        self.assertFalse(c.check_following("the and"))
        self.assertIn("stopwords", adapter.download_calls)

    def test_ngram_overlap(self):
        c = adapter.instructions.NGramOverlapChecker("ratio:overlap")
        c.build_description(reference_text="abcdef", percentage=100)
        self.assertTrue(c.check_following("abcdef"))
        self.assertFalse(c.check_following("abcxyz"))

    def test_pos_tagger_good_bad_boundary(self):
        c = adapter.instructions.StartWithVerbChecker("words:start_verb")
        c.build_description()
        self.assertTrue(c.check_following("Go now."))
        self.assertFalse(c.check_following("Cats sleep."))
        self.assertFalse(c.check_following(""))

    def test_emoji_checker(self):
        c = adapter.instructions.EmojiSentenceChecker("format:emoji")
        c.build_description()
        self.assertTrue(c.check_following("Hello 😀."))
        self.assertFalse(c.check_following("Hello."))
        self.assertTrue(c.check_following("😀."))

    def test_syllable_parity_checker(self):
        c = adapter.instructions.AlternateParitySyllablesChecker("words:odd_even_syllables")
        c.build_description()
        self.assertTrue(c.check_following("cat water cat water"))
        self.assertFalse(c.check_following("cat dog"))
        self.assertTrue(c.check_following("cat"))

    def test_evaluation_lib_integration(self):
        inp = adapter.evaluation_lib.InputExample(
            key=1,
            instruction_id_list=["count:word_count_range"],
            prompt="Synthetic non-terminal preflight.",
            kwargs=[{"min_words": 2, "max_words": 2}],
        )
        good = adapter.evaluation_lib.test_instruction_following_loose(inp, "one two")
        bad = adapter.evaluation_lib.test_instruction_following_loose(inp, "one")
        self.assertTrue(good.follow_all_instructions)
        self.assertFalse(bad.follow_all_instructions)


if __name__ == "__main__":
    unittest.main(verbosity=2)
