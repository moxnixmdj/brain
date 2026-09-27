#!/usr/bin/env python3
"""Strict executor for Project Brain external-tool bridge requests.

This process is deliberately separate from ASTRA. It services only requests
already materialized by the content-addressed bridge and writes responses bound
to the exact request hash + durable agent/task identity.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import ipaddress
import json
import pathlib
import socket
import tempfile
import urllib.error
import urllib.parse
import urllib.request


REQUEST_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_REQUEST_V1"
RESPONSE_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1"
ALLOWED_KINDS = {"urlopen"}
ALLOWED_METHODS = {"GET", "HEAD"}
SAFE_REQUEST_HEADERS = {"user-agent", "accept", "accept-encoding"}


class RelayError(RuntimeError):
    pass


def _canonical_request_sha(request: dict) -> str:
    canonical = dict(request)
    canonical.pop("request_sha256", None)
    raw = json.dumps(
        canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _atomic_write_json(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        temp = pathlib.Path(handle.name)
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temp.replace(path)


def _validate_public_resolution(host: str) -> None:
    # Host allowlisting is the primary authority. This secondary check blocks
    # accidental allowlisting of loopback/private/link-local destinations.
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise RelayError("DNS_RESOLUTION_FAILED:" + host) from exc
    if not infos:
        raise RelayError("DNS_RESOLUTION_EMPTY:" + host)
    for info in infos:
        raw = info[4][0]
        ip = ipaddress.ip_address(raw)
        if not ip.is_global:
            raise RelayError("NONPUBLIC_DESTINATION:" + raw)


def _validate_url(raw: str, allowed_hosts: set[str]) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(str(raw or ""))
    if parsed.scheme != "https":
        raise RelayError("HTTPS_REQUIRED")
    if parsed.username or parsed.password:
        raise RelayError("URL_CREDENTIALS_FORBIDDEN")
    if parsed.fragment:
        raise RelayError("URL_FRAGMENT_FORBIDDEN")
    host = (parsed.hostname or "").rstrip(".").lower()
    if not host or host not in allowed_hosts:
        raise RelayError("HOST_NOT_ALLOWED:" + host)
    _validate_public_resolution(host)
    return parsed


class _RestrictedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_hosts: set[str]):
        self.allowed_hosts = allowed_hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_url(newurl, self.allowed_hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_urlopen(payload: dict, allowed_hosts: set[str], max_body_bytes: int) -> dict:
    if not isinstance(payload, dict):
        raise RelayError("PAYLOAD_OBJECT_REQUIRED")
    parsed = _validate_url(payload.get("url"), allowed_hosts)
    method = str(payload.get("method") or "GET").upper()
    if method not in ALLOWED_METHODS:
        raise RelayError("METHOD_NOT_ALLOWED:" + method)
    data_b64 = payload.get("data_b64")
    if data_b64 not in (None, ""):
        raise RelayError("REQUEST_BODY_FORBIDDEN")

    raw_headers = payload.get("headers") or {}
    if not isinstance(raw_headers, dict):
        raise RelayError("HEADERS_OBJECT_REQUIRED")
    headers = {}
    for key, value in raw_headers.items():
        if str(key).lower() in SAFE_REQUEST_HEADERS:
            headers[str(key)] = str(value)[:1000]

    timeout = float(payload.get("timeout_s", 20))
    if timeout <= 0 or timeout > 60:
        raise RelayError("TIMEOUT_OUT_OF_RANGE")

    opener = urllib.request.build_opener(_RestrictedRedirect(allowed_hosts))
    request = urllib.request.Request(
        urllib.parse.urlunparse(parsed), headers=headers, method=method
    )
    try:
        response = opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        response = exc

    with response:
        body = b"" if method == "HEAD" else response.read(max_body_bytes + 1)
        if len(body) > max_body_bytes:
            raise RelayError("RESPONSE_TOO_LARGE")
        final_url = response.geturl()
        _validate_url(final_url, allowed_hosts)
        response_headers = {
            str(k): str(v)[:4000]
            for k, v in response.headers.items()
            if str(k).lower() in {
                "content-type", "content-length", "content-encoding",
                "etag", "last-modified", "cache-control"
            }
        }
        return {
            "status": int(response.status),
            "final_url": str(final_url),
            "headers": response_headers,
            "body_b64": base64.b64encode(body).decode("ascii"),
        }


def service_request(
    request_path: pathlib.Path,
    *,
    allowed_hosts: set[str],
    agent_id: str,
    task_id: str,
    max_body_bytes: int,
    fetcher=fetch_urlopen,
) -> dict:
    request_path = request_path.resolve()
    if not request_path.is_file() or not request_path.name.endswith(".request.json"):
        raise RelayError("REQUEST_FILE_INVALID")
    request = json.loads(request_path.read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise RelayError("REQUEST_OBJECT_REQUIRED")
    if request.get("schema") != REQUEST_SCHEMA:
        raise RelayError("REQUEST_SCHEMA_INVALID")
    if request.get("kind") not in ALLOWED_KINDS:
        raise RelayError("REQUEST_KIND_NOT_ALLOWED:" + str(request.get("kind")))
    if request.get("agent_id") != agent_id or request.get("task_id") != task_id:
        raise RelayError("REQUEST_IDENTITY_MISMATCH")

    supplied = str(request.get("request_sha256") or "").lower()
    computed = _canonical_request_sha(request)
    if supplied != computed:
        raise RelayError("REQUEST_HASH_MISMATCH")
    if request_path.name != supplied + ".request.json":
        raise RelayError("REQUEST_FILENAME_HASH_MISMATCH")

    response_path = request_path.with_name(supplied + ".response.json")
    if response_path.exists():
        existing = json.loads(response_path.read_text(encoding="utf-8"))
        if (
            existing.get("schema") != RESPONSE_SCHEMA
            or existing.get("request_sha256") != supplied
            or existing.get("kind") != request.get("kind")
            or existing.get("agent_id") != agent_id
            or existing.get("task_id") != task_id
        ):
            raise RelayError("EXISTING_RESPONSE_BINDING_INVALID")
        return {"status": "ALREADY_RESPONDED", "request_sha256": supplied}

    result = fetcher(request.get("payload"), allowed_hosts, max_body_bytes)
    if not isinstance(result, dict):
        raise RelayError("FETCH_RESULT_OBJECT_REQUIRED")
    response = {
        "schema": RESPONSE_SCHEMA,
        "request_sha256": supplied,
        "kind": request["kind"],
        "agent_id": agent_id,
        "task_id": task_id,
        "status": "ok",
        "result": result,
    }
    _atomic_write_json(response_path, response)
    return {
        "status": "RESPONDED",
        "request_sha256": supplied,
        "response_path": str(response_path),
    }


def service_pending(
    bridge_dir: pathlib.Path,
    *,
    allowed_hosts: set[str],
    agent_id: str,
    task_id: str,
    max_body_bytes: int,
) -> dict:
    bridge_dir = bridge_dir.resolve()
    bridge_dir.mkdir(parents=True, exist_ok=True)
    serviced = []
    for path in sorted(bridge_dir.glob("*.request.json")):
        response = path.with_name(path.name.replace(".request.json", ".response.json"))
        if response.exists():
            continue
        serviced.append(service_request(
            path,
            allowed_hosts=allowed_hosts,
            agent_id=agent_id,
            task_id=task_id,
            max_body_bytes=max_body_bytes,
        ))
    return {"pending_serviced": len(serviced), "responses": serviced}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-dir", required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--allow-host", action="append", required=True)
    parser.add_argument("--max-body-bytes", type=int, default=50_000_000)
    args = parser.parse_args()

    hosts = {str(h).rstrip(".").lower() for h in args.allow_host if str(h).strip()}
    if not hosts:
        raise RelayError("ALLOW_HOST_REQUIRED")
    if args.max_body_bytes <= 0 or args.max_body_bytes > 100_000_000:
        raise RelayError("MAX_BODY_BYTES_OUT_OF_RANGE")

    result = service_pending(
        pathlib.Path(args.bridge_dir),
        allowed_hosts=hosts,
        agent_id=args.agent_id,
        task_id=args.task_id,
        max_body_bytes=args.max_body_bytes,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
