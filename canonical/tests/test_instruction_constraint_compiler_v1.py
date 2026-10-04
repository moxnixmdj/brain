import unittest

from canonical.runtime.instruction_constraint_compiler_v1 import (
    compile_constraints,
    synthesize_formal_only,
    validate_response,
)


class InstructionConstraintCompilerTests(unittest.TestCase):
    def test_exact_response(self):
        out = synthesize_formal_only('Reply with exactly "ALPHA".')
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["response"], "ALPHA")

    def test_exact_response_plus_case(self):
        out = synthesize_formal_only('Reply with exactly "ALPHA". Use lowercase only.')
        self.assertEqual(out["status"], "BLOCKED")

    def test_word_range_parses(self):
        c = compile_constraints("The response must contain between 5 and 7 words.")
        self.assertEqual((c.min_words, c.max_words), (5, 7))

    def test_structural_synthesis_is_not_semantic_claim(self):
        out = synthesize_formal_only("Use at least 5 unique words in the response.")
        self.assertEqual(out["status"], "FORMAL_CONSTRAINTS_SATISFIED_SEMANTIC_SEED_STILL_REQUIRED")
        self.assertTrue(out["semantic_seed_required"])
        ok, _ = validate_response(out["response"], compile_constraints("Use at least 5 unique words in the response."))
        self.assertTrue(ok)

    def test_forbidden_literal_not_misparsed_as_required(self):
        c = compile_constraints('Do not include the word "omega".')
        self.assertEqual(c.required_literals, ())
        self.assertEqual(c.forbidden_literals, ("omega",))

    def test_exact_numbers_inside_word_budget(self):
        out = synthesize_formal_only("Use exactly 5 words and include exactly 2 numbers.")
        self.assertEqual(out["status"], "FORMAL_CONSTRAINTS_SATISFIED_SEMANTIC_SEED_STILL_REQUIRED")
        self.assertEqual(len(out["response"].split()), 5)

    def test_unquoted_exact_response_atom(self):
        cases = [
            ("Reply with exactly SYNTHETIC_OK.", "SYNTHETIC_OK"),
            ("Answer exactly BETA_7.", "BETA_7"),
            ("Output exactly TOKEN-3.", "TOKEN-3"),
            ("Say exactly ns:value.", "ns:value"),
        ]
        for instruction, expected in cases:
            with self.subTest(instruction=instruction):
                out = synthesize_formal_only(instruction)
                self.assertEqual(out["status"], "PASS")
                self.assertEqual(out["response"], expected)
                self.assertFalse(out["semantic_seed_required"])

    def test_unquoted_multiword_exact_response_fails_closed(self):
        out = synthesize_formal_only("Reply with exactly two words.")
        self.assertNotEqual(out["status"], "PASS")

    def test_unquoted_atom_with_extra_instruction_does_not_overmatch(self):
        out = synthesize_formal_only("Reply with exactly ALPHA. Then explain why.")
        self.assertNotEqual(out["status"], "PASS")

    def test_no_constraint_route_blocks(self):
        out = synthesize_formal_only("Explain photosynthesis.")
        self.assertEqual(out["status"], "BLOCKED")
        self.assertTrue(out["semantic_seed_required"])


if __name__ == "__main__":
    unittest.main()
