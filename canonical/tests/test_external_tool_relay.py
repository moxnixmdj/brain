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


    @mock.patch.object(relay, "_source_tree_from_repo")
    @mock.patch.object(relay, "_github_api_json")
    def test_services_bounded_python_source_tree_request(self, github_json, source_tree):
        github_json.return_value = {"items": [{"full_name": "NeuroJSON/pybj"}]}
        source_tree.return_value = {
            "schema": "PROJECT_BRAIN_EXTERNAL_SOURCE_TREE_V1",
            "repository": "NeuroJSON/pybj",
            "revision": "a" * 40,
            "files": [{
                "path": "bjdata/__init__.py",
                "git_blob_sha": "b" * 40,
                "content": "def dumpb(x): return b'x'\n",
            }],
        }
        result = relay.execute_python_source_tree({
            "goal": "Encode input as UBJSON and save output.ubj",
            "allowed_suffixes": [".py"],
            "max_files_per_tree": 128,
            "max_total_bytes_per_tree": 2000000,
            "max_trees": 12,
            "require_git_blob_sha": True,
        })
        self.assertEqual(len(result["trees"]), 1)
        self.assertEqual(result["trees"][0]["repository"], "NeuroJSON/pybj")
        source_tree.assert_called_once()



    @mock.patch.object(
        relay,
        "execute_npm_package_closure",
        side_effect=relay.RelayError("NPM_CLOSURE_PACKAGE_COUNT_LIMIT"),
    )
    def test_candidate_level_relay_failure_becomes_bound_error_response(self, _mocked):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            request = {
                "schema": relay.REQUEST_SCHEMA,
                "kind": "npm_package_closure",
                "agent_id": "SUPERWORKER-UNIFIED-1",
                "task_id": "SI-REAL-UBJSON-SNAPSHOT-001",
                "payload": {
                    "package": "jda",
                    "version": "0.4.0",
                    "max_packages": 32,
                    "max_total_bytes": 80000000,
                },
            }
            request["request_sha256"] = relay.canonical_request_sha(request)
            path = root / (request["request_sha256"] + ".request.json")
            path.write_text(json.dumps(request), encoding="utf-8")
            response_path = relay.service_request(
                path, request["agent_id"], request["task_id"]
            )
            self.assertIsNotNone(response_path)
            response = json.loads(response_path.read_text(encoding="utf-8"))
            self.assertEqual(response["status"], "error")
            self.assertEqual(response["request_sha256"], request["request_sha256"])
            self.assertIn("NPM_CLOSURE_PACKAGE_COUNT_LIMIT", response["error"])



if __name__ == "__main__":
    unittest.main()
