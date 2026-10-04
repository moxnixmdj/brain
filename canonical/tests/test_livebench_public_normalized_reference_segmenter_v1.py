import unittest

from canonical.runtime.livebench_public_normalized_reference_segmenter_v1 import (
    normalize_ws,
    recover_normalized_reference,
)


class PublicNormalizedReferenceSegmenterTests(unittest.TestCase):
    def assert_recovers(self, prompt, expected, percentage):
        out = recover_normalized_reference(prompt)
        self.assertEqual(
            out["status"], "PASS__PUBLIC_GRAMMAR_NORMALIZED_REFERENCE_RECOVERED"
        )
        self.assertEqual(out["normalized_reference"], normalize_ws(expected))
        self.assertEqual(out["percentage"], percentage)
        self.assertEqual(out["model_dependency_count"], 0)
        self.assertEqual(out["terminal_case_dependency_count"], 0)

    def test_suffix_overlap_clause(self):
        self.assert_recovers(
            "Explain alpha beta. Maintain a trigram overlap of 72% (±2%) "
            "with the provided reference text.",
            "Explain alpha beta.",
            72.0,
        )

    def test_prefix_overlap_clause(self):
        self.assert_recovers(
            "Maintain a trigram overlap of 59% (±2%) with the provided reference text. "
            "Write a short scene.",
            "Write a short scene.",
            59.0,
        )

    def test_keyword_sentence_coconstraint_is_erased(self):
        self.assert_recovers(
            "Question body. Maintain a trigram overlap of 13% (±2%) with the provided "
            "reference text. The response must include keyword giraffe in the 7-th sentence.",
            "Question body.",
            13.0,
        )

    def test_consonant_cluster_coconstraint_is_erased(self):
        self.assert_recovers(
            "Question body. Ensure each word in your response has at least one consonant "
            "cluster (two or more consonants together). Maintain a trigram overlap of 54% "
            "(±2%) with the provided reference text.",
            "Question body.",
            54.0,
        )

    def test_public_whitespace_and_zero_width_noise_normalizes(self):
        self.assert_recovers(
            "alpha\n beta. \u200bMaintain a trigram overlap of 74% (±2%) with the "
            "provided reference text.",
            "alpha beta.",
            74.0,
        )

    def test_missing_overlap_clause_fails_closed(self):
        out = recover_normalized_reference("Question body only.")
        self.assertEqual(out["status"], "BLOCKED")
        self.assertIsNone(out["normalized_reference"])

    def test_multiple_overlap_clauses_fail_closed(self):
        clause = "Maintain a trigram overlap of 10% (±2%) with the provided reference text."
        out = recover_normalized_reference(f"Question. {clause} {clause}")
        self.assertEqual(out["status"], "BLOCKED")

    def test_no_base_text_fails_closed(self):
        out = recover_normalized_reference(
            "Maintain a trigram overlap of 10% (±2%) with the provided reference text."
        )
        self.assertEqual(out["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
