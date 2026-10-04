import unittest
from canonical.runtime.livebench_ratio_overlap_prompt_segmenter_v1 import recover, SegmenterError

class LiveBenchRatioOverlapPromptSegmenterV1Tests(unittest.TestCase):
    def test_ratio_suffix(self):
        prompt="Base request text. Maintain a trigram overlap of 72% (±2%) with the provided reference text."
        out=recover(prompt)
        self.assertEqual(out["normalized_reference"],"Base request text.")
        self.assertEqual(out["percentage"],72.0)

    def test_ratio_prefix_and_sentence_keyword_ordinal(self):
        prompt=(
            "Maintain a trigram overlap of 23% (±2%) with the provided reference text. "
            "The response must include keyword horary in the 30-th sentence. "
            "Base request."
        )
        out=recover(prompt)
        self.assertEqual(out["normalized_reference"],"Base request.")
        self.assertEqual(out["percentage"],23.0)

    def test_middle_and_rd_ordinal(self):
        prompt=(
            "Base request. Maintain a trigram overlap of 24% (±2%) with the provided reference text. "
            "The response must include keyword metricism in the 3-rd sentence."
        )
        self.assertEqual(recover(prompt)["normalized_reference"],"Base request.")

    def test_zero_width_outer_delimiter(self):
        prompt="Base request. \u200bMaintain a trigram overlap of 74% (±2%) with the provided reference text."
        self.assertEqual(recover(prompt)["normalized_reference"],"Base request.")

    def test_consonant_cluster_co_constraint(self):
        prompt=(
            "Ensure each word in your response has at least one consonant cluster "
            "(two or more consonants together). "
            "Maintain a trigram overlap of 11% (±2%) with the provided reference text. "
            "Base request."
        )
        self.assertEqual(recover(prompt)["normalized_reference"],"Base request.")

    def test_fail_closed_without_ratio_instruction(self):
        with self.assertRaises(SegmenterError):
            recover("Base request only.")

if __name__=="__main__":
    unittest.main()
