import hashlib
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from canonical.runtime import external_tool_relay as relay


class FakeResponse:
    status = 200
    headers = {"Content-Type": "application/json"}
    def __init__(self, raw=b'{"objects":[]}'):
        self.raw = raw
    def read(self, _n=-1):
        return self.raw
    def geturl(self):
        return "https://registry.npmjs.org/-/v1/search?text=ubj&size=40"
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return False


class RelayTests(unittest.TestCase):
    def _request(self):
        request = {
            "schema": relay.REQUEST_SCHEMA,
            "kind": "urlopen",
            "agent_id": "SUPERWORKER-UNIFIED-1",
            "task_id": "SI-REAL-UBJSON-SNAPSHOT-001",
            "payload": {
                "url": "https://registry.npmjs.org/-/v1/search?text=ubj&size=40",
                "method": "GET",
                "headers": {"User-Agent": "test", "Authorization": "must-not-pass"},
                "timeout_s": 20,
                "data_b64": None,
            },
        }
        request["request_sha256"] = relay.canonical_request_sha(request)
        return request

    @mock.patch("urllib.request.urlopen", return_value=FakeResponse())
    def test_services_hash_bound_identity_bound_request(self, mocked):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            req = self._request()
            sha = req["request_sha256"]
            p = root / f"{sha}.request.json"
            p.write_text(json.dumps(req), encoding="utf-8")
            written = relay.service_pending(root, req["agent_id"], req["task_id"])
            self.assertEqual(written, [f"{sha}.response.json"])
            response = json.loads((root / written[0]).read_text())
            self.assertEqual(response["request_sha256"], sha)
            self.assertEqual(response["result"]["body_sha256"], hashlib.sha256(b'{"objects":[]}').hexdigest())
            sent = mocked.call_args.args[0]
            self.assertNotIn("Authorization", dict(sent.header_items()))

    def test_rejects_identity_mismatch(self):
        req = self._request()
        with self.assertRaisesRegex(relay.RelayError, "REQUEST_IDENTITY_MISMATCH"):
            relay.validate_request(req, "OTHER", req["task_id"])

    def test_rejects_non_npm_host(self):
        payload = self._request()["payload"] | {"url": "https://example.com/"}
        with self.assertRaisesRegex(relay.RelayError, "URL_NOT_ALLOWED"):
            relay.execute_urlopen(payload)


if __name__ == "__main__":
    unittest.main()
