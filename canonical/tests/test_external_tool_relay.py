from __future__ import annotations

import base64
import hashlib
import io
import json
import pathlib
import tempfile
import unittest
import urllib.error
from unittest import mock

import canonical.runtime.external_tool_relay as relay


class FakeResponse:
    def __init__(self, raw=b'{"ok":true}', status=200, url="https://registry.npmjs.org/-/v1/search?text=ubj&size=40"):
        self._raw = io.BytesIO(raw)
        self.status = status
        self._url = url
        self.headers = {"content-type": "application/json"}

    def read(self, n=-1):
        return self._raw.read(n)

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def make_request(path: pathlib.Path, *, url="https://registry.npmjs.org/-/v1/search?text=ubj&size=40"):
    request = {
        "schema": relay.REQUEST_SCHEMA,
        "kind": "urlopen",
        "agent_id": "SUPERWORKER-UNIFIED-1",
        "task_id": "SI-REAL-UBJSON-SNAPSHOT-001",
        "payload": {
            "url": url,
            "method": "GET",
            "headers": {"User-agent": "ProjectBrain-Test/1"},
            "timeout_s": 20,
            "data_b64": None,
        },
    }
    canonical = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    request["request_sha256"] = sha
    target = path / f"{sha}.request.json"
    target.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target, sha


class ExternalToolRelayTests(unittest.TestCase):
    def test_services_bound_npm_request(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            request_path, sha = make_request(root)

            def opener(req, timeout):
                self.assertEqual(req.full_url, "https://registry.npmjs.org/-/v1/search?text=ubj&size=40")
                self.assertEqual(timeout, 20)
                return FakeResponse()

            response_path = relay.service_request(
                request_path,
                allowed_hosts={"registry.npmjs.org"},
                opener=opener,
            )
            response = json.loads(response_path.read_text())
            self.assertEqual(response["schema"], relay.RESPONSE_SCHEMA)
            self.assertEqual(response["request_sha256"], sha)
            self.assertEqual(response["agent_id"], "SUPERWORKER-UNIFIED-1")
            self.assertEqual(response["task_id"], "SI-REAL-UBJSON-SNAPSHOT-001")
            self.assertEqual(response["status"], "ok")
            self.assertEqual(base64.b64decode(response["result"]["body_b64"]), b'{"ok":true}')

    def test_rejects_request_hash_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            request_path, _ = make_request(root)
            value = json.loads(request_path.read_text())
            value["payload"]["url"] = "https://registry.npmjs.org/tampered"
            request_path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(relay.RelayError, "REQUEST_SHA256_MISMATCH"):
                relay.service_request(
                    request_path,
                    allowed_hosts={"registry.npmjs.org"},
                    opener=lambda *_a, **_k: FakeResponse(),
                )

    def test_rejects_non_allowlisted_host(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            request_path, _ = make_request(root, url="https://example.com/")
            with self.assertRaisesRegex(relay.RelayError, "URL_HOST_FORBIDDEN"):
                relay.service_request(
                    request_path,
                    allowed_hosts={"registry.npmjs.org"},
                    opener=lambda *_a, **_k: FakeResponse(),
                )

    def test_existing_response_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            request_path, sha = make_request(root)
            response_path = root / f"{sha}.response.json"
            existing = {
                "schema": relay.RESPONSE_SCHEMA,
                "request_sha256": sha,
                "kind": "urlopen",
                "agent_id": "SUPERWORKER-UNIFIED-1",
                "task_id": "SI-REAL-UBJSON-SNAPSHOT-001",
                "status": "ok",
                "result": {"sentinel": True},
            }
            response_path.write_text(json.dumps(existing), encoding="utf-8")
            opener = mock.Mock(side_effect=AssertionError("network should not be called"))
            observed = relay.service_request(
                request_path,
                allowed_hosts={"registry.npmjs.org"},
                opener=opener,
            )
            self.assertEqual(observed, response_path)
            self.assertEqual(json.loads(response_path.read_text()), existing)
            opener.assert_not_called()

    def test_http_404_is_returned_as_bridge_observation(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            request_path, _ = make_request(root, url="https://pypi.org/pypi/definitely-missing-project/json")

            def opener(req, timeout):
                raise urllib.error.HTTPError(
                    req.full_url,
                    404,
                    "Not Found",
                    {"content-type": "application/json"},
                    io.BytesIO(b'{"message":"Not Found"}'),
                )

            response_path = relay.service_request(
                request_path,
                allowed_hosts={"pypi.org"},
                opener=opener,
            )
            response = json.loads(response_path.read_text())
            self.assertEqual(response["status"], "ok")
            self.assertEqual(response["result"]["status"], 404)
            self.assertEqual(
                base64.b64decode(response["result"]["body_b64"]),
                b'{"message":"Not Found"}',
            )

    def test_pending_unsupported_kind_is_left_for_next_causal_frontier(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            request = {
                "schema": relay.REQUEST_SCHEMA,
                "kind": "python_source_tree",
                "agent_id": "SUPERWORKER-UNIFIED-1",
                "task_id": "SI-REAL-UBJSON-SNAPSHOT-001",
                "payload": {"effect": "structured.binary.encode", "ecosystem": "pypi"},
            }
            canonical = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            request["request_sha256"] = sha
            path = root / f"{sha}.request.json"
            path.write_text(json.dumps(request), encoding="utf-8")
            observed = relay.service_pending(
                root,
                allowed_hosts={"pypi.org"},
                opener=mock.Mock(side_effect=AssertionError("network should not be called")),
            )
            self.assertEqual(observed, [])
            self.assertFalse((root / f"{sha}.response.json").exists())

    def test_services_pypi_package_name_search_without_returning_simple_index(self):
        request = {
            "payload": {
                "ecosystem": "pypi",
                "tokens": ["ubj"],
                "limit": 10,
                "timeout_s": 12,
            }
        }

        def opener(req, timeout):
            self.assertEqual(req.full_url, "https://pypi.org/search/?q=ubj")
            self.assertEqual(timeout, 12)
            return FakeResponse(
                raw=b'<a href="/project/py-ubjson/">py-ubjson</a><a href="/project/another-ubj/">another-ubj</a>',
                url=req.full_url,
            )

        observed = relay._service_package_name_search(request, opener=opener)
        self.assertEqual(observed["source"], "PYPI_SEARCH")
        self.assertEqual(observed["names"], ["py-ubjson", "another-ubj"])


if __name__ == "__main__":
    unittest.main()
