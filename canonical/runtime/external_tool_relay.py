#!/usr/bin/env python3
"""Service bounded Project Brain external-tool bridge requests.

The relay is outside the network-constrained ASTRA runtime. It validates
request identity/hash and implements only the external request contracts that
the live runtime has actually emitted.
"""
from __future__ import annotations

import argparse
import base64
import configparser
import hashlib
import io
import ipaddress
import json
import os
import pathlib
import re
import socket
import subprocess
import tarfile
import tempfile
import urllib.parse
import urllib.request

REQUEST_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_REQUEST_V1"
RESPONSE_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1"
DEFAULT_MAX_BYTES = 25_000_000
DENIED_HEADERS = {"authorization", "cookie", "proxy-authorization"}
GITHUB_API_HOST = "api.github.com"


class RelayError(RuntimeError):
    pass


def _canonical_request_hash(req: dict) -> str:
    body = dict(req)
    body.pop("request_sha256", None)
    canonical = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


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


def _read_bounded(response, max_bytes: int) -> bytes:
    declared = response.headers.get("Content-Length")
    if declared is not None:
        try:
            if int(declared) > max_bytes:
                raise RelayError("RESPONSE_TOO_LARGE")
        except ValueError:
            pass
    raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise RelayError("RESPONSE_TOO_LARGE")
    return raw


