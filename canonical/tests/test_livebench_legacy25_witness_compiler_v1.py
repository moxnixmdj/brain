import unittest

from canonical.runtime.livebench_legacy25_witness_compiler_v1 import parse_specs, synthesize


class Legacy25WitnessCompilerTests(unittest.TestCase):
    def assertPass(self, prompt):
        out = synthesize(prompt)
        self.assertEqual(out["status"], "PASS", out)
        self.assertTrue(out["response"].strip())
        return out

    def test_single_family_surface(self):
        prompts = [
            "Include keywords ['apple', 'river'] in the response.",
            "In your response, the word apple should appear at least 3 times.",
            "In your response, the word apple should appear less than 2 times.",
            "Do not include keywords ['apple', 'river'] in the response.",
            "In your response, the letter a should appear at least 4 times.",
            "In your response, the letter a should appear less than 1 times.",
            "Your response should contain at least 3 sentences.",
            "Your response should contain less than 3 sentences.",
            "There should be 3 paragraphs. Paragraphs are separated with the markdown divider: ***",
            "Answer with at least 6 words.",
            "Answer with less than 6 words.",
            "There should be 3 paragraphs. Paragraphs and only paragraphs are separated with each other by two new lines as if it was '\\n\\n' in python. Paragraph 2 must start with word zebra.",
            "The response must contain at least 3 placeholders represented by square brackets, such as [address].",
            "At the end of your response, please explicitly add a postscript starting with P.S.",
            "Your answer must contain exactly 3 bullet points. Use the markdown bullet points such as:",
            "Answer with one of the following options: ('My answer is yes.', 'My answer is no.', 'My answer is maybe.')",
            "Highlight at least 3 sections in your answer with markdown, i.e. *highlighted section*.",
            "Your response must have 3 sections. Mark the beginning of each section with Section X, such as:",
            "Entire output should be wrapped in JSON format. You can use markdown ticks such as ```.",
            "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.",
            "Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******.",
            "Finish your response with this exact phrase Any other questions?. No other words should follow this phrase.",
            "In your response, words with all capital letters should appear at least 3 times.",
            "In your response, words with all capital letters should appear less than 3 times.",
            "In your entire response, refrain from the use of any commas.",
            "Wrap your entire response with double quotation marks.",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assertPass(prompt)

    def test_compositions(self):
        prompts = [
            "Write anything. Include keywords ['apple','river'] in the response. Do not include keywords ['omega'] in the response. In your entire response, refrain from the use of any commas. Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.",
            "Write anything. Answer with at least 8 words. Finish your response with this exact phrase Any other questions?. No other words should follow this phrase. In your entire response, refrain from the use of any commas.",
            "Write anything. The response must contain at least 2 placeholders represented by square brackets, such as [address]. Your answer must contain exactly 2 bullet points. Use the markdown bullet points such as: In your entire response, refrain from the use of any commas.",
            "Write anything. Entire output should be wrapped in JSON format. You can use markdown ticks such as ```. Include keywords ['apple'] in the response. Do not include keywords ['omega'] in the response.",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assertPass(prompt)

    def test_repeat_prompt_visible_prefix(self):
        prompt = (
            "Write a funny haiku about moms.\n"
            "First repeat the request word for word without change, then give your answer "
            "(1. do not say any words or characters before repeating the request; "
            "2. the request you need to repeat does not include this sentence)"
        )
        out = self.assertPass(prompt)
        self.assertTrue(out["response"].lower().startswith("write a funny haiku about moms."))

    def test_langdetect_families_are_recognized_but_fail_closed(self):
        cases = [
            ("Your ENTIRE response should be in Spanish language, no other language is allowed.", "response_language"),
            ("Your entire response should be in English, and in all capital letters.", "english_capital"),
            ("Your entire response should be in English, and in all lowercase letters. No capital letters are allowed.", "english_lowercase"),
        ]
        for prompt, kind in cases:
            with self.subTest(kind=kind):
                self.assertEqual([s.kind for s in parse_specs(prompt)], [kind])
                out = synthesize(prompt)
                self.assertEqual(out["status"], "BLOCKED")
                self.assertEqual(out["reason"], "LANGDETECT_DEPENDENT_FAMILY_REQUIRES_EXACT_VALIDATOR")

    def test_forbidden_not_misparsed_as_required(self):
        prompt = "Do not include keywords ['apple', 'river'] in the response."
        self.assertEqual([s.kind for s in parse_specs(prompt)], ["forbidden_words"])


if __name__ == "__main__":
    unittest.main()
