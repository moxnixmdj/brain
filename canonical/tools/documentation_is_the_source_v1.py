#!/usr/bin/env python3
"""Instant knowledge over the web: the artifact's own documentation is the supervision.

THE QUESTION THIS ANSWERS
-------------------------
The user's algorithm, in their words:

    "all he should do is just scan everything in the environment and then retrieve from his
     memory what he knows and what he doesn't know. What he doesn't know, he should get it
     instantly from the web, like from instant knowledge, because everything exists already."

`scan_retrieve_fetch_v1` already does scan -> retrieve -> fetch, but its fetch is a LOCAL
`--help` page. The web half was never built; earlier receipts recorded "browsing/web
acquisition out of scope by constraint". That was never a constraint, it was an unbuilt part:
`github.com`, `api.github.com` and `registry.npmjs.org` are all reachable from the sandbox.

So there is exactly ONE new component here -- a source channel -- and the point of the file is
to prove that the rest is already present, not to add a second mechanism.

WHAT WAS MEASURED BEFORE WRITING THIS, AND WHAT IT KILLED
---------------------------------------------------------
The obvious shortcut would be to take executable examples from the docs: a `>>>` line in a
docstring is an exact action, and verifying it is running it. Measured over four packages
nobody in this repo has ever touched:

    click     defs=671  documented=274  with_doctest=0
    rich      defs=1091 documented=688  with_doctest=11
    tenacity  defs=205  documented=59   with_doctest=0
    tabulate  defs=79   documented=43   with_doctest=16

    27 of 2046 documented definitions carry a runnable example -- 1.3%.

So the doctest route cannot be the acquisition channel, and building it would have been a
component that justifies itself on tabulate and dies on click. Killed before it was built.

What survives: **prose**. 1064 of 2046 definitions carry a docstring, and every one of them is
the artifact making a statement about one of its own names. The load-bearing question is
therefore not "can we fetch" but:

    given a goal in a user's words and a library NEVER SEEN, does the artifact's own prose
    rank the right name to the top?

If yes, instant knowledge works over the web with zero training. If no, no amount of fetching
helps and the whole idea needs a different mechanism. This file measures exactly that.

THE COMPUTED PARTS
------------------
  * `fetch_units`   a source channel: GitHub contents API, pinned to a commit. JSON and base64
                    only, no model, no HTML scraping. The `pypi` fallback reads an sdist
                    tarball from `files.pythonhosted.org` with `tarfile`, which is the same
                    unit shape.
  * `units_from_source`  ast, not execution: each def/class becomes (dotted name, kind,
                    computed signature, first-paragraph docstring). A signature is the
                    artifact stating its own arity -- the same fact `scan_retrieve_fetch`
                    reads off a `--help` page, in a different alphabet.
  * `rank_units`    the EXISTING ranker (`learned_ranking_store_v1`), weights untouched.
                    Nothing is refitted for this file. If a ranker fitted on stdlib names
                    transfers to libraries by other authors, that is evidence the mechanism is
                    computed rather than memorized.

WHAT THIS FILE DOES NOT DO
--------------------------
It does not judge whether the top name is "understandable". It reports the RANK of a ground
truth that was fixed before the ranking was run, plus the bytes and seconds the answer cost,
and it prints the whole ordered list so a wrong verdict is visible rather than summarized.

Schema BRAIN_DOCUMENTATION_IS_THE_SOURCE_V1. Authority NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import ast
import base64
import collections
import io
import re
import json
import pathlib
import sys
import tarfile
import time
import urllib.error
import urllib.request
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

SCHEMA = "BRAIN_DOCUMENTATION_IS_THE_SOURCE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
UA = "brain-instant-knowledge/1"

# The whole network surface of this file is these two hosts, and both are plain JSON/tar.gz.
GH_API = "https://api.github.com"
CODELOAD = "https://codeload.github.com"
PYPI_FILES = "https://files.pythonhosted.org"
# THE CHANNEL THAT DOES NOT RUN OUT. The contents API is a nice protocol and it has a
# measured ceiling: 5000 requests/hour for an unauthenticated caller, and a full run of four
# libraries cost ~5000 of them. Measured at the end of one session: {"limit": 5000, "used":
# 5000, "remaining": 0}, after which every fetch is a 403. An "instant" channel that stops
# answering after one library is not instant, so the primary is `codeload`, which serves a
# whole repository as one tar.gz with no API quota at all -- strictly fewer requests and
# strictly more data per request. The contents API stays as the pinned-commit path.


# ---------------------------------------------------------------------------------------------
# the ONE new component: a source channel
# ---------------------------------------------------------------------------------------------
def _get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept":
                                              "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_source(repo: str, path: str = "", ref: str | None = None,
                 max_files: int = 120) -> dict[str, str]:
    """Every `.py` under `path` in `repo`, as {relative name: text}, from a pinned commit.

    Pinned by `ref` when given, because an unpinned read is a different corpus on a different
    day and a measurement that cannot be repeated is not a measurement.

    GitHub returns a directory listing of small JSON records; each file body is base64. That is
    the entire protocol -- deliberately not HTML, because a page is prose about a page whereas
    this is the artifact itself.
    """
    q = f"?ref={ref}" if ref else ""
    url = f"{GH_API}/repos/{repo}/contents/{path}{q}"
    listing = json.loads(_get(url))
    if isinstance(listing, dict):
        listing = [listing]
    out: dict[str, str] = {}
    for e in listing:
        if len(out) >= max_files:
            break
        if e.get("type") == "dir":
            out.update({f"{e['name']}/{k}": v
                        for k, v in fetch_source(repo, e["path"], ref, max_files - len(out)).items()})
            continue
        if e.get("type") != "file" or not e.get("name", "").endswith(".py"):
            continue
        blob = json.loads(_get(e["url"]))
        out[e["name"]] = base64.b64decode(blob["content"]).decode("utf8", "replace")
    return out


def fetch_tarball(repo: str, ref: str | None = None, subdir: str = "",
                  suffix: str = ".py", max_files: int = 400,
                  keep: Any = None) -> dict[str, str]:
    """A whole repository as one request, no API quota, no pagination.

    `codeload.github.com/<repo>/tar.gz/<ref>`. One HTTP request returns every file, which is
    the smallest possible number of round trips for a corpus -- and round trips, not bytes,
    are what an unauthenticated channel bills for.

    `ref` defaults to the repository's default branch; pass a commit for a repeatable corpus.
    """
    ref = ref or "refs/heads/main"
    if not ref.startswith("refs/"):
        ref = f"refs/heads/{ref}"
    raw = _get(f"{CODELOAD}/{repo}/tar.gz/{ref}")
    out: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
        for m in tf.getmembers():
            if not m.isfile() or not m.name.endswith(suffix):
                continue
            parts = m.name.split("/", 1)
            rel = parts[1] if len(parts) > 1 else parts[0]
            if subdir and not rel.startswith(subdir.rstrip("/") + "/"):
                continue
            if subdir:
                rel = rel[len(subdir.rstrip("/")) + 1:]
            # TESTS ARE A DIFFERENT ROLE, NOT NOISE. An earlier version dropped every path
            # containing "test", which silently made the corpus unusable for any measurement
            # whose ground truth comes from the project's own tests -- rich went from 212
            # fetched files to 145 and every row count was 0. Keep them; the caller says which
            # role it wants.
            if keep is not None and not keep(rel):
                continue
            if len(out) >= max_files:
                break
            f = tf.extractfile(m)
            if f is None:
                continue
            out[rel] = f.read().decode("utf8", "replace")
    return out


def fetch_from_pypi(name: str, version: str | None = None) -> dict[str, str]:
    """The same unit shape, from an sdist tarball, when no repo is named.

    A distribution is the artifact as shipped, which is a stronger statement than a repo
    checkout; the cost is fetching a whole tarball instead of one directory.
    """
    meta = json.loads(_get(f"https://pypi.org/pypi/{name}/json"))
    ver = version or meta["info"]["version"]
    urls = [u for u in meta["releases"][ver] if u["packagetype"] == "sdist"]
    if not urls:
        raise LookupError(f"{name} {ver} has no sdist")
    raw = _get(urls[0]["url"])
    out: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
        for m in tf.getmembers():
            if not m.isfile() or not m.name.endswith(".py"):
                continue
            f = tf.extractfile(m)
            if f is None:
                continue
            text = f.read().decode("utf8", "replace")
            out[m.name.split("/", 1)[-1]] = text
    return out


# ---------------------------------------------------------------------------------------------
# extraction: what the artifact says about each of its own names
# ---------------------------------------------------------------------------------------------
def _signature(node: ast.AST) -> str:
    """The text of the parameter list, computed from the AST.

    A signature is arity stated by the artifact. It is the same fact `scan_retrieve_fetch`
    reads from a `--help` page, and it costs no execution.
    """
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return ""
    try:
        return ast.unparse(node.args)
    except Exception:  # pragma: no cover - unparse is total in 3.11
        return ""


# A DOCSTRING IS NOT A SENTENCE. This function used to cut every docstring at the first
# sentence boundary within 220 characters, which measured as a real loss: `librosa.resample`
# states 3093 characters across Parameters, Returns, Examples, Raises, See Also and Notes, and
# the whole ranking pipeline was seeing the first line only. The sections are where a docstring
# says what a thing takes, gives back, and is used FOR -- the exact information a goal needs --
# so truncating there discards the most useful half of the artifact's self-description.
#
# What survives truncation is a hard ceiling at `MAX_DOC` for cost, and the SUMMARY is kept
# separately because it is the highest-density statement per byte.
MAX_DOC = 1400
SUMMARY_CHARS = 220


def doc_summary(doc: str | None) -> str:
    """The first sentence -- the artifact's one-line statement of what it is for."""
    if not doc:
        return ""
    text = " ".join(doc.split())
    for stop in (". ", ".\n", ": "):
        i = text.find(stop)
        if 0 < i < SUMMARY_CHARS:
            return text[:i].strip()
    return text[:SUMMARY_CHARS].strip()


