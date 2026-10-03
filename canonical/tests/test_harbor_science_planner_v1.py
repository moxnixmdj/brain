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
    def test_first_alias_success_and_payload_shape(self):
        seen=[]
        def fake(req, timeout=20):
            body=json.loads(req.data.decode("utf-8"))
            seen.append(body)
            return Response('{"material_requirements":["R1"],"candidates":[{"action_id":"A1","covers":["R1"],"command":"echo x","verify_command":"test true"}]}')
        with patch.object(p.urllib.request, "urlopen", fake):
            out=p.plan("synthetic", timeout_s=20)
        self.assertEqual(out["model"], "openai-fast")
        self.assertEqual(out["endpoint"], p.ENDPOINT)
        self.assertEqual(seen[0]["model"], "openai-fast")
        self.assertTrue(seen[0]["jsonMode"])

    def test_failover_to_second_alias(self):
        calls=[]
        def fake(req, timeout=20):
            body=json.loads(req.data.decode("utf-8"))
            calls.append(body["model"])
            if len(calls)==1:
                raise OSError("first unavailable")
            return Response('{"material_requirements":["R1"],"candidates":[{"action_id":"A1","covers":["R1"],"command":"echo x","verify_command":"test true"}]}')
        with patch.object(p.urllib.request, "urlopen", fake):
            out=p.plan("synthetic", timeout_s=20)
        self.assertEqual(calls[:2], ["openai-fast","openai"])
        self.assertEqual(out["model"], "openai")
        self.assertEqual(len(out["errors"]),1)

    def test_all_aliases_fail_closed(self):
        with patch.object(p.urllib.request, "urlopen", side_effect=OSError("offline")):
            with self.assertRaisesRegex(Exception, "ALL_ROUTES_FAILED"):
                p.plan("synthetic", timeout_s=20)


if __name__=="__main__":
    unittest.main(verbosity=2)
