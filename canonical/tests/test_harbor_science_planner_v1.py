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


def tool_response(args: dict, *, model: str = "brain-qwen3.5-9b") -> str:
    return json.dumps({
        "model": model,
        "choices": [{
            "finish_reason": "tool_calls",
            "message": {
                "role": "assistant",
                "tool_calls": [{
                    "type": "function",
                    "function": {
                        "name": p.TOOL_NAME,
                        "arguments": json.dumps(args),
                    },
                }],
            },
        }],
    })


class PlannerTests(unittest.TestCase):
    def test_extract_plain_object(self):
        self.assertEqual(p.extract_json_object('{"x":1}'), {"x": 1})

    def test_extract_fenced_noise_by_outer_object(self):
        self.assertEqual(p.extract_json_object('text before {"x":1} text after'), {"x": 1})

    def test_non_object_rejected(self):
        with self.assertRaisesRegex(Exception, "OBJECT_REQUIRED"):
            p.extract_json_object("[1,2]")

    def test_normalizes_observed_safe_candidates_alias(self):
        raw={
            "material_requirements":["R1"],
            "safe_candidates":[{
                "action_id":"A1",
                "covers":["R1"],
                "command":"echo x",
                "verify_command":"test true",
            }],
        }
        out=p.normalize_proposal_object(raw)
        self.assertNotIn("safe_candidates",out)
        self.assertEqual(out["candidates"][0]["action_id"],"A1")

    def test_rejects_ambiguous_candidate_aliases(self):
        raw={"candidates":[],"safe_candidates":[]}
        with self.assertRaisesRegex(Exception,"ALIAS_AMBIGUOUS"):
            p.normalize_proposal_object(raw)

    def test_local_tool_call_success_and_payload_shape(self):
        seen=[]
        args={
            "material_requirements":["R1"],
            "candidates":[{
                "action_id":"A1",
                "covers":["R1"],
                "command":"echo x",
                "verify_command":"test true",
            }],
        }
        def fake(req, timeout=180):
            seen.append({
                "url": req.full_url,
                "body": json.loads(req.data.decode("utf-8")),
                "timeout": timeout,
            })
            return Response(tool_response(args))
        with patch.object(p.urllib.request,"urlopen",fake):
            out=p.plan("synthetic",timeout_s=180)
        self.assertEqual(out["endpoint"],p.ENDPOINT)
        self.assertEqual(out["transport"],"PINNED_LOCAL_QWEN_LLAMA_CPP_TOOL_CALL")
        self.assertEqual(out["model"],"brain-qwen3.5-9b")
        self.assertEqual(p.extract_json_object(out["text"]),args)
        self.assertEqual(seen[0]["url"],"http://127.0.0.1:8080/v1/chat/completions")
        body=seen[0]["body"]
        self.assertEqual(body["model"],p.MODEL)
        self.assertEqual(body["tool_choice"],"required")
        self.assertFalse(body["parallel_tool_calls"])
        self.assertEqual(body["temperature"],0)
        self.assertEqual(body["max_tokens"],p.MAX_TOOL_COMPLETION_TOKENS)
        self.assertFalse(body["stream"])
        self.assertEqual(len(body["tools"]),1)
        self.assertEqual(body["tools"][0]["function"]["name"],p.TOOL_NAME)
        self.assertEqual(body["tools"][0]["function"]["parameters"]["properties"]["candidates"]["maxItems"],1)

    def test_length_finish_reason_fails_closed_before_parsing_partial_arguments(self):
        response=json.dumps({
            "model":p.MODEL,
            "choices":[{
                "finish_reason":"length",
                "message":{
                    "tool_calls":[{
                        "function":{
                            "name":p.TOOL_NAME,
                            "arguments":"{\\\"material_requirements\\\":[\\\"R1\\\"],\\\"candidates\\\":[{"
                        }
                    }]
                }
            }],
        })
        with patch.object(p.urllib.request,"urlopen",return_value=Response(response)):
            with self.assertRaisesRegex(Exception,"OUTPUT_TRUNCATED"):
                p.plan("synthetic")

    def test_missing_tool_call_fails_closed(self):
        response=json.dumps({
            "model":p.MODEL,
            "choices":[{"message":{"role":"assistant","content":"{}"}}],
        })
        with patch.object(p.urllib.request,"urlopen",return_value=Response(response)):
            with self.assertRaisesRegex(Exception,"TOOL_CALL_REQUIRED"):
                p.plan("synthetic")

    def test_wrong_tool_name_fails_closed(self):
        response=json.dumps({
            "model":p.MODEL,
            "choices":[{
                "message":{
                    "tool_calls":[{
                        "function":{"name":"wrong_tool","arguments":"{}"}
                    }]
                }
            }],
        })
        with patch.object(p.urllib.request,"urlopen",return_value=Response(response)):
            with self.assertRaisesRegex(Exception,"EXACTLY_ONE_PROPOSAL_TOOL_CALL_REQUIRED"):
                p.plan("synthetic")

    def test_multiple_proposal_calls_fail_closed(self):
        call={"function":{"name":p.TOOL_NAME,"arguments":"{}"}}
        response=json.dumps({
            "model":p.MODEL,
            "choices":[{"message":{"tool_calls":[call,call]}}],
        })
        with patch.object(p.urllib.request,"urlopen",return_value=Response(response)):
            with self.assertRaisesRegex(Exception,"EXACTLY_ONE_PROPOSAL_TOOL_CALL_REQUIRED"):
                p.plan("synthetic")

    def test_local_transport_failure_fails_closed(self):
        with patch.object(p.urllib.request,"urlopen",side_effect=OSError("offline")):
            with self.assertRaisesRegex(Exception,"LOCAL_ROUTE_FAILED"):
                p.plan("synthetic")

    def test_timeout_bounds_fail_closed(self):
        for value in (0,301,True,1.5):
            with self.subTest(value=value):
                with self.assertRaisesRegex(Exception,"TIMEOUT_INVALID"):
                    p.plan("synthetic",timeout_s=value)


if __name__=="__main__":
    unittest.main(verbosity=2)
