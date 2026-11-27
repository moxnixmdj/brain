"""A service that is not running is information, not an exception.

Measured on a real benchmark trial: the engine classified a repo gap as an HTTP API to
probe, probed `http://localhost:…/openapi.json`, nothing was listening, and the resulting
`URLError: [Errno 111] Connection refused` propagated out of the acquisition layer and
aborted the solve. The trial scored 0 and the 0 was about our plumbing.

The law this pins: transport failure (refused, timeout, unresolvable host) from an
environment probe returns a structured `unreachable` observation with status 0, so the
gap stays open and the rest of the solve continues. A response — even a 404 or a 500 — is
still returned as a response, because that IS evidence about the service.
"""
from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from canonical.runtime.epistemic_scan_acquire_compress_v1 import _http_json_request


def _closed_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - stdlib signature
        body = json.dumps({"paths": {"/login": {}, "/items": {}}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        self.send_response(401)
        self.end_headers()
        self.wfile.write(b'{"detail":"no token"}')

    def log_message(self, *a):  # silence
        return


def _serve() -> tuple[HTTPServer, str]:
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def test_connection_refused_is_an_observation_not_a_raise() -> None:
    port = _closed_port()
    code, body = _http_json_request(f"http://127.0.0.1:{port}/openapi.json", timeout_s=2.0)
    assert code == 0, body
    assert body["error"] == "unreachable"
    assert "url" in body and "reason" in body
    # and the refusal reason survives, so a reader can tell refused from unresolvable
    assert "refused" in str(body["reason"]).lower() or "timed out" in str(body["reason"]).lower()


def test_unresolvable_host_is_the_same_kind_of_fact() -> None:
    code, body = _http_json_request("http://no-such-host-xyz.invalid/openapi.json", timeout_s=3.0)
    assert code == 0 and body["error"] == "unreachable", body


def test_a_real_response_is_still_a_real_response() -> None:
    """The fix must not swallow evidence: status and parsed body come back untouched."""
    srv, base = _serve()
    try:
        code, body = _http_json_request(base + "/openapi.json", timeout_s=3.0)
        assert code == 200, body
        assert "paths" in body and "/login" in body["paths"]
        # 401 is a response, not unreachability: the auth probe learns something here
        c2, b2 = _http_json_request(base + "/token", method="POST", payload={"a": 1}, timeout_s=3.0)
        assert c2 == 401 and b2 == {"detail": "no token"}, (c2, b2)
    finally:
        srv.shutdown()
        srv.server_close()


def test_the_solver_callers_survive_an_unreachable_probe() -> None:
    """`code, body = _http_json_request(...)` at the auth-probe call sites must not crash on 0."""
    port = _closed_port()
    for base in (f"http://127.0.0.1:{port}", f"http://127.0.0.1:{port}/api"):
        code, body = _http_json_request(base + "/token", method="POST", payload={"grant_type": "x"}, timeout_s=2.0)
        assert isinstance(code, int) and isinstance(body, dict)
        assert code not in (200, 201)  # so a caller gating on those takes its no-token path


def test_a_bare_oserror_from_the_transport_is_also_a_fact(monkeypatch) -> None:
    """Some failures surface as raw OSError (e.g. a reset mid-request), not URLError."""
    import urllib.request as ur

    from canonical.runtime import epistemic_scan_acquire_compress_v1 as esac

    def boom(*a, **k):
        raise OSError("connection reset by peer")

    monkeypatch.setattr(ur, "urlopen", boom)
    code, body = esac._http_json_request("http://127.0.0.1:1/x", timeout_s=1.0)
    assert code == 0 and body["error"] == "unreachable"
    assert "reset" in body["reason"]
