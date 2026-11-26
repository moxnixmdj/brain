#!/usr/bin/env python3
"""Zero-Leakage Causal SWE Repair Engine.

Given ONLY `(worktree, test_target)` -- NEVER a fix commit SHA, diff, or target line:
  1. Dynamically traces failing vs. passing test executions at native C speed outside
     the project source tree (`sys.settrace` returning `None` for non-project frames),
     computing Ochiai fault localization, crash stack frames, `DID NOT RAISE` targets,
     live local variable snapshots, falsy-non-None guards, and single-pass iterators.
  2. Synthesizes minimal, frame-consistent candidate repairs across five first-principles
     semantic operator families:
       - `GUARD_PROJECTION_AND_POLARITY`: falsy-non-None (`x` -> `x is not None`),
         relational/boundary flips (`<` <-> `<=`, `==` <-> `!=`, `in` <-> `not in`),
         membership widening from failing-frame values (`x != 'a'` -> `x not in ('a', 'b')`),
         and frame-discriminated conjunctive/disjunctive guards (`C and P`, `C or P`);
       - `ITERATOR_AND_PROTOCOL_MATERIALIZATION`: single-pass iterator exhaustion
         (`fn(...)` -> `tuple(fn(...))` / `list(fn(...))`) and boundary coercions;
       - `DID_NOT_RAISE_VALIDATION`: widening existing `if C: raise ExpectedExc(...)`
         guards with minimal predicates separating the failing invalid input from 100%
         of passing valid frames;
       - `EXCEPTION_GUARD_AND_TRANSLATION`: guarding `None`/empty/bounds crashes or
         translating uncaught parser errors into the domain exception demanded by
         `pytest.raises(ExpectedExc)`;
       - `DEMAND_ALIGNED_EXPRESSION`: dynamic assertion operand alignment, induced
         `f-string` templates over live frame variables, cross-attribute projections,
         and off-by-one index/slice repairs.
  3. Verifies every surviving patch on the FULL unmodified test file with bytecode
     caching completely disabled (`PYTHONDONTWRITEBYTECODE=1` + `__pycache__` purge),
     requiring 100% of failing tests to turn green AND 100% of previously passing
     tests to remain green, while rejecting constant/literal test-echoing cheats.
  4. Persists only operator-family value/cost posteriors and variable-erased structural
     schemas in an inspectable, refutable external store (`SWERepairMemory`).

Model calls: 0. Stored world-fact weights: 0. Answer/diff leakage: 0. Authority: NONE.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from canonical.swe_kernel import first_principles_mental_cegis_v1 as fpm
from canonical.swe_kernel import incremental_semantic_graph_v1 as isg

SCHEMA = "PROJECT_BRAIN_CAUSAL_SWE_REPAIR_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

OPERATOR_FAMILIES: tuple[str, ...] = (
    "ANGELIC_BRANCH_CEGIS",
    "ANGELIC_VALUE_CEGIS",
    "STUN_GUARD_SYNTHESIS",
    "COUPLED_DATAFLOW_CEGIS",
    "SEMANTIC_IR_TRANSFER",
    "ITERATOR_MATERIALIZATION",
    "FALSY_NON_NONE_GUARD",
    "MEMBERSHIP_SET_EXTENSION",
    "GUARD_CONJUNCTIVE_RESTRICTION",
    "GUARD_DISJUNCTIVE_RELAXATION",
    "GUARD_BOUNDARY_OPERATOR",
    "DID_NOT_RAISE_PREDICATE",
    "EXCEPTION_SAFE_GUARD",
    "DEMAND_FSTRING_INDUCTION",
    "DEMAND_EXPRESSION_ALIGNMENT",
)


# =========================================================================== #
# INSPECTABLE, REFUTABLE OPERATOR MEMORY (ZERO PATHS, ZERO LITERALS)
# =========================================================================== #

class SWERepairMemory:
    """Tracks empirical `p_useful / (1 + mean_cost_s)` per semantic operator family."""

    def __init__(self, store_path: pathlib.Path | str | None = None) -> None:
        self.store_path = pathlib.Path(store_path) if store_path is not None else None
        self.stats: dict[str, dict[str, Any]] = {
            fam: {"trials": 0, "verified": 0, "regressions": 0, "cost_s": 0.1}
            for fam in OPERATOR_FAMILIES
        }
        self.schemas: list[dict[str, Any]] = []
        if self.store_path is not None and self.store_path.is_file():
            try:
                raw = json.loads(self.store_path.read_text(encoding="utf-8"))
                if isinstance(raw.get("stats"), dict):
                    self.stats.update(raw["stats"])
                if isinstance(raw.get("schemas"), list):
                    self.schemas = raw["schemas"]
            except Exception:
                pass

    def priority_score(self, family: str) -> float:
        row = self.stats.get(family) or {"trials": 0, "verified": 0, "regressions": 0, "cost_s": 0.1}
        trials = max(0, int(row.get("trials", 0)))
        verified = max(0, int(row.get("verified", 0)))
        regressions = max(0, int(row.get("regressions", 0)))
        mean_cost = float(row.get("cost_s", 0.1)) / max(1, trials)
        p_useful = (verified + 0.5) / (trials + 1.0)
        penalty = 1.0 + 0.25 * regressions
        return p_useful / ((1.0 + mean_cost) * penalty)

    def record_outcome(
        self,
        family: str,
        *,
        verified: bool,
        caused_regression: bool,
        elapsed_s: float,
        abstract_shape: str | None = None,
    ) -> None:
        row = self.stats.setdefault(
            family, {"trials": 0, "verified": 0, "regressions": 0, "cost_s": 0.0}
        )
        row["trials"] = int(row["trials"]) + 1
        if verified:
            row["verified"] = int(row["verified"]) + 1
        if caused_regression:
            row["regressions"] = int(row["regressions"]) + 1
        row["cost_s"] = round(float(row["cost_s"]) + max(0.001, elapsed_s), 4)
        if verified and abstract_shape:
            if not any(s["shape"] == abstract_shape for s in self.schemas):
                self.schemas.append({
                    "family": family,
                    "shape": abstract_shape,
                    "verified_count": 1,
                    "refutations": 0,
                })
            else:
                for s in self.schemas:
                    if s["shape"] == abstract_shape:
                        s["verified_count"] = int(s["verified_count"]) + 1

    def save(self, path: pathlib.Path | str) -> None:
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema": SCHEMA + "_MEMORY", "stats": self.stats, "schemas": self.schemas}
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(p)

    @classmethod
    def load(cls, path: pathlib.Path | str) -> "SWERepairMemory":
        mem = cls()
        p = pathlib.Path(path)
        if not p.is_file():
            return mem
        raw = json.loads(p.read_text(encoding="utf-8"))
        for k, v in (raw.get("stats") or {}).items():
            mem.stats[k] = dict(v)
        mem.schemas = list(raw.get("schemas") or [])
        return mem


# =========================================================================== #
# SUBPROCESS ORACLE & TRACE HARNESS (ZERO BYTECODE CACHE MASKING)
# =========================================================================== #

_VERDICT_AFTER = re.compile(
    r"^(\S.*?::.+?)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)(?:\s+\[\s*\d+%\])?\s*$"
)


def _clean_env(worktree: pathlib.Path) -> dict[str, str]:
    """Configure `PYTHONPATH` (`worktree/src` + `worktree` ahead of site-packages) with `/tmp` pycache."""
    py_paths = []
    if (worktree / "src").is_dir():
        py_paths.append(str(worktree / "src"))
    py_paths.append(str(worktree))
    existing = os.environ.get("PYTHONPATH", "")
    if existing:
        py_paths.append(existing)
    return {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(py_paths),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPYCACHEPREFIX": str(pathlib.Path(tempfile.gettempdir()) / "brain_nocache"),
    }


def run_pytest_verdicts(
    worktree: pathlib.Path,
    target: str | Sequence[str],
    *,
    python_exe: str | None = None,
    timeout_s: float = 45.0,
) -> dict[str, Any]:
    """Run pytest (or unittest fallback if pytest absent) and return exact per-test verdicts."""
    py = python_exe or sys.executable
    targets = [target] if isinstance(target, str) else list(target)
    uses_hyp = any(
        (worktree / str(t).split("::")[0]).is_file()
        and "hypothesis" in (worktree / str(t).split("::")[0]).read_text(encoding="utf-8", errors="ignore")
        for t in targets[:4]
    )
    extra_p = [] if uses_hyp else ["-p", "no:hypothesis"]
    first_p = pathlib.Path(str(targets[0]).split("::")[0])
    rdir = first_p.parent if first_p.is_absolute() and not str(first_p).startswith(str(worktree)) else worktree
    cmd = [
        py,
        "-m",
        "pytest",
        *targets,
        "-v",
        "--tb=short",
        f"--rootdir={rdir}",
        "-p",
        "no:cacheprovider",
        "-p",
        "no:xprocess",
        *extra_p,
        "-o",
        "addopts=",
        "-W",
        "default",
    ]
    env = _clean_env(worktree)
    started = time.perf_counter()
    proc = subprocess.Popen(
        cmd,
        cwd=str(worktree),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        stdin=subprocess.DEVNULL,
        env=env,
        start_new_session=True,
    )
    try:
        stdout_s, stderr_s = proc.communicate(timeout=timeout_s)
        done = subprocess.CompletedProcess(cmd, proc.returncode, stdout_s, stderr_s)
    except subprocess.TimeoutExpired:
        try:
            import signal
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            proc.kill()
        try:
            proc.communicate(timeout=3.0)
        except Exception:
            pass
        return {
            "ok": False,
            "timeout": True,
            "verdicts": {},
            "failing": [],
            "passing": [],
            "output": "TIMEOUT",
            "seconds": round(time.perf_counter() - started, 4),
        }

    out = (done.stdout or "") + "\n" + (done.stderr or "")
    # Fallback to stdlib unittest if `py` has no `pytest` installed (keeps stdlib unit tests runnable!)
    if done.returncode != 0 and "No module named pytest" in out:
        return _run_unittest_fallback(worktree, targets, py, env, timeout_s)

    verdicts: dict[str, str] = {}
    for line in out.splitlines():
        m = _VERDICT_AFTER.match(line.strip())
        if m:
            verdicts[m.group(1)] = m.group(2)

    failing = [k for k, v in verdicts.items() if v in ("FAILED", "ERROR")]
    passing = [k for k, v in verdicts.items() if v == "PASSED"]
    return {
        "ok": done.returncode == 0 and bool(passing) and not failing,
        "returncode": done.returncode,
        "verdicts": verdicts,
        "failing": failing,
        "passing": passing,
        "output": out[-4000:],
        "seconds": round(time.perf_counter() - started, 4),
    }


def _passed_baseline_nodes(before: Mapping[str, Any], after: Mapping[str, Any]) -> bool:
    """A disappearing failure (skip, lost collection, timeout) is not a repair."""
    required = set(before['failing']) | set(before['passing'])
    return bool(required) and after['ok'] is True and required <= set(after['passing'])


def _regression_check(before: Mapping[str, Any], after: Mapping[str, Any]) -> str | None:
    """Compare witnesses, not summary counts. Inconclusive is not green."""
    for run in (before, after):
        rc = run.get('returncode')
        if (rc not in (0, 1) or not (run.get('passing') or run.get('failing'))
                or bool(run.get('failing')) != (rc == 1)):
            return 'INCOMPLETE_REGRESSION_CHECK'
    old_pass, old_fail = set(before['passing']), set(before['failing'])
    new_pass, new_fail = set(after['passing']), set(after['failing'])
    if new_fail - old_fail:
        return 'REGRESSED_CROSS_MODULE_IMPACTED_TESTS'
    if not old_pass <= new_pass or not old_fail <= new_pass | new_fail:
        return 'INCOMPLETE_REGRESSION_CHECK'
    return None


def verify_runner_canary(
    worktree: pathlib.Path,
    *,
    python_exe: str | None = None,
    timeout_s: float = 15.0,
) -> bool:
    """Victim/decoy check on the test runner itself (`earn_a_judge` invariant for SWE).

    In self-hosting packages (`pluggy`, `pytest`, `unittest` wrappers), a patch could
    suppress exception propagation inside the test runner so `assert False` exits 0!
    A patched worktree is admissible ONLY if a deliberate false canary assertion still FAILS.
    """
    with tempfile.TemporaryDirectory(prefix="brain-canary-") as tmp:
        canary_file = pathlib.Path(tmp) / "test_runner_canary_decoy.py"
        canary_file.write_text(
            "import unittest\n"
            "def test_plain_function_false_assertion_must_fail():\n"
            "    assert 1 == 2\n\n"
            "class RunnerCanaryTests(unittest.TestCase):\n"
            "    def test_false_assertion_must_fail(self):\n"
            "        self.assertEqual(1, 2)\n",
            encoding="utf-8",
        )
        res = run_pytest_verdicts(
            worktree, str(canary_file), python_exe=python_exe, timeout_s=timeout_s
        )
        used_pytest = any("::" in k for k in res["verdicts"])
        min_expected = 2 if used_pytest else 1
        return res.get("returncode") == 1 and len(res["failing"]) >= min_expected and not res["ok"]


def _run_unittest_fallback(
    worktree: pathlib.Path,
    targets: Sequence[str],
    py: str,
    env: Mapping[str, str],
    timeout_s: float,
) -> dict[str, Any]:
    """Stdlib unittest runner when `pytest` is absent in minimal sandbox interpreters."""
    runner_code = (
        "import json, sys, unittest, pathlib\n"
        "sys.path[:0] = [p for p in ['src', '.'] if pathlib.Path(p).exists()]\n"
        "loader = unittest.TestLoader()\n"
        "suite = unittest.TestSuite()\n"
        "for t in sys.argv[1:]:\n"
        "    p = pathlib.Path(t.split('::')[0])\n"
        "    mod_suite = loader.discover(str(p.parent), pattern=p.name)\n"
        "    suite.addTests(mod_suite)\n"
        "class Rec(unittest.TextTestResult):\n"
        "    def __init__(self, *a, **kw):\n"
        "        super().__init__(*a, **kw); self.v = {}\n"
        "    def addSuccess(self, test): super().addSuccess(test); self.v[str(test)] = 'PASSED'\n"
        "    def addFailure(self, test, err): super().addFailure(test, err); self.v[str(test)] = 'FAILED'\n"
        "    def addError(self, test, err): super().addError(test, err); self.v[str(test)] = 'ERROR'\n"
        "res = unittest.TextTestRunner(resultclass=Rec, verbosity=0).run(suite)\n"
        "print('BRAIN_UNITTEST_JSON:' + json.dumps({'verdicts': res.v, 'errors': [[str(t), tb] for t, tb in res.failures + res.errors]}))\n"
    )
    started = time.perf_counter()
    done = subprocess.run(
        [py, "-c", runner_code, *targets],
        cwd=str(worktree),
        capture_output=True,
        text=True,
        errors="replace",
        stdin=subprocess.DEVNULL,
        timeout=timeout_s,
        env=dict(env),
    )
    out = (done.stdout or "") + "\n" + (done.stderr or "")
    verdicts: dict[str, str] = {}
    for line in out.splitlines():
        if line.startswith("BRAIN_UNITTEST_JSON:"):
            payload = json.loads(line[len("BRAIN_UNITTEST_JSON:"):])
            verdicts = payload.get("verdicts") or {}
    failing = [k for k, v in verdicts.items() if v in ("FAILED", "ERROR")]
    passing = [k for k, v in verdicts.items() if v == "PASSED"]
    return {
        "ok": bool(verdicts) and not failing,
        "returncode": 0 if (verdicts and not failing) else 1,
        "verdicts": verdicts,
        "failing": failing,
        "passing": passing,
        "output": out[-4000:],
        "seconds": round(time.perf_counter() - started, 4),
    }


# --------------------------------------------------------------------------- #
# In-process Tracer Script (spawned once inside `worktree` to collect runtime
# coverage, frame values, iterators, exceptions, and assertion comparisons)
# --------------------------------------------------------------------------- #

_TRACER_DRIVER = r'''
import ast
import json
import os
import pathlib
import re
import sys
import types

cfg = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
wt = pathlib.Path(cfg["worktree"]).resolve()
for p in ([str(wt / "src")] if (wt / "src").is_dir() else []) + [str(wt)]:
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

def _is_proj_source(filename: str) -> str | None:
    try:
        rp = pathlib.Path(filename).resolve()
        rel = rp.relative_to(wt).as_posix()
    except Exception:
        return None
    parts = rel.split("/")
    if any(x in (".git", ".venv", "venv", "tests", "test", "doc", "docs") for x in parts[:-1]):
        return None
    name = parts[-1]
    if not name.endswith(".py") or name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py":
        return None
    return rel

def _safe_val(v):
    tname = type(v).__name__
    is_iter = hasattr(v, "__iter__") and hasattr(v, "__next__") and not isinstance(v, (str, bytes, dict, list, tuple, set, frozenset))
    try:
        b = bool(v)
    except Exception:
        b = True
    is_none = (v is None)
    falsy_non_none = (not b) and (not is_none) and (type(v) is not bool)
    scalar = None
    if isinstance(v, (bool, int, float)) and not isinstance(v, bool):
        scalar = v
    elif isinstance(v, bool):
        scalar = v
    elif isinstance(v, str) and len(v) <= 200:
        scalar = v
    elif isinstance(v, bytes) and len(v) <= 120:
        scalar = {"__bytes__": list(v)}
    elif isinstance(v, tuple) and len(v) <= 8 and all(isinstance(x, (str, int, float, bool, type(None))) for x in v):
        scalar = {"__tuple__": [x for x in v]}
    attrs = {}
    if not isinstance(v, (int, float, bool, str, bytes, list, tuple, dict, set, frozenset, type(None), types.ModuleType, types.FunctionType, type)):
        try:
            for k in list(vars(v).keys())[:12]:
                av = getattr(v, k)
                if isinstance(av, (str, int, float, bool, type(None))) and (not isinstance(av, str) or len(av) <= 100):
                    attrs[k] = av
                else:
                    attrs[k] = {"__repr__": repr(av)[:80], "__type__": type(av).__name__}
        except Exception:
            pass
    try:
        rep = repr(v)[:140]
    except Exception:
        rep = f"<{tname}>"
    return {
        "type": tname,
        "bool": b,
        "is_none": is_none,
        "falsy_non_none": falsy_non_none,
        "is_iterator": is_iter,
        "scalar": scalar,
        "attrs": attrs,
        "repr": rep,
    }

def _snap_locals(f_locals):
    out = {}
    for k, v in list(f_locals.items())[:24]:
        if not isinstance(k, str) or k.startswith("__"):
            continue
        if isinstance(v, (types.ModuleType, types.FunctionType, types.BuiltinFunctionType, type)):
            continue
        out[k] = _safe_val(v)
    return out

records = {}
current_node = [None]

def _new_rec():
    return {
        "outcome": "unknown",
        "lines": [],
        "_tail": [],
        "frames_by_site": {},
        "exceptions": [],
        "iterators_seen": [],
        "falsy_non_none_sites": [],
        "asserts": [],
        "did_not_raise": None,
        "crash": None,
    }

def _tracer(frame, event, arg):
    node = current_node[0]
    if node is None:
        return None
    rel = _is_proj_source(frame.f_code.co_filename)
    if rel is None:
        return None
    rec = records[node]
    if event == "call":
        return _tracer
    lineno = frame.f_lineno
    site_key = f"{rel}:{lineno}"
    if event == "line":
        is_new_site = site_key not in rec["frames_by_site"]
        if is_new_site and len(rec["lines"]) < 6000:
            rec["lines"].append([rel, lineno, frame.f_code.co_name])
        tail = rec["_tail"]
        if len(tail) >= 160:
            tail.pop(0)
        tail.append([rel, lineno, frame.f_code.co_name])
        bucket = rec["frames_by_site"].setdefault(site_key, [])
        if len(bucket) < 3:
            snap = _snap_locals(frame.f_locals)
            bucket.append(snap)
            for vname, vinfo in snap.items():
                if vinfo["falsy_non_none"] and len(rec["falsy_non_none_sites"]) < 48:
                    rec["falsy_non_none_sites"].append({"site": site_key, "var": vname, "repr": vinfo["repr"], "type": vinfo["type"]})
                if vinfo["is_iterator"] and len(rec["iterators_seen"]) < 48:
                    rec["iterators_seen"].append({"site": site_key, "var": vname, "type": vinfo["type"]})
    elif event == "return":
        if arg is not None and hasattr(arg, "__iter__") and hasattr(arg, "__next__") and not isinstance(arg, (str, bytes, dict, list, tuple, set, frozenset)):
            if len(rec["iterators_seen"]) < 48:
                rec["iterators_seen"].append({"site": site_key, "var": "<return>", "type": type(arg).__name__})
    elif event == "exception":
        exc_type, exc_val, _ = arg
        if len(rec["exceptions"]) >= 28:
            rec["exceptions"].pop(0)
        rec["exceptions"].append({
            "site": site_key,
            "func": frame.f_code.co_name,
            "exc_type": getattr(exc_type, "__name__", str(exc_type)),
            "exc_msg": str(exc_val)[:200],
            "locals": _snap_locals(frame.f_locals),
        })
    return _tracer

try:
    import pytest
    has_pytest = True
except ImportError:
    has_pytest = False

if has_pytest:
    class _Plugin:
        def pytest_runtest_setup(self, item):
            records[item.nodeid] = _new_rec()
        def pytest_runtest_call(self, item):
            current_node[0] = item.nodeid
            sys.settrace(_tracer)
        def pytest_runtest_teardown(self, item):
            sys.settrace(None)
            current_node[0] = None
        def pytest_assertrepr_compare(self, config, op, left, right):
            nid = current_node[0]
            if nid and nid in records and len(records[nid]["asserts"]) < 8:
                records[nid]["asserts"].append({
                    "op": str(op),
                    "left": _safe_val(left),
                    "right": _safe_val(right),
                })
            return None
        def pytest_runtest_makereport(self, item, call):
            sys.settrace(None)
            if call.when != "call":
                return
            rec = records.setdefault(item.nodeid, _new_rec())
            if call.excinfo is None:
                rec["outcome"] = "passed"
                return
            rec["outcome"] = "failed"
            msg = str(call.excinfo.value)
            m = re.search(r"DID NOT RAISE <class '([^']+)'>", msg)
            if m:
                rec["did_not_raise"] = m.group(1).split(".")[-1]
            else:
                # Walk traceback inside project source
                proj_tb = []
                for entry in call.excinfo.traceback:
                    rel = _is_proj_source(str(entry.path))
                    if rel:
                        proj_tb.append({"rel": rel, "lineno": entry.lineno})
                rec["crash"] = {
                    "exc_type": call.excinfo.typename,
                    "exc_msg": msg[:300],
                    "proj_traceback": proj_tb[-6:],
                }

    old_argv = sys.argv[:]
    old_cwd = os.getcwd()
    try:
        os.chdir(wt)
        sys.argv = ["pytest"]
        uses_hyp = any(
            (pathlib.Path(wt) / str(n).split("::")[0]).is_file()
            and "hypothesis" in (pathlib.Path(wt) / str(n).split("::")[0]).read_text(encoding="utf-8", errors="ignore")
            for n in cfg["nodes"][:4]
        )
        extra_p = [] if uses_hyp else ["-p", "no:hypothesis"]
        pytest.main(
            [*cfg["nodes"], "-q", "--no-header", "--tb=short", f"--rootdir={wt}",
             "-p", "no:cacheprovider", "-p", "no:xprocess", *extra_p,
             "-o", "addopts=", "-W", "default"],
            plugins=[_Plugin()],
        )
    finally:
        sys.settrace(None)
        os.chdir(old_cwd)
        sys.argv = old_argv
else:
    import unittest
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for t in cfg["targets"]:
        p = pathlib.Path(t.split("::")[0])
        suite.addTests(loader.discover(str((wt / p).parent), pattern=p.name))
    for group in suite:
        for sub in (group if hasattr(group, "__iter__") else [group]):
            for case in (sub if hasattr(sub, "__iter__") else [sub]):
                nid = str(case)
                records[nid] = _new_rec()
                current_node[0] = nid
                old_cwd = os.getcwd()
                os.chdir(wt)
                res = unittest.TestResult()
                sys.settrace(_tracer)
                try:
                    case.run(res)
                finally:
                    sys.settrace(None)
                    os.chdir(old_cwd)
                    current_node[0] = None
                if res.wasSuccessful():
                    records[nid]["outcome"] = "passed"
                else:
                    records[nid]["outcome"] = "failed"
                    for _, tb_str in res.failures + res.errors:
                        m = re.search(r"([A-Za-z_]\w*(?:Error|Exception))\s*not triggered", tb_str)
                        if m:
                            records[nid]["did_not_raise"] = m.group(1)
                        records[nid]["crash"] = {"exc_type": "Failure", "exc_msg": tb_str[-300:], "proj_traceback": []}

for _r in records.values():
    _tl = _r.pop("_tail", [])
    if _tl:
        _r["lines"].extend(_tl)
pathlib.Path(cfg["out"]).write_text(json.dumps({"records": records}), encoding="utf-8")
'''


def collect_causal_trace(
    worktree: pathlib.Path,
    failing_nodes: Sequence[str],
    passing_nodes: Sequence[str],
    test_target: str,
    *,
    python_exe: str | None = None,
    timeout_s: float = 45.0,
) -> dict[str, Any]:
    """Run the 1-pass dynamic tracer on failing tests + up to 8 lexically closest passing contrast tests."""
    py = python_exe or sys.executable
    fail_toks = {tok for fn in failing_nodes[:4] for tok in re.findall(r"[a-z0-9]+", fn.lower())}
    ranked_pass = sorted(
        passing_nodes,
        key=lambda pn: (-len(set(re.findall(r"[a-z0-9]+", pn.lower())) & fail_toks), pn),
    )[:8]
    selected_nodes = list(failing_nodes[:4]) + ranked_pass
    # Only pass `::` node IDs directly to pytest; unittest fallback uses `test_target`
    pytest_nodes = [n for n in selected_nodes if "::" in n] or [test_target]
    with tempfile.TemporaryDirectory(prefix="brain-trace-") as tmp:
        tdir = pathlib.Path(tmp)
        driver_py = tdir / "driver.py"
        cfg_json = tdir / "cfg.json"
        out_json = tdir / "out.json"
        driver_py.write_text(_TRACER_DRIVER, encoding="utf-8")
        cfg_json.write_text(
            json.dumps({
                "worktree": str(worktree),
                "nodes": pytest_nodes,
                "targets": [test_target],
                "out": str(out_json),
            }),
            encoding="utf-8",
        )
        env = _clean_env(worktree)
        try:
            subprocess.run(
                [py, str(driver_py), str(cfg_json)],
                cwd=str(worktree),
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=timeout_s,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return {"records": {}}
        if not out_json.is_file():
            return {"records": {}}
        try:
            return json.loads(out_json.read_text(encoding="utf-8"))
        except Exception:
            return {"records": {}}


# =========================================================================== #
# STAGE 1: DYNAMIC FAULT LOCALIZATION (OCHIAI + CALL-TAIL + CRASH PROXIMITY)
# =========================================================================== #

def localize_suspicious_sites(
    trace_data: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Rank `(rel_path, lineno)` sites purely from execution traces (ZERO commit/diff knowledge)."""
    recs = trace_data.get("records") or {}
    fail_recs = [r for r in recs.values() if r.get("outcome") == "failed"]
    pass_recs = [r for r in recs.values() if r.get("outcome") == "passed"]
    total_f = max(1, len(fail_recs))

    ef: dict[tuple[str, int], int] = {}
    ep: dict[tuple[str, int], int] = {}
    tail_bonus: dict[tuple[str, int], float] = {}
    crash_bonus: dict[tuple[str, int], float] = {}

    for r in fail_recs:
        seen_in_test: set[tuple[str, int]] = set()
        lines = r.get("lines") or []
        for idx, (rel, ln, _fn) in enumerate(lines):
            seen_in_test.add((rel, int(ln)))
        for key in seen_in_test:
            ef[key] = ef.get(key, 0) + 1
        # Recent lines right before failure/return carry higher causal weight
        tail = lines[-25:]
        for dist_from_end, (rel, ln, _fn) in enumerate(reversed(tail)):
            key = (rel, int(ln))
            tail_bonus[key] = max(tail_bonus.get(key, 0.0), 0.35 * (0.92 ** dist_from_end))
        crash = r.get("crash") or {}
        for depth, entry in enumerate(reversed(crash.get("proj_traceback") or [])):
            ckey = (entry["rel"], int(entry["lineno"]))
            crash_bonus[ckey] = max(crash_bonus.get(ckey, 0.0), 1.5 / (1 + depth))
            # Also boost the line immediately above a `raise` (typically its `if` guard!)
            for delta in (-3, -2, -1, 1):
                nkey = (entry["rel"], int(entry["lineno"]) + delta)
                crash_bonus[nkey] = max(crash_bonus.get(nkey, 0.0), 0.9 / (1 + depth))
        for exc in r.get("exceptions") or []:
            rel_s, ln_s = exc["site"].split(":", 1)
            ekey = (rel_s, int(ln_s))
            crash_bonus[ekey] = max(crash_bonus.get(ekey, 0.0), 0.8)
            for delta in (-2, -1):
                nkey = (rel_s, int(ln_s) + delta)
                crash_bonus[nkey] = max(crash_bonus.get(nkey, 0.0), 0.6)

    for r in pass_recs:
        seen_p: set[tuple[str, int]] = set()
        for rel, ln, _fn in r.get("lines") or []:
            seen_p.add((rel, int(ln)))
        for key in seen_p:
            ep[key] = ep.get(key, 0) + 1

    ranked: list[dict[str, Any]] = []
    all_keys = set(ef) | set(crash_bonus)
    for rel, ln in all_keys:
        if ln <= 0:
            continue
        c_ef = ef.get((rel, ln), 0)
        c_ep = ep.get((rel, ln), 0)
        denom = math.sqrt(total_f * max(1, c_ef + c_ep))
        ochiai = (c_ef / denom) if denom > 0 else 0.0
        score = ochiai + tail_bonus.get((rel, ln), 0.0) + crash_bonus.get((rel, ln), 0.0)
        ranked.append({
            "rel": rel,
            "lineno": ln,
            "ochiai": round(ochiai, 4),
            "score": round(score, 4),
            "failed_hits": c_ef,
            "passed_hits": c_ep,
        })
    ranked.sort(key=lambda row: (-row["score"], -row["ochiai"], row["passed_hits"], row["lineno"]))
    return ranked


