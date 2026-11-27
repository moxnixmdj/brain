import unittest

from canonical.runtime.instruction_constraint_compiler_v2 import (
    compile_program,
    synthesize_formal_v2,
    validate_program,
)

class InstructionConstraintCompilerV2Tests(unittest.TestCase):
    def assert_passes(self, instruction):
        out=synthesize_formal_v2(instruction)
        self.assertEqual(out["status"],"FORMAL_CONSTRAINTS_SATISFIED",out)
        self.assertIsInstance(out["response"],str)
        ok,errors=validate_program(out["response"],compile_program(instruction))
        self.assertTrue(ok,errors)
        self.assertEqual(out["model_dependency_count"],0)
        return out

    def test_v1_exact_route_preserved(self):
        out=self.assert_passes('Reply with exactly "ALPHA".')
        self.assertEqual(out["response"],"ALPHA")
        self.assertFalse(out["semantic_seed_required"])

    def test_no_whitespace(self):
        self.assert_passes("The output should not contain any whitespace.")

    def test_title_case_plus_exact_word_count(self):
        self.assert_passes("Write the entire response in title case. Use exactly 2 words.")

    def test_newline_words(self):
        self.assert_passes("Write each word on a new line.")

    def test_sentence_ratio(self):
        self.assert_passes("Maintain a 2:1 ratio of declarative to interrogative sentences.")

    def test_sentence_balance(self):
        self.assert_passes(
            "Ensure that the ratio of sentence types (declarative, interrogative, exclamatory) is balanced."
        )

    def test_punctuation_cover(self):
        self.assert_passes(
            "Use every standard punctuation mark at least once, including semicolons, colons, and the interrobang (?!)."
        )

    def test_nested_delimiters(self):
        self.assert_passes("Nest parentheses and brackets at least 5 levels deep.")

    def test_repeat_limit(self):
        self.assert_passes("Do not repeat any word more than 1 times.")

    def test_min_pronouns(self):
        self.assert_passes("Include at least 4 personal pronouns.")

    def test_options(self):
        out=self.assert_passes(
            "Answer with one of the following options: yes/no/maybe. Do not give any explanation."
        )
        self.assertIn(out["response"],("yes","no","maybe"))

    def test_output_template(self):
        self.assert_passes(
            "Use this exact template for your response: My Answer: [answer] "
            "My Conclusion: [conclusion] Future Outlook: [outlook]"
        )

    def test_sub_bullets(self):
        self.assert_passes(
            "Your response must include bullet points denoted by * and at least one sub-bullet point denoted by - for each bullet point."
        )

    def test_sentence_then_bullets(self):
        self.assert_passes(
            "Your answer must contain at least two sentences ending in a period followed by at least two newline-separated bullet points."
        )

    def test_italic_thesis(self):
        self.assert_passes(
            "Each section must begin with a thesis statement in italics, use HTML to indicate the italics."
        )

    def test_paragraph_cycle(self):
        self.assert_passes(
            "Write at least two paragraphs, where each paragraph ends with exactly the same word it started with."
        )

    def test_sentence_increment(self):
        self.assert_passes("Each sentence must contain exactly 2 more words than the previous one.")

    def test_no_adjacent_initial(self):
        self.assert_passes("No two consecutive words can share the same first letter.")

    def test_keyword_sentence(self):
        self.assert_passes('Include keyword "orbit" in the 3-th sentence.')

    def test_keyword_position(self):
        self.assert_passes(
            "Include keyword 'orbit' in the 2-th sentence, as the 3-th word of that sentence."
        )

    def test_repeated_position_word(self):
        self.assert_passes(
            "The second word in your response and the second to last word in your response should be the word 'orbit'."
        )

    def test_joint_ratio_and_no_same_initial(self):
        self.assert_passes(
            "Maintain a 2:1 ratio of declarative to interrogative sentences. "
            "No two consecutive words can share the same first letter."
        )

    def test_joint_template_and_title_case(self):
        self.assert_passes(
            "Use this exact template for your response: My Answer: [answer] "
            "My Conclusion: [conclusion] Future Outlook: [outlook]. "
            "Write the entire response in title case."
        )

    def test_conflicting_whitespace_fails_closed(self):
        out=synthesize_formal_v2(
            "The output should not contain any whitespace. Write each word on a new line."
        )
        self.assertEqual(out["status"],"BLOCKED")
        self.assertIsNone(out["response"])

    def test_conflicting_sentence_ratios_fail_closed(self):
        out=synthesize_formal_v2(
            "Maintain a 2:1 ratio of declarative to interrogative sentences. "
            "Ensure that the ratio of sentence types (declarative, interrogative, exclamatory) is balanced."
        )
        self.assertEqual(out["status"],"BLOCKED")

    def test_no_formal_constraint_does_not_fake_semantics(self):
        out=synthesize_formal_v2("Explain photosynthesis accurately.")
        self.assertEqual(out["status"],"BLOCKED")
        self.assertTrue(out["semantic_seed_required"])

    def test_structural_pass_keeps_semantic_nonclaim(self):
        out=self.assert_passes("Use exactly 4 words.")
        self.assertTrue(out["semantic_seed_required"])
        self.assertIn("DOES_NOT_BY_ITSELF_PROVE_SEMANTIC_TASK_QUALITY",out["hard_nonclaim"])

if __name__=="__main__":
    unittest.main(verbosity=2)