def _service_urlopen(payload: dict, *, allowed_hosts: set[str], max_bytes: int, opener) -> dict:
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
    try:
        response = opener(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        response = exc

    with response:
        final_url = str(response.geturl())
        final = urllib.parse.urlsplit(final_url)
        final_host = (final.hostname or "").lower()
        if final.scheme != "https" or final_host not in allowed_hosts:
            raise RelayError("REDIRECT_DESTINATION_NOT_ALLOWED")
        _validate_public_host(final_host)
        raw = _read_bounded(response, max_bytes)
        status = int(getattr(response, "status", getattr(response, "code", 200)))
        return {
            "status": status,
            "final_url": final_url,
            "headers": {str(k): str(v) for k, v in response.headers.items()},
            "body_b64": base64.b64encode(raw).decode("ascii"),
        }


def _format_hint(text: str) -> str:
    text = str(text or "")
    match = re.search(r"\bas\s+([A-Za-z][A-Za-z0-9._+-]{1,40})\b", text, re.I)
    if match:
        return match.group(1).lower()
    match = re.search(r"\.([A-Za-z][A-Za-z0-9]{1,12})\b", text)
    return match.group(1).lower() if match else ""


def _github_headers() -> dict[str, str]:
    headers = {
        "User-Agent": "ProjectBrain-ExternalRelay/1",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = str(os.environ.get("GITHUB_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = "Bearer " + token
    return headers


def _github_json(url: str, timeout: int = 20) -> dict:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != GITHUB_API_HOST:
        raise RelayError("GITHUB_API_URL_INVALID")
    _validate_public_host(GITHUB_API_HOST)
    req = urllib.request.Request(url, headers=_github_headers(), method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = _read_bounded(response, 4_000_000)
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise RelayError("GITHUB_API_JSON_INVALID")
    return value


def _github_bytes(url: str, max_bytes: int, timeout: int = 45) -> bytes:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != GITHUB_API_HOST:
        raise RelayError("GITHUB_API_URL_INVALID")
    _validate_public_host(GITHUB_API_HOST)
    req = urllib.request.Request(url, headers=_github_headers(), method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        final = urllib.parse.urlsplit(str(response.geturl()))
        if final.scheme != "https" or (final.hostname or "").lower() not in {
            "api.github.com", "codeload.github.com"
        }:
            raise RelayError("GITHUB_REDIRECT_INVALID")
        _validate_public_host((final.hostname or "").lower())
        return _read_bounded(response, max_bytes)


def _github_repo_candidates(hint: str, limit: int = 8) -> list[str]:
    hint = re.sub(r"[^A-Za-z0-9+._-]+", " ", str(hint or "")).strip()
    if not hint:
        return []
    repos = []
    queries = [f"{hint} language:Python", f"{hint} python"]
    for query in queries:
        encoded = urllib.parse.quote(query)
        urls = [
            f"https://api.github.com/search/code?q={encoded}&per_page=20",
            f"https://api.github.com/search/repositories?q={encoded}&sort=stars&order=desc&per_page=20",
        ]
        for url in urls:
            try:
                data = _github_json(url)
            except Exception:
                continue
            for item in data.get("items") or []:
                repo = item.get("repository") if isinstance(item, dict) else None
                if not isinstance(repo, dict):
                    repo = item if isinstance(item, dict) else {}
                full = str(repo.get("full_name") or "").strip()
                if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", full) and full not in repos:
                    repos.append(full)
                    if len(repos) >= limit:
                        return repos
    return repos


def _top_level_python_packages(members: list[tuple[str, bytes]]) -> list[tuple[str, list[tuple[str, bytes]]]]:
    init_dirs = []
    for path, raw in members:
        p = pathlib.PurePosixPath(path)
        if p.name == "__init__.py":
            init_dirs.append(p.parent)
    init_dirs.sort(key=lambda p: (len(p.parts), str(p)))
    roots = []
    for candidate in init_dirs:
        if any(candidate == root or root in candidate.parents for root in roots):
            continue
        roots.append(candidate)

    out = []
    for root in roots:
        files = []
        for path, raw in members:
            p = pathlib.PurePosixPath(path)
            if root == p.parent or root in p.parents:
                rel = pathlib.PurePosixPath(root.name) / p.relative_to(root)
                files.append((rel.as_posix(), raw))
        if any(path == root.name + "/__init__.py" for path, _ in files):
            out.append((root.name, files))
    return out


def _source_trees_from_repo(full_name: str, max_files: int, max_total: int) -> list[dict]:
    repo_url = "https://api.github.com/repos/" + full_name
    meta = _github_json(repo_url)
    default_branch = str(meta.get("default_branch") or "").strip()
    if not default_branch:
        return []
    commit = _github_json(repo_url + "/commits/" + urllib.parse.quote(default_branch, safe=""))
    revision = str(commit.get("sha") or "").lower()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        return []

    archive = _github_bytes(repo_url + "/tarball/" + revision, max(8_000_000, max_total * 4))
    members = []
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as tar:
        for member in tar:
            if not member.isfile() or member.size > max_total:
                continue
            p = pathlib.PurePosixPath(member.name)
            if p.is_absolute() or ".." in p.parts or len(p.parts) < 2:
                continue
            rel = pathlib.PurePosixPath(*p.parts[1:])
            if rel.suffix != ".py":
                continue
            lowered = {part.lower() for part in rel.parts}
            if lowered & {"tests", "test", "docs", "doc", "examples", "example", "benchmarks"}:
                continue
            handle = tar.extractfile(member)
            if handle is None:
                continue
            raw = handle.read(max_total + 1)
            if len(raw) > max_total:
                continue
            try:
                raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            members.append((rel.as_posix(), raw))

    trees = []
    for package, files in _top_level_python_packages(members):
        if not files or len(files) > max_files:
            continue
        total = sum(len(raw) for _, raw in files)
        if total > max_total:
            continue
        records = [
            {
                "path": path,
                "git_blob_sha": _git_blob_sha(raw),
                "content": raw.decode("utf-8"),
            }
            for path, raw in sorted(files)
        ]
        trees.append(
            {
                "schema": "PROJECT_BRAIN_EXTERNAL_SOURCE_TREE_V1",
                "repository": full_name,
                "revision": revision,
                "package": package,
                "files": records,
            }
        )
    return trees


def _service_python_source_tree(payload: dict) -> dict:
    goal = str(payload.get("goal") or "")
    hint = _format_hint(goal)
    if not hint:
        raise RelayError("SOURCE_TREE_FORMAT_HINT_MISSING")
    max_trees = max(1, min(int(payload.get("max_trees") or 12), 12))
    max_files = max(1, min(int(payload.get("max_files_per_tree") or 128), 128))
    max_total = max(1, min(int(payload.get("max_total_bytes_per_tree") or 2_000_000), 2_000_000))
    trees = []
    for repo in _github_repo_candidates(hint, limit=8):
        try:
            trees.extend(_source_trees_from_repo(repo, max_files, max_total))
        except Exception:
            continue
        if len(trees) >= max_trees:
            break
    if not trees:
        raise RelayError("SOURCE_TREE_SEARCH_EMPTY")
    return {"trees": trees[:max_trees]}


def _service_package_name_search(payload: dict) -> dict:
    if str(payload.get("ecosystem") or "").lower() != "pypi":
        raise RelayError("PACKAGE_SEARCH_ECOSYSTEM_NOT_ALLOWED")
    limit = max(1, min(int(payload.get("limit") or 24), 50))
    effect = str(payload.get("effect") or "")
    tokens = [str(x).lower() for x in payload.get("tokens") or [] if str(x).strip()]
    hint = _format_hint(effect) or (tokens[0] if tokens else "")
    names = []

    def add(value):
        value = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "")).strip("-")
        if value and value.lower() not in {x.lower() for x in names}:
            names.append(value)

    seeds = [hint] + tokens
    for seed in seeds:
        if not seed:
            continue
        add(seed)
        add("py-" + seed)
        add("python-" + seed)
        add(seed + "-python")
    for repo in _github_repo_candidates(hint, limit=8):
        add(repo.split("/", 1)[1])
        if len(names) >= limit:
            break
    return {"names": names[:limit]}


def _service_pypi_wheel_closure(payload: dict) -> dict:
    project = str(payload.get("project") or "").strip()
    version = str(payload.get("version") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,120}", project) or not version:
        raise RelayError("PYPI_WHEEL_IDENTITY_INVALID")
    max_wheels = max(1, min(int(payload.get("max_wheels") or 32), 32))
    max_total = max(1, min(int(payload.get("max_total_bytes") or 160_000_000), 160_000_000))
    with tempfile.TemporaryDirectory(prefix="brain-relay-wheel-") as td:
        proc = subprocess.run(
            [
                os.sys.executable, "-m", "pip", "download",
                "--disable-pip-version-check", "--only-binary=:all:",
                "--dest", td, f"{project}=={version}",
            ],
            text=True, capture_output=True, timeout=180,
        )
        if proc.returncode != 0:
            raise RelayError("PYPI_WHEEL_DOWNLOAD_FAILED:" + proc.stderr[-1000:])
        wheels = sorted(pathlib.Path(td).glob("*.whl"))
        if not wheels or len(wheels) > max_wheels:
            raise RelayError("PYPI_WHEEL_CLOSURE_INVALID")
        total = 0
        artifacts = []
        for wheel in wheels:
            raw = wheel.read_bytes()
            total += len(raw)
            if total > max_total:
                raise RelayError("PYPI_WHEEL_CLOSURE_TOO_LARGE")
            artifacts.append(
                {
                    "filename": wheel.name,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "content_b64": base64.b64encode(raw).decode("ascii"),
                }
            )
        return {"artifacts": artifacts}


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

    payload = req.get("payload")
    if not isinstance(payload, dict):
        raise RelayError("REQUEST_PAYLOAD_INVALID")
    kind = str(req.get("kind") or "")
    if kind == "urlopen":
        result = _service_urlopen(
            payload, allowed_hosts=allowed_hosts, max_bytes=max_bytes, opener=opener
        )
    elif kind == "package_name_search":
        result = _service_package_name_search(payload)
    elif kind == "python_source_tree":
        result = _service_python_source_tree(payload)
    elif kind == "pypi_wheel_closure":
        result = _service_pypi_wheel_closure(payload)
    else:
        raise RelayError("REQUEST_KIND_NOT_ALLOWED:" + kind)

    return {
        "schema": RESPONSE_SCHEMA,
        "request_sha256": request_sha,
        "kind": kind,
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
    skipped = []
    for request_path in sorted(bridge_dir.glob("*.request.json")):
        request_sha = request_path.name.removesuffix(".request.json")
        response_path = bridge_dir / (request_sha + ".response.json")
        if response_path.exists():
            continue
        try:
            response = service_request(
                request_path,
                allowed_hosts=allowed_hosts,
                expected_agent=expected_agent,
                expected_task=expected_task,
                max_bytes=max_bytes,
            )
        except RelayError as exc:
            skipped.append({"request_sha256": request_sha, "error": str(exc)})
            continue
        _atomic_json(response_path, response)
        serviced.append(request_sha)
        if len(serviced) >= max_requests:
            break
    return {
        "schema": "PROJECT_BRAIN_EXTERNAL_TOOL_RELAY_RUN_V1",
        "serviced_count": len(serviced),
        "serviced_request_sha256": serviced,
        "skipped": skipped,
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