# =========================================================================== #
# AST SOURCE UTILITIES & SAFE BYTE-OFFSET SLICING
# =========================================================================== #

def _char_col(line_text: str, byte_offset: int) -> int:
    raw = line_text.encode("utf-8")
    return len(raw[:byte_offset].decode("utf-8", errors="ignore"))


def replace_ast_node_source(source: str, node: ast.AST, replacement_expr: str) -> str | None:
    """Replace a single-line or multi-line AST node span in `source`, verifying valid syntax."""
    start_ln = getattr(node, "lineno", None)
    end_ln = getattr(node, "end_lineno", None)
    start_col_b = getattr(node, "col_offset", None)
    end_col_b = getattr(node, "end_col_offset", None)
    if None in (start_ln, end_ln, start_col_b, end_col_b):
        return None
    lines = source.splitlines(keepends=True)
    if start_ln < 1 or end_ln > len(lines):
        return None
    s_col = _char_col(lines[start_ln - 1], start_col_b)
    e_col = _char_col(lines[end_ln - 1], end_col_b)
    prefix = lines[start_ln - 1][:s_col]
    suffix = lines[end_ln - 1][e_col:]
    new_lines = lines[: start_ln - 1] + [prefix + replacement_expr + suffix] + lines[end_ln:]
    patched = "".join(new_lines)
    try:
        ast.parse(patched)
    except SyntaxError:
        return None
    return patched


