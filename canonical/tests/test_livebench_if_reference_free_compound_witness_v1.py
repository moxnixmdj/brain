import unittest

from canonical.runtime import livebench_if_reference_free_compound_witness_v1 as witness


class CompoundWitnessTests(unittest.TestCase):
    def test_exact_no_whitespace_classifier(self):
        base = "alpha beta gamma"
        out = witness.certify_no_whitespace("alpha", base)
        self.assertEqual(out["status"], "PASS_UNDER_CONTRACT")
        self.assertEqual(out["numerator"], out["denominator"])
        self.assertEqual(out["certified_percent"], 100.0)

    def test_public_keyword_form_seventh_sentence(self):
        prompt = (
            "Is it easier to urbanize a jungle or to urbanize a desert? "
            "Maintain a trigram overlap of 13% (±2%) with the provided reference text. "
            "The response must include keyword giraffe in the 7-th sentence."
        )
        out = witness.construct_from_prompt(prompt)
        self.assertEqual(out["status"], "PASS_UNDER_CONTRACT")
        self.assertTrue(11 <= out["certified_percent"] <= 15)
        self.assertTrue(
            witness._keyword_sentence_ok(out["response"], "giraffe", 7)
        )
        self.assertFalse(any(ch.isspace() for ch in out["response"]))

    def test_public_keyword_form_thirtieth_sentence_set_denominator_is_small(self):
        prompt = (
            "Maintain a trigram overlap of 23% (±2%) with the provided reference text. "
            "The response must include keyword horary in the 30-th sentence. "
            "Write a believable sci fi history about a parasite that could loosely retain "
            "the form, memories and personality of its' hosts, eventually being destroyed."
        )
        out = witness.construct_from_prompt(prompt)
        self.assertEqual(out["status"], "PASS_UNDER_CONTRACT")
        self.assertTrue(21 <= out["certified_percent"] <= 25)
        self.assertTrue(
            witness._keyword_sentence_ok(out["response"], "horary", 30)
        )
        self.assertLess(out["denominator"], 25)

    def test_public_consonant_form(self):
        prompt = (
            "Ensure each word in your response has at least one consonant cluster "
            "(two or more consonants together). Maintain a trigram overlap of 11% (±2%) "
            'with the provided reference text. What are the pros and cons of defining '
            '"model" in machine learning to be just weights and biases?'
        )
        out = witness.construct_from_prompt(prompt)
        self.assertEqual(out["status"], "PASS_UNDER_CONTRACT")
        self.assertTrue(9 <= out["certified_percent"] <= 13)
        self.assertTrue(witness._consonant_cluster_ok(out["response"]))

    def test_unknown_or_missing_ratio_fails_closed(self):
        out = witness.construct_from_prompt("Explain photosynthesis clearly.")
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertFalse(out["reference_text_read"])


if __name__ == "__main__":
    unittest.main()