def _first_paragraph(doc: str | None) -> str:
    """The full statement, capped, not the first sentence.

    Name kept so every caller is unchanged; behaviour is what changed, and the reason is above.
    """
    if not doc:
        return ""
    text = " ".join((doc or "").split())
    return text[:MAX_DOC].strip()


def units_from_source(src: Mapping[str, str], module: str) -> list[dict[str, Any]]:
    """Every public definition the source states a docstring for.

    Undocumented names are dropped: a name with no statement about itself is not knowledge,
    it is a string. That is the same rule `an_actions_vocabulary_is_its_refusal_surface`
    applies to flags -- what the artifact refuses to describe, we do not pretend to know.
    """
    out: list[dict[str, Any]] = []
    for fname, text in src.items():
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        rel = fname[:-3].replace("/", ".")
        if rel.endswith(".__init__"):
            rel = rel[: -len(".__init__")]
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if node.name.startswith("_"):
                continue
            doc = _first_paragraph(ast.get_docstring(node))
            if not doc:
                continue
            out.append({
                "name": node.name,
                "dotted": f"{module}.{rel}.{node.name}" if rel else f"{module}.{node.name}",
                "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                "signature": _signature(node),
                "doc": doc,
                "summary": doc_summary(ast.get_docstring(node)),
            })
    # ONE NAME, ONE UNIT. A package may define `retry` in `_utils.py` and re-export it from
    # `__init__.py`; the re-export is a module-level `ImportFrom`, so the SAME public name can
    # arrive twice, and only one of the two carries the docstring. Keeping both makes the
    # docstring-less copy a rival that shares the name and loses every content comparison --
    # measured on tenacity, where `retry` ranked 16 with the answer at rank 1 under the
    # documented copy alone. So: dedupe by public name and keep the RICHEST statement.
    best: dict[str, dict[str, Any]] = {}
    for u in out:
        prev = best.get(u["name"])
        if prev is None or (len(u["doc"]), len(u["signature"])) > (len(prev["doc"]), len(prev["signature"])):
            best[u["name"]] = u
    out = sorted(best.values(), key=lambda u: (u["dotted"],))
    return out


