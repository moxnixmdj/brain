import unittest
from canonical.runtime.hle_native_research_solver_v4 import propose

class NativeResearchV4Tests(unittest.TestCase):
    def test_relation_answer_from_search_snippet(self):
        def rich(q,limit=8):
            return [{"title":"Fictionland","url":"https://example.org/a",
                     "snippet":"Fictionland is a country. The capital of Fictionland is Nova City.","rank":1}]
        o=propose(task_id="a",question="What city is the capital of Fictionland?",
                  rich_search_fn=rich,wiki_search_fn=lambda *a,**k:[],
                  wiki_extracts_fn=lambda *a,**k:{})
        self.assertEqual(o["candidate_answer"],"Nova City")
        self.assertEqual(o["external_model_calls"],0)
        self.assertEqual(o["model_dependency_count"],0)

    def test_cross_query_wikipedia_title(self):
        def rich(q,limit=8): return []
        def ws(q,limit=6):
            return [{"pageid":7,"title":"Measure for Example",
                     "snippet":"A play by William Example set in Vienna.","rank":1}]
        def ex(ids):
            return {7:"Measure for Example is a play by William Example. The play is set in Vienna."}
        o=propose(task_id="b",question="Which play by William Example is set in Vienna?",
                  rich_search_fn=rich,wiki_search_fn=ws,wiki_extracts_fn=ex)
        self.assertEqual(o["candidate_answer"],"Measure for Example")
        self.assertGreaterEqual(o["supporting_view_count"],2)

    def test_clue_entity_not_promoted_as_title(self):
        def rich(q,limit=8): return []
        def ws(q,limit=6):
            return [{"pageid":8,"title":"William Example",
                     "snippet":"William Example wrote many plays.","rank":1}]
        o=propose(task_id="c",question="Which play by William Example is set in Vienna?",
                  rich_search_fn=rich,wiki_search_fn=ws,wiki_extracts_fn=lambda ids:{8:"William Example wrote many plays."})
        self.assertIsNone(o["candidate_answer"])

    def test_negative_fails_closed(self):
        o=propose(task_id="d",question="Which of these is not a capital?",
                  rich_search_fn=lambda *a,**k:[],wiki_search_fn=lambda *a,**k:[],
                  wiki_extracts_fn=lambda *a,**k:{})
        self.assertIn("NEGATIVE_POLARITY",o["status"])

    def test_image_defer(self):
        o=propose(task_id="e",question="Who is shown?",has_nonempty_image_payload=True,
                  rich_search_fn=lambda *a,**k:[],wiki_search_fn=lambda *a,**k:[],
                  wiki_extracts_fn=lambda *a,**k:{})
        self.assertIn("IMAGE_SEMANTICS",o["status"])
        self.assertEqual(o["external_model_calls"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
