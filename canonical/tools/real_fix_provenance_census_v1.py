#!/usr/bin/env python3
"""Is the repair site on the executed path?  A census that decides whether provenance is viable.

WHY THIS MEASUREMENT
--------------------
Every repair mechanism measured on this corpus succeeds exactly when the test names the
site and fails when it does not:

  local arm (traceback site)      1/56   -- 77% of tracebacks never reach repo code
  witness inversion (return site) 0/79   -- the site was right, the target value was junk
  guard synthesis                 0/27   -- the frame was never entered from the failing test
  literal repair in a guard       1/6    -- the test named the exception, the guard named the site

So localisation is the binding constraint, and localisation has a precondition that has never
been measured: **the repair site must be on the path the failing test executes.** If it usually
is, then provenance (which function produced the wrong value) is a viable signal. If it usually
is not, no tracer can find it and the search has to be static.

WHAT THIS DOES
--------------
For each well-formed task:

  1. `changed`   -- functions whose source differs between `before` and `after`, by AST.
                    This is the TRUE repair site, and it is judge-side: it uses `after`.
  2. `executed`  -- every function in repository source that the failing test actually calls,
                    recorded by tracing the single failing node.
  3. the intersection, and the depth of the deepest changed function on the path.

NOTHING HERE IS A SOLVER. It sees `after` by construction -- it exists to measure whether a
signal exists, not to produce one. Any repair number derived from it would be a forgery.

AUTHORITY: NONE.  Producer-run sandbox measurement.  No model, no network at decision time.

Usage
-----
    python3 canonical/tools/real_fix_provenance_census_v1.py --limit 10
    python3 canonical/tools/real_fix_provenance_census_v1.py --out /tmp/prov.json
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from real_fix_oracle_baseline_v1 import CORPUS, DEFAULT_WORKDIR, Oracle  # noqa: E402

SCHEMA = "PROJECT_BRAIN_REAL_FIX_PROVENANCE_CENSUS_V1"

#: records every CALL into a repository source file: file::function
TRACER = r'''
import json, os, sys
OUT = os.environ["PROV_OUT"]
ROOT = os.environ["PROV_ROOT"]
CALLS = []
SEEN = set()
DEPTH = {"n": 0}
MAX_DEPTH = 20000

def _tracer(frame, event, arg):
    fn = frame.f_code.co_filename
    if not fn.startswith(ROOT):
        return None
    if event != "call":
        return None
    # bound by UNIQUENESS, not by call count: a 64-call cap was binding on
    # nearly every task and silently hid every call after the 64th
    key = (fn, frame.f_code.co_name)
    if key not in SEEN and DEPTH["n"] < MAX_DEPTH:
        SEEN.add(key)
        DEPTH["n"] += 1
        CALLS.append({"file": fn[len(ROOT):].lstrip("/"),
                      "function": frame.f_code.co_name,
                      "line": frame.f_lineno,
                      "depth": DEPTH["n"]})
    return _tracer

def pytest_runtest_setup(item):
    sys.settrace(_tracer)

def pytest_runtest_teardown(item, nextitem):
    sys.settrace(None)

def pytest_sessionfinish(session, exitstatus):
    try:
        with open(OUT, "w") as h:
            json.dump(CALLS, h)
    except Exception:
        pass
'''


# --------------------------------------------------------------------------- #
# judge-side: which functions did the fix change?
# --------------------------------------------------------------------------- #

def _functions(source: str) -> dict[str, str]:
    """`function -> its unparsed source`, keyed by qualified name."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    out: dict[str, str] = {}

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[prefix + child.name] = ast.unparse(child)
                walk(child, prefix + child.name + ".")
            elif isinstance(child, ast.ClassDef):
                walk(child, prefix + child.name + ".")
            else:
                walk(child, prefix)

    walk(tree, "")
    return out


def changed_functions(before: str, after: str) -> dict[str, list[str]]:
    """`modified` / `added` / `removed`, keyed by qualified function name.

    Only `modified` can appear on the path of a *before* run. A function the fix
    ADDS is unreachable by definition, so folding it into one "changed" set makes
    every task that adds a helper look off-path when it is not.
    """
    b, a = _functions(before), _functions(after)
    return {
        "modified": sorted(k for k in set(b) & set(a) if b[k] != a[k]),
        "added": sorted(set(a) - set(b)),
        "removed": sorted(set(b) - set(a)),
    }


# --------------------------------------------------------------------------- #
# the trace
# --------------------------------------------------------------------------- #

