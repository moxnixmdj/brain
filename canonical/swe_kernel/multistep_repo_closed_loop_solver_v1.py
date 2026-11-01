#!/usr/bin/env python3
"""Multi-Step Closed-Loop Repository Solver, Differential Trace Localizer & Race Prober.

Solves unseen multi-file repository bugs from raw failing symptoms alone (zero file
or symbol hints required) with K3 = 0 (zero model calls) and $0 incremental spend:

1. **Zero-Hint Differential Fault Localization (`localize_faults_by_differential_trace`)**:
   Executes discovered repository tests in an isolated child process under `sys.settrace`,
   recording per-test line/function spectra, exception frames, and live call arguments/returns.
   Ranks every source function by Ochiai spectrum suspiciousness + stack-frame proximity +
   `IncrementalSemanticGraph` dependency edges.

2. **Checkpointed Beam-Search Repair Loop (`solve_repository_closed_loop`)**:
   Iterates `Locate -> Hypothesize -> Patch -> Test -> Observe -> Backtrack/Advance` inside
   an isolated worktree (`NEVER-MUTATE-SOURCE` invariant):
     - Composes `VerifiedSkillStore` recall, live runtime observational synthesis,
       cross-module signature/keyword choreography, deductive AST boundary/operator/guard
       repairs, and `RLock` synchronization synthesis.
     - Enforces monotonic progress, zero test deletion, and a mandatory **Sabotage Control**
       check (breaking the repaired function in a scratch copy MUST fail the test suite)
       before declaring `PASS`.

3. **Execution-Backed Concurrency Schedule Prober (`probe_concurrency_races_live`)**:
   Pairs AST shared-mutable state detection with a child-process `sys.setswitchinterval(1e-6)`
   + `threading.Barrier` thread-interleaving stress oracle against a sequential baseline.
"""
from __future__ import annotations

import ast
import copy
import difflib
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
from typing import Any, Mapping, Sequence

from canonical.swe_kernel import incremental_semantic_graph_v1 as sem_graph
from canonical.swe_kernel import verified_skill_crystallizer_v1 as crystallizer
from canonical.swe_kernel import whitebox_introspector_and_trace_synthesizer_v1 as wb_synth

SCHEMA = "PROJECT_BRAIN_MULTISTEP_REPO_CLOSED_LOOP_SOLVER_V1"

_SKIP_DIRS = frozenset({
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", "node_modules", "build", "dist",
})


def _is_test_relpath(rel_posix: str) -> bool:
    parts = pathlib.PurePosixPath(rel_posix).parts
    name = parts[-1] if parts else ""
    return (
        "tests" in parts
        or "test" in parts
        or "testing" in parts
        or name.startswith("test_")
        or name.endswith("_test.py")
    )


def _iter_repo_files(root: pathlib.Path) -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
        for fn in sorted(filenames):
            p = pathlib.Path(dirpath) / fn
            if p.is_file():
                out.append(p)
    return out


