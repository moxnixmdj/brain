import hashlib
import unittest
from canonical.runtime.hle_exact_retrieval_extract_v1 import propose

PAGES={
 "https://a.test/x":"Synthetic history records that the Arcturus device was invented in 1874 by Elena Maren.",
 "https://b.test/x":"A museum catalogue dates the Arcturus device invention to 1874.",
 "https://c.test/x":"The fictional process is called Silver Moss in the reference handbook.",
 "https://d.test/x":"Independent notes say the process is known as Silver Moss.",
}
def search(q,limit=12):
    return {"status":"PASS","results":[{"url":u} for u in PAGES]}
def fetch(u,max_bytes=600000):
    t=PAGES[u]
    return {"status":"PASS","url":u,"final_url":u,"body_excerpt":t,
            "body_sha256":hashlib.sha256(t.encode()).hexdigest()}

class T(unittest.TestCase):
    def test_year(self):
        q="In what year was the fictional Arcturus device invented?"
        o=propose(task_id="y",question=q,search_fn=search,fetch_fn=fetch)
        self.assertEqual(o["candidate_answer"],"1874")
        self.assertEqual(o["external_model_calls"],0)

    def test_term(self):
        q="What is the name of the fictional process described by the synthetic handbook?"
        o=propose(task_id="t",question=q,search_fn=search,fetch_fn=fetch)
        self.assertEqual(o["status"],"CANDIDATE_GENERATED")
        self.assertIn("Silver Moss",o["candidate_answer"])

    def test_image_fails_closed(self):
        o=propose(task_id="i",question="Who made the synthetic device?",
                  has_nonempty_image_payload=True,search_fn=search,fetch_fn=fetch)
        self.assertTrue(o["status"].startswith("FAIL_CLOSED"))
        self.assertIsNone(o["candidate_answer"])

    def test_unsupported_fails_closed(self):
        o=propose(task_id="u",question="Explain the synthetic mechanism deeply.",
                  search_fn=search,fetch_fn=fetch)
        self.assertEqual(o["status"],"FAIL_CLOSED__QUESTION_FORM_UNSUPPORTED")

    def test_deterministic(self):
        q="In what year was the fictional Arcturus device invented?"
        a=propose(task_id="a",question=q,search_fn=search,fetch_fn=fetch)
        b=propose(task_id="a",question=q,search_fn=search,fetch_fn=fetch)
        self.assertEqual(a["candidate_answer"],b["candidate_answer"])
        self.assertEqual(a["candidate_score"],b["candidate_score"])

if __name__=="__main__":
    unittest.main(verbosity=2)
