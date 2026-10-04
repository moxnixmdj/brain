import unittest

from canonical.runtime.livebench_if_char_trigram_overlap_solver_v1 import (
    char_trigrams,
    solve,
)


def exact_score(response: str, reference: str) -> float:
    a, b = char_trigrams(response), char_trigrams(reference)
    return 100.0 * len(a & b) / len(a)


class CharTrigramOverlapSolverTests(unittest.TestCase):
    def assert_passes(self, prompt: str, reference: str, target: float):
        out = solve(prompt)
        self.assertTrue(out["status"].startswith("PASS__"), out)
        self.assertFalse(any(ch.isspace() for ch in out["response"]))
        score = exact_score(out["response"], reference)
        self.assertGreaterEqual(score, target - 2.0)
        self.assertLessEqual(score, target + 2.0)
        self.assertAlmostEqual(score, out["guaranteed_overlap_percent"], places=10)
        return out

    def test_whitespace_ambiguity_is_irrelevant(self):
        reference = "Use induction to prove this claim.\nConsider a simple graph."
        prompt = (
            "Use induction to prove this claim. Consider a simple graph. "
            "Maintain a trigram overlap of 72% (±2%) with the provided reference text."
        )
        self.assert_passes(prompt, reference, 72)

    def test_high_overlap_band(self):
        reference = "Self-Determination Theory (SDT):\n- Autonomy: flexible work."
        prompt = (
            "Self-Determination Theory (SDT): - Autonomy: flexible work. "
            "Maintain a trigram overlap of 93% (±2%) with the provided reference text."
        )
        self.assert_passes(prompt, reference, 93)

    def test_keyword_30th_sentence_compound(self):
        reference = (
            "Write a believable sci fi history about a parasite that could loosely "
            "retain the form, memories and personality of its hosts."
        )
        prompt = (
            "Maintain a trigram overlap of 23% (±2%) with the provided reference text. "
            'The response must include keyword "horary" in the 30-th sentence. '
            + reference
        )
        out = self.assert_passes(prompt, reference, 23)
        sentences = [x for x in out["response"].split(".") if x]
        self.assertGreaterEqual(len(sentences), 30)
        self.assertIn("horary", sentences[29].lower())

    def test_consonant_compound(self):
        reference = (
            "What are the pros and cons of defining model in machine learning "
            "to be just weights and biases?"
        )
        prompt = (
            "Ensure each word in your response has at least one consonant cluster "
            "(two or more consonants together). "
            "Maintain a trigram overlap of 11% (±2%) with the provided reference text. "
            + reference
        )
        self.assert_passes(prompt, reference, 11)

    def test_absent_overlap_description_fails_closed(self):
        out = solve("Explain photosynthesis.")
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIsNone(out["response"])


if __name__ == "__main__":
    unittest.main()
