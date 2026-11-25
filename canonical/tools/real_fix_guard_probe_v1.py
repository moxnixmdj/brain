#!/usr/bin/env python3
"""Can a guard be SYNTHESISED from the one place the corpus hands over a specification?

THE OPPORTUNITY, MEASURED FIRST
-------------------------------
`THE_ASSERTION_IS_NOT_A_SPECIFICATION_20261124_V1.md` measured that 14/70 real tasks fail as
`DID NOT RAISE <Exc>`.  That is a first-order requirement the test states outright:

    on THIS input, the function must raise <Exc>.

It is the only place in the corpus where a specification is handed over rather than inferred.
And it is unreachable by the existing repair mechanisms, for two measured reasons:
`witness_inversion_v1` refuses it at `isinstance(excinfo.value, AssertionError)`, and its
operation class is expression substitution anyway -- a missing guard needs a conditional
`raise` INSERTED.

WHAT THIS PROBE DOES
--------------------
Nothing new.  It wires three parts that already exist:

  1. the test file states the requirement -- `pytest.raises(<Exc>)` around a call;
  2. tracing that call and every other call to the same function in the same test file
     yields a WITNESS SET of concrete frames: one that must raise, many that must not;
  3. `angelic_cegis_v1.synthesize_guard` already harvests the vocabulary of a frame and
     CEGIS-verifies a predicate over it.

So: one positive example (must raise) and N negative examples (must not) is exactly the
input `synthesize_guard` wants, and the oracle is trivially `env is the bad one`.

The synthesised predicate is inserted as `if <pred>: raise <Exc>()` at the top of the target
function, then judged by the REAL test and by the whole test file as a failure-subset test.
The judge has the last word; a proposal is never a result.

AUTHORITY: NONE.  Producer-run sandbox measurement.  No model, no network at decision time.

Usage
-----
    python3 canonical/tools/real_fix_guard_probe_v1.py --limit 6
    python3 canonical/tools/real_fix_guard_probe_v1.py --out /tmp/guard.json
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
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "swe_kernel"))

from real_fix_oracle_baseline_v1 import CORPUS, DEFAULT_WORKDIR, Oracle  # noqa: E402

SCHEMA = "PROJECT_BRAIN_REAL_FIX_GUARD_PROBE_V1"

#: records every call to TARGET_FN inside TARGET_FILE: its locals and whether it raised
TRACER = r'''
import json, os, sys
TARGET_FILE = os.environ["GUARD_TARGET_FILE"]
TARGET_FN = os.environ["GUARD_TARGET_FN"]
OUT = os.environ["GUARD_OUT"]
RECORDS = []
CURRENT = {"node": None}

def _safe(v):
    for t in (str, int, float, bool, type(None)):
        if isinstance(v, t):
            return repr(v)
    if isinstance(v, (list, tuple)):
        try:
            return repr(list(v))
        except Exception:
            return None
    if isinstance(v, dict):
        try:
            return repr(dict(v))
        except Exception:
            return None
    return None

def _tracer(frame, event, arg):
    if frame.f_code.co_filename != TARGET_FILE or frame.f_code.co_name != TARGET_FN:
        return None
    if event == "call":
        rec = {"node": CURRENT["node"], "locals": {}, "raised": None, "returned": None}
        # capture at ENTRY, not at return: the guard is inserted at the top of
        # the function, so a local that is only assigned further down the body
        # is not in scope there.  Harvesting it produced a guard referencing
        # `value` in a function whose parameter is `name`, admitted by CEGIS and
        # rejected by the real test with UnboundLocalError.
        for k, v in frame.f_locals.items():
            if k.startswith("__"):
                continue
            sv = _safe(v)
            if sv is not None:
                rec["locals"][k] = sv
        RECORDS.append(rec)
        return _local
    return None

def _local(frame, event, arg):
    rec = RECORDS[-1] if RECORDS else None
    if rec is None:
        return _local
    if event == "exception":
        rec["raised"] = type(arg[1]).__name__ if arg and len(arg) > 1 and arg[1] is not None else None
    elif event == "return":
        rec["returned"] = _safe(arg)
        for k, v in frame.f_locals.items():
            if k.startswith("__"):
                continue
            s = _safe(v)
            if s is not None:
                rec["locals"][k] = s
    return _local

def pytest_runtest_setup(item):
    CURRENT["node"] = item.nodeid
    sys.settrace(_tracer)

def pytest_runtest_teardown(item, nextitem):
    sys.settrace(None)

def pytest_sessionfinish(session, exitstatus):
    try:
        with open(OUT, "w") as h:
            json.dump(RECORDS, h)
    except Exception:
        pass
'''


# --------------------------------------------------------------------------- #
# reading the requirement out of the test
# --------------------------------------------------------------------------- #

def _test_body(tree: ast.AST, test_name: str) -> ast.AST | None:
    """The failing test's own body.

    A test file contains many `pytest.raises` blocks; reading the first one in
    the file attributes another test's requirement to this failure.  The node id
    names the test, possibly class-qualified and parametrised
    (`TestX::test_y[a-b]`), so strip to the function name and search its body.
    """
    fname = test_name.split("[")[0].split("::")[-1].strip()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fname:
            return node
    return None


def requirement(test_source: str, test_name: str) -> dict[str, Any] | None:
    """`with pytest.raises(<Exc>[, match=...])`: <call>` -- the stated requirement."""
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return None
    body = _test_body(tree, test_name)
    if body is None:
        return None
    for node in ast.walk(body):
        if not isinstance(node, ast.With):
            continue
        for item in node.items:
            call = item.context_expr
            if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "raises"):
                continue
            if not call.args:
                continue
            exc = ast.unparse(call.args[0])
            match = next((ast.unparse(k.value) for k in call.keywords if k.arg == "match"), None)
            called = None
            calls: list[str] = []
            for st in node.body:
                value = st.value if isinstance(st, ast.Expr) else (
                    st.value if isinstance(st, ast.Assign) else None)
                if isinstance(value, ast.Call):
                    calls.append(ast.unparse(value.func))
                # `with pytest.raises(...): obj.method(x)` nested deeper
                for sub in ast.walk(st):
                    if isinstance(sub, ast.Call) and not (
                            isinstance(sub.func, ast.Attribute) and sub.func.attr == "raises"):
                        c = ast.unparse(sub.func)
                        if c not in calls:
                            calls.append(c)
            called = target_in_source("", calls)
            return {"exc": exc, "match": match, "call": called}
    return None


def target_of(repo: pathlib.Path, source: str, call: str | None) -> str | None:
    """The function the requirement is about: `parse(x)` -> `parse`, `obj.m(x)` -> `m`."""
    if not call:
        return None
    name = call.split("(")[0].strip()
    return name.split(".")[-1] if name else None


def _defined_functions(source: str) -> set[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    return {n.name for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def target_in_source(source: str, calls: Sequence[str]) -> str | None:
    """Prefer a called function that is DEFINED in the file being repaired.

    On several tasks the function that must raise lives in another module
    (`packaging.utils.parse_wheel_filename`), so inserting a guard in the task's
    own source file cannot satisfy it.  Reporting that is more useful than
    inserting a guard in the wrong file and calling it a repair.
    """
    defined = _defined_functions(source)
    for c in calls:
        n = c.split("(")[0].strip().split(".")[-1]
        if n in defined:
            return n
    return calls[0].split("(")[0].strip().split(".")[-1] if calls else None


# --------------------------------------------------------------------------- #
# the witness set
# --------------------------------------------------------------------------- #

def _trace(o: Oracle, target_file: str, target_fn: str, pytest_args: Sequence[str],
           timeout: float = 300.0) -> list[dict[str, Any]]:
    work = pathlib.Path(tempfile.mkdtemp(prefix="guard-", dir=str(o.path)))
    try:
        (work / "guard_plugin.py").write_text(TRACER, encoding="utf-8")
        out = work / "records.json"
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(work)
        env["GUARD_TARGET_FILE"] = str((o.path / target_file).resolve())
        env["GUARD_TARGET_FN"] = target_fn
        env["GUARD_OUT"] = str(out)
        try:
            subprocess.run([o.py, "-m", "pytest", *pytest_args, "-q", "--no-header",
                            "--tb=no", "-p", "guard_plugin", "-p", "no:cacheprovider"],
                           cwd=str(o.path), capture_output=True, text=True,
                           env=env, timeout=timeout)
        except subprocess.TimeoutExpired:
            return []
        return json.loads(out.read_text()) if out.exists() else []
    finally:
        import shutil
        shutil.rmtree(work, ignore_errors=True)


def _revive(text: str) -> Any:
    """Reconstruct a simple value from its repr, or None.

    Only HASHABLE values are kept: `angelic_cegis_v1.invent` prunes atoms with
    `set(observation_vector)`, so an unhashable observation (a dict local) raises
    `TypeError: unhashable type: 'dict'` and the whole synthesis dies.  Dropping
    the value keeps the existing module untouched and loses only guards that
    test a dict directly.
    """
    try:
        val = ast.literal_eval(text)
    except Exception:
        return None
    try:
        hash(val)
    except TypeError:
        return None
    return val


def environments(records: Sequence[Mapping[str, Any]],
                 bad_node: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(must_raise, must_not_raise) as concrete environments.

    The split is by WHICH TEST produced the frame, not by whether it raised.
    On a `DID NOT RAISE` task the offending frame by definition does NOT raise --
    splitting on `raised` puts every bad frame in the good set and the probe
    reports `NO_BAD_FRAME_RECORDED` while having recorded it.
    """
    bad: list[dict[str, Any]] = []
    good: list[dict[str, Any]] = []
    for rec in records:
        env: dict[str, Any] = {}
        for k, v in rec.get("locals", {}).items():
            val = _revive(v)
            if val is not None:
                env[k] = val
        if not env:
            continue
        (bad if rec.get("node") == bad_node else good).append(env)
    return bad, good


# --------------------------------------------------------------------------- #
# insertion
# --------------------------------------------------------------------------- #

def insert_guard(source: str, function: str, predicate: str, exc: str,
                 match: str | None) -> str | None:
    """`if <pred>: raise <Exc>()` as the first statement of `function`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name == function), None)
    if fn is None or not fn.body:
        return None
    lines = source.splitlines(keepends=True)
    first = fn.body[0]
    indent = " " * first.col_offset
    # the message is part of the requirement when the test states one
    msg = f" {match}" if match else ""
    block = [f"{indent}if {predicate}:\n", f"{indent}    raise {exc}({msg})\n"]
    return "".join(lines[: first.lineno - 1] + block + lines[first.lineno - 1:])


# --------------------------------------------------------------------------- #
# one task
# --------------------------------------------------------------------------- #

def probe(o: Oracle, t: Mapping[str, Any], *, budget: int = 256) -> dict[str, Any]:
    import angelic_cegis_v1 as C

    node = t["failed_nodes"][0]
    test_file, _, test_name = node.partition("::")
    test_path = o.path / test_file
    out: dict[str, Any] = {"node": node}

    req = requirement(test_path.read_text(encoding="utf-8"), test_name)
    if req is None:
        return {**out, "verdict": "NOT_A_GUARD_TASK"}
    fn = target_in_source(t["before"], [req["call"]] if req.get("call") else [])
    if not fn:
        return {**out, "verdict": "NO_TARGET_FUNCTION", "requirement": req}
    out.update({"requirement": req, "function": fn})

    # the bad frame: trace ONLY the failing node
    # one trace over the whole file: the failing test's frames are the positive
    # example, every other test's frames are the negative examples
    all_recs = _trace(o, t["source"], fn, [test_file])
    bad, good = environments(all_recs, node)
    out["witnesses"] = {"must_raise": len(bad), "must_not_raise": len(good)}
    if not bad:
        return {**out, "verdict": "NO_BAD_FRAME_RECORDED"}
    if not good:
        return {**out, "verdict": "NO_GOOD_FRAME_RECORDED"}

    # oracle: fire exactly on the frame that had to raise
    bad_keys = [dict(b) for b in bad]

    def oracle(env: Mapping[str, Any]) -> bool:
        return any(all(env.get(k) == v for k, v in b.items()) for b in bad_keys)

    bound = set()
    for e in bad + good:
        bound.update(e)
    try:
        scope = C.harvest_scope(t["before"], target=fn)
        # only names that are actually bound where the guard will be inserted;
        # everything else is a NameError waiting to happen
        for attr in ("locals", "params", "binds"):
            vals = getattr(scope, attr, None)
            if isinstance(vals, (tuple, list)):
                setattr(scope, attr, tuple(v for v in vals if v in bound))
        cegis = C.AngelicCEGIS(budget=budget)
        synth = cegis.invent(scope, oracle, bad + good, kind="guard")
    except Exception as exc:  # noqa: BLE001
        import traceback
        return {**out, "verdict": f"SYNTH_ERROR_{type(exc).__name__}",
                "detail": str(exc)[:300],
                "trace": traceback.format_exc()[-700:]}
    out["synthesis"] = {k: synth.get(k) for k in
                        ("status", "admitted", "attempts", "reason", "kind")}
    cand = synth.get("candidate") or {}
    expr = cand.get("expr") or synth.get("expr")
    out["synthesis"]["expr"] = expr
    if not expr:
        return {**out, "verdict": "NO_GUARD_ADMITTED"}

    patched = insert_guard(t["before"], fn, expr, req["exc"], req.get("match"))
    if patched is None:
        return {**out, "verdict": "INSERT_FAILED", "expression": expr}
    o.write_source(t["source"], patched)
    target_ok = o.test(t["failed_nodes"])["passed"]
    out["target_pass"] = target_ok
    if target_ok:
        base = o.fail_set([test_file])
        o.write_source(t["source"], patched)
        cand = o.fail_set([test_file])
        out["file_subset_ok"] = cand <= base
        o.write_source(t["source"], t["before"])
        if out["file_subset_ok"]:
            return {**out, "verdict": "REPAIRED", "expression": expr}
        return {**out, "verdict": "BROKE_ITS_OWN_FILE", "expression": expr}
    o.write_source(t["source"], t["before"])
    return {**out, "verdict": "GUARD_DOES_NOT_SATISFY_THE_TEST", "expression": expr}


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
        res = probe(o, t)
        if res["verdict"] == "NOT_A_GUARD_TASK":
            continue
        res.update({"idx": i, "repo": slug, "sha": t["sha"][:10], "source": t["source"]})
        rows.append(res)
        print(f"[{i:2d}] {slug:20s} {res['verdict']:34s} "
              f"fn={res.get('function')} w={res.get('witnesses')} expr={str(res.get('expression'))[:60]}")
        sys.stdout.flush()
        o.write_source(t["source"], t["before"])

    text = json.dumps({"schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX",
                       "model_dependency_count": 0, "rows": rows}, indent=1, default=str)
    if ns.out:
        pathlib.Path(ns.out).write_text(text)
    print("\nverdicts:", {v: sum(1 for r in rows if r["verdict"] == v)
                          for v in sorted({r["verdict"] for r in rows})})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
