import hashlib
import unittest
from canonical.runtime.hle_mcq_retrieval_vote_v1 import propose

Q="""Which synthetic material is associated with the fictional Aster process?
Answer Choices:
A. Cobalt glass
B. Silver moss
C. Neon clay
D. Amber ice
E. Quartz foam"""

def search_fixture(query,limit=10):
    q=query.lower()
    if "silver moss" in q:
        return {"status":"PASS","results":[{"url":"https://source-a.test/a"},{"url":"https://source-b.test/b"}]}
    if "cobalt glass" in q:
        return {"status":"PASS","results":[{"url":"https://source-c.test/c"}]}
    return {"status":"PASS","results":[{"url":"https://source-a.test/a"},{"url":"https://source-d.test/d"}]}

PAGES={
 "https://source-a.test/a":"The fictional Aster process is associated with silver moss in this synthetic corpus.",
 "https://source-b.test/b":"Independent synthetic documentation: silver moss is used in the Aster process.",
 "https://source-c.test/c":"Cobalt glass belongs to a different fictional process.",
 "https://source-d.test/d":"Aster is a fictional process used for testing retrieval.",
}

def fetch_fixture(url,max_bytes=600000):
    text=PAGES[url]
    return {"status":"PASS","url":url,"final_url":url,
            "body_sha256":hashlib.sha256(text.encode()).hexdigest(),
            "body_excerpt":text}

class RetrievalVoteTests(unittest.TestCase):
    def test_positive_retrieval_selects_supported_option(self):
        out=propose(task_id="s",question=Q,search_fn=search_fixture,fetch_fn=fetch_fixture)
        self.assertEqual(out["status"],"CANDIDATE_GENERATED")
        self.assertEqual(out["candidate_answer"],"B")
        self.assertFalse(out["candidate_answer_authority"])
        self.assertEqual(out["external_model_calls"],0)

    def test_negative_question_inverts_support(self):
        q=Q.replace("Which synthetic material","Which synthetic material is NOT").replace(
            "is NOT is associated","is NOT associated")
        out=propose(task_id="n",question=q,search_fn=search_fixture,fetch_fn=fetch_fixture)
        self.assertTrue(out["negative_question_detected"])
        self.assertEqual(out["selection_mode"],"MIN_SUPPORT_FOR_EXPLICIT_NEGATIVE_QUESTION")

    def test_deterministic(self):
        a=propose(task_id="s",question=Q,search_fn=search_fixture,fetch_fn=fetch_fixture)
        b=propose(task_id="s",question=Q,search_fn=search_fixture,fetch_fn=fetch_fixture)
        self.assertEqual(a["candidate_answer"],b["candidate_answer"])
        self.assertEqual(a["option_scores"],b["option_scores"])

    def test_no_pages_still_emits_deterministic_search_candidate(self):
        def nofetch(url,max_bytes=600000): return {"status":"FAILED"}
        out=propose(task_id="z",question=Q,search_fn=search_fixture,fetch_fn=nofetch)
        self.assertEqual(out["status"],"CANDIDATE_GENERATED")
        self.assertIn(out["candidate_answer"],["A","B","C","D","E"])
        self.assertEqual(out["confidence_band"],"LOW")

if __name__=="__main__":
    unittest.main()