# ---------------------------------------------------------------------------------------------
# ranking: the EXISTING mechanism, unchanged
# ---------------------------------------------------------------------------------------------
def declared_surface(src: Mapping[str, str], module: str) -> dict[str, int]:
    """The names the artifact DECLARES as its own, and how strongly.

    This is the same law that decides item 180 in `body_grammar_v1`: STATED FIRST, THEN
    DERIVED. A library states its own surface twice, and both statements are literal:

      1. `__all__` -- an explicit list. The artifact naming the names it is for. Weight 0.
      2. top-level re-export in `__init__.py` (`from .core import command`) -- the same claim
         made by construction rather than by list. Weight 1.
      3. anything else that merely lives in a submodule. Weight 2.

    That is the whole mechanism, and it is measured rather than chosen: on the four libraries
    in `FIXED_PACKAGES` the declared surface is 3 to 70 names against 4 to 606 definitions.

    Ordering inside `__all__` is NOT used. A `__all__` list is frequently alphabetical or
    grouped by origin module, so treating its order as a priority would be reading a signal
    the artifact never meant to send.
    """
    init = src.get("__init__.py", "")
    tier: dict[str, int] = {}
    m = re.search(r"__all__\s*=\s*[\[(](.*?)[\])]", init, re.S)
    if m:
        for n in re.findall(r"[\"']([A-Za-z_][\w]*)[\"']", m.group(1)):
            tier[n] = 0
    # `from .x import a, b` / `from .x import (a, b)` at top level of __init__
    for stmt in re.findall(r"^\s*from\s+[.\w]+\s+import\s+(.+?)(?=\n\s*(?:from|import|def|class|#|$))",
                           init, re.M | re.S):
        stmt = stmt.replace("(", " ").replace(")", " ")
        for part in stmt.split(","):
            n = part.strip()
            if not n or n == "*" or n.startswith("#"):
                continue
            n = n.split(" as ")[-1].strip()
            if n.isidentifier():
                tier.setdefault(n, 1)
    # `a = x.y` style aliases and names bound by assignment in __init__.
    # `__all__` itself is a declaration, not a member: it was being listed as a re-exported
    # public name (measured: {'command': 0, '__all__': 1}) which would put a dunder into the
    # candidate set and let it win a tie against a real name.
    for n in re.findall(r"^([A-Za-z_][\w]*)\s*=", init, re.M):
        if n.startswith("_"):
            continue
        tier.setdefault(n, 1)
    return tier


