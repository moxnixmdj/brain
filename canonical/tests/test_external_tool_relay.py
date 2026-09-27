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

    def __init__(self, url, body=b'{"objects":[]}'):
        self.url = url
        self.body = body

    def read(self, n=-1):
        return self.body[:n] if n >= 0 else self.body

    def geturl(self):
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def make_request(kind, payload):
    req = {
        "schema": "PROJECT_BRAIN_EXTERNAL_TOOL_REQUEST_V1",
        "kind": kind,
        "agent_id": "SUPERWORKER-UNIFIED-2",
        "task_id": "SI-REAL-UBJSON-SNAPSHOT-002",
        "payload": payload,
    }
    canonical = json.dumps(req, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    req["request_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return req


class ExternalToolRelayTests(unittest.TestCase):
    def _write(self, bridge, req):
        path = bridge / (req["request_sha256"] + ".request.json")
        path.write_text(json.dumps(req), encoding="utf-8")
        return path

    def test_services_exact_hash_bound_npm_request(self):
        with tempfile.TemporaryDirectory() as td:
            bridge = pathlib.Path(td)
            url = "https://registry.npmjs.org/-/v1/search?text=ubj&size=40"
            req = make_request("urlopen", {
                "url": url, "method": "GET", "headers": {},
                "timeout_s": 20, "data_b64": None,
            })
            path = self._write(bridge, req)
            response = relay.service_request(
                path, opener=lambda *_args, **_kwargs: FakeResponse(url)
            )
            observed = json.loads(response.read_text(encoding="utf-8"))
            self.assertEqual(observed["schema"], "PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1")
            self.assertEqual(observed["request_sha256"], req["request_sha256"])
            self.assertEqual(observed["agent_id"], "SUPERWORKER-UNIFIED-2")
            self.assertEqual(observed["task_id"], "SI-REAL-UBJSON-SNAPSHOT-002")
            self.assertEqual(observed["status"], "ok")
            self.assertEqual(observed["result"]["status"], 200)

    def test_services_generic_pypi_name_search_without_hardcoded_package(self):
        with tempfile.TemporaryDirectory() as td:
            bridge = pathlib.Path(td)
            req = make_request("package_name_search", {
                "ecosystem": "pypi",
                "effect": "encode some .ubj binary",
                "limit": 5,
                "timeout_s": 12,
                "tokens": ["ubj"],
            })
            path = self._write(bridge, req)
            body = b'<a href="/simple/foo/">foo</a><a href="/simple/ubjson-x/">ubjson-x</a><a href="/simple/xubj/">xubj</a>'
            response = relay.service_request(
                path,
                opener=lambda request, **_kwargs: FakeResponse(request.full_url, body),
            )
            observed = json.loads(response.read_text(encoding="utf-8"))
            self.assertEqual(observed["result"]["names"], ["ubjson-x", "xubj"])

    def test_source_tree_request_requires_git_blob_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            bridge = pathlib.Path(td)
            req = make_request("python_source_tree", {
                "goal": "encode data",
                "mission_id": "M1",
                "max_trees": 2,
                "max_files_per_tree": 10,
                "max_total_bytes_per_tree": 10000,
                "allowed_suffixes": [".py"],
                "require_git_blob_sha": False,
            })
            path = self._write(bridge, req)
            with self.assertRaisesRegex(relay.RelayError, "SOURCE_TREE_GIT_BLOB_REQUIRED"):
                relay.service_request(path)

    def test_rejects_unapproved_http_host(self):
        with tempfile.TemporaryDirectory() as td:
            bridge = pathlib.Path(td)
            req = make_request("urlopen", {
                "url": "https://example.com/", "method": "GET", "headers": {},
                "timeout_s": 20, "data_b64": None,
            })
            path = self._write(bridge, req)
            with self.assertRaisesRegex(relay.RelayError, "URL_HOST_FORBIDDEN"):
                relay.service_request(
                    path,
                    opener=lambda *_args, **_kwargs: FakeResponse("https://example.com/"),
                )

    def test_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            bridge = pathlib.Path(td)
            url = "https://registry.npmjs.org/-/v1/search?text=ubj&size=40"
            req = make_request("urlopen", {
                "url": url, "method": "GET", "headers": {},
                "timeout_s": 20, "data_b64": None,
            })
            req["payload"]["url"] = "https://registry.npmjs.org/-/v1/search?text=changed&size=40"
            path = self._write(bridge, req)
            with self.assertRaisesRegex(relay.RelayError, "REQUEST_HASH_MISMATCH"):
                relay.service_request(
                    path,
                    opener=lambda *_args, **_kwargs: FakeResponse(url),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
