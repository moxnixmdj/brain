import unittest
from canonical.runtime.hle_native_retrieval_query_planner_v2 import plan_queries

class QueryPlannerV2Tests(unittest.TestCase):
    def q(self,text,max_views=8):
        out=plan_queries(task_id="synthetic",question=text,max_views=max_views)
        self.assertFalse(out["gold_accessed"])
        self.assertEqual(out["external_model_calls"],0)
        self.assertEqual(out["model_dependency_count"],0)
        self.assertFalse(any(v["full_question_verbatim_used"] for v in out["views"]))
        return out,[v["query"] for v in out["views"]]

    def test_interrogative_punctuation_is_normalized(self):
        out,qs=self.q("Which. Martian city is named after the explorer Ada Example?")
        self.assertTrue(any("martian" in q.casefold() and "city" in q.casefold() for q in qs))
        self.assertFalse(any("which." in q.casefold() for q in qs))

    def test_ordinal_is_preserved(self):
        _,qs=self.q("Which president was the first to be assassinated in Exampleland?")
        self.assertTrue(any("first" in q.casefold() and "president" in q.casefold() for q in qs))

    def test_multiword_subject_gets_slot_relation_query(self):
        _,qs=self.q("Business magnate Alex Example dropped out of which university?")
        self.assertTrue(any("Alex Example" in q and "university" in q.casefold() for q in qs),qs)

    def test_pairwise_relation_query(self):
        _,qs=self.q("What relation was Napoleon Example to Joseph Example?")
        self.assertTrue(any("Napoleon Example" in q and "Joseph Example" in q and ("relation" in q.casefold() or "relationship" in q.casefold()) for q in qs),qs)

    def test_definition_query(self):
        _,qs=self.q("What is the term for a triangle with two equal sides?")
        self.assertTrue(any("triangle" in q.casefold() and ("term" in q.casefold() or "definition" in q.casefold()) for q in qs),qs)

    def test_v1_anchor_survives(self):
        _,qs=self.q("Which composer wrote the operas 'Lohengrin' and 'Tannhauser'?")
        self.assertIn("Lohengrin",qs)

    def test_view_bound_and_dedupe(self):
        out,qs=self.q("What is the country of origin of the supermarket chain Aldi?",max_views=5)
        self.assertLessEqual(len(qs),5)
        self.assertEqual(len(qs),len({q.casefold() for q in qs}))
        self.assertEqual(out["view_count"],len(qs))

if __name__=="__main__":
    unittest.main(verbosity=2)
