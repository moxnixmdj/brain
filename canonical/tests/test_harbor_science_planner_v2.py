from __future__ import annotations
import json
import os
import unittest
from unittest.mock import patch

from canonical.runtime import harbor_science_planner_v2 as p


class Response:
    def __init__(self, obj, status=200):
        self.status = status
        self._raw = json.dumps(obj).encode("utf-8")
    def read(self, n=-1):
        return self._raw if n < 0 else self._raw[:n]
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


def tool_response(arguments, *, model=p.DEFAULT_MODEL, calls=1, name=p.TOOL_NAME):
    call = {
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }
    return {
        "model": model,
        "choices": [{"message": {"tool_calls": [call for _ in range(calls)]}, "finish_reason": "tool_calls"}],
    }


class PlannerV2Tests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("PROJECT_BRAIN_SCIENCE_LOCAL_ENDPOINT", None)
        os.environ.pop("PROJECT_BRAIN_SCIENCE_LOCAL_MODEL", None)

    def test_external_endpoint_is_rejected(self):
        os.environ["PROJECT_BRAIN_SCIENCE_LOCAL_ENDPOINT"] = "https://example.com/v1/chat/completions"
        with self.assertRaisesRegex(Exception, "NOT_LOOPBACK|SCHEME_INVALID"):
            p.plan("x")

    def test_forced_single_tool_payload_and_exact_arguments(self):
        seen = {}
        proposal = {
            "material_requirements": ["R1"],
            "candidates": [{
                "action_id": "A1",
                "covers": ["R1"],
                "command": "echo x",
                "verify_command": "test true",
            }],
        }
        def fake(req, timeout=180):
            seen["payload"] = json.loads(req.data.decode("utf-8"))
            seen["url"] = req.full_url
            return Response(tool_response(proposal))
        with patch.object(p.urllib.request, "urlopen", fake):
            out = p.plan("synthetic", timeout_s=180)
        payload = seen["payload"]
        self.assertEqual(seen["url"], p.DEFAULT_ENDPOINT)
        self.assertEqual(payload["tool_choice"], "required")
        self.assertFalse(payload["parallel_tool_calls"])
        self.assertEqual(len(payload["tools"]), 1)
        self.assertEqual(payload["tools"][0]["function"]["name"], p.TOOL_NAME)
        self.assertEqual(json.loads(out["text"]), proposal)
        self.assertFalse(out["external_network_fallback"])

    def test_wrong_model_identity_rejected(self):
        with patch.object(
            p.urllib.request, "urlopen",
            return_value=Response(tool_response({"candidates": []}, model="wrong-model")),
        ):
            with self.assertRaisesRegex(Exception, "MODEL_IDENTITY_MISMATCH"):
                p.plan("synthetic")

    def test_multiple_tool_calls_rejected(self):
        proposal = {"candidates": [{"action_id":"A","covers":["R"],"command":"echo x","verify_command":"test true"}]}
        with patch.object(
            p.urllib.request, "urlopen",
            return_value=Response(tool_response(proposal, calls=2)),
        ):
            with self.assertRaisesRegex(Exception, "TOOL_CALL_COUNT_INVALID"):
                p.plan("synthetic")

    def test_wrong_tool_name_rejected(self):
        proposal = {"candidates": [{"action_id":"A","covers":["R"],"command":"echo x","verify_command":"test true"}]}
        with patch.object(
            p.urllib.request, "urlopen",
            return_value=Response(tool_response(proposal, name="other")),
        ):
            with self.assertRaisesRegex(Exception, "TOOL_NAME_INVALID"):
                p.plan("synthetic")

    def test_local_unavailability_fails_closed_without_fallback(self):
        with patch.object(p.urllib.request, "urlopen", side_effect=OSError("offline")):
            with self.assertRaisesRegex(Exception, "LOCAL_PLANNER_UNAVAILABLE"):
                p.plan("synthetic")


if __name__ == "__main__":
    unittest.main(verbosity=2)
