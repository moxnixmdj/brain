#!/usr/bin/env python3
"""Zero-cost GitHub public-surface retrieval provider.

This module binds several residual-witness discovery surfaces to GitHub REST
search endpoints while preserving strict authority separation. It discovers
candidates only. It never claims completeness, sufficiency, acceptance credit,
or nonexistence.

Supported surfaces:
- REPOSITORY_METADATA
- CODE_CONTENT
- SYMBOLS (code-text proxy; not semantic symbol authority)
- MANIFESTS
- TESTS_EXAMPLES
- ISSUES_PRS
- COMMITS_RELEASES_BRANCHES_TAGS (commit-search subset only)

Queries remain Unicode-native. Authentication is read from GITHUB_TOKEN or
GH_TOKEN when available. Backend/API failures raise and therefore remain UNKNOWN
in the caller rather than being converted into empty-result evidence.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_GITHUB_PUBLIC_RETRIEVAL_PROVIDER_V1"
API = "https://api.github.com"
UA = "ProjectBrain-ResidualWitnessGitHub/1.0"

SUPPORTED_SURFACES = {
    "REPOSITORY_METADATA",
    "CODE_CONTENT",
    "SYMBOLS",
    "MANIFESTS",
    "TESTS_EXAMPLES",
    "ISSUES_PRS",
    "COMMITS_RELEASES_BRANCHES_TAGS",
}

_MANIFEST_NAMES = (
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "requirements.txt",
)
_TEST_PATH_TERMS = ("test", "tests", "example", "examples")


class GitHubRetrievalError(RuntimeError):
    pass


def _canon(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _token() -> str | None:
    value = _canon(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"))
    return value or None


def _request_json(
    endpoint: str,
    params: Mapping[str, Any],
    *,
    timeout: int = 20,
    opener=None,
) -> Mapping[str, Any]:
    query = urllib.parse.urlencode(
        {str(k): str(v) for k, v in params.items() if v is not None},
        doseq=True,
    )
    url = API + endpoint + ("?" + query if query else "")
    headers = {
        "User-Agent": UA,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    tok = _token()
    if tok:
        headers["Authorization"] = "Bearer " + tok
    req = urllib.request.Request(url, headers=headers)
    opener = opener or urllib.request.urlopen
    try:
        with opener(req, timeout=max(2, min(int(timeout), 30))) as resp:
            raw = resp.read(5_000_000)
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read(1000).decode("utf-8", "replace")
        except Exception:
            pass
        raise GitHubRetrievalError(
            f"GITHUB_HTTP_{getattr(exc, 'code', 'ERROR')}:{detail[:500]}"
        ) from exc
    except Exception as exc:
        raise GitHubRetrievalError(
            "GITHUB_REQUEST_FAILED:" + type(exc).__name__ + ":" + str(exc)[:500]
        ) from exc
    try:
        value = json.loads(raw.decode("utf-8", "replace"))
    except Exception as exc:
        raise GitHubRetrievalError("GITHUB_JSON_INVALID") from exc
    if not isinstance(value, Mapping):
        raise GitHubRetrievalError("GITHUB_RESPONSE_MAPPING_REQUIRED")
    return value


def _repo_name_from_api_url(url: Any) -> str | None:
    text = _canon(url)
    m = re.search(r"/repos/([^/]+/[^/?#]+)", text)
    return m.group(1) if m else None


def _code_candidate(item: Mapping[str, Any], *, mode: str) -> dict[str, Any]:
    repo = item.get("repository") if isinstance(item.get("repository"), Mapping) else {}
    return {
        "candidate_id": _canon(item.get("html_url") or item.get("url") or item.get("sha")),
        "repository": _canon(repo.get("full_name")) or None,
        "path": _canon(item.get("path") or item.get("name")) or None,
        "blob_sha": _canon(item.get("sha")) or None,
        "url": _canon(item.get("html_url") or item.get("url")) or None,
        "discovery_mode": mode,
        "authority_status": "UNVERIFIED",
    }


def _dedupe(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        key = _canon(
            row.get("candidate_id")
            or row.get("url")
            or row.get("repository")
            or row.get("name")
        )
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row)
        if len(out) >= limit:
            break
    return out


def _search_code(
    query: str,
    *,
    qualifiers: list[str] | None = None,
    limit: int = 20,
    opener=None,
) -> list[dict[str, Any]]:
    q = _canon(query)
    if not q:
        raise GitHubRetrievalError("GITHUB_QUERY_REQUIRED")
    suffix = " ".join(x for x in (qualifiers or []) if _canon(x))
    search = q + ((" " + suffix) if suffix else "")
    payload = _request_json(
        "/search/code",
        {"q": search, "per_page": min(max(int(limit), 1), 50)},
        opener=opener,
    )
    items = payload.get("items") or []
    if not isinstance(items, list):
        raise GitHubRetrievalError("GITHUB_CODE_ITEMS_LIST_REQUIRED")
    return [
        _code_candidate(item, mode="CODE_SEARCH")
        for item in items
        if isinstance(item, Mapping)
    ]


def _repository_metadata(query: str, *, limit: int, opener=None) -> list[dict[str, Any]]:
    payload = _request_json(
        "/search/repositories",
        {"q": query, "per_page": min(max(int(limit), 1), 50)},
        opener=opener,
    )
    rows = []
    for item in payload.get("items") or []:
        if not isinstance(item, Mapping):
            continue
        rows.append({
            "candidate_id": _canon(item.get("html_url") or item.get("full_name")),
            "repository": _canon(item.get("full_name")) or None,
            "url": _canon(item.get("html_url")) or None,
            "description": _canon(item.get("description")) or None,
            "language": _canon(item.get("language")) or None,
            "default_branch": _canon(item.get("default_branch")) or None,
            "archived": bool(item.get("archived")),
            "fork": bool(item.get("fork")),
            "discovery_mode": "REPOSITORY_SEARCH",
            "authority_status": "UNVERIFIED",
        })
    return rows


def _issues_prs(query: str, *, limit: int, opener=None) -> list[dict[str, Any]]:
    payload = _request_json(
        "/search/issues",
        {"q": query, "per_page": min(max(int(limit), 1), 50)},
        opener=opener,
    )
    rows = []
    for item in payload.get("items") or []:
        if not isinstance(item, Mapping):
            continue
        rows.append({
            "candidate_id": _canon(item.get("html_url") or item.get("url")),
            "repository": _repo_name_from_api_url(item.get("repository_url")),
            "url": _canon(item.get("html_url") or item.get("url")) or None,
            "title": _canon(item.get("title")) or None,
            "kind": "PULL_REQUEST" if isinstance(item.get("pull_request"), Mapping) else "ISSUE",
            "state": _canon(item.get("state")) or None,
            "discovery_mode": "ISSUE_PR_SEARCH",
            "authority_status": "UNVERIFIED",
        })
    return rows


def _commits(query: str, *, limit: int, opener=None) -> list[dict[str, Any]]:
    payload = _request_json(
        "/search/commits",
        {"q": query, "per_page": min(max(int(limit), 1), 50)},
        opener=opener,
    )
    rows = []
    for item in payload.get("items") or []:
        if not isinstance(item, Mapping):
            continue
        commit = item.get("commit") if isinstance(item.get("commit"), Mapping) else {}
        repo = item.get("repository") if isinstance(item.get("repository"), Mapping) else {}
        rows.append({
            "candidate_id": _canon(item.get("html_url") or item.get("sha")),
            "repository": _canon(repo.get("full_name")) or None,
            "commit_sha": _canon(item.get("sha")) or None,
            "url": _canon(item.get("html_url")) or None,
            "message": _canon(commit.get("message")) or None,
            "discovery_mode": "COMMIT_SEARCH_SUBSET_OF_HISTORY_SURFACE",
            "authority_status": "UNVERIFIED",
        })
    return rows


def search(
    action: Mapping[str, Any],
    *,
    limit: int = 20,
    opener=None,
) -> dict[str, Any]:
    if not isinstance(action, Mapping):
        raise ValueError("ACTION_MAPPING_REQUIRED")
    surface = _canon(action.get("surface"))
    query = _canon(action.get("query"))
    if surface not in SUPPORTED_SURFACES:
        raise GitHubRetrievalError("GITHUB_SURFACE_UNSUPPORTED:" + surface)
    if not query:
        raise GitHubRetrievalError("GITHUB_QUERY_REQUIRED")
    limit = max(1, min(int(limit), 50))

    if surface == "REPOSITORY_METADATA":
        rows = _repository_metadata(query, limit=limit, opener=opener)
        detail = "REPOSITORY_SEARCH"

    elif surface == "CODE_CONTENT":
        rows = _search_code(query, limit=limit, opener=opener)
        detail = "GLOBAL_CODE_SEARCH"

    elif surface == "SYMBOLS":
        rows = _search_code(query, limit=limit, opener=opener)
        for row in rows:
            row["discovery_mode"] = "CODE_TEXT_PROXY_FOR_SYMBOL_DISCOVERY"
        detail = "CODE_TEXT_PROXY_NOT_SYMBOL_COMPLETENESS"

    elif surface == "MANIFESTS":
        rows = []
        per = max(1, min(8, (limit + 2) // 3))
        for filename in _MANIFEST_NAMES:
            rows.extend(
                _search_code(
                    query,
                    qualifiers=[f"filename:{filename}"],
                    limit=per,
                    opener=opener,
                )
            )
            if len(_dedupe(rows, limit)) >= limit:
                break
        rows = _dedupe(rows, limit)
        for row in rows:
            row["discovery_mode"] = "MANIFEST_FILENAME_CODE_SEARCH"
        detail = "COMMON_MANIFEST_FILENAMES"

    elif surface == "TESTS_EXAMPLES":
        rows = []
        per = max(1, min(8, (limit + 1) // 2))
        for path_term in _TEST_PATH_TERMS:
            rows.extend(
                _search_code(
                    query,
                    qualifiers=[f"path:{path_term}"],
                    limit=per,
                    opener=opener,
                )
            )
            if len(_dedupe(rows, limit)) >= limit:
                break
        rows = _dedupe(rows, limit)
        for row in rows:
            row["discovery_mode"] = "TEST_EXAMPLE_PATH_CODE_SEARCH"
        detail = "COMMON_TEST_EXAMPLE_PATHS"

    elif surface == "ISSUES_PRS":
        rows = _issues_prs(query, limit=limit, opener=opener)
        detail = "GLOBAL_ISSUE_PR_SEARCH"

    else:
        rows = _commits(query, limit=limit, opener=opener)
        detail = "GLOBAL_COMMIT_SEARCH_ONLY__RELEASE_BRANCH_TAG_SUBSURFACES_OPEN"

    rows = _dedupe(rows, limit)
    return {
        "schema": SCHEMA,
        "backend_id": "GITHUB_PUBLIC_RETRIEVAL_PROVIDER_V1",
        "surface": surface,
        "query": query,
        "candidates": rows,
        "candidate_count": len(rows),
        "complete": False,
        "independently_complete": False,
        "coverage_detail": detail,
        "sufficiency_status": "UNVERIFIED",
        "acceptance_credit": 0,
        "incremental_spend_usd": 0,
    }