def _merkle_snapshot(root: pathlib.Path) -> dict[str, str]:
    snap: dict[str, str] = {}
    for p in _iter_repo_files(root):
        rel = p.relative_to(root).as_posix()
        snap[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return snap


def _copy_repo_to_worktree(src: pathlib.Path, dst: pathlib.Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for p in _iter_repo_files(src):
        rel = p.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)


# --------------------------------------------------------------------------- #
# 1. Isolated Child-Process Differential Execution Tracer (Ochiai SBFL)
# --------------------------------------------------------------------------- #

_DIFF_TRACE_CHILD_CODE = r"""
import ast
import importlib.util
import inspect
import json
import os
import pathlib
import sys
import traceback
import unittest

repo_root = pathlib.Path(sys.argv[1]).resolve()
explicit_rels = [x for x in sys.argv[2:] if x and not x.startswith("--")]
sys.path.insert(0, str(repo_root))
for sub in ("src", "pkg", "lib"):
    cand = repo_root / sub
    if cand.is_dir() and not (cand / "__init__.py").exists():
        sys.path.insert(0, str(cand))

SKIP_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", "node_modules", "build", "dist", "docs", "examples",
}

test_files = []
if explicit_rels:
    for r in explicit_rels:
        p = (repo_root / r).resolve()
        if p.is_file():
            test_files.append(p)
else:
    for dp, dns, fns in os.walk(repo_root):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
        for fn in sorted(fns):
            if fn.endswith(".py") and (fn.startswith("test_") or fn.endswith("_test.py")):
                test_files.append(pathlib.Path(dp) / fn)

_rel_cache = {}
def _rel_source(filename: str):
    if filename in _rel_cache:
        return _rel_cache[filename]
    if not filename or filename.startswith("<"):
        _rel_cache[filename] = None
        return None
    try:
        p = pathlib.Path(filename).resolve()
        if repo_root not in p.parents or not p.is_file():
            _rel_cache[filename] = None
            return None
        rel = p.relative_to(repo_root).as_posix()
        parts = rel.split("/")
        nm = parts[-1]
        if (
            "tests" in parts
            or "test" in parts
            or "testing" in parts
            or nm.startswith("test_")
            or nm.endswith("_test.py")
            or nm == "conftest.py"
        ):
            _rel_cache[filename] = None
            return None
        _rel_cache[filename] = rel
        return rel
    except Exception:
        _rel_cache[filename] = None
        return None

def _safe_repr(val):
    try:
        if isinstance(val, (int, float, bool, str, type(None))):
            r = repr(val)
            return r if len(r) <= 120 else r[:117] + "..."
        if isinstance(val, (list, tuple, dict, set)) and len(val) <= 12:
            r = repr(val)
            return r if len(r) <= 120 else r[:117] + "..."
        return f"<{type(val).__name__}>"
    except Exception:
        return "<unrepr>"

def _needs_pytest(tfiles):
    if importlib.util.find_spec("pytest") is None:
        return False
    for tf in tfiles:
        for parent in (tf.parent, *tf.parent.parents):
            if (parent / "conftest.py").is_file() or (parent / "pytest.ini").is_file():
                return True
            if parent == repo_root:
                break
        if "testing" in tf.relative_to(repo_root).parts:
            return True
        try:
            txt = tf.read_text(encoding="utf-8", errors="replace")
            if "pytest" in txt:
                return True
            tree = ast.parse(txt)
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                    if node.args.args or node.decorator_list:
                        return True
        except Exception:
            pass
    return False

passed_tests = []
failed_tests = []
spectra = {}       # key "file::func@firstlineno" -> [ef, ep]
line_spectra = {}  # key "file::func@firstlineno::line" -> [ef, ep]
call_samples = {}  # key "file::func@firstlineno" -> list
runner_kind = "unittest"

def _make_tracer(touched_funcs, touched_lines, local_calls):
    def _tracer(frame, event, arg):
        rel = _rel_source(frame.f_code.co_filename)
        if rel is None:
            return None
        fn = frame.f_code.co_name
        if fn.startswith("<"):
            return None
        fkey = f"{rel}::{fn}@{frame.f_code.co_firstlineno}"
        touched_funcs.add(fkey)
        if event == "line":
            touched_lines.add(f"{fkey}::{frame.f_lineno}")
        elif event == "call" and len(local_calls) < 32:
            arg_info = inspect.getargvalues(frame)
            bound = {}
            for a in arg_info.args[:6]:
                if a in arg_info.locals and a not in ("self", "cls"):
                    bound[a] = _safe_repr(arg_info.locals[a])
            local_calls.append({"fkey": fkey, "args": bound, "ret": None, "exc": None})
        elif event == "return" and local_calls:
            for item in reversed(local_calls):
                if item["fkey"] == fkey and item["ret"] is None and item["exc"] is None:
                    item["ret"] = _safe_repr(arg)
                    break
        elif event == "exception" and local_calls:
            exc_type = arg[0].__name__ if arg and arg[0] else "Exception"
            exc_msg = str(arg[1])[:160] if arg and len(arg) > 1 else ""
            for item in reversed(local_calls):
                if item["fkey"] == fkey and item["exc"] is None:
                    item["exc"] = f"{exc_type}: {exc_msg}"
                    break
        return _tracer
    return _tracer

if test_files and _needs_pytest(test_files):
    import pytest
    runner_kind = "pytest"
    class _BrainTracePlugin:
        def __init__(self):
            self._cur = None
        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_call(self, item):
            tf = set()
            tl = set()
            lc = []
            self._cur = (tf, tl, lc)
            sys.settrace(_make_tracer(tf, tl, lc))
            try:
                yield
            finally:
                sys.settrace(None)
        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_makereport(self, item, call):
            outcome = yield
            rep = outcome.get_result()
            if rep.when == "setup" and rep.failed:
                failed_tests.append({
                    "test_id": rep.nodeid,
                    "test_file": rep.nodeid.split("::", 1)[0],
                    "error_type": "SetupError",
                    "message": str(rep.longrepr)[:300],
                    "stack_frames": [],
                })
            elif rep.when == "call":
                cur = self._cur or (set(), set(), [])
                self._cur = None
                tf, tl, lc = cur
                ok = bool(rep.passed or rep.skipped)
                if rep.passed:
                    passed_tests.append(rep.nodeid)
                elif rep.failed:
                    tb_frames = []
                    err_type = "AssertionError"
                    err_msg = ""
                    if call.excinfo is not None:
                        err_type = call.excinfo.typename
                        err_msg = str(call.excinfo.value)[:300]
                        tb = call.excinfo.tb
                        while tb is not None:
                            rs = _rel_source(tb.tb_frame.f_code.co_filename)
                            if rs:
                                tb_frames.append([
                                    rs,
                                    f"{tb.tb_frame.f_code.co_name}@{tb.tb_frame.f_code.co_firstlineno}",
                                    int(tb.tb_lineno),
                                ])
                            tb = tb.tb_next
                    failed_tests.append({
                        "test_id": rep.nodeid,
                        "test_file": rep.nodeid.split("::", 1)[0],
                        "error_type": err_type,
                        "message": err_msg,
                        "stack_frames": tb_frames,
                    })
                if rep.passed or rep.failed:
                    idx_slot = 1 if ok else 0
                    for fk in tf:
                        row = spectra.setdefault(fk, [0, 0])
                        row[idx_slot] += 1
                    for lk in tl:
                        lrow = line_spectra.setdefault(lk, [0, 0])
                        lrow[idx_slot] += 1
                    for rec in lc:
                        bucket = call_samples.setdefault(rec["fkey"], [])
                        if len(bucket) < 12:
                            bucket.append({
                                "args": rec["args"],
                                "ret": rec["ret"],
                                "exc": rec["exc"],
                                "test_ok": ok,
                                "test_id": rep.nodeid,
                            })
        def pytest_collectreport(self, report):
            if report.failed:
                failed_tests.append({
                    "test_id": f"{report.nodeid}::<import>",
                    "test_file": str(report.nodeid),
                    "error_type": "CollectError",
                    "message": str(report.longrepr)[:300],
                    "stack_frames": [],
                })

    plugin = _BrainTracePlugin()
    pytest.main(
        ["-q", "-p", "no:cacheprovider", "--tb=no", *(str(tf) for tf in test_files)],
        plugins=[plugin],
    )
else:
    discovered = []
    import_errors = []
    for idx, tf in enumerate(test_files):
        rel_tf = tf.relative_to(repo_root).as_posix()
        mod_name = f"_brain_tmod_{idx}_{tf.stem}"
        try:
            spec = importlib.util.spec_from_file_location(mod_name, tf)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)
        except Exception as exc:
            tb_frames = []
            tb = exc.__traceback__
            while tb is not None:
                rs = _rel_source(tb.tb_frame.f_code.co_filename)
                if rs:
                    tb_frames.append([
                        rs,
                        f"{tb.tb_frame.f_code.co_name}@{tb.tb_frame.f_code.co_firstlineno}",
                        int(tb.tb_lineno),
                    ])
                tb = tb.tb_next
            import_errors.append({
                "test_id": f"{rel_tf}::<import>",
                "test_file": rel_tf,
                "error_type": type(exc).__name__,
                "message": str(exc)[:300],
                "stack_frames": tb_frames,
            })
            continue

        for attr_name, obj in sorted(vars(mod).items()):
            if isinstance(obj, type) and issubclass(obj, unittest.TestCase) and obj is not unittest.TestCase:
                for mname in unittest.defaultTestLoader.getTestCaseNames(obj):
                    discovered.append((f"{rel_tf}::{obj.__name__}.{mname}", rel_tf, ("unittest", obj, mname)))
            elif attr_name.startswith("test_") and callable(obj) and not isinstance(obj, type):
                sig = inspect.signature(obj)
                req_params = [
                    p for p in sig.parameters.values()
                    if p.default is inspect.Parameter.empty
                    and p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
                ]
                if not req_params:
                    discovered.append((f"{rel_tf}::{attr_name}", rel_tf, ("func", obj, None)))

    failed_tests.extend(import_errors)
    for test_id, rel_tf, runner_spec in discovered:
        touched_funcs = set()
        touched_lines = set()
        local_calls = []
        ok = True
        err_type = ""
        err_msg = ""
        tb_frames = []

        sys.settrace(_make_tracer(touched_funcs, touched_lines, local_calls))
        try:
            if runner_spec[0] == "unittest":
                cls_obj, mname = runner_spec[1], runner_spec[2]
                res = unittest.TestResult()
                cls_obj(mname).run(res)
                if res.failures or res.errors:
                    ok = False
                    _, tb_txt = (res.errors or res.failures)[0]
                    lines = [ln.strip() for ln in tb_txt.strip().splitlines() if ln.strip()]
                    last = lines[-1] if lines else "AssertionError"
                    if ":" in last:
                        err_type, err_msg = last.split(":", 1)
                        err_msg = err_msg.strip()[:300]
                    else:
                        err_type, err_msg = last[:80], ""
                    for m_file, m_line, m_fn in __import__("re").findall(
                        r'File "([^"]+)", line (\d+), in ([A-Za-z0-9_<>]+)', tb_txt
                    ):
                        rs = _rel_source(m_file)
                        if rs:
                            tb_frames.append([rs, m_fn, int(m_line)])
            else:
                fn_obj = runner_spec[1]
                fn_obj()
        except BaseException as exc:
            ok = False
            err_type = type(exc).__name__
            err_msg = str(exc)[:300]
            tb = exc.__traceback__
            while tb is not None:
                rs = _rel_source(tb.tb_frame.f_code.co_filename)
                if rs:
                    tb_frames.append([
                        rs,
                        f"{tb.tb_frame.f_code.co_name}@{tb.tb_frame.f_code.co_firstlineno}",
                        int(tb.tb_lineno),
                    ])
                tb = tb.tb_next
        finally:
            sys.settrace(None)

        if ok:
            passed_tests.append(test_id)
        else:
            failed_tests.append({
                "test_id": test_id,
                "test_file": rel_tf,
                "error_type": err_type.strip(),
                "message": err_msg,
                "stack_frames": tb_frames,
            })

        idx_slot = 1 if ok else 0
        for fk in touched_funcs:
            row = spectra.setdefault(fk, [0, 0])
            row[idx_slot] += 1
        for lk in touched_lines:
            lrow = line_spectra.setdefault(lk, [0, 0])
            lrow[idx_slot] += 1
        for rec in local_calls:
            bucket = call_samples.setdefault(rec["fkey"], [])
            if len(bucket) < 16:
                bucket.append({
                    "args": rec["args"],
                    "ret": rec["ret"],
                    "exc": rec["exc"],
                    "test_ok": ok,
                    "test_id": test_id,
                })

sys.stdout.write("\n" + json.dumps({
    "runner": runner_kind,
    "passed_tests": passed_tests,
    "failed_tests": failed_tests,
    "test_files": [tf.relative_to(repo_root).as_posix() for tf in test_files],
    "spectra": spectra,
    "line_spectra": line_spectra,
    "call_samples": call_samples,
}) + "\n")
"""


def localize_faults_by_differential_trace(
    repo_root: str | pathlib.Path,
    *,
    test_files: Sequence[str] | None = None,
    hinted_files: Sequence[str] | None = None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Run repository tests under isolated `sys.settrace` and rank suspects via Ochiai SBFL."""
    root = pathlib.Path(repo_root).resolve()
    if not root.is_dir():
        return {"ok": False, "reason": "REPO_ROOT_NOT_FOUND"}

    hinted_set = {str(h).strip().lstrip("./") for h in (hinted_files or ()) if str(h).strip()}
    explicit_args = [str(tf).strip() for tf in (test_files or ()) if str(tf).strip()]

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, "-B", "-c", _DIFF_TRACE_CHILD_CODE, str(root), *explicit_args],
            cwd=str(root),
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "TEST_TRACE_TIMEOUT"}

    raw_out = proc.stdout.strip()
    if not raw_out:
        return {
            "ok": False,
            "reason": "TEST_TRACE_EMPTY_OUTPUT",
            "stderr": (proc.stderr or "")[:400],
        }
    data = None
    for ln in reversed(raw_out.splitlines()):
        ln = ln.strip()
        if ln.startswith("{") and ln.endswith("}"):
            try:
                data = json.loads(ln)
                break
            except json.JSONDecodeError:
                continue
    if data is None:
        return {"ok": False, "reason": "TEST_TRACE_INVALID_JSON", "stdout": raw_out[-300:]}

    runner_kind = str(data.get("runner") or "unittest")
    passed_tests: list[str] = list(data.get("passed_tests") or [])
    failed_tests: list[dict[str, Any]] = list(data.get("failed_tests") or [])
    spectra: dict[str, list[int]] = dict(data.get("spectra") or {})
    line_spectra: dict[str, list[int]] = dict(data.get("line_spectra") or {})
    call_samples: dict[str, list[dict[str, Any]]] = dict(data.get("call_samples") or {})
    total_failed = len(failed_tests)
    total_passed = len(passed_tests)

    def _split_fkey(fk: str) -> tuple[str, str, int]:
        rel_f, _, rest = fk.partition("::")
        if "@" in rest:
            fn_nm, _, fl_s = rest.rpartition("@")
            try:
                return rel_f, fn_nm, int(fl_s)
            except ValueError:
                return rel_f, fn_nm, 0
        return rel_f, rest, 0

    # Stack-frame boosts: innermost source frame gets +0.40, outer frames +0.22
    stack_bonus: dict[str, float] = {}
    for ft in failed_tests:
        frames = ft.get("stack_frames") or []
        for idx, fr in enumerate(frames):
            if isinstance(fr, list) and len(fr) >= 2:
                fkey = f"{fr[0]}::{fr[1]}"
                bonus = 0.40 if idx == len(frames) - 1 else 0.22
                stack_bonus[fkey] = max(stack_bonus.get(fkey, 0.0), bonus)

    # Also inspect static call/import dependencies when stack_frames or spectra point to a caller:
    # any source function called inside an executed suspect also gets a small structural prior
    callee_bonus: dict[str, float] = {}
    try:
        py_files = [
            p for p in _iter_repo_files(root)
            if p.suffix == ".py" and not _is_test_relpath(p.relative_to(root).as_posix())
        ]
        func_defs: dict[str, list[str]] = {}
        file_asts: dict[str, ast.Module] = {}
        for pf in py_files:
            rel = pf.relative_to(root).as_posix()
            try:
                tree = ast.parse(pf.read_text(encoding="utf-8"))
                file_asts[rel] = tree
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        func_defs.setdefault(node.name, []).append(f"{rel}::{node.name}@{node.lineno}")
            except SyntaxError:
                pass
        for fk, counts in spectra.items():
            if counts[0] > 0:
                rel_f, fn_nm, fl_no = _split_fkey(fk)
                tree = file_asts.get(rel_f)
                if tree is not None:
                    for node in ast.walk(tree):
                        if (
                            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and node.name == fn_nm
                            and (fl_no == 0 or node.lineno == fl_no)
                        ):
                            for sub in ast.walk(node):
                                if isinstance(sub, ast.Call):
                                    cname = (
                                        sub.func.id if isinstance(sub.func, ast.Name)
                                        else (sub.func.attr if isinstance(sub.func, ast.Attribute) else "")
                                    )
                                    for target_fk in func_defs.get(cname, ()):
                                        if target_fk != fk:
                                            callee_bonus[target_fk] = max(callee_bonus.get(target_fk, 0.0), 0.12)
    except Exception:
        pass

    suspects: list[dict[str, Any]] = []
    all_keys = set(spectra.keys()) | set(stack_bonus.keys()) | set(callee_bonus.keys())
    for fk in all_keys:
        ef, ep = spectra.get(fk, [0, 0])
        if ef == 0 and fk not in stack_bonus:
            continue
        denom = math.sqrt(max(1, total_failed) * max(1, ef + ep))
        ochiai = (ef / denom) if ef > 0 else 0.0
        rel_f, fn_nm, fl_no = _split_fkey(fk)
        line_scores: dict[int, float] = {}
        prefix = f"{fk}::"
        for lk, (lef, lep) in line_spectra.items():
            if lk.startswith(prefix) and lef > 0:
                try:
                    lno = int(lk.rsplit("::", 1)[1])
                    ldenom = math.sqrt(max(1, total_failed) * max(1, lef + lep))
                    line_scores[lno] = round(lef / ldenom, 6)
                except ValueError:
                    pass
        max_line_ochiai = max(line_scores.values(), default=ochiai)
        hint_bonus = 0.35 if rel_f in hinted_set else 0.0
        score = round(
            0.5 * ochiai
            + 0.5 * max_line_ochiai
            + stack_bonus.get(fk, 0.0)
            + callee_bonus.get(fk, 0.0)
            + hint_bonus,
            6,
        )
        # Order hot_lines by descending statement Ochiai so most selective lines mutate first
        hot_lines = [ln for ln, _sc in sorted(line_scores.items(), key=lambda kv: (-kv[1], kv[0]))]
        suspects.append({
            "file": rel_f,
            "function": fn_nm,
            "firstlineno": fl_no,
            "ochiai": round(ochiai, 6),
            "max_line_ochiai": round(max_line_ochiai, 6),
            "score": score,
            "failed_hits": ef,
            "passed_hits": ep,
            "hot_lines": hot_lines,
            "line_scores": line_scores,
            "sample_calls": call_samples.get(fk, [])[:8],
        })

    # If a syntax error or import error prevented function execution, include non-test .py files
    if not suspects and failed_tests:
        for pf in _iter_repo_files(root):
            rel = pf.relative_to(root).as_posix()
            if pf.suffix == ".py" and not _is_test_relpath(rel):
                try:
                    tree = ast.parse(pf.read_text(encoding="utf-8"))
                    for node in tree.body:
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            suspects.append({
                                "file": rel,
                                "function": node.name,
                                "firstlineno": node.lineno,
                                "ochiai": 0.1,
                                "max_line_ochiai": 0.1,
                                "score": 0.1 + (0.35 if rel in hinted_set else 0.0),
                                "failed_hits": 0,
                                "passed_hits": 0,
                                "hot_lines": [],
                                "line_scores": {},
                                "sample_calls": [],
                            })
                except SyntaxError:
                    pass

    suspects.sort(key=lambda s: (-s["score"], -s.get("max_line_ochiai", 0.0), -s["ochiai"], s["file"], s["function"]))
    return {
        "ok": True,
        "runner": runner_kind,
        "passed_count": total_passed,
        "failed_count": total_failed,
        "total_tests": total_passed + total_failed,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "test_files": list(data.get("test_files") or []),
        "suspects": suspects,
    }


# --------------------------------------------------------------------------- #
# 2. Multi-Mechanism Deterministic Candidate Patch Synthesis
# --------------------------------------------------------------------------- #

def _extract_function_source(src: str, fn_name: str, *, firstlineno: int = 0) -> str | None:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    lines = src.splitlines(keepends=True)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name:
            if firstlineno > 0 and node.lineno != firstlineno:
                continue
            start = (node.decorator_list[0].lineno if node.decorator_list else node.lineno) - 1
            end = node.end_lineno or node.lineno
            return "".join(lines[start:end])
    return None


def _splice_ast_span_bytes(src_bytes: bytes, node: ast.AST, replacement_str: str) -> str | None:
    """Replace exact UTF-8 AST span `(lineno, col_offset .. end_lineno, end_col_offset)` with minimal diff."""
    lineno = getattr(node, "lineno", None)
    col = getattr(node, "col_offset", None)
    end_lineno = getattr(node, "end_lineno", None)
    end_col = getattr(node, "end_col_offset", None)
    if None in (lineno, col, end_lineno, end_col):
        return None
    lines = src_bytes.splitlines(keepends=True)
    if not (1 <= lineno <= end_lineno <= len(lines)):
        return None
    prefix = b"".join(lines[: lineno - 1]) + lines[lineno - 1][:col]
    suffix = lines[end_lineno - 1][end_col:] + b"".join(lines[end_lineno:])
    try:
        return (prefix + replacement_str.encode("utf-8") + suffix).decode("utf-8")
    except UnicodeDecodeError:
        return None


def _surgical_span_mutations(
    src: str,
    fn_name: str,
    hot_lines: Sequence[int],
    line_scores: Mapping[int, float] | None = None,
    *,
    firstlineno: int = 0,
) -> list[tuple[str, str]]:
    """Produce minimal 1-line span-preserving AST repairs ordered by statement-level Ochiai."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    src_bytes = src.encode("utf-8")
    scores = dict(line_scores or {})
    hot_set = set(hot_lines)
    scored_results: list[tuple[float, int, str, str]] = []
    seq = 0

    BINOP_TOK = [
        (ast.Sub, " + ", "sub_to_add"),
        (ast.Add, " - ", "add_to_sub"),
        (ast.Mult, " / ", "mul_to_div"),
        (ast.FloorDiv, " / ", "floordiv_to_div"),
        (ast.Div, " // ", "div_to_floordiv"),
        (ast.Mult, " + ", "mul_to_add"),
        (ast.Add, " * ", "add_to_mul"),
        (ast.BitXor, " ** ", "xor_to_pow"),
    ]
    CMP_TOK = [
        (ast.Lt, " <= ", "lt_to_lte"),
        (ast.LtE, " < ", "lte_to_lt"),
        (ast.Gt, " >= ", "gt_to_gte"),
        (ast.GtE, " > ", "gte_to_gt"),
        (ast.Eq, " != ", "eq_to_neq"),
        (ast.NotEq, " == ", "neq_to_eq"),
    ]

    for node in ast.walk(tree):
        if not (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name):
            continue
        if firstlineno > 0 and node.lineno != firstlineno:
            continue

        for sub in ast.walk(node):
            lineno = getattr(sub, "lineno", None)
            if hot_set and lineno is not None and not any(abs(lineno - hl) <= 2 for hl in hot_set):
                continue
            prio = max(
                (scores.get(lineno + d, 0.0) for d in (-1, 0, 1, 2) if lineno is not None),
                default=0.0,
            )

            # Boolean `and` <-> `or` preserving exact operand source text and BoolOp precedence parens
            if isinstance(sub, ast.BoolOp) and len(sub.values) >= 2:
                new_kw = " or " if isinstance(sub.op, ast.And) else " and "
                segs = [ast.get_source_segment(src, v) for v in sub.values]
                if all(segs):
                    formatted_segs = [
                        f"({s})" if isinstance(v, (ast.BoolOp, ast.IfExp, ast.Lambda)) else str(s)
                        for v, s in zip(sub.values, segs)
                    ]
                    repl = new_kw.join(formatted_segs)
                    cand = _splice_ast_span_bytes(src_bytes, sub, repl)
                    if cand and cand != src:
                        try:
                            ast.parse(cand)
                            seq += 1
                            scored_results.append((prio + 0.05, seq, "boolop_flip", cand))
                        except SyntaxError:
                            pass

            # Comparison boundary swap preserving exact operand source text
            if isinstance(sub, ast.Compare) and len(sub.ops) == 1 and len(sub.comparators) == 1:
                lseg = ast.get_source_segment(src, sub.left)
                rseg = ast.get_source_segment(src, sub.comparators[0])
                if lseg and rseg:
                    for from_cmp, op_str, tag in CMP_TOK:
                        if isinstance(sub.ops[0], from_cmp):
                            cand = _splice_ast_span_bytes(src_bytes, sub, f"{lseg}{op_str}{rseg}")
                            if cand and cand != src:
                                try:
                                    ast.parse(cand)
                                    seq += 1
                                    scored_results.append((prio, seq, tag, cand))
                                except SyntaxError:
                                    pass

            # Binary operator swap preserving exact operand source text
            if isinstance(sub, ast.BinOp):
                lseg = ast.get_source_segment(src, sub.left)
                rseg = ast.get_source_segment(src, sub.right)
                if lseg and rseg:
                    for from_op, op_str, tag in BINOP_TOK:
                        if isinstance(sub.op, from_op):
                            cand = _splice_ast_span_bytes(src_bytes, sub, f"({lseg}{op_str}{rseg})" if op_str.strip() in ("*", "/", "//", "**") else f"{lseg}{op_str}{rseg}")
                            if cand and cand != src:
                                try:
                                    ast.parse(cand)
                                    seq += 1
                                    scored_results.append((prio, seq, tag, cand))
                                except SyntaxError:
                                    pass
                    if isinstance(sub.op, (ast.Add, ast.Sub)) and isinstance(sub.right, ast.Constant) and sub.right.value == 1:
                        cand = _splice_ast_span_bytes(src_bytes, sub, lseg)
                        if cand and cand != src:
                            try:
                                ast.parse(cand)
                                seq += 1
                                scored_results.append((prio, seq, "drop_off_by_one", cand))
                            except SyntaxError:
                                pass

        break

    scored_results.sort(key=lambda r: (-r[0], r[1]))
    return [(tag, cand) for _p, _s, tag, cand in scored_results[:24]]


def _replace_ast_node_in_function(
    src: str,
    fn_name: str,
    mutator_fn: Any,
    *,
    firstlineno: int = 0,
) -> list[tuple[str, str]]:
    """Apply `mutator_fn(fn_node) -> list[(label, new_fn_node)]` and splice cleanly into `src`."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    lines = src.splitlines(keepends=True)
    results: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name:
            if firstlineno > 0 and node.lineno != firstlineno:
                continue
            # Only splice top-level or class-method functions cleanly with indentation preserved
            fn_start = node.lineno - 1
            fn_end = node.end_lineno or node.lineno
            orig_header = lines[fn_start]
            indent = orig_header[: len(orig_header) - len(orig_header.lstrip())]
            variants = mutator_fn(node)
            for label, new_fn in variants:
                ast.fix_missing_locations(new_fn)
                try:
                    unparsed = ast.unparse(new_fn)
                except Exception:
                    continue
                indented = "\n".join(
                    (indent + ln if ln.strip() else ln) for ln in unparsed.splitlines()
                ) + "\n"
                # Keep decorators if node had any; ast.unparse(new_fn) already includes decorators!
                dec_start = (node.decorator_list[0].lineno - 1) if node.decorator_list else fn_start
                new_src = "".join(lines[:dec_start]) + indented + "".join(lines[fn_end:])
                if new_src != src:
                    try:
                        ast.parse(new_src)
                        results.append((label, new_src))
                    except SyntaxError:
                        pass
            break
    return results


def _deductive_ast_mutations(fn_node: ast.FunctionDef | ast.AsyncFunctionDef, hot_lines: Sequence[int]) -> list[tuple[str, ast.AST]]:
    """Generate targeted AST repairs on executed hot lines inside `fn_node`."""
    hot_set = set(hot_lines)
    variants: list[tuple[str, ast.AST]] = []

    BINOP_SWAPS: list[tuple[type[ast.operator], type[ast.operator], str]] = [
        (ast.Sub, ast.Add, "sub_to_add"),
        (ast.Add, ast.Sub, "add_to_sub"),
        (ast.Mult, ast.Div, "mul_to_div"),
        (ast.FloorDiv, ast.Div, "floordiv_to_div"),
        (ast.Div, ast.FloorDiv, "div_to_floordiv"),
        (ast.Mult, ast.Add, "mul_to_add"),
        (ast.Add, ast.Mult, "add_to_mul"),
        (ast.BitXor, ast.Pow, "xor_to_pow"),
    ]
    CMP_SWAPS: list[tuple[type[ast.cmpop], type[ast.cmpop], str]] = [
        (ast.Lt, ast.LtE, "lt_to_lte"),
        (ast.LtE, ast.Lt, "lte_to_lt"),
        (ast.Gt, ast.GtE, "gt_to_gte"),
        (ast.GtE, ast.Gt, "gte_to_gt"),
        (ast.Eq, ast.NotEq, "eq_to_neq"),
        (ast.NotEq, ast.Eq, "neq_to_eq"),
    ]
    AUG_SWAPS: list[tuple[type[ast.operator], type[ast.operator], str]] = [
        (ast.Sub, ast.Add, "aug_sub_to_add"),
        (ast.Add, ast.Sub, "aug_add_to_sub"),
        (ast.Mult, ast.Add, "aug_mul_to_add"),
    ]

    # Collect paths (index sequence by ast.walk order) of mutable expressions
    all_nodes = list(ast.walk(fn_node))
    for idx, sub in enumerate(all_nodes):
        lineno = getattr(sub, "lineno", None)
        if hot_set and lineno is not None and lineno not in hot_set:
            continue

        # 1. Binary operator repairs + off-by-one constant adjustments
        if isinstance(sub, ast.BinOp):
            for from_op, to_op, tag in BINOP_SWAPS:
                if isinstance(sub.op, from_op):
                    cloned = copy.deepcopy(fn_node)
                    target_node = list(ast.walk(cloned))[idx]
                    if isinstance(target_node, ast.BinOp):
                        target_node.op = to_op()
                        variants.append((tag, cloned))
            # Off-by-one: `expr - 1` -> `expr` or `expr + 1` -> `expr`
            if isinstance(sub.op, (ast.Add, ast.Sub)) and isinstance(sub.right, ast.Constant) and sub.right.value == 1:
                cloned = copy.deepcopy(fn_node)
                # Replace BinOp with its left operand via parent transformer
                class _DropPlusMinusOne(ast.NodeTransformer):
                    def __init__(self, target_idx: int) -> None:
                        self.seen = -1
                        self.target_idx = target_idx
                    def visit(self, n: ast.AST) -> ast.AST:
                        self.seen += 1
                        if self.seen == self.target_idx and isinstance(n, ast.BinOp):
                            return n.left
                        return self.generic_visit(n)
                variants.append(("drop_off_by_one", _DropPlusMinusOne(idx).visit(cloned)))

        # 2. Augmented assignment (`total -= x` <-> `total += x`)
        if isinstance(sub, ast.AugAssign):
            for from_op, to_op, tag in AUG_SWAPS:
                if isinstance(sub.op, from_op):
                    cloned = copy.deepcopy(fn_node)
                    target_node = list(ast.walk(cloned))[idx]
                    if isinstance(target_node, ast.AugAssign):
                        target_node.op = to_op()
                        variants.append((tag, cloned))

        # 3. Comparison operator boundary repairs
        if isinstance(sub, ast.Compare) and len(sub.ops) == 1:
            for from_cmp, to_cmp, tag in CMP_SWAPS:
                if isinstance(sub.ops[0], from_cmp):
                    cloned = copy.deepcopy(fn_node)
                    target_node = list(ast.walk(cloned))[idx]
                    if isinstance(target_node, ast.Compare):
                        target_node.ops[0] = to_cmp()
                        variants.append((tag, cloned))

        # 4. Boolean `and` <-> `or`
        if isinstance(sub, ast.BoolOp):
            cloned = copy.deepcopy(fn_node)
            target_node = list(ast.walk(cloned))[idx]
            if isinstance(target_node, ast.BoolOp):
                target_node.op = ast.Or() if isinstance(sub.op, ast.And) else ast.And()
                variants.append(("boolop_flip", cloned))

        # 5. `range(len(xs) - 1)` -> `range(len(xs))` or `range(1, n)` -> `range(0, n + 1)`
        if (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Name)
            and sub.func.id == "range"
            and len(sub.args) in (1, 2)
        ):
            if len(sub.args) == 1 and isinstance(sub.args[0], ast.BinOp) and isinstance(sub.args[0].op, ast.Sub):
                if isinstance(sub.args[0].right, ast.Constant) and sub.args[0].right.value == 1:
                    cloned = copy.deepcopy(fn_node)
                    target_node = list(ast.walk(cloned))[idx]
                    if isinstance(target_node, ast.Call):
                        target_node.args[0] = target_node.args[0].left  # type: ignore[attr-defined]
                        variants.append(("range_upper_bound_fix", cloned))
            elif len(sub.args) == 2 and isinstance(sub.args[1], ast.Name):
                cloned = copy.deepcopy(fn_node)
                target_node = list(ast.walk(cloned))[idx]
                if isinstance(target_node, ast.Call):
                    target_node.args[1] = ast.BinOp(
                        left=target_node.args[1], op=ast.Add(), right=ast.Constant(value=1)
                    )
                    variants.append(("range_inclusive_upper_fix", cloned))

        # 6. Small integer constant repairs (`0` <-> `1`, `100` <-> `100.0`, percentage `/ 100` vs `* 100`)
        if isinstance(sub, ast.Constant) and type(sub.value) is int and sub.value in (0, 1, -1):
            for repl in (0, 1):
                if repl != sub.value:
                    cloned = copy.deepcopy(fn_node)
                    target_node = list(ast.walk(cloned))[idx]
                    if isinstance(target_node, ast.Constant):
                        target_node.value = repl
                        variants.append((f"const_{sub.value}_to_{repl}", cloned))

        if len(variants) >= 28:
            break

    return variants[:28]


def _cross_module_keyword_alignment_candidates(
    worktree: pathlib.Path,
    failed_tests: Sequence[Mapping[str, Any]],
) -> list[tuple[str, str, str, str]]:
    """Repair cross-module `TypeError: fn() got an unexpected keyword argument 'x'` mismatches."""
    out: list[tuple[str, str, str, str]] = []
    kw_err_re = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\(\)\s+got an unexpected keyword argument '([A-Za-z_][A-Za-z0-9_]*)'")
    for ft in failed_tests:
        if ft.get("error_type") != "TypeError":
            continue
        m = kw_err_re.search(str(ft.get("message") or ""))
        if not m:
            continue
        callee_name, bad_kw = m.group(1), m.group(2)
        # Find definition of `callee_name` in non-test source files to inspect its actual parameter names
        callee_params: list[str] = []
        for pf in _iter_repo_files(worktree):
            rel = pf.relative_to(worktree).as_posix()
            if pf.suffix != ".py" or _is_test_relpath(rel):
                continue
            try:
                tree = ast.parse(pf.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == callee_name:
                    callee_params = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]
                    break
        if not callee_params:
            continue
        # Inspect caller source frame where TypeError occurred and align keyword argument
        for fr in ft.get("stack_frames") or []:
            if not (isinstance(fr, list) and len(fr) >= 2):
                continue
            caller_rel, caller_fn = str(fr[0]), str(fr[1])
            caller_path = worktree / caller_rel
            if not caller_path.is_file() or _is_test_relpath(caller_rel):
                continue
            src = caller_path.read_text(encoding="utf-8")
            try:
                ctree = ast.parse(src)
            except SyntaxError:
                continue
            for cand_param in callee_params:
                class _KwRewriter(ast.NodeTransformer):
                    def __init__(self, target_callee: str, old_k: str, new_k: str) -> None:
                        self.target_callee = target_callee
                        self.old_k = old_k
                        self.new_k = new_k
                        self.changed = False
                    def visit_Call(self, node: ast.Call) -> ast.AST:
                        self.generic_visit(node)
                        cname = (
                            node.func.id if isinstance(node.func, ast.Name)
                            else (node.func.attr if isinstance(node.func, ast.Attribute) else "")
                        )
                        if cname == self.target_callee:
                            used = {kw.arg for kw in node.keywords if kw.arg}
                            if self.new_k not in used:
                                for kw in node.keywords:
                                    if kw.arg == self.old_k:
                                        kw.arg = self.new_k
                                        self.changed = True
                        return node

                rewriter = _KwRewriter(callee_name, bad_kw, cand_param)
                new_tree = rewriter.visit(copy.deepcopy(ctree))
                if rewriter.changed:
                    ast.fix_missing_locations(new_tree)
                    new_src = ast.unparse(new_tree) + "\n"
                    out.append((caller_rel, caller_fn, f"align_kw_{bad_kw}_to_{cand_param}", new_src))
    return out


def _concurrency_rlock_candidates(src: str, fn_name: str) -> list[tuple[str, str]]:
    """Synthesize module-level RLock synchronization around unlocked shared-state mutations."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    has_shared_mutation = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name:
            has_with = any(isinstance(sub, ast.With) for sub in ast.walk(node))
            if has_with:
                return []
            for sub in ast.walk(node):
                if isinstance(sub, (ast.Global, ast.AugAssign, ast.Subscript, ast.Attribute)):
                    has_shared_mutation = True
                    break
    if not has_shared_mutation:
        return []

    lock_name = "_BRAIN_SYNC_RLOCK"
    new_tree = copy.deepcopy(tree)
    wrapped = False
    # Wrap ALL functions in the module that mutate shared state under the same RLock
    for node in new_tree.body:
        if isinstance(node, ast.FunctionDef):
            if node.name == fn_name or any(isinstance(s, ast.Global) for s in ast.walk(node)):
                globals_stmts = [s for s in node.body if isinstance(s, ast.Global)]
                rest_stmts = [s for s in node.body if not isinstance(s, ast.Global)]
                if rest_stmts:
                    with_stmt = ast.With(
                        items=[ast.withitem(context_expr=ast.Name(id=lock_name, ctx=ast.Load()))],
                        body=rest_stmts,
                    )
                    node.body = globals_stmts + [with_stmt]
                    wrapped = True
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name != "__init__":
                    with_stmt = ast.With(
                        items=[ast.withitem(context_expr=ast.Name(id=lock_name, ctx=ast.Load()))],
                        body=list(item.body),
                    )
                    item.body = [with_stmt]
                    wrapped = True

    if not wrapped:
        return []

    # Insert `import threading` and `_BRAIN_SYNC_RLOCK = threading.RLock()` right after future imports
    insert_at = 0
    for idx, stmt in enumerate(new_tree.body):
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
            insert_at = idx + 1
        elif isinstance(stmt, ast.ImportFrom) and stmt.module == "__future__":
            insert_at = idx + 1
        else:
            break
    lock_preamble = ast.parse(f"import threading\n{lock_name} = threading.RLock()\n").body
    new_tree.body[insert_at:insert_at] = lock_preamble
    ast.fix_missing_locations(new_tree)
    try:
        return [("synchronize_with_rlock", ast.unparse(new_tree) + "\n")]
    except Exception:
        return []


def _generate_candidates_for_state(
    worktree: pathlib.Path,
    diag: Mapping[str, Any],
    skill_store: crystallizer.VerifiedSkillStore,
    *,
    max_suspects: int = 8,
) -> list[tuple[str, str, int, str, str]]:
    """Return round-robin interleaved `(rel_file, fn_name, firstlineno, mechanism, candidate_source)`."""
    candidates: list[tuple[str, str, int, str, str]] = []
    seen_hashes: set[tuple[str, str]] = set()

    def _add_to(
        bucket: list[tuple[str, str, int, str, str]],
        rel_f: str,
        fn_nm: str,
        fl_no: int,
        mech: str,
        code: str,
    ) -> None:
        h = hashlib.sha256(code.encode("utf-8")).hexdigest()
        if (rel_f, h) not in seen_hashes:
            seen_hashes.add((rel_f, h))
            bucket.append((rel_f, fn_nm, fl_no, mech, code))

    failed_tests = list(diag.get("failed_tests") or [])
    test_files = [worktree / tf for tf in (diag.get("test_files") or []) if (worktree / tf).is_file()]
    is_pytest_suite = str(diag.get("runner") or "") == "pytest"

    # 1. Cross-module TypeError keyword alignment (always highest priority)
    for rel_f, fn_nm, mech, code in _cross_module_keyword_alignment_candidates(worktree, failed_tests):
        _add_to(candidates, rel_f, fn_nm, 0, mech, code)

    suspects = list(diag.get("suspects") or [])[:max_suspects]
    # Load python crystallized rules once
    stored_rules: list[dict[str, Any]] = []
    try:
        conn = crystallizer._connect(skill_store.db_path)
        try:
            rows = conn.execute(
                "SELECT pattern_json FROM crystallized_skills WHERE language = 'python' ORDER BY verified_hits DESC LIMIT 32"
            ).fetchall()
            stored_rules = [json.loads(r[0]) for r in rows if r and r[0]]
        finally:
            conn.close()
    except Exception:
        stored_rules = []

    suspect_buckets: list[list[tuple[str, str, int, str, str]]] = []
    for susp in suspects:
        rel_f = str(susp.get("file") or "")
        fn_nm = str(susp.get("function") or "")
        fl_no = int(susp.get("firstlineno") or 0)
        fpath = worktree / rel_f
        if not rel_f or not fpath.is_file() or _is_test_relpath(rel_f):
            continue
        orig_src = fpath.read_text(encoding="utf-8")
        bucket: list[tuple[str, str, int, str, str]] = []

        # Mechanism A: Crystallized code rules (only on small standalone modules)
        if len(orig_src) <= 6_000:
            for rule in stored_rules:
                patched = crystallizer.apply_crystallized_code_rule(orig_src, rule)
                if patched and patched != orig_src:
                    try:
                        ast.parse(patched)
                        _add_to(bucket, rel_f, fn_nm, fl_no, f"crystallized_skill:{rule.get('skill_id', '')[:12]}", patched)
                    except SyntaxError:
                        pass

        # Mechanism B: Live runtime assertion trace observational synthesis (for standalone non-pytest modules)
        if test_files and fn_nm and not is_pytest_suite and len(orig_src) <= 12_000:
            try:
                synth_list = wb_synth.synthesize_candidates_for_file(
                    fpath, test_files, target_fn=fn_nm, max_candidates=6
                )
                for sc in synth_list:
                    c_src = str(sc.get("patched_source") or "")
                    if c_src and c_src != orig_src:
                        _add_to(bucket, rel_f, fn_nm, fl_no, f"live_trace_synthesis:{sc.get('expr', '')[:32]}", c_src)
            except Exception:
                pass

        # Mechanism C1: Surgical 1-line UTF-8 span-preserving AST repairs ordered by statement Ochiai
        hot_lines = list(susp.get("hot_lines") or [])
        line_scores = susp.get("line_scores") or {}
        for tag, c_src in _surgical_span_mutations(
            orig_src, fn_nm, hot_lines, line_scores, firstlineno=fl_no
        ):
            _add_to(bucket, rel_f, fn_nm, fl_no, f"surgical_ast:{tag}", c_src)

        # Mechanism C2: Function-level deductive AST mutations (range/augassign/const) on small modules
        if len(orig_src) <= 6_000:
            for tag, c_src in _replace_ast_node_in_function(
                orig_src,
                fn_nm,
                lambda fn_node, hl=hot_lines: _deductive_ast_mutations(fn_node, hl),
                firstlineno=fl_no,
            ):
                _add_to(bucket, rel_f, fn_nm, fl_no, f"deductive_ast:{tag}", c_src)

        # Mechanism D: Concurrency RLock synthesis if threading appears in test or module
        if len(orig_src) <= 12_000 and (
            "thread" in orig_src.lower() or any(
                "thread" in (worktree / tf).read_text(encoding="utf-8", errors="replace").lower()
                for tf in (diag.get("test_files") or [])[:6]
                if (worktree / tf).is_file()
            )
        ):
            for tag, c_src in _concurrency_rlock_candidates(orig_src, fn_nm):
                _add_to(bucket, rel_f, fn_nm, fl_no, tag, c_src)

        if bucket:
            suspect_buckets.append(bucket)

    # Round-robin interleave (stride=2) across suspect buckets so top Ochiai lines of every top suspect run early
    stride = 2
    max_len = max((len(b) for b in suspect_buckets), default=0)
    for offset in range(0, max_len, stride):
        for b in suspect_buckets:
            candidates.extend(b[offset : offset + stride])

    return candidates


_QUICK_PYTEST_CODE = r"""
import os, pathlib, sys
repo_root = pathlib.Path(sys.argv[1]).resolve()
nodeids = sys.argv[2:]
sys.path.insert(0, str(repo_root))
for sub in ("src", "pkg", "lib"):
    cand = repo_root / sub
    if cand.is_dir() and not (cand / "__init__.py").exists():
        sys.path.insert(0, str(cand))
import pytest
class _Cnt:
    def __init__(self):
        self.failed = 0
        self.passed = 0
    def pytest_runtest_logreport(self, report):
        if report.when == "call":
            if report.failed:
                self.failed += 1
            elif report.passed:
                self.passed += 1
        elif report.when == "setup" and report.failed:
            self.failed += 1
c = _Cnt()
rc = int(pytest.main(["-q", "-p", "no:cacheprovider", "--tb=no", *nodeids], plugins=[c]))
sys.stdout.write(f"\nBRAIN_QUICK:{rc}:{c.failed}:{c.passed}\n")
"""


def _quick_pytest_failing_subset(
    worktree: pathlib.Path,
    failing_nodeids: Sequence[str],
    *,
    timeout: float = 6.0,
) -> tuple[bool, int]:
    """Fast untraced check of failing pytest nodeids; returns `(ran_ok, still_failing_count)`."""
    if not failing_nodeids:
        return False, 0
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, "-B", "-c", _QUICK_PYTEST_CODE, str(worktree), *failing_nodeids[:25]],
            cwd=str(worktree),
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, len(failing_nodeids)
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if "BRAIN_SABOTAGE_NEGATIVE_CONTROL" in combined:
        return True, max(1, len(failing_nodeids))
    for ln in reversed((proc.stdout or "").splitlines()):
        if ln.startswith("BRAIN_QUICK:"):
            parts = ln.split(":")
            if len(parts) == 4:
                try:
                    rc = int(parts[1])
                    failed = int(parts[2])
                    passed = int(parts[3])
                    if rc not in (0, 1) and failed == 0 and passed == 0:
                        return False, len(failing_nodeids)
                    return True, failed
                except ValueError:
                    pass
    return False, len(failing_nodeids)


def _sabotage_control_kills_suite(
    worktree: pathlib.Path,
    patched_rel_file: str,
    patched_fn_name: str,
    *,
    firstlineno: int = 0,
    test_files: Sequence[str] | None = None,
    failing_nodeids: Sequence[str] | None = None,
    timeout: float = 10.0,
) -> bool:
    """Verify the test suite is NON-TAUTOLOGICAL: breaking `patched_fn_name` MUST fail a test."""
    target = worktree / patched_rel_file
    if not target.is_file():
        return False
    good_bytes = target.read_bytes()
    good_src = good_bytes.decode("utf-8")
    try:
        sabotaged_variants = _replace_ast_node_in_function(
            good_src,
            patched_fn_name,
            lambda fn_node: [(
                "sabotage",
                ast.FunctionDef(
                    name=fn_node.name,
                    args=fn_node.args,
                    body=[ast.Raise(exc=ast.Call(
                        func=ast.Name(id="RuntimeError", ctx=ast.Load()),
                        args=[ast.Constant(value="BRAIN_SABOTAGE_NEGATIVE_CONTROL")],
                        keywords=[],
                    ))],
                    decorator_list=fn_node.decorator_list,
                    returns=fn_node.returns,
                ),
            )],
            firstlineno=firstlineno,
        )
        if not sabotaged_variants:
            return False
        target.write_text(sabotaged_variants[0][1], encoding="utf-8")
        if failing_nodeids:
            ran_ok, still_f = _quick_pytest_failing_subset(worktree, failing_nodeids, timeout=timeout)
            if ran_ok and still_f > 0:
                return True
        check = localize_faults_by_differential_trace(worktree, test_files=test_files, timeout=timeout)
        return bool(check.get("ok") and int(check.get("failed_count", 0)) > 0)
    finally:
        target.write_bytes(good_bytes)


def _assertion_residual(failed_tests: Sequence[Mapping[str, Any]]) -> float:
    """Compute continuous numeric/edit residual from `AssertionError: actual != expected` messages."""
    num_re = re.compile(r"(-?\d+(?:\.\d+)?)\s*!=\s*(-?\d+(?:\.\d+)?)")
    total = 0.0
    for ft in failed_tests:
        msg = str(ft.get("message") or "")
        m = num_re.search(msg)
        if m:
            try:
                a, b = float(m.group(1)), float(m.group(2))
                total += min(1e6, abs(a - b))
                continue
            except ValueError:
                pass
        total += 100.0
    return round(total, 6)

def solve_repository_closed_loop(
    repo_root: str | pathlib.Path,
    goal: str = "",
    *,
    test_files: Sequence[str] | None = None,
    apply_to_source: bool = False,
    max_steps: int = 5,
    beam_width: int = 5,
    timeout_s: float = 45.0,
    skill_db_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Iteratively localize, patch, verify, and backtrack across a repository until 100% tests pass."""
    t0 = time.perf_counter()
    src_root = pathlib.Path(repo_root).resolve()
    if not src_root.is_dir():
        return {
            "schema": SCHEMA,
            "ok": False,
            "verified": False,
            "status": "FAIL_CLOSED__REPOSITORY_NOT_FOUND",
            "reason": "REPOSITORY_NOT_FOUND",
        }

    source_merkle_before = _merkle_snapshot(src_root)
    skill_store = crystallizer.VerifiedSkillStore(db_path=skill_db_path)

    with tempfile.TemporaryDirectory(prefix="brain_closed_loop_repo_") as tmp_dir:
        wt = pathlib.Path(tmp_dir) / "worktree"
        _copy_repo_to_worktree(src_root, wt)

        # Extract any explicitly stated source file path from `goal` that exists under `wt`
        hinted_files: list[str] = []
        if goal:
            for tok in re.findall(r"[A-Za-z0-9_./-]+\.py\b", str(goal)):
                rel_tok = tok.lstrip("./")
                if (wt / rel_tok).is_file() and not _is_test_relpath(rel_tok):
                    hinted_files.append(rel_tok)

        initial_diag = localize_faults_by_differential_trace(
            wt,
            test_files=test_files,
            hinted_files=hinted_files,
            timeout=min(20.0, timeout_s),
        )
        if not initial_diag.get("ok"):
            return {
                "schema": SCHEMA,
                "ok": False,
                "verified": False,
                "status": "FAIL_CLOSED__" + str(initial_diag.get("reason") or "TRACE_FAILED"),
                "reason": str(initial_diag.get("reason") or "TRACE_FAILED"),
            }
        if initial_diag["total_tests"] == 0:
            return {
                "schema": SCHEMA,
                "ok": False,
                "verified": False,
                "status": "FAIL_CLOSED__NO_TESTS_DISCOVERED",
                "reason": "NO_TESTS_DISCOVERED",
            }
        if initial_diag["failed_count"] == 0:
            return {
                "schema": SCHEMA,
                "ok": True,
                "verified": True,
                "already_passing": True,
                "status": "PASS__SUITE_ALREADY_GREEN",
                "steps_taken": 0,
                "passed_count": initial_diag["passed_count"],
                "failed_count": 0,
                "changed_files": [],
                "diff": "",
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "model_dependency_count": 0,
                "incremental_spend_usd": 0,
            }

        initial_source_files: dict[str, bytes] = {
            p.relative_to(wt).as_posix(): p.read_bytes()
            for p in _iter_repo_files(wt)
            if not _is_test_relpath(p.relative_to(wt).as_posix())
        }

        # Beam element: (files_dict, steps_history, diag_dict)
        beam: list[tuple[dict[str, bytes], list[dict[str, Any]], dict[str, Any]]] = [
            (dict(initial_source_files), [], initial_diag)
        ]
        visited_state_fps: set[str] = {
            hashlib.sha256(
                json.dumps(
                    {k: hashlib.sha256(v).hexdigest() for k, v in sorted(initial_source_files.items())},
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
        }

        winning_state: tuple[dict[str, bytes], list[dict[str, Any]], dict[str, Any]] | None = None
        pruned_regressions = 0
        candidates_evaluated = 0
        use_fast_pytest_screen = (
            initial_diag.get("runner") == "pytest"
            and int(initial_diag["total_tests"]) >= 15
        )

        for step_idx in range(1, max_steps + 1):
            if (time.perf_counter() - t0) >= timeout_s:
                break
            next_beam: list[tuple[dict[str, bytes], list[dict[str, Any]], dict[str, Any]]] = []

            for state_files, history, state_diag in beam:
                if (time.perf_counter() - t0) >= timeout_s:
                    break
                # Materialize `state_files` into `wt`
                for rel_p, raw_b in state_files.items():
                    (wt / rel_p).write_bytes(raw_b)

                parent_passed_set = set(state_diag.get("passed_tests") or [])
                parent_failed_count = int(state_diag.get("failed_count") or 0)
                failing_nodeids = [
                    str(ft.get("test_id") or "")
                    for ft in (state_diag.get("failed_tests") or [])
                    if ft.get("test_id") and not str(ft.get("test_id")).endswith("::<import>")
                ]

                cand_list = _generate_candidates_for_state(wt, state_diag, skill_store)
                for rel_f, fn_nm, fl_no, mech, cand_code in cand_list:
                    if (time.perf_counter() - t0) >= timeout_s:
                        break
                    cand_bytes = cand_code.encode("utf-8")
                    next_files = dict(state_files)
                    next_files[rel_f] = cand_bytes
                    fp = hashlib.sha256(
                        json.dumps(
                            {k: hashlib.sha256(v).hexdigest() for k, v in sorted(next_files.items())},
                            sort_keys=True,
                        ).encode("utf-8")
                    ).hexdigest()
                    if fp in visited_state_fps:
                        continue
                    visited_state_fps.add(fp)

                    # Write candidate and evaluate
                    (wt / rel_f).write_bytes(cand_bytes)
                    candidates_evaluated += 1
                    if use_fast_pytest_screen and 0 < len(failing_nodeids) <= 25:
                        ran_q, still_f = _quick_pytest_failing_subset(wt, failing_nodeids, timeout=6.0)
                        if ran_q and still_f >= len(failing_nodeids):
                            (wt / rel_f).write_bytes(state_files[rel_f])
                            continue

                    cand_diag = localize_faults_by_differential_trace(
                        wt,
                        test_files=test_files,
                        hinted_files=hinted_files,
                        timeout=15.0,
                    )
                    # Restore parent file immediately
                    (wt / rel_f).write_bytes(state_files[rel_f])

                    if not cand_diag.get("ok"):
                        continue
                    # Never allow test count shrinkage or syntax/import collapse
                    if int(cand_diag["total_tests"]) < int(initial_diag["total_tests"]):
                        pruned_regressions += 1
                        continue
                    if any(ft.get("test_id", "").endswith("::<import>") for ft in (cand_diag.get("failed_tests") or [])):
                        pruned_regressions += 1
                        continue

                    cand_passed_set = set(cand_diag.get("passed_tests") or [])
                    cand_failed_count = int(cand_diag["failed_count"])
                    parent_res = _assertion_residual(state_diag.get("failed_tests") or [])
                    cand_res = _assertion_residual(cand_diag.get("failed_tests") or [])

                    # Accept state into beam if:
                    # (a) strictly fewer failures without breaking passing tests, OR
                    # (b) residual error drops / failure value shifts on an intermediate step (< max_steps)
                    #     enabling coupled multi-file bug repairs where two bugs cancel on one input!
                    no_regression = parent_passed_set.issubset(cand_passed_set)
                    made_progress = (cand_failed_count < parent_failed_count and no_regression)
                    if not made_progress and step_idx < max_steps:
                        old_sig = [(f.get("error_type"), f.get("message")) for f in (state_diag.get("failed_tests") or [])]
                        new_sig = [(f.get("error_type"), f.get("message")) for f in (cand_diag.get("failed_tests") or [])]
                        if cand_res < parent_res or (new_sig != old_sig and cand_failed_count <= parent_failed_count + 1):
                            made_progress = True

                    if not made_progress:
                        if not no_regression:
                            pruned_regressions += 1
                        continue

                    before_fn_snip = _extract_function_source(
                        state_files[rel_f].decode("utf-8", errors="replace"), fn_nm, firstlineno=fl_no
                    ) or ""
                    after_fn_snip = _extract_function_source(cand_code, fn_nm, firstlineno=fl_no) or ""
                    step_rec = {
                        "step": step_idx,
                        "file": rel_f,
                        "function": fn_nm,
                        "firstlineno": fl_no,
                        "mechanism": mech,
                        "failed_before": parent_failed_count,
                        "failed_after": cand_failed_count,
                        "passed_after": int(cand_diag["passed_count"]),
                        "before_snippet": before_fn_snip,
                        "after_snippet": after_fn_snip,
                    }
                    new_history = history + [step_rec]

                    if cand_failed_count == 0:
                        # Materialize candidate and run mandatory Sabotage Control
                        for rp, rb in next_files.items():
                            (wt / rp).write_bytes(rb)
                        sabotage_ok = _sabotage_control_kills_suite(
                            wt,
                            rel_f,
                            fn_nm,
                            firstlineno=fl_no,
                            test_files=test_files,
                            failing_nodeids=failing_nodeids if use_fast_pytest_screen else None,
                        )
                        if not sabotage_ok:
                            continue
                        winning_state = (next_files, new_history, cand_diag)
                        break

                    next_beam.append((next_files, new_history, cand_diag))

                if winning_state is not None:
                    break

            if winning_state is not None:
                break
            if not next_beam:
                break
            # Rank beam by (fewest failed tests, smallest assertion residual, most passed tests, shortest patch history)
            next_beam.sort(
                key=lambda item: (
                    int(item[2]["failed_count"]),
                    _assertion_residual(item[2].get("failed_tests") or []),
                    -int(item[2]["passed_count"]),
                    len(item[1]),
                )
            )
            beam = next_beam[:beam_width]

        # Enforce NEVER-MUTATE-SOURCE prior to authorized promotion
        if _merkle_snapshot(src_root) != source_merkle_before:
            return {
                "schema": SCHEMA,
                "ok": False,
                "verified": False,
                "status": "FAIL_CLOSED__SOURCE_TREE_DRIFTED_DURING_SEARCH",
                "reason": "SOURCE_TREE_DRIFTED_DURING_SEARCH",
            }

        if winning_state is None:
            return {
                "schema": SCHEMA,
                "ok": False,
                "verified": False,
                "status": "FAIL_CLOSED__CLOSED_LOOP_EXHAUSTED_WITHOUT_GREEN_SUITE",
                "reason": "CLOSED_LOOP_EXHAUSTED_WITHOUT_GREEN_SUITE",
                "initial_failed_count": initial_diag["failed_count"],
                "candidates_evaluated": candidates_evaluated,
                "pruned_regressions": pruned_regressions,
                "initial_suspects": initial_diag["suspects"][:5],
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "model_dependency_count": 0,
                "incremental_spend_usd": 0,
            }

        final_files, final_history, final_diag = winning_state
        changed_files: list[str] = []
        unified_diffs: list[str] = []
        crystallized_ids: list[str] = []

        for rel_p, new_b in sorted(final_files.items()):
            old_b = initial_source_files[rel_p]
            if new_b != old_b:
                changed_files.append(rel_p)
                old_txt = old_b.decode("utf-8", errors="replace")
                new_txt = new_b.decode("utf-8", errors="replace")
                diff_txt = "".join(
                    difflib.unified_diff(
                        old_txt.splitlines(keepends=True),
                        new_txt.splitlines(keepends=True),
                        fromfile=f"a/{rel_p}",
                        tofile=f"b/{rel_p}",
                    )
                )
                unified_diffs.append(diff_txt)

        # Crystallize verified function-level steps into VerifiedSkillStore
        for step_rec in final_history:
            b_snip = str(step_rec.get("before_snippet") or "").strip()
            a_snip = str(step_rec.get("after_snippet") or "").strip()
            if b_snip and a_snip and b_snip != a_snip:
                try:
                    c_res = skill_store.crystallize_code_fix(
                        before_snippet=b_snip,
                        after_snippet=a_snip,
                        language="python",
                        error_class="CLOSED_LOOP_REPO_REPAIR",
                    )
                    if c_res.get("crystallized") and c_res.get("skill_id"):
                        crystallized_ids.append(str(c_res["skill_id"]))
                except Exception:
                    pass

        if apply_to_source:
            for rel_p in changed_files:
                (src_root / rel_p).write_bytes(final_files[rel_p])

        return {
            "schema": SCHEMA,
            "ok": True,
            "verified": True,
            "sabotage_control_passed": True,
            "applied_to_source": apply_to_source,
            "status": "PASS__CLOSED_LOOP_MULTISTEP_REPO_REPAIRED_AND_VERIFIED",
            "steps_taken": len(final_history),
            "repair_steps": [
                {k: v for k, v in s.items() if k not in ("before_snippet", "after_snippet")}
                for s in final_history
            ],
            "initial_suspects": [
                {"file": s["file"], "function": s["function"], "score": s["score"]}
                for s in initial_diag["suspects"][:5]
            ],
            "initial_failed_count": initial_diag["failed_count"],
            "passed_count": final_diag["passed_count"],
            "failed_count": 0,
            "candidates_evaluated": candidates_evaluated,
            "pruned_regressions": pruned_regressions,
            "changed_files": changed_files,
            "patched_sources": {
                rel_p: final_files[rel_p].decode("utf-8", errors="replace")
                for rel_p in changed_files
            },
            "crystallized_skill_ids": crystallized_ids,
            "diff": "\n".join(unified_diffs),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
        }


# --------------------------------------------------------------------------- #
# 4. Execution-Backed Concurrency Schedule Prober (`sys.setswitchinterval`)
# --------------------------------------------------------------------------- #

_RACE_PROBER_CHILD_CODE = r"""
import importlib.util
import inspect
import json
import pathlib
import sys
import threading

target_file = pathlib.Path(sys.argv[1]).resolve()
threads_n = int(sys.argv[2])
iters_n = int(sys.argv[3])
sys.path.insert(0, str(target_file.parent))

spec = importlib.util.spec_from_file_location("_race_subj", target_file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

witnesses = []

def _snapshot_globals(m):
    snap = {}
    for k, v in vars(m).items():
        if k.startswith("__"):
            continue
        if isinstance(v, (int, float, str, bool)):
            snap[k] = v
        elif isinstance(v, (list, dict, set)) and len(v) <= 5000:
            snap[k] = len(v) if not isinstance(v, dict) else dict(list(v.items())[:50])
    return snap

# 1. Probe module-level zero-arg or single-int-arg mutators against sequential run
for name, fn in sorted(vars(mod).items()):
    if name.startswith("_") or not inspect.isfunction(fn):
        continue
    sig = inspect.signature(fn)
    params = [
        p for p in sig.parameters.values()
        if p.default is inspect.Parameter.empty
        and p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if len(params) > 1:
        continue
    call_args = (1,) if len(params) == 1 else ()

    # Sequential run in fresh module copy
    mod_seq = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod_seq)
    before_seq = _snapshot_globals(mod_seq)
    seq_fn = getattr(mod_seq, name)
    try:
        for _ in range(threads_n * iters_n):
            seq_fn(*call_args)
    except Exception:
        continue
    after_seq = _snapshot_globals(mod_seq)
    if after_seq == before_seq:
        continue

    # Concurrent interleaved run under sys.setswitchinterval(1e-6)
    for attempt in range(3):
        mod_conc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod_conc)
        conc_fn = getattr(mod_conc, name)
        barrier = threading.Barrier(threads_n)
        errors = []

        def _worker():
            try:
                barrier.wait(timeout=5.0)
                for _ in range(iters_n):
                    conc_fn(*call_args)
            except BaseException as exc:
                errors.append(f"{type(exc).__name__}: {exc}")

        old_si = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)
        try:
            ts = [threading.Thread(target=_worker) for _ in range(threads_n)]
            for t in ts:
                t.start()
            for t in ts:
                t.join(timeout=8.0)
        finally:
            sys.setswitchinterval(old_si)

        after_conc = _snapshot_globals(mod_conc)
        if errors or after_conc != after_seq:
            witnesses.append({
                "target": name,
                "kind": "EXECUTION_PROVED_DATA_RACE",
                "sequential_state": after_seq,
                "concurrent_state": after_conc,
                "thread_errors": errors[:3],
            })
            break

# 2. Probe zero-arg classes with zero/one-arg mutating methods (e.g. Counter/Account/Cache)
for cls_name, cls_obj in sorted(vars(mod).items()):
    if cls_name.startswith("_") or not inspect.isclass(cls_obj) or cls_obj.__module__ != mod.__name__:
        continue
    try:
        inst_seq = cls_obj()
    except Exception:
        continue
    for mname, mfn in inspect.getmembers(cls_obj, predicate=inspect.isfunction):
        if mname.startswith("_"):
            continue
        sig = inspect.signature(mfn)
        params = [
            p for p in list(sig.parameters.values())[1:]
            if p.default is inspect.Parameter.empty
            and p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        if len(params) > 1:
            continue
        call_args = (1,) if len(params) == 1 else ()
        inst_seq = cls_obj()
        before_d = dict(vars(inst_seq))
        try:
            for _ in range(threads_n * iters_n):
                getattr(inst_seq, mname)(*call_args)
        except Exception:
            continue
        after_seq_d = {k: (len(v) if isinstance(v, (list, set)) else v) for k, v in vars(inst_seq).items()}
        if after_seq_d == before_d:
            continue

        for attempt in range(3):
            inst_conc = cls_obj()
            barrier = threading.Barrier(threads_n)
            errors = []

            def _cworker():
                try:
                    barrier.wait(timeout=5.0)
                    bound = getattr(inst_conc, mname)
                    for _ in range(iters_n):
                        bound(*call_args)
                except BaseException as exc:
                    errors.append(f"{type(exc).__name__}: {exc}")

            old_si = sys.getswitchinterval()
            sys.setswitchinterval(1e-6)
            try:
                ts = [threading.Thread(target=_cworker) for _ in range(threads_n)]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join(timeout=8.0)
            finally:
                sys.setswitchinterval(old_si)

            after_conc_d = {k: (len(v) if isinstance(v, (list, set)) else v) for k, v in vars(inst_conc).items()}
            if errors or after_conc_d != after_seq_d:
                witnesses.append({
                    "target": f"{cls_name}.{mname}",
                    "kind": "EXECUTION_PROVED_INSTANCE_DATA_RACE",
                    "sequential_state": after_seq_d,
                    "concurrent_state": after_conc_d,
                    "thread_errors": errors[:3],
                })
                break

print(json.dumps({"witnesses": witnesses}))
"""


def probe_concurrency_races_live(
    target: str | pathlib.Path,
    *,
    threads: int = 8,
    iterations: int = 200,
    timeout: float = 12.0,
) -> dict[str, Any]:
    """Run deterministic thread-switch stress probing in an isolated child process."""
    p = pathlib.Path(target).resolve()
    py_files = [p] if p.is_file() else sorted(f for f in _iter_repo_files(p) if f.suffix == ".py")
    witnesses: list[dict[str, Any]] = []
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"

    for pf in py_files:
        if _is_test_relpath(pf.name):
            continue
        try:
            proc = subprocess.run(
                [sys.executable, "-B", "-c", _RACE_PROBER_CHILD_CODE, str(pf), str(threads), str(iterations)],
                cwd=str(pf.parent),
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                doc = json.loads(proc.stdout.strip().splitlines()[-1])
                for w in doc.get("witnesses") or []:
                    w["file"] = str(pf)
                    witnesses.append(w)
        except Exception:
            continue

    return {
        "ok": True,
        "execution_proved_count": len(witnesses),
        "witnesses": witnesses,
    }
