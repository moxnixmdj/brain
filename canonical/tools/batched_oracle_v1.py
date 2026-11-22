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
import time
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

import signal

class _Hang(Exception):
    pass

def _alarm(signum, frame):
    raise _Hang()

try:
    signal.signal(signal.SIGALRM, _alarm)
except BaseException:
    pass

per_body_seconds = int(payload.get("per_body_seconds") or 5)

results = []
for body in bodies:
    # A single candidate that never returns (an infinite generator, a huge prime search) must
    # not consume the whole item's budget. It is bounded here and reported as a timeout for
    # THAT candidate only; the rest of the list still gets judged.
    try:
        signal.alarm(per_body_seconds)
    except BaseException:
        pass
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
        except _Hang:
            ok = False; why = "candidate_timeout"; break
        except BaseException:
            ok = False; why = "runner_error"; break
        if res.failures or res.errors:
            ok = False; why = "failed"; break
    try:
        signal.alarm(0)
    except BaseException:
        pass
    results.append({"passed": ok, "why": why})
    # STREAMED, and flushed. A batch result that only arrives at the end is lost entirely
    # when any later candidate hangs the worker -- and it did: index.free_symbols sits at
    # position 8 of a chunk of 25 and passes in 0.4s, but a hang at position 12 killed the
    # worker and with it the correct verdict. Streaming makes a pass survive any later hang.
    print("@@@" + json.dumps({"passed": ok, "why": why}), flush=True)
'''


def judge_many(python: str, starting_code: str, tests_src: str,
               bodies: Sequence[str], *, timeout: float = 900.0,
               test_path: str | None = None,
               per_body_seconds: int = 3) -> list[dict]:
    """Judge every body against the item's hidden test, importing the library once.

    The per-candidate limit and the worker budget must be consistent: 60 candidates at 5 s
    each is 300 s of allowance, which exceeds any sane worker timeout, so the whole item
    returns `worker_timeout` and EVERY verdict is lost -- including the correct one. The
    allowance is therefore capped by the budget rather than chosen independently.
    """
    if bodies:
        allowance = max(1, int(timeout / max(len(bodies), 1)) - 1)
        per_body_seconds = max(1, min(int(per_body_seconds), allowance))
    modname = ""
    m = re.search(r"^\s*from\s+(\w+)\s+import\s+", tests_src, re.M)
    if m:
        modname = m.group(1)
    payload = json.dumps({"starting_code": starting_code, "tests_src": tests_src,
                          "bodies": list(bodies), "modname": modname,
                          "test_path": str(test_path or ""),
                          "per_body_seconds": int(per_body_seconds)})
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


def judge_stream(python: str, starting_code: str, tests_src: str,
                 bodies: Sequence[str], *, timeout: float = 120.0,
                 test_path: str | None = None,
                 per_body_seconds: int = 2) -> dict | None:
    """Stop the moment any candidate passes, even if the worker later hangs.

    Reads the worker's output incrementally. Returns the first passing body, or None.
    """
    modname = ""
    m = re.search(r"^\s*from\s+(\w+)\s+import\s+", tests_src, re.M)
    if m:
        modname = m.group(1)
    payload = json.dumps({"starting_code": starting_code, "tests_src": tests_src,
                          "bodies": list(bodies), "modname": modname,
                          "test_path": str(test_path or ""),
                          "per_body_seconds": int(per_body_seconds)})
    proc = subprocess.Popen([python, "-c", _WORKER], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    try:
        proc.stdin.write(payload)
        proc.stdin.close()
    except (BrokenPipeError, OSError):
        return None
    deadline = time.time() + timeout
    found: list[dict] = []

    # A blocking readline cannot be interrupted by a deadline, so reading happens on a
    # daemon thread and the main thread polls. Without this the caller waits for the worker
    # to finish -- which is exactly the hang the streaming was added to survive.
    import threading

    def _reader() -> None:
        index = 0
        try:
            for line in proc.stdout:
                if not line.startswith("@@@"):
                    continue
                try:
                    verdict = json.loads(line[3:])
                except json.JSONDecodeError:
                    continue
                if verdict.get("passed"):
                    found.append({"passed": True, "index": index,
                                  "body": bodies[index] if index < len(bodies) else ""})
                    return
                index += 1
        except (ValueError, OSError):
            return

    thread = threading.Thread(target=_reader, daemon=True)
    thread.start()
    try:
        while time.time() < deadline and thread.is_alive() and not found:
            thread.join(timeout=0.2)
    finally:
        try:
            proc.kill()
        except OSError:
            pass
    return found[0] if found else None
    return None


def judge_in_chunks(python: str, starting_code: str, tests_src: str,
                    bodies: Sequence[str], *, chunk: int = 40,
                    timeout_per_chunk: float = 120.0,
                    test_path: str | None = None,
                    per_body_seconds: int = 2) -> list[dict]:
    """Judge a long candidate list in bounded chunks, stopping at the first pass.

    A 600-entry candidate list in one worker call either exceeds the budget and returns
    `worker_timeout` for every entry, or forces a per-candidate allowance so small that the
    real answer is scored as a failure. Neither is acceptable, and both were observed.
    Chunking bounds each call independently: a pathological block of candidates costs one
    chunk, not the item.
    """
    out: list[dict] = []
    for start in range(0, len(bodies), max(1, chunk)):
        part = list(bodies[start:start + max(1, chunk)])
        verdicts = judge_many(python, starting_code, tests_src, part,
                              timeout=timeout_per_chunk, test_path=test_path,
                              per_body_seconds=per_body_seconds)
        out.extend(verdicts)
        if any(v.get("passed") for v in verdicts):
            # everything after this point is irrelevant; keep lengths aligned
            out.extend({"passed": False, "why": "not_run"} for _ in bodies[len(out):])
            return out
        if all(v.get("why") in ("worker_timeout", "worker_failed", "worker_bad_json",
                                "worker_short") for v in verdicts):
            # the whole chunk died: report it, but do not abandon the remaining chunks
            continue
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