def trace(o: Oracle, node: str, timeout: float = 300.0) -> list[dict[str, Any]]:
    work = pathlib.Path(tempfile.mkdtemp(prefix="prov-", dir=str(o.path)))
    try:
        (work / "prov_plugin.py").write_text(TRACER, encoding="utf-8")
        out = work / "calls.json"
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(work)
        env["PROV_OUT"] = str(out)
        env["PROV_ROOT"] = str(o.path.resolve())
        try:
            subprocess.run([o.py, "-m", "pytest", node, "-q", "--no-header", "--tb=no",
                            "-p", "prov_plugin", "-p", "no:cacheprovider"],
                           cwd=str(o.path), capture_output=True, text=True,
                           env=env, timeout=timeout)
        except subprocess.TimeoutExpired:
            return []
        return json.loads(out.read_text()) if out.exists() else []
    finally:
        import shutil
        shutil.rmtree(work, ignore_errors=True)


def _leaf(name: str) -> str:
    return name.split(".")[-1]


# --------------------------------------------------------------------------- #
# one task
# --------------------------------------------------------------------------- #

def measure(o: Oracle, t: Mapping[str, Any]) -> dict[str, Any]:
    node = t["failed_nodes"][0]
    out: dict[str, Any] = {"node": node}
    parts = changed_functions(t["before"], t["after"])
    calls = trace(o, node)
    executed_names = {c["function"] for c in calls}
    modified, added = parts["modified"], parts["added"]

    # qualified names are not observable at runtime, so match on the leaf name
    hit = sorted({c for c in modified if _leaf(c) in executed_names})
    out.update({
        "modified": modified,
        "added": added,
        "removed": parts["removed"],
        "n_modified": len(modified),
        "n_added": len(added),
        "n_executed": len({(c["file"], c["function"]) for c in calls}),
        "n_calls": len(calls),
        "on_path": hit,
        "n_on_path": len(hit),
        "single_function_fix": len(modified) == 1 and not added,
        "path_covers_fix": bool(hit),
        "max_depth": max((c["depth"] for c in calls), default=0),
        # ordered call list, so ranking signals (deepest, last-before-assert,
        # innermost) can be evaluated without re-running anything
        "call_order": [c["function"] for c in calls],
        "call_depth": {c["function"]: c["depth"] for c in calls},
    })
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(CORPUS))
    ap.add_argument("--workdir", default=str(DEFAULT_WORKDIR))
    ap.add_argument("--well-formed", default="/tmp/wf_idx.json")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=None)
    ns = ap.parse_args(argv)

    idxs = json.loads(pathlib.Path(ns.well_formed).read_text())[ns.offset:]
    if ns.limit:
        idxs = idxs[:ns.limit]
    tasks = json.loads(pathlib.Path(ns.corpus).read_text())["tasks"]

    oracles: dict[str, Oracle] = {}
    rows: list[dict[str, Any]] = []
    for i in idxs:
        t = tasks[i]
        if not t.get("failed_nodes"):
            continue
        slug = t["repo"]
        if slug not in oracles:
            oracles[slug] = Oracle(slug, pathlib.Path(ns.workdir))
            oracles[slug].ensure()
        o = oracles[slug]
        o.checkout(t["sha"])
        o.write_source(t["source"], t["before"])
        try:
            res = measure(o, t)
        except Exception as exc:  # noqa: BLE001
            res = {"error": f"{type(exc).__name__}: {exc}"[:200]}
        res.update({"idx": i, "repo": slug, "sha": t["sha"][:10], "source": t["source"]})
        rows.append(res)
        print(f"[{i:2d}] {slug:20s} modified={res.get('n_modified')} added={res.get('n_added')} "
              f"on_path={res.get('n_on_path')} calls={res.get('n_calls')} "
              f"depth={res.get('max_depth')} covers={res.get('path_covers_fix')} "
              f"{res.get('error', '')}")
        sys.stdout.flush()
        o.write_source(t["source"], t["before"])

    ok = [r for r in rows if "error" not in r]
    summary = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "model_dependency_count": 0,
        "note": ("judge-side measurement: changed_functions uses `after`. It measures whether a "
                 "localisation signal exists. It is not a solver and produces no repair."),
        "measured": len(ok),
        "path_covers_fix": sum(1 for r in ok if r.get("path_covers_fix")),
        "single_function_fix": sum(1 for r in ok if r.get("single_function_fix")),
        "single_function_and_on_path": sum(
            1 for r in ok if r.get("single_function_fix") and r.get("n_on_path")),
        "no_calls_recorded": sum(1 for r in ok if not r.get("n_calls")),
        "rows": rows,
    }
    text = json.dumps(summary, indent=1, default=str)
    if ns.out:
        pathlib.Path(ns.out).write_text(text)
    print("\n" + "\n".join(f"  {k}: {summary[k]}" for k in
                           ("measured", "path_covers_fix", "single_function_fix",
                            "single_function_and_on_path", "no_calls_recorded")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
