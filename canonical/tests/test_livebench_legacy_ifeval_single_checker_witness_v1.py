import unittest

from canonical.runtime import livebench_legacy_ifeval_single_checker_witness_v1 as solver


class LegacySingleCheckerWitnessTests(unittest.TestCase):
    def test_keyword_existence(self):
        out = solver.solve("Include keywords ['alpha', 'beta'] in the response.")
        self.assertEqual(out["status"], "PASS_CANDIDATE_SINGLE_CHECKER_WITNESS")
        self.assertIn("alpha", out["response"])
        self.assertIn("beta", out["response"])

    def test_word_floor(self):
        out = solver.solve("Answer with at least 5 words.")
        self.assertEqual(len(out["response"].split()), 5)

    def test_paragraph_first_word(self):
        prompt = (
            "There should be 3 paragraphs. Paragraphs and only paragraphs are separated "
            "with each other by two new lines as if it was '\\n\\n' in python. "
            "Paragraph 2 must start with word cedar."
        )
        out = solver.solve(prompt)
        self.assertEqual(out["response"].split("\n\n")[1].split()[0], "cedar")

    def test_json(self):
        out = solver.solve("Entire output should be wrapped in JSON format. You can use markdown ticks such as ```.")
        self.assertEqual(out["response"], '{"answer":"safe"}')

    def test_two_constraints_fail_closed(self):
        out = solver.solve(
            "Include keywords ['alpha'] in the response. "
            "Wrap your entire response with double quotation marks."
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(len(out["recognized_instruction_ids"]), 2)

    def test_unknown_text_fails_closed(self):
        out = solver.solve("Explain a topic.")
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["recognized_instruction_ids"], [])


if __name__ == "__main__":
    unittest.main()
