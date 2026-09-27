#!/usr/bin/env python3
"""Bounded zero-secret executor for Project Brain external-tool bridge requests.

The ASTRA runtime remains network-constrained. This relay is a replaceable
external actuator that validates content-addressed requests, performs only a
small allowlisted set of zero-cost public operations, and writes identity-bound
responses for the same worker/task to consume on its next resume.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import ipaddress
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

REQUEST_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_REQUEST_V1"
RESPONSE_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1"
MAX_HTTP_BYTES = 80_000_000
DEFAULT_ALLOWED_HOSTS = {
    "pypi.org",
    "files.pythonhosted.org",
    "registry.npmjs.org",
    "api.github.com",
    "github.com",
    "raw.githubusercontent.com",
    "codeload.github.com",
    "text.pollinations.ai",
}


class RelayFailure(RuntimeError):
    pass


def _canonical_request_core(request):
    return {
        "schema": request.get("schema"),
        "kind": request.get("kind"),
        "agent_id": request.get("agent_id"),
        "task_id": request.get("task_id"),
        "payload": request.get("payload"),
    }


def request_sha256(request):
    raw = json.dumps(
        _canonical_request_core(request),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_request(request, path=None, expected_agent=None, expected_task=None):
    if not isinstance(request, dict) or request.get("schema") != REQUEST_SCHEMA:
        raise RelayFailure("REQUEST_SCHEMA_INVALID")
    if not isinstance(request.get("payload"), dict):
        raise RelayFailure("REQUEST_PAYLOAD_INVALID")
    observed = str(request.get("request_sha256") or "")
    computed = request_sha256(request)
    if not re.fullmatch(r"[0-9a-f]{64}", observed) or observed != computed:
        raise RelayFailure("REQUEST_HASH_MISMATCH")
    if path is not None and pathlib.Path(path).name != observed + ".request.json":
        raise RelayFailure("REQUEST_FILENAME_HASH_MISMATCH")
    if expected_agent is not None and request.get("agent_id") != expected_agent:
        raise RelayFailure("REQUEST_AGENT_MISMATCH")
    if expected_task is not None and request.get("task_id") != expected_task:
        raise RelayFailure("REQUEST_TASK_MISMATCH")
    return computed


def _allowed_host(host, allowed_hosts=None):
    host = str(host or "").strip(".").lower()
    allowed = set(allowed_hosts or DEFAULT_ALLOWED_HOSTS)
    return host in allowed


def _validate_public_https_url(url, allowed_hosts=None):
    parsed = urllib.parse.urlsplit(str(url or ""))
    if parsed.scheme.lower() != "https":
        raise RelayFailure("URL_HTTPS_REQUIRED")
    if parsed.username or parsed.password:
        raise RelayFailure("URL_USERINFO_FORBIDDEN")
    if parsed.port not in (None, 443):
        raise RelayFailure("URL_PORT_FORBIDDEN")
    host = (parsed.hostname or "").lower()
    if not _allowed_host(host, allowed_hosts):
        raise RelayFailure("URL_HOST_FORBIDDEN:" + host)
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        ip = None
    if ip is not None and (
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
        or ip.is_multicast or ip.is_unspecified
    ):
        raise RelayFailure("URL_IP_FORBIDDEN")
    return parsed.geturl()


def _safe_headers(headers):
    out = {}
    allowed = {"accept", "content-type", "user-agent", "accept-encoding"}
    for key, value in dict(headers or {}).items():
        lk = str(key).lower()
        if lk in allowed and "\n" not in str(value) and "\r" not in str(value):
            out[str(key)] = str(value)
    if not any(str(k).lower() == "user-agent" for k in out):
        out["User-Agent"] = "ProjectBrain-ExternalRelay/1"
    return out


def _http_bytes(url, method="GET", headers=None, data=None, timeout_s=30, max_bytes=MAX_HTTP_BYTES):
    url = _validate_public_https_url(url)
    method = str(method or "GET").upper()
    if method not in {"GET", "HEAD", "POST"}:
        raise RelayFailure("HTTP_METHOD_FORBIDDEN:" + method)
    timeout_s = max(1, min(int(timeout_s or 30), 90))
    max_bytes = max(1, min(int(max_bytes or MAX_HTTP_BYTES), MAX_HTTP_BYTES))
    if data is not None and len(data) > 1_000_000:
        raise RelayFailure("HTTP_REQUEST_BODY_TOO_LARGE")
    req = urllib.request.Request(
        url,
        data=data,
        headers=_safe_headers(headers),
        method=method,
    )
    started = time.monotonic()
    try:
        response = urllib.request.urlopen(req, timeout=timeout_s)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        final_url = _validate_public_https_url(response.geturl())
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise RelayFailure("HTTP_RESPONSE_TOO_LARGE")
        status = int(getattr(response, "status", getattr(response, "code", 200)))
        response_headers = {str(k): str(v) for k, v in response.headers.items()}
    return {
        "status": status,
        "final_url": final_url,
        "headers": response_headers,
        "raw": raw,
        "duration_s": round(time.monotonic() - started, 3),
    }


def _handle_urlopen(payload):
    encoded = payload.get("data_b64")
    data = None
    if encoded is not None:
        try:
            data = base64.b64decode(str(encoded), validate=True)
        except Exception as exc:
            raise RelayFailure("URLOPEN_DATA_BASE64_INVALID") from exc
    result = _http_bytes(
        payload.get("url"),
        method=payload.get("method", "GET"),
        headers=payload.get("headers") or {},
        data=data,
        timeout_s=payload.get("timeout_s", 20),
        max_bytes=MAX_HTTP_BYTES,
    )
    return {
        "status": result["status"],
        "final_url": result["final_url"],
        "headers": result["headers"],
        "body_b64": base64.b64encode(result["raw"]).decode("ascii"),
        "duration_s": result["duration_s"],
    }


def _handle_http_get(payload):
    limit = max(1, min(int(payload.get("max_bytes") or 200_000), 2_000_000))
    result = _http_bytes(
        payload.get("url"),
        method="GET",
        headers={"User-Agent": "ProjectBrain-ExternalRelay/1"},
        timeout_s=payload.get("timeout_s", 20),
        max_bytes=limit,
    )
    body = result["raw"]
    return {
        "url": result["final_url"],
        "status": result["status"],
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "body_excerpt": body[:12_000].decode("utf-8", "replace"),
        "duration_s": result["duration_s"],
    }


def _handle_planner(payload):
    prompt = str(payload.get("prompt") or "")
    if not prompt or len(prompt) > 200_000:
        raise RelayFailure("PLANNER_PROMPT_INVALID")
    raw_models = payload.get("models") or []
    allowed_models = {"openai-fast", "openai", "mistral"}
    models = [str(x) for x in raw_models if str(x) in allowed_models][:3]
    if not models:
        raise RelayFailure("PLANNER_MODELS_INVALID")
    timeout_s = max(1, min(int(payload.get("timeout_s") or 20), 40))
    errors = []
    for model in models:
        body = json.dumps({
            "messages": [{"role": "user", "content": prompt}],
            "model": model,
            "jsonMode": True,
        }).encode("utf-8")
        try:
            result = _http_bytes(
                "https://text.pollinations.ai/",
                method="POST",
                headers={"Content-Type": "application/json", "User-Agent": "ProjectBrain-ExternalRelay/1"},
                data=body,
                timeout_s=timeout_s,
                max_bytes=30_000,
            )
            if 200 <= result["status"] < 300:
                text = result["raw"].decode("utf-8", "replace")
                if text.strip():
                    return {
                        "text": text,
                        "model": model,
                        "duration_s": result["duration_s"],
                        "errors": errors,
                    }
            errors.append({"model": model, "status": result["status"]})
        except Exception as exc:
            errors.append({"model": model, "error": type(exc).__name__ + ":" + str(exc)})
    raise RelayFailure("PLANNER_ALL_ROUTES_FAILED:" + json.dumps(errors, sort_keys=True)[:1800])


def _package_token(value):
    return re.sub(r"[-_.]+", "", str(value or "").lower())


def _handle_package_name_search(payload):
    ecosystem = str(payload.get("ecosystem") or "").strip().lower()
    tokens = []
    for raw in payload.get("tokens") or []:
        token = str(raw or "").strip().lower()
        if re.fullmatch(r"[a-z0-9][a-z0-9._+-]{1,80}", token) and token not in tokens:
            tokens.append(token)
    if not tokens:
        raise RelayFailure("PACKAGE_SEARCH_TOKENS_INVALID")
    limit = max(1, min(int(payload.get("limit") or 24), 50))
    timeout_s = max(1, min(int(payload.get("timeout_s") or 12), 30))

    if ecosystem == "npm":
        query = " ".join(tokens[:8])
        url = "https://registry.npmjs.org/-/v1/search?" + urllib.parse.urlencode(
            {"text": query, "size": limit}
        )
        result = _http_bytes(url, timeout_s=timeout_s, max_bytes=2_000_000)
        if result["status"] != 200:
            raise RelayFailure("NPM_SEARCH_HTTP_" + str(result["status"]))
        data = json.loads(result["raw"].decode("utf-8"))
        names = []
        for obj in data.get("objects") or []:
            package = obj.get("package") if isinstance(obj, dict) else None
            name = str((package or {}).get("name") or "")
            if name and name not in names:
                names.append(name)
            if len(names) >= limit:
                break
        return {"names": names}

    if ecosystem == "pypi":
        url = _validate_public_https_url("https://pypi.org/simple/")
        req = urllib.request.Request(url, headers={"User-Agent": "ProjectBrain-ExternalRelay/1"})
        normalized = [_package_token(t) for t in tokens if _package_token(t)]
        found = []
        total = 0
        carry = ""
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            _validate_public_https_url(resp.geturl())
            while total <= 64 * 1024 * 1024 and len(found) < limit:
                raw = resp.read(262_144)
                if not raw:
                    break
                total += len(raw)
                text = carry + raw.decode("utf-8", "replace")
                carry = text[-1024:]
                body = text[:-1024] if len(text) > 1024 else ""
                for name in re.findall(r">\s*([^<>\s][^<>]{0,120}?)\s*</a>", body, re.I):
                    project = html.unescape(name).strip()
                    norm = _package_token(project)
                    if any(token in norm for token in normalized):
                        if (
                            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,120}", project)
                            and project.lower() not in [x.lower() for x in found]
                        ):
                            found.append(project)
                            if len(found) >= limit:
                                break
        return {"names": found}

    raise RelayFailure("PACKAGE_SEARCH_ECOSYSTEM_UNSUPPORTED:" + ecosystem)


def _github_api_json(url, timeout_s=20, max_bytes=3_000_000):
    result = _http_bytes(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "ProjectBrain-ExternalRelay/1"},
        timeout_s=timeout_s,
        max_bytes=max_bytes,
    )
    if result["status"] != 200:
        raise RelayFailure("GITHUB_API_HTTP_" + str(result["status"]))
    return json.loads(result["raw"].decode("utf-8"))


def _distinctive_goal_terms(goal):
    words = re.findall(r"[A-Za-z][A-Za-z0-9+_.-]{2,40}", str(goal or "").lower())
    stop = {
        "encode","decode","binary","data","file","save","create","verify","verified",
        "independently","different","implementation","canonical","snapshot","json",
        "exactly","identical","using","with","from","into","same","keys","values",
        "nesting","arrays","strings","numbers","booleans","nulls","artifact",
    }
    out = []
    for word in words:
        token = word.strip("._-")
        if token not in stop and token not in out:
            out.append(token)
    return out[:12]


def _source_tree_from_repo(full_name, goal, timeout_s=60):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", full_name):
        raise RelayFailure("GITHUB_REPOSITORY_ID_INVALID")
    with tempfile.TemporaryDirectory(prefix="brain-external-source-") as td:
        dest = pathlib.Path(td) / "repo"
        url = "https://github.com/" + full_name + ".git"
        proc = subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", url, str(dest)],
            text=True, capture_output=True, timeout=timeout_s,
        )
        if proc.returncode != 0:
            raise RelayFailure("GIT_CLONE_FAILED:" + proc.stderr[-800:])
        rev = subprocess.run(
            ["git", "-C", str(dest), "rev-parse", "HEAD"],
            text=True, capture_output=True, timeout=10, check=True,
        ).stdout.strip()
        if not re.fullmatch(r"[0-9a-f]{40}", rev):
            raise RelayFailure("GIT_REVISION_INVALID")

        package_dirs = []
        for init in dest.glob("*/__init__.py"):
            if init.parent.name.lower() in {"tests","test","docs","doc","examples","example","benchmarks"}:
                continue
            package_dirs.append(init.parent)
        for init in dest.glob("src/*/__init__.py"):
            if init.parent.name.lower() in {"tests","test"}:
                continue
            package_dirs.append(init.parent)
        if not package_dirs:
            raise RelayFailure("NO_TOP_LEVEL_PYTHON_PACKAGE")

        terms = _distinctive_goal_terms(goal)
        best = None
        best_score = -1
        for package in package_dirs:
            files = sorted(p for p in package.rglob("*.py") if p.is_file())
            if not files or len(files) > 128:
                continue
            score = 0
            haystack = (full_name + " " + package.name).lower()
            for term in terms:
                if term in haystack:
                    score += 5
            for p in files[:40]:
                lname = p.name.lower()
                if any(x in lname for x in ("codec","encode","decode","dump","load","pack","ubj","json")):
                    score += 2
            if score > best_score:
                best_score, best = score, (package, files)
        if best is None:
            raise RelayFailure("NO_BOUNDED_PYTHON_PACKAGE")
        package, files = best
        files = files[:128]
        records = []
        total = 0
        for p in files:
            raw = p.read_bytes()
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            total += len(raw)
            if total > 2_000_000:
                break
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
            raise RelayFailure("SOURCE_TREE_EMPTY")
        return {
            "schema": "PROJECT_BRAIN_EXTERNAL_SOURCE_TREE_V1",
            "repository": full_name,
            "revision": rev,
            "files": records,
        }


def _handle_python_source_tree(payload):
    goal = str(payload.get("goal") or "")
    if not goal or len(goal) > 20_000:
        raise RelayFailure("SOURCE_TREE_GOAL_INVALID")
    max_trees = max(1, min(int(payload.get("max_trees") or 12), 12))
    terms = _distinctive_goal_terms(goal)
    if not terms:
        raise RelayFailure("SOURCE_TREE_SEARCH_TERMS_EMPTY")
    queries = []
    for term in terms[:4]:
        queries.append(f"{term} language:Python")
    queries.append(" ".join(terms[:4]) + " language:Python")

    repositories = []
    for query in queries[:5]:
        url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
            {"q": query, "sort": "stars", "order": "desc", "per_page": 5}
        )
        try:
            data = _github_api_json(url, timeout_s=20)
        except Exception:
            continue
        for item in data.get("items") or []:
            full_name = str(item.get("full_name") or "")
            if full_name and full_name not in repositories:
                repositories.append(full_name)
        if len(repositories) >= 8:
            break

    trees = []
    for repo in repositories[:8]:
        try:
            tree = _source_tree_from_repo(repo, goal)
            trees.append(tree)
        except Exception:
            continue
        if len(trees) >= min(max_trees, 4):
            break
    return {"trees": trees}


def _handle_pypi_wheel_closure(payload):
    project = str(payload.get("project") or "").strip()
    version = str(payload.get("version") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,120}", project):
        raise RelayFailure("PYPI_PROJECT_INVALID")
    if not version or len(version) > 80:
        raise RelayFailure("PYPI_VERSION_INVALID")
    max_wheels = max(1, min(int(payload.get("max_wheels") or 32), 32))
    max_total = max(1, min(int(payload.get("max_total_bytes") or 160_000_000), 160_000_000))
    with tempfile.TemporaryDirectory(prefix="brain-external-wheels-") as td:
        proc = subprocess.run(
            [
                sys.executable, "-m", "pip", "download",
                "--disable-pip-version-check", "--only-binary=:all:",
                "--dest", td, f"{project}=={version}",
            ],
            text=True, capture_output=True, timeout=180,
            env={**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1"},
        )
        if proc.returncode != 0:
            raise RelayFailure("PYPI_WHEEL_DOWNLOAD_FAILED:" + proc.stderr[-1200:])
        wheels = sorted(pathlib.Path(td).glob("*.whl"))
        if not wheels or len(wheels) > max_wheels:
            raise RelayFailure("PYPI_WHEEL_COUNT_INVALID")
        artifacts = []
        total = 0
        for wheel in wheels:
            raw = wheel.read_bytes()
            total += len(raw)
            if total > max_total:
                raise RelayFailure("PYPI_WHEEL_BYTES_LIMIT")
            artifacts.append({
                "filename": wheel.name,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "content_b64": base64.b64encode(raw).decode("ascii"),
            })
        return {"artifacts": artifacts}


HANDLERS = {
    "urlopen": _handle_urlopen,
    "http_get": _handle_http_get,
    "planner": _handle_planner,
    "package_name_search": _handle_package_name_search,
    "python_source_tree": _handle_python_source_tree,
    "pypi_wheel_closure": _handle_pypi_wheel_closure,
}


def execute_request(request):
    kind = str(request.get("kind") or "")
    handler = HANDLERS.get(kind)
    if handler is None:
        raise RelayFailure("REQUEST_KIND_UNSUPPORTED:" + kind)
    return handler(request["payload"])


def build_response(request, result=None, error=None):
    response = {
        "schema": RESPONSE_SCHEMA,
        "request_sha256": request["request_sha256"],
        "kind": request["kind"],
        "agent_id": request.get("agent_id"),
        "task_id": request.get("task_id"),
        "status": "ok" if error is None else "error",
    }
    if error is None:
        if not isinstance(result, dict):
            raise RelayFailure("RESULT_OBJECT_REQUIRED")
        response["result"] = result
    else:
        response["error"] = str(error)[:4000]
    return response


def _write_json_atomic(path, value):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def service_pending(bridge_dir, expected_agent=None, expected_task=None, max_requests=8):
    bridge = pathlib.Path(bridge_dir).resolve()
    bridge.mkdir(parents=True, exist_ok=True)
    serviced = []
    for request_path in sorted(bridge.glob("*.request.json")):
        if len(serviced) >= max_requests:
            break
        try:
            request = json.loads(request_path.read_text(encoding="utf-8"))
            validate_request(
                request, request_path,
                expected_agent=expected_agent,
                expected_task=expected_task,
            )
        except Exception as exc:
            raise RelayFailure(
                "REQUEST_VALIDATION_FAILED:" + request_path.name + ":" + type(exc).__name__ + ":" + str(exc)
            ) from exc
        response_path = bridge / (request["request_sha256"] + ".response.json")
        if response_path.exists():
            continue
        try:
            result = execute_request(request)
            response = build_response(request, result=result)
        except Exception as exc:
            response = build_response(
                request,
                error=type(exc).__name__ + ":" + str(exc),
            )
        _write_json_atomic(response_path, response)
        serviced.append({
            "request_sha256": request["request_sha256"],
            "kind": request["kind"],
            "status": response["status"],
            "response_path": str(response_path),
        })
    return serviced


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-dir", required=True)
    parser.add_argument("--expected-agent")
    parser.add_argument("--expected-task")
    parser.add_argument("--max-requests", type=int, default=8)
    args = parser.parse_args()
    serviced = service_pending(
        args.bridge_dir,
        expected_agent=args.expected_agent,
        expected_task=args.expected_task,
        max_requests=max(1, min(args.max_requests, 32)),
    )
    print(json.dumps({
        "schema": "PROJECT_BRAIN_EXTERNAL_RELAY_RUN_V1",
        "serviced_count": len(serviced),
        "serviced": serviced,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
