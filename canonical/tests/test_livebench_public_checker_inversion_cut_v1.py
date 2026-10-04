import unittest

from canonical.runtime import livebench_public_checker_inversion_cut_v1 as inv
from canonical.runtime import livebench_public_grammar_compiler_v2 as c


class PublicCheckerInversionCutTests(unittest.TestCase):
    def test_direct_witnesses_validate(self):
        cases = [
            ("x_word_range", (5, 7)),
            ("x_unique", 6),
            ("x_stopword_pct", 1),
            ("x_sent_type", None),
            ("x_sent_balance", None),
            ("x_conjunctions", 4),
            ("x_person_names", 8),
            ("x_palindrome", None),
            ("x_char_count", None),
            ("x_limited_repeat", 1),
            ("x_pronouns", 5),
            ("x_last_first", None),
            ("x_paragraph_loop", None),
            ("x_increment_words", 3),
            ("x_no_consecutive", None),
            ("x_indent_stairs", None),
            ("x_quote_explain", None),
            ("x_italics_thesis", None),
            ("x_sub_bullets", None),
            ("x_some_bullets", None),
            ("x_multiples", None),
            ("x_mcq", None),
            ("x_reverse_newline", None),
            ("x_word_reverse", None),
            ("x_char_reverse", None),
            ("x_sentence_alpha", None),
        ]
        for rule, arg in cases:
            with self.subTest(rule=rule):
                value = inv.witness(rule, arg)
                self.assertTrue(inv.validate(rule, arg, value), (rule, value))

    def test_compiler_routes_new_parameterized_classes(self):
        prompts = [
            "The response must contain between 5 and 7 words.",
            "Use at least 6 unique words in the response.",
            "Ensure that stop words constitute no more than 1% of the total words in your response.",
            "Use at least 4 different coordinating conjunctions in the response.",
            "Mention at least 8 different person names in the response, from this list of person names: Emma, Liam, Sophia.",
            "The response should not repeat any word more than 1 times.",
            "The response should include at least 5 personal pronouns.",
            "Each sentence must contain exactly 3 more words than the previous one.",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                out = c.synthesize_public_structural_only(prompt)
                self.assertEqual(out["status"], "PASS")
                self.assertFalse(out["semantic_seed_required"])
                self.assertTrue(any(r.startswith("x_") for r in out["matched_public_rules"]))

    def test_compiler_routes_new_static_classes(self):
        prompts = [
            "Maintain a 2:1 ratio of declarative to interrogative sentences.",
            "Ensure that the ratio of sentence types (declarative, interrogative, exclamatory) is balanced.",
            "Include at least 10 single-word palindromes, each at least 5 characters long.",
            "Respond with three sentences, all containing the same number of characters; the sentences cannot be identical.",
            "The last word of each sentence must become the first word of the next sentence.",
            "Write at least two paragraphs, where each paragraph ends with exactly the same word it started with, and separate paragraphs with two newlines.",
            "No two consecutive words can share the same first letter.",
            "Create stairs by incrementally indenting each new line.",
            "Every quoted phrase must be followed by an unquoted explanation.",
            "Each section must begin with a thesis statement in italics, use HTML to indicate the italics.",
            "Your response must include newline-separated bullet points denoted by * and at least one sub-bullet point denoted by - for each bullet point.",
            "Your answer must contain at least two sentences ending in a period followed by at least two newline-separated bullet points denoted by *.",
            "Count from 10 to 50 but only print multiples of 7.",
            "What animal is the national symbol of the US? Respond to this query, but make your sentence in reverse order of what it should be, per letter.",
            "Tell me a 26-sentence story where each sentence's first word starts with the letters of the alphabet in order.",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                out = c.synthesize_public_structural_only(prompt)
                self.assertEqual(out["status"], "PASS")
                self.assertFalse(out["semantic_seed_required"])

    def test_unsupported_semantic_prompt_still_fails_closed(self):
        out = c.synthesize_public_structural_only("Explain photosynthesis clearly.")
        self.assertEqual(out["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