def _unparse(node: ast.AST) -> str:
    return ast.unparse(node)


def _reconstruct_value(vinfo: Mapping[str, Any]) -> tuple[bool, Any]:
    """Rehydrate a scalar/tuple/bytes value from the tracer's safe JSON snapshot."""
    if vinfo.get("is_none"):
        return True, None
    sc = vinfo.get("scalar")
    if sc is not None:
        if isinstance(sc, dict):
            if "__bytes__" in sc:
                return True, bytes(sc["__bytes__"])
            if "__tuple__" in sc:
                return True, tuple(sc["__tuple__"])
        return True, sc
    return False, None


def _module_constants_and_attrs(tree: ast.Module) -> dict[str, list[str]]:
    """Collect attribute references (`mod.CONST`, `self._attr`) already written in the file."""
    by_base: dict[str, list[str]] = {}
    all_attrs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            base = node.value.id
            by_base.setdefault(base, [])
            if node.attr not in by_base[base]:
                by_base[base].append(node.attr)
            all_attrs.add(node.attr)
    by_base["__all_attrs__"] = sorted(all_attrs)
    return by_base


def _enclosing_function(tree: ast.Module, lineno: int) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_ln = getattr(node, "end_lineno", node.lineno)
            if node.lineno <= lineno <= end_ln:
                if best is None or node.lineno >= best.lineno:
                    best = node
    return best


def _boolean_atoms_in_guard(test_expr: ast.expr) -> list[ast.expr]:
    """Sub-expressions whose truthiness is directly tested (`if a and not b:` -> `[a and not b, a, b]`)."""
    out: list[ast.expr] = [test_expr]
    if isinstance(test_expr, ast.BoolOp):
        for v in test_expr.values:
            out.extend(_boolean_atoms_in_guard(v))
    elif isinstance(test_expr, ast.UnaryOp) and isinstance(test_expr.op, ast.Not):
        out.extend(_boolean_atoms_in_guard(test_expr.operand))
    return out


def _is_degenerate_guard_extension(test_expr: ast.expr, candidate_pred: str) -> bool:
    """Reject redundant (`P and P`) or contradictory (`x is not None and x is None`) guard atoms."""
    try:
        cand_ast = ast.parse(candidate_pred, mode="eval").body
    except SyntaxError:
        return True
    cand_norm = _unparse(cand_ast)
    neg_pairs = {
        ast.Is: ast.IsNot,
        ast.IsNot: ast.Is,
        ast.Eq: ast.NotEq,
        ast.NotEq: ast.Eq,
        ast.In: ast.NotIn,
        ast.NotIn: ast.In,
        ast.Lt: ast.GtE,
        ast.GtE: ast.Lt,
        ast.Gt: ast.LtE,
        ast.LtE: ast.Gt,
    }
    forbidden: set[str] = set()
    for atom in _boolean_atoms_in_guard(test_expr):
        atom_s = _unparse(atom)
        forbidden.add(atom_s)
        forbidden.add(f"not {atom_s}")
        forbidden.add(f"not ({atom_s})")
        if isinstance(atom, ast.UnaryOp) and isinstance(atom.op, ast.Not):
            forbidden.add(_unparse(atom.operand))
        if isinstance(atom, ast.Compare) and len(atom.ops) == 1 and len(atom.comparators) == 1:
            op_t = type(atom.ops[0])
            if op_t in neg_pairs:
                neg_cmp = ast.Compare(
                    left=atom.left,
                    ops=[neg_pairs[op_t]()],
                    comparators=atom.comparators,
                )
                forbidden.add(_unparse(neg_cmp))
    return cand_norm in forbidden


# =========================================================================== #
# STAGE 2: FIVE CAUSAL SEMANTIC REPAIR GENERATORS
# =========================================================================== #

@dataclass
class PatchCandidate:
    family: str
    rel_path: str
    lineno: int
    description: str
    new_source: str
    abstract_shape: str
    heuristic_bonus: float = 0.0


