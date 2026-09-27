#!/usr/bin/env python3
"""Bounded external-tool relay for Project Brain.

The relay is a replaceable actuator, not a planner. It services only exact,
content-addressed requests already emitted by ASTRA and returns typed results.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import io
import ipaddress
import json
import pathlib
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request

REQUEST_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_REQUEST_V1"
RESPONSE_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1"
ALLOWED_KINDS = {"urlopen", "package_name_search", "python_source_tree", "pypi_wheel_closure"}
ASTRA_HTTPS_HOSTS = {
    "registry.npmjs.org",
    "pypi.org",
    "files.pythonhosted.org",
    "registry.modelcontextprotocol.io",
}
RELAY_GITHUB_HOSTS = {"api.github.com", "codeload.github.com"}
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


def _safe_https_url(raw: str, allowed_hosts: set[str]) -> str:
    parsed = urllib.parse.urlsplit(str(raw or ""))
    if parsed.scheme.lower() != "https":
        raise RelayError("URL_SCHEME_FORBIDDEN")
    if parsed.username or parsed.password:
        raise RelayError("URL_CREDENTIALS_FORBIDDEN")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in allowed_hosts:
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
    kind = str(request.get("kind") or "")
    if kind not in ALLOWED_KINDS:
        raise RelayError("REQUEST_KIND_FORBIDDEN:" + kind)
    supplied = str(request.get("request_sha256") or "")
    computed = _canonical_request_sha(request)
    if supplied != computed or path.name != supplied + ".request.json":
        raise RelayError("REQUEST_HASH_MISMATCH")
    if not request.get("agent_id") or not request.get("task_id"):
        raise RelayError("REQUEST_IDENTITY_MISSING")
    payload = request.get("payload")
    if not isinstance(payload, dict):
        raise RelayError("REQUEST_PAYLOAD_INVALID")
    if kind == "urlopen":
        method = str(payload.get("method") or "GET").upper()
        if method not in {"GET", "HEAD"}:
            raise RelayError("METHOD_FORBIDDEN:" + method)
        if payload.get("data_b64") not in {None, ""}:
            raise RelayError("REQUEST_BODY_FORBIDDEN")
        _safe_https_url(payload.get("url"), ASTRA_HTTPS_HOSTS)
        headers = payload.get("headers") or {}
        if not isinstance(headers, dict):
            raise RelayError("REQUEST_HEADERS_INVALID")
        if any(str(k).lower() in FORBIDDEN_REQUEST_HEADERS for k in headers):
            raise RelayError("CREDENTIAL_HEADER_FORBIDDEN")
        timeout = float(payload.get("timeout_s") or 20)
        if timeout <= 0 or timeout > 60:
            raise RelayError("TIMEOUT_OUT_OF_RANGE")
    elif kind == "package_name_search":
        ecosystem = str(payload.get("ecosystem") or "").lower()
        if ecosystem not in {"pypi", "npm"}:
            raise RelayError("PACKAGE_ECOSYSTEM_FORBIDDEN:" + ecosystem)
        tokens = payload.get("tokens")
        if not isinstance(tokens, list) or not tokens or len(tokens) > 12:
            raise RelayError("PACKAGE_SEARCH_TOKENS_INVALID")
        limit = int(payload.get("limit") or 20)
        if limit < 1 or limit > 100:
            raise RelayError("PACKAGE_SEARCH_LIMIT_INVALID")
    elif kind == "python_source_tree":
        if int(payload.get("max_trees") or 0) < 1 or int(payload.get("max_trees") or 0) > 12:
            raise RelayError("SOURCE_TREE_LIMIT_INVALID")
        if payload.get("allowed_suffixes") != [".py"]:
            raise RelayError("SOURCE_TREE_SUFFIX_POLICY_INVALID")
        if payload.get("require_git_blob_sha") is not True:
            raise RelayError("SOURCE_TREE_GIT_BLOB_REQUIRED")
    elif kind == "pypi_wheel_closure":
        project = str(payload.get("project") or "").strip()
        version = str(payload.get("version") or "").strip()
        metadata_url = str(payload.get("metadata_url") or "").strip()
        if not project or len(project) > 200 or not version or len(version) > 200:
            raise RelayError("PYPI_CLOSURE_IDENTITY_INVALID")
        _safe_https_url(metadata_url, {"pypi.org"})
        max_wheels = int(payload.get("max_wheels") or 0)
        max_total = int(payload.get("max_total_bytes") or 0)
        if max_wheels < 1 or max_wheels > 32:
            raise RelayError("PYPI_CLOSURE_WHEEL_LIMIT_INVALID")
        if max_total < 1 or max_total > 160_000_000:
            raise RelayError("PYPI_CLOSURE_BYTE_LIMIT_INVALID")
    return request


def _read_http(
    url: str,
    *,
    allowed_hosts: set[str],
    headers: dict[str, str] | None = None,
    timeout: float = 20,
    max_bytes: int = MAX_RESPONSE_BYTES,
    opener=urllib.request.urlopen,
):
    safe = _safe_https_url(url, allowed_hosts)
    req = urllib.request.Request(safe, headers=headers or {}, method="GET")
    with opener(req, timeout=timeout) as response:
        final_url = _safe_https_url(response.geturl(), allowed_hosts)
        status = int(getattr(response, "status", 200))
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise RelayError("RESPONSE_TOO_LARGE")
        response_headers = dict(getattr(response, "headers", {}) or {})
    return status, final_url, response_headers, raw


def _service_urlopen(request: dict, opener=urllib.request.urlopen) -> dict:
    payload = request["payload"]
    url = _safe_https_url(payload["url"], ASTRA_HTTPS_HOSTS)
    method = str(payload.get("method") or "GET").upper()
    headers = {str(k): str(v) for k, v in (payload.get("headers") or {}).items()}
    req = urllib.request.Request(url, headers=headers, method=method)
    timeout = min(float(payload.get("timeout_s") or 20), 60.0)
    try:
        with opener(req, timeout=timeout) as response:
            final_url = _safe_https_url(response.geturl(), ASTRA_HTTPS_HOSTS)
            status = int(getattr(response, "status", 200))
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            response_headers = dict(getattr(response, "headers", {}) or {})
    except urllib.error.HTTPError as exc:
        final_url = _safe_https_url(exc.geturl(), ASTRA_HTTPS_HOSTS)
        status = int(exc.code)
        raw = exc.read(MAX_RESPONSE_BYTES + 1)
        response_headers = dict(getattr(exc, "headers", {}) or {})
    if len(raw) > MAX_RESPONSE_BYTES:
        raise RelayError("RESPONSE_TOO_LARGE")
    return {
        "status": status,
        "final_url": final_url,
        "headers": {str(k): str(v) for k, v in response_headers.items()},
        "body_b64": base64.b64encode(raw).decode("ascii"),
    }


def _normalized_search_tokens(payload: dict) -> list[str]:
    out = []
    for raw in payload.get("tokens") or []:
        token = re.sub(r"[^a-z0-9._+-]+", "", str(raw).lower())
        if token and token not in out:
            out.append(token)
    return out[:12]


def _service_package_name_search(request: dict, opener=urllib.request.urlopen) -> dict:
    payload = request["payload"]
    ecosystem = str(payload["ecosystem"]).lower()
    tokens = _normalized_search_tokens(payload)
    limit = int(payload.get("limit") or 20)
    headers = {"User-Agent": "ProjectBrain-ExternalRelay/1"}
    if ecosystem == "npm":
        query = urllib.parse.quote(" ".join(tokens))
        url = "https://registry.npmjs.org/-/v1/search?text=" + query + "&size=" + str(limit)
        _status, _final, _headers, raw = _read_http(
            url, allowed_hosts={"registry.npmjs.org"}, headers=headers, opener=opener
        )
        data = json.loads(raw.decode("utf-8"))
        names = [
            str((item.get("package") or {}).get("name") or "")
            for item in data.get("objects") or []
            if isinstance(item, dict)
        ]
        return {"names": [x for x in names if x][:limit]}

    _status, _final, _headers, raw = _read_http(
        "https://pypi.org/simple/",
        allowed_hosts={"pypi.org"},
        headers=headers,
        max_bytes=MAX_RESPONSE_BYTES,
        opener=opener,
    )
    text = raw.decode("utf-8", "replace")
    names = [html.unescape(x) for x in re.findall(r">([^<>]+)</a>", text, flags=re.I)]
    scored = []
    for name in names:
        lower = name.lower()
        hits = sum(1 for token in tokens if token in lower)
        if not hits:
            continue
        exact = 0 if lower in tokens else 1
        prefix = 0 if any(lower.startswith(t) for t in tokens) else 1
        scored.append((exact, prefix, -hits, len(name), lower, name))
    scored.sort()
    return {"names": [x[-1] for x in scored[:limit]]}


def _goal_terms(goal: str) -> list[str]:
    raw = str(goal or "").lower()
    terms = []
    for match in re.findall(r"\b[a-z][a-z0-9+_.-]{2,30}\b", raw):
        if match in {
            "canonical", "json", "save", "encode", "binary", "file", "using",
            "verify", "different", "implementation", "exactly", "identical",
        }:
            continue
        if match not in terms:
            terms.append(match)
    for ext in re.findall(r"\.([a-z0-9]{2,10})\b", raw):
        if ext not in terms:
            terms.insert(0, ext)
    return terms[:6]


def _github_json(url: str, opener=urllib.request.urlopen):
    _status, _final, _headers, raw = _read_http(
        url,
        allowed_hosts={"api.github.com"},
        headers={
            "User-Agent": "ProjectBrain-ExternalRelay/1",
            "Accept": "application/vnd.github+json",
        },
        max_bytes=16 * 1024 * 1024,
        opener=opener,
    )
    return json.loads(raw.decode("utf-8"))


def _repo_source_tree(repo: dict, payload: dict, opener=urllib.request.urlopen):
    full_name = str(repo.get("full_name") or "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", full_name):
        return None
    default_branch = str(repo.get("default_branch") or "main")
    commit = _github_json(
        "https://api.github.com/repos/" + full_name + "/commits/" + urllib.parse.quote(default_branch, safe=""),
        opener=opener,
    )
    revision = str(commit.get("sha") or "")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        return None
    tree = _github_json(
        "https://api.github.com/repos/" + full_name + "/git/trees/" + revision + "?recursive=1",
        opener=opener,
    )
    entries = tree.get("tree") or []
    blob_shas = {
        str(x.get("path")): str(x.get("sha"))
        for x in entries
        if isinstance(x, dict)
        and x.get("type") == "blob"
        and str(x.get("path") or "").endswith(".py")
        and re.fullmatch(r"[0-9a-f]{40}", str(x.get("sha") or ""))
    }
    if not blob_shas:
        return None

    init_paths = [
        p for p in blob_shas
        if p.endswith("/__init__.py")
        and len(pathlib.PurePosixPath(p).parts) <= 5
        and not any(seg.lower() in {"tests", "test", "examples", "example", "docs"} for seg in pathlib.PurePosixPath(p).parts)
    ]
    if not init_paths:
        return None

    archive_url = "https://codeload.github.com/" + full_name + "/tar.gz/" + revision
    _status, _final, _headers, archive = _read_http(
        archive_url,
        allowed_hosts={"codeload.github.com"},
        headers={"User-Agent": "ProjectBrain-ExternalRelay/1"},
        max_bytes=32 * 1024 * 1024,
        opener=opener,
    )
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tf:
        archive_files = {}
        for member in tf.getmembers():
            if not member.isfile():
                continue
            parts = pathlib.PurePosixPath(member.name).parts
            if len(parts) < 2:
                continue
            rel = pathlib.PurePosixPath(*parts[1:]).as_posix()
            if rel in blob_shas:
                fh = tf.extractfile(member)
                if fh is not None:
                    archive_files[rel] = fh.read()

    max_files = min(int(payload.get("max_files_per_tree") or 128), 128)
    max_total = min(int(payload.get("max_total_bytes_per_tree") or 2_000_000), 2_000_000)
    candidates = []
    for init_path in sorted(init_paths, key=lambda p: (len(pathlib.PurePosixPath(p).parts), p)):
        package_dir = pathlib.PurePosixPath(init_path).parent.as_posix()
        package_name = pathlib.PurePosixPath(package_dir).name
        selected = []
        total = 0
        for repo_path in sorted(blob_shas):
            if repo_path != package_dir + "/__init__.py" and not repo_path.startswith(package_dir + "/"):
                continue
            raw = archive_files.get(repo_path)
            if raw is None:
                continue
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            if actual != blob_shas[repo_path]:
                raise RelayError("GITHUB_BLOB_VERIFICATION_FAILED:" + repo_path)
            suffix = pathlib.PurePosixPath(repo_path).relative_to(pathlib.PurePosixPath(package_dir).parent)
            total += len(raw)
            if total > max_total or len(selected) >= max_files:
                break
            selected.append({
                "path": suffix.as_posix(),
                "git_blob_sha": actual,
                "content": content,
            })
        if selected and any(x["path"] == package_name + "/__init__.py" for x in selected):
            candidates.append({
                "schema": "PROJECT_BRAIN_EXTERNAL_SOURCE_TREE_V1",
                "repository": full_name,
                "revision": revision,
                "files": selected,
            })
    return candidates[0] if candidates else None


def _service_python_source_tree(request: dict, opener=urllib.request.urlopen) -> dict:
    payload = request["payload"]
    terms = _goal_terms(payload.get("goal"))
    max_trees = min(int(payload.get("max_trees") or 12), 12)
    seen = set()
    trees = []
    for term in terms[:4]:
        query = urllib.parse.urlencode({
            "q": term + " language:Python",
            "sort": "stars",
            "order": "desc",
            "per_page": "5",
        })
        data = _github_json("https://api.github.com/search/repositories?" + query, opener=opener)
        for repo in data.get("items") or []:
            full_name = str(repo.get("full_name") or "")
            if not full_name or full_name in seen:
                continue
            seen.add(full_name)
            try:
                tree = _repo_source_tree(repo, payload, opener=opener)
            except Exception:
                tree = None
            if tree is not None:
                trees.append(tree)
            if len(trees) >= max_trees:
                return {"trees": trees}
    return {"trees": trees}


def _service_pypi_wheel_closure(request: dict) -> dict:
    payload = request["payload"]
    project = str(payload["project"]).strip()
    version = str(payload["version"]).strip()
    max_wheels = min(int(payload.get("max_wheels") or 32), 32)
    max_total = min(int(payload.get("max_total_bytes") or 160_000_000), 160_000_000)

    with tempfile.TemporaryDirectory(prefix="brain-external-pypi-closure-") as td:
        proc = subprocess.run(
            [
                sys.executable, "-m", "pip", "download",
                "--disable-pip-version-check",
                "--only-binary=:all:",
                "--dest", td,
                project + "==" + version,
            ],
            text=True,
            capture_output=True,
            timeout=180,
        )
        if proc.returncode != 0:
            raise RelayError(
                "PYPI_CLOSURE_RESOLUTION_FAILED:" + (proc.stderr or proc.stdout or "")[-1800:]
            )
        wheels = sorted(pathlib.Path(td).glob("*.whl"))
        if not wheels or len(wheels) > max_wheels:
            raise RelayError("PYPI_CLOSURE_WHEEL_COUNT_INVALID:" + str(len(wheels)))
        artifacts = []
        total = 0
        for wheel in wheels:
            raw = wheel.read_bytes()
            total += len(raw)
            if total > max_total:
                raise RelayError("PYPI_CLOSURE_BYTES_LIMIT")
            artifacts.append({
                "filename": wheel.name,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "content_b64": base64.b64encode(raw).decode("ascii"),
            })
    return {"artifacts": artifacts}


def _dispatch(request: dict, opener=urllib.request.urlopen) -> dict:
    kind = request["kind"]
    if kind == "urlopen":
        return _service_urlopen(request, opener=opener)
    if kind == "package_name_search":
        return _service_package_name_search(request, opener=opener)
    if kind == "python_source_tree":
        return _service_python_source_tree(request, opener=opener)
    if kind == "pypi_wheel_closure":
        return _service_pypi_wheel_closure(request)
    raise RelayError("REQUEST_KIND_FORBIDDEN:" + str(kind))


def service_request(path: pathlib.Path, opener=urllib.request.urlopen) -> pathlib.Path:
    request = _validate_request(path)
    request_sha = request["request_sha256"]
    response_path = path.with_name(request_sha + ".response.json")
    if response_path.exists():
        return response_path
    result = _dispatch(request, opener=opener)
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
