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
    def setUp(self):
        self._real_count_input_tokens = p.count_input_tokens
        self._count_patcher = patch.object(p, "count_input_tokens", return_value=1000)
        self.mock_count_input_tokens = self._count_patcher.start()
        self.addCleanup(self._count_patcher.stop)

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
        self.assertEqual(out["transport"],"PINNED_LOCAL_QWEN_LLAMA_CPP_TOOL_CALL__EXACT_SERVER_TOKEN_COUNT")
        self.assertEqual(out["model"],"brain-qwen3.5-9b")
        self.assertEqual(out["input_tokens"],1000)
        self.assertEqual(out["effective_timeout_s"],300)
        self.assertEqual(out["token_count_endpoint"],p.TOKEN_COUNT_ENDPOINT)
        self.assertEqual(p.extract_json_object(out["text"]),args)
        self.assertEqual(seen[0]["url"],"http://127.0.0.1:8080/v1/chat/completions")
        body=seen[0]["body"]
        self.assertEqual(body["model"],p.MODEL)
        self.assertEqual(body["tool_choice"],"required")
        self.assertFalse(body["parallel_tool_calls"])
        self.assertEqual(body["temperature"],0)
        self.assertEqual(body["chat_template_kwargs"],{"enable_thinking":False})
        self.assertEqual(body["max_tokens"],p.MAX_TOOL_COMPLETION_TOKENS)
        self.assertFalse(body["stream"])
        self.assertEqual(len(body["tools"]),1)
        self.assertEqual(body["tools"][0]["function"]["name"],p.TOOL_NAME)
        self.assertEqual(body["tools"][0]["function"]["parameters"]["properties"]["candidates"]["maxItems"],p.MAX_CANDIDATES_PER_PROPOSAL)
        candidate_schema=body["tools"][0]["function"]["parameters"]["properties"]["candidates"]["items"]["properties"]
        self.assertNotIn("maxLength",candidate_schema["command"])
        self.assertNotIn("maxLength",candidate_schema["verify_command"])
        self.assertGreaterEqual(p.MAX_TOOL_COMPLETION_TOKENS,4096)

    def test_request_disables_model_thinking_at_chat_template_boundary(self):
        payload=p._request_payload("synthetic")
        self.assertEqual(
            payload["chat_template_kwargs"],
            {"enable_thinking":False},
        )

    def test_exact_token_count_endpoint_uses_full_chat_payload(self):
        payload=p._request_payload("synthetic")
        seen=[]
        def fake(req, timeout=180):
            seen.append({
                "url":req.full_url,
                "body":json.loads(req.data.decode("utf-8")),
                "timeout":timeout,
            })
            return Response(json.dumps({
                "object":"response.input_tokens",
                "input_tokens":7311,
            }))
        with patch.object(p.urllib.request,"urlopen",fake):
            out=self._real_count_input_tokens(payload)
        self.assertEqual(out,7311)
        self.assertEqual(seen[0]["url"],p.TOKEN_COUNT_ENDPOINT)
        self.assertEqual(seen[0]["body"],payload)
        self.assertEqual(seen[0]["timeout"],p.TOKEN_COUNT_TIMEOUT_S)

    def test_exact_token_timeout_keeps_small_prompt_floor(self):
        self.assertEqual(p.effective_timeout_s(1000,180),300)

    def test_exact_token_timeout_exceeds_rank12_observed_prefill_need(self):
        # Rank12 inferred about 7,142 prompt tokens and timed out at 300s.
        out=p.effective_timeout_s(7142,300)
        self.assertGreaterEqual(out,657)
        self.assertLessEqual(out,p.MAX_TIMEOUT_S)

    def test_exact_token_timeout_caps_inside_fail_closed_envelope(self):
        self.assertEqual(p.effective_timeout_s(100000,300),p.MAX_TIMEOUT_S)

    def test_exact_token_timeout_rejects_invalid_counts(self):
        for value in (0,-1,True,1.5):
            with self.subTest(value=value):
                with self.assertRaisesRegex(Exception,"INPUT_TOKEN_COUNT_INVALID"):
                    p.effective_timeout_s(value,300)

    def test_plan_uses_exact_count_for_effective_timeout_and_receipt(self):
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
        self.mock_count_input_tokens.return_value=7142
        def fake(req, timeout=180):
            seen.append(timeout)
            return Response(tool_response(args))
        with patch.object(p.urllib.request,"urlopen",fake):
            out=p.plan("synthetic",timeout_s=300)
        expected=p.effective_timeout_s(7142,300)
        self.assertEqual(seen,[expected])
        self.assertEqual(out["input_tokens"],7142)
        self.assertEqual(out["effective_timeout_s"],expected)

    def test_decoded_command_length_is_enforced_after_transport(self):
        args={
            "material_requirements":["R1"],
            "candidates":[{
                "action_id":"A1",
                "covers":["R1"],
                "command":"x"*(p.MAX_COMMAND_CHARS+1),
                "verify_command":"test true",
            }],
        }
        with patch.object(p.urllib.request,"urlopen",return_value=Response(tool_response(args))):
            with self.assertRaisesRegex(Exception,"COMMAND_TOO_LONG"):
                p.plan("synthetic")

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
        for value in (0,p.MAX_TIMEOUT_S+1,True,1.5):
            with self.subTest(value=value):
                with self.assertRaisesRegex(Exception,"TIMEOUT_INVALID"):
                    p.plan("synthetic",timeout_s=value)


    def test_multi_action_schema_is_bounded_and_dependency_aware(self):
        schema=p.TOOL["function"]["parameters"]["properties"]["candidates"]
        self.assertEqual(schema["maxItems"],p.MAX_CANDIDATES_PER_PROPOSAL)
        props=schema["items"]["properties"]
        self.assertIn("depends_on",props)
        self.assertEqual(props["timeout_sec"]["maximum"],7200)
        self.assertEqual(props["verify_timeout_sec"]["maximum"],3600)

    def test_plan_accepts_four_bounded_candidates(self):
        args={
            "material_requirements":["R1","R2","R3","R4"],
            "candidates":[
                {"action_id":f"A{i}","covers":[f"R{i}"],"command":f"echo {i}","verify_command":"test true"}
                for i in range(1,5)
            ],
        }
        with patch.object(p.urllib.request,"urlopen",lambda req,timeout=180: Response(tool_response(args))):
            out=p.plan("synthetic",timeout_s=180)
        self.assertEqual(len(p.extract_json_object(out["text"])["candidates"]),4)

if __name__=="__main__":
    unittest.main(verbosity=2)