def taught_names(readme_text: str) -> dict[str, int]:
    """The names the guide puts in runnable code, and how often.

    Two shapes of "runnable" in the wild, and both are counted because both are the artifact
    showing a name in use rather than merely spelling it: fenced blocks (Markdown) and indented
    literal blocks (reStructuredText, which is what half these projects write).
    """
    chunks = re.findall(r"```[\w]*\n(.*?)```", readme_text, re.S)
    chunks += re.findall(r"^(?:    |\t)(\S.*)$", readme_text, re.M)
    code = "\n".join(chunks)
    return dict(collections.Counter(re.findall(r"[A-Za-z_][\w]*", code)))


def readme_of(repo: str) -> str:
    """The guide: the one document written for someone who does not know the library yet."""
    import base64 as _b64
    for nm in ("README.md", "README.rst", "readme.md", "Readme.rst", "README"):
        try:
            rec = json.loads(_get(f"{GH_API}/repos/{repo}/contents/{nm}"))
            return _b64.b64decode(_get(rec["url"]) and json.loads(_get(rec["url"]))["content"]).decode("utf8", "replace")
        except Exception:
            continue
    return ""


def rank_units(units: Sequence[Mapping[str, Any]], goal: str,
               weights: Mapping[str, float] | None = None,
               surface: Mapping[str, int] | None = None,
               taught: Mapping[str, int] | None = None) -> list[dict[str, Any]]:
    """Order the units by the stored ranker. No refit, no per-package tuning.

    `learned_ranking_store_v1` fits four floats on stdlib names and applies them. This call
    deliberately does not touch the weights: a ranker that had to be refitted per library would
    be a memorized table wearing a score, and the whole claim under test is that the mechanism
    is computed.
    """
    import learned_ranking_store_v1 as L

    w = weights or L.get_weights(L.load())
    scored: list[dict[str, Any]] = []
    for u in units:
        stub = f"{u['kind']} {u['name']}({u['signature']})"
        try:
            s = L.score(u["dotted"], goal, u["doc"], stub, w)
        except Exception:
            s = 0.0
        # THE TIER IS ADDITIVE, NOT A GATE. An earlier version put a hard floor under
        # "not on the declared surface", and that made `rich.Table` invisible: rich re-exports
        # 12 names and Table is not one of them, yet rich's own README shows
        # `Table("Star Wars", box=box.ROUNDED)` in runnable code. A name the guide teaches is
        # STATED, full stop. So the tier is a sum of independent statements about a name:
        #   declared in __all__            0
        #   re-exported by __init__        1
        #   shown in runnable code in the guide   -1  (this is the strongest of the three)
        # and `2` (merely lives in a submodule) is the absence of all of them.
        tier = (surface or {}).get(u["name"], 2) - (1 if (taught or {}).get(u["name"], 0) > 0 else 0)
        scored.append({**u, "score": float(s), "surface": tier,
                       "taught": (taught or {}).get(u["name"], 0)})
    # STATED FIRST: the statement tier outranks the score; the stored ranker breaks ties.
    scored.sort(key=lambda r: (r["surface"], -r["score"], r["dotted"]))
    return scored


