import unittest

from canonical.runtime import livebench_legacy_ifeval_description_inverter_v1 as inv


class LegacyIFEvalDescriptionInverterTests(unittest.TestCase):
    def test_registry_surface_is_exactly_25(self):
        self.assertEqual(len(inv.LEGACY_IDS), 25)

    def test_all_25_public_source_descriptions_recognize(self):
        examples = {
            "keywords:existence": "Include keywords ['alpha', 'beta'] in the response.",
            "keywords:frequency": "In your response, the word alpha should appear at least 3 times.",
            "keywords:forbidden_words": "Do not include keywords ['gamma', 'delta'] in the response.",
            "keywords:letter_frequency": "In your response, the letter q should appear less than 4 times.",
            "language:response_language": "Your ENTIRE response should be in French language, no other language is allowed.",
            "length_constraints:number_sentences": "Your response should contain at least 3 sentences.",
            "length_constraints:number_paragraphs": "There should be 2 paragraphs. Paragraphs are separated with the markdown divider: ***",
            "length_constraints:number_words": "Answer with less than 120 words.",
            "length_constraints:nth_paragraph_first_word": (
                "There should be 3 paragraphs. Paragraphs and only paragraphs are separated "
                "with each other by two new lines as if it was '\\n\\n' in python. "
                "Paragraph 2 must start with word orchid."
            ),
            "detectable_content:number_placeholders": (
                "The response must contain at least 3 placeholders represented by square brackets, such as [address]."
            ),
            "detectable_content:postscript": "At the end of your response, please explicitly add a postscript starting with P.S.",
            "detectable_format:number_bullet_lists": (
                "Your answer must contain exactly 3 bullet points. Use the markdown bullet points such as:\\n"
                "* This is point 1. \\n* This is point 2"
            ),
            "detectable_format:constrained_response": (
                "Answer with one of the following options: ('My answer is yes.', 'My answer is no.', 'My answer is maybe.')"
            ),
            "detectable_format:number_highlighted_sections": (
                "Highlight at least 2 sections in your answer with markdown, i.e. *highlighted section*."
            ),
            "detectable_format:multiple_sections": (
                "Your response must have 3 sections. Mark the beginning of each section with SECTION X, such as:\\n"
                "SECTION 1\\n[content of section 1]\\nSECTION 2\\n[content of section 2]"
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
                "Explain photosynthesis. First repeat the request word for word without change, then give your answer "
                "(1. do not say any words or characters before repeating the request; 2. the request you need to repeat "
                "does not include this sentence)"
            ),
            "startend:end_checker": (
                "Finish your response with this exact phrase Any other questions?. No other words should follow this phrase."
            ),
            "change_case:capital_word_frequency": (
                "In your response, words with all capital letters should appear at least 4 times."
            ),
            "change_case:english_capital": "Your entire response should be in English, and in all capital letters.",
            "change_case:english_lowercase": (
                "Your entire response should be in English, and in all lowercase letters. No capital letters are allowed."
            ),
            "punctuation:no_comma": "In your entire response, refrain from the use of any commas.",
            "startend:quotation": "Wrap your entire response with double quotation marks.",
        }
        self.assertEqual(set(examples), inv.LEGACY_IDS)
        for expected, prompt in examples.items():
            with self.subTest(expected=expected):
                ids = {x["instruction_id"] for x in inv.recognize(prompt)}
                self.assertIn(expected, ids)

    def test_parameter_recovery(self):
        prompt = (
            "Base task. Include keywords ['alpha', 'beta'] in the response. "
            "In your response, the word alpha should appear at least 3 times. "
            "Your response should contain less than 5 sentences. "
            "Finish your response with this exact phrase Any other questions?. "
            "No other words should follow this phrase."
        )
        got = {x["instruction_id"]: x["slots"] for x in inv.recognize(prompt)}
        self.assertEqual(got["keywords:existence"]["keywords"], ["alpha", "beta"])
        self.assertEqual(got["keywords:frequency"]["keyword"], "alpha")
        self.assertEqual(got["keywords:frequency"]["frequency"], 3)
        self.assertEqual(got["keywords:frequency"]["relation"], "at least")
        self.assertEqual(got["length_constraints:number_sentences"]["num_sentences"], 5)
        self.assertEqual(got["startend:end_checker"]["end_phrase"], "Any other questions?")

    def test_language_name_maps_to_exact_legacy_code(self):
        got = inv.recognize("Your ENTIRE response should be in Arabic language, no other language is allowed.")
        self.assertEqual(got[0]["slots"]["language_code"], "ar")

    def test_repeat_prompt_recovers_only_visible_prefix(self):
        base = "Write a compact parser."
        prompt = (
            base + " First repeat the request word for word without change, then give your answer "
            "(1. do not say any words or characters before repeating the request; "
            "2. the request you need to repeat does not include this sentence)"
        )
        got = {x["instruction_id"]: x["slots"] for x in inv.recognize(prompt)}
        self.assertEqual(got["combination:repeat_prompt"]["prompt_to_repeat"], base)

    def test_unrelated_text_fails_closed(self):
        self.assertEqual(inv.recognize("Explain photosynthesis clearly."), [])


if __name__ == "__main__":
    unittest.main()
