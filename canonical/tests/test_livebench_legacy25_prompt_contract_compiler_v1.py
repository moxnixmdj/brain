import unittest

from canonical.runtime.livebench_legacy25_prompt_contract_compiler_v1 import (
    ACTIVE_LEGACY_IDS,
    compile_prompt,
)

FIXTURES = {
    "keywords:existence": "Include keywords ['amber', 'birch'] in the response.",
    "keywords:frequency": "In your response, the word cedar should appear at least 3 times.",
    "keywords:forbidden_words": "Do not include keywords ['delta', 'ember'] in the response.",
    "keywords:letter_frequency": "In your response, the letter q should appear less than 4 times.",
    "language:response_language": "Your ENTIRE response should be in French language, no other language is allowed.",
    "length_constraints:number_sentences": "Your response should contain at least 3 sentences.",
    "length_constraints:number_paragraphs": "There should be 3 paragraphs. Paragraphs are separated with the markdown divider: ***",
    "length_constraints:number_words": "Answer with less than 120 words.",
    "length_constraints:nth_paragraph_first_word": "There should be 3 paragraphs. Paragraphs and only paragraphs are separated with each other by two new lines as if it was '\\n\\n' in python. Paragraph 2 must start with word harbor.",
    "detectable_content:number_placeholders": "The response must contain at least 2 placeholders represented by square brackets, such as [address].",
    "detectable_content:postscript": "At the end of your response, please explicitly add a postscript starting with P.S.",
    "detectable_format:number_bullet_lists": "Your answer must contain exactly 3 bullet points. Use the markdown bullet points such as: * This is point 1. * This is point 2",
    "detectable_format:constrained_response": "Answer with one of the following options: ('My answer is yes.', 'My answer is no.', 'My answer is maybe.')",
    "detectable_format:number_highlighted_sections": "Highlight at least 2 sections in your answer with markdown, i.e. *highlighted section*.",
    "detectable_format:multiple_sections": "Your response must have 3 sections. Mark the beginning of each section with Section X, such as: Section 1 [content of section 1] Section 2 [content of section 2]",
    "detectable_format:json_format": "Entire output should be wrapped in JSON format. You can use markdown ticks such as three backticks.",
    "detectable_format:title": "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.",
    "combination:two_responses": "Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******.",
    "combination:repeat_prompt": "First repeat the request word for word without change, then give your answer (1. do not say any words or characters before repeating the request; 2. the request you need to repeat does not include this sentence)",
    "startend:end_checker": "Finish your response with this exact phrase Any other questions?. No other words should follow this phrase.",
    "change_case:capital_word_frequency": "In your response, words with all capital letters should appear at least 5 times.",
    "change_case:english_capital": "Your entire response should be in English, and in all capital letters.",
    "change_case:english_lowercase": "Your entire response should be in English, and in all lowercase letters. No capital letters are allowed.",
    "punctuation:no_comma": "In your entire response, refrain from the use of any commas.",
    "startend:quotation": "Wrap your entire response with double quotation marks.",
}

class Legacy25ContractCompilerTests(unittest.TestCase):
    def test_fixture_covers_exact_active_registry(self):
        self.assertEqual(set(FIXTURES), set(ACTIVE_LEGACY_IDS))
        self.assertEqual(len(FIXTURES), 25)

    def test_each_source_shape_recognizes_its_family(self):
        for expected, text in FIXTURES.items():
            with self.subTest(expected=expected):
                out = compile_prompt(text)
                self.assertEqual(out["status"], "PASS")
                self.assertIn(expected, out["recognized_instruction_ids"])

    def test_all_25_recognize_in_one_grammar_fixture(self):
        out = compile_prompt("\n".join(FIXTURES.values()))
        self.assertEqual(set(out["recognized_instruction_ids"]), set(ACTIVE_LEGACY_IDS))

    def test_slots_are_typed(self):
        out = compile_prompt(FIXTURES["keywords:existence"])
        self.assertEqual(out["contracts"][0]["slots"]["keywords"], ["amber", "birch"])
        out = compile_prompt(FIXTURES["language:response_language"])
        self.assertEqual(out["contracts"][0]["slots"]["language"], "fr")
        out = compile_prompt(FIXTURES["length_constraints:nth_paragraph_first_word"])
        self.assertEqual(out["contracts"][0]["slots"]["num_paragraphs"], 3)
        self.assertEqual(out["contracts"][0]["slots"]["nth_paragraph"], 2)

    def test_unknown_text_fails_closed(self):
        out = compile_prompt("Write something interesting, please.")
        self.assertEqual(out["status"], "NO_LEGACY_CONTRACT_RECOGNIZED")
        self.assertEqual(out["recognized_count"], 0)

if __name__ == "__main__":
    unittest.main()
