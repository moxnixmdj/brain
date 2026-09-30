#!/usr/bin/env python3
"""Model-independent open-web source candidate discovery.

This primitive discovers provenance-bearing source candidates. It deliberately
does NOT claim that any candidate is authoritative, primary, relevant enough,
or sufficient evidence. Those are separate verification obligations.
"""
from __future__ import annotations

import hashlib
import html
import importlib.util
import json
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

SCHEMA = "PROJECT_BRAIN_OPEN_WEB_SOURCE_CANDIDATE_DISCOVERY_V1"
UA = "ProjectBrain-SourceDiscovery/1.0 (+zero-cost model-independent research)"

def _canon(text):
    return " ".join(str(text or "").strip().split())

def _query_focus(objective):
    text=_canon(objective)
    if not text:
        raise ValueError("OBJECTIVE_REQUIRED")
    if len(text)>4000:
        raise ValueError("OBJECTIVE_TOO_LONG")
    path=pathlib.Path(__file__).resolve().with_name("research_query_focus.py")
    spec=importlib.util.spec_from_file_location("project_brain_research_query_focus_discovery",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("RESEARCH_QUERY_FOCUS_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result=module.focus(text)
    if result.get("status")!="FOCUSED" or not _canon(result.get("query")):
        raise ValueError("RESEARCH_QUERY_FOCUS_UNRESOLVED")
    return result

def _query(objective):
    return _canon(_query_focus(objective).get("query"))

def _safe_url(raw):
    try:
        u = urllib.parse.urlsplit(str(raw or "").strip())
    except Exception:
        return None
    if u.scheme not in ("http", "https") or not u.netloc:
        return None
    host = (u.hostname or "").lower().strip(".")
    if (
        not host
        or host in {"localhost", "127.0.0.1", "::1"}
        or host.endswith(".local")
        or host.endswith(".internal")
    ):
        return None
    return urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, u.query, ""))

def _unwrap_ddg(raw):
    raw = html.unescape(str(raw or ""))
    if raw.startswith("//"):
        raw = "https:" + raw
    try:
        u = urllib.parse.urlsplit(raw)
    except Exception:
        return raw
    host = (u.hostname or "").lower()
    if host.endswith("duckduckgo.com"):
        qs = urllib.parse.parse_qs(u.query)
        if qs.get("uddg"):
            return urllib.parse.unquote(qs["uddg"][0])
    return raw

class _DDGParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self._href = None
        self._title = []
        self._capture = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        a = dict(attrs)
        cls = str(a.get("class") or "")
        href = a.get("href")
        if href and ("result__a" in cls or "result-link" in cls):
            self._href = href
            self._title = []
            self._capture = True

    def handle_data(self, data):
        if self._capture:
            self._title.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._capture:
            self.items.append((self._href, _canon("".join(self._title))))
            self._href = None
            self._title = []
            self._capture = False

def _fetch(url, timeout):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.1",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read(2_500_000)
        ctype = str(resp.headers.get("Content-Type") or "")
        return body, ctype, int(getattr(resp, "status", 200))


def _bing_rss(query, limit, timeout):
    endpoint = "https://www.bing.com/search?" + urllib.parse.urlencode({
        "q": query,
        "format": "rss",
    })
    body, ctype, status = _fetch(endpoint, timeout)
    root = ET.fromstring(body.decode("utf-8", "replace"))
    out = []
    for item in root.findall(".//item"):
        url = _safe_url(item.findtext("link"))
        if not url:
            continue
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
        if host.endswith("bing.com"):
            continue
        out.append({
            "url": url,
            "host": host,
            "title": _canon(item.findtext("title")),
            "snippet": _canon(item.findtext("description")),
            "source_class": "OPEN_WEB_SEARCH_CANDIDATE",
            "discovery_backend": "BING_RSS",
            "authority_status": "UNVERIFIED",
        })
        if len(out) >= limit:
            break
    return out, {
        "backend": "BING_RSS",
        "endpoint": "https://www.bing.com/search?format=rss",
        "http_status": status,
        "content_type": ctype,
        "candidate_count": len(out),
    }

