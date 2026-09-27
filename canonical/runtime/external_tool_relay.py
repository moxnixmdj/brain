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
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

REQUEST_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_REQUEST_V1"
RESPONSE_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1"
ALLOWED_HOSTS = {"registry.npmjs.org", "pypi.org", "registry.modelcontextprotocol.io", "api.github.com"}
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


SUPPORTED_KINDS = {"urlopen", "package_name_search", "python_source_tree", "pypi_wheel_closure", "npm_package_closure"}

def validate_request(request: dict, agent_id: str, task_id: str) -> tuple[str, str, dict]:
    if request.get("schema") != REQUEST_SCHEMA:
        raise RelayError("REQUEST_SCHEMA_INVALID")
    if request.get("agent_id") != agent_id or request.get("task_id") != task_id:
        raise RelayError("REQUEST_IDENTITY_MISMATCH")
    expected = canonical_request_sha(request)
    supplied = str(request.get("request_sha256") or "")
    if supplied != expected:
        raise RelayError("REQUEST_HASH_MISMATCH")
    kind = str(request.get("kind") or "")
    if kind not in SUPPORTED_KINDS:
        raise RelayError("REQUEST_KIND_NOT_ALLOWED")
    payload = request.get("payload")
    if not isinstance(payload, dict):
        raise RelayError("REQUEST_PAYLOAD_INVALID")
    return supplied, kind, payload


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



