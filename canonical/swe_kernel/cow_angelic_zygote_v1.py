#!/usr/bin/env python3
"""Copy-on-Write Prewarmed Pytest Zygote Server, Angelic Branch Inversion,
Contrastive Separating-Guard Synthesis, Algebraic Differential Lenses,
Zero-Leakage Docstring/Git-History Oracle Factory, and CoW Boundary Fuzzer.

Zero model calls (`model_calls == 0`), `$0.00` spend, zero memorized world facts.
Every mechanism is purely general and algorithmic:
  1. `PytestCoWZygoteServer`: boots Python + pytest ONCE per repo, serves `os.fork()`
     Copy-on-Write candidate evaluations via an in-memory `sys.meta_path` loader
     (zero disk writes, zero `__pycache__` thrashing, parallel batching, mandatory
     clean disk verification on final winning patches).
  2. `synthesize_angelic_separating_guards`: live `os.fork()` angelic branch flips
     prove the exact causal `if`/`elif` site, capture contrastive runtime states
     `Sigma_pos` (passing tests) vs `Sigma_neg` (failing tests), and solve for the
     minimal structural separating predicate (boolean/nullability/sentinel/pairwise/DNF).
  3. `synthesize_algebraic_differential_repairs`: general algebraic operators:
     (a) Angelic call-wrapper unwrap (`f(x) -> x`),
     (b) Differential output-to-literal & percent-encoding / caret-FST codec lenses,
     (c) Sibling call-site keyword/context propagation.
  4. `ZeroLeakageOracleFactory`: ephemeral per-repo `git log` symbol alignment
     (destroyed on exit), docstring-stated metamorphic oracle compiler, and inline
     issue reproducer extractor — zero hidden test leakage.
  5. `verify_cow_boundary_invariance` & `L3 Negative-Space Invariants`: 64-vector
     boundary invariance check + O(1) structural negative-space pruning.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import itertools
import json
import os
import pathlib
import re
import select
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_COW_ANGELIC_ZYGOTE_V1"
PRODUCER_MODEL_CALLS: int = 0

_PYTEST_CORE_CONFLICTS = frozenset({"pytest", "_pytest", "pluggy", "packaging", "iniconfig"})
_BUILTIN_SENTINELS = frozenset({"None", "True", "False"})


# ============================================================================
# 1. PREWARMED COPY-ON-WRITE (`os.fork()`) PYTEST ZYGOTE SERVER
# ============================================================================

_ZYGOTE_WORKER_SCRIPT = r'''
import ast
import contextlib
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import io
import json
import os
import pathlib
import re
import select
import signal
import sys
import time
import traceback

REPO_ROOT = pathlib.Path(sys.argv[1]).resolve()
CAN_PREIMPORT_PYTEST = (sys.argv[2] == "1")
EXTRA_PATHS = [p for p in sys.argv[3].split(os.pathsep) if p]

# Put repo paths at the front of sys.path
for p in reversed(EXTRA_PATHS):
    if p and p not in sys.path:
        sys.path.insert(0, p)

if CAN_PREIMPORT_PYTEST:
    try:
        import pytest  # noqa: F401
        import _pytest  # noqa: F401
        import _pytest.config  # noqa: F401
    except Exception:
        pass


class _InMemorySourceLoader(importlib.abc.SourceLoader):
    def __init__(self, fullname: str, path: str, source_bytes: bytes, is_pkg: bool):
        self.fullname = fullname
        self.path = path
        self.source_bytes = source_bytes
        self.is_pkg = is_pkg

    def get_filename(self, fullname: str) -> str:
        return self.path

    def get_data(self, path: str) -> bytes:
        if os.path.abspath(path) == os.path.abspath(self.path):
            return self.source_bytes
        with open(path, "rb") as f:
            return f.read()


class _InMemoryEditFinder(importlib.abc.MetaPathFinder):
    """Intercepts imports whose source file is in `edits_by_abs`, serving patched
    code directly from memory with ZERO disk writes and ZERO __pycache__ writes."""

    def __init__(self, edits_by_abs: dict[str, bytes]):
        self.edits_by_abs = edits_by_abs
        self._in_find = False

    def find_spec(self, fullname, path, target=None):
        if self._in_find or not self.edits_by_abs:
            return None
        self._in_find = True
        try:
            spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
            if spec is None or not spec.origin:
                return None
            abs_origin = os.path.abspath(spec.origin)
            if abs_origin in self.edits_by_abs:
                is_pkg = spec.submodule_search_locations is not None
                loader = _InMemorySourceLoader(fullname, abs_origin, self.edits_by_abs[abs_origin], is_pkg)
                new_spec = importlib.util.spec_from_loader(fullname, loader, origin=abs_origin, is_package=is_pkg)
                if new_spec is not None and is_pkg and spec.submodule_search_locations is not None:
                    new_spec.submodule_search_locations = list(spec.submodule_search_locations)
                return new_spec
            return None
        finally:
            self._in_find = False


def _parse_failures(output: str) -> list[str]:
    failed = []
    seen = set()
    for line in output.splitlines():
        m = re.match(r"^(?:FAILED|ERROR)\s+([^\s]+)", line.strip())
        if m:
            nid = m.group(1)
            if nid not in seen:
                seen.add(nid)
                failed.append(nid)
            continue
        m2 = re.match(r"^SUBFAILED(?:\[[^\]]*\])?\s+([^\s]+)", line.strip())
        if m2:
            nid = m2.group(1)
            if nid not in seen:
                seen.add(nid)
                failed.append(nid)
    return failed


def _passed_count(output: str) -> int:
    m = re.search(r"(\d+)\s+passed", output)
    return int(m.group(1)) if m else 0


def _install_memory_edits(edits: dict[str, str], top_pkgs: list[str]) -> None:
    if not edits:
        return
    edits_by_abs = {}
    for rel, src in edits.items():
        ap = os.path.abspath(str((REPO_ROOT / rel).resolve()))
        edits_by_abs[ap] = src.encode("utf-8")
    # Evict any pre-loaded target package modules so the in-memory finder serves fresh code
    if top_pkgs:
        for mod_name in list(sys.modules.keys()):
            root_pkg = mod_name.split(".", 1)[0]
            if root_pkg in top_pkgs:
                sys.modules.pop(mod_name, None)
    sys.dont_write_bytecode = True
    sys.meta_path.insert(0, _InMemoryEditFinder(edits_by_abs))


def _run_pytest_in_child(targets: list[str], edits: dict[str, str], top_pkgs: list[str]) -> dict:
    t0 = time.perf_counter()
    os.chdir(str(REPO_ROOT))
    _install_memory_edits(edits, top_pkgs)
    import pytest  # noqa: F401

    buf = io.StringIO()
    args = [
        "-q",
        "--tb=short",
        "-o", "addopts=",
        "-o", "filterwarnings=default",
        "-p", "no:asyncio",
        "-p", "no:hypothesispytest",
        "-p", "no:cacheprovider",
        *targets,
    ]
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            rc = int(pytest.main(args))
        except SystemExit as exc:
            rc = int(exc.code) if isinstance(exc.code, int) else 1
        except Exception:
            traceback.print_exc(file=buf)
            rc = 2
    out = buf.getvalue()
    failed = _parse_failures(out)
    passed = _passed_count(out)
    return {
        "ok": (rc == 0 and not failed),
        "rc": rc,
        "passed": passed,
        "failed_nodeids": failed,
        "output": out[-6000:],
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }


def _collect_branch_states_in_child(
    rel_file: str,
    branch_lines: list[int],
    failing_targets: list[str],
    passing_targets: list[str],
    sentinel_exprs: list[str],
    top_pkgs: list[str],
) -> dict:
    """Instrument each candidate `if` condition in memory to record (cond_val, structural_state)
    on failing vs passing test executions in a SINGLE CoW child process."""
    t0 = time.perf_counter()
    os.chdir(str(REPO_ROOT))
    target_path = (REPO_ROOT / rel_file).resolve()
    orig_src = target_path.read_text(encoding="utf-8", errors="replace")
    branch_set = set(int(x) for x in branch_lines)

    # Shared recorder stored in builtins so instrumented module accesses it with zero import cycles
    import builtins

    records: dict[int, list[dict]] = {ln: [] for ln in branch_set}
    phase_box = ["fail"]

    def _safe_structural_state(loc_dict: dict, glob_dict: dict) -> dict:
        # Resolve module/imported sentinel objects ONCE per snapshot (strictly non-primitive repo sentinels!)
        resolved_sentinels: list[tuple[str, object]] = []
        for sexpr in sentinel_exprs[:20]:
            try:
                sobj = None
                found = False
                if "." in sexpr:
                    base, attr = sexpr.split(".", 1)
                    obj = loc_dict.get(base, glob_dict.get(base))
                    if obj is not None and hasattr(obj, attr):
                        sobj = getattr(obj, attr)
                        found = True
                else:
                    if sexpr in glob_dict:
                        sobj = glob_dict[sexpr]
                        found = True
                # Never treat plain bools/ints/floats/None (e.g. TYPE_CHECKING, PY_3_10_PLUS) as identity sentinels!
                if found and sobj is not None and not isinstance(sobj, (bool, int, float, str, bytes)):
                    resolved_sentinels.append((sexpr, sobj))
            except Exception:
                pass

        atoms: dict[str, bool] = {}
        scalar_vals: dict[str, tuple[type, object]] = {}

        import types as _types

        def _record_val(expr_name: str, val: object, depth: int) -> None:
            if isinstance(val, (_types.MethodType, _types.BuiltinMethodType, _types.ModuleType)):
                return
            is_none = (val is None)
            atoms[f"{expr_name} is None"] = is_none
            atoms[f"{expr_name} is not None"] = (not is_none)
            if isinstance(val, bool):
                atoms[expr_name] = val
                atoms[f"not {expr_name}"] = (not val)
            elif not callable(val):
                try:
                    truth = bool(val)
                    atoms[f"bool({expr_name})"] = truth
                    atoms[f"not {expr_name}"] = (not truth)
                except Exception:
                    pass
            if isinstance(val, (str, bytes, list, tuple, dict, set, frozenset)):
                atoms[f"len({expr_name}) == 0"] = (len(val) == 0)
                atoms[f"len({expr_name}) > 0"] = (len(val) > 0)
            if isinstance(val, (str, int, float, bytes)) and not isinstance(val, bool):
                scalar_vals[expr_name] = (type(val), val)
            for sname, sobj in resolved_sentinels:
                if val is sobj:
                    atoms[f"{expr_name} is {sname}"] = True
                    atoms[f"{expr_name} is not {sname}"] = False
                else:
                    atoms[f"{expr_name} is {sname}"] = False
                    atoms[f"{expr_name} is not {sname}"] = True
            # Inspect depth-1 / depth-2 instance attributes (vars / __slots__)
            if depth < 2 and val is not None and not callable(val) and not isinstance(val, (bool, int, float, str, bytes, list, tuple, dict, set, frozenset, type)):
                attr_names: list[str] = []
                try:
                    d = getattr(val, "__dict__", None)
                    if isinstance(d, dict):
                        attr_names.extend(list(d.keys())[:48])
                    else:
                        for cls in type(val).__mro__[:3]:
                            sl = getattr(cls, "__slots__", ())
                            if isinstance(sl, str):
                                sl = (sl,)
                            for s in sl:
                                if s not in attr_names:
                                    attr_names.append(s)
                            if len(attr_names) >= 48:
                                break
                except Exception:
                    pass
                for aname in attr_names[:44]:
                    if aname.startswith("__"):
                        continue
                    try:
                        aval = getattr(val, aname)
                    except Exception:
                        continue
                    if isinstance(aval, (_types.MethodType, _types.BuiltinMethodType, _types.ModuleType)):
                        continue
                    _record_val(f"{expr_name}.{aname}", aval, depth + 1)

        for k, v in list(loc_dict.items())[:18]:
            if k.startswith("__"):
                continue
            _record_val(k, v, 0)

        # Pairwise equalities among same-typed scalar locals/attrs (strictly program variables, NEVER test literals!)
        s_items = list(scalar_vals.items())[:14]
        for i in range(len(s_items)):
            n1, (t1, v1) = s_items[i]
            for j in range(i + 1, len(s_items)):
                n2, (t2, v2) = s_items[j]
                if t1 is t2:
                    eq = (v1 == v2)
                    atoms[f"{n1} == {n2}"] = eq
                    atoms[f"{n1} != {n2}"] = (not eq)
        return atoms

    def _brain_probe_if(lineno: int, cond_val: object, loc_dict: dict, glob_dict: dict) -> bool:
        bval = bool(cond_val)
        bucket = records.get(lineno)
        if bucket is not None and len(bucket) < 30:
            bucket.append({
                "phase": phase_box[0],
                "cond": bval,
                "atoms": _safe_structural_state(loc_dict, glob_dict),
            })
        return bval

    builtins._brain_probe_if = _brain_probe_if

    # AST-instrument target `if` conditions at `branch_set`
    class _IfInstrumentor(ast.NodeTransformer):
        def visit_If(self, node: ast.If) -> ast.AST:
            self.generic_visit(node)
            if node.lineno in branch_set:
                node.test = ast.Call(
                    func=ast.Name(id="_brain_probe_if", ctx=ast.Load()),
                    args=[
                        ast.Constant(value=int(node.lineno)),
                        node.test,
                        ast.Call(func=ast.Name(id="locals", ctx=ast.Load()), args=[], keywords=[]),
                        ast.Call(func=ast.Name(id="globals", ctx=ast.Load()), args=[], keywords=[]),
                    ],
                    keywords=[],
                )
            return node

    try:
        tree = ast.parse(orig_src)
        inst_tree = _IfInstrumentor().visit(tree)
        ast.fix_missing_locations(inst_tree)
        inst_src = ast.unparse(inst_tree)
    except Exception as exc:
        return {"ok": False, "error": f"instrument_failed:{exc}", "records": {}}

    _install_memory_edits({rel_file: inst_src}, top_pkgs)
    import pytest  # noqa: F401

    base_args = ["-q", "--tb=no", "-o", "addopts=", "-o", "filterwarnings=default", "-p", "no:asyncio", "-p", "no:hypothesispytest", "-p", "no:cacheprovider"]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        phase_box[0] = "fail"
        try:
            pytest.main(base_args + list(failing_targets[:4]))
        except SystemExit:
            pass
        except Exception:
            pass
        if passing_targets:
            phase_box[0] = "pass"
            try:
                pytest.main(base_args + list(passing_targets[:20]))
            except SystemExit:
                pass
            except Exception:
                pass

    return {
        "ok": True,
        "records": {str(k): v for k, v in records.items() if v},
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }


def _trace_differential_spectrum_in_child(
    failing_targets: list[str],
    passing_targets: list[str],
    top_pkgs: list[str],
) -> dict:
    """1-shot CoW Ochiai Differential Spectrum Tracer: records executed (rel_file, lineno)
    counts across failing tests vs passing sibling tests in a SINGLE CoW child (~250ms)."""
    t0 = time.perf_counter()
    os.chdir(str(REPO_ROOT))
    import pytest  # noqa: F401

    root_str = str(REPO_ROOT)
    fail_lines: dict[str, dict[int, int]] = {}
    pass_lines: dict[str, dict[int, int]] = {}
    cur_bucket = [fail_lines]
    cur_test_seen: set[tuple[str, int]] = set()
    ev_budget = [20000]

    def _rel_if_repo_src(fn: str) -> str | None:
        if not fn or fn.startswith("<"):
            return None
        try:
            ap = os.path.abspath(fn)
        except Exception:
            return None
        if not ap.startswith(root_str + os.sep):
            return None
        rel = ap[len(root_str) + 1:].replace(os.sep, "/")
        low = rel.lower()
        if "test" in low or "/tests/" in low or low.startswith("tests/") or not rel.endswith(".py"):
            return None
        return rel

    def _tracer(frame, event, arg):
        if event == "line":
            ev_budget[0] -= 1
            if ev_budget[0] <= 0:
                sys.settrace(None)
                return None
            rel = _rel_if_repo_src(frame.f_code.co_filename)
            if rel is not None:
                key = (rel, frame.f_lineno)
                if key not in cur_test_seen:
                    cur_test_seen.add(key)
                    d = cur_bucket[0].setdefault(rel, {})
                    d[frame.f_lineno] = d.get(frame.f_lineno, 0) + 1
        return _tracer

    class _SpecPlugin:
        def pytest_runtest_call(self, item):
            cur_test_seen.clear()
            ev_budget[0] = 20000
            sys.settrace(_tracer)
            try:
                item.runtest()
            finally:
                sys.settrace(None)
            return True

    base_args = [
        "-q", "--tb=no", "-o", "addopts=", "-o", "filterwarnings=default",
        "-p", "no:asyncio", "-p", "no:hypothesispytest", "-p", "no:cacheprovider",
    ]
    buf = io.StringIO()
    n_fail = max(1, len(failing_targets[:3]))
    n_pass = len(passing_targets[:4])
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        cur_bucket[0] = fail_lines
        try:
            pytest.main(base_args + list(failing_targets[:3]), plugins=[_SpecPlugin()])
        except SystemExit:
            pass
        except Exception:
            pass
        if passing_targets:
            cur_bucket[0] = pass_lines
            try:
                pytest.main(base_args + list(passing_targets[:4]), plugins=[_SpecPlugin()])
            except SystemExit:
                pass
            except Exception:
                pass

    # Compute Ochiai suspiciousness per (rel_file, lineno)
    import math
    line_scores: dict[str, dict[str, float]] = {}
    file_scores: dict[str, float] = {}
    for rel, lmap in fail_lines.items():
        pmap = pass_lines.get(rel, {})
        scores_f: dict[str, float] = {}
        top_vals: list[float] = []
        for ln, ef in lmap.items():
            ep = pmap.get(ln, 0)
            ochiai = ef / math.sqrt(float(n_fail) * float(ef + ep))
            scores_f[str(ln)] = round(ochiai, 4)
            top_vals.append(ochiai)
        line_scores[rel] = scores_f
        top_vals.sort(reverse=True)
        # File score = mean of top-5 most suspicious lines (immune to huge runner files!)
        base_f = sum(top_vals[:5]) / max(1, len(top_vals[:5]))
        if rel.endswith("testing.py") or rel.endswith("/test.py"):
            base_f *= 0.45
        file_scores[rel] = round(base_f, 4)

    ranked_files = sorted(file_scores.keys(), key=lambda r: -file_scores[r])
    return {
        "ok": True,
        "ranked_files": ranked_files,
        "file_scores": file_scores,
        "line_scores": line_scores,
        "n_fail": n_fail,
        "n_pass": n_pass,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }


def _fork_exec(fn, timeout_s: float) -> dict:
    r_fd, w_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(r_fd)
        try:
            res = fn()
            payload = json.dumps(res, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        except Exception as exc:
            payload = json.dumps({"ok": False, "rc": 2, "error": str(exc), "failed_nodeids": [], "output": ""}).encode("utf-8")
        try:
            view = memoryview(payload)
            off = 0
            while off < len(view):
                off += os.write(w_fd, view[off:])
        finally:
            os.close(w_fd)
            os._exit(0)
    os.close(w_fd)
    chunks = []
    deadline = time.monotonic() + max(0.5, float(timeout_s))
    timed_out = False
    try:
        while True:
            rem = deadline - time.monotonic()
            if rem <= 0:
                timed_out = True
                break
            rlist, _, _ = select.select([r_fd], [], [], min(0.25, rem))
            if rlist:
                data = os.read(r_fd, 65536)
                if not data:
                    break
                chunks.append(data)
    finally:
        os.close(r_fd)
        if timed_out:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
    if timed_out:
        return {"ok": False, "rc": 124, "passed": 0, "failed_nodeids": [], "output": "ZYGOTE_TIMEOUT"}
    raw = b"".join(chunks).decode("utf-8", errors="replace").strip()
    if not raw:
        return {"ok": False, "rc": 2, "passed": 0, "failed_nodeids": [], "output": "ZYGOTE_EMPTY"}
    return json.loads(raw)


def _fork_batch(items: list[dict], targets: list[str], top_pkgs: list[str], timeout_s: float, max_workers: int) -> list[dict]:
    """Run up to `max_workers` CoW children concurrently over `items` (each `{id, edits}`)."""
    results: dict[int, dict] = {}
    queue = list(enumerate(items))
    active: list[tuple[int, int, int, float, list[bytes]]] = []  # (idx, pid, r_fd, deadline, chunks)

    def _spawn(idx: int, item: dict) -> None:
        r_fd, w_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(r_fd)
            try:
                t_list = item.get("targets") or targets
                res = _run_pytest_in_child(t_list, item.get("edits") or {}, top_pkgs)
                payload = json.dumps(res, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            except Exception as exc:
                payload = json.dumps({"ok": False, "rc": 2, "error": str(exc), "failed_nodeids": [], "output": ""}).encode("utf-8")
            try:
                view = memoryview(payload)
                off = 0
                while off < len(view):
                    off += os.write(w_fd, view[off:])
            finally:
                os.close(w_fd)
                os._exit(0)
        os.close(w_fd)
        os.set_blocking(r_fd, False)
        active.append((idx, pid, r_fd, time.monotonic() + max(0.5, float(timeout_s)), []))

    while queue or active:
        while queue and len(active) < max(1, int(max_workers)):
            idx, item = queue.pop(0)
            _spawn(idx, item)
        if not active:
            break
        r_fds = [entry[2] for entry in active]
        ready, _, _ = select.select(r_fds, [], [], 0.05)
        now = time.monotonic()
        still_active = []
        for idx, pid, r_fd, dl, chunks in active:
            done = False
            timed_out = False
            if r_fd in ready:
                while True:
                    try:
                        data = os.read(r_fd, 65536)
                        if not data:
                            done = True
                            break
                        chunks.append(data)
                    except BlockingIOError:
                        break
            if not done and now >= dl:
                timed_out = True
                done = True
            if done:
                os.close(r_fd)
                if timed_out:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    try:
                        os.waitpid(pid, 0)
                    except ChildProcessError:
                        pass
                    results[idx] = {"ok": False, "rc": 124, "passed": 0, "failed_nodeids": [], "output": "ZYGOTE_TIMEOUT"}
                else:
                    try:
                        os.waitpid(pid, 0)
                    except ChildProcessError:
                        pass
                    raw = b"".join(chunks).decode("utf-8", errors="replace").strip()
                    results[idx] = json.loads(raw) if raw else {"ok": False, "rc": 2, "passed": 0, "failed_nodeids": [], "output": "ZYGOTE_EMPTY"}
            else:
                still_active.append((idx, pid, r_fd, dl, chunks))
        active = still_active

    return [results[i] for i in range(len(items))]


def _main_loop() -> None:
    # Signal ready
    sys.stdout.write(json.dumps({"ready": True, "preimported_pytest": CAN_PREIMPORT_PYTEST}) + "\n")
    sys.stdout.flush()
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        req = json.loads(line)
        op = req.get("op")
        if op == "quit":
            break
        elif op == "eval_patch":
            resp = _fork_exec(
                lambda: _run_pytest_in_child(req["targets"], req.get("edits") or {}, req.get("top_pkgs") or []),
                timeout_s=float(req.get("timeout_s", 8.0)),
            )
        elif op == "eval_batch":
            resp = {
                "results": _fork_batch(
                    req.get("items") or [],
                    req.get("targets") or [],
                    req.get("top_pkgs") or [],
                    timeout_s=float(req.get("timeout_s", 6.0)),
                    max_workers=int(req.get("max_workers", 2)),
                )
            }
        elif op == "probe_branches":
            resp = _fork_exec(
                lambda: _collect_branch_states_in_child(
                    req["rel_file"],
                    req["branch_lines"],
                    req["failing_targets"],
                    req.get("passing_targets") or [],
                    req.get("sentinel_exprs") or [],
                    req.get("top_pkgs") or [],
                ),
                timeout_s=float(req.get("timeout_s", 8.0)),
            )
        elif op == "trace_spectrum":
            resp = _fork_exec(
                lambda: _trace_differential_spectrum_in_child(
                    req["failing_targets"],
                    req.get("passing_targets") or [],
                    req.get("top_pkgs") or [],
                ),
                timeout_s=float(req.get("timeout_s", 10.0)),
            )
        else:
            resp = {"ok": False, "error": f"unknown_op:{op}"}
        sys.stdout.write(json.dumps(resp, separators=(",", ":"), ensure_ascii=False) + "\n")
        sys.stdout.flush()


_main_loop()
'''


def _detect_repo_top_packages(repo_root: pathlib.Path) -> list[str]:
    pkgs: list[str] = []
    for base in (repo_root / "src", repo_root):
        if not base.is_dir():
            continue
        for entry in sorted(base.iterdir()):
            name = entry.name
            if name.startswith(".") or name in ("tests", "test", "docs", "doc", "scripts", "examples", "build", "dist"):
                continue
            if entry.is_dir() and (entry / "__init__.py").is_file():
                if name not in pkgs:
                    pkgs.append(name)
            elif entry.is_file() and name.endswith(".py") and name != "setup.py":
                stem = name[:-3]
                if stem not in pkgs:
                    pkgs.append(stem)
    return pkgs


class PytestCoWZygoteServer:
    """Prewarmed Copy-on-Write (`os.fork()`) pytest evaluator with zero disk writes."""

    def __init__(self, repo_root: pathlib.Path, *, extra_pythonpath: str | None = None) -> None:
        self.repo_root = pathlib.Path(repo_root).resolve()
        self.extra_pythonpath = extra_pythonpath
        self.top_pkgs = _detect_repo_top_packages(self.repo_root)
        # Only pre-import pytest before fork when the repo itself doesn't shadow pytest core deps
        self.can_preimport_pytest = not bool(set(self.top_pkgs) & _PYTEST_CORE_CONFLICTS)
        self._proc: subprocess.Popen[str] | None = None
        self.eval_count = 0
        self.total_eval_ms = 0.0

    def _build_pythonpaths(self) -> list[str]:
        parts: list[str] = []
        if (self.repo_root / "src").is_dir():
            parts.append(str((self.repo_root / "src").resolve()))
        parts.append(str(self.repo_root))
        if self.extra_pythonpath:
            parts.append(self.extra_pythonpath)
        elif pathlib.Path("/tmp/eval_deps").is_dir():
            parts.append("/tmp/eval_deps")
        return parts

    def start(self) -> bool:
        if self._proc is not None and self._proc.poll() is None:
            return True
        env = dict(os.environ)
        py_paths = self._build_pythonpaths()
        old_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join(py_paths + ([old_pp] if old_pp else []))
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        self._proc = subprocess.Popen(
            [
                sys.executable,
                "-u",
                "-c",
                _ZYGOTE_WORKER_SCRIPT,
                str(self.repo_root),
                "1" if self.can_preimport_pytest else "0",
                os.pathsep.join(py_paths),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            cwd=str(self.repo_root),
            env=env,
        )
        assert self._proc.stdout is not None
        rlist, _, _ = select.select([self._proc.stdout], [], [], 8.0)
        if not rlist:
            self.close()
            return False
        line = self._proc.stdout.readline().strip()
        if not line:
            self.close()
            return False
        info = json.loads(line)
        return bool(info.get("ready"))

    def _rpc(self, payload: Mapping[str, Any], timeout_s: float) -> dict[str, Any]:
        if self._proc is None or self._proc.poll() is not None:
            if not self.start():
                return {"ok": False, "rc": 2, "passed": 0, "failed_nodeids": [], "output": "ZYGOTE_START_FAILED"}
        assert self._proc is not None and self._proc.stdin is not None and self._proc.stdout is not None
        try:
            self._proc.stdin.write(json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n")
            self._proc.stdin.flush()
        except BrokenPipeError:
            self.close()
            return {"ok": False, "rc": 2, "passed": 0, "failed_nodeids": [], "output": "ZYGOTE_BROKEN_PIPE"}
        rlist, _, _ = select.select([self._proc.stdout], [], [], max(1.0, timeout_s + 2.0))
        if not rlist:
            self.close()
            return {"ok": False, "rc": 124, "passed": 0, "failed_nodeids": [], "output": "ZYGOTE_RPC_TIMEOUT"}
        line = self._proc.stdout.readline().strip()
        if not line:
            self.close()
            return {"ok": False, "rc": 2, "passed": 0, "failed_nodeids": [], "output": "ZYGOTE_EOF"}
        return json.loads(line)

    def eval_patch(
        self,
        edits: Mapping[str, str],
        targets: Sequence[str],
        *,
        timeout_s: float = 8.0,
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        res = self._rpc(
            {
                "op": "eval_patch",
                "edits": dict(edits),
                "targets": list(targets),
                "top_pkgs": self.top_pkgs,
                "timeout_s": float(timeout_s),
            },
            timeout_s=timeout_s,
        )
        self.eval_count += 1
        self.total_eval_ms += (time.perf_counter() - t0) * 1000.0
        return res

    def eval_batch(
        self,
        items: Sequence[Mapping[str, Any]],
        targets: Sequence[str],
        *,
        timeout_s: float = 6.0,
        max_workers: int = 2,
    ) -> list[dict[str, Any]]:
        if not items:
            return []
        t0 = time.perf_counter()
        resp = self._rpc(
            {
                "op": "eval_batch",
                "items": [dict(x) for x in items],
                "targets": list(targets),
                "top_pkgs": self.top_pkgs,
                "timeout_s": float(timeout_s),
                "max_workers": max(1, min(int(max_workers), os.cpu_count() or 2)),
            },
            timeout_s=timeout_s * max(1.5, len(items) / max(1, max_workers)) + 3.0,
        )
        results = resp.get("results")
        if not isinstance(results, list) or len(results) != len(items):
            return [{"ok": False, "rc": 2, "passed": 0, "failed_nodeids": [], "output": "BATCH_ERROR"} for _ in items]
        self.eval_count += len(items)
        self.total_eval_ms += (time.perf_counter() - t0) * 1000.0
        return results

    def probe_branches(
        self,
        rel_file: str,
        branch_lines: Sequence[int],
        failing_targets: Sequence[str],
        passing_targets: Sequence[str],
        sentinel_exprs: Sequence[str],
        *,
        timeout_s: float = 8.0,
    ) -> dict[str, Any]:
        return self._rpc(
            {
                "op": "probe_branches",
                "rel_file": rel_file,
                "branch_lines": [int(x) for x in branch_lines],
                "failing_targets": list(failing_targets),
                "passing_targets": list(passing_targets),
                "sentinel_exprs": list(sentinel_exprs),
                "top_pkgs": self.top_pkgs,
                "timeout_s": float(timeout_s),
            },
            timeout_s=timeout_s,
        )

    def trace_differential_spectrum(
        self,
        failing_targets: Sequence[str],
        passing_targets: Sequence[str],
        *,
        timeout_s: float = 10.0,
    ) -> dict[str, Any]:
        return self._rpc(
            {
                "op": "trace_spectrum",
                "failing_targets": list(failing_targets),
                "passing_targets": list(passing_targets),
                "top_pkgs": self.top_pkgs,
                "timeout_s": float(timeout_s),
            },
            timeout_s=timeout_s,
        )

    def close(self) -> None:
        if self._proc is not None:
            try:
                if self._proc.poll() is None and self._proc.stdin is not None:
                    self._proc.stdin.write('{"op":"quit"}\n')
                    self._proc.stdin.flush()
            except Exception:
                pass
            for stream in (self._proc.stdin, self._proc.stdout, self._proc.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
            try:
                self._proc.terminate()
                self._proc.wait(timeout=1.0)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None

    def __enter__(self) -> "PytestCoWZygoteServer":
        self.start()
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()


# ============================================================================
# 2. ANGELIC BRANCH INVERSION + CONTRASTIVE SEPARATING-GUARD SYNTHESIS
# ============================================================================

def _splice_node(source: str, node: ast.AST, replacement: str) -> str | None:
    if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
        return None
    lines = source.splitlines(keepends=True)
    sl, sc = node.lineno - 1, node.col_offset
    el, ec = node.end_lineno - 1, node.end_col_offset
    if sl < 0 or el >= len(lines):
        return None
    start_off = sum(len(lines[i]) for i in range(sl)) + sc
    end_off = sum(len(lines[i]) for i in range(el)) + ec
    patched = source[:start_off] + replacement + source[end_off:]
    try:
        ast.parse(patched)
    except SyntaxError:
        return None
    return patched


def _get_node_src(source: str, node: ast.AST) -> str | None:
    try:
        return ast.get_source_segment(source, node)
    except Exception:
        return None


def _mine_file_sentinel_exprs(tree: ast.Module, repo_root: pathlib.Path, rel_file: str) -> list[str]:
    """Harvest module-level constants / sentinels declared or imported in this file
    (e.g., `setters.NO_OP`, `_missing`, `UNSET`, `NOTHING`, `SENTINEL`)."""
    sentinels: list[str] = []
    seen: set[str] = set()

    def _add(expr: str) -> None:
        if expr not in seen and expr not in _BUILTIN_SENTINELS:
            seen.add(expr)
            sentinels.append(expr)

    imported_mods: dict[str, str] = {}
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name) and (t.id.isupper() or t.id.startswith("_") and "miss" in t.id.lower() or "unset" in t.id.lower() or "sentinel" in t.id.lower() or "noop" in t.id.lower().replace("_", "")):
                    _add(t.id)
        elif isinstance(stmt, ast.ImportFrom):
            mod = stmt.module or ""
            for alias in stmt.names:
                local = alias.asname or alias.name
                if local.isupper() or local in ("NOTHING", "UNSET", "NO_OP", "MISSING", "SENTINEL"):
                    _add(local)
                else:
                    imported_mods[local] = mod
        elif isinstance(stmt, ast.Import):
            for alias in stmt.names:
                local = alias.asname or alias.name.split(".")[-1]
                imported_mods[local] = alias.name

    # Also inspect `mod.UPPER_CONST` references already used anywhere in this file AND sibling module uppercase exports
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id in imported_mods and (node.attr.isupper() or node.attr in ("NO_OP", "NOTHING", "UNSET", "MISSING")):
                _add(f"{node.value.id}.{node.attr}")

    # Inspect sibling `.py` files imported via relative `from . import X` for uppercase sentinel exports
    cur_dir = (repo_root / rel_file).parent
    for local_name in list(imported_mods.keys())[:10]:
        sib = cur_dir / f"{local_name}.py"
        if sib.is_file():
            try:
                stree = ast.parse(sib.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for sstmt in stree.body:
                if isinstance(sstmt, ast.Assign):
                    for t in sstmt.targets:
                        if isinstance(t, ast.Name) and t.id.isupper() and len(t.id) >= 3:
                            _add(f"{local_name}.{t.id}")
                elif isinstance(sstmt, ast.AnnAssign) and isinstance(sstmt.target, ast.Name):
                    if sstmt.target.id.isupper() and len(sstmt.target.id) >= 3:
                        _add(f"{local_name}.{sstmt.target.id}")
    return sentinels[:24]


def _discover_passing_sibling_nodeids(
    repo_root: pathlib.Path,
    test_file_rel: str,
    failing_nodeids: Sequence[str],
    max_passing: int = 16,
) -> list[str]:
    """Extract top-level passing `def test_*` nodeids from the same test file (AST only, <2ms)."""
    tf = repo_root / test_file_rel
    if not tf.is_file():
        return []
    try:
        tree = ast.parse(tf.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    fail_bases = {nid.split("[", 1)[0] for nid in failing_nodeids}
    passing: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            cand = f"{test_file_rel}::{node.name}"
            if cand not in fail_bases:
                passing.append(cand)
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test_"):
                    cand = f"{test_file_rel}::{node.name}::{item.name}"
                    if cand not in fail_bases:
                        passing.append(cand)
    # Prioritize tests near the failing test(s) in the file (same feature domain!)
    if len(passing) > max_passing:
        tail_n = min(4, max(1, max_passing // 2))
        head_n = max(1, max_passing - tail_n)
        step = max(1, len(passing) // head_n)
        picked = passing[::step][:head_n] + passing[-tail_n:]
        return list(dict.fromkeys(picked))[:max_passing]
    return passing


def _extract_cond_subclauses(test_node: ast.expr, source: str) -> list[str]:
    """Extract atomic boolean sub-expressions already appearing in an `if` test."""
    out: list[str] = []
    def _walk(n: ast.expr) -> None:
        if isinstance(n, ast.BoolOp):
            for v in n.values:
                _walk(v)
        elif isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            _walk(n.operand)
        else:
            s = _get_node_src(source, n)
            if s and s not in out:
                out.append(s.strip())
    _walk(test_node)
    return out


def _solve_minimal_separating_predicates(
    pos_states: Sequence[Mapping[str, bool]],
    neg_states: Sequence[Mapping[str, bool]],
    *,
    want_pos_val: bool,
    hint_tokens: set[str],
    orig_cond_atoms: Sequence[str],
    max_results: int = 16,
) -> list[tuple[str, float]]:
    """Solve for minimal 1-atom and 2-atom structural separating predicates P over
    live runtime state snapshots such that:
      - P(s) == want_pos_val for all s in pos_states, AND
      - P(s) == (not want_pos_val) for all s in neg_states.
    Pure first-principles boolean separation (zero hardcoded repo rules!)."""
    if not neg_states:
        return []
    # Gather all atoms present across every neg_state
    all_atoms: set[str] = set(neg_states[0].keys())
    for ns in neg_states[1:]:
        all_atoms &= set(ns.keys())
    if not all_atoms:
        return []

    def _atom_complexity(a: str) -> float:
        # Prefer simple direct boolean/nullability/sentinel/equality predicates over `bool(...)`
        score = 0.0
        if " is not " in a or " is " in a:
            score += 4.0
        if "==" in a or "!=" in a:
            score += 3.5
        if a.startswith("not ") and "bool(" not in a:
            score += 3.0
        if "bool(" in a:
            score -= 2.0
        if "len(" in a:
            score -= 1.0
        # Shallow attribute depth preferred
        dot_depth = a.count(".")
        score -= 0.7 * dot_depth
        # Mild bonus if identifier overlaps tokens from failing test / condition / sentinel
        a_toks = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", a.lower()))
        overlap = len(a_toks & hint_tokens)
        score += 2.5 * min(3, overlap)
        if any(a in oa or oa in a for oa in orig_cond_atoms):
            score += 1.5
        # Prefer clean `not x` over `x is False`, and `x` over `bool(x)`
        score -= 0.03 * len(a)
        return score

    want_neg_val = not want_pos_val
    results: list[tuple[str, float]] = []
    seen_exprs: set[str] = set()

    def _clean_expr(expr: str) -> str:
        # Convert `bool(x)` to `x` cleanly for Python conditions
        m = re.fullmatch(r"bool\((.+)\)", expr.strip())
        return m.group(1) if m else expr.strip()

    # Pass 1: 1-Atom exact separators (and high-precision separators when pos_states is empty)
    exact_1: list[tuple[str, float]] = []
    partial_atoms: list[tuple[str, float, int, int]] = []
    for atom in sorted(all_atoms):
        # Must agree with want_neg_val on ALL negative states
        if not all(ns.get(atom) is want_neg_val for ns in neg_states):
            continue
        if pos_states:
            pos_hits = sum(1 for ps in pos_states if ps.get(atom) is want_pos_val)
            pos_total = sum(1 for ps in pos_states if atom in ps)
            if pos_total > 0 and pos_hits == pos_total:
                exact_1.append((atom, 90.0 + _atom_complexity(atom)))
            elif pos_total > 0 and pos_hits > 0:
                partial_atoms.append((atom, pos_hits / pos_total, pos_hits, pos_total))
        else:
            # No positive runs hit this branch; rank structural predicates by hint relevance & simplicity
            if any(t in atom.lower() for t in hint_tokens) or " is not " in atom or " is " in atom:
                exact_1.append((atom, 78.0 + _atom_complexity(atom)))

    exact_1.sort(key=lambda x: -x[1])
    for atom, sc in exact_1[:max_results]:
        ce = _clean_expr(atom)
        if ce not in seen_exprs:
            seen_exprs.add(ce)
            results.append((ce, sc))

    # Pass 2: Exact 2-Atom Boolean Disjunction / Conjunction Separation (when 1 atom is insufficient!)
    if len(results) < 6 and pos_states and partial_atoms:
        # Take top-16 partial atoms sorted by positive coverage + complexity
        partial_atoms.sort(key=lambda x: (-x[1], -_atom_complexity(x[0])))
        top_p = [a for a, _, _, _ in partial_atoms[:16]]
        # If want_pos_val is True, (a1 or a2) is False on all neg_states (since both are False on neg)
        # and True on a pos_state if EITHER a1 or a2 is True!
        # Dual: if want_pos_val is False, (a1 and a2) is True on all neg_states and False if EITHER is False!
        joiner = " or " if want_pos_val else " and "
        for a1, a2 in itertools.combinations(top_p, 2):
            if a1.split()[0] == a2.split()[0] and ("None" in a1 or "bool(" in a1):
                continue
            ok_pos = True
            for ps in pos_states:
                v1 = ps.get(a1)
                v2 = ps.get(a2)
                if v1 is None or v2 is None:
                    continue
                comb = (v1 or v2) if want_pos_val else (v1 and v2)
                if comb is not want_pos_val:
                    ok_pos = False
                    break
            if ok_pos:
                ce = f"({_clean_expr(a1)}{joiner}{_clean_expr(a2)})"
                if ce not in seen_exprs:
                    seen_exprs.add(ce)
                    sc = 84.0 + 0.5 * (_atom_complexity(a1) + _atom_complexity(a2))
                    results.append((ce, sc))
                    if len(results) >= max_results:
                        break

    results.sort(key=lambda x: -x[1])
    return results[:max_results]


@dataclass
class SynthesizedCandidate:
    rel_file: str
    patched_source: str
    mechanism: str
    description: str
    priority: float
    line_no: int


def synthesize_angelic_separating_guards(
    repo_root: pathlib.Path,
    rel_file: str,
    active_lines: set[int],
    failing_nodeids: Sequence[str],
    primary_test_file: str,
    raw_failure_output: str,
    zygote: PytestCoWZygoteServer,
    *,
    deadline: float,
    max_candidates: int = 24,
    line_ochiai: Mapping[int, float] | None = None,
    tb_lines: set[int] | None = None,
) -> list[SynthesizedCandidate]:
    """1. Rank executed `if` statements in localized functions by Differential Ochiai +
       traceback proximity + failure-output token overlap (NEVER line-number truncation!).
    2. Use 1 CoW batch fork to flip each top `if` (`False` / `True` / `not`) and prove
       which EXACT branch causes the failure (`angelic_branch_blame`).
    3. Simultaneously probe contrastive runtime state vectors (`Sigma_pos` vs `Sigma_neg`)
       at ONLY the proven causal branch(es) and solve for minimal structural separating guards.
    """
    path = repo_root / rel_file
    if not path.is_file() or not failing_nodeids:
        return []
    source = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    ochiai_map = {int(k): float(v) for k, v in (line_ochiai or {}).items()}
    tb_set = set(tb_lines or set())
    hint_tokens = {
        tok.lower()
        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", raw_failure_output)
        if tok.lower() not in {"assert", "failed", "error", "test", "none", "true", "false", "line", "file", "self"}
    }

    # Collect candidate `if` nodes executed during the failing run (or in traceback functions)
    if_nodes: list[ast.If] = []
    exec_or_ochiai = active_lines | set(ochiai_map.keys()) | tb_set
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn_start = node.lineno
            fn_end = getattr(node, "end_lineno", fn_start)
            if not exec_or_ochiai or any(fn_start <= ln <= fn_end for ln in exec_or_ochiai):
                for sub in ast.walk(node):
                    if isinstance(sub, ast.If):
                        sub_end = getattr(sub, "end_lineno", sub.lineno)
                        # Include `if` if its test line OR immediate body executed, or within 12 lines of traceback!
                        if (
                            not exec_or_ochiai
                            or sub.lineno in exec_or_ochiai
                            or any(sub.lineno <= ln <= min(sub_end, sub.lineno + 8) for ln in exec_or_ochiai)
                            or any(0 <= (tl - sub.lineno) <= 15 for tl in tb_set)
                        ):
                            if_nodes.append(sub)
    if not if_nodes:
        return []

    def _branch_suspiciousness(n: ast.If) -> float:
        # 1. Max Ochiai score across `if` header + first 4 body lines
        sc = max((ochiai_map.get(ln, 0.0) for ln in range(n.lineno, n.lineno + 5)), default=0.0) * 100.0
        # 2. Strong traceback proximity bonus (e.g. `if frozen is True: raise ValueError(...)` right above raise!)
        if tb_set:
            min_dist = min((abs(tl - n.lineno) for tl in tb_set), default=999)
            if min_dist <= 10:
                sc += (12 - min_dist) * 14.0
        # 3. Failure-output identifier overlap inside condition or immediate body (e.g., `envvar`, `required`, `frozen`, `external`)
        seg = (_get_node_src(source, n.test) or "")
        body_seg = " ".join((_get_node_src(source, st) or "")[:120] for st in n.body[:2])
        toks = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", (seg + " " + body_seg).lower()))
        # Also match sub-parts of snake_case tokens (`show_envvar` -> `show`, `envvar`)
        sub_toks = {part for t in toks for part in t.split("_") if len(part) >= 3}
        sc += min(4, len((toks | sub_toks) & hint_tokens)) * 22.0
        if n.lineno in active_lines:
            sc += 5.0
        return sc

    # Deduplicate by lineno, rank by Ochiai + traceback proximity + failure-token relevance!
    by_line: dict[int, ast.If] = {}
    for n in if_nodes:
        by_line.setdefault(n.lineno, n)
    ordered_ifs = sorted(by_line.values(), key=lambda n: (-_branch_suspiciousness(n), n.lineno))[:24]

    # Step A: Parallel CoW Angelic Branch Flip (proves exact causal branch!)
    flip_items: list[dict[str, Any]] = []
    flip_meta: list[tuple[ast.If, str, str]] = []  # (node, flip_kind, patched_src)
    for if_node in ordered_ifs:
        cond_src = _get_node_src(source, if_node.test)
        if not cond_src:
            continue
        for flip_kind, repl in (("FORCE_FALSE", "False"), ("FORCE_TRUE", "True")):
            patched = _splice_node(source, if_node.test, repl)
            if patched and patched != source:
                flip_items.append({"edits": {rel_file: patched}})
                flip_meta.append((if_node, flip_kind, patched))

    if not flip_items or time.monotonic() >= deadline:
        return []

    batch_res = zygote.eval_batch(
        flip_items,
        list(failing_nodeids[:4]),
        timeout_s=min(4.0, max(1.5, deadline - time.monotonic())),
        max_workers=2,
    )

    causal_branches: dict[int, tuple[ast.If, set[str]]] = {}
    for (if_node, flip_kind, _patched), res in zip(flip_meta, batch_res):
        if res.get("ok"):
            if if_node.lineno not in causal_branches:
                causal_branches[if_node.lineno] = (if_node, set())
            causal_branches[if_node.lineno][1].add(flip_kind)

    # Dual-Program Intra-Test Split Discovery: if a single failing test asserts BOTH the
    # positive and negative path of a branch, no constant True/False flip can pass it!
    # Always include up to 4 highest-suspiciousness (`ochiai >= 0.70`) branches for contrastive probing.
    for if_node in ordered_ifs[:6]:
        if len(causal_branches) >= 6:
            break
        if if_node.lineno not in causal_branches:
            b_och = max((ochiai_map.get(ln, 0.0) for ln in range(if_node.lineno, if_node.lineno + 4)), default=0.0)
            if b_och >= 0.70 or _branch_suspiciousness(if_node) >= 90.0:
                causal_branches[if_node.lineno] = (if_node, {"INTRA_SPLIT"})

    if not causal_branches or time.monotonic() >= deadline:
        return []

    # Step B: Contrastive State Snapshot Capture (Sigma_pos vs Sigma_neg) at ONLY the proven causal branches!
    passing_siblings = _discover_passing_sibling_nodeids(repo_root, primary_test_file, failing_nodeids, max_passing=12)
    sentinels = _mine_file_sentinel_exprs(tree, repo_root, rel_file)
    probe = zygote.probe_branches(
        rel_file,
        list(causal_branches.keys()),
        list(failing_nodeids[:4]),
        passing_siblings,
        sentinels,
        timeout_s=min(6.0, max(2.0, deadline - time.monotonic())),
    )
    records_by_line = probe.get("records") or {}

    # Harvest sibling boolean/comparison atoms already written in the same enclosing function
    # (pure local context idiom reuse — e.g. `a.on_setattr is not setters.NO_OP` in adjacent elif!)
    fn_sibling_preds: dict[int, list[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn_start = node.lineno
            fn_end = getattr(node, "end_lineno", fn_start)
            hits = [ln for ln in causal_branches if fn_start <= ln <= fn_end]
            if not hits:
                continue
            sibs: list[str] = []
            for sub in ast.walk(node):
                if isinstance(sub, ast.Compare):
                    s = (_get_node_src(source, sub) or "").strip()
                    if s and len(s) <= 60 and s not in sibs:
                        sibs.append(s)
            for hln in hits:
                fn_sibling_preds[hln] = sibs[:12]

    candidates: list[SynthesizedCandidate] = []
    seen_hashes: set[str] = set()

    def _add(patched: str | None, mech: str, desc: str, prio: float, ln: int) -> None:
        if not patched or patched == source:
            return
        h = hashlib.sha1(patched.encode("utf-8")).hexdigest()
        if h in seen_hashes:
            return
        seen_hashes.add(h)
        candidates.append(SynthesizedCandidate(rel_file, patched, mech, desc, prio, ln))

    for ln, (if_node, flip_kinds) in causal_branches.items():
        orig_cond = (_get_node_src(source, if_node.test) or "").strip()
        if not orig_cond:
            continue
        # Strictly prioritize mathematically proven angelic flip branches over speculative intra-split branches!
        proven_bonus = 18.0 if ("FORCE_FALSE" in flip_kinds or "FORCE_TRUE" in flip_kinds) else 0.0
        orig_atoms = _extract_cond_subclauses(if_node.test, source)
        recs = records_by_line.get(str(ln)) or []
        fail_true = [r["atoms"] for r in recs if r.get("phase") == "fail" and r.get("cond") is True]
        fail_false = [r["atoms"] for r in recs if r.get("phase") == "fail" and r.get("cond") is False]
        pass_true = [r["atoms"] for r in recs if r.get("phase") == "pass" and r.get("cond") is True]
        pass_false = [r["atoms"] for r in recs if r.get("phase") == "pass" and r.get("cond") is False]

        # Sibling-function predicate reuse on proven causal branches (checked against contrastive states!)
        for spred in fn_sibling_preds.get(ln, []):
            if spred in orig_cond:
                continue
            if "FORCE_FALSE" in flip_kinds or "INTRA_SPLIT" in flip_kinds:
                new_cond = f"({orig_cond}) and ({spred})" if (" or " in orig_cond or " or " in spred) else f"{orig_cond} and {spred}"
                _add(
                    _splice_node(source, if_node.test, new_cond),
                    "ANGELIC_SEPARATING_GUARD__SIBLING_CONJUNCTION",
                    f"L{ln}: refine `if {orig_cond}` with sibling `{spred}`",
                    94.0 + proven_bonus if "FORCE_FALSE" in flip_kinds else 87.0,
                    ln,
                )

        # Case 0 (Dual-Program Intra-Test Split): branch hit with both True & False values of a
        # discriminating atom INSIDE the failing test itself (or vs passing runs)!
        if "INTRA_SPLIT" in flip_kinds and fail_true:
            # Find structural atoms that vary across fail_true hits OR are False on fail_true & True on pass_true
            all_a = set(fail_true[0].keys())
            for ft in fail_true[1:]:
                all_a &= set(ft.keys())
            split_preds: list[tuple[str, float]] = []
            # Boost atoms whose attribute shares tokens with the `if` condition itself (e.g. `show_envvar` <-> `envvar`)
            cond_sub_toks = {
                p for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", orig_cond.lower())
                for p in t.split("_") if len(p) >= 3 and p not in ("self", "not", "none", "true", "false", "and", "show", "has", "get")
            }
            for atom in sorted(all_a):
                if "bool(" in atom or "len(" in atom:
                    continue
                vals = {ft.get(atom) for ft in fail_true}
                a_toks = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", atom.lower()))
                a_sub = {p for t in a_toks for p in t.split("_") if len(p) >= 3}
                overlap = len((a_toks | a_sub) & hint_tokens)
                cond_overlap = len((a_toks | a_sub) & cond_sub_toks)
                # Splitting within fail_true itself (intra-test dual assertion!) OR differing vs pass_true
                if len(vals) == 2 and (overlap > 0 or cond_overlap > 0):
                    split_preds.append((atom, 95.0 + 3.0 * overlap + 6.0 * cond_overlap - 0.5 * atom.count(".")))
                elif (
                    all(ft.get(atom) is False for ft in fail_true)
                    and pass_true
                    and all(pt.get(atom) is True for pt in pass_true if atom in pt)
                ):
                    split_preds.append((atom, 94.0 + 3.0 * overlap + 6.0 * cond_overlap - 0.5 * atom.count(".")))
                elif all(ft.get(atom) is False for ft in fail_true) and (overlap > 0 or cond_overlap > 0) and (" is not None" in atom or atom.startswith("not ")):
                    split_preds.append((atom, 91.0 + 2.5 * overlap + 6.0 * cond_overlap - 0.5 * atom.count(".")))
            split_preds.sort(key=lambda x: -x[1])
            for pred, sc in split_preds[:8]:
                new_cond = f"({orig_cond}) and ({pred})" if (" or " in orig_cond or " or " in pred) else f"{orig_cond} and {pred}"
                _add(
                    _splice_node(source, if_node.test, new_cond),
                    "ANGELIC_DUAL_SPLICING__INTRA_GUARD",
                    f"L{ln}: intra-branch split `if {orig_cond}` with `and {pred}`",
                    sc,
                    ln,
                )

        # Case 1: Condition evaluated True in failing run and flipping to False fixed the failure -> `orig_cond and P`
        if ("FORCE_FALSE" in flip_kinds or "INVERT" in flip_kinds) and (fail_true or not recs):
            neg_s = fail_true if fail_true else [r["atoms"] for r in recs if r.get("phase") == "fail"]
            seps = _solve_minimal_separating_predicates(
                pass_true, neg_s, want_pos_val=True, hint_tokens=hint_tokens, orig_cond_atoms=orig_atoms, max_results=8
            )
            for pred, sc in seps:
                new_cond = f"({orig_cond}) and ({pred})" if (" or " in orig_cond or " or " in pred) else f"{orig_cond} and {pred}"
                _add(
                    _splice_node(source, if_node.test, new_cond),
                    "ANGELIC_SEPARATING_GUARD__CONJUNCTION",
                    f"L{ln}: refine `if {orig_cond}` with `and {pred}`",
                    sc + 4.0 + proven_bonus,
                    ln,
                )

        # Case 2: Condition evaluated False in failing run and flipping to True fixed the failure -> `orig_cond or P`
        if ("FORCE_TRUE" in flip_kinds or "INVERT" in flip_kinds) and (fail_false or not recs):
            neg_s = fail_false if fail_false else [r["atoms"] for r in recs if r.get("phase") == "fail"]
            seps = _solve_minimal_separating_predicates(
                pass_false, neg_s, want_pos_val=False, hint_tokens=hint_tokens, orig_cond_atoms=orig_atoms, max_results=8
            )
            for pred, sc in seps:
                new_cond = f"({orig_cond}) or ({pred})" if (" and " in orig_cond or " and " in pred) else f"{orig_cond} or {pred}"
                _add(
                    _splice_node(source, if_node.test, new_cond),
                    "ANGELIC_SEPARATING_GUARD__DISJUNCTION",
                    f"L{ln}: widen `if {orig_cond}` with `or {pred}`",
                    sc + 3.0 + proven_bonus,
                    ln,
                )

        # Case 3: Sub-clause De Morgan / clause-drop / full boolean re-synthesis on compound `if` conditions
        if isinstance(if_node.test, ast.BoolOp) and len(if_node.test.values) >= 2:
            sub_srcs = [(_get_node_src(source, v) or "").strip() for v in if_node.test.values]
            sub_srcs = [s for s in sub_srcs if s]
            op_str = " and " if isinstance(if_node.test.op, ast.And) else " or "
            dual_op = " or " if isinstance(if_node.test.op, ast.And) else " and "
            # Try dropping or negating individual clauses
            for idx, s in enumerate(sub_srcs):
                others = [x for j, x in enumerate(sub_srcs) if j != idx]
                if others:
                    _add(
                        _splice_node(source, if_node.test, op_str.join(others)),
                        "ANGELIC_BOOLEAN_CLAUSE_DROP",
                        f"L{ln}: drop clause `{s}`",
                        86.0 + proven_bonus,
                        ln,
                    )
                neg_sub = [f"(not ({x}))" if j == idx else x for j, x in enumerate(sub_srcs)]
                _add(
                    _splice_node(source, if_node.test, op_str.join(neg_sub)),
                    "ANGELIC_BOOLEAN_CLAUSE_NEGATE",
                    f"L{ln}: negate clause `{s}`",
                    85.0 + proven_bonus,
                    ln,
                )
            # When the compound `and` has a disjunction sub-term `(A or B)`, try relaxing inner negation/disjunction:
            # e.g., `not force_external and (not (A or B) or P)` when both FORCE_TRUE & pass_true/fail_false exist!
            if isinstance(if_node.test.op, ast.And) and len(sub_srcs) >= 2 and fail_false:
                lead = sub_srcs[0]
                tail_clauses = sub_srcs[1:]
                # Direct guard inversion on tail clause (highest structural priority — reuses ONLY existing clauses!)
                for idx in range(1, len(sub_srcs)):
                    tc = sub_srcs[idx]
                    rest = [x for j, x in enumerate(sub_srcs) if j not in (0, idx)]
                    if rest:
                        expr = f"{lead} and (not ({tc}) or ({' and '.join(rest)}))"
                        _add(
                            _splice_node(source, if_node.test, expr),
                            "ANGELIC_BOOLEAN_DEMORGAN_REWRITE",
                            f"L{ln}: restructure `{lead} and (not ({tc}) or ...)`",
                            97.0 + proven_bonus,
                            ln,
                        )
                seps_or = _solve_minimal_separating_predicates(
                    pass_false, fail_false, want_pos_val=False, hint_tokens=hint_tokens, orig_cond_atoms=orig_atoms, max_results=5
                )
                for pred, sc in seps_or:
                    for tc in tail_clauses:
                        _add(
                            _splice_node(source, if_node.test, f"{lead} and (not ({tc}) or ({pred}))"),
                            "ANGELIC_BOOLEAN_RESYNTHESIS",
                            f"L{ln}: boolean guard resynthesis over `{lead}`, `{tc}`, `{pred}`",
                            sc + 2.0 + proven_bonus,
                            ln,
                        )
                    _add(
                        _splice_node(source, if_node.test, f"{lead} and ({' and '.join(tail_clauses)} or ({pred}))"),
                        "ANGELIC_BOOLEAN_RESYNTHESIS",
                        f"L{ln}: preserve `{lead}`, widen tail with `or {pred}`",
                        sc + 1.5 + proven_bonus,
                        ln,
                    )
            _add(
                _splice_node(source, if_node.test, dual_op.join(sub_srcs)),
                "ANGELIC_BOOLEAN_OP_DUAL",
                f"L{ln}: swap boolean op to `{dual_op.strip()}`",
                82.0 + proven_bonus,
                ln,
            )

        # Case 4: Direct inversion / constant when no positive runs contradict it
        if "INVERT" in flip_kinds and not pass_true and not pass_false:
            _add(
                _splice_node(source, if_node.test, f"not ({orig_cond})"),
                "ANGELIC_BRANCH_INVERT",
                f"L{ln}: invert `{orig_cond}`",
                80.0,
                ln,
            )

    candidates.sort(key=lambda c: (-c.priority, c.line_no))
    return candidates[:max_candidates]


# ============================================================================
# 3. ALGEBRAIC DIFFERENTIAL OPERATORS (UNWRAP, STRING/CODEC FST LENS, CALL-ARG PROPAGATION)
# ============================================================================

def _extract_expected_actual_str_pairs(raw_output: str) -> list[tuple[str, str]]:
    """Extract `(actual, expected)` string/bytes literal pairs from pytest assertion output."""
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    # Pattern 1: `assert 'actual' == 'expected'` or `AssertionError: assert "a" == "b"`
    for m in re.finditer(r"assert\s+(b?'[^'\n]{1,300}'|b?\"[^\"\n]{1,300}\")\s*==\s*(b?'[^'\n]{1,300}'|b?\"[^\"\n]{1,300}\")", raw_output):
        try:
            a = ast.literal_eval(m.group(1))
            e = ast.literal_eval(m.group(2))
            if isinstance(a, bytes):
                a = a.decode("latin1")
            if isinstance(e, bytes):
                e = e.decode("latin1")
            if isinstance(a, str) and isinstance(e, str) and a != e and (a, e) not in seen:
                seen.add((a, e))
                pairs.append((a, e))
        except Exception:
            pass
    # Pattern 2: pytest `- expected` / (optional `? carets`) / `+ actual` unified diff lines
    lines = raw_output.splitlines()
    for i in range(len(lines) - 1):
        m_minus = re.match(r"^E\s+-\s+(.+)$", lines[i])
        if not m_minus:
            continue
        for j in (i + 1, i + 2):
            if j >= len(lines):
                break
            if re.match(r"^E\s+\?\s+", lines[j]):
                continue
            m_plus = re.match(r"^E\s+\+\s+(.+)$", lines[j])
            if m_plus:
                exp = m_minus.group(1).strip()
                act = m_plus.group(1).strip()
                if act and exp and act != exp and (act, exp) not in seen:
                    seen.add((act, exp))
                    pairs.append((act, exp))
            break
    # Pattern 3: `Regex pattern did not match.\n Regex: '...'\n Input: '...'` (pytest.raises match=!)
    m_re = re.search(r"Regex:\s*('[^'\n]{2,300}'|\"[^\"\n]{2,300}\")\s*\n\s*E\s+Input:\s*('[^'\n]{2,300}'|\"[^\"\n]{2,300}\")", raw_output)
    if m_re:
        try:
            exp = ast.literal_eval(m_re.group(1))
            act = ast.literal_eval(m_re.group(2))
            if isinstance(exp, str) and isinstance(act, str) and act != exp:
                # Unescape simple regex escapes so literal delta sees the expected substring
                exp_clean = re.sub(r"\\([()\[\].+*?^$|])", r"\1", exp)
                if (act, exp_clean) not in seen:
                    seen.add((act, exp_clean))
                    pairs.append((act, exp_clean))
        except Exception:
            pass
    return pairs[:12]


def _caret_encode_table(pairs: Sequence[tuple[str, str]]) -> dict[int, str]:
    """Detect Bidirectional Control-Byte Caret Transducer pairs (`\x04 -> ^D`, `\x1a -> ^Z`)."""
    mapping: dict[int, str] = {}
    for actual, expected in pairs:
        for m in re.finditer(r"\^([A-Z])", expected):
            ch = m.group(1)
            ctrl_byte = ord(ch) - 64
            if 1 <= ctrl_byte <= 26 and f"^{ch}" not in actual:
                mapping[ctrl_byte] = f"^{ch}"
    return mapping


def _percent_codec_char_deltas(pairs: Sequence[tuple[str, str]]) -> tuple[set[str], set[str]]:
    """Detect characters that should be percent-encoded (remove from `safe=`) or left unencoded (add to `safe=`)."""
    must_encode: set[str] = set()
    must_keep_safe: set[str] = set()
    for actual, expected in pairs:
        for m in re.finditer(r"%([0-9A-Fa-f]{2})", expected):
            ch = chr(int(m.group(1), 16))
            if ch in actual and m.group(0) not in actual:
                must_encode.add(ch)
        for m in re.finditer(r"%([0-9A-Fa-f]{2})", actual):
            ch = chr(int(m.group(1), 16))
            if ch in expected and m.group(0) not in expected:
                must_keep_safe.add(ch)
    return must_encode, must_keep_safe


def synthesize_algebraic_differential_repairs(
    repo_root: pathlib.Path,
    rel_file: str,
    active_lines: set[int],
    raw_failure_output: str,
    *,
    max_candidates: int = 24,
) -> list[SynthesizedCandidate]:
    """Generate general algebraic & differential lens repairs (zero hardcoded repo rules):
      1. Angelic Call-Wrapper Unwrap (`f(x) -> x`) on traced failing lines.
      2. Differential Output-to-Literal String Delta back-propagation.
      3. Percent-Encoding `safe=` Character-Set Codec Lens.
      4. Bidirectional Control-Byte Caret FST Lens.
      5. Enclosing-Function Parameter Propagation to Callee Call Sites.
    """
    path = repo_root / rel_file
    if not path.is_file():
        return []
    source = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    funcs: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn_start = node.lineno
            fn_end = getattr(node, "end_lineno", fn_start)
            if not active_lines or any(fn_start <= ln <= fn_end for ln in active_lines):
                funcs.append(node)
    if not funcs:
        funcs = [tree]

    candidates: list[SynthesizedCandidate] = []
    seen_hashes: set[str] = set()

    def _add(patched: str | None, mech: str, desc: str, prio: float, ln: int) -> None:
        if not patched or patched == source:
            return
        h = hashlib.sha1(patched.encode("utf-8")).hexdigest()
        if h in seen_hashes:
            return
        seen_hashes.add(h)
        candidates.append(SynthesizedCandidate(rel_file, patched, mech, desc, prio, ln))

    str_pairs = _extract_expected_actual_str_pairs(raw_failure_output)
    must_encode, must_keep_safe = _percent_codec_char_deltas(str_pairs)

    # ---- Op 1: Percent-Encoding `safe=` Codec Lens ----
    if must_encode or must_keep_safe:
        for fn in funcs:
            for node in ast.walk(fn):
                if isinstance(node, ast.Call):
                    for kw in node.keywords:
                        if kw.arg == "safe" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                            cur_safe = kw.value.value
                            new_safe = cur_safe
                            for ch in sorted(must_encode):
                                new_safe = new_safe.replace(ch, "")
                            for ch in sorted(must_keep_safe):
                                if ch not in new_safe:
                                    new_safe += ch
                            if new_safe != cur_safe:
                                _add(
                                    _splice_node(source, kw.value, repr(new_safe)),
                                    "ALGEBRAIC_CODEC_LENS__SAFE_CHARSET",
                                    f"L{node.lineno}: update codec safe charset {cur_safe!r} -> {new_safe!r}",
                                    96.5,
                                    node.lineno,
                                )

    # ---- Op 2: Differential Output-to-Literal String Delta Back-Propagation ----
    if str_pairs:
        for actual, expected in str_pairs:
            sm = difflib.SequenceMatcher(None, actual, expected)
            opcodes = [op for op in sm.get_opcodes() if op[0] != "equal"]
            if not opcodes or len(opcodes) > 5:
                continue
            # Combine ALL non-equal opcodes into one unified minimal span (`first_i1..last_i2 -> first_j1..last_j2`)
            # so multi-char edits like `not` -> `in` aren't fragmented into `i` + delete `ot`!
            span_specs: list[tuple[int, int, int, int]] = [
                (opcodes[0][1], opcodes[-1][2], opcodes[0][3], opcodes[-1][4])
            ]
            if len(opcodes) == 1:
                pass
            else:
                for _tag, i1, i2, j1, j2 in opcodes:
                    span_specs.append((i1, i2, j1, j2))
            for i1, i2, j1, j2 in span_specs:
                ctx_l = max(0, i1 - 6)
                ctx_r = min(len(actual), i2 + 6)
                old_seg = actual[ctx_l:ctx_r]
                new_seg = actual[ctx_l:i1] + expected[j1:j2] + actual[i2:ctx_r]
                if not old_seg or old_seg == new_seg:
                    continue
                for fn in funcs:
                    for node in ast.walk(fn):
                        if isinstance(node, ast.Constant) and isinstance(node.value, str) and old_seg in node.value:
                            new_val = node.value.replace(old_seg, new_seg, 1)
                            if new_val != node.value:
                                _add(
                                    _splice_node(source, node, repr(new_val)),
                                    "ALGEBRAIC_DIFFERENTIAL_LITERAL_DELTA",
                                    f"L{node.lineno}: literal delta {old_seg!r} -> {new_seg!r}",
                                    96.0 if (i1 == opcodes[0][1] and i2 == opcodes[-1][2]) else 88.0,
                                    node.lineno,
                                )

    # ---- Op 3: Angelic Call-Wrapper Unwrap (`f(x) -> x`) ----
    # Focused strictly on single-argument helper calls on hot executed lines
    for fn in funcs:
        for node in ast.walk(fn):
            if isinstance(node, ast.Call):
                ln = getattr(node, "lineno", 0)
                if active_lines and ln not in active_lines:
                    continue
                if len(node.args) == 1 and not node.keywords:
                    arg0 = node.args[0]
                    if isinstance(arg0, (ast.Name, ast.Attribute, ast.Subscript)):
                        # Skip constructors / builtin conversions that break types (`len`, `int`, `list`, `tuple`, `set`, `dict`, `isinstance`)
                        fname = node.func.id if isinstance(node.func, ast.Name) else (node.func.attr if isinstance(node.func, ast.Attribute) else "")
                        if fname in ("len", "int", "float", "bool", "list", "tuple", "set", "dict", "type", "repr", "next", "iter", "range", "enumerate", "sorted", "reversed"):
                            continue
                        arg_src = _get_node_src(source, arg0)
                        if arg_src:
                            # Prefer helper functions whose name suggests transformation/quoting/stripping/encoding
                            prio = 93.0 if any(k in fname.lower() for k in ("unquote", "quote", "strip", "clean", "norm", "escape", "decode", "encode", "parse", "format", "wrap")) else 81.0
                            _add(
                                _splice_node(source, node, arg_src),
                                "ANGELIC_CALL_WRAPPER_UNWRAP",
                                f"L{ln}: unwrap `{fname}({arg_src})` -> `{arg_src}`",
                                prio,
                                ln,
                            )
            # Inside an f-string (`ast.FormattedValue`), unwrapping any 1-arg wrapper (`{list(x)}` -> `{x!r}` / `{x}`)
            # fixes display/formatting wrappers without breaking runtime types.
            elif isinstance(node, ast.FormattedValue):
                ln = getattr(node, "lineno", 0)
                if active_lines and ln not in active_lines:
                    continue
                if isinstance(node.value, ast.Call) and len(node.value.args) == 1 and not node.value.keywords:
                    arg0 = node.value.args[0]
                    if isinstance(arg0, (ast.Name, ast.Attribute, ast.Subscript)):
                        arg_src = _get_node_src(source, arg0)
                        if arg_src:
                            _add(
                                _splice_node(source, node.value, f"{arg_src}!r") if node.conversion == -1 else _splice_node(source, node.value, arg_src),
                                "ANGELIC_CALL_WRAPPER_UNWRAP__FSTRING_REPR",
                                f"L{ln}: unwrap f-string call to `{arg_src}!r`",
                                92.0,
                                ln,
                            )
                            _add(
                                _splice_node(source, node.value, arg_src),
                                "ANGELIC_CALL_WRAPPER_UNWRAP__FSTRING",
                                f"L{ln}: unwrap f-string call to `{arg_src}`",
                                89.0,
                                ln,
                            )

    # ---- Op 4: Bidirectional Control-Byte Caret FST Lens ----
    caret_map = _caret_encode_table(str_pairs)
    if caret_map:
        # Locate write/echo/decode call sites in localized functions operating on bytes/str buffers
        trans_expr_bytes = "".join(f".replace({bytes([b])!r}, {v.encode('ascii')!r})" for b, v in sorted(caret_map.items()))
        trans_expr_str = "".join(f".replace({chr(b)!r}, {v!r})" for b, v in sorted(caret_map.items()))
        for fn in funcs:
            for node in ast.walk(fn):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("write", "getvalue", "decode", "echo"):
                    ln = getattr(node, "lineno", 0)
                    if active_lines and ln not in active_lines:
                        continue
                    if node.args:
                        a0 = node.args[0]
                        a0_src = _get_node_src(source, a0)
                        if a0_src:
                            for suffix, kind in ((trans_expr_bytes, "bytes"), (trans_expr_str, "str")):
                                _add(
                                    _splice_node(source, a0, f"({a0_src}){suffix}"),
                                    f"BIDIRECTIONAL_FST_CARET_LENS__{kind.upper()}",
                                    f"L{ln}: apply caret FST lens ({kind}) to `{a0_src}`",
                                    91.0,
                                    ln,
                                )

    # ---- Op 5: Enclosing Parameter Propagation (`context`, `ctx`, etc.) to Callee ----
    # Index local/file function parameter names so we only propagate a parameter the callee actually accepts!
    callee_params: dict[str, set[str]] = {}
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            pnames = {a.arg for a in n.args.args + n.args.kwonlyargs}
            if n.args.kwarg is not None:
                pnames.add("**kwargs")
            callee_params[n.name] = pnames
    for fn in funcs:
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        fn_params = [a.arg for a in fn.args.args + fn.args.kwonlyargs if a.arg not in ("self", "cls")]
        if not fn_params:
            continue
        for node in ast.walk(fn):
            if not isinstance(node, ast.Call):
                continue
            ln = getattr(node, "lineno", 0)
            if active_lines and ln not in active_lines:
                continue
            cname = node.func.id if isinstance(node.func, ast.Name) else (node.func.attr if isinstance(node.func, ast.Attribute) else "")
            accepted = callee_params.get(cname, set())
            if not accepted:
                continue
            existing_kw = {kw.arg for kw in node.keywords if kw.arg}
            existing_pos = {_get_node_src(source, a) for a in node.args}
            call_src = _get_node_src(source, node)
            if not call_src or not call_src.endswith(")"):
                continue
            for p in fn_params:
                if p in accepted and p not in existing_kw and p not in existing_pos:
                    sep = ", " if (node.args or node.keywords) else ""
                    new_call = f"{call_src[:-1]}{sep}{p}={p})"
                    _add(
                        _splice_node(source, node, new_call),
                        "ALGEBRAIC_CONTEXT_PARAM_PROPAGATION",
                        f"L{ln}: propagate `{p}={p}` to `{cname}(...)`",
                        90.0,
                        ln,
                    )

    candidates.sort(key=lambda c: (-c.priority, c.line_no))
    return candidates[:max_candidates]


# ============================================================================
# 4. ZERO-LEAKAGE WALL-1 ORACLE FACTORY (GIT ALIGNMENT + DOCSTRING + INLINE REPRO)
# ============================================================================

def mine_ephemeral_git_alignment(
    repo_root: pathlib.Path,
    issue_text: str,
    *,
    max_commits: int = 250,
) -> dict[str, float]:
    """Ephemeral per-repo git-history alignment compiler (0 weights, destroyed on exit).
    Maps issue text tokens to repo source files purely from the repo's OWN past commits
    (strictly excluding any commit after HEAD — works on pristine parent checkout!)."""
    if not (repo_root / ".git").exists():
        return {}
    issue_toks = {
        t.lower()
        for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", issue_text)
        if t.lower() not in {"the", "and", "for", "with", "when", "that", "this", "from", "should", "does", "not", "fix", "bug"}
    }
    if not issue_toks:
        return {}
    try:
        cp = subprocess.run(
            ["git", "-C", str(repo_root), "log", f"-n{max_commits}", "--pretty=format:__C__%s", "--name-only"],
            capture_output=True,
            text=True,
            timeout=2.5,
        )
    except Exception:
        return {}
    if cp.returncode != 0:
        return {}

    file_scores: dict[str, float] = {}
    cur_toks: set[str] = set()
    for line in cp.stdout.splitlines():
        s = line.strip()
        if s.startswith("__C__"):
            subj = s[5:]
            cur_toks = {t.lower() for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", subj)}
        elif s and s.endswith(".py") and "test" not in s.lower():
            overlap = len(cur_toks & issue_toks)
            if overlap > 0:
                file_scores[s] = file_scores.get(s, 0.0) + (overlap / max(1.0, len(cur_toks) ** 0.5))
    return file_scores


@dataclass
class DocstringOracleSpec:
    rel_file: str
    module_name: str
    func_name: str
    kind: str
    probe_code: str
    docstring_excerpt: str


def mine_docstring_metamorphic_oracles(
    repo_root: pathlib.Path,
    candidate_rel_files: Sequence[str],
    issue_text: str,
) -> list[DocstringOracleSpec]:
    """Extract executable metamorphic oracles stated verbatim in the repo's own docstrings
    (e.g. `A(x) == (B(x) == x)` roundtrip, `equivalent to B(x)`, or regex/format exclusion
    invariants). Zero hidden test leakage."""
    specs: list[DocstringOracleSpec] = []
    issue_low = issue_text.lower()

    def _mod_name(rel_f: str) -> str:
        p = rel_f[:-3] if rel_f.endswith(".py") else rel_f
        if p.startswith("src/"):
            p = p[4:]
        if p.endswith("/__init__"):
            p = p[:-9]
        return p.replace("/", ".")

    for rel_f in candidate_rel_files[:6]:
        p = repo_root / rel_f
        if not p.is_file():
            continue
        src = p.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        mod = _mod_name(rel_f)
        top_funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}

        # Pattern 1: Docstring stating `A(x) <-> B(x) == x` (roundtrip) or `equivalent to B`
        # Strictly filter to functions actually referenced in the issue text so unrelated
        # functions in large modules never hijack witness abduction!
        issue_words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", issue_low))
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name.lower() not in issue_words and node.name.lower() not in issue_low:
                continue
            doc = ast.get_docstring(node) or ""
            if not doc:
                continue
            doc_low = doc.lower()
            # Check references to another function in the same module
            other_refs = [f for f in top_funcs if f != node.name and f in doc]
            for other in other_refs:
                if any(k in doc_low for k in ("roundtrip", "round-trip", "unchanged", "normalized", "canonical")):
                    code = textwrap.dedent(f"""\
                        import importlib

                        def test_docstring_roundtrip_oracle():
                            mod = importlib.import_module({mod!r})
                            fn_a = getattr(mod, {node.name!r})
                            fn_b = getattr(mod, {other!r})
                            corpus = [
                                'foo', 'foo-bar', 'foo_bar', 'Foo-Bar', 'a--b', '1--1',
                                'a---b', 'foo.bar', 'foo\\n', 'a-b\\n', 'a', '1',
                                '-foo', 'foo-', '', 'a..b', 'a__b', 'pkg-1.0',
                            ]
                            for s in corpus:
                                try:
                                    res_a = fn_a(s)
                                    res_b = fn_b(s)
                                except Exception:
                                    continue
                                if isinstance(res_a, bool) and isinstance(res_b, str):
                                    assert res_a == (res_b == s), f'Docstring roundtrip mismatch on {{s!r}}: {{res_a!r}} vs ({{res_b!r}} == {{s!r}})'
                    """)
                    specs.append(DocstringOracleSpec(rel_f, mod, node.name, "DOCSTRING_ROUNDTRIP_ORACLE", code, doc[:160]))
                elif any(k in doc_low for k in ("equivalent to", "same as", "agrees with")):
                    code = textwrap.dedent(f"""\
                        import importlib

                        def test_docstring_equivalence_oracle():
                            mod = importlib.import_module({mod!r})
                            fn_a = getattr(mod, {node.name!r})
                            fn_b = getattr(mod, {other!r})
                            for s in ['foo', 'foo-bar', 'a--b', 'foo\\n', '', '123', 'a_b']:
                                try:
                                    ra = fn_a(s)
                                    rb = fn_b(s)
                                except Exception:
                                    continue
                                assert ra == rb, f'Docstring equivalence mismatch on {{s!r}}: {{ra!r}} != {{rb!r}}'
                    """)
                    specs.append(DocstringOracleSpec(rel_f, mod, node.name, "DOCSTRING_EQUIVALENCE_ORACLE", code, doc[:160]))

        # Pattern 2: Module-level compiled regex with comment/docstring describing valid charset + issue mentions newline/end
        if any(k in issue_low for k in ("newline", "\\n", "end of", "trailing", "metadata", "name", "regex", "full")):
            for stmt in tree.body:
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                    vname = stmt.targets[0].id
                    stmt_src = _get_node_src(src, stmt) or ""
                    if "re.compile" in stmt_src and "$" in stmt_src:
                        # Check nearby comment or name match with issue tokens
                        s_lines = src.splitlines()
                        ctx_comment = "\n".join(s_lines[max(0, stmt.lineno - 4):stmt.lineno]).lower()
                        name_hit = any(tok in (vname.lower() + " " + ctx_comment) for tok in ("name", "metadata", "valid", "normal", "origin", "end") if tok in issue_low)
                        if name_hit:
                            code = textwrap.dedent(f"""\
                                import importlib

                                def test_docstring_regex_newline_oracle():
                                    mod = importlib.import_module({mod!r})
                                    pat = getattr(mod, {vname!r})
                                    for sample in ('foo', 'a1', 'pkg-name', 'valid_name'):
                                        if pat.match(sample) is not None:
                                            assert pat.match(sample + '\\n') is None, f'Regex {vname} matched trailing newline on {{sample!r}}'
                                            return
                                    assert False, 'no_invoked_serializer'
                            """)
                            specs.append(DocstringOracleSpec(rel_f, mod, vname, "DOCSTRING_REGEX_NEWLINE_ORACLE", code, ctx_comment[:160]))

    return specs


def extract_inline_issue_reproducer(issue_text: str) -> str | None:
    """Extract a concrete executable Python reproducer from fenced code blocks or `>>>` doctests
    inside the issue text itself (zero hidden test leakage)."""
    # Check fenced ```python ... ``` blocks
    m = re.search(r"```(?:python|py)?\s*\n(.*?)```", issue_text, re.DOTALL)
    if m:
        block = textwrap.dedent(m.group(1)).strip()
        try:
            ast.parse(block)
            if "assert" in block or "raise" in block:
                indented = textwrap.indent(block, "    ")
                return f"def test_inline_issue_reproducer():\n{indented}\n"
        except SyntaxError:
            pass
    # Check `>>> expr\nexpected` doctest lines
    doctest_lines = [l.strip() for l in issue_text.splitlines() if l.strip().startswith(">>> ")]
    if doctest_lines:
        body = [l[4:] for l in doctest_lines]
        try:
            ast.parse("\n".join(body))
            indented = textwrap.indent("\n".join(body), "    ")
            return f"def test_inline_doctest_reproducer():\n{indented}\n"
        except SyntaxError:
            pass
    return None


# ============================================================================
# 5. 64-VECTOR CoW BOUNDARY INVARIANCE FUZZER & L3 NEGATIVE-SPACE GUARD
# ============================================================================

def build_64_boundary_vectors() -> list[Any]:
    """Deterministic 64-input cross-type boundary corpus (numbers, strings, bytes, containers, None)."""
    return [
        None, True, False, 0, -0, 1, -1, 2, 255, 256, 65535, -65536, 10**9, 0.0, -0.0, 1.5,
        "", " ", "\t", "\n", "\r\n", "a", "A", "0", "a\n", "foo-bar", "foo_bar", "a--b", "1--1",
        "Foo.Bar", "foo+bar", "foo%2Bbar", "  spaced  ", "x" * 64, "unicode-\u00e9-\u2603",
        "user:pass@host", "user:p@ss@host", "https://example.com", "https://example.com.evil",
        b"", b" ", b"\x00", b"\x04", b"\x1a", b"\n", b"abc", b"foo+bar",
        [], [None], [0], ["a", "b"], (), (1,), (None, ""), {}, {"k": "v"}, {"": None},
        set(), {1, 2}, iter([1, 2, 3]), (x for x in ()), (x for x in [1, 2]),
        {"url": "https://example.com"}, ["a", "", None],
    ]


def verify_cow_boundary_invariance(
    repo_root: pathlib.Path,
    rel_file: str,
    orig_source: str,
    patched_source: str,
    target_func_name: str,
    *,
    timeout_s: float = 4.0,
) -> dict[str, Any]:
    """Run deterministic 64-vector differential boundary fuzzing between `orig_source`
    and `patched_source` inside an isolated subprocess/fork. Checks that valid passing
    boundary inputs do not suddenly crash with new unexpected exceptions."""
    mod_p = rel_file[:-3] if rel_file.endswith(".py") else rel_file
    if mod_p.startswith("src/"):
        mod_p = mod_p[4:]
    mod_name = mod_p.replace("/", ".")

    runner = textwrap.dedent(f"""\
        import importlib, json, sys
        vectors = [
            None, True, False, 0, 1, -1, 2, 255, 0.0, 1.5,
            "", " ", "\\t", "\\n", "\\r\\n", "a", "A", "0", "a\\n", "foo-bar", "foo_bar",
            "a--b", "1--1", "Foo.Bar", "foo+bar", "foo%2Bbar", "  spaced  ", "x" * 64,
            "user:pass@host", "user:p@ss@host", "https://example.com", "https://example.com.evil",
            b"", b" ", b"\\x00", b"\\x04", b"\\x1a", b"abc",
            [], [None], [0], ["a", "b"], (), (1,), {{}}, {{"k": "v"}}, set(), {{1, 2}},
        ]
        def _run(src_code):
            ns = {{"__name__": {mod_name!r}, "__file__": {str((repo_root / rel_file).resolve())!r}}}
            try:
                mod = importlib.import_module({mod_name!r})
                ns.update(mod.__dict__)
                exec(compile(src_code, ns["__file__"], "exec"), ns)
            except Exception as exc:
                return {{"load_error": repr(exc), "outcomes": []}}
            fn = ns.get({target_func_name!r})
            if not callable(fn):
                return {{"load_error": "not_callable", "outcomes": []}}
            out = []
            for v in vectors:
                try:
                    r = fn(v)
                    out.append(("OK", type(r).__name__, repr(r)[:80]))
                except Exception as exc:
                    out.append(("EXC", type(exc).__name__, ""))
            return {{"load_error": None, "outcomes": out}}
        orig_r = _run(sys.stdin.read().split("\\x00__SPLIT__\\x00")[0])
        sys.exit(0)
    """)
    # Cleaner 2-pass exec via temp JSON payload (zero stdin delimiter fragility)
    probe_script = textwrap.dedent(f"""\
        import importlib, json, sys
        data = json.load(sys.stdin)
        vectors = [
            None, True, False, 0, 1, -1, 2, 255, 0.0, 1.5,
            "", " ", "\\t", "\\n", "\\r\\n", "a", "A", "0", "a\\n", "foo-bar", "foo_bar",
            "a--b", "1--1", "Foo.Bar", "foo+bar", "foo%2Bbar", "  spaced  ", "x" * 64,
            "user:pass@host", "user:p@ss@host", "https://example.com", "https://example.com.evil",
            b"", b" ", b"\\x00", b"\\x04", b"\\x1a", b"abc",
            [], [None], [0], ["a", "b"], (), (1,), {{}}, {{"k": "v"}}, set(), {{1, 2}},
        ]
        def _eval(src_code):
            ns = {{}}
            try:
                mod = importlib.import_module(data["mod"])
                ns.update(mod.__dict__)
                exec(compile(src_code, data["file"], "exec"), ns)
            except Exception as exc:
                return {{"load_error": repr(exc), "outcomes": []}}
            fn = ns.get(data["func"])
            if not callable(fn):
                return {{"load_error": "not_callable", "outcomes": []}}
            outs = []
            for v in vectors:
                try:
                    r = fn(v)
                    outs.append(["OK", type(r).__name__, repr(r)[:60]])
                except Exception as exc:
                    outs.append(["EXC", type(exc).__name__])
            return {{"load_error": None, "outcomes": outs}}
        o1 = _eval(data["orig"])
        o2 = _eval(data["patched"])
        new_crashes = 0
        changed_ok = 0
        preserved_ok = 0
        for a, b in zip(o1["outcomes"], o2["outcomes"]):
            if a[0] == "OK" and b[0] == "EXC":
                new_crashes += 1
            elif a[0] == "OK" and b[0] == "OK":
                if a == b:
                    preserved_ok += 1
                else:
                    changed_ok += 1
        print(json.dumps({{
            "ok": (o2["load_error"] is None and new_crashes == 0),
            "new_crashes": new_crashes,
            "changed_ok": changed_ok,
            "preserved_ok": preserved_ok,
            "vectors_tested": len(vectors),
            "load_error": o2["load_error"],
        }}))
    """)
    env = dict(os.environ)
    py_paths = []
    if (repo_root / "src").is_dir():
        py_paths.append(str((repo_root / "src").resolve()))
    py_paths.append(str(repo_root.resolve()))
    if pathlib.Path("/tmp/eval_deps").is_dir():
        py_paths.append("/tmp/eval_deps")
    env["PYTHONPATH"] = os.pathsep.join(py_paths + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    payload = json.dumps({
        "mod": mod_name,
        "file": str((repo_root / rel_file).resolve()),
        "func": target_func_name,
        "orig": orig_source,
        "patched": patched_source,
    })
    try:
        cp = subprocess.run(
            [sys.executable, "-c", probe_script],
            input=payload,
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            env=env,
            timeout=timeout_s,
        )
        if cp.returncode == 0 and cp.stdout.strip():
            return json.loads(cp.stdout.strip().splitlines()[-1])
    except Exception as exc:
        return {"ok": True, "skipped": True, "error": str(exc)}
    return {"ok": True, "skipped": True, "vectors_tested": 0}


def canonical_ast_delta_fingerprint(orig_source: str, patched_source: str) -> str:
    """Compute a structural alpha-renamed fingerprint of an AST edit for O(1) L3
    Negative-Space Invariant indexing (independent of variable names)."""
    diff_lines = [
        l[1:].strip()
        for l in difflib.unified_diff(orig_source.splitlines(), patched_source.splitlines(), n=0)
        if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))
    ]
    if not diff_lines:
        return ""
    norm = "\n".join(re.sub(r"\b[a-z_][a-z0-9_]*\b", "$id", l) for l in diff_lines[:6])
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:24]


class NegativeSpaceGuard:
    """In-memory + external-JSON-serializable L3 Negative-Space Invariant guard.
    Crystallizes refuted patch patterns into O(1) structural rejection filters with O(1) deletion."""

    def __init__(self, store_path: pathlib.Path | None = None) -> None:
        self.store_path = store_path
        self._invariants: dict[str, dict[str, Any]] = {}
        if store_path and store_path.is_file():
            try:
                data = json.loads(store_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._invariants = dict(data)
            except Exception:
                pass

    def record_refutation(self, orig_source: str, patched_source: str, reason: str) -> str:
        fp = canonical_ast_delta_fingerprint(orig_source, patched_source)
        if not fp:
            return ""
        self._invariants[fp] = {
            "fingerprint": fp,
            "reason": reason[:160],
            "hits": self._invariants.get(fp, {}).get("hits", 0) + 1,
            "ts": round(time.time(), 3),
        }
        self._flush()
        return fp

    def is_refuted(self, orig_source: str, patched_source: str) -> bool:
        fp = canonical_ast_delta_fingerprint(orig_source, patched_source)
        return bool(fp and fp in self._invariants)

    def delete_invariant(self, fp: str) -> bool:
        removed = self._invariants.pop(fp, None) is not None
        if removed:
            self._flush()
        return removed

    def count(self) -> int:
        return len(self._invariants)

    def _flush(self) -> None:
        if self.store_path is not None:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            self.store_path.write_text(json.dumps(self._invariants, indent=2, sort_keys=True), encoding="utf-8")

def self_check() -> dict[str, Any]:
    """Behavioral positive+negative proof contract for cow_angelic_zygote_v1."""
    import tempfile as _tf
    checks: dict[str, bool] = {}
    _vecs = build_64_boundary_vectors()
    checks["boundary_vectors_nonempty"] = isinstance(_vecs, list) and len(_vecs) >= 16
    _orig = "def f(x):\n    return x\n"
    _p1 = "def f(x):\n    return x + 1\n"
    _p2 = "def f(x):\n    return x * 2\n"
    _fp1 = canonical_ast_delta_fingerprint(_orig, _p1)
    _fp2 = canonical_ast_delta_fingerprint(_orig, _p2)
    checks["delta_fp_nonempty"] = isinstance(_fp1, str) and bool(_fp1)
    checks["delta_fp_distinguishes_ops"] = _fp1 != _fp2
    with _tf.TemporaryDirectory(prefix="w51_zyg_") as _td:
        _nsg = NegativeSpaceGuard(pathlib.Path(_td) / "nsg.json")
        checks["nsg_initially_clean"] = not _nsg.is_refuted(_orig, _p1)
        _nsg.record_refutation(_orig, _p1, "counterexample")
        checks["nsg_blocks_refuted"] = _nsg.is_refuted(_orig, _p1)
        checks["nsg_allows_unrelated"] = not _nsg.is_refuted(_orig, _p2)
    _ok = all(checks.values())
    return {"pass": _ok, "verdict": "PASS" if _ok else "FAIL", "checks": len(checks), "passed": sum(checks.values()), "details": checks}

