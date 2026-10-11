import unittest
from canonical.runtime.hle_native_retrieval_query_planner_v1 import plan_queries

class QueryPlannerV1Tests(unittest.TestCase):
    def queries(self,q):
        x=plan_queries(task_id="x",question=q)
        self.assertFalse(x["gold_accessed"])
        self.assertEqual(x["external_model_calls"],0)
        self.assertEqual(x["model_dependency_count"],0)
        self.assertTrue(all(v["full_question_verbatim_used"] is False for v in x["views"]))
        return [v["query"] for v in x["views"]]

    def test_capital_subject_seed(self):
        self.assertTrue(any(q=="Dominican Republic" for q in self.queries("What is the capital of the Dominican Republic?")))
    def test_company_seed(self):
        self.assertTrue(any("Aldi" in q for q in self.queries("What is the country of origin of the supermarket chain Aldi?")))
    def test_person_seed(self):
        self.assertTrue(any("William the Conqueror" in q for q in self.queries("William the Conqueror came from which French region?")))
    def test_quoted_work_seeds(self):
        q=self.queries("Which composer wrote the operas 'Lohengrin' and 'Tannhauser'?")
        self.assertIn("Lohengrin",q);self.assertIn("Tannhauser",q)
    def test_song_seed(self):
        self.assertIn("When You Wish Upon a Star",self.queries("In which Walt Disney film does the song 'When You Wish Upon a Star' appear?"))
    def test_ordered_core_preserves_order(self):
        q=self.queries("According to Newton's Second Law, what does mass times acceleration equal?")
        self.assertTrue(any("newton" in x and "mass" in x and "acceleration" in x for x in q))

if __name__=="__main__":unittest.main(verbosity=2)
