import unittest

from canonical.runtime.livebench_stopword_zero_witness_v1 import (
    StopwordWitnessError,
    parse_percentage,
    synthesize,
)


class LiveBenchStopwordZeroWitnessTests(unittest.TestCase):
    def test_parse_exact_public_description(self):
        text = "Ensure that stop words constitute no more than 37% of the total words in your response."
        self.assertEqual(parse_percentage(text), 37.0)

    def test_zero_ceiling_is_accepted(self):
        text = "Ensure that stop words constitute no more than 0% of the total words in your response."
        out = synthesize(text)
        self.assertEqual(out.percentage_ceiling, 0.0)
        self.assertGreater(out.token_count, 0)

    def test_witness_uses_only_word_tokens(self):
        text = "Ensure that stop words constitute no more than 100% of the total words in your response."
        out = synthesize(text, token_count=8)
        self.assertEqual(out.response.split(), [f"qzxv{i}" for i in range(8)])

    def test_unrecognized_description_fails_closed(self):
        with self.assertRaises(StopwordWitnessError):
            synthesize("Talk about stop words.")

    def test_out_of_range_percentage_fails_closed(self):
        with self.assertRaises(StopwordWitnessError):
            synthesize("Ensure that stop words constitute no more than 101% of the total words in your response.")


if __name__ == "__main__":
    unittest.main()