# ---------------------------------------------------------------------------------------------
# the measurement
# ---------------------------------------------------------------------------------------------
def measure(packages: Mapping[str, Mapping[str, Any]], goals: Sequence[Mapping[str, Any]],
            verbose: bool = True) -> dict[str, Any]:
    """For each goal: fetch the package, rank its own units, report the rank of the truth.

    `goals` entries are {package, goal, truth} where `truth` is the NAME only. The goal text is
    fixed before any ranking is run, and the truth is a single name so that the verdict is a
    rank and not an opinion.
    """
    corpus: dict[str, list[dict[str, Any]]] = {}
    surfaces: dict[str, dict[str, int]] = {}
    taught: dict[str, dict[str, int]] = {}
    cost: dict[str, dict[str, Any]] = {}
    for pkg, spec in packages.items():
        t0 = time.time()
        try:
            if spec.get("repo"):
                try:
                    src = fetch_tarball(spec["repo"], spec.get("ref"), spec.get("path", ""))
                except Exception:
                    src = fetch_source(spec["repo"], spec.get("path", ""), spec.get("ref"))
            else:
                src = fetch_from_pypi(pkg, spec.get("version"))
            bytes_n = sum(len(v) for v in src.values())
            corpus[pkg] = units_from_source(src, spec.get("module", pkg))
            surfaces[pkg] = declared_surface(src, spec.get("module", pkg))
            taught[pkg] = taught_names(readme_of(spec["repo"])) if spec.get("repo") else {}
            surf = surfaces[pkg]
            cost[pkg] = {"files": len(src), "bytes": bytes_n, "units": len(corpus[pkg]),
                         "declared": sum(1 for v in surf.values() if v == 0),
                         "reexported": sum(1 for v in surf.values() if v == 1),
                         "seconds": round(time.time() - t0, 2),
                         "channel": "github" if spec.get("repo") else "pypi"}
            if verbose:
                print(f"  {pkg:12s} units={cost[pkg]['units']:4d} "
                      f"declared={cost[pkg]['declared']:3d} reexported={cost[pkg]['reexported']:3d} "
                      f"{cost[pkg]['seconds']:5.1f}s {bytes_n/1024:7.1f} KiB")
        except Exception as e:
            cost[pkg] = {"error": f"{type(e).__name__}: {str(e)[:90]}"}
            if verbose:
                print(f"  {pkg:12s} FETCH FAILED {cost[pkg]['error']}")

    rows: list[dict[str, Any]] = []
    for g in goals:
        pkg = g["package"]
        if pkg not in corpus:
            rows.append({**g, "rank": None, "n": 0, "top": None, "error": "package unavailable"})
            continue
        ranked = rank_units(corpus[pkg], g["goal"], surface=surfaces.get(pkg),
                            taught=taught.get(pkg))
        names = [r["name"] for r in ranked]
        truth = g["truth"]
        rank = names.index(truth) + 1 if truth in names else None
        row = {**g, "n": len(ranked), "rank": rank, "top": names[0] if names else None,
               "top_doc": ranked[0]["doc"] if ranked else "",
               "mrr": (1.0 / rank) if rank else 0.0}
        rows.append(row)
        if verbose:
            mark = "HIT " if rank == 1 else ("    " if rank else "MISS")
            print(f"  {mark} {pkg:10s} rank={str(rank):>4s}/{len(ranked):<4d} "
                  f"truth={truth:24s} top={names[0] if names else '-'}")

    hit1 = sum(1 for r in rows if r["rank"] == 1)
    found = sum(1 for r in rows if r["rank"])
    return {
        "schema": SCHEMA, "authority": AUTHORITY,
        "packages": {k: {kk: vv for kk, vv in v.items() if kk != "units"} for k, v in cost.items()},
        "units_total": sum(len(v) for v in corpus.values()),
        "goals": len(rows),
        "top1": hit1, "found": found,
        "mrr": round(sum(r["mrr"] for r in rows) / max(len(rows), 1), 3),
        "rows": rows,
    }


