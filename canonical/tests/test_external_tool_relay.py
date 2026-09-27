#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import pathlib
import tempfile
import unittest

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME = CANONICAL_ROOT / "runtime"
spec = importlib.util.spec_from_file_location("external_tool_relay_target", RUNTIME / "external_tool_relay.py")
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)


class FakeResponse:
    status = 200
    headers = {"content-type": "application/json"}

    def __init__(self, body=b'{"objects":[]}'):
        self.body = body

    def read(self, n=-1):
        return self.body[:n] if n >= 0 else self.body

    def geturl(self):
        return "https://registry.npmjs.org/-/v1/search?text=ubj&size=40"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def make_request(url):
    req = {
        "schema": "PROJECT_BRAIN_EXTERNAL_TOOL_REQUEST_V1",
        "kind": "urlopen",
        "agent_id": "SUPERWORKER-UNIFIED-2",
        "task_id": "SI-REAL-UBJSON-SNAPSHOT-002",
        "payload": {
            "url": url,
            "method": "GET",
            "headers": {},
            "timeout_s": 20,
            "data_b64": None,
        },
    }
    canonical = json.dumps(req, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    req["request_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return req


class ExternalToolRelayTests(unittest.TestCase):
    def test_services_exact_hash_bound_npm_request(self):
        with tempfile.TemporaryDirectory() as td:
            bridge = pathlib.Path(td)
            req = make_request("https://registry.npmjs.org/-/v1/search?text=ubj&size=40")
            path = bridge / (req["request_sha256"] + ".request.json")
            path.write_text(json.dumps(req), encoding="utf-8")
            response = relay.service_request(path, opener=lambda *_args, **_kwargs: FakeResponse())
            observed = json.loads(response.read_text(encoding="utf-8"))
            self.assertEqual(observed["schema"], "PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1")
            self.assertEqual(observed["request_sha256"], req["request_sha256"])
            self.assertEqual(observed["agent_id"], "SUPERWORKER-UNIFIED-2")
            self.assertEqual(observed["task_id"], "SI-REAL-UBJSON-SNAPSHOT-002")
            self.assertEqual(observed["status"], "ok")
            self.assertEqual(observed["result"]["status"], 200)

    def test_rejects_non_npm_host(self):
        with tempfile.TemporaryDirectory() as td:
            bridge = pathlib.Path(td)
            req = make_request("https://example.com/")
            path = bridge / (req["request_sha256"] + ".request.json")
            path.write_text(json.dumps(req), encoding="utf-8")
            with self.assertRaisesRegex(relay.RelayError, "URL_HOST_FORBIDDEN"):
                relay.service_request(path, opener=lambda *_args, **_kwargs: FakeResponse())

    def test_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            bridge = pathlib.Path(td)
            req = make_request("https://registry.npmjs.org/-/v1/search?text=ubj&size=40")
            req["payload"]["url"] = "https://registry.npmjs.org/-/v1/search?text=changed&size=40"
            path = bridge / (req["request_sha256"] + ".request.json")
            path.write_text(json.dumps(req), encoding="utf-8")
            with self.assertRaisesRegex(relay.RelayError, "REQUEST_HASH_MISMATCH"):
                relay.service_request(path, opener=lambda *_args, **_kwargs: FakeResponse())


if __name__ == "__main__":
    unittest.main(verbosity=2)
