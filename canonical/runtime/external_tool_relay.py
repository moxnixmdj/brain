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
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

REQUEST_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_REQUEST_V1"
RESPONSE_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1"
DEFAULT_ALLOWED_HOSTS = (
    "registry.npmjs.org",
    "registry.modelcontextprotocol.io",
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
    try:
        response = opener(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        # HTTP errors are valid external observations. Return them through the
        # bridge so the network-isolated worker sees the same urllib semantics.
        response = exc
    try:
        raw = response.read(max_body_bytes + 1)
        if len(raw) > max_body_bytes:
            raise RelayError("RESPONSE_TOO_LARGE")
        status = int(getattr(response, "status", getattr(response, "code", 200)))
        final_url = str(response.geturl())
        _allowed_url(final_url, allowed_hosts)
        response_headers = dict(getattr(response, "headers", {}) or {})
    finally:
        close = getattr(response, "close", None)
        if callable(close):
            close()
    return {
        "status": status,
        "final_url": final_url,
        "headers": {str(k): str(v) for k, v in response_headers.items()},
        "body_b64": base64.b64encode(raw).decode("ascii"),
    }


def _service_package_name_search(
    request: dict[str, Any],
    *,
    opener=urllib.request.urlopen,
) -> dict[str, Any]:
    payload = request.get("payload")
    if not isinstance(payload, dict):
        raise RelayError("PAYLOAD_INVALID")
    ecosystem = str(payload.get("ecosystem") or "").strip().lower()
    tokens = [
        str(x).strip().lower()
        for x in (payload.get("tokens") or [])
        if str(x).strip()
    ]
    limit = int(payload.get("limit", 32))
    timeout = float(payload.get("timeout_s", 20))
    if not tokens or limit < 1 or limit > 100 or not (0 < timeout <= 60):
        raise RelayError("PACKAGE_SEARCH_INPUT_INVALID")

    if ecosystem == "npm":
        query = urllib.parse.quote(" ".join(tokens), safe="")
        url = f"https://registry.npmjs.org/-/v1/search?text={query}&size={min(limit, 100)}"
        req = urllib.request.Request(url, headers={"User-Agent": "ProjectBrain-ExternalRelay/1"})
        with opener(req, timeout=timeout) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise RelayError("PACKAGE_SEARCH_RESPONSE_TOO_LARGE")
        payload_json = json.loads(raw.decode("utf-8"))
        names = []
        for item in payload_json.get("objects") or []:
            package = (item or {}).get("package") or {}
            name = str(package.get("name") or "").strip()
            if name and name not in names:
                names.append(name)
        return {"names": names[:limit], "source": "NPM_REGISTRY_SEARCH"}

    if ecosystem != "pypi":
        raise RelayError("PACKAGE_SEARCH_ECOSYSTEM_UNSUPPORTED:" + ecosystem)

    query = urllib.parse.quote(" ".join(tokens), safe="")
    search_url = f"https://pypi.org/search/?q={query}"
    req = urllib.request.Request(
        search_url,
        headers={"User-Agent": "ProjectBrain-ExternalRelay/1", "Accept-Encoding": "identity"},
    )
    try:
        with opener(req, timeout=timeout) as response:
            raw = response.read(2_000_001)
    except urllib.error.HTTPError as exc:
        raw = exc.read(2_000_001)
    if len(raw) > 2_000_000:
        raise RelayError("PACKAGE_SEARCH_RESPONSE_TOO_LARGE")
    text = raw.decode("utf-8", "replace")
    names = []
    for match in re.finditer(r'href=["\\\']/project/([^/"\\\']+)/', text, re.I):
        name = urllib.parse.unquote(match.group(1)).strip()
        if name and name not in names:
            names.append(name)
    if names:
        return {"names": names[:limit], "source": "PYPI_SEARCH"}

    # PyPI search may present an anti-bot page. Fall back to a bounded scan of
    # the authoritative Simple index, but return only the tiny matched name set.
    req = urllib.request.Request(
        "https://pypi.org/simple/",
        headers={"User-Agent": "ProjectBrain-ExternalRelay/1", "Accept-Encoding": "identity"},
    )
    with opener(req, timeout=min(timeout, 60)) as response:
        raw = response.read(64 * 1024 * 1024 + 1)
    if len(raw) > 64 * 1024 * 1024:
        raise RelayError("PYPI_SIMPLE_INDEX_TOO_LARGE")
    text = raw.decode("utf-8", "replace")
    candidates = []
    for match in re.finditer(r">([^<>]+)</a>", text, re.I):
        name = match.group(1).strip()
        low = name.lower()
        score = max((len(t) for t in tokens if t in low), default=0)
        if score:
            candidates.append((-score, len(name), low, name))
    candidates.sort()
    for _score, _length, _low, name in candidates:
        if name not in names:
            names.append(name)
        if len(names) >= limit:
            break
    return {"names": names, "source": "PYPI_SIMPLE_BOUNDED_MATCH"}


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
    if kind not in {"urlopen", "package_name_search"}:
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

    if kind == "urlopen":
        result = _service_urlopen(
            request,
            allowed_hosts=allowed_hosts,
            opener=opener,
            max_body_bytes=max_body_bytes,
        )
    else:
        result = _service_package_name_search(request, opener=opener)
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
        request = _read_json(request_path)
        # Service only relay kinds implemented here. Leave other pending kinds
        # untouched so the mission can prove whether they are actually causal.
        if request.get("kind") not in {"urlopen", "package_name_search"}:
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
