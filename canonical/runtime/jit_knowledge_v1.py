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
DEFAULT_MIN_KINDS = 2            # and they must be different KINDS of source
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

# Asking the same question twice is not thoroughness, it is waste -- and at
# github's unauthenticated search rate it is self-inflicted blindness: the
# burst of duplicates exhausts the allowance and the failures then look like
# the world having no data. A short cache makes repeat questions instant.
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
CACHE_TTL_S = float(os.environ.get("BRAIN_JIT_CACHE_TTL", "120"))
# A refusal is remembered briefly, not forever. Caching it for the full
# lifetime freezes whatever made it a refusal -- usually a host that was busy
# for a moment -- and hands that to every later caller as a fact about the
# world. Not caching it at all means a repeated question re-spends the network
# allowance until the sources rate-limit us into the very failure we were
# trying to avoid. Short enough to recover, long enough to stop the stampede.
CACHE_TTL_REFUSED_S = float(os.environ.get("BRAIN_JIT_CACHE_TTL_REFUSED", "10"))
CACHE_ENABLED = os.environ.get("BRAIN_JIT_CACHE", "1") != "0"


def cache_clear() -> None:
    _CACHE.clear()


def cache_stats() -> dict[str, Any]:
    now = time.time()
    live = sum(1 for exp, _ in _CACHE.values() if exp > now)
    return {"entries": len(_CACHE), "live": live}


# --------------------------------------------------------------------------- #
# sources -- each one real, each one honest about whether it answered
# --------------------------------------------------------------------------- #
def _get(url: str, timeout: int = DEFAULT_TIMEOUT_S) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return int(resp.status), resp.read()


_GH_SEARCH: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def _fetch_github(query: str, limit: int, timeout: int) -> list[dict[str, Any]]:
    """One search, shared. github's unauthenticated search allows about ten
    requests a minute, and the docs source needs the same result the github
    source just fetched -- asking twice spends the allowance on a duplicate
    and the second caller then reads the failure as 'no such data'."""
    key = f"{query}|{limit}"
    hit = _GH_SEARCH.get(key)
    if hit is not None and hit[0] > time.time():
        return list(hit[1])
    out = _gh_search(query, limit, timeout)
    # never cache an empty answer: a single transient failure would then be
    # served as "github has nothing about this" for the next minute
    if out:
        _GH_SEARCH[key] = (time.time() + 60.0, list(out))
    return out


def _gh_search(query: str, limit: int, timeout: int) -> list[dict[str, Any]]:
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


def _fetch_docs(query: str, limit: int, timeout: int) -> list[dict[str, Any]]:
    """Prose about WHAT a thing is for -- a different kind of witness entirely.

    A registry can only say that a package exists. Documentation says what
    people use it for, what problem it claims to solve, and what it does not
    do. That is not the same claim, so it is not the same kind of evidence.

    Fetched from real source tarballs over the allowed codeload host, stopping
    as soon as a README is found rather than downloading whole repositories --
    3MB of source to read 2KB of prose is not fast, and fast is required.
    """
    import io
    import tarfile
    import urllib.request

    found = _fetch_github(query, max(1, min(limit, 4)), timeout)
    out: list[dict[str, Any]] = []
    for item in found:
        full = str(item.get("id") or "")
        if "/" not in full:
            continue
        for branch in ("main", "master"):
            url = f"https://codeload.github.com/{full}/tar.gz/refs/heads/{branch}"
            try:
                req = urllib.request.Request(url, headers=_UA)
                resp = urllib.request.urlopen(req, timeout=timeout + 10)
            except Exception:
                continue
            try:
                with tarfile.open(fileobj=io.BytesIO(resp.read(4_000_000)),
                                  mode="r:gz") as tar:
                    for member in tar:
                        if not member.isfile():
                            continue
                        name = member.name.rsplit("/", 1)[-1].lower()
                        if not (name.startswith("readme")
                                and name.endswith((".md", ".rst", ".txt", ""))):
                            continue
                        if member.size > 400_000:
                            continue
                        body = tar.extractfile(member).read()
                        text = body.decode("utf-8", "replace")
                        if len(text.strip()) < 40:
                            continue
                        out.append({
                            "kind": "documentation",
                            "id": full + "#README",
                            "title": str(item.get("title") or full),
                            "summary": text[:600],
                            "url": f"https://github.com/{full}#readme",
                            "bytes": len(body),
                        })
                        break
            except Exception:
                continue
            finally:
                try:
                    resp.close()
                except Exception:
                    pass
            if out and len(out) >= limit:
                break
            break
        if len(out) >= limit:
            break
    return out