def _ddg(query, limit, timeout):
    endpoint = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    body, ctype, status = _fetch(endpoint, timeout)
    parser = _DDGParser()
    parser.feed(body.decode("utf-8", "replace"))
    out = []
    for href, title in parser.items:
        url = _safe_url(_unwrap_ddg(href))
        if not url:
            continue
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
        if host.endswith("duckduckgo.com"):
            continue
        out.append({
            "url": url,
            "host": host,
            "title": title,
            "source_class": "OPEN_WEB_SEARCH_CANDIDATE",
            "discovery_backend": "DUCKDUCKGO_HTML",
            "authority_status": "UNVERIFIED",
        })
        if len(out) >= limit:
            break
    return out, {
        "backend": "DUCKDUCKGO_HTML",
        "endpoint": "https://html.duckduckgo.com/html/",
        "http_status": status,
        "content_type": ctype,
        "candidate_count": len(out),
    }

def _crossref(query, limit, timeout):
    endpoint = "https://api.crossref.org/works?" + urllib.parse.urlencode({
        "query.bibliographic": query,
        "rows": min(max(limit, 1), 20),
        "select": "DOI,title,URL,publisher,type,published",
    })
    body, ctype, status = _fetch(endpoint, timeout)
    data = json.loads(body.decode("utf-8", "replace"))
    items = (((data or {}).get("message") or {}).get("items") or [])
    out = []
    for item in items:
        doi = _canon(item.get("DOI"))
        url = _safe_url(item.get("URL") or (("https://doi.org/" + doi) if doi else ""))
        if not url:
            continue
        titles = item.get("title") or []
        title = _canon(titles[0] if titles else "")
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
        out.append({
            "url": url,
            "host": host,
            "title": title,
            "doi": doi or None,
            "publisher": _canon(item.get("publisher")) or None,
            "work_type": item.get("type"),
            "source_class": "SCHOLARLY_REGISTRY_CANDIDATE",
            "discovery_backend": "CROSSREF",
            "authority_status": "UNVERIFIED",
        })
        if len(out) >= limit:
            break
    return out, {
        "backend": "CROSSREF",
        "endpoint": "https://api.crossref.org/works",
        "http_status": status,
        "content_type": ctype,
        "candidate_count": len(out),
    }

def discover(objective, limit=12, timeout=15, query_override=None):
    original_objective=_canon(objective)
    focus=_query_focus(original_objective)
    focused_query=_canon(focus.get("query"))
    query=_canon(query_override) if query_override is not None else focused_query
    if not query:
        raise ValueError("DISCOVERY_QUERY_REQUIRED")
    if len(query)>1200:
        query=query[:1200].rsplit(" ",1)[0] or query[:1200]
    limit = max(1, min(int(limit), 40))
    timeout = max(2, min(int(timeout), 30))
    candidates = []
    traces = []
    errors = []

    for name, fn in (("BING_RSS", _bing_rss), ("DUCKDUCKGO_HTML", _ddg), ("CROSSREF", _crossref)):
        try:
            found, trace = fn(query, limit, timeout)
            candidates.extend(found)
            traces.append(trace)
        except Exception as exc:
            errors.append({
                "backend": name,
                "error_class": type(exc).__name__,
                "error": str(exc)[:500],
            })

    unique = []
    seen = set()
    for item in candidates:
        key = item.get("url")
        if not key or key in seen:
            continue
        seen.add(key)
        x = dict(item)
        x["rank"] = len(unique)
        unique.append(x)
        if len(unique) >= limit:
            break

    status = "CANDIDATES_DISCOVERED" if unique else "DISCOVERY_UNAVAILABLE"
    return {
        "schema": SCHEMA,
        "status": status,
        "objective": original_objective,
        "query": query,
        "query_focus": focus,
        "query_origin":"METADATA_REFINED_OVERRIDE" if query_override is not None else "FOCUSED_OBJECTIVE",
        "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "candidates": unique,
        "candidate_count": len(unique),
        "retrieval_provenance": traces,
        "backend_errors": errors,
        "authority_verification": "NOT_PERFORMED",
        "primary_source_verification": "NOT_PERFORMED",
        "evidence_sufficiency_verification": "NOT_PERFORMED",
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }

if __name__ == "__main__":
    import sys
    result = discover(" ".join(sys.argv[1:]))
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "CANDIDATES_DISCOVERED" else 2)
