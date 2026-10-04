#!/usr/bin/env python3
import json
import unittest
from unittest.mock import patch

from canonical.runtime import local_qwen_semantic_seed_v1 as s


class Response:
    def __init__(self, body: str, status: int = 200):
        self.body = body.encode("utf-8")
        self.status = status

    def read(self, n: int = -1) -> bytes:
        return self.body if n < 0 else self.body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def completion(content: str) -> str:
    return json.dumps(
        {
            "model": s.MODEL,
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
        }
    )


class SemanticSeedTests(unittest.TestCase):
    def test_local_generation_contract(self):
        seen = []

        def fake(req, timeout=180):
            seen.append(
                {
                    "url": req.full_url,
                    "body": json.loads(req.data.decode("utf-8")),
                    "timeout": timeout,
                }
            )
            return Response(completion("A faithful transformed answer."))

        with patch.object(s.urllib.request, "urlopen", fake):
            out = s.generate("Paraphrase this sentence without changing its meaning.")

        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["response"], "A faithful transformed answer.")
        self.assertEqual(out["network_scope"], "LOOPBACK_ONLY")
        self.assertEqual(out["remote_generation_dependencies"], 0)
        self.assertEqual(out["api_key_dependencies"], 0)
        self.assertFalse(any(out["authority"].values()))
        self.assertEqual(seen[0]["url"], s.ENDPOINT)
        body = seen[0]["body"]
        self.assertEqual(body["model"], s.MODEL)
        self.assertEqual(body["temperature"], 0)
        self.assertFalse(body["stream"])
        self.assertNotIn("tools", body)
        self.assertEqual(body["messages"][-1]["role"], "user")

    def test_empty_prompt_fails_closed(self):
        with self.assertRaisesRegex(Exception, "PROMPT_REQUIRED"):
            s.generate("   ")

    def test_empty_completion_fails_closed(self):
        with patch.object(
            s.urllib.request, "urlopen", return_value=Response(completion("  "))
        ):
            with self.assertRaisesRegex(Exception, "NONEMPTY_CONTENT_REQUIRED"):
                s.generate("Summarize the visible text.")

    def test_tool_call_is_rejected(self):
        body = json.dumps(
            {
                "model": s.MODEL,
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [{"function": {"name": "unexpected"}}],
                        }
                    }
                ],
            }
        )
        with patch.object(s.urllib.request, "urlopen", return_value=Response(body)):
            with self.assertRaisesRegex(Exception, "UNEXPECTED_TOOL_CALL"):
                s.generate("Write a short story.")

    def test_nonlocal_failure_fails_closed(self):
        with patch.object(s.urllib.request, "urlopen", side_effect=OSError("offline")):
            with self.assertRaisesRegex(Exception, "LOCAL_ROUTE_FAILED"):
                s.generate("Simplify this explanation.")

    def test_bounds_fail_closed(self):
        for value in (0, 301, True, 1.5):
            with self.subTest(timeout=value):
                with self.assertRaisesRegex(Exception, "TIMEOUT_INVALID"):
                    s.generate("x", timeout_s=value)
        for value in (63, 4097, True, 1.5):
            with self.subTest(max_tokens=value):
                with self.assertRaisesRegex(Exception, "MAX_TOKENS_INVALID"):
                    s.generate("x", max_tokens=value)

    def test_no_remote_generation_url_is_embedded(self):
        self.assertTrue(s.ENDPOINT.startswith("http://127.0.0.1:"))
        source = open(s.__file__, "r", encoding="utf-8").read()
        self.assertNotIn("https://", source)
        self.assertNotIn("Authorization", source)
        self.assertNotIn("api_key", source.lower().replace("api_key_dependencies", ""))


if __name__ == "__main__":
    unittest.main()
