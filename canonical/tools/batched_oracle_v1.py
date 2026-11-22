#!/usr/bin/env python3
"""Judge many candidate bodies against one item's hidden test without paying for the import.

Measured: one oracle call costs 0.95 s through the subprocess+pytest path, and **0.59 s of
that is `import sympy` alone**. Spawning a fresh interpreter per candidate means paying the
library import thousands of times to answer a question that the library only has to be
imported once to answer.

The judged object is tiny -- a function definition of a few characters -- so the cost of a
trial is dominated by process setup, not by the work. The fix is not a faster judge; it is to
stop rebuilding the world for each candidate.

A worker imports the item's own imports once, then for each candidate: executes the stub with
the candidate as its body in a FRESH namespace, and runs the hidden test's own TestCase.
Fresh namespace per trial, so one candidate's side effects cannot leak into another's verdict.

This preserves the property that matters: the verdict is still produced by executing the
benchmark's own hidden test. Nothing is predicted, sampled or approximated.

Authority: NONE. Producer-run sandbox measurement. Zero model calls.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_BATCHED_ORACLE_V1"

_WORKER = r'''
import importlib, json, sys, types, unittest, io, re

payload = json.loads(sys.stdin.read())
starting = payload["starting_code"]
tests_src = payload["tests_src"]
bodies = payload["bodies"]
modname = payload["modname"]

# The item's own imports, executed ONCE. This is the 0.59 s that the per-candidate
# subprocess path was paying 13,000 times.
ns_base = {}
for _line in starting.splitlines():
    if _line.startswith(("import ", "from ")):
        try:
            exec(_line, ns_base)
        except BaseException:
            pass

fname = None
for line in starting.splitlines():
    if line.lstrip().startswith("def "):
        fname = re.match(r"\s*def\s+([A-Za-z_]\w*)", line).group(1)
        break

def build(body, ns):
    src = starting + body + "\n"
    exec(compile(src, "<candidate>", "exec"), ns)
    return ns

# The hidden test imports `from sample_N import f`. Satisfy that with a live module object
# whose attribute is swapped per candidate -- the test's own source then compiles unchanged
# and every TestCase runs exactly as pytest would run it.
module = types.ModuleType(modname)
sys.modules[modname] = module

# The hidden test computes `os.path.dirname(os.path.abspath(__file__))` to put its own
# directory on sys.path. Executing source has no __file__, so it is supplied explicitly --
# the same file path the test would have had under pytest.
test_ns = {"__file__": payload.get("test_path", "<hidden_test>.py"),
           "__name__": "hidden_test"}
compiled = False
compile_error = ""

# The test module's `from sample_N import f` executes at compile time, so the module object
# must already carry the function before the test source is executed. Compiling is therefore
# deferred until the first candidate has been built, and repeated only if it failed.
def compile_tests():
    global compiled, compile_error
    try:
        exec(compile(tests_src, "<hidden_test>", "exec"), test_ns)
        compiled = True
    except BaseException as _exc:
        compile_error = f"{type(_exc).__name__}: {_exc}"

results = []
for body in bodies:
    ns = dict(ns_base)
    try:
        build(body, ns)
    except BaseException:
        results.append({"passed": False, "why": "definition_failed"})
        continue
    if fname is None or fname not in ns:
        results.append({"passed": False, "why": "no_function"})
        continue
    setattr(module, fname, ns[fname])
    if not compiled:
        compile_tests()
    if not compiled:
        results.append({"passed": False, "why": "tests_uncompilable", "detail": compile_error})
        continue
    # the test module imported the function by name at compile time; rebind per candidate
    if fname in test_ns:
        test_ns[fname] = ns[fname]
    ok = True
    why = "ok"
    for name, obj in list(test_ns.items()):
        if not (isinstance(obj, type) and issubclass(obj, unittest.TestCase)):
            continue
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(obj)
        runner = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0)
        try:
            res = runner.run(suite)
        except BaseException:
            ok = False; why = "runner_error"; break
        if res.failures or res.errors:
            ok = False; why = "failed"; break
    results.append({"passed": ok, "why": why})

print(json.dumps(results))
'''


def judge_many(python: str, starting_code: str, tests_src: str,
               bodies: Sequence[str], *, timeout: float = 900.0,
               test_path: str | None = None) -> list[dict]:
    """Judge every body against the item's hidden test, importing the library once."""
    modname = ""
    m = re.search(r"^\s*from\s+(\w+)\s+import\s+", tests_src, re.M)
    if m:
        modname = m.group(1)
    payload = json.dumps({"starting_code": starting_code, "tests_src": tests_src,
                          "bodies": list(bodies), "modname": modname,
                          "test_path": str(test_path or "")})
    try:
        proc = subprocess.run([python, "-c", _WORKER], input=payload, capture_output=True,
                              text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return [{"passed": False, "why": "worker_timeout"} for _ in bodies]
    lines = [l for l in (proc.stdout or "").strip().splitlines() if l.startswith("[")]
    if not lines:
        return [{"passed": False, "why": "worker_failed"} for _ in bodies]
    try:
        out = json.loads(lines[-1])
    except json.JSONDecodeError:
        return [{"passed": False, "why": "worker_bad_json"} for _ in bodies]
    if len(out) != len(bodies):
        return [{"passed": False, "why": "worker_short"} for _ in bodies]
    return out


def verify_against_pytest(bench: str | pathlib.Path, item: Mapping[str, Any], body: str,
                          *, python: str) -> bool:
    """Cross-check the batched verdict against the authoritative subprocess+pytest path."""
    import docstring_purpose_search_v1 as D

    return bool(D._run_oracle(pathlib.Path(bench), dict(item), body,
                              python=python, timeout=90)["passed"])


def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bench", required=True)
    ap.add_argument("--python", required=True)
    ap.add_argument("--item", required=True)
    ap.add_argument("--bodies", required=True, help="path to a JSON list of bodies")
    ap.add_argument("--cross-check", action="store_true")
    args = ap.parse_args(list(argv) if argv is not None else None)

    import time

    bench = pathlib.Path(args.bench)
    item = [json.loads(l) for l in (bench / "dataset" / "dataset.jsonl").read_text().splitlines()
            if l.strip() and json.loads(l)["example_id"] == args.item][0]
    tests = (bench / "dataset" / "hidden_tests" /
             f"test_sample_{args.item}.py").read_text()
    bodies = json.loads(pathlib.Path(args.bodies).read_text())

    t0 = time.time()
    verdicts = judge_many(args.python, item["starting_code"], tests, bodies)
    dt = time.time() - t0
    print(json.dumps({
        "schema": SCHEMA, "item": args.item, "n": len(bodies),
        "seconds": round(dt, 3), "per_candidate_ms": round(1000 * dt / max(len(bodies), 1), 2),
        "solved": [b for b, v in zip(bodies, verdicts) if v["passed"]][:10],
    }, indent=1))

    if args.cross_check:
        solved = [b for b, v in zip(bodies, verdicts) if v["passed"]][:5]
        for b in solved:
            agree = verify_against_pytest(bench, item, b, python=args.python)
            print(f"  cross-check {b[:44]!r} batched=True pytest={agree}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
