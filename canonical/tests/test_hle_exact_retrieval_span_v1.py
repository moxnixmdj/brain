import hashlib
import unittest
from canonical.runtime.hle_exact_retrieval_span_v1 import propose

def search_fixture(query,limit=14):
    return {"status":"PASS","results":[
        {"url":"https://a.test/x"},{"url":"https://b.test/y"},{"url":"https://c.test/z"}]}

P={
 "https://a.test/x":"In synthetic botany, the process is called Lumen drift. Lumen drift occurs in the Aster plant.",
 "https://b.test/y":"Independent reference: the Aster plant process is known as Lumen drift.",
 "https://c.test/z":"Unrelated synthetic reference to another process called Delta fall.",
}
def fetch_fixture(url,max_bytes=700000):
    t=P[url]
    return {"status":"PASS","url":url,"final_url":url,
            "body_sha256":hashlib.sha256(t.encode()).hexdigest(),"body_excerpt":t}

class ExactRetrievalTests(unittest.TestCase):
    def test_entity_term_candidate(self):
        q="In synthetic botany, what is the name of the process occurring in the Aster plant?"
        out=propose(task_id="e",question=q,search_fn=search_fixture,fetch_fn=fetch_fixture)
        self.assertEqual(out["status"],"CANDIDATE_GENERATED")
        self.assertIn("Lumen drift",out["candidate_answer"])
        self.assertFalse(out["candidate_answer_authority"])
        self.assertEqual(out["external_model_calls"],0)

    def test_temporal_candidate(self):
        def ff(url,max_bytes=700000):
            t="The fictional Aster event occurred in 1987. Separate chronology confirms 1987."
            return {"status":"PASS","url":url,"final_url":url,
                    "body_sha256":hashlib.sha256(t.encode()).hexdigest(),"body_excerpt":t}
        q="Synthetic chronology. When did the Aster event occur?"
        out=propose(task_id="t",question=q,search_fn=search_fixture,fetch_fn=ff)
        self.assertEqual(out["candidate_kind"],"TEMPORAL")
        self.assertEqual(out["candidate_answer"],"1987")

    def test_numeric_candidate(self):
        def ff(url,max_bytes=700000):
            t="For the synthetic quantity alpha, the measured value is 42.5 Hz."
            return {"status":"PASS","url":url,"final_url":url,
                    "body_sha256":hashlib.sha256(t.encode()).hexdigest(),"body_excerpt":t}
        q=r"For synthetic alpha, determine the measured value \(\nu\)."
        out=propose(task_id="n",question=q,search_fn=search_fixture,fetch_fn=ff)
        self.assertEqual(out["candidate_kind"],"NUMERIC")
        self.assertIn("42.5",out["candidate_answer"])

    def test_no_candidate(self):
        def ff(url,max_bytes=700000):
            t="lowercase filler words without candidate cues"
            return {"status":"PASS","url":url,"final_url":url,
                    "body_sha256":hashlib.sha256(t.encode()).hexdigest(),"body_excerpt":t}
        q="Synthetic open question without a known answer?"
        out=propose(task_id="z",question=q,search_fn=search_fixture,fetch_fn=ff)
        self.assertIn(out["status"],{"NO_CANDIDATE","CANDIDATE_GENERATED"})
        self.assertFalse(out.get("candidate_answer_authority",False))

if __name__=="__main__":
    unittest.main()