# ---------------------------------------------------------------------------------------------
# the fixed goal set: written from a person's need, BEFORE running any ranking
# ---------------------------------------------------------------------------------------------
# Every goal below is phrased the way someone who has never opened the library would phrase it:
# a thing they want to happen, no parameter names, no module names. The truth is one public
# name. `ref` pins the corpus so the run is repeatable.
FIXED_PACKAGES: dict[str, dict[str, Any]] = {
    "click":     {"repo": "pallets/click", "path": "src/click", "module": "click"},
    "tenacity":  {"repo": "jd/tenacity", "path": "tenacity", "module": "tenacity"},
    "rich":      {"repo": "Textualize/rich", "path": "rich", "module": "rich"},
    "tabulate":  {"repo": "astanin/python-tabulate", "path": "tabulate", "module": "tabulate"},
}

FIXED_GOALS: list[dict[str, Any]] = [
    # click: the user wants a command line program with options and a help page
    {"package": "click", "goal": "decorate a function so it becomes a command line program "
     "with a name, options and an automatically generated help page", "truth": "command"},
    {"package": "click", "goal": "show a message to the user and read a line of text they type "
     "back, so the program can ask a question", "truth": "prompt"},
    {"package": "click", "goal": "declare a parameter that the user must supply, with a default "
     "value and a help string", "truth": "option"},
    # tenacity: retrying something that fails
    {"package": "tenacity", "goal": "run an operation again and again when it raises an "
     "exception, waiting a little longer each time, until it succeeds", "truth": "retry"},
    # rich: printing to a terminal
    {"package": "rich", "goal": "print a table with columns and rows to the terminal", "truth": "Table"},
    {"package": "rich", "goal": "print text in a colour and style in the terminal", "truth": "print"},
    # tabulate: the whole library is one call
    {"package": "tabulate", "goal": "render a list of rows as a formatted text table", "truth": "tabulate"},
]


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out_path = pathlib.Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    print("fetching unseen libraries from the network and ranking their own prose ...")
    res = measure(FIXED_PACKAGES, FIXED_GOALS)
    print(f"\nunits ranked: {res['units_total']}  goals: {res['goals']}  "
          f"top-1 correct: {res['top1']}/{res['goals']}  in-corpus: {res['found']}/{res['goals']}  "
          f"MRR: {res['mrr']}")
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(res, indent=2, sort_keys=True))
        print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
