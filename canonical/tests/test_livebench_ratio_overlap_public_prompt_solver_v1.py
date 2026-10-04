import unittest

from canonical.runtime.livebench_ratio_overlap_public_prompt_solver_v1 import (
    RatioOverlapPromptError,
    construct_public_ratio_overlap_response,
    parse_public_ratio_overlap_prompt,
)


class PublicPromptRatioOverlapSolverTests(unittest.TestCase):
    def test_left_edge_parse_and_100_percent_construct(self):
        prompt = (
            "Maintain a trigram overlap of 100% (±2%) with the provided reference text. "
            "abcdefghijklmno"
        )
        parsed = parse_public_ratio_overlap_prompt(prompt)
        self.assertEqual(parsed["constraint_block_side"], "LEFT")
        self.assertEqual(parsed["target_percent"], 100.0)
        self.assertEqual(parsed["reference_normalized"], "abcdefghijklmno")

        out = construct_public_ratio_overlap_response(prompt)
        self.assertEqual(out["status"], "PASS", out)
        self.assertLessEqual(out["absolute_target_error_percent"], 2.0)
        self.assertTrue(out["candidate_whitespace_free"])
        self.assertFalse(out["hidden_metadata_required"])
        self.assertFalse(out["raw_reference_required"])

    def test_right_edge_parse(self):
        prompt = (
            "abcdefghijklmno "
            "Maintain a trigram overlap of 100% (±2%) with the provided reference text."
        )
        parsed = parse_public_ratio_overlap_prompt(prompt)
        self.assertEqual(parsed["constraint_block_side"], "RIGHT")
        self.assertEqual(parsed["reference_normalized"], "abcdefghijklmno")

    def test_supported_conjunction_metadata_is_public_prompt_derived(self):
        prompt = (
            'The response must include keyword "delta" in the 2-nd sentence. '
            "Maintain a trigram overlap of 50% (±2%) with the provided reference text. "
            "abcdefghijklmnopqrstuv"
        )
        parsed = parse_public_ratio_overlap_prompt(prompt)
        self.assertEqual(parsed["keyword"], "delta")
        self.assertEqual(parsed["keyword_sentence"], 2)
        self.assertFalse(parsed["consonant_cluster_required"])

    def test_unsupported_prompt_fails_closed(self):
        with self.assertRaises(RatioOverlapPromptError):
            parse_public_ratio_overlap_prompt("write something vaguely similar")


if __name__ == "__main__":
    unittest.main()
