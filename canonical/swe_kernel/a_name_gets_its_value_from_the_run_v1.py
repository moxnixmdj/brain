"""Resolve a blocked name from the value the program actually passed through it.

THE BOTTLENECK
--------------
`every_call_site_v1` measured executability over three repositories: 17.3%, 25.0%, 6.2%.
The dominant refusal was a bare `Name`. A name has no value at parse time. A RUNNING
program has one, in the local variable at the moment the call executes.

Five attempts to observe it failed before one worked, and every failure produced a clean
number that measured nothing:

  1. `exec`-ing test files -- every `from x import y` breaks. 11 files "ran", 0 completed.
  2. `sys.executable` as the child -- a bare python3 with no pytest exits 1, and the
     instrument still reported OK with 19 pairs seen at import time.
  3. `sys.settrace` around `subprocess.run([... -m pytest])` -- **hits: 0** while 26,852
     tests passed. A trace cannot cross a process boundary.
  4. pytest importing the INSTALLED copy of the package instead of the tree under study:
     2 collection errors, 69 failures, no project frame -- and a clean "0 converted".
  5. `sitecustomize` -- it is imported BEFORE pytest exists, and pytest manages its own
     trace during collection, so a tracer installed there is silently replaced.

What works is a pytest PLUGIN loaded with `-p`, which installs the trace from
`pytest_collection_finish` -- after collection, in the same process that runs the tests.
The flag that fixes the last one is `src/` first on PYTHONPATH so the tree, not
site-packages, is what runs.

A cost finding: tracing every frame made a 20 s suite exceed 600 s. The filter is therefore
name-first (a set lookup) and only then a path check.

WHAT IS MEASURED
----------------
For each call site whose only defect is an unresolvable bare Name: was the callee entered at
all, and was the parameter value witnessed with ONE type? A site converts only when both
hold. Everything else stays refused and is counted as refused.

Schema BRAIN_A_NAME_GETS_ITS_VALUE_FROM_THE_RUN_V1.
Authority NONE__PRODUCER_RUN_SANDBOX. No model, no network.
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
from typing import Any, Mapping

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import every_call_site_v1 as E  # noqa: E402

SCHEMA = "BRAIN_A_NAME_GETS_ITS_VALUE_FROM_THE_RUN_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

PLUGIN_NAME = "brain_witness"

WITNESS_PLUGIN = '''"""A pytest plugin that records the value of every argument reaching project code."""
import json
import math
import os
import pathlib
import sys

SINK = os.environ.get("BRAIN_WITNESS_SINK")
ROOT = None
SEEN = {}


def canon(value):
    if value is None:
        return ["none", None]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["int", value]
    if isinstance(value, float):
        return ["float", value if math.isfinite(value) else str(value)]
    if isinstance(value, str):
        return ["str", value[:60]]
    return [type(value).__name__, None]


TARGETS = set(json.loads(os.environ.get("BRAIN_WITNESS_TARGETS") or "[]"))
MINE = {}


def ours(frame):
    """Cheap enough to run on every call in the process.

    A path resolution per frame is what made this instrument take >900 s. The file is
    resolved ONCE per code object and cached, and the name set is checked first, so the
    common case is one set membership test.
    """
    code = frame.f_code
    known = MINE.get(code)
    if known is not None:
        return known
    hit = False
    if code.co_name in TARGETS:
        try:
            hit = ROOT in pathlib.Path(code.co_filename).resolve().parents
        except Exception:
            hit = False
    MINE[code] = hit
    return hit


def trace(frame, event, arg):
    if event != "call" or not ours(frame):
        return None
    code = frame.f_code
    count = code.co_argcount + code.co_kwonlyargcount
    for index, name in enumerate(code.co_varnames[:count]):
        if name in frame.f_locals:
            kind, value = canon(frame.f_locals[name])
            slot = SEEN.setdefault(code.co_name + "|" + str(index),
                                   {"types": {}, "values": {}, "param": name})
            slot["types"][kind] = slot["types"].get(kind, 0) + 1
            if value is not None:
                bucket = slot["values"].setdefault(kind, [])
                if value not in bucket and len(bucket) < 4:
                    bucket.append(value)
    return None


def dump():
    if not SINK:
        return
    sys.settrace(None)
    try:
        with open(SINK, "w") as handle:
            json.dump(SEEN, handle)
    except Exception:
        pass


def pytest_runtest_setup(item):
    """Trace only while a test is running.

    Tracing from collection onward re-traced pytest's own machinery and turned a 40 s
    suite into more than 900 s. The observation is only needed while a test body executes,
    so the trace goes on at setup and off at teardown.
    """
    del item
    global ROOT
    if ROOT is None:
        ROOT = pathlib.Path(os.environ["BRAIN_WITNESS_ROOT"]).resolve()
    sys.settrace(trace)


def pytest_runtest_teardown(item, nextitem):
    del item, nextitem
    sys.settrace(None)


def pytest_sessionfinish(session, exitstatus):
    del session, exitstatus
    dump()
'''


def _interpreter_with_pytest() -> str:
    for candidate in ("/tmp/brainvenv/bin/python", sys.executable):
        if not pathlib.Path(candidate).exists():
            continue
        try:
            done = subprocess.run([candidate, "-c", "import pytest"], capture_output=True,
                                  timeout=60)
        except (OSError, subprocess.SubprocessError):
            continue
        if done.returncode == 0:
            return candidate
    return sys.executable


def blocked_sites(tree: pathlib.Path) -> list[dict[str, Any]]:
    """Every call site whose ONLY defect is an unresolvable bare Name."""
    out: list[dict[str, Any]] = []
    for path in sorted(tree.rglob("*.py")):
        if ".git" in path.parts:
            continue
        module = E.module_tree(path)
        if module is None:
            continue
        defined = E.defined_functions(module)
        if not defined:
            continue
        constants = E.AC.module_constants(module)
        holders = [ast.Module(body=[s for s in module.body if not isinstance(
            s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))], type_ignores=[])]
        holders += [n for n in ast.walk(module)
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for holder in holders:
            scope = {} if isinstance(holder, ast.Module) else E.AC._scope_of(holder)
            for call in [n for n in ast.walk(holder) if isinstance(n, ast.Call)]:
                if not isinstance(call.func, ast.Name) or call.func.id not in defined:
                    continue
                if call.keywords or any(isinstance(a, ast.Starred) for a in call.args):
                    continue
                tokens = [E._token_for(a, scope, constants) for a in call.args]
                blocked = [a.id for a, t in zip(call.args, tokens)
                           if t is None and isinstance(a, ast.Name)]
                others_bad = any(t is None and not isinstance(a, ast.Name)
                                 for a, t in zip(call.args, tokens))
                if not blocked or others_bad:
                    continue
                try:
                    rel = str(path.relative_to(tree))
                except ValueError:
                    rel = path.name
                blocked_positions = [i for i, token in enumerate(tokens)
                                     if token is None]
                out.append({"file": rel, "line": call.lineno, "callee": call.func.id,
                            "blocked_names": blocked,
                            "blocked_positions": blocked_positions})
    return out


def witness(tree: pathlib.Path, timeout: float = 900.0) -> dict[str, Any]:
    """Run the suite with a tracer installed from a pytest plugin, in the tree's own process."""
    src = tree / "src" if (tree / "src").is_dir() else tree
    with tempfile.TemporaryDirectory(prefix="witness-") as scratch:
        boost = pathlib.Path(scratch) / "boost"
        boost.mkdir()
        (boost / f"{PLUGIN_NAME}.py").write_text(WITNESS_PLUGIN)
        sink = pathlib.Path(scratch) / "witness.json"
        env = {
            "PYTHONPATH": f"{boost}{os.pathsep}{src}",
            "BRAIN_WITNESS_SINK": str(sink),
            "BRAIN_WITNESS_ROOT": str(tree.resolve()),
            "BRAIN_WITNESS_TARGETS": json.dumps(sorted(
                {site["callee"] for site in blocked_sites(tree)})),
            "PATH": "/usr/bin:/bin",
            "HOME": "/tmp",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        interpreter = _interpreter_with_pytest()
        try:
            done = subprocess.run(
                [interpreter, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider",
                 "-p", PLUGIN_NAME, "--continue-on-collection-errors"],
                cwd=str(tree), capture_output=True, text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            return {"seen": {}, "reason": "TIMEOUT", "interpreter": interpreter}
        tail = (done.stdout or "").strip().splitlines()[-1:] or [""]
        seen = json.loads(sink.read_text()) if sink.exists() else {}
        return {"seen": seen, "reason": "OK" if seen else "NO_WITNESS",
                "pytest": tail[0][:120], "interpreter": interpreter,
                "returncode": done.returncode}


def convert(sites: list[dict[str, Any]], seen: Mapping[str, Any]) -> list[dict[str, Any]]:
    """A site converts only if every blocked name was witnessed with one single type."""
    out = []
    for site in sites:
        positions = site.get("blocked_positions") or []
        if not positions:
            continue
        witnesses = []
        for position in positions:
            slot = seen.get(f"{site['callee']}|{position}")
            if not slot:
                break
            types = slot.get("types", {})
            if len(types) != 1:
                break
            kind, count = next(iter(types.items()))
            witnesses.append({"position": position, "param": slot.get("param"),
                              "type": kind, "count": count,
                              "values": slot.get("values", {}).get(kind, [])})
        if witnesses and len(witnesses) == len(positions):
            out.append({**site, "witnessed": witnesses})
    return out


def run(tree: pathlib.Path, receipt: pathlib.Path | None = None) -> dict[str, Any]:
    sites = blocked_sites(tree)
    got = witness(tree)
    seen = got.get("seen", {})
    converted = convert(sites, seen)
    targets = {s["callee"] for s in sites}
    hits = {k: v for k, v in seen.items() if k.split("|")[0] in targets}
    report = {
        "schema": SCHEMA, "authority": AUTHORITY, "tree": str(tree),
        "blocked_sites": len(sites),
        "distinct_blocked_callees": len(targets),
        "witnessed_pairs": len(seen),
        "target_pairs_witnessed": len(hits),
        "converted_sites": len(converted),
        "conversion_rate": round(len(converted) / len(sites), 4) if sites else 0.0,
        "witness_reason": got.get("reason"),
        "pytest": got.get("pytest"),
        "interpreter": got.get("interpreter"),
        "converted": converted[:40],
        "target_witness_sample": [{"key": k, **v} for k, v in list(hits.items())[:12]],
    }
    if receipt:
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(report, indent=1, sort_keys=True))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tree", nargs="?", default="/tmp/repos/pypa_packaging@24.0")
    parser.add_argument("--json", type=pathlib.Path)
    args = parser.parse_args(argv)
    report = run(pathlib.Path(args.tree), args.json)
    print(json.dumps({k: report[k] for k in
                      ("blocked_sites", "distinct_blocked_callees", "witnessed_pairs",
                       "target_pairs_witnessed", "converted_sites", "conversion_rate",
                       "witness_reason", "pytest")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
