import unittest
from canonical.runtime import hle_native_open_web_fallback_v1 as fallback

def fake_plan(**kwargs):
    return {
        "schema":"PLAN",
        "views":[
            {"method":"QUOTED_SEED","query":"When You Wish Upon a Star"},
            {"method":"ENTITY_SEED","query":"Walt Disney"},
        ],
    }

def mixed_discover(objective, **kwargs):
    q=kwargs["query_override"]
    if q=="When You Wish Upon a Star":
        return {
          "candidates":[{"url":"https://example.org/a","title":"A","discovery_backend":"BING_RSS"}],
          "retrieval_provenance":[{"backend":"BING_RSS","candidate_count":1},{"backend":"CROSSREF","candidate_count":0}],
          "backend_errors":[{"backend":"DUCKDUCKGO_HTML","error":"outage"}],
        }
    return {
      "candidates":[{"url":"https://example.org/a","title":"dup"},{"url":"https://example.org/b","title":"B"}],
      "retrieval_provenance":[{"backend":"BING_RSS","candidate_count":2},{"backend":"DUCKDUCKGO_HTML","candidate_count":0}],
      "backend_errors":[],
    }

def dead_discover(objective, **kwargs):
    return {"candidates":[],"retrieval_provenance":[],"backend_errors":[{"backend":"BING_RSS","error":"down"},{"backend":"DUCKDUCKGO_HTML","error":"down"}]}

class HLENativeOpenWebFallbackV1Tests(unittest.TestCase):
    def test_mixed_health_and_dedupe(self):
        out=fallback.retrieve(task_id="x",question="visible",plan_fn=fake_plan,discover_fn=mixed_discover)
        self.assertEqual(out["candidate_count"],2)
        self.assertEqual(out["backend_health"]["BING_RSS"]["health"],"HEALTHY")
        self.assertEqual(out["backend_health"]["DUCKDUCKGO_HTML"]["health"],"DEGRADED")
        self.assertFalse(out["gold_accessed"])
        self.assertEqual(out["external_model_calls"],0)
        self.assertFalse(out["answer_authority"])
        self.assertFalse(out["nonexistence_claim_authorized"])

    def test_all_backends_failed_is_retryable_not_negative_evidence(self):
        out=fallback.retrieve(task_id="x",question="visible",plan_fn=fake_plan,discover_fn=dead_discover)
        self.assertEqual(out["status"],"RETRYABLE_SOURCE_FAILURE")
        self.assertEqual(out["failed_retryable_view_count"],2)
        self.assertTrue(all(v["retryable"] for v in out["views"]))
        self.assertFalse(out["nonexistence_claim_authorized"])

    def test_successful_empty_is_not_nonexistence(self):
        def empty(objective,**kwargs):
            return {"candidates":[],"retrieval_provenance":[{"backend":"BING_RSS","candidate_count":0}],"backend_errors":[]}
        out=fallback.retrieve(task_id="x",question="visible",plan_fn=fake_plan,discover_fn=empty)
        self.assertEqual(out["status"],"NO_CANDIDATES_YET")
        self.assertTrue(all(v["status"]=="SUCCESSFUL_EMPTY__NOT_NONEXISTENCE" for v in out["views"]))
        self.assertEqual(out["backend_health"]["BING_RSS"]["health"],"HEALTHY_EMPTY_ON_THIS_SAMPLE")

    def test_invalid_plan_fails_closed(self):
        with self.assertRaises(ValueError):
            fallback.retrieve(task_id="x",question="visible",plan_fn=lambda **k:{"views":[]},discover_fn=mixed_discover)

if __name__=="__main__":
    unittest.main(verbosity=2)
