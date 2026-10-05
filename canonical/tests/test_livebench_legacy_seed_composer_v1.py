import unittest

from canonical.runtime import livebench_legacy_seed_composer_v1 as composer


class LegacySeedComposerTests(unittest.TestCase):
    def test_keyword_placeholder_title_and_end_preserve_seed(self):
        seed = "Cedar forests store carbon safely."
        prompt = (
            "Include keywords ['cedar'] in the response. "
            "The response must contain at least 2 placeholders represented by square brackets, such as [address]. "
            "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>. "
            "Finish your response with this exact phrase ENDNOW. No other words should follow this phrase."
        )
        out = composer.compose(seed, prompt)
        self.assertEqual(out["status"], "PASS_CANDIDATE_SEED_PRESERVED")
        self.assertIn(seed, out["response"])
        self.assertTrue(out["response"].endswith("ENDNOW"))
        self.assertTrue(out["seed_verbatim_preserved"])
        self.assertGreaterEqual(len(__import__("re").findall(r"\[.*?\]", out["response"])), 2)

    def test_bullets_and_highlights_do_not_alias(self):
        seed = "A semantic answer remains intact."
        prompt = (
            "Highlight at least 2 sections in your answer with markdown, i.e. *highlighted section*. "
            "Your answer must contain exactly 2 bullet points. Use the markdown bullet points such as:\n"
            "* This is point 1. \n"
            "* This is point 2"
        )
        out = composer.compose(seed, prompt)
        self.assertEqual(out["status"], "PASS_CANDIDATE_SEED_PRESERVED")
        self.assertIn(seed, out["response"])
        self.assertEqual(composer._bullet_count(out["response"]), 2)
        self.assertGreaterEqual(composer._highlight_count(out["response"]), 2)

    def test_keyword_frequency_at_least_is_repaired_without_seed_rewrite(self):
        seed = "The answer mentions cedar once."
        prompt = "In your response, the word cedar should appear at least 3 times."
        out = composer.compose(seed, prompt)
        self.assertEqual(out["status"], "PASS_CANDIDATE_SEED_PRESERVED")
        self.assertIn(seed, out["response"])
        self.assertGreaterEqual(
            composer._regex_count("cedar", out["response"], __import__("re").IGNORECASE),
            3,
        )

    def test_less_than_frequency_violation_fails_closed(self):
        seed = "cedar cedar"
        prompt = "In your response, the word cedar should appear less than 2 times."
        out = composer.compose(seed, prompt)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["error"], "LOCAL_CHECKER_EQUIVALENT_POSTVALIDATION_FAILED")

    def test_cross_constraint_contradiction_fails_closed(self):
        seed = "A neutral answer."
        prompt = (
            "Include keywords ['cedar'] in the response. "
            "Do not include keywords ['cedar'] in the response."
        )
        out = composer.compose(seed, prompt)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("keywords:forbidden_words", out["failed_constraint_ids"])

    def test_word_count_is_validate_only(self):
        seed = "one two three four"
        good = composer.compose(seed, "Answer with at least 4 words.")
        self.assertEqual(good["status"], "PASS_CANDIDATE_SEED_PRESERVED")
        self.assertEqual(good["response"], seed)

        bad = composer.compose("one two", "Answer with at least 4 words.")
        self.assertEqual(bad["status"], "FAIL_CLOSED")
        self.assertEqual(bad["error"], "LOCAL_CHECKER_EQUIVALENT_POSTVALIDATION_FAILED")

    def test_repeat_prompt_prefixes_visible_request_and_keeps_seed(self):
        seed = "Trees convert light into stored chemical energy."
        prompt = (
            "Explain photosynthesis simply. "
            "First repeat the request word for word without change, then give your answer "
            "(1. do not say any words or characters before repeating the request; "
            "2. the request you need to repeat does not include this sentence)"
        )
        out = composer.compose(seed, prompt)
        self.assertEqual(out["status"], "PASS_CANDIDATE_SEED_PRESERVED")
        self.assertTrue(out["response"].lower().startswith("explain photosynthesis simply."))
        self.assertIn(seed, out["response"])

    def test_end_phrase_then_outer_quotation_both_postvalidate(self):
        seed = "Core semantic answer."
        prompt = (
            "Finish your response with this exact phrase ENDNOW. No other words should follow this phrase. "
            "Wrap your entire response with double quotation marks."
        )
        out = composer.compose(seed, prompt)
        self.assertEqual(out["status"], "PASS_CANDIDATE_SEED_PRESERVED")
        self.assertTrue(out["response"].startswith('"'))
        self.assertTrue(out["response"].endswith('ENDNOW"'))
        self.assertIn(seed, out["response"])

    def test_unsupported_recognized_family_fails_closed(self):
        out = composer.compose(
            "semantic seed",
            "Your entire response should be in English, and in all lowercase letters. No capital letters are allowed.",
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("change_case:english_lowercase", out["unsupported_constraint_ids"])

    def test_empty_seed_fails_closed(self):
        out = composer.compose("", "In your entire response, refrain from the use of any commas.")
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["error"], "SEMANTIC_SEED_REQUIRED")


if __name__ == "__main__":
    unittest.main()
