from __future__ import annotations

import json
from unittest.mock import patch

from canonical.runtime import osworld_v21_local_qwen_policy_v1 as p


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


def tool_response(action: dict, response: str = "") -> str:
    return json.dumps({
        "model": p.MODEL,
        "choices": [{
            "finish_reason": "tool_calls",
            "message": {
                "tool_calls": [{
                    "type": "function",
                    "function": {
                        "name": p.TOOL_NAME,
                        "arguments": json.dumps({
                            "response": response,
                            "action_json": json.dumps(action),
                        }),
                    },
                }],
            },
        }],
    })


def state():
    return {
        "instruction": "Open the browser and inspect the page",
        "screen": {"width": 1920, "height": 1080},
        "screenshot_sha256": "a" * 64,
        "ocr": {
            "text_items": [
                {"text": "Example", "box": {"x0": 10, "y0": 10, "x1_exclusive": 100, "y1_exclusive": 30}}
            ]
        },
        "a11y_tree": None,
        "history": [],
    }


def test_state_prompt_contains_only_bounded_observations():
    prompt = p.state_prompt(state())
    assert "Open the browser" in prompt
    assert "Example" in prompt
    assert "screenshot_bytes" not in prompt
    assert len(prompt) <= p.MAX_PROMPT_CHARS + 32


def test_local_qwen_tool_call_decodes_one_action():
    with patch.object(p, "count_input_tokens", return_value=1000), patch.object(
        p.urllib.request,
        "urlopen",
        return_value=Response(tool_response({"type": "BROWSER_OP", "op": {"type": "OBSERVE"}}, "observe")),
    ):
        out = p.plan_state(state(), timeout_s=300)
    assert out["response"] == "observe"
    assert out["actions"] == [{"type": "BROWSER_OP", "op": {"type": "OBSERVE"}}]
    assert out["_policy_receipt"]["model"] == p.MODEL
    assert out["_policy_receipt"]["endpoint"] == p.ENDPOINT


def test_invalid_action_json_fails_closed():
    body = json.dumps({
        "model": p.MODEL,
        "choices": [{
            "finish_reason": "tool_calls",
            "message": {
                "tool_calls": [{
                    "function": {
                        "name": p.TOOL_NAME,
                        "arguments": json.dumps({"action_json": "{bad"}),
                    }
                }]
            },
        }],
    })
    with patch.object(p, "count_input_tokens", return_value=1000), patch.object(
        p.urllib.request, "urlopen", return_value=Response(body)
    ):
        try:
            p.plan_state(state(), timeout_s=300)
        except p.OSWorldPolicyError as exc:
            assert str(exc) == "ACTION_JSON_INVALID"
        else:
            raise AssertionError("expected invalid action rejection")


def test_wrong_tool_name_fails_closed():
    body = json.dumps({
        "choices": [{
            "message": {
                "tool_calls": [{
                    "function": {"name": "wrong", "arguments": "{}"}
                }]
            }
        }]
    })
    with patch.object(p, "count_input_tokens", return_value=1000), patch.object(
        p.urllib.request, "urlopen", return_value=Response(body)
    ):
        try:
            p.plan_state(state(), timeout_s=300)
        except p.OSWorldPolicyError as exc:
            assert str(exc) == "WRONG_TOOL_CALL"
        else:
            raise AssertionError("expected wrong tool rejection")