def synthesize_candidates(
    worktree: pathlib.Path,
    trace_data: Mapping[str, Any],
    ranked_sites: Sequence[Mapping[str, Any]],
    memory: SWERepairMemory,
    *,
    python_exe: str | None = None,
    max_sites: int = 24,
    max_candidates: int = 48,
) -> list[PatchCandidate]:
    """Synthesize minimal, frame-consistent candidate patches across all 5 causal modes."""
    recs = trace_data.get("records") or {}
    fail_recs = [r for r in recs.values() if r.get("outcome") == "failed"]
    pass_recs = [r for r in recs.values() if r.get("outcome") == "passed"]
    if not fail_recs:
        return []

    source_cache: dict[str, tuple[str, ast.Module, dict[str, list[str]]]] = {}

    def _get_file(rel: str) -> tuple[str, ast.Module, dict[str, list[str]]] | None:
        if rel in source_cache:
            return source_cache[rel]
        p = worktree / rel
        if not p.is_file():
            return None
        try:
            txt = p.read_text(encoding="utf-8")
            mod = ast.parse(txt)
        except (OSError, SyntaxError):
            return None
        entry = (txt, mod, _module_constants_and_attrs(mod))
        source_cache[rel] = entry
        return entry

    # Index runtime snapshots per site for failing vs passing tests
    fail_snaps: dict[str, list[dict[str, Any]]] = {}
    pass_snaps: dict[str, list[dict[str, Any]]] = {}
    falsy_vars_by_site: dict[str, set[str]] = {}
    iterator_sites: set[str] = set()
    iterator_vars_by_func: dict[tuple[str, str], set[str]] = {}

    for r in fail_recs:
        for skey, snaps in (r.get("frames_by_site") or {}).items():
            fail_snaps.setdefault(skey, []).extend(snaps)
        for item in r.get("falsy_non_none_sites") or []:
            falsy_vars_by_site.setdefault(item["site"], set()).add(item["var"])
        for item in r.get("iterators_seen") or []:
            iterator_sites.add(item["site"])
            rel_i, ln_i = item["site"].split(":", 1)
            loaded = _get_file(rel_i)
            if loaded:
                fn_node = _enclosing_function(loaded[1], int(ln_i))
                if fn_node:
                    iterator_vars_by_func.setdefault((rel_i, fn_node.name), set()).add(item["var"])

    for r in pass_recs:
        for skey, snaps in (r.get("frames_by_site") or {}).items():
            pass_snaps.setdefault(skey, []).extend(snaps)

    # Collect assertion demands (including exception message strings!) from failing tests
    string_demands: list[str] = []
    scalar_demands: list[Any] = []
    did_not_raise_excs: list[str] = []
    unexpected_crashes: list[dict[str, Any]] = []

    for r in fail_recs:
        if r.get("did_not_raise"):
            did_not_raise_excs.append(str(r["did_not_raise"]))
        if r.get("crash"):
            unexpected_crashes.append(r["crash"])
        for a in r.get("asserts") or []:
            for side in ("left", "right"):
                ok_v, val = _reconstruct_value(a[side])
                if ok_v:
                    if isinstance(val, str) and 1 <= len(val) <= 200 and not val.startswith("assert "):
                        if val not in string_demands:
                            string_demands.append(val)
                    elif val not in scalar_demands:
                        scalar_demands.append(val)

    candidates: list[PatchCandidate] = []
    seen_patches: set[tuple[str, str]] = set()

    def _emit(cand: PatchCandidate) -> None:
        key = (cand.rel_path, cand.new_source)
        if key not in seen_patches and not fpm._has_new_dead_branch_equivalence(
            (_get_file(cand.rel_path) or ("", None, None))[0], cand.new_source
        ):
            seen_patches.add(key)
            candidates.append(cand)

    # -----------------------------------------------------------------------
    # Scan top suspicious sites & their enclosing functions
    # -----------------------------------------------------------------------
    visited_funcs: set[tuple[str, int]] = set()

    for rank_idx, site_info in enumerate(ranked_sites[:max_sites]):
        rel = site_info["rel"]
        lineno = int(site_info["lineno"])
        skey = f"{rel}:{lineno}"
        loaded = _get_file(rel)
        if loaded is None:
            continue
        src, tree, file_attrs = loaded
        site_bonus = float(site_info["score"])
        f_frames = fail_snaps.get(skey) or []
        p_frames = pass_snaps.get(skey) or []

        # Find AST statements / expressions on or enclosing `lineno`
        fn_node = _enclosing_function(tree, lineno)
        search_root: ast.AST = fn_node if fn_node is not None else tree

        # --- FAMILY 1B: CODEBASE TYPE-HABITATION (runs at every ranked line + CFG guards!) ---
        from canonical.swe_kernel.petri_cow_splicing_engine_v1 import CodebaseTypeHabitationMiner

        stmt_at_ln, _, enc_ifs_ln = fpm.AngelicCEGISSynthesizer._find_enclosing_stmt_and_func(tree, lineno)
        for t_st in ([stmt_at_ln, *enc_ifs_ln[:2]] if stmt_at_ln is not None else list(enc_ifs_ln[:2])):
            if t_st is None:
                continue
            for p_src_h, mech_h, desc_h in CodebaseTypeHabitationMiner.synthesize_stmt_habitation_rewrites(
                worktree, rel, src, t_st, f_frames
            ):
                _emit(PatchCandidate(
                    family="FALSY_NON_NONE_GUARD" if "GUARD" in mech_h else "DEMAND_EXPRESSION_ALIGNMENT",
                    rel_path=rel,
                    lineno=getattr(t_st, "lineno", lineno),
                    description=desc_h,
                    new_source=p_src_h,
                    abstract_shape=mech_h,
                    heuristic_bonus=site_bonus + 3.2,
                ))

        # --- FAMILY 1: ITERATOR MATERIALIZATION (`x = fn(...)` -> `tuple(fn(...))`) ---
        if fn_node and (rel, fn_node.name) not in visited_funcs:
            visited_funcs.add((rel, fn_node.name))
            iter_vars = iterator_vars_by_func.get((rel, fn_node.name)) or set()
            if iter_vars:
                for stmt in ast.walk(fn_node):
                    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                        vname = stmt.targets[0].id
                        if vname in iter_vars and isinstance(stmt.value, ast.Call):
                            if not (isinstance(stmt.value.func, ast.Name) and stmt.value.func.id in ("tuple", "list")):
                                inner = _unparse(stmt.value)
                                for wrapper in ("tuple", "list"):
                                    patched = replace_ast_node_source(src, stmt.value, f"{wrapper}({inner})")
                                    if patched:
                                        _emit(PatchCandidate(
                                            family="ITERATOR_MATERIALIZATION",
                                            rel_path=rel,
                                            lineno=stmt.lineno,
                                            description=f"materialize single-pass iterator `{vname}` with `{wrapper}(...)`",
                                            new_source=patched,
                                            abstract_shape=f"$VAR = {wrapper}($CALL)",
                                            heuristic_bonus=site_bonus + 2.5,
                                        ))

            # Finite-State Transducer Fixed-Point Image Refinement:
            # Whenever a module pairs a boolean validator `is_*` with a sibling `canonicalize_*`/`normalize_*`
            # transducer, execute `(v_fn, c_fn)` on a finite probe basis `W_probe`, observe the canonical
            # separator & case-fold directly from `c_fn`'s runtime outputs, and synthesize the exact fixed-point
            # regular expression `R_image` verified on `W_probe` against `bool(v_fn(w)) and (c_fn(w) == w)`!
            if (rel, "<fst_fixed_point>") not in visited_funcs:
                visited_funcs.add((rel, "<fst_fixed_point>"))
                is_validators = [
                    st for st in tree.body if isinstance(st, ast.FunctionDef) and st.name.startswith("is_")
                ]
                canon_fns = [
                    st
                    for st in tree.body
                    if isinstance(st, ast.FunctionDef) and st.name.startswith(("canonicalize_", "normalize_"))
                ]
                if is_validators and canon_fns:
                    mod_parts = list((worktree / rel).relative_to(worktree).parts)
                    if mod_parts and mod_parts[0] == "src":
                        mod_parts = mod_parts[1:]
                    if mod_parts and mod_parts[-1].endswith(".py"):
                        mod_parts[-1] = mod_parts[-1][:-3]
                    if mod_parts and mod_parts[-1] == "__init__":
                        mod_parts = mod_parts[:-1]
                    mod_qual = ".".join(mod_parts)
                    probe_words = [
                        "", "a", "z", "0", "a1", "a-b", "a-b-c", "a1-b2-c3",
                        "a--b", "a---b", "a_b", "a__b", "a.b", "a..b", "a._-b",
                        "A", "A-b", "a-B", "-a", "a-", "_a", "a_", ".a", "a.",
                        "a:b", "a/b", "a b",
                    ]
                    probe_py = (
                        "import importlib, json, sys\n"
                        "mod_n, v_names, c_names, words = json.loads(sys.argv[1])\n"
                        "m = importlib.import_module(mod_n)\n"
                        "out = []\n"
                        "for vn in v_names:\n"
                        "    vf = getattr(m, vn, None)\n"
                        "    if not callable(vf): continue\n"
                        "    for cn in c_names:\n"
                        "        cf = getattr(m, cn, None)\n"
                        "        if not callable(cf): continue\n"
                        "        try:\n"
                        "            vw = {w: bool(vf(w)) for w in words}\n"
                        "            cw = {w: str(cf(w)) for w in words}\n"
                        "            out.append({'v': vn, 'c': cn, 'vw': vw, 'cw': cw})\n"
                        "        except Exception:\n"
                        "            pass\n"
                        "print(json.dumps(out))\n"
                    )
                    probe_pairs: list[dict[str, Any]] = []
                    if mod_qual:
                        try:
                            pr_done = subprocess.run(
                                [
                                    python_exe or sys.executable,
                                    "-c",
                                    probe_py,
                                    json.dumps([
                                        mod_qual,
                                        [f.name for f in is_validators],
                                        [f.name for f in canon_fns],
                                        probe_words,
                                    ]),
                                ],
                                cwd=str(worktree),
                                env=_clean_env(worktree),
                                capture_output=True,
                                text=True,
                                timeout=4.0,
                            )
                            if pr_done.returncode == 0 and pr_done.stdout.strip():
                                probe_pairs = json.loads(pr_done.stdout.strip().splitlines()[-1])
                        except Exception:
                            probe_pairs = []

                    mod_regexes: dict[str, ast.Call] = {}
                    for top_st in tree.body:
                        if isinstance(top_st, (ast.Assign, ast.AnnAssign)):
                            tgt = (
                                top_st.targets[0]
                                if isinstance(top_st, ast.Assign) and len(top_st.targets) == 1
                                else getattr(top_st, "target", None)
                            )
                            val_n = top_st.value
                            if isinstance(tgt, ast.Name) and isinstance(val_n, ast.Call) and val_n.args:
                                mod_regexes[tgt.id] = val_n

                    for pair_info in probe_pairs:
                        vn = str(pair_info["v"])
                        vw: dict[str, bool] = pair_info["vw"]
                        cw: dict[str, str] = pair_info["cw"]
                        # Must currently violate fixed-point (`v(w)` True while `c(w) != w`)!
                        if not any(vw.get(w) and cw.get(w) != w for w in probe_words):
                            continue
                        c_double = cw.get("a--b", "")
                        canon_sep = c_double[1] if len(c_double) == 3 and c_double[0] == "a" and c_double[2] == "b" else "-"
                        alnum_cls = (
                            "[a-z0-9]"
                            if cw.get("A") == "a"
                            else ("[A-Z0-9]" if cw.get("a") == "A" else "[A-Za-z0-9]")
                        )
                        esc_sep = "-" if canon_sep == "-" else re.escape(canon_sep)
                        img_pat = f"^{alnum_cls}+({esc_sep}{alnum_cls}+)*$"
                        try:
                            img_cre = re.compile(img_pat)
                        except re.error:
                            continue
                        if not all(
                            bool(img_cre.match(w)) == (bool(vw.get(w)) and cw.get(w) == w)
                            for w in probe_words
                        ):
                            continue
                        v_fn = next((f for f in is_validators if f.name == vn), None)
                        if v_fn is None:
                            continue
                        other_fn_names_used = {
                            n.id
                            for top_st in tree.body
                            if isinstance(top_st, ast.FunctionDef) and top_st is not v_fn
                            for n in ast.walk(top_st)
                            if isinstance(n, ast.Name)
                        }
                        emitted_re = False
                        for n in ast.walk(v_fn):
                            if isinstance(n, ast.Name) and n.id in mod_regexes and n.id not in other_fn_names_used:
                                call_node = mod_regexes[n.id]
                                fn_callee = _unparse(call_node.func)
                                patched_re = replace_ast_node_source(src, call_node, f"{fn_callee}({img_pat!r})")
                                if patched_re:
                                    emitted_re = True
                                    _emit(PatchCandidate(
                                        family="DEMAND_EXPRESSION_ALIGNMENT",
                                        rel_path=rel,
                                        lineno=call_node.lineno,
                                        description=f"compute exact FST fixed-point regex image `{img_pat}` for `{n.id}`",
                                        new_source=patched_re,
                                        abstract_shape="REGEX_FIXED_POINT_REFINEMENT",
                                        heuristic_bonus=site_bonus + 4.2,
                                    ))
                        if not emitted_re and v_fn.args.args:
                            p0 = v_fn.args.args[0].arg
                            ret_stmts = [st for st in v_fn.body if isinstance(st, ast.Return) and st.value is not None]
                            if len(ret_stmts) == 1 and ("import re" in src or "from re " in src):
                                patched_ret = replace_ast_node_source(
                                    src, ret_stmts[0].value, f"re.match({img_pat!r}, {p0}) is not None"
                                )
                                if patched_ret:
                                    _emit(PatchCandidate(
                                        family="DEMAND_EXPRESSION_ALIGNMENT",
                                        rel_path=rel,
                                        lineno=ret_stmts[0].lineno,
                                        description=f"compute exact FST fixed-point regex image `{img_pat}` in `{v_fn.name}`",
                                        new_source=patched_ret,
                                        abstract_shape="REGEX_FIXED_POINT_REFINEMENT",
                                        heuristic_bonus=site_bonus + 4.2,
                                    ))

        # Bidirectional FST Lens Synthesis (`dec(enc(x)) == x` round-trip repairs on codec/escape/format pairs)
        if (rel, "<fst_lens>") not in visited_funcs:
            visited_funcs.add((rel, "<fst_lens>"))
            from canonical.swe_kernel.petri_cow_splicing_engine_v1 import BidirectionalFSTLensSynthesizer

            for p_src_l, ln_l, mech_l, desc_l in BidirectionalFSTLensSynthesizer.synthesize_lens_repairs(src, tree):
                _emit(PatchCandidate(
                    family="DEMAND_EXPRESSION_ALIGNMENT",
                    rel_path=rel,
                    lineno=ln_l,
                    description=desc_l,
                    new_source=p_src_l,
                    abstract_shape=mech_l,
                    heuristic_bonus=site_bonus + 4.0,
                ))

        # Also check callee live-parameter threading at exact `lineno` (even inside nested lambdas!)
        for p_src_c, mech_c, desc_c in fpm._synthesize_callee_param_threading(
            worktree, rel, src, tree, lineno, f_frames
        ):
            _emit(PatchCandidate(
                family="DEMAND_EXPRESSION_ALIGNMENT",
                rel_path=rel,
                lineno=lineno,
                description=desc_c,
                new_source=p_src_c,
                abstract_shape=mech_c,
                heuristic_bonus=site_bonus + 3.6,
            ))

        for node in ast.walk(search_root):
            n_ln = getattr(node, "lineno", None)
            if n_ln != lineno and not (isinstance(node, ast.IfExp) and n_ln is not None and n_ln <= lineno):
                continue

            # --- FAMILY 2: GUARD PROJECTION, MEMBERSHIP, BOUNDARY, CONJUNCTIVE/DISJUNCTIVE ---
            if isinstance(node, (ast.If, ast.While, ast.IfExp)):
                none_params: set[str] = set()
                if fn_node is not None:
                    p_args = list(fn_node.args.args)
                    p_defs = list(fn_node.args.defaults)
                    for pa, pd in zip(p_args[len(p_args) - len(p_defs) :], p_defs):
                        if isinstance(pd, ast.Constant) and pd.value is None:
                            none_params.add(pa.arg)
                    for ka, kd in zip(fn_node.args.kwonlyargs, fn_node.args.kw_defaults):
                        if isinstance(kd, ast.Constant) and kd.value is None:
                            none_params.add(ka.arg)
                # 2a. Falsy non-None (`if x` -> `if x is not None` or `a if key else b` -> `a if key is not None else b`)
                for sub in _boolean_atoms_in_guard(node.test):
                    if isinstance(sub, (ast.Name, ast.Attribute)):
                        sub_txt = _unparse(sub)
                        observed_falsy = _expr_was_falsy_non_none(sub, f_frames) or (
                            isinstance(sub, ast.Name) and sub.id in none_params
                        )
                        if observed_falsy or isinstance(sub, ast.Attribute):
                            patched = replace_ast_node_source(src, sub, f"{sub_txt} is not None")
                            if patched:
                                _emit(PatchCandidate(
                                    family="FALSY_NON_NONE_GUARD",
                                    rel_path=rel,
                                    lineno=lineno,
                                    description=f"project `{sub_txt}` to `{sub_txt} is not None`",
                                    new_source=patched,
                                    abstract_shape="if $EXPR is not None:",
                                    heuristic_bonus=site_bonus + (3.0 if observed_falsy else 0.4),
                                ))

                # 2b. Membership Set Extension (`if x != 'a':` -> `if x not in ('a', 'b'):` using live failing value!)
                for sub in ast.walk(node.test):
                    if isinstance(sub, ast.Compare) and len(sub.ops) == 1 and len(sub.comparators) == 1:
                        op = sub.ops[0]
                        left_node = sub.left
                        comp_node = sub.comparators[0]
                        if isinstance(left_node, ast.Name):
                            var_id = left_node.id
                            fail_vals = _distinct_scalars_in_frames(var_id, f_frames)
                            pass_vals = _distinct_scalars_in_frames(var_id, p_frames)
                            novel_vals = [v for v in fail_vals if v not in pass_vals and isinstance(v, (str, int))]
                            if novel_vals:
                                new_lit = repr(novel_vals[0])
                                if isinstance(op, ast.NotEq) and isinstance(comp_node, ast.Constant):
                                    old_lit = repr(comp_node.value)
                                    if old_lit != new_lit:
                                        patched = replace_ast_node_source(
                                            src, sub, f"{var_id} not in ({old_lit}, {new_lit})"
                                        )
                                        if patched:
                                            _emit(PatchCandidate(
                                                family="MEMBERSHIP_SET_EXTENSION",
                                                rel_path=rel,
                                                lineno=lineno,
                                                description=f"extend inequality on `{var_id}` with failing literal {new_lit}",
                                                new_source=patched,
                                                abstract_shape="$VAR not in ($LIT1, $LIT2)",
                                                heuristic_bonus=site_bonus + 2.6,
                                            ))
                                elif isinstance(op, ast.Eq) and isinstance(comp_node, ast.Constant):
                                    old_lit = repr(comp_node.value)
                                    if old_lit != new_lit:
                                        patched = replace_ast_node_source(
                                            src, sub, f"{var_id} in ({old_lit}, {new_lit})"
                                        )
                                        if patched:
                                            _emit(PatchCandidate(
                                                family="MEMBERSHIP_SET_EXTENSION",
                                                rel_path=rel,
                                                lineno=lineno,
                                                description=f"extend equality on `{var_id}` with failing literal {new_lit}",
                                                new_source=patched,
                                                abstract_shape="$VAR in ($LIT1, $LIT2)",
                                                heuristic_bonus=site_bonus + 2.4,
                                            ))
                                elif isinstance(op, (ast.In, ast.NotIn)) and isinstance(comp_node, (ast.Tuple, ast.List, ast.Set)):
                                    existing_elts = [_unparse(e) for e in comp_node.elts]
                                    if new_lit not in existing_elts:
                                        op_str = "in" if isinstance(op, ast.In) else "not in"
                                        joined = ", ".join([*existing_elts, new_lit])
                                        patched = replace_ast_node_source(src, sub, f"{var_id} {op_str} ({joined})")
                                        if patched:
                                            _emit(PatchCandidate(
                                                family="MEMBERSHIP_SET_EXTENSION",
                                                rel_path=rel,
                                                lineno=lineno,
                                                description=f"widen `{op_str}` tuple on `{var_id}` with {new_lit}",
                                                new_source=patched,
                                                abstract_shape=f"$VAR {op_str} (..., $LIT)",
                                                heuristic_bonus=site_bonus + 2.5,
                                            ))

                        # 2c. Boundary relational flips (`<` <-> `<=`, `>` <-> `>=`, `==` <-> `!=`)
                        flip_map = {
                            ast.Lt: "<=",
                            ast.LtE: "<",
                            ast.Gt: ">=",
                            ast.GtE: ">",
                        }
                        if type(op) in flip_map:
                            new_op = flip_map[type(op)]
                            patched = replace_ast_node_source(
                                src, sub, f"{_unparse(left_node)} {new_op} {_unparse(comp_node)}"
                            )
                            if patched:
                                _emit(PatchCandidate(
                                    family="GUARD_BOUNDARY_OPERATOR",
                                    rel_path=rel,
                                    lineno=lineno,
                                    description=f"boundary flip to `{new_op}`",
                                    new_source=patched,
                                    abstract_shape=f"$A {new_op} $B",
                                    heuristic_bonus=site_bonus + 1.2,
                                ))

                # 2d. Frame-discriminated Conjunctive Restriction (`C and P`) & Disjunctive Relaxation (`C or P`)
                discriminators = _discriminating_predicates(f_frames, p_frames, file_attrs)
                old_cond_txt = _unparse(node.test)
                # Wrap compound `or` in parens before `and`
                wrapped_old = f"({old_cond_txt})" if isinstance(node.test, ast.BoolOp) else old_cond_txt
                for pred_false_on_fail in discriminators["false_on_fail_true_on_pass"][:6]:
                    if _is_degenerate_guard_extension(node.test, pred_false_on_fail):
                        continue
                    patched = replace_ast_node_source(src, node.test, f"{wrapped_old} and {pred_false_on_fail}")
                    if patched:
                        _emit(PatchCandidate(
                            family="GUARD_CONJUNCTIVE_RESTRICTION",
                            rel_path=rel,
                            lineno=lineno,
                            description=f"restrict guard with `and {pred_false_on_fail}`",
                            new_source=patched,
                            abstract_shape="($COND) and $PRED",
                            heuristic_bonus=site_bonus + 2.0,
                        ))
                # If `did_not_raise` is active and this `if` body raises that exact exception, boost `or P`!
                raises_target = any(
                    isinstance(b, ast.Raise) and (
                        not did_not_raise_excs
                        or any(exc_name in _unparse(b) for exc_name in did_not_raise_excs)
                    )
                    for b in (node.body if isinstance(node.body, list) else ())
                )
                for pred_true_on_fail in discriminators["true_on_fail_false_on_pass"][:6]:
                    if _is_degenerate_guard_extension(node.test, pred_true_on_fail):
                        continue
                    fam = "DID_NOT_RAISE_PREDICATE" if (did_not_raise_excs and raises_target) else "GUARD_DISJUNCTIVE_RELAXATION"
                    patched = replace_ast_node_source(src, node.test, f"{wrapped_old} or {pred_true_on_fail}")
                    if patched:
                        _emit(PatchCandidate(
                            family=fam,
                            rel_path=rel,
                            lineno=lineno,
                            description=f"widen guard with `or {pred_true_on_fail}`",
                            new_source=patched,
                            abstract_shape="($COND) or $PRED",
                            heuristic_bonus=site_bonus + (3.2 if fam == "DID_NOT_RAISE_PREDICATE" else 1.5),
                        ))

            # --- FAMILY 4: EXCEPTION SAFE GUARD (`None.attr` / `d[k]` / domain exception translation) ---
            if unexpected_crashes and isinstance(node, (ast.Assign, ast.Return, ast.Expr)):
                val_expr = getattr(node, "value", None)
                if val_expr is not None:
                    for sub in ast.walk(val_expr):
                        if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
                            base_name = sub.value.id
                            if _var_was_none(base_name, f_frames):
                                sub_s = _unparse(sub)
                                patched = replace_ast_node_source(
                                    src, sub, f"({sub_s} if {base_name} is not None else None)"
                                )
                                if patched:
                                    _emit(PatchCandidate(
                                        family="EXCEPTION_SAFE_GUARD",
                                        rel_path=rel,
                                        lineno=lineno,
                                        description=f"guard `None` receiver `{base_name}`",
                                        new_source=patched,
                                        abstract_shape="$X.$ATTR if $X is not None else None",
                                        heuristic_bonus=site_bonus + 2.4,
                                    ))

            # --- FAMILY 5: DEMAND-ALIGNED EXPRESSION SYNTHESIS (Induced f-strings, String/Slice/Attr) ---
            if isinstance(node, (ast.Assign, ast.Return, ast.Raise)):
                for sub in ast.walk(node):
                    # 5a. Induced f-string when a string constant is a prefix/substring of a demanded string!
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and len(sub.value) >= 4:
                        for demanded in string_demands:
                            if sub.value != demanded and sub.value in demanded:
                                for fstring_expr in _induce_fstrings(demanded, f_frames):
                                    patched = replace_ast_node_source(src, sub, fstring_expr)
                                    if patched:
                                        _emit(PatchCandidate(
                                            family="DEMAND_FSTRING_INDUCTION",
                                            rel_path=rel,
                                            lineno=lineno,
                                            description=f"induce f-string `{fstring_expr}` from demanded message",
                                            new_source=patched,
                                            abstract_shape='f"...{$VAR}..."',
                                            heuristic_bonus=site_bonus + 3.5,
                                        ))

                # 5b. Return / RHS expression projections (`.strip()`, `.lower()`, `±1`, file attribute swap)
                target_expr = getattr(node, "value", None) if isinstance(node, (ast.Assign, ast.Return)) else None
                if target_expr is not None and getattr(target_expr, "lineno", None) == lineno:
                    expr_txt = _unparse(target_expr)
                    # Attribute swap on same receiver (`ca.converter` -> `ca._converter`)
                    if isinstance(target_expr, ast.Attribute) and isinstance(target_expr.value, ast.Name):
                        recv = target_expr.value.id
                        for alt_attr in file_attrs.get("__all_attrs__", []):
                            if alt_attr != target_expr.attr and (
                                alt_attr.lstrip("_") == target_expr.attr.lstrip("_")
                            ):
                                patched = replace_ast_node_source(src, target_expr, f"{recv}.{alt_attr}")
                                if patched:
                                    _emit(PatchCandidate(
                                        family="DEMAND_EXPRESSION_ALIGNMENT",
                                        rel_path=rel,
                                        lineno=lineno,
                                        description=f"align attribute `{recv}.{target_expr.attr}` -> `{recv}.{alt_attr}`",
                                        new_source=patched,
                                        abstract_shape="$OBJ.$ALT_ATTR",
                                        heuristic_bonus=site_bonus + 2.2,
                                    ))
                    # Off-by-one slice/binop (`a + 1` <-> `a`, `s[1:]`, `.strip()`)
                    if isinstance(target_expr, ast.BinOp) and isinstance(target_expr.op, (ast.Add, ast.Sub)):
                        if isinstance(target_expr.right, ast.Constant) and target_expr.right.value == 1:
                            patched = replace_ast_node_source(src, target_expr, _unparse(target_expr.left))
                            if patched:
                                _emit(PatchCandidate(
                                    family="DEMAND_EXPRESSION_ALIGNMENT",
                                    rel_path=rel,
                                    lineno=lineno,
                                    description="remove off-by-one +/- 1",
                                    new_source=patched,
                                    abstract_shape="$X",
                                    heuristic_bonus=site_bonus + 1.1,
                                ))

    # Also scan ALL `raise ExpectedExc` guards in executed files when `DID NOT RAISE` occurred,
    # because in `DID NOT RAISE` the guard `if C: raise ExpectedExc` had `C == False`, so the
    # `if` line itself WAS hit even though the `raise` line inside it was NOT hit!
    if did_not_raise_excs:
        executed_rels = {row["rel"] for row in ranked_sites[:max_sites]}
        for rel in sorted(executed_rels):
            loaded = _get_file(rel)
            if not loaded:
                continue
            src, tree, file_attrs = loaded
            for node in ast.walk(tree):
                if not isinstance(node, ast.If):
                    continue
                if not any(
                    isinstance(b, ast.Raise)
                    and any(exc in _unparse(b) for exc in did_not_raise_excs)
                    for b in node.body
                ):
                    continue
                skey = f"{rel}:{node.lineno}"
                f_frames = fail_snaps.get(skey) or []
                p_frames = pass_snaps.get(skey) or []
                if not f_frames:
                    continue
                discriminators = _discriminating_predicates(f_frames, p_frames, file_attrs)
                old_txt = _unparse(node.test)
                wrapped = f"({old_txt})" if isinstance(node.test, ast.BoolOp) else old_txt
                for pred in discriminators["true_on_fail_false_on_pass"][:6]:
                    patched = replace_ast_node_source(src, node.test, f"{wrapped} or {pred}")
                    if patched:
                        _emit(PatchCandidate(
                            family="DID_NOT_RAISE_PREDICATE",
                            rel_path=rel,
                            lineno=node.lineno,
                            description=f"widen `{did_not_raise_excs[0]}` guard with `or {pred}`",
                            new_source=patched,
                            abstract_shape="($COND) or $PRED",
                            heuristic_bonus=3.8,
                        ))

    # Rank candidates by `memory.priority_score(family) * (1.0 + heuristic_bonus)`
    candidates.sort(
        key=lambda c: -(memory.priority_score(c.family) * (1.0 + c.heuristic_bonus))
    )
    return candidates[:max_candidates]