def execute_package_name_search(payload: dict) -> dict:
    if str(payload.get("ecosystem") or "") != "pypi":
        raise RelayError("PACKAGE_ECOSYSTEM_NOT_ALLOWED")
    tokens = [
        re.sub(r"[-_.]+", "-", str(x).strip().lower())
        for x in (payload.get("tokens") or [])
        if str(x).strip()
    ]
    if not tokens or len(tokens) > 8:
        raise RelayError("PACKAGE_SEARCH_TOKENS_INVALID")
    limit = min(max(int(payload.get("limit") or 50), 1), 100)
    req = urllib.request.Request(
        "https://pypi.org/simple/",
        headers={"User-Agent": "ProjectBrain-ExternalRelay/1", "Accept": "text/html"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read(MAX_BODY_BYTES + 1)
    if len(raw) > MAX_BODY_BYTES:
        raise RelayError("PACKAGE_INDEX_TOO_LARGE")
    text = raw.decode("utf-8", "replace")
    names = re.findall(r">([^<>]+)</a>", text, flags=re.I)
    scored = []
    for name in names:
        norm = re.sub(r"[-_.]+", "-", name.strip().lower())
        if not all(token in norm for token in tokens):
            continue
        score = (
            0 if norm in tokens else
            1 if any(norm == token for token in tokens) else
            2 if any(norm.startswith(token) or token in norm.split("-") for token in tokens) else
            3
        )
        scored.append((score, len(norm), norm, name.strip()))
    scored.sort()
    out = []
    seen = set()
    for _score, _length, norm, name in scored:
        if norm in seen:
            continue
        seen.add(norm)
        out.append(name)
        if len(out) >= limit:
            break
    return {"names": out}


def execute_pypi_wheel_closure(payload: dict) -> dict:
    project = str(payload.get("project") or "").strip()
    version = str(payload.get("version") or "").strip()
    if not project or not version or not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", project):
        raise RelayError("PYPI_IDENTITY_INVALID")
    max_wheels = min(max(int(payload.get("max_wheels") or 32), 1), 32)
    max_total = min(max(int(payload.get("max_total_bytes") or 160000000), 1), 160000000)
    with tempfile.TemporaryDirectory(prefix="brain-external-wheel-closure-") as td:
        proc = subprocess.run(
            [
                sys.executable, "-m", "pip", "download",
                "--disable-pip-version-check",
                "--only-binary=:all:",
                "--dest", td,
                f"{project}=={version}",
            ],
            text=True,
            capture_output=True,
            timeout=180,
        )
        if proc.returncode != 0:
            # "No compatible binary closure" is a candidate-level negative result,
            # not a transport failure. Return an empty closure so the runtime can
            # reject this candidate and continue its existing supplier race.
            return {"artifacts": []}
        wheels = sorted(pathlib.Path(td).glob("*.whl"))
        if not wheels:
            return {"artifacts": []}
        if len(wheels) > max_wheels:
            raise RelayError("PYPI_WHEEL_CLOSURE_COUNT_INVALID")
        artifacts = []
        total = 0
        for wheel in wheels:
            raw = wheel.read_bytes()
            total += len(raw)
            if total > max_total:
                raise RelayError("PYPI_WHEEL_CLOSURE_BYTES_LIMIT")
            artifacts.append({
                "filename": wheel.name,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "content_b64": base64.b64encode(raw).decode("ascii"),
            })
    return {"artifacts": artifacts}

def _npm_name_from_install_path(raw: str) -> str:
    path = pathlib.PurePosixPath(str(raw or ""))
    parts = list(path.parts)
    indexes = [i for i, part in enumerate(parts) if part == "node_modules"]
    if not indexes:
        raise RelayError("NPM_CLOSURE_INSTALL_PATH_INVALID")
    i = indexes[-1] + 1
    if i >= len(parts):
        raise RelayError("NPM_CLOSURE_INSTALL_PATH_INVALID")
    if parts[i].startswith("@"):
        if i + 1 >= len(parts):
            raise RelayError("NPM_CLOSURE_INSTALL_PATH_INVALID")
        return parts[i] + "/" + parts[i + 1]
    return parts[i]


def _verify_npm_sri(raw: bytes, integrity: str) -> tuple[str, str]:
    choices = []
    order = {"sha512": 3, "sha384": 2, "sha256": 1}
    for token in str(integrity or "").split():
        if "-" not in token:
            continue
        alg, encoded = token.split("-", 1)
        if alg not in order:
            continue
        try:
            expected = base64.b64decode(encoded, validate=True)
        except Exception:
            continue
        choices.append((order[alg], alg, expected))
    if not choices:
        raise RelayError("NPM_CLOSURE_STRONG_INTEGRITY_REQUIRED")
    _, alg, expected = max(choices)
    actual = hashlib.new(alg, raw).digest()
    if actual != expected:
        raise RelayError("NPM_CLOSURE_TARBALL_INTEGRITY_MISMATCH")
    return alg, actual.hex()


def execute_npm_package_closure(payload: dict) -> dict:
    package = str(payload.get("package") or "").strip()
    version = str(payload.get("version") or "").strip()
    if not re.fullmatch(r"(?:@[A-Za-z0-9_.-]+/)?[A-Za-z0-9_.-]{1,160}", package):
        raise RelayError("NPM_CLOSURE_PACKAGE_INVALID")
    if not version or len(version) > 100:
        raise RelayError("NPM_CLOSURE_VERSION_INVALID")
    max_packages = min(max(int(payload.get("max_packages") or 32), 1), 32)
    max_total = min(max(int(payload.get("max_total_bytes") or 80_000_000), 1), 80_000_000)

    with tempfile.TemporaryDirectory(prefix="brain-npm-closure-") as td:
        work = pathlib.Path(td)
        (work / "package.json").write_text(json.dumps({
            "name": "project-brain-closure",
            "private": True,
            "version": "0.0.0",
            "dependencies": {package: version},
        }, sort_keys=True), encoding="utf-8")
        env = {
            **os.environ,
            "npm_config_ignore_scripts": "true",
            "npm_config_audit": "false",
            "npm_config_fund": "false",
        }
        proc = subprocess.run(
            [
                "npm", "install", "--package-lock-only", "--ignore-scripts",
                "--no-audit", "--no-fund", "--omit=dev",
            ],
            cwd=work, text=True, capture_output=True, timeout=180, env=env,
        )
        if proc.returncode != 0:
            raise RelayError("NPM_CLOSURE_RESOLUTION_FAILED:" + proc.stderr[-1200:])
        lock = json.loads((work / "package-lock.json").read_text(encoding="utf-8"))
        packages = lock.get("packages")
        if not isinstance(packages, dict):
            raise RelayError("NPM_CLOSURE_LOCK_INVALID")

        rows = []
        total = 0
        for install_path, meta in sorted(packages.items()):
            if not install_path:
                continue
            if not isinstance(meta, dict):
                raise RelayError("NPM_CLOSURE_LOCK_RECORD_INVALID")
            posix = pathlib.PurePosixPath(str(install_path))
            if posix.is_absolute() or ".." in posix.parts or "node_modules" not in posix.parts:
                raise RelayError("NPM_CLOSURE_INSTALL_PATH_INVALID")
            name = _npm_name_from_install_path(install_path)
            resolved_version = str(meta.get("version") or "")
            resolved_url = _validate_url(meta.get("resolved"))
            integrity = str(meta.get("integrity") or "")
            if not resolved_version or not integrity:
                raise RelayError("NPM_CLOSURE_LOCK_RECORD_INCOMPLETE")
            req = urllib.request.Request(
                resolved_url,
                headers={"User-Agent": "ProjectBrain-ExternalRelay/1"},
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                raw = response.read(MAX_BODY_BYTES + 1)
            if len(raw) > MAX_BODY_BYTES:
                raise RelayError("NPM_CLOSURE_TARBALL_TOO_LARGE")
            total += len(raw)
            if total > max_total:
                raise RelayError("NPM_CLOSURE_TOTAL_BYTES_LIMIT")
            alg, digest_hex = _verify_npm_sri(raw, integrity)
            rows.append({
                "install_path": posix.as_posix(),
                "package": name,
                "version": resolved_version,
                "resolved_url": resolved_url,
                "integrity": integrity,
                "integrity_algorithm": alg,
                "integrity_digest_hex": digest_hex,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "content_b64": base64.b64encode(raw).decode("ascii"),
                "bytes": len(raw),
            })
            if len(rows) > max_packages:
                raise RelayError("NPM_CLOSURE_PACKAGE_COUNT_LIMIT")

    root_matches = [
        row for row in rows
        if row["install_path"] == "node_modules/" + package
    ]
    if len(root_matches) != 1 or root_matches[0]["version"] != version:
        raise RelayError("NPM_CLOSURE_ROOT_IDENTITY_MISMATCH")
    return {
        "schema": "PROJECT_BRAIN_EXTERNAL_NPM_PACKAGE_CLOSURE_V1",
        "root_package": package,
        "root_version": version,
        "package_count": len(rows),
        "total_bytes": total,
        "packages": rows,
    }


def _distinctive_goal_terms(goal: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+_.-]{2,40}", str(goal or ""))
    stop = {
        "encode", "decode", "binary", "data", "file", "save", "create", "verify",
        "verified", "independently", "different", "implementation", "canonical",
        "snapshot", "json", "exactly", "identical", "using", "with", "from",
        "into", "same", "keys", "values", "nesting", "arrays", "strings",
        "numbers", "booleans", "nulls", "artifact", "artifacts",
    }
    out = []
    for raw in words:
        token = raw.strip("._-").lower()
        if not token or token in stop or token in out:
            continue
        out.append(token)
    out.sort(key=lambda x: (0 if any(tag in x for tag in ("ubj", "codec", "pack")) else 1, len(x), x))
    return out[:12]


def _github_api_json(url: str) -> dict:
    result = execute_urlopen({
        "url": url,
        "method": "GET",
        "headers": {
            "Accept": "application/vnd.github+json",
            "User-Agent": "ProjectBrain-ExternalRelay/1",
        },
        "timeout_s": 20,
        "data_b64": None,
    })
    if int(result.get("status", 0)) != 200:
        raise RelayError("GITHUB_API_HTTP_" + str(result.get("status")))
    try:
        raw = base64.b64decode(str(result["body_b64"]), validate=True)
        value = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise RelayError("GITHUB_API_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise RelayError("GITHUB_API_JSON_INVALID")
    return value


def _source_tree_from_repo(
    full_name: str,
    goal: str,
    max_files: int,
    max_total_bytes: int,
) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", full_name):
        raise RelayError("GITHUB_REPOSITORY_ID_INVALID")
    with tempfile.TemporaryDirectory(prefix="brain-external-source-") as td:
        dest = pathlib.Path(td) / "repo"
        proc = subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet",
             "https://github.com/" + full_name + ".git", str(dest)],
            text=True, capture_output=True, timeout=60,
        )
        if proc.returncode != 0:
            raise RelayError("GIT_CLONE_FAILED:" + proc.stderr[-800:])
        rev = subprocess.run(
            ["git", "-C", str(dest), "rev-parse", "HEAD"],
            text=True, capture_output=True, timeout=10, check=True,
        ).stdout.strip()
        if not re.fullmatch(r"[0-9a-f]{40}", rev):
            raise RelayError("GIT_REVISION_INVALID")

        package_dirs = []
        for init in list(dest.glob("*/__init__.py")) + list(dest.glob("src/*/__init__.py")):
            if init.parent.name.lower() in {
                "tests", "test", "docs", "doc", "examples", "example", "benchmarks"
            }:
                continue
            if init.parent not in package_dirs:
                package_dirs.append(init.parent)
        if not package_dirs:
            raise RelayError("NO_TOP_LEVEL_PYTHON_PACKAGE")

        terms = _distinctive_goal_terms(goal)
        best = None
        best_score = -1
        for package in package_dirs:
            files = sorted(p for p in package.rglob("*.py") if p.is_file())
            if not files or len(files) > max_files:
                continue
            score = 0
            haystack = (full_name + " " + package.name).lower()
            for term in terms:
                if term in haystack:
                    score += 5
            for p in files[:40]:
                lname = p.name.lower()
                if any(x in lname for x in (
                    "codec", "encode", "decode", "dump", "load", "pack", "ubj", "json"
                )):
                    score += 2
            if score > best_score:
                best_score, best = score, (package, files)
        if best is None:
            raise RelayError("NO_BOUNDED_PYTHON_PACKAGE")

        package, files = best
        records = []
        total = 0
        for p in files:
            raw = p.read_bytes()
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            total += len(raw)
            if total > max_total_bytes:
                raise RelayError("SOURCE_TREE_BYTES_LIMIT")
            rel = pathlib.PurePosixPath(package.name) / p.relative_to(package).as_posix()
            git_blob_sha = hashlib.sha1(
                b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
            ).hexdigest()
            records.append({
                "path": rel.as_posix(),
                "git_blob_sha": git_blob_sha,
                "content": content,
            })
        if not records or not any(x["path"].endswith("/__init__.py") for x in records):
            raise RelayError("SOURCE_TREE_EMPTY")
        return {
            "schema": "PROJECT_BRAIN_EXTERNAL_SOURCE_TREE_V1",
            "repository": full_name,
            "revision": rev,
            "files": records,
        }


def execute_python_source_tree(payload: dict) -> dict:
    goal = str(payload.get("goal") or "")
    if not goal or len(goal) > 20_000:
        raise RelayError("SOURCE_TREE_GOAL_INVALID")
    allowed_suffixes = list(payload.get("allowed_suffixes") or [".py"])
    if allowed_suffixes != [".py"]:
        raise RelayError("SOURCE_TREE_SUFFIXES_UNSUPPORTED")
    if payload.get("require_git_blob_sha") is not True:
        raise RelayError("SOURCE_TREE_GIT_BLOB_SHA_REQUIRED")
    max_trees = min(max(int(payload.get("max_trees") or 12), 1), 12)
    max_files = min(max(int(payload.get("max_files_per_tree") or 128), 1), 128)
    max_total = min(max(int(payload.get("max_total_bytes_per_tree") or 2_000_000), 1), 2_000_000)
    terms = _distinctive_goal_terms(goal)
    if not terms:
        raise RelayError("SOURCE_TREE_SEARCH_TERMS_EMPTY")

    queries = [f"{term} language:Python" for term in terms[:4]]
    if len(terms) > 1:
        queries.append(" ".join(terms[:4]) + " language:Python")

    repositories = []
    for query in queries[:5]:
        url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode({
            "q": query, "sort": "stars", "order": "desc", "per_page": 5
        })
        try:
            data = _github_api_json(url)
        except Exception:
            continue
        for item in data.get("items") or []:
            full_name = str(item.get("full_name") or "")
            if full_name and full_name not in repositories:
                repositories.append(full_name)
        if len(repositories) >= 8:
            break

    trees = []
    for full_name in repositories[:8]:
        try:
            tree = _source_tree_from_repo(full_name, goal, max_files, max_total)
            trees.append(tree)
        except Exception:
            continue
        if len(trees) >= min(max_trees, 4):
            break
    return {"trees": trees}


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
    request_sha, kind, payload = validate_request(request, agent_id, task_id)
    response_path = path.with_name(request_sha + ".response.json")
    if response_path.exists():
        return None
    try:
        if kind == "urlopen":
            result = execute_urlopen(payload)
        elif kind == "package_name_search":
            result = execute_package_name_search(payload)
        elif kind == "python_source_tree":
            result = execute_python_source_tree(payload)
        elif kind == "pypi_wheel_closure":
            result = execute_pypi_wheel_closure(payload)
        elif kind == "npm_package_closure":
            result = execute_npm_package_closure(payload)
        else:
            raise RelayError("REQUEST_KIND_NOT_ALLOWED")
        response = {
            "schema": RESPONSE_SCHEMA,
            "request_sha256": request_sha,
            "kind": kind,
            "agent_id": agent_id,
            "task_id": task_id,
            "status": "ok",
            "result": result,
        }
    except Exception as exc:
        response = {
            "schema": RESPONSE_SCHEMA,
            "request_sha256": request_sha,
            "kind": kind,
            "agent_id": agent_id,
            "task_id": task_id,
            "status": "error",
            "error": type(exc).__name__ + ":" + str(exc)[:3000],
        }
    _write_json_atomic(response_path, response)
    return response_path


def service_pending(bridge_dir: pathlib.Path, agent_id: str, task_id: str) -> list[str]:
    bridge_dir = bridge_dir.resolve()
    bridge_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for path in sorted(bridge_dir.glob("*.request.json")):
        request = json.loads(path.read_text(encoding="utf-8"))
        # Leave unknown/custom kinds pending. They are separate authority surfaces
        # and must be implemented only if a resumed real mission proves them causal.
        if request.get("kind") not in SUPPORTED_KINDS:
            continue
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
