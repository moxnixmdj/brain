import unittest

from canonical.runtime import livebench_legacy_visible_constraint_compiler_v1 as c


SAMPLES = {
    "keywords:existence": "Include keywords ['alpha', 'beta'] in the response.",
    "keywords:frequency": "In your response, the word alpha should appear at least 3 times.",
    "keywords:forbidden_words": "Do not include keywords ['alpha', 'beta'] in the response.",
    "keywords:letter_frequency": "In your response, the letter q should appear less than 4 times.",
    "language:response_language": "Your ENTIRE response should be in Japanese language, no other language is allowed.",
    "length_constraints:number_sentences": "Your response should contain at least 4 sentences.",
    "length_constraints:number_paragraphs": "There should be 3 paragraphs. Paragraphs are separated with the markdown divider: ***",
    "length_constraints:number_words": "Answer with less than 120 words.",
    "length_constraints:nth_paragraph_first_word": (
        "There should be 3 paragraphs. Paragraphs and only paragraphs are separated "
        "with each other by two new lines as if it was '\\n\\n' in python. "
        "Paragraph 2 must start with word orbit."
    ),
    "detectable_content:number_placeholders": (
        "The response must contain at least 3 placeholders represented by square brackets, such as [address]."
    ),
    "detectable_content:postscript": (
        "At the end of your response, please explicitly add a postscript starting with P.S."
    ),
    "detectable_format:number_bullet_lists": (
        "Your answer must contain exactly 3 bullet points. Use the markdown bullet points such as:\n"
        "* This is point 1. \n* This is point 2"
    ),
    "detectable_format:constrained_response": (
        "Answer with one of the following options: ('My answer is yes.', 'My answer is no.', 'My answer is maybe.')"
    ),
    "detectable_format:number_highlighted_sections": (
        "Highlight at least 3 sections in your answer with markdown, i.e. *highlighted section*."
    ),
    "detectable_format:multiple_sections": (
        "Your response must have 3 sections. Mark the beginning of each section with Section X, such as:\n"
        "Section 1\n[content of section 1]\nSection 2\n[content of section 2]"
    ),
    "detectable_format:json_format": (
        "Entire output should be wrapped in JSON format. You can use markdown ticks such as " + chr(96) * 3 + "."
    ),
    "detectable_format:title": (
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>."
    ),
    "combination:two_responses": (
        "Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******."
    ),
    "combination:repeat_prompt": (
        "First repeat the request word for word without change, then give your answer "
        "(1. do not say any words or characters before repeating the request; 2. the request "
        "you need to repeat does not include this sentence)"
    ),
    "startend:end_checker": (
        "Finish your response with this exact phrase Any other questions?. "
        "No other words should follow this phrase."
    ),
    "change_case:capital_word_frequency": (
        "In your response, words with all capital letters should appear at least 5 times."
    ),
    "change_case:english_capital": (
        "Your entire response should be in English, and in all capital letters."
    ),
    "change_case:english_lowercase": (
        "Your entire response should be in English, and in all lowercase letters. No capital letters are allowed."
    ),
    "punctuation:no_comma": "In your entire response, refrain from the use of any commas.",
    "startend:quotation": "Wrap your entire response with double quotation marks.",
}


class LegacyVisibleConstraintCompilerTests(unittest.TestCase):
    def test_exact_active_registry_surface_has_25_types(self):
        self.assertEqual(len(c.ACTIVE_IDS), 25)
        self.assertEqual(len(set(c.ACTIVE_IDS)), 25)
        self.assertEqual(set(SAMPLES), set(c.ACTIVE_IDS))
        self.assertTrue(c.source_surface_coverage()["all_active_registry_ids_have_recognizer"])

    def test_every_active_source_description_family_is_recognized(self):
        for expected, prompt in SAMPLES.items():
            with self.subTest(expected=expected):
                observed = {m["instruction_id"] for m in c.recognize(prompt)}
                self.assertIn(expected, observed)

    def test_parameter_recovery(self):
        joined = " Base task. ".join([
            SAMPLES["keywords:frequency"],
            SAMPLES["keywords:letter_frequency"],
            SAMPLES["language:response_language"],
            SAMPLES["length_constraints:number_sentences"],
            SAMPLES["length_constraints:nth_paragraph_first_word"],
            SAMPLES["detectable_format:multiple_sections"],
            SAMPLES["change_case:capital_word_frequency"],
        ])
        matches = {m["instruction_id"]: m["kwargs"] for m in c.recognize(joined)}
        self.assertEqual(matches["keywords:frequency"], {
            "keyword": "alpha", "frequency": 3, "relation": "at least"
        })
        self.assertEqual(matches["keywords:letter_frequency"], {
            "letter": "q", "let_frequency": 4, "let_relation": "less than"
        })
        self.assertEqual(matches["language:response_language"]["language"], "ja")
        self.assertEqual(matches["length_constraints:number_sentences"]["num_sentences"], 4)
        self.assertEqual(matches["length_constraints:nth_paragraph_first_word"]["nth_paragraph"], 2)
        self.assertEqual(matches["detectable_format:multiple_sections"], {
            "num_sections": 3, "section_spliter": "Section"
        })
        self.assertEqual(matches["change_case:capital_word_frequency"]["capital_frequency"], 5)

    def test_repeat_prompt_hidden_value_is_not_invented(self):
        match = [
            m for m in c.recognize("Write a poem. " + SAMPLES["combination:repeat_prompt"])
            if m["instruction_id"] == "combination:repeat_prompt"
        ][0]
        self.assertIsNone(match["kwargs"]["prompt_to_repeat"])
        self.assertEqual(
            match["kwargs"]["parameter_status"],
            "VISIBLE_DESCRIPTION_DOES_NOT_ENCODE_HIDDEN_VALUE",
        )

    def test_semantic_text_does_not_create_checker(self):
        self.assertEqual(
            c.recognize("Explain photosynthesis clearly and compare it with respiration."),
            [],
        )

    def test_source_surface_is_recognition_only(self):
        surface = c.source_surface_coverage()
        self.assertFalse(surface["hidden_terminal_metadata_read"])
        self.assertFalse(surface["response_witness_authorized"])
        self.assertTrue(surface["repeat_prompt_hidden_parameter_residual"])


if __name__ == "__main__":
    unittest.main()