def _fetch_web(query: str, limit: int, timeout: int) -> list[dict[str, Any]]:
    """Generic web. Unreachable from a restricted network, and says so."""
    url = "https://duckduckgo.com/?q=" + urllib.parse.quote(query)
    status, body = _get(url, timeout)
    return [{"kind": "page", "id": url, "title": query, "summary": "",
             "url": url, "bytes": len(body)}]


# A KIND is what makes two sources independent evidence. github, pypi and npm
# all answer "what code exists" -- three answers from one kind of place is not
# three independent witnesses, and treating it as such is exactly the failure
# of concluding "YouTube" from one paper, merely repeated three times.
SOURCES: dict[str, dict[str, Any]] = {
    "github":      {"fetch": _fetch_github,      "cost": 1.0, "kind": "code_host",
                    "note": "code and repositories"},
    # code search requires authentication; left registered but not asked by
    # default, because an unauthenticated call is a guaranteed failure that
    # still costs a slot in the search allowance
    "github_code": {"fetch": _fetch_github_code, "cost": 1.6, "kind": "code_host",
                    "note": "code search, needs auth", "opt_in": True},
    "pypi":        {"fetch": _fetch_pypi,        "cost": 0.7, "kind": "package_registry",
                    "note": "python packages"},
    "npm":         {"fetch": _fetch_npm,         "cost": 0.7, "kind": "package_registry",
                    "note": "node packages"},
    "docs":        {"fetch": _fetch_docs,        "cost": 1.4, "kind": "documentation",
                    "note": "README prose: what a thing is FOR"},
    "web":         {"fetch": _fetch_web,         "cost": 2.0, "kind": "open_web",
                    "note": "open web, often blocked"},
}