def _expr_was_falsy_non_none(expr: ast.expr, frames: Sequence[Mapping[str, Any]]) -> bool:
    if isinstance(expr, ast.Name):
        return any(bool((fr.get(expr.id) or {}).get("falsy_non_none")) for fr in frames)
    if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name):
        base = expr.value.id
        attr = expr.attr
        for fr in frames:
            binfo = fr.get(base) or {}
            aval = (binfo.get("attrs") or {}).get(attr)
            if aval is not None and aval is not False and aval != "" and aval != 0:
                if isinstance(aval, dict) and aval.get("__type__") not in ("NoneType", "bool"):
                    return True
            if aval in (0, "", ()):
                return True
    return False


def _var_was_none(name: str, frames: Sequence[Mapping[str, Any]]) -> bool:
    return any(bool((fr.get(name) or {}).get("is_none")) for fr in frames)


def _distinct_scalars_in_frames(name: str, frames: Sequence[Mapping[str, Any]]) -> list[Any]:
    out: list[Any] = []
    for fr in frames:
        vinfo = fr.get(name)
        if not vinfo:
            continue
        ok, val = _reconstruct_value(vinfo)
        if ok and val not in out:
            out.append(val)
    return out


def _induce_fstrings(demanded: str, frames: Sequence[Mapping[str, Any]]) -> list[str]:
    """Construct valid `f"..."` expressions from `demanded` using live frame variables."""
    out: list[str] = []
    for fr in frames:
        for var_name, vinfo in fr.items():
            if not var_name.isidentifier() or var_name.startswith("_"):
                continue
            ok, val = _reconstruct_value(vinfo)
            if not ok or val is None or isinstance(val, (bool, bytes, tuple)):
                continue
            for fmt_suffix, rendered in (("", str(val)), ("!r", repr(val))):
                if not rendered or len(rendered) > 80 or rendered not in demanded:
                    continue
                parts = demanded.split(rendered)
                if len(parts) < 2 or any("{" in p or "}" in p for p in parts):
                    continue
                hole = "{" + var_name + fmt_suffix + "}"
                body = hole.join(parts).replace("\\", "\\\\").replace('"', '\\"')
                expr = f'f"{body}"'
                if expr not in out:
                    out.append(expr)
    return out[:6]


