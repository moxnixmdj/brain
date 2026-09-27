#!/usr/bin/env python3
import base64
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME = CANONICAL_ROOT / "runtime"
spec = importlib.util.spec_from_file_location(
    "external_tool_relay_target", RUNTIME / "external_tool_relay.py"
)
relay = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = relay
spec.loader.exec_module(relay)


def request(kind="urlopen", payload=None):
    req = {
        "schema": relay.REQUEST_SCHEMA,
        "kind": kind,
        "agent_id": "SUPERWORKER-UNIFIED-1",
        "task_id": "SI-REAL-UBJSON-SNAPSHOT-001",
        "payload": payload or {
            "url": "https://registry.npmjs.org/-/v1/search?text=ubj&size=40",
            "method": "GET",
            "headers": {},
            "timeout_s": 20,
            "data_b64": None,
        },
    }
    req["request_sha256"] = relay.request_sha256(req)
    return req


class ExternalToolRelayTests(unittest.TestCase):
    def test_request_hash_and_identity_are_authoritative(self):
        req = request()
        relay.validate_request(
            req,
            expected_agent="SUPERWORKER-UNIFIED-1",
            expected_task="SI-REAL-UBJSON-SNAPSHOT-001",
        )
        req["payload"]["url"] = "https://registry.npmjs.org/changed"
        with self.assertRaisesRegex(relay.RelayFailure, "REQUEST_HASH_MISMATCH"):
            relay.validate_request(req)

    def test_urlopen_response_preserves_body_and_identity(self):
        req = request()
        fake = {
            "status": 200,
            "final_url": req["payload"]["url"],
            "headers": {"Content-Type": "application/json"},
            "raw": b'{"ok":true}',
            "duration_s": 0.01,
        }
        with mock.patch.object(relay, "_http_bytes", return_value=fake):
            result = relay.execute_request(req)
        self.assertEqual(base64.b64decode(result["body_b64"]), b'{"ok":true}')
        response = relay.build_response(req, result=result)
        self.assertEqual(response["request_sha256"], req["request_sha256"])
        self.assertEqual(response["agent_id"], "SUPERWORKER-UNIFIED-1")
        self.assertEqual(response["task_id"], "SI-REAL-UBJSON-SNAPSHOT-001")

    def test_service_pending_writes_hash_bound_response(self):
        req = request()
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            p = root / (req["request_sha256"] + ".request.json")
            p.write_text(json.dumps(req), encoding="utf-8")
            fake = {
                "status": 200,
                "final_url": req["payload"]["url"],
                "headers": {},
                "raw": b"{}",
                "duration_s": 0.01,
            }
            with mock.patch.object(relay, "_http_bytes", return_value=fake):
                serviced = relay.service_pending(
                    root,
                    expected_agent="SUPERWORKER-UNIFIED-1",
                    expected_task="SI-REAL-UBJSON-SNAPSHOT-001",
                )
            self.assertEqual(len(serviced), 1)
            response = json.loads(
                (root / (req["request_sha256"] + ".response.json")).read_text()
            )
            self.assertEqual(response["status"], "ok")
            self.assertEqual(response["request_sha256"], req["request_sha256"])

    def test_non_allowlisted_host_fails_closed(self):
        with self.assertRaisesRegex(relay.RelayFailure, "URL_HOST_FORBIDDEN"):
            relay._validate_public_https_url("https://example.com/secret")


if __name__ == "__main__":
    unittest.main(verbosity=2)
