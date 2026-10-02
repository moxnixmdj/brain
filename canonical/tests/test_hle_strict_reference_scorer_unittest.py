import unittest
from canonical.runtime.hle_strict_reference_scorer import extract_declared_answer,score_predictions,strict_reference_verdict

class HLEStrictLowerBoundTests(unittest.TestCase):
    def test_exact_reference_passes(self):
        self.assertTrue(strict_reference_verdict("Explanation: x\nAnswer: canonical\nConfidence: 77%","canonical").correct)
    def test_equivalent_but_nonidentical_is_conservatively_rejected(self):
        self.assertFalse(strict_reference_verdict("Answer: 0.5","1/2").correct)
    def test_multiple_answer_lines_fail_closed(self):
        answer,reason=extract_declared_answer("Answer: A\nAnswer: B")
        self.assertIsNone(answer); self.assertEqual(reason,"ANSWER_LINE_COUNT_2")
    def test_missing_prediction_is_wrong(self):
        r=score_predictions({},[{"id":"q1","answer":"A"}])
        self.assertEqual(r["accuracy_percent"],0.0)
    def test_never_claims_official_equivalence(self):
        r=score_predictions({"q1":"Answer: A"},[{"id":"q1","answer":"A"}])
        self.assertFalse(r["official_score_equivalence_claimed"])

if __name__=="__main__":
    unittest.main()
