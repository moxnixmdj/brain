import unittest

from canonical.runtime.livebench_if_response_adapter import adapt_responses, validate_against_questions


class LiveBenchIFResponseAdapterTests(unittest.TestCase):
    def test_exact_livebench_shape(self):
        out=adapt_responses([
            {"question_id":7,"response":"answer seven"},
            {"question_id":9,"response":"answer nine"},
        ],model_id="brain")
        self.assertEqual(out["brain"][7]["choices"][0]["turns"][0],"answer seven")
        self.assertEqual(out["brain"][9]["question_id"],9)

    def test_duplicate_question_id_fails_closed(self):
        with self.assertRaises(ValueError):
            adapt_responses([
                {"question_id":1,"response":"a"},
                {"question_id":1,"response":"b"},
            ])

    def test_non_string_response_fails_closed(self):
        with self.assertRaises(TypeError):
            adapt_responses([{"question_id":1,"response":None}])

    def test_id_only_preflight_passes(self):
        answers=adapt_responses([
            {"question_id":1,"response":"x"},
            {"question_id":2,"response":"y"},
        ])
        out=validate_against_questions(answers,[{"question_id":1},{"question_id":2}])
        self.assertEqual(out,{"status":"PASS","count":2,"content_inspected":False})

    def test_id_mismatch_fails_closed(self):
        answers=adapt_responses([{"question_id":1,"response":"x"}])
        out=validate_against_questions(answers,[{"question_id":1},{"question_id":2}])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["missing"],[2])


if __name__=="__main__":
    unittest.main(verbosity=2)
