#!/usr/bin/env python3
"""Service bounded Project Brain external-tool bridge requests.

This process is intentionally outside the network-constrained ASTRA runtime.
It validates request identity/hash, permits only explicit public HTTPS hosts,
executes one bounded GET, and writes the exact bridge response schema.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import ipaddress
import json
import os
import pathlib
import socket
import tempfile
import urllib.parse
import urllib.request

REQUEST_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_REQUEST_V1"
RESPONSE_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1"
DEFAULT_MAX_BYTES = 25_000_000
DENIED_HEADERS = {"authorization", "cookie", "proxy-authorization"}


class RelayError(RuntimeError):
    pass


def _canonical_request_hash(req: dict) -> str:
    body = dict(req)
    body.pop("request_sha256", None)
    canonical = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _is_public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _validate_public_host(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise RelayError("HOST_RESOLUTION_FAILED") from exc
    addresses = {info[4][0] for info in infos}
    if not addresses or any(not _is_public_ip(addr) for addr in addresses):
        raise RelayError("NON_PUBLIC_DESTINATION")


def _atomic_json(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        tmp = pathlib.Path(handle.name)
    os.replace(tmp, path)


def service_request(
    request_path: pathlib.Path,
    *,
    allowed_hosts: set[str],
    expected_agent: str,
    expected_task: str,
    max_bytes: int = DEFAULT_MAX_BYTES,
    opener=urllib.request.urlopen,
) -> dict:
    req = json.loads(request_path.read_text(encoding="utf-8"))
    if req.get("schema") != REQUEST_SCHEMA:
        raise RelayError("REQUEST_SCHEMA_INVALID")
    request_sha = str(req.get("request_sha256") or "")
    if request_sha != _canonical_request_hash(req):
        raise RelayError("REQUEST_HASH_MISMATCH")
    if request_path.name != request_sha + ".request.json":
        raise RelayError("REQUEST_FILENAME_MISMATCH")
    if req.get("agent_id") != expected_agent or req.get("task_id") != expected_task:
        raise RelayError("REQUEST_IDENTITY_MISMATCH")
    if req.get("kind") != "urlopen":
        raise RelayError("REQUEST_KIND_NOT_ALLOWED")

    payload = req.get("payload")
    if not isinstance(payload, dict):
        raise RelayError("REQUEST_PAYLOAD_INVALID")
    if str(payload.get("method") or "GET").upper() != "GET":
        raise RelayError("HTTP_METHOD_NOT_ALLOWED")
    if payload.get("data_b64") not in (None, ""):
        raise RelayError("REQUEST_BODY_NOT_ALLOWED")

    url = str(payload.get("url") or "")
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host or host not in allowed_hosts:
        raise RelayError("DESTINATION_NOT_ALLOWED")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise RelayError("DESTINATION_AUTH_OR_PORT_NOT_ALLOWED")
    _validate_public_host(host)

    headers = {
        str(k): str(v)
        for k, v in dict(payload.get("headers") or {}).items()
        if str(k).lower() not in DENIED_HEADERS
    }
    timeout = max(1, min(int(payload.get("timeout_s") or 20), 60))
    request = urllib.request.Request(url, headers=headers, method="GET")

    with opener(request, timeout=timeout) as response:
        final_url = str(response.geturl())
        final = urllib.parse.urlsplit(final_url)
        final_host = (final.hostname or "").lower()
        if final.scheme != "https" or final_host not in allowed_hosts:
            raise RelayError("REDIRECT_DESTINATION_NOT_ALLOWED")
        _validate_public_host(final_host)

        declared = response.headers.get("Content-Length")
        if declared is not None and int(declared) > max_bytes:
            raise RelayError("RESPONSE_TOO_LARGE")
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise RelayError("RESPONSE_TOO_LARGE")

        result = {
            "status": int(getattr(response, "status", 200)),
            "final_url": final_url,
            "headers": {str(k): str(v) for k, v in response.headers.items()},
            "body_b64": base64.b64encode(raw).decode("ascii"),
        }

    return {
        "schema": RESPONSE_SCHEMA,
        "request_sha256": request_sha,
        "kind": req["kind"],
        "agent_id": req["agent_id"],
        "task_id": req["task_id"],
        "status": "ok",
        "result": result,
    }


def service_pending(
    bridge_dir: pathlib.Path,
    *,
    allowed_hosts: set[str],
    expected_agent: str,
    expected_task: str,
    max_requests: int,
    max_bytes: int,
) -> dict:
    bridge_dir.mkdir(parents=True, exist_ok=True)
    serviced = []
    for request_path in sorted(bridge_dir.glob("*.request.json")):
        request_sha = request_path.name.removesuffix(".request.json")
        response_path = bridge_dir / (request_sha + ".response.json")
        if response_path.exists():
            continue
        response = service_request(
            request_path,
            allowed_hosts=allowed_hosts,
            expected_agent=expected_agent,
            expected_task=expected_task,
            max_bytes=max_bytes,
        )
        _atomic_json(response_path, response)
        serviced.append(request_sha)
        if len(serviced) >= max_requests:
            break
    return {
        "schema": "PROJECT_BRAIN_EXTERNAL_TOOL_RELAY_RUN_V1",
        "serviced_count": len(serviced),
        "serviced_request_sha256": serviced,
        "allowed_hosts": sorted(allowed_hosts),
        "agent_id": expected_agent,
        "task_id": expected_task,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-dir", required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--allowed-host", action="append", required=True)
    parser.add_argument("--max-requests", type=int, default=16)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    args = parser.parse_args()

    allowed_hosts = {str(v).strip().lower() for v in args.allowed_host if str(v).strip()}
    if not allowed_hosts:
        raise RelayError("ALLOWED_HOST_REQUIRED")
    report = service_pending(
        pathlib.Path(args.bridge_dir),
        allowed_hosts=allowed_hosts,
        expected_agent=args.agent_id,
        expected_task=args.task_id,
        max_requests=max(1, min(args.max_requests, 64)),
        max_bytes=max(1, min(args.max_bytes, 100_000_000)),
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
