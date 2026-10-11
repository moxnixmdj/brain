import unittest
from canonical.runtime.hle_native_research_solver_v5 import propose

class ResearchSolverV5Tests(unittest.TestCase):
    def test_capital_typed(self):
        def rich(q,limit=8):
            return [{"title":"Fictionland","url":"https://example.org/x","snippet":"The capital of Fictionland is Nova City.","rank":1}]
        o=propose(task_id="a",question="What is the capital of Fictionland?",
            rich_search_fn=rich,wiki_search_fn=lambda *a,**k:[],wiki_extracts_fn=lambda *a,**k:{},
            exact_retrieval_proposer=lambda **k:{"candidate_answer":None,"external_model_calls":0,"model_dependency_count":0})
        self.assertEqual(o["candidate_answer"],"Nova City")
        self.assertEqual(o["external_model_calls"],0)

    def test_cross_view_title(self):
        def ws(q,limit=8):
            return [{"pageid":7,"title":"Measure for Example","snippet":"A play by William Example set in Vienna.","rank":2}]
        o=propose(task_id="b",question="Which of William Example's plays is set in Vienna?",
            rich_search_fn=lambda *a,**k:[],wiki_search_fn=ws,
            wiki_extracts_fn=lambda ids:{7:"Measure for Example is a play by William Example."},
            exact_retrieval_proposer=lambda **k:{"candidate_answer":None,"external_model_calls":0,"model_dependency_count":0})
        self.assertEqual(o["candidate_answer"],"Measure for Example")
        self.assertGreaterEqual(o["supporting_view_count"],2)

    def test_clue_title_rejected(self):
        def ws(q,limit=8):
            return [{"pageid":8,"title":"William Example","snippet":"William Example wrote many plays.","rank":1}]
        o=propose(task_id="c",question="Which of William Example's plays is set in Vienna?",
            rich_search_fn=lambda *a,**k:[],wiki_search_fn=ws,
            wiki_extracts_fn=lambda ids:{8:"William Example wrote many plays."},
            exact_retrieval_proposer=lambda **k:{"candidate_answer":None,"external_model_calls":0,"model_dependency_count":0})
        self.assertIsNone(o["candidate_answer"])

    def test_exact_retrieval_only_agreement(self):
        def ws(q,limit=8):
            return [{"pageid":9,"title":"Nova City","snippet":"Fictionland topic.","rank":4}]
        o=propose(task_id="d",question="What is the capital of Fictionland?",
            rich_search_fn=lambda *a,**k:[],wiki_search_fn=ws,wiki_extracts_fn=lambda ids:{9:"Fictionland topic."},
            exact_retrieval_proposer=lambda **k:{"status":"CANDIDATE_GENERATED","candidate_answer":"Nova City",
                "external_model_calls":0,"model_dependency_count":0,"gold_accessed":False})
        self.assertEqual(o["candidate_answer"],"Nova City")
        self.assertIn("EXACT_RETRIEVAL",o["selection_reason"])

    def test_external_exact_candidate_rejected(self):
        def ws(q,limit=8):
            return [{"pageid":9,"title":"Nova City","snippet":"Fictionland topic.","rank":4}]
        o=propose(task_id="e",question="What is the capital of Fictionland?",
            rich_search_fn=lambda *a,**k:[],wiki_search_fn=ws,wiki_extracts_fn=lambda ids:{9:"Fictionland topic."},
            exact_retrieval_proposer=lambda **k:{"status":"CANDIDATE_GENERATED","candidate_answer":"Nova City",
                "external_model_calls":1,"model_dependency_count":1})
        self.assertIsNone(o["candidate_answer"])

if __name__=="__main__":unittest.main(verbosity=2)
