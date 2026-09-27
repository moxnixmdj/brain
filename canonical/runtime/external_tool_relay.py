#!/usr/bin/env python3
"""Bounded executor for Project Brain external-tool bridge requests.

This process is deliberately not part of ASTRA cognition. It services only
content-addressed bridge requests that match an explicit allow policy and
writes the response atomically for the same agent/task identity.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pathlib
import tempfile
import urllib.parse
import urllib.request
from typing import Any

REQUEST_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_REQUEST_V1"
RESPONSE_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1"
DEFAULT_ALLOWED_HOSTS = (
    "registry.npmjs.org",
    "pypi.org",
    "files.pythonhosted.org",
    "github.com",
    "api.github.com",
    "raw.githubusercontent.com",
    "codeload.github.com",
)
MAX_BODY_BYTES = 32 * 1024 * 1024


class RelayError(RuntimeError):
    pass


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RelayError("JSON_OBJECT_REQUIRED")
    return value


def _write_json_atomic(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def _canonical_request_sha(request: dict[str, Any]) -> str:
    bare = dict(request)
    supplied = str(bare.pop("request_sha256", "") or "")
    canonical = json.dumps(
        bare, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    computed = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if supplied != computed:
        raise RelayError("REQUEST_SHA256_MISMATCH")
    return computed


def _allowed_url(url: str, allowed_hosts: set[str]) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise RelayError("URL_SCHEME_FORBIDDEN")
    host = (parsed.hostname or "").lower()
    if host not in allowed_hosts:
        raise RelayError("URL_HOST_FORBIDDEN:" + host)
    if parsed.username or parsed.password:
        raise RelayError("URL_CREDENTIALS_FORBIDDEN")
    return parsed


def _service_urlopen(
    request: dict[str, Any],
    *,
    allowed_hosts: set[str],
    opener=urllib.request.urlopen,
    max_body_bytes: int = MAX_BODY_BYTES,
) -> dict[str, Any]:
    payload = request.get("payload")
    if not isinstance(payload, dict):
        raise RelayError("PAYLOAD_INVALID")
    url = str(payload.get("url") or "")
    _allowed_url(url, allowed_hosts)
    method = str(payload.get("method") or "GET").upper()
    if method not in {"GET", "HEAD"}:
        raise RelayError("HTTP_METHOD_FORBIDDEN:" + method)
    data_b64 = payload.get("data_b64")
    if data_b64 not in {None, ""}:
        raise RelayError("REQUEST_BODY_FORBIDDEN")
    timeout = float(payload.get("timeout_s", 20))
    if not (0 < timeout <= 60):
        raise RelayError("TIMEOUT_OUT_OF_RANGE")
    headers = payload.get("headers") or {}
    if not isinstance(headers, dict):
        raise RelayError("HEADERS_INVALID")
    safe_headers = {
        str(k): str(v)
        for k, v in headers.items()
        if str(k).lower() in {"accept", "user-agent", "accept-encoding"}
    }
    req = urllib.request.Request(url, method=method, headers=safe_headers)
    with opener(req, timeout=timeout) as response:
        raw = response.read(max_body_bytes + 1)
        if len(raw) > max_body_bytes:
            raise RelayError("RESPONSE_TOO_LARGE")
        status = int(getattr(response, "status", 200))
        final_url = str(response.geturl())
        _allowed_url(final_url, allowed_hosts)
        response_headers = dict(getattr(response, "headers", {}) or {})
    return {
        "status": status,
        "final_url": final_url,
        "headers": {str(k): str(v) for k, v in response_headers.items()},
        "body_b64": base64.b64encode(raw).decode("ascii"),
    }


def service_request(
    request_path: pathlib.Path,
    *,
    allowed_hosts: set[str],
    opener=urllib.request.urlopen,
    max_body_bytes: int = MAX_BODY_BYTES,
) -> pathlib.Path:
    request = _read_json(request_path)
    if request.get("schema") != REQUEST_SCHEMA:
        raise RelayError("REQUEST_SCHEMA_INVALID")
    request_sha = _canonical_request_sha(request)
    if request_path.name != request_sha + ".request.json":
        raise RelayError("REQUEST_FILENAME_MISMATCH")
    agent_id = request.get("agent_id")
    task_id = request.get("task_id")
    if not isinstance(agent_id, str) or not agent_id:
        raise RelayError("AGENT_ID_MISSING")
    if not isinstance(task_id, str) or not task_id:
        raise RelayError("TASK_ID_MISSING")
    kind = str(request.get("kind") or "")
    if kind != "urlopen":
        raise RelayError("KIND_FORBIDDEN:" + kind)

    response_path = request_path.with_name(request_sha + ".response.json")
    if response_path.exists():
        existing = _read_json(response_path)
        if (
            existing.get("schema") != RESPONSE_SCHEMA
            or existing.get("request_sha256") != request_sha
            or existing.get("kind") != kind
            or existing.get("agent_id") != agent_id
            or existing.get("task_id") != task_id
        ):
            raise RelayError("EXISTING_RESPONSE_BINDING_INVALID")
        return response_path

    result = _service_urlopen(
        request,
        allowed_hosts=allowed_hosts,
        opener=opener,
        max_body_bytes=max_body_bytes,
    )
    response = {
        "schema": RESPONSE_SCHEMA,
        "request_sha256": request_sha,
        "kind": kind,
        "agent_id": agent_id,
        "task_id": task_id,
        "status": "ok",
        "result": result,
    }
    _write_json_atomic(response_path, response)
    return response_path


def service_pending(
    bridge_dir: pathlib.Path,
    *,
    allowed_hosts: set[str],
    opener=urllib.request.urlopen,
    max_body_bytes: int = MAX_BODY_BYTES,
) -> list[pathlib.Path]:
    bridge_dir = bridge_dir.resolve()
    if not bridge_dir.is_dir():
        return []
    serviced: list[pathlib.Path] = []
    for request_path in sorted(bridge_dir.glob("*.request.json")):
        response_path = request_path.with_name(
            request_path.name.replace(".request.json", ".response.json")
        )
        if response_path.exists():
            continue
        serviced.append(
            service_request(
                request_path,
                allowed_hosts=allowed_hosts,
                opener=opener,
                max_body_bytes=max_body_bytes,
            )
        )
    return serviced


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-dir", required=True)
    parser.add_argument(
        "--allow-host",
        action="append",
        default=[],
        help="Exact HTTPS hostname allowed by the relay. May be repeated.",
    )
    parser.add_argument("--max-body-bytes", type=int, default=MAX_BODY_BYTES)
    args = parser.parse_args()
    allowed_hosts = {
        h.strip().lower()
        for h in (args.allow_host or list(DEFAULT_ALLOWED_HOSTS))
        if h.strip()
    }
    if not allowed_hosts:
        raise SystemExit("no allowed hosts")
    if args.max_body_bytes <= 0 or args.max_body_bytes > MAX_BODY_BYTES:
        raise SystemExit("max-body-bytes out of range")
    try:
        serviced = service_pending(
            pathlib.Path(args.bridge_dir),
            allowed_hosts=allowed_hosts,
            max_body_bytes=args.max_body_bytes,
        )
    except RelayError as exc:
        print(json.dumps({"status": "RELAY_BLOCKED", "error": str(exc)}, sort_keys=True))
        return 2
    print(
        json.dumps(
            {
                "status": "OK",
                "serviced_count": len(serviced),
                "responses": [p.name for p in serviced],
                "allowed_hosts": sorted(allowed_hosts),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