def _discriminating_predicates(
    fail_frames: Sequence[Mapping[str, Any]],
    pass_frames: Sequence[Mapping[str, Any]],
    file_attrs: Mapping[str, Sequence[str]],
) -> dict[str, list[str]]:
    """Synthesize atomic Python predicates separating `fail_frames` from `pass_frames`.

    Returns:
      - `true_on_fail_false_on_pass`: predicates True on >=1 failing frame and False on 100% of `pass_frames`
      - `false_on_fail_true_on_pass`: predicates False on >=1 failing frame and True on 100% of `pass_frames`
    """
    true_fail_false_pass: list[str] = []
    false_fail_true_pass: list[str] = []
    if not fail_frames:
        return {
            "true_on_fail_false_on_pass": true_fail_false_pass,
            "false_on_fail_true_on_pass": false_fail_true_pass,
        }

    # Gather shared variable names
    var_names = sorted({k for fr in fail_frames for k in fr if k.isidentifier() and not k.startswith("__")})

    for var in var_names:
        f_infos = [fr[var] for fr in fail_frames if var in fr]
        p_infos = [fr[var] for fr in pass_frames if var in fr]
        if not f_infos:
            continue

        # 1. None / truthiness checks
        if any(i["is_none"] for i in f_infos) and p_infos and all(not i["is_none"] for i in p_infos):
            true_fail_false_pass.append(f"{var} is None")
            false_fail_true_pass.append(f"{var} is not None")
        if any(not i["is_none"] for i in f_infos) and p_infos and all(i["is_none"] for i in p_infos):
            true_fail_false_pass.append(f"{var} is not None")
            false_fail_true_pass.append(f"{var} is None")
        if any(not i["bool"] for i in f_infos) and p_infos and all(i["bool"] for i in p_infos):
            true_fail_false_pass.append(f"not {var}")
            false_fail_true_pass.append(f"bool({var})")

        # 2. String property discriminators (essential for parsers like packaging & tomli!)
        f_strs = [i["scalar"] for i in f_infos if isinstance(i.get("scalar"), str)]
        p_strs = [i["scalar"] for i in p_infos if isinstance(i.get("scalar"), str)]
        if f_strs:
            if any(s == "" for s in f_strs) and all(s != "" for s in p_strs):
                true_fail_false_pass.append(f"not {var}")
            if any(not s.isascii() for s in f_strs) and all(s.isascii() for s in p_strs):
                true_fail_false_pass.append(f"not {var}.isascii()")
                false_fail_true_pass.append(f"{var}.isascii()")
            if any(s != s.strip() for s in f_strs) and p_strs and all(s == s.strip() for s in p_strs):
                true_fail_false_pass.append(f"{var} != {var}.strip()")
                false_fail_true_pass.append(f"{var} == {var}.strip()")
            # Specific offending characters present in failing string and NEVER in any passing string
            p_chars = {ch for s in p_strs for ch in s}
            for s in f_strs:
                for ch in s:
                    if not ch.isalnum() and ch not in p_chars:
                        pred_in = f"{repr(ch)} in {var}"
                        pred_notin = f"{repr(ch)} not in {var}"
                        if pred_in not in true_fail_false_pass:
                            true_fail_false_pass.append(pred_in)
                        if pred_notin not in false_fail_true_pass:
                            false_fail_true_pass.append(pred_notin)
                        break

        # 3. Object attribute vs file-referenced module constants (`a.on_setattr is not setters.NO_OP`)
        f_attrs_list = [i.get("attrs") or {} for i in f_infos if i.get("attrs")]
        p_attrs_list = [i.get("attrs") or {} for i in p_infos if i.get("attrs")]
        if f_attrs_list:
            attr_keys = sorted({ak for d in f_attrs_list for ak in d})
            for ak in attr_keys:
                f_avals = [d[ak] for d in f_attrs_list if ak in d]
                p_avals = [d[ak] for d in p_attrs_list if ak in d]
                if not f_avals:
                    continue
                # Check None vs non-None on `var.ak`
                if any(v is None for v in f_avals) and p_avals and all(v is not None for v in p_avals):
                    true_fail_false_pass.append(f"{var}.{ak} is None")
                    false_fail_true_pass.append(f"{var}.{ak} is not None")
                if any(v is not None for v in f_avals) and p_avals and all(v is None for v in p_avals):
                    true_fail_false_pass.append(f"{var}.{ak} is not None")
                    false_fail_true_pass.append(f"{var}.{ak} is None")
                # Check module constant references already used in the file (e.g. `setters.NO_OP`)
                for mod_base, mod_consts in file_attrs.items():
                    if mod_base in ("self", "cls", "__all_attrs__", var):
                        continue
                    for mconst in mod_consts:
                        # Match if failing attribute repr mentions the constant name or differs from all passing!
                        f_reprs = [v.get("__repr__", repr(v)) if isinstance(v, dict) else repr(v) for v in f_avals]
                        p_reprs = [v.get("__repr__", repr(v)) if isinstance(v, dict) else repr(v) for v in p_avals]
                        if p_reprs and any(r not in p_reprs for r in f_reprs):
                            if any(mconst.lower() in r.lower() for r in f_reprs) or mconst.isupper():
                                cand_not = f"{var}.{ak} is not {mod_base}.{mconst}"
                                cand_is = f"{var}.{ak} is {mod_base}.{mconst}"
                                if cand_not not in false_fail_true_pass:
                                    false_fail_true_pass.append(cand_not)
                                if cand_is not in true_fail_false_pass:
                                    true_fail_false_pass.append(cand_is)

    return {
        "true_on_fail_false_on_pass": true_fail_false_pass,
        "false_on_fail_true_on_pass": false_fail_true_pass,
    }


# =========================================================================== #
# STAGE 3: CLOSED-LOOP VERIFICATION & FULL REPAIR ENTRY POINT
# =========================================================================== #

