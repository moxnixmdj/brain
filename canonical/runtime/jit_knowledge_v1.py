"""Just-in-time knowledge: the machine goes and gets what it does not have.

The owner's requirement, verbatim: "I don't have the data, so I must figure out
the fastest way to get this data." That sentence IS this module. Until now the
channel was registered but empty -- `knowledge.json.fetch.external` names an
adapter that exists nowhere in the repo, so a data gap had nowhere to go.

The second requirement shapes the whole design. One source is never enough:

    "If this is the only source that it knows about, it will extrapolate that
    the fastest way is YouTube videos ... just from the data that it knows."

That failure is prevented structurally, not by advice. A resolve() must gather
INDEPENDENT sources and pass a completeness gate before anything is called
known. One source cannot conclude anything, and the refusal says so.

What is admitted is the governance law's own list: pre-existing facts,
documents, records, measurements, specifications and public evidence. Nothing
here counts as the machine's own capability -- external knowledge is external,
and every document carries where it came from.

Sources are REACHABLE AND REAL. github, pypi and npm respond from this sandbox,
so the machinery is proven against live traffic rather than against a fixture.
A generic web source is present too and reports itself unreachable honestly
rather than pretending.

Which source is tried first is EARNED. Sources that produced something useful
rise; sources that came back empty or failed fall. Nothing here is a fixed
sequence -- the order is the machine's experience of where knowledge actually
is, and it differs per machine.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_JIT_KNOWLEDGE_V1"

PASS = "PASS__JIT_KNOWLEDGE_RESOLVED"
OPEN_THIN = "OPEN__JIT_KNOWLEDGE_INCOMPLETE_DATA"
FAIL_NO_SOURCE = "FAIL__JIT_KNOWLEDGE_NO_SOURCE_REACHABLE"
FAIL_EMPTY = "FAIL_CLOSED__JIT_KNOWLEDGE_EMPTY_QUERY"

DEFAULT_MIN_SOURCES = 2          # one source cannot conclude anything
DEFAULT_TIMEOUT_S = 12
DEFAULT_LIMIT = 5

STATE_PATH = os.environ.get(
    "BRAIN_JIT_KNOWLEDGE_STATE")
if not STATE_PATH:
    STATE_PATH = str(Path(__file__).resolve().parent.parent.parent
                     / "canonical" / "astra_runtime" / "state"
                     / "JIT_KNOWLEDGE_SOURCE_VALUE_V1.json")

_UA = {"User-Agent": "project-brain-jit-knowledge/1",
       "Accept": "application/json"}


# --------------------------------------------------------------------------- #
# sources -- each one real, each one honest about whether it answered
# --------------------------------------------------------------------------- #
def _get(url: str, timeout: int = DEFAULT_TIMEOUT_S) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return int(resp.status), resp.read()


def _fetch_github(query: str, limit: int, timeout: int) -> list[dict[str, Any]]:
    url = ("https://api.github.com/search/repositories?q="
           + urllib.parse.quote(query) + f"&per_page={max(1, min(limit, 10))}")
    status, body = _get(url, timeout)
    data = json.loads(body)
    out = []
    for item in (data.get("items") or [])[:limit]:
        out.append({
            "kind": "repository",
            "id": str(item.get("full_name") or ""),
            "title": str(item.get("full_name") or ""),
            "summary": str(item.get("description") or "")[:400],
            "url": str(item.get("html_url") or ""),
            "stars": item.get("stargazers_count"),
            "language": item.get("language"),
        })
    return out


def _fetch_github_code(query: str, limit: int, timeout: int) -> list[dict[str, Any]]:
    url = ("https://api.github.com/search/code?q=" + urllib.parse.quote(query)
           + f"&per_page={max(1, min(limit, 10))}")
    status, body = _get(url, timeout)
    data = json.loads(body)
    out = []
    for item in (data.get("items") or [])[:limit]:
        out.append({
            "kind": "code",
            "id": str(item.get("path") or ""),
            "title": str(item.get("name") or ""),
            "summary": str((item.get("repository") or {}).get("full_name") or ""),
            "url": str(item.get("html_url") or ""),
        })
    return out


def _fetch_pypi(query: str, limit: int, timeout: int) -> list[dict[str, Any]]:
    # pypi has no search API; the simple index is a real, complete record
    terms = [t for t in query.lower().split() if len(t) > 2][:3]
    out: list[dict[str, Any]] = []
    for term in terms:
        try:
            status, body = _get(f"https://pypi.org/pypi/{urllib.parse.quote(term)}/json",
                                timeout)
        except urllib.error.HTTPError:
            continue
        except Exception:
            continue
        info = (json.loads(body) or {}).get("info") or {}
        if not info.get("name"):
            continue
        out.append({
            "kind": "package",
            "id": str(info.get("name")),
            "title": f"{info.get('name')} {info.get('version') or ''}".strip(),
            "summary": str(info.get("summary") or "")[:400],
            "url": str(info.get("project_url") or info.get("package_url") or ""),
            "version": info.get("version"),
        })
        if len(out) >= limit:
            break
    return out


def _fetch_npm(query: str, limit: int, timeout: int) -> list[dict[str, Any]]:
    url = ("https://registry.npmjs.org/-/v1/search?text="
           + urllib.parse.quote(query) + f"&size={max(1, min(limit, 10))}")
    status, body = _get(url, timeout)
    data = json.loads(body)
    out = []
    for obj in (data.get("objects") or [])[:limit]:
        pkg = obj.get("package") or {}
        out.append({
            "kind": "package",
            "id": str(pkg.get("name") or ""),
            "title": f"{pkg.get('name')} {pkg.get('version') or ''}".strip(),
            "summary": str(pkg.get("description") or "")[:400],
            "url": str((pkg.get("links") or {}).get("npm") or ""),
            "version": pkg.get("version"),
        })
    return out


def _fetch_web(query: str, limit: int, timeout: int) -> list[dict[str, Any]]:
    """Generic web. Unreachable from a restricted network, and says so."""
    url = "https://duckduckgo.com/?q=" + urllib.parse.quote(query)
    status, body = _get(url, timeout)
    return [{"kind": "page", "id": url, "title": query, "summary": "",
             "url": url, "bytes": len(body)}]


SOURCES: dict[str, dict[str, Any]] = {
    "github":      {"fetch": _fetch_github,      "cost": 1.0, "note": "code and repositories"},
    "github_code": {"fetch": _fetch_github_code, "cost": 1.6, "note": "code search, needs auth"},
    "pypi":        {"fetch": _fetch_pypi,        "cost": 0.7, "note": "python packages"},
    "npm":         {"fetch": _fetch_npm,         "cost": 0.7, "note": "node packages"},
    "web":         {"fetch": _fetch_web,         "cost": 2.0, "note": "open web, often blocked"},
}


# --------------------------------------------------------------------------- #
# earned order -- where knowledge actually turned out to be
# --------------------------------------------------------------------------- #
def _load_state() -> dict[str, Any]:
    try:
        with open(STATE_PATH) as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(state: Mapping[str, Any]) -> None:
    try:
        Path(STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(str(STATE_PATH) + ".tmp")
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(STATE_PATH)
    except OSError:
        pass


def source_value(name: str) -> float:
    """p_useful / (1 + cost), from what this source has actually delivered."""
    spec = SOURCES.get(name) or {}
    cost = float(spec.get("cost", 1.0))
    seen = _load_state().get(name) or {}
    trials = int(seen.get("trials", 0) or 0)
    helped = int(seen.get("helped", 0) or 0)
    p = (helped + 0.5) / (trials + 1)          # same prior the ledger uses
    return p / (1.0 + cost)


def credit(name: str, helped: bool) -> None:
    """Did asking here actually produce knowledge? This is what earns the order."""
    state = _load_state()
    row = dict(state.get(name) or {})
    row["trials"] = int(row.get("trials", 0) or 0) + 1
    row["helped"] = int(row.get("helped", 0) or 0) + (1 if helped else 0)
    row["last_seen_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state[name] = row
    _save_state(state)


def ordered_sources(only: Sequence[str] | None = None) -> list[str]:
    """Sources, best-value first. Experience decides; nothing here is fixed."""
    names = [n for n in (only or list(SOURCES)) if n in SOURCES]
    return sorted(names, key=lambda n: (-source_value(n), n))


# --------------------------------------------------------------------------- #
# resolution
# --------------------------------------------------------------------------- #
def fetch_source(name: str, query: str, *, limit: int = DEFAULT_LIMIT,
                 timeout: int = DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    """One source, one answer, with provenance and an honest failure."""
    started = time.time()
    spec = SOURCES.get(name)
    if spec is None:
        return {"source": name, "ok": False, "documents": [],
                "reason": "UNKNOWN_SOURCE", "duration_s": 0.0}
    # a source that answers with nothing has not failed -- it just found
    # nothing. Without this the reason would be left unbound and the reporting
    # of an empty answer would crash, which is how a source going quiet takes
    # down the whole resolve instead of being recorded as quiet.
    reason = "NO_DOCUMENTS_RETURNED"
    try:
        docs = spec["fetch"](query, limit, timeout)
    except urllib.error.HTTPError as exc:
        docs, reason = [], f"HTTP_{exc.code}"
    except (urllib.error.URLError, OSError) as exc:
        docs, reason = [], f"UNREACHABLE:{type(exc).__name__}"
    except (ValueError, json.JSONDecodeError) as exc:
        docs, reason = [], f"UNPARSEABLE:{type(exc).__name__}"
    except Exception as exc:  # noqa: BLE001 - a source must never break a resolve
        docs, reason = [], f"SOURCE_ERROR:{type(exc).__name__}"

    ok = bool(docs)
    out = {
        "source": name,
        "ok": ok,
        "documents": docs,
        "count": len(docs),
        "duration_s": round(time.time() - started, 3),
        "authority": "EXTERNAL_PUBLIC_EVIDENCE_FETCHED" if ok else
                     "SOURCE_DID_NOT_ANSWER",
    }
    if not ok:
        out["reason"] = reason
    credit(name, ok)
    return out


def resolve(query: str, *, min_sources: int = DEFAULT_MIN_SOURCES,
            limit: int = DEFAULT_LIMIT, timeout: int = DEFAULT_TIMEOUT_S,
            only: Sequence[str] | None = None,
            parallel: bool = True) -> dict[str, Any]:
    """Get the data, from more than one place, before anything is called known.

    One source is exactly how "one paper said YouTube" becomes a conclusion, so
    fewer than `min_sources` independent answers is not a thin result -- it is
    an OPEN one, and the caller is told the data is incomplete rather than
    handed a confident guess.
    """
    started = time.time()
    q = str(query or "").strip()
    if not q:
        return {"schema": SCHEMA, "status": FAIL_EMPTY, "pass": False,
                "query": q, "documents": [], "sources": [],
                "authority": "NO_QUERY_NO_KNOWLEDGE"}

    names = ordered_sources(only)
    results: list[dict[str, Any]] = []
    if parallel:
        with ThreadPoolExecutor(max_workers=min(8, max(1, len(names)))) as pool:
            futs = {pool.submit(fetch_source, n, q, limit=limit, timeout=timeout): n
                    for n in names}
            for fut in futs:
                try:
                    results.append(fut.result(timeout=timeout + 8))
                except FuturesTimeout:
                    results.append({"source": futs[fut], "ok": False, "documents": [],
                                    "count": 0, "reason": "TIMEOUT", "duration_s": 0.0,
                                    "authority": "SOURCE_DID_NOT_ANSWER"})
        results.sort(key=lambda r: names.index(r["source"]) if r["source"] in names else 99)
    else:
        for n in names:
            results.append(fetch_source(n, q, limit=limit, timeout=timeout))

    answered = [r for r in results if r.get("ok")]
    documents: list[dict[str, Any]] = []
    for r in answered:
        for doc in r.get("documents") or []:
            body = json.dumps(doc, sort_keys=True, default=str)
            documents.append({
                **doc,
                "source": r["source"],
                "authority": "EXTERNAL_PUBLIC_EVIDENCE_FETCHED",
                "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()[:16],
            })

    sources_answered = [r["source"] for r in answered]
    complete = len(sources_answered) >= max(1, min_sources)
    status = PASS if complete else (
        OPEN_THIN if answered else FAIL_NO_SOURCE)

    out = {
        "schema": SCHEMA,
        "status": status,
        "pass": status == PASS,
        "query": q,
        "documents": documents,
        "document_count": len(documents),
        "sources_asked": names,
        "sources_answered": sources_answered,
        "sources_failed": [r["source"] for r in results if not r.get("ok")],
        "min_sources_required": min_sources,
        "complete": complete,
        "detail": [{"source": r["source"], "ok": r.get("ok"),
                    "count": r.get("count", 0),
                    "reason": r.get("reason"),
                    "duration_s": r.get("duration_s")} for r in results],
        "authority": ("EXTERNAL_PUBLIC_EVIDENCE_FETCHED" if complete else
                      "INCOMPLETE_DATA_NO_CONCLUSION_DRAWN"),
        "duration_s": round(time.time() - started, 3),
    }
    if not complete:
        out["gap"] = ("only %d of %d required independent sources answered"
                      % (len(sources_answered), min_sources))
    return out


def known(query: str, **kwargs: Any) -> dict[str, Any]:
    """Compatibility name. What came back, and whether it is enough to conclude."""
    return resolve(query, **kwargs)
