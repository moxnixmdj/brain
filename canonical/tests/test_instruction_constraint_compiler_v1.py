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

    def test_no_constraint_route_blocks(self):
        out = synthesize_formal_only("Explain photosynthesis.")
        self.assertEqual(out["status"], "BLOCKED")
        self.assertTrue(out["semantic_seed_required"])


if __name__ == "__main__":
    unittest.main()
