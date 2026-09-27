#!/usr/bin/env python3
"""Bounded external-tool relay for Project Brain.

This process is intentionally separate from ASTRA. It services only already
materialized, content-addressed bridge requests and never interprets goals.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import ipaddress
import json
import pathlib
import urllib.parse
import urllib.request

REQUEST_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_REQUEST_V1"
RESPONSE_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1"
ALLOWED_KIND = "urlopen"
ALLOWED_HOSTS = {"registry.npmjs.org"}
MAX_RESPONSE_BYTES = 64 * 1024 * 1024
FORBIDDEN_REQUEST_HEADERS = {"authorization", "cookie", "proxy-authorization"}


class RelayError(RuntimeError):
    pass


def _canonical_request_sha(request: dict) -> str:
    unsigned = dict(request)
    unsigned.pop("request_sha256", None)
    canonical = json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _safe_https_url(raw: str) -> str:
    parsed = urllib.parse.urlsplit(str(raw or ""))
    if parsed.scheme.lower() != "https":
        raise RelayError("URL_SCHEME_FORBIDDEN")
    if parsed.username or parsed.password:
        raise RelayError("URL_CREDENTIALS_FORBIDDEN")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in ALLOWED_HOSTS:
        raise RelayError("URL_HOST_FORBIDDEN:" + host)
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise RelayError("IP_LITERAL_FORBIDDEN")
    return urllib.parse.urlunsplit(parsed)


def _validate_request(path: pathlib.Path) -> dict:
    request = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(request, dict) or request.get("schema") != REQUEST_SCHEMA:
        raise RelayError("REQUEST_SCHEMA_INVALID")
    if request.get("kind") != ALLOWED_KIND:
        raise RelayError("REQUEST_KIND_FORBIDDEN")
    supplied = str(request.get("request_sha256") or "")
    computed = _canonical_request_sha(request)
    if supplied != computed or path.name != supplied + ".request.json":
        raise RelayError("REQUEST_HASH_MISMATCH")
    if not request.get("agent_id") or not request.get("task_id"):
        raise RelayError("REQUEST_IDENTITY_MISSING")
    payload = request.get("payload")
    if not isinstance(payload, dict):
        raise RelayError("REQUEST_PAYLOAD_INVALID")
    method = str(payload.get("method") or "GET").upper()
    if method not in {"GET", "HEAD"}:
        raise RelayError("METHOD_FORBIDDEN:" + method)
    if payload.get("data_b64") not in {None, ""}:
        raise RelayError("REQUEST_BODY_FORBIDDEN")
    _safe_https_url(payload.get("url"))
    headers = payload.get("headers") or {}
    if not isinstance(headers, dict):
        raise RelayError("REQUEST_HEADERS_INVALID")
    if any(str(k).lower() in FORBIDDEN_REQUEST_HEADERS for k in headers):
        raise RelayError("CREDENTIAL_HEADER_FORBIDDEN")
    timeout = float(payload.get("timeout_s") or 20)
    if timeout <= 0 or timeout > 60:
        raise RelayError("TIMEOUT_OUT_OF_RANGE")
    return request


def _fetch(request: dict, opener=urllib.request.urlopen) -> dict:
    payload = request["payload"]
    url = _safe_https_url(payload["url"])
    method = str(payload.get("method") or "GET").upper()
    headers = {str(k): str(v) for k, v in (payload.get("headers") or {}).items()}
    req = urllib.request.Request(url, headers=headers, method=method)
    timeout = min(float(payload.get("timeout_s") or 20), 60.0)
    with opener(req, timeout=timeout) as response:
        final_url = _safe_https_url(response.geturl())
        status = int(getattr(response, "status", 200))
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise RelayError("RESPONSE_TOO_LARGE")
        response_headers = dict(getattr(response, "headers", {}) or {})
    return {
        "status": status,
        "final_url": final_url,
        "headers": {str(k): str(v) for k, v in response_headers.items()},
        "body_b64": base64.b64encode(raw).decode("ascii"),
    }


def service_request(path: pathlib.Path, opener=urllib.request.urlopen) -> pathlib.Path:
    request = _validate_request(path)
    request_sha = request["request_sha256"]
    response_path = path.with_name(request_sha + ".response.json")
    if response_path.exists():
        return response_path
    result = _fetch(request, opener=opener)
    response = {
        "schema": RESPONSE_SCHEMA,
        "request_sha256": request_sha,
        "kind": request["kind"],
        "agent_id": request["agent_id"],
        "task_id": request["task_id"],
        "status": "ok",
        "result": result,
    }
    temp = response_path.with_suffix(response_path.suffix + ".tmp")
    temp.write_text(json.dumps(response, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(response_path)
    return response_path


def service_pending(bridge_dir: pathlib.Path) -> dict:
    bridge_dir = bridge_dir.resolve()
    bridge_dir.mkdir(parents=True, exist_ok=True)
    serviced = []
    rejected = []
    for path in sorted(bridge_dir.glob("*.request.json")):
        response_path = path.with_name(path.name.replace(".request.json", ".response.json"))
        if response_path.exists():
            continue
        try:
            serviced.append(str(service_request(path)))
        except Exception as exc:
            rejected.append({"request": str(path), "error": type(exc).__name__ + ":" + str(exc)})
    return {"serviced": serviced, "rejected": rejected}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-dir", required=True)
    args = parser.parse_args()
    result = service_pending(pathlib.Path(args.bridge_dir))
    print(json.dumps(result, sort_keys=True))
    return 2 if result["rejected"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
