import unittest
from canonical.runtime.livebench_public_parameter_derivability_audit_v1 import analyze

class PublicParameterAuditTests(unittest.TestCase):
    def test_overlap_raw_whitespace_loss_is_visible(self):
        rows=[{
            "prompt":"alpha beta Maintain a trigram overlap of 50% (±2%) with the provided reference text.",
            "instruction_id_list":["ratio:overlap"],
            "kwargs":[{"reference_text":"alpha\nbeta","percentage":50}],
        }]
        out=analyze(rows)
        self.assertEqual(out["ratio_overlap"]["instruction_rows"],1)
        self.assertEqual(out["ratio_overlap"]["raw_reference_visible"],0)
        self.assertEqual(out["ratio_overlap"]["normalized_reference_visible"],1)

    def test_repeat_span_score_relevant_slice_survives_whitespace(self):
        rows=[{
            "prompt":"alpha beta gamma delta Copy the span of words that lies between (and including) index 1 and 2, the indices are word indices, split by whitespace!",
            "instruction_id_list":["repeat:repeat_span"],
            "kwargs":[{"prompt_to_repeat":"alpha  beta\ngamma delta","n_start":1,"n_end":2}],
        }]
        out=analyze(rows)
        self.assertEqual(out["repeat_span"]["score_relevant_slice_equal"],1)

if __name__=="__main__":
    unittest.main()
