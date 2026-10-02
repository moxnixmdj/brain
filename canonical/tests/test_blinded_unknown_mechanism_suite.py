import unittest
from canonical.runtime.blinded_unknown_mechanism_suite import (
    generate_hidden_case, public_case, run_queries, score_predictions, apply
)

class BlindedUnknownMechanismSuiteTests(unittest.TestCase):
    def test_deterministic_hidden_generation(self):
        a=generate_hidden_case("synthetic-test-seed",0)
        b=generate_hidden_case("synthetic-test-seed",0)
        self.assertEqual(a,b)

    def test_public_case_hides_mechanism_and_seed(self):
        c=generate_hidden_case("synthetic-test-seed",1)
        p=public_case(c)
        self.assertNotIn("kind",p)
        self.assertNotIn("params",p)
        self.assertNotIn("seed",p)

    def test_query_budget_and_duplicates_fail_closed(self):
        c=generate_hidden_case("synthetic-test-seed",2,query_budget=2)
        with self.assertRaises(ValueError):
            run_queries(c,[1,2,3])
        with self.assertRaises(ValueError):
            run_queries(c,[1,1])

    def test_exact_predictions_pass(self):
        c=generate_hidden_case("synthetic-test-seed",3)
        preds={x:apply(c,x) for x in c.eval_points}
        out=score_predictions(c,preds)
        self.assertTrue(out["exact_pass"])
        self.assertEqual(out["accuracy"],1.0)

    def test_wrong_or_incomplete_predictions_fail(self):
        c=generate_hidden_case("synthetic-test-seed",4)
        out=score_predictions(c,{})
        self.assertEqual(out["status"],"FAIL_CLOSED")
        preds={x:apply(c,x) for x in c.eval_points}
        first=next(iter(preds)); preds[first]=(preds[first]+1)%257
        out=score_predictions(c,preds)
        self.assertFalse(out["exact_pass"])
        self.assertLess(out["accuracy"],1.0)

if __name__=="__main__":
    unittest.main()
