from __future__ import annotations
import json
import unittest
from unittest.mock import patch

from canonical.runtime import harbor_science_planner_v1 as p


class Response:
    def __init__(self, body: str, status: int = 200):
        self._body = body.encode("utf-8")
        self.status = status
    def read(self, n=-1):
        return self._body if n < 0 else self._body[:n]
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


def envelope(content: str, model: str = p.MODEL) -> str:
    return json.dumps({
        "model": model,
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
    })


class PlannerTests(unittest.TestCase):
    def test_extract_plain_object(self):
        self.assertEqual(p.extract_json_object('{"x":1}'), {"x":1})

    def test_extract_fenced_noise_by_outer_object(self):
        self.assertEqual(p.extract_json_object('text before {"x":1} text after'), {"x":1})

    def test_non_object_rejected(self):
        with self.assertRaisesRegex(Exception, "OBJECT_REQUIRED"):
            p.extract_json_object("[1,2]")

    def test_normalizes_observed_safe_candidates_alias(self):
        raw={"material_requirements":["R1"],"safe_candidates":[{"action_id":"A1","covers":["R1"],"command":"echo x","verify_command":"test true"}]}
        out=p.normalize_proposal_object(raw)
        self.assertNotIn("safe_candidates",out)
        self.assertEqual(out["candidates"][0]["action_id"],"A1")

    def test_rejects_ambiguous_candidate_aliases(self):
        raw={"candidates":[],"safe_candidates":[]}
        with self.assertRaisesRegex(Exception,"ALIAS_AMBIGUOUS"):
            p.normalize_proposal_object(raw)

    def test_exact_local_endpoint_and_openai_payload(self):
        seen=[]
        proposal='{"material_requirements":["R1"],"candidates":[{"action_id":"A1","covers":["R1"],"command":"echo x","verify_command":"test true"}]}'
        def fake(req, timeout=180):
            seen.append((req,timeout,json.loads(req.data.decode("utf-8"))))
            return Response(envelope(proposal))
        with patch.object(p.urllib.request, "urlopen", fake):
            out=p.plan("synthetic", timeout_s=180)
        req,timeout,body=seen[0]
        self.assertEqual(req.full_url,"http://127.0.0.1:8080/v1/chat/completions")
        self.assertEqual(timeout,180)
        self.assertEqual(body["model"],"brain-qwen3.5-9b")
        self.assertEqual(body["temperature"],0)
        self.assertFalse(body["stream"])
        self.assertEqual(out["model"],"brain-qwen3.5-9b")
        self.assertEqual(out["backend"],"LOCAL_LLAMA_SERVER")
        self.assertEqual(out["transport"],"PINNED_LOCAL_OPENAI_CHAT_COMPLETIONS")

    def test_hosted_endpoint_override_fails_closed_before_network(self):
        with patch.dict(p.os.environ,{"PROJECT_BRAIN_SCIENCE_PLANNER_ENDPOINT":"https://text.pollinations.ai/"},clear=False), \
             patch.object(p.urllib.request,"urlopen",side_effect=AssertionError("network must not run")):
            with self.assertRaisesRegex(Exception,"ENDPOINT_IDENTITY_MISMATCH"):
                p.plan("synthetic")

    def test_wrong_model_identity_rejected(self):
        with patch.object(p.urllib.request,"urlopen",return_value=Response(envelope('{"x":1}',model="other"))):
            with self.assertRaisesRegex(Exception,"MODEL_IDENTITY_MISMATCH"):
                p.plan("synthetic")

    def test_invalid_local_response_fails_closed(self):
        with patch.object(p.urllib.request,"urlopen",return_value=Response(envelope("not json"))):
            with self.assertRaisesRegex(Exception,"NO_JSON"):
                p.plan("synthetic")

    def test_local_transport_failure_has_no_fallback(self):
        calls=[]
        def fail(req, timeout=180):
            calls.append(req.full_url)
            raise OSError("local down")
        with patch.object(p.urllib.request,"urlopen",side_effect=fail):
            with self.assertRaisesRegex(Exception,"SCIENCE_LOCAL_PLANNER_FAILED"):
                p.plan("synthetic")
        self.assertEqual(calls,[p.ENDPOINT])


if __name__=="__main__":
    unittest.main(verbosity=2)