def repair_worktree(
    worktree: pathlib.Path,
    test_target: str | Sequence[str],
    *,
    python_exe: str | None = None,
    memory: SWERepairMemory | None = None,
    skill_store: Any | None = None,
    budget_s: float = 90.0,
    max_verifications: int = 20,
    admit_skills: bool = True,
    _allow_zipper: bool = True,
) -> dict[str, Any]:
    """Autonomously localize, synthesize, and verify a bug repair in `worktree` (ZERO diff leakage)."""
    started = time.perf_counter()
    memory = memory if memory is not None else SWERepairMemory()
    worktree = pathlib.Path(worktree).resolve()
    primary_test_str = test_target if isinstance(test_target, str) else str(test_target[0])

    # 1. Baseline suite run: confirm there is a real failure and record passing baseline!
    baseline = run_pytest_verdicts(
        worktree, test_target, python_exe=python_exe, timeout_s=min(45.0, budget_s * 0.5)
    )
    if not baseline["verdicts"]:
        return {
            "schema": SCHEMA,
            "status": "REFUSED__SUITE_DID_NOT_COLLECT",
            "pass": False,
            "detail": baseline["output"][-400:],
            "seconds": round(time.perf_counter() - started, 4),
            "model_calls": 0,
        }
    if not baseline["failing"]:
        return {
            "schema": SCHEMA,
            "status": "REFUSED__NO_FAILING_TEST_AT_START",
            "pass": False,
            "passing_baseline": len(baseline["passing"]),
            "seconds": round(time.perf_counter() - started, 4),
            "model_calls": 0,
        }

    failing_nodes = baseline["failing"]
    passing_nodes = baseline["passing"]

    # 2. Build Cross-File & Cross-Process Causal Data-Flow Graph + 1-pass frame trace (zero diff input!)
    dfg = fpm.collect_causal_dataflow_graph(
        worktree,
        failing_nodes,
        passing_nodes,
        default_test_file=primary_test_str,
        pytest_output=baseline.get("output", ""),
        python_exe=python_exe,
        timeout_s=min(12.0, max(5.0, budget_s * 0.22)),
    )
    dfg_ranked_sites = dfg.rank_causal_sites(len(failing_nodes))

    trace_data = collect_causal_trace(
        worktree,
        failing_nodes,
        passing_nodes,
        primary_test_str,
        python_exe=python_exe,
        timeout_s=min(12.0, max(5.0, budget_s * 0.22)),
    )
    local_sites = localize_suspicious_sites(trace_data)

    # Interleave cross-file/cross-process DFG sites 1-for-1 with crash-tail local sites so low-score
    # tail DFG sites never bury `local_sites[0]` past `max_sites`!
    seen_site_keys: set[tuple[str, int]] = set()
    ranked_sites: list[dict[str, Any]] = []
    max_len = max(len(dfg_ranked_sites), len(local_sites))
    interleaved: list[Mapping[str, Any]] = []
    for idx_i in range(max_len):
        if idx_i < len(dfg_ranked_sites):
            interleaved.append(dfg_ranked_sites[idx_i])
        if idx_i < len(local_sites):
            interleaved.append(local_sites[idx_i])
    for s in interleaved:
        key = (
            str(s.get("rel") or s.get("file") or s.get("rel_path")),
            int(s.get("lineno") if s.get("lineno") is not None else s["line"]),
        )
        if key not in seen_site_keys:
            seen_site_keys.add(key)
            ranked_sites.append({
                **s,
                "rel": key[0],
                "file": key[0],
                "rel_path": key[0],
                "lineno": key[1],
                "line": key[1],
                "score": float(s.get("score") if s.get("score") is not None else s.get("ochiai", 0.0)),
            })

    top_localized_files: list[str] = []
    for s in ranked_sites:
        rf = s["rel"]
        if rf not in top_localized_files:
            top_localized_files.append(rf)
            if len(top_localized_files) >= 5:
                break

    if not ranked_sites:
        return {
            "schema": SCHEMA,
            "status": "OPEN__NO_PROJECT_LINES_TRACED",
            "pass": False,
            "failing_count": len(failing_nodes),
            "seconds": round(time.perf_counter() - started, 4),
            "model_calls": 0,
        }

    # 3. Boot Pre-Warmed CoW Fork Mental Simulator (`0` disk writes) & Run Angelic CEGIS + Demand Synthesis!
    deadline = started + budget_s
    sim_verified_patches: list[dict[str, Any]] = []
    mental_stats = {
        "mental_simulations": 0,
        "mental_pruned": 0,
        "cow_fork_simulations": 0,
        "angelic_interventions": 0,
        "cegis_refinements": 0,
        "cross_process_events": dfg.cross_process_events,
    }

    structural_cands = synthesize_candidates(
        worktree, trace_data, ranked_sites, memory, python_exe=python_exe
    )

    with fpm.CoWProgramSimulator(
        worktree, failing_nodes, passing_nodes, default_test_file=primary_test_str, python_exe=python_exe
    ) as cow_sim:
        # 3a. Multi-Statement AST Subtree Skill Retrieval (`O(1)`-removable external skill store)
        if skill_store is not None and getattr(skill_store, "mode", "generalized") != "disabled":
            seen_sub_fns: set[tuple[str, int]] = set()
            for r_site in ranked_sites[:12]:
                rf_s = str(r_site.get("file") or "")
                ln_s = int(r_site.get("line") or 0)
                fp_s = worktree / rf_s
                if not fp_s.is_file():
                    continue
                try:
                    src_s = fp_s.read_text(encoding="utf-8")
                    tree_s = ast.parse(src_s)
                except (OSError, SyntaxError):
                    continue
                _, enc_fn_s, _ = fpm.AngelicCEGISSynthesizer._find_enclosing_stmt_and_func(tree_s, ln_s)
                if enc_fn_s is None or not enc_fn_s.body:
                    continue
                fk_s = (rf_s, enc_fn_s.lineno)
                if fk_s in seen_sub_fns:
                    continue
                seen_sub_fns.add(fk_s)
                lines_s = src_s.splitlines(keepends=True)
                b_start = enc_fn_s.body[0].lineno - 1
                b_end = getattr(enc_fn_s.body[-1], "end_lineno", enc_fn_s.body[-1].lineno)
                raw_body = "".join(lines_s[b_start:b_end])
                indent_match = re.match(r"^([ \t]*)", lines_s[b_start]) if b_start < len(lines_s) else None
                body_indent = indent_match.group(1) if indent_match else "    "
                retrieved_hits = skill_store.retrieve_for_subtree(raw_body, target_lang="python")
                for new_body_dedented, matched_skill_id in retrieved_hits[:4]:
                    if skill_store.is_blocked_by_negative_invariant(
                        target_ast_shape=enc_fn_s.name,
                        candidate_delta_op=matched_skill_id,
                    ):
                        continue
                    reindented = "".join(
                        (body_indent + ln if ln.strip() else ln)
                        for ln in (new_body_dedented.rstrip("\n") + "\n").splitlines(keepends=True)
                    )
                    cand_full_src = "".join(lines_s[:b_start]) + reindented + "".join(lines_s[b_end:])
                    try:
                        ast.parse(cand_full_src)
                    except SyntaxError:
                        continue
                    if not cow_sim.ready or cow_sim.simulate_patch({rf_s: cand_full_src}).get("ok"):
                        sim_verified_patches.append({
                            "file_patches": {rf_s: cand_full_src},
                            "primary_file": rf_s,
                            "primary_line": enc_fn_s.lineno,
                            "family": "SUBTREE_SKILL_REUSE",
                            "mechanism": "SUBTREE_SKILL_REUSE",
                            "description": f"Reused anti-unified subtree skill `{matched_skill_id}` on {rf_s}:{enc_fn_s.lineno}",
                            "abstract_shape": f"SUBTREE_SKILL({matched_skill_id})",
                            "reused_skill_id": matched_skill_id,
                        })

        if dfg_ranked_sites and not sim_verified_patches:
            cegis = fpm.AngelicCEGISSynthesizer(worktree, dfg, cow_sim)
            # Always reserve >= 30% of `budget_s` for structural CoW screening + Step 4 clean-process verification!
            cegis_deadline = min(
                deadline - max(10.0, budget_s * 0.30),
                time.perf_counter() + max(6.0, budget_s * 0.32),
            )
            cegis_winners = cegis.run_cegis(
                dfg_ranked_sites,
                deadline_monotonic=max(time.perf_counter() + 2.0, cegis_deadline),
            )
            mental_stats["mental_simulations"] = cegis.mental_simulations
            mental_stats["mental_pruned"] = cegis.mental_pruned
            mental_stats["angelic_interventions"] = cegis.angelic_interventions_tested
            mental_stats["cegis_refinements"] = cegis.cegis_refinements

            for cw in cegis_winners:
                # Map canonical semantic mechanism while preserving specialized labels when exact!
                fam = cw.mechanism
                matched_sc = next(
                    (sc for sc in structural_cands if cw.file_patches == {sc.rel_path: sc.new_source}),
                    None,
                )
                if matched_sc is not None:
                    fam = matched_sc.family
                elif "is not None" in cw.description and " is None" not in cw.description.split("->")[0]:
                    fam = "FALSY_NON_NONE_GUARD"
                elif "tuple(" in cw.description and "Stream materialization" in cw.description:
                    fam = "ITERATOR_MATERIALIZATION"
                elif (
                    " in (" in cw.description
                    or " in {" in cw.description
                    or " not in (" in cw.description
                    or ("!=" in cw.description and "and not (" in cw.description and "==" in cw.description)
                ):
                    fam = "MEMBERSHIP_SET_EXTENSION"
                elif cw.mechanism == "ANGELIC_BRANCH_CEGIS" and "->" in cw.description and ") or (" in cw.description.split("->", 1)[-1]:
                    fam = "GUARD_DISJUNCTIVE_RELAXATION"
                sim_verified_patches.append({
                    "file_patches": dict(cw.file_patches),
                    "primary_file": cw.primary_file,
                    "primary_line": cw.primary_line,
                    "family": fam,
                    "mechanism": cw.mechanism,
                    "description": cw.description,
                    "abstract_shape": cw.semantic_delta_ir,
                })

        # Screen supplementary structural/demand candidates in CoW RAM (~2 ms, 0 disk writes!)
        partial_cow_cands: list[PatchCandidate] = []
        if cow_sim.ready:
            for sc in structural_cands[: max(64, max_verifications * 3)]:
                if time.perf_counter() >= deadline:
                    break
                if any(
                    p["file_patches"] == {sc.rel_path: sc.new_source}
                    for p in sim_verified_patches
                ):
                    continue
                sres = cow_sim.simulate_patch({sc.rel_path: sc.new_source})
                if sres.get("ok"):
                    entry_sc = {
                        "file_patches": {sc.rel_path: sc.new_source},
                        "primary_file": sc.rel_path,
                        "primary_line": sc.lineno,
                        "family": sc.family,
                        "mechanism": sc.family,
                        "description": sc.description,
                        "abstract_shape": sc.abstract_shape,
                    }
                    # Prefer general structural repairs (`ITERATOR_MATERIALIZATION`, `MEMBERSHIP_SET_EXTENSION`)
                    # ahead of literal-return `STUN_GUARD_SYNTHESIS` guards!
                    stun_idx = next(
                        (i_p for i_p, p_e in enumerate(sim_verified_patches) if p_e.get("mechanism") == "STUN_GUARD_SYNTHESIS"),
                        None,
                    )
                    if stun_idx is not None and sc.family in {"ITERATOR_MATERIALIZATION", "MEMBERSHIP_SET_EXTENSION"}:
                        sim_verified_patches.insert(stun_idx, entry_sc)
                    else:
                        sim_verified_patches.append(entry_sc)
                elif _allow_zipper and len(partial_cow_cands) < 3:
                    pmask = list(sres.get("passed_fail_mask") or [])
                    if len(pmask) >= 2 and 1 <= sum(1 for x in pmask if x) < len(pmask):
                        partial_cow_cands.append(sc)
            for sc in [*partial_cow_cands, *structural_cands[:6]]:
                if not any(p["file_patches"] == {sc.rel_path: sc.new_source} for p in sim_verified_patches):
                    sim_verified_patches.append({
                        "file_patches": {sc.rel_path: sc.new_source},
                        "primary_file": sc.rel_path,
                        "primary_line": sc.lineno,
                        "family": sc.family,
                        "mechanism": sc.family,
                        "description": sc.description,
                        "abstract_shape": sc.abstract_shape,
                    })
        else:
            for sc in structural_cands[:max_verifications]:
                sim_verified_patches.append({
                    "file_patches": {sc.rel_path: sc.new_source},
                    "primary_file": sc.rel_path,
                    "primary_line": sc.lineno,
                    "family": sc.family,
                    "mechanism": sc.family,
                    "description": sc.description,
                    "abstract_shape": sc.abstract_shape,
                })
        mental_stats["cow_fork_simulations"] = cow_sim.simulations_count

    total_generated = mental_stats["mental_simulations"] + len(structural_cands)
    if not sim_verified_patches and total_generated == 0:
        return {
            "schema": SCHEMA,
            "status": "OPEN__NO_CANDIDATE_SYNTHESIZED",
            "pass": False,
            "top_localized_sites": ranked_sites[:5],
            "mental_model_stats": mental_stats,
            "seconds": round(time.perf_counter() - started, 4),
            "model_calls": 0,
        }

    # 4. Cold Clean-Process Full-Suite Referee + Runner Canary (`0` trust in simulation alone!)
    originals: dict[str, str] = {}
    attempts: list[dict[str, Any]] = []
    zipper_seeds: list[tuple[int, int, dict[str, Any], list[str]]] = []

    sibling_baselines: dict[tuple[str, ...], dict[str, Any]] = {}
    def check_siblings(names: list[str]) -> dict[str, Any]:
        remaining = budget_s - (time.perf_counter() - started)
        if remaining <= 0:
            return {'passing': [], 'failing': [], 'timeout': True}
        return run_pytest_verdicts(worktree, names, python_exe=python_exe, timeout_s=min(18.0, remaining))

    for idx, item in enumerate(sim_verified_patches[:max_verifications]):
        if time.perf_counter() - started > budget_s:
            break
        file_patches: Mapping[str, str] = item["file_patches"]
        for rel_p in file_patches:
            if rel_p not in originals:
                originals[rel_p] = (worktree / rel_p).read_text(encoding="utf-8")

        t0 = time.perf_counter()
        for rel_p, new_src in file_patches.items():
            (worktree / rel_p).write_text(new_src, encoding="utf-8")
            shutil.rmtree((worktree / rel_p).parent / "__pycache__", ignore_errors=True)
        try:
            full = run_pytest_verdicts(
                worktree, test_target, python_exe=python_exe, timeout_s=40.0
            )
            regressed = not _passed_baseline_nodes(baseline, full)
            if regressed:
                # Record partial-progress seed for Def-Use Relational Zipper (Wall 3):
                # If `item` strictly fixed >= 1 original failing test (or ALL original failing tests)
                # while leaving 1..3 remaining/secondary failures, propagate a 2nd hop along call edges!
                cur_fails = list(full.get("failing") or [])
                orig_fail_set = set(failing_nodes)
                fixed_orig = len(orig_fail_set.intersection(full["passing"]))
                lost = sorted(set(passing_nodes).intersection(cur_fails))
                cause = "REGRESSED_PASSING_TESTS" if lost else "BASELINE_NODES_NOT_ALL_PASSING"
                if _allow_zipper and fixed_orig >= 1 and 1 <= len(cur_fails) <= 3:
                    zipper_seeds.append((fixed_orig, -len(cur_fails), item, cur_fails))
                memory.record_outcome(
                    item["family"],
                    verified=False,
                    caused_regression=bool(lost),
                    elapsed_s=time.perf_counter() - t0,
                )
                if lost and skill_store is not None and hasattr(skill_store, "record_negative_invariant"):
                    skill_store.record_negative_invariant(
                        domain="swe_python",
                        target_ast_shape=str(item.get("primary_file") or ""),
                        forbidden_delta_op=str(item.get("abstract_shape") or item["family"]),
                        failure_kind="REGRESSED_PASSING_TESTS",
                        minimal_witness={"formerly_passing": lost[:3]},
                    )
                attempts.append({
                    "rank": idx + 1,
                    "family": item["family"],
                    "site": f"{item['primary_file']}:{item['primary_line']}",
                    "description": item["description"],
                    "verdict": cause,
                })
                for rel_p in file_patches:
                    (worktree / rel_p).write_text(originals[rel_p], encoding="utf-8")
                continue

            if not verify_runner_canary(worktree, python_exe=python_exe):
                memory.record_outcome(
                    item["family"],
                    verified=False,
                    caused_regression=True,
                    elapsed_s=time.perf_counter() - t0,
                )
                attempts.append({
                    "rank": idx + 1,
                    "family": item["family"],
                    "site": f"{item['primary_file']}:{item['primary_line']}",
                    "description": item["description"],
                    "verdict": "REFUSED__RUNNER_CANARY_LOBOTOMIZED",
                })
                for rel_p in file_patches:
                    (worktree / rel_p).write_text(originals[rel_p], encoding="utf-8")
                continue

            # Cross-module reverse-import & stem-matched impacted test referee (`IncrementalSemanticGraph` + `src/`-layout scan)!
            # Always enforced (never skipped near timeout!) so degenerate patches cannot sneak past narrow single-test targets.
            base_test_rel = primary_test_str.split("::")[0]
            if True:
                imp = isg.query_impacted_tests(worktree, ".", list(file_patches.keys()))
                cand_tests: list[str] = []
                if imp.get("exact_hit"):
                    cand_tests.extend(imp.get("impacted_tests") or [])
                edited_stems = {pathlib.Path(rp).stem.removeprefix("_") for rp in file_patches}
                # Also scan 2-hop `src/`-stripped dotted module names (`utils.py` -> `metadata.py` -> `test_metadata.py`)!
                direct_mods: set[str] = set()
                for rp in file_patches:
                    direct_mods.add(rp.removeprefix("src/").removesuffix(".py").replace("/", "."))
                hop2_mods: set[str] = set(direct_mods)
                src_root = worktree / "src" if (worktree / "src").is_dir() else worktree
                scan_dl = time.perf_counter() + 2.5
                for idx_py, py_p in enumerate(src_root.rglob("*.py")):
                    if idx_py >= 600 or time.perf_counter() >= scan_dl:
                        break
                    rel_py = py_p.relative_to(worktree).as_posix()
                    if rel_py.startswith(("tests/", "test/", "testing/")) or py_p.stat().st_size > 180_000:
                        continue
                    py_txt = py_p.read_text(encoding="utf-8", errors="ignore")
                    for dm in direct_mods:
                        leaf = dm.rsplit(".", 1)[-1]
                        if dm in py_txt or f"import {leaf}" in py_txt:
                            hop2_mods.add(rel_py.removeprefix("src/").removesuffix(".py").replace("/", "."))
                mod_tokens: list[str] = []
                for nm in sorted(hop2_mods)[:12]:
                    mod_tokens.append(nm)
                    if "." in nm:
                        pkg_p, leaf_m = nm.rsplit(".", 1)
                        mod_tokens.append(f"from {pkg_p} import {leaf_m}")
                all_test_candidates = list(imp.get("impacted_tests") or [])
                for td_name in ("tests", "test", "testing"):
                    td_p = worktree / td_name
                    if td_p.is_dir():
                        for idx_tf, tf_cand in enumerate(td_p.rglob("test_*.py")):
                            if idx_tf >= 600 or time.perf_counter() >= scan_dl:
                                break
                            r_tf = tf_cand.relative_to(worktree).as_posix()
                            if r_tf not in all_test_candidates:
                                all_test_candidates.append(r_tf)
                # Prioritize exact stem-matched unit test files (`main.py` -> `tests/test_main.py`) first!
                for tf_rel in all_test_candidates:
                    if tf_rel == base_test_rel or tf_rel in cand_tests:
                        continue
                    tf_stem = pathlib.Path(tf_rel).stem.removeprefix("test_").removesuffix("_test")
                    if tf_stem in edited_stems:
                        cand_tests.insert(0, tf_rel)
                for tf_rel in all_test_candidates:
                    if tf_rel == base_test_rel or tf_rel in cand_tests:
                        continue
                    tf_p = worktree / tf_rel
                    if tf_p.is_file() and tf_p.stat().st_size < 180_000:
                        txt_t = tf_p.read_text(encoding="utf-8", errors="ignore")
                        if any(tok in txt_t for tok in mod_tokens):
                            cand_tests.append(tf_rel)
                sibling_tests = [
                    t for t in cand_tests
                    if t != base_test_rel and (worktree / t).is_file() and (worktree / t).stat().st_size < 180_000
                ][:6]
                if sibling_tests:
                    key = tuple(sibling_tests)
                    if key not in sibling_baselines:
                        for rel_p in file_patches:
                            (worktree / rel_p).write_text(originals[rel_p], encoding="utf-8")
                        sibling_baselines[key] = check_siblings(sibling_tests)
                        for rel_p, new_src in file_patches.items():
                            (worktree / rel_p).write_text(new_src, encoding="utf-8")
                    pre_sib = sibling_baselines[key]
                    sib_res = check_siblings(sibling_tests)
                    reason = _regression_check(pre_sib, sib_res)
                    if reason:
                        new_fails = sorted(set(sib_res['failing']) - set(pre_sib['failing']))
                        if _allow_zipper and reason.startswith('REGRESSED') and 1 <= len(new_fails) <= 3:
                            zipper_seeds.append((len(failing_nodes), -len(new_fails), item, new_fails))
                        memory.record_outcome(item['family'], verified=False, caused_regression=bool(new_fails),
                                              elapsed_s=time.perf_counter() - t0)
                        attempts.append({'rank': idx + 1, 'family': item['family'],
                                         'site': f"{item['primary_file']}:{item['primary_line']}",
                                         'description': item['description'], 'verdict': reason,
                                         'cross_module_regressions': new_fails[:4]})
                        for rel_p in file_patches:
                            (worktree / rel_p).write_text(originals[rel_p], encoding="utf-8")
                        continue

            memory.record_outcome(
                item["family"],
                verified=True,
                caused_regression=False,
                elapsed_s=time.perf_counter() - t0,
                abstract_shape=item["abstract_shape"],
            )
            learned_skill_id = None
            reused_skill_id = item.get("reused_skill_id")
            admission = None if admit_skills else "NOT_ADMITTED__PROVISIONAL_WITNESS"
            if admit_skills and skill_store is not None and reused_skill_id is None and hasattr(skill_store, "try_admit_subtree"):
                # A green multi-file transaction does not verify any one of its
                # edits in isolation. Feed the learner the whole checked pair
                # or abstain; independent line numbers can point at different
                # functions after a deletion.
                if len(file_patches) != 1:
                    admission = "NOT_ADMITTED__MULTI_FILE_TRANSACTION"
                else:
                    (rel, after), = file_patches.items()
                    before = originals[rel]
                    ok_adm, admission = skill_store.try_admit_subtree(
                        domain="swe_python", concrete_before=before, concrete_after=after,
                        verified=True, goal_relevant=True, probes_before_success=1 + len(attempts),
                        raw_episode_bytes=len(before.encode()) + len(after.encode()),
                        source_fingerprint=hashlib.sha256(before.encode()).hexdigest(),
                        witness_inputs=[{"failing_nodes": list(failing_nodes[:3])}],
                        revalidation_probe={"source": rel, "test_target": test_target,
                                            "candidate_sha256": hashlib.sha256(after.encode()).hexdigest()},
                    )
                    if ok_adm:
                        learned_skill_id = admission

            attempts.append({
                "rank": idx + 1,
                "family": item["family"],
                "site": f"{item['primary_file']}:{item['primary_line']}",
                "description": item["description"],
                "verdict": "VERIFIED_FULL_SUITE_GREEN",
            })
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "status": "PASS__VERIFIED_REPAIR",
                "pass": True,
                "winning_rank": idx + 1,
                "winning_family": item["family"],
                "winning_mechanism": item["mechanism"],
                "learned_skill_id": learned_skill_id,
                "subtree_admission": admission,
                "reused_skill_id": reused_skill_id,
                "repaired_file": item["primary_file"],
                "repaired_files": sorted(file_patches.keys()),
                "repaired_line": item["primary_line"],
                "description": item["description"],
                "abstract_shape": item["abstract_shape"],
                "semantic_delta_ir": item["abstract_shape"],
                "tests_passing_before": len(passing_nodes),
                "tests_failing_before": len(failing_nodes),
                "tests_passing_after": len(full["passing"]),
                "tests_failing_after": 0,
                "candidates_generated": total_generated,
                "verifications_run": idx + 1,
                "mental_model_stats": mental_stats,
                "top_localized_sites": ranked_sites[:5],
                "top_localized_files": top_localized_files,
                "attempts": attempts,
                "seconds": round(time.perf_counter() - started, 4),
                "model_calls": 0,
                "parameters_stored": 0,
            }
        except Exception:
            for rel_p in file_patches:
                (worktree / rel_p).write_text(originals[rel_p], encoding="utf-8")
            raise

    for rel_path, orig_src in originals.items():
        (worktree / rel_path).write_text(orig_src, encoding="utf-8")
        shutil.rmtree((worktree / rel_path).parent / "__pycache__", ignore_errors=True)

    target_rel_list = [
        str(t).split("::")[0]
        for t in ([test_target] if isinstance(test_target, str) else list(test_target))
    ]

    def _resolve_node_test_file(node_id: str) -> str:
        head = node_id.split("::")[0]
        if head.endswith(".py"):
            return head
        # `unittest` node format in Python 3.11+: `"test_method (pkg.test_module.ClassName.test_method)"`
        m_ut = re.search(r"\(([\w.]+)\)", node_id)
        if m_ut:
            dotted_parts = m_ut.group(1).split(".")
            for part_tok in dotted_parts:
                for cand_t in target_rel_list:
                    if pathlib.Path(cand_t).stem == part_tok:
                        return cand_t
                for td_nm in ("tests", "test", "testing", "."):
                    cand_p = worktree / td_nm / f"{part_tok}.py"
                    if cand_p.is_file():
                        return cand_p.relative_to(worktree).as_posix()
        return ""

    # 5A. Petri Articulation-Point Multi-Test-File Checkpoint Composition (Wall 3):
    # When failing tests span 2..3 distinct test modules `[T_1, ..., T_k]` and joint single-site synthesis
    # found no single-file fix, solve each failing module sequentially into a speculative checkpoint `P_1 o ... o P_k`
    # and accept ONLY if the full union suite + runner canary passes!
    distinct_fail_files = sorted({rf for rf in (_resolve_node_test_file(n) for n in failing_nodes) if rf})
    if (
        _allow_zipper
        and not zipper_seeds
        and 2 <= len(distinct_fail_files) <= 3
        and (budget_s - (time.perf_counter() - started)) > 16.0
    ):
        saved_t_blobs: dict[str, bytes] = {}
        for t_arg in ([test_target] if isinstance(test_target, str) else list(test_target)):
            t_rel = str(t_arg).split("::")[0]
            if (worktree / t_rel).is_file():
                saved_t_blobs[t_rel] = (worktree / t_rel).read_bytes()
        composed_files: list[str] = []
        composed_descs: list[str] = []
        verified_art = False
        try:
            for idx_art, tf_part in enumerate(distinct_fail_files):
                rem_art = budget_s - (time.perf_counter() - started)
                if rem_art < 8.0:
                    composed_files.clear()
                    break
                per_hop_b = max(8.0, (rem_art - 4.0) / max(1, len(distinct_fail_files) - idx_art))
                hop_res = repair_worktree(
                    worktree,
                    tf_part,
                    python_exe=python_exe,
                    memory=memory,
                    skill_store=skill_store,
                    budget_s=min(28.0, per_hop_b),
                    max_verifications=8,
                    admit_skills=False,  # subgoal, not yet a verified transaction
                    _allow_zipper=False,
                )
                if not hop_res.get("pass"):
                    if hop_res.get("status") == "REFUSED__NO_FAILING_TEST_AT_START" and composed_files:
                        continue
                    composed_files.clear()
                    break
                rf_h = str(hop_res.get("repaired_file") or "")
                if rf_h and rf_h not in composed_files:
                    composed_files.append(rf_h)
                composed_descs.append(str(hop_res.get("description") or rf_h))
            if composed_files:
                joint_res = run_pytest_verdicts(
                    worktree, test_target, python_exe=python_exe, timeout_s=30.0
                )
                if (
                    _passed_baseline_nodes(baseline, joint_res)
                    and verify_runner_canary(worktree, python_exe=python_exe)
                ):
                    verified_art = True
                    return {
                        "schema": SCHEMA,
                        "authority": AUTHORITY,
                        "status": "PASS__VERIFIED_REPAIR",
                        "pass": True,
                        "winning_rank": len(attempts) + 1,
                        "winning_family": "ARTICULATION_CHECKPOINT_ZIPPER",
                        "winning_mechanism": "ARTICULATION_CHECKPOINT_ZIPPER",
                        "learned_skill_id": None,
                        "repaired_file": composed_files[0],
                        "repaired_files": sorted(composed_files),
                        "repaired_line": 1,
                        "description": " + ".join(composed_descs),
                        "abstract_shape": "ARTICULATION_CHECKPOINT_ZIPPER",
                        "semantic_delta_ir": "ARTICULATION_CHECKPOINT_ZIPPER",
                        "tests_passing_before": len(passing_nodes),
                        "tests_failing_before": len(failing_nodes),
                        "tests_passing_after": len(joint_res["passing"]),
                        "tests_failing_after": 0,
                        "candidates_generated": total_generated,
                        "verifications_run": len(attempts) + len(composed_files),
                        "mental_model_stats": mental_stats,
                        "top_localized_sites": ranked_sites[:5],
                        "top_localized_files": top_localized_files,
                        "attempts": attempts[:10],
                        "seconds": round(time.perf_counter() - started, 4),
                        "model_calls": 0,
                        "parameters_stored": 0,
                    }
        finally:
            if not verified_art:
                subprocess.run(
                    ["git", "-C", str(worktree), "checkout", "--", "."],
                    capture_output=True,
                    timeout=15,
                )
                for t_rel, t_bytes in saved_t_blobs.items():
                    (worktree / t_rel).write_bytes(t_bytes)

    # 5B. Def-Use Relational Zipper (Wall 3 Multi-File / Multi-Site Coupled Propagation):
    # Propagate top partial-progress root patch `P_1` into a bounded 2nd-hop synthesis on remaining
    # caller/callee failures `rem_fails`, accepting `P_1 U P_2` ONLY if the entire combined suite passes!
    if _allow_zipper and zipper_seeds and (budget_s - (time.perf_counter() - started)) > 10.0:
        zipper_seeds.sort(key=lambda t: (-t[0], -t[1]))
        seen_zip_patches: set[tuple[tuple[str, str], ...]] = set()
        for _, _, root_item, rem_fails in zipper_seeds[:2]:
            rem_budget_z = budget_s - (time.perf_counter() - started)
            if rem_budget_z < 8.0:
                break
            fp_sig = tuple(sorted(root_item["file_patches"].items()))
            if fp_sig in seen_zip_patches:
                continue
            seen_zip_patches.add(fp_sig)
            for rel_p, new_src in root_item["file_patches"].items():
                if rel_p not in originals:
                    originals[rel_p] = (worktree / rel_p).read_text(encoding="utf-8")
                (worktree / rel_p).write_text(new_src, encoding="utf-8")
                shutil.rmtree((worktree / rel_p).parent / "__pycache__", ignore_errors=True)
            try:
                rem_test_files = sorted({rf for rf in (_resolve_node_test_file(n) for n in rem_fails) if rf})
                hop2_target: str | Sequence[str] = (
                    rem_test_files[0] if len(rem_test_files) == 1 else (rem_test_files or test_target)
                )
                hop2 = repair_worktree(
                    worktree,
                    hop2_target,
                    python_exe=python_exe,
                    memory=memory,
                    skill_store=skill_store,
                    budget_s=min(24.0, rem_budget_z - 3.0),
                    max_verifications=8,
                    admit_skills=False,  # subgoal, not yet a verified transaction
                    _allow_zipper=False,
                )
                if hop2.get("pass"):
                    union_targets = sorted({
                        *( [test_target] if isinstance(test_target, str) else list(test_target) ),
                        *rem_test_files,
                    })
                    final_check = run_pytest_verdicts(
                        worktree, union_targets, python_exe=python_exe, timeout_s=30.0
                    )
                    if (
                        _passed_baseline_nodes(baseline, final_check)
                        and verify_runner_canary(worktree, python_exe=python_exe)
                    ):
                        combined_files = sorted({
                            *root_item["file_patches"].keys(),
                            *(hop2.get("repaired_files") or [hop2.get("repaired_file")]),
                        })
                        return {
                            "schema": SCHEMA,
                            "authority": AUTHORITY,
                            "status": "PASS__VERIFIED_REPAIR",
                            "pass": True,
                            "winning_rank": len(attempts) + 1,
                            "winning_family": "DEF_USE_RELATIONAL_ZIPPER",
                            "winning_mechanism": "DEF_USE_RELATIONAL_ZIPPER",
                            "learned_skill_id": hop2.get("learned_skill_id"),
                            "repaired_file": root_item["primary_file"],
                            "repaired_files": combined_files,
                            "repaired_line": root_item["primary_line"],
                            "description": f"Zipper[{root_item['description']} ==> {hop2.get('description')}]",
                            "abstract_shape": "DEF_USE_RELATIONAL_ZIPPER",
                            "semantic_delta_ir": "DEF_USE_RELATIONAL_ZIPPER",
                            "tests_passing_before": len(passing_nodes),
                            "tests_failing_before": len(failing_nodes),
                            "tests_passing_after": len(final_check["passing"]),
                            "tests_failing_after": 0,
                            "candidates_generated": total_generated + int(hop2.get("candidates_generated", 0)),
                            "verifications_run": len(attempts) + int(hop2.get("verifications_run", 1)),
                            "mental_model_stats": mental_stats,
                            "top_localized_sites": ranked_sites[:5],
                            "top_localized_files": top_localized_files,
                            "attempts": attempts[:10],
                            "seconds": round(time.perf_counter() - started, 4),
                            "model_calls": 0,
                            "parameters_stored": 0,
                        }
                # Revert ANY modifications made by hop1 or aborted hop2
                subprocess.run(
                    ["git", "-C", str(worktree), "checkout", "--", "."],
                    capture_output=True,
                    timeout=15,
                )
                for rel_path, orig_src in originals.items():
                    (worktree / rel_path).write_text(orig_src, encoding="utf-8")
                    shutil.rmtree((worktree / rel_path).parent / "__pycache__", ignore_errors=True)
            except Exception:
                for rel_path, orig_src in originals.items():
                    (worktree / rel_path).write_text(orig_src, encoding="utf-8")

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "status": "OPEN__NO_CANDIDATE_VERIFIED",
        "pass": False,
        "candidates_generated": total_generated,
        "verifications_run": len(attempts),
        "mental_model_stats": mental_stats,
        "top_localized_sites": ranked_sites[:5],
        "top_localized_files": top_localized_files,
        "attempts": attempts[:10],
        "seconds": round(time.perf_counter() - started, 4),
        "model_calls": 0,
        "parameters_stored": 0,
    }