def kinds_answered(sources: Sequence[str]) -> list[str]:
    """The distinct KINDS among the sources that answered."""
    out: list[str] = []
    for name in sources:
        kind = str((SOURCES.get(name) or {}).get("kind") or "unknown")
        if kind not in out:
            out.append(kind)
    return sorted(out)


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
    if only is None:
        names = [n for n in names if not (SOURCES.get(n) or {}).get("opt_in")]
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
    def attempt() -> tuple[list, str]:
        try:
            return list(spec["fetch"](query, limit, timeout) or []), "NO_DOCUMENTS_RETURNED"
        except urllib.error.HTTPError as exc:
            return [], f"HTTP_{exc.code}"
        except (urllib.error.URLError, OSError) as exc:
            return [], f"UNREACHABLE:{type(exc).__name__}"
        except (ValueError, json.JSONDecodeError) as exc:
            return [], f"UNPARSEABLE:{type(exc).__name__}"
        except Exception as exc:  # noqa: BLE001 - a source must never break a resolve
            return [], f"SOURCE_ERROR:{type(exc).__name__}"

    docs, reason = attempt()
    # A transient network error is not evidence about the world. Counting a
    # momentary failure as "this source has nothing to say" makes the
    # completeness gate refuse to conclude for the wrong reason -- it looked
    # like the data did not exist when really the socket hiccuped. Retry once;
    # a permanent outage still reports itself, and honestly.
    # 403/429 here are rate limits, which are transient BY NATURE: they say
    # "not right now", not "no such data". Treating one as an answer is how a
    # machine concludes the world is empty because it asked too politely.
    if not docs and reason.startswith(("UNREACHABLE", "SOURCE_ERROR", "HTTP_5",
                                       "HTTP_429", "HTTP_403", "HTTP_408")):
        time.sleep(0.4)
        docs, reason = attempt()

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
            min_kinds: int = DEFAULT_MIN_KINDS,
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

    cache_key = json.dumps([q, min_sources, min_kinds, limit,
                            sorted(only or []), parallel], sort_keys=True)
    if CACHE_ENABLED:
        hit = _CACHE.get(cache_key)
        if hit is not None and hit[0] > time.time():
            cached = dict(hit[1])
            cached["from_cache"] = True
            cached["duration_s"] = round(time.time() - started, 4)
            return cached

    names = ordered_sources(only)

    def fetch_all(subset: list[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if not subset:
            return out
        if parallel:
            with ThreadPoolExecutor(max_workers=min(8, max(1, len(subset)))) as pool:
                futs = {pool.submit(fetch_source, n, q, limit=limit,
                                    timeout=timeout): n for n in subset}
                for fut in futs:
                    try:
                        out.append(fut.result(timeout=timeout + 8))
                    except FuturesTimeout:
                        out.append({"source": futs[fut], "ok": False, "documents": [],
                                    "count": 0, "reason": "TIMEOUT",
                                    "duration_s": 0.0,
                                    "authority": "SOURCE_DID_NOT_ANSWER"})
            out.sort(key=lambda r: names.index(r["source"])
                     if r["source"] in names else 99)
        else:
            for n in subset:
                out.append(fetch_source(n, q, limit=limit, timeout=timeout))
        return out

    # STAGED: ask the cheap sources first and stop if the gate is already met.
    # Fetching READMEs out of multi-megabyte tarballs when two registries
    # already answered is not thorough, it is slow -- and the burst of it is
    # enough to make the expensive sources fail under load, which then looks
    # like the world having no data.
    cheap = [n for n in names if float((SOURCES.get(n) or {}).get("cost", 1.0)) <= 1.0]
    expensive = [n for n in names if n not in cheap]
    results = fetch_all(cheap)

    def satisfied(rows: list[dict[str, Any]]) -> bool:
        answered = [r["source"] for r in rows if r.get("ok")]
        return (len(answered) >= max(1, min_sources)
                and len(kinds_answered(answered)) >= max(1, min_kinds))

    if not satisfied(results):
        results = results + fetch_all(expensive)
        results.sort(key=lambda r: names.index(r["source"])
                     if r["source"] in names else 99)

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
    kinds = kinds_answered(sources_answered)
    # Counting sources is not enough: three package registries are one kind of
    # witness asked three times. Independence is the point of the gate, so the
    # requirement is on distinct kinds as well as on raw count.
    enough_sources = len(sources_answered) >= max(1, min_sources)
    enough_kinds = len(kinds) >= max(1, min_kinds)
    complete = enough_sources and enough_kinds
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
        "kinds_answered": kinds,
        "min_sources_required": min_sources,
        "min_kinds_required": min_kinds,
        "complete": complete,
        "detail": [{"source": r["source"], "ok": r.get("ok"),
                    "count": r.get("count", 0),
                    "reason": r.get("reason"),
                    "duration_s": r.get("duration_s")} for r in results],
        "authority": ("EXTERNAL_PUBLIC_EVIDENCE_FETCHED" if complete else
                      "INCOMPLETE_DATA_NO_CONCLUSION_DRAWN"),
        "duration_s": round(time.time() - started, 3),
    }
    out["from_cache"] = False
    # the result must be FINISHED before it is cached. Storing it first and
    # filling in the reason afterwards means a cache hit returns an answer
    # with no explanation attached -- the second caller gets a refusal it
    # cannot understand, and the field it asserts on simply is not there.
    if not complete:
        if not enough_kinds:
            out["gap"] = ("only %d of %d required distinct KINDS of source answered "
                          "(%s) -- these agree because they are the same kind of "
                          "place, not because the world agrees"
                          % (len(kinds), min_kinds, ", ".join(kinds) or "none"))
        else:
            out["gap"] = ("only %d of %d required independent sources answered"
                          % (len(sources_answered), min_sources))
    if CACHE_ENABLED and status != FAIL_NO_SOURCE:
        _CACHE[cache_key] = (time.time() +
                             (CACHE_TTL_S if complete else CACHE_TTL_REFUSED_S),
                             dict(out))
    return out


def known(query: str, **kwargs: Any) -> dict[str, Any]:
    """Compatibility name. What came back, and whether it is enough to conclude."""
    return resolve(query, **kwargs)
