#!/usr/bin/env python3
import base64
import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME = CANONICAL_ROOT / "runtime"
spec = importlib.util.spec_from_file_location(
    "external_tool_relay_target", RUNTIME / "external_tool_relay.py"
)
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class _Response:
    status = 200

    def __init__(self, body=b'{"objects":[]}'):
        self._body = body
        self.headers = _Headers({"Content-Length": str(len(body)), "Content-Type": "application/json"})

    def read(self, n=-1):
        return self._body[:n] if n >= 0 else self._body

    def geturl(self):
        return "https://registry.npmjs.org/-/v1/search?text=ubj&size=40"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _write_request(path, url):
    req = {
        "schema": relay.REQUEST_SCHEMA,
        "kind": "urlopen",
        "agent_id": "SUPERWORKER-UNIFIED-1",
        "task_id": "SI-REAL-UBJSON-SNAPSHOT-001",
        "payload": {
            "url": url,
            "method": "GET",
            "headers": {"User-agent": "ProjectBrain-test"},
            "timeout_s": 20,
            "data_b64": None,
        },
    }
    req["request_sha256"] = relay._canonical_request_hash(req)
    request_path = path / (req["request_sha256"] + ".request.json")
    request_path.write_text(json.dumps(req), encoding="utf-8")
    return request_path


class RelayTests(unittest.TestCase):
    def test_services_exact_identity_bound_npm_request(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            request_path = _write_request(
                root, "https://registry.npmjs.org/-/v1/search?text=ubj&size=40"
            )
            with mock.patch.object(relay, "_validate_public_host", return_value=None):
                response = relay.service_request(
                    request_path,
                    allowed_hosts={"registry.npmjs.org"},
                    expected_agent="SUPERWORKER-UNIFIED-1",
                    expected_task="SI-REAL-UBJSON-SNAPSHOT-001",
                    opener=lambda request, timeout: _Response(),
                )
            self.assertEqual(response["schema"], relay.RESPONSE_SCHEMA)
            self.assertEqual(response["status"], "ok")
            self.assertEqual(response["request_sha256"], request_path.name.split(".")[0])
            self.assertEqual(
                base64.b64decode(response["result"]["body_b64"]),
                b'{"objects":[]}',
            )

    def test_rejects_unapproved_destination(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            request_path = _write_request(root, "https://example.com/")
            with self.assertRaisesRegex(relay.RelayError, "DESTINATION_NOT_ALLOWED"):
                relay.service_request(
                    request_path,
                    allowed_hosts={"registry.npmjs.org"},
                    expected_agent="SUPERWORKER-UNIFIED-1",
                    expected_task="SI-REAL-UBJSON-SNAPSHOT-001",
                    opener=lambda request, timeout: _Response(),
                )

    def test_rejects_identity_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            request_path = _write_request(
                root, "https://registry.npmjs.org/-/v1/search?text=ubj&size=40"
            )
            with self.assertRaisesRegex(relay.RelayError, "REQUEST_IDENTITY_MISMATCH"):
                relay.service_request(
                    request_path,
                    allowed_hosts={"registry.npmjs.org"},
                    expected_agent="OTHER",
                    expected_task="SI-REAL-UBJSON-SNAPSHOT-001",
                    opener=lambda request, timeout: _Response(),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
