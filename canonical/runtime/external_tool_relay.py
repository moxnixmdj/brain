#!/usr/bin/env python3
"""Bounded external-tool relay for Project Brain's content-addressed bridge.

This process is deliberately not cognition. It services already-authorized,
identity-bound bridge requests and writes hash-bound responses. Initial scope
is intentionally narrow: HTTPS GET/HEAD to the npm registry only.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pathlib
import tempfile
import urllib.error
import urllib.parse
import urllib.request

REQUEST_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_REQUEST_V1"
RESPONSE_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1"
ALLOWED_HOSTS = {"registry.npmjs.org"}
ALLOWED_METHODS = {"GET", "HEAD"}
ALLOWED_HEADERS = {"accept", "accept-encoding", "user-agent"}
MAX_BODY_BYTES = 50_000_000


class RelayError(RuntimeError):
    pass


def canonical_request_sha(request: dict) -> str:
    body = dict(request)
    body.pop("request_sha256", None)
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _validate_url(raw: str) -> str:
    parsed = urllib.parse.urlparse(str(raw))
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise RelayError("URL_NOT_ALLOWED")
    if parsed.username or parsed.password:
        raise RelayError("URL_CREDENTIALS_FORBIDDEN")
    return parsed.geturl()


def _safe_headers(raw) -> dict[str, str]:
    headers = {}
    for key, value in dict(raw or {}).items():
        name = str(key).strip().lower()
        if name in ALLOWED_HEADERS:
            headers[str(key)] = str(value)
    return headers


def validate_request(request: dict, agent_id: str, task_id: str) -> tuple[str, dict]:
    if request.get("schema") != REQUEST_SCHEMA:
        raise RelayError("REQUEST_SCHEMA_INVALID")
    if request.get("agent_id") != agent_id or request.get("task_id") != task_id:
        raise RelayError("REQUEST_IDENTITY_MISMATCH")
    expected = canonical_request_sha(request)
    supplied = str(request.get("request_sha256") or "")
    if supplied != expected:
        raise RelayError("REQUEST_HASH_MISMATCH")
    kind = str(request.get("kind") or "")
    if kind != "urlopen":
        raise RelayError("REQUEST_KIND_NOT_ALLOWED")
    payload = request.get("payload")
    if not isinstance(payload, dict):
        raise RelayError("REQUEST_PAYLOAD_INVALID")
    return supplied, payload


def execute_urlopen(payload: dict) -> dict:
    url = _validate_url(payload.get("url"))
    method = str(payload.get("method") or "GET").upper()
    if method not in ALLOWED_METHODS:
        raise RelayError("HTTP_METHOD_NOT_ALLOWED")
    data_b64 = payload.get("data_b64")
    if data_b64 not in (None, ""):
        raise RelayError("REQUEST_BODY_FORBIDDEN")
    timeout = min(max(float(payload.get("timeout_s") or 20), 1.0), 60.0)
    req = urllib.request.Request(
        url,
        method=method,
        headers=_safe_headers(payload.get("headers")),
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(MAX_BODY_BYTES + 1)
            if len(raw) > MAX_BODY_BYTES:
                raise RelayError("RESPONSE_TOO_LARGE")
            final_url = _validate_url(response.geturl())
            status = int(getattr(response, "status", 200))
            headers = dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        raw = exc.read(MAX_BODY_BYTES + 1)
        if len(raw) > MAX_BODY_BYTES:
            raise RelayError("RESPONSE_TOO_LARGE")
        final_url = _validate_url(exc.geturl())
        status = int(exc.code)
        headers = dict(exc.headers.items()) if exc.headers else {}
    return {
        "status": status,
        "final_url": final_url,
        "headers": headers,
        "body_b64": base64.b64encode(raw).decode("ascii"),
        "body_sha256": hashlib.sha256(raw).hexdigest(),
        "body_bytes": len(raw),
    }


def _write_json_atomic(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(value, fh, sort_keys=True, separators=(",", ":"))
            fh.write("\n")
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def service_request(path: pathlib.Path, agent_id: str, task_id: str) -> pathlib.Path | None:
    request = json.loads(path.read_text(encoding="utf-8"))
    request_sha, payload = validate_request(request, agent_id, task_id)
    response_path = path.with_name(request_sha + ".response.json")
    if response_path.exists():
        return None
    result = execute_urlopen(payload)
    response = {
        "schema": RESPONSE_SCHEMA,
        "request_sha256": request_sha,
        "kind": "urlopen",
        "agent_id": agent_id,
        "task_id": task_id,
        "status": "ok",
        "result": result,
    }
    _write_json_atomic(response_path, response)
    return response_path


def service_pending(bridge_dir: pathlib.Path, agent_id: str, task_id: str) -> list[str]:
    bridge_dir = bridge_dir.resolve()
    bridge_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for path in sorted(bridge_dir.glob("*.request.json")):
        response = service_request(path, agent_id, task_id)
        if response is not None:
            written.append(response.name)
    return written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-dir", required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--task-id", required=True)
    args = parser.parse_args()
    written = service_pending(pathlib.Path(args.bridge_dir), args.agent_id, args.task_id)
    print(json.dumps({"serviced": len(written), "responses": written}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
