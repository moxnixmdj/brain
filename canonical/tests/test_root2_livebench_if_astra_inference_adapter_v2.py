import unittest
from unittest import mock

from canonical.runtime import root2_livebench_if_astra_inference_adapter_v2 as v2

REQ=lambda text:{
    "benchmark_id":"LIVEBENCH_IF_2026_06_25",
    "task_id":"synthetic",
    "task_payload":{"instruction":text},
    "allowed_tools":[],
}

class LiveBenchAdapterV2Tests(unittest.TestCase):
    def test_exact_formal_route(self):
        out=v2.infer(REQ('Reply with exactly "ALPHA".'))
        self.assertEqual(out["status"],"PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertEqual(out["answer"],"ALPHA")
        self.assertEqual(out["response_route"],"VERIFIED_GENERIC_FORMAL_CONSTRAINT_COMPILER_V1")
        self.assertEqual(out["model_dependency_count"],0)

    def test_semantic_request_falls_through_unchanged(self):
        expected={
            "task_id":"synthetic",
            "status":"PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
            "answer":"fallback",
            "artifacts":[],
            "tool_trace":[],
            "cognition_dependency_class":"MODEL_INDEPENDENT",
            "model_dependency_count":0,
        }
        with mock.patch.object(v2.fallback_v1,"infer",return_value=expected) as f:
            out=v2.infer(REQ("Explain photosynthesis clearly."))
        self.assertEqual(out,expected)
        f.assert_called_once()

    def test_semantic_seed_structural_route_does_not_shortcut(self):
        expected={"status":"BLOCKED_BY_FALLBACK"}
        with mock.patch.object(v2.fallback_v1,"infer",return_value=expected) as f:
            out=v2.infer(REQ("Use at least 5 unique words in the response."))
        self.assertEqual(out,expected)
        f.assert_called_once()

    def test_contradictory_formal_constraints_do_not_invent_answer(self):
        expected={"status":"BLOCKED_BY_FALLBACK"}
        with mock.patch.object(v2.fallback_v1,"infer",return_value=expected) as f:
            out=v2.infer(REQ('Reply with exactly "ALPHA". Use lowercase only.'))
        self.assertEqual(out,expected)
        f.assert_called_once()

    def test_external_tools_remain_forbidden(self):
        req=REQ('Reply with exactly "ALPHA".')
        req["allowed_tools"]=["browser"]
        with self.assertRaises(v2.Root2InferenceBlocked):
            v2.infer(req)

if __name__=="__main__":
    unittest.main()
