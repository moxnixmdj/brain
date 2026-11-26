#!/usr/bin/env python3
"""Zero-Dependency `os.fork()` CoW Test & Assertion-Value Runner (`stdlib_cow_test_runner_v1`).

Eliminates the hard external `pytest` package requirement AND eliminates cold
subprocess interpreter startup overhead (`~60-250 ms` -> `~1.5 ms` per run via
`os.fork()` Copy-on-Write) while emitting 100% pytest-compatible failure/traceback
diagnostics (`rel.py:line: in func`, `E   ExcType: ...`, `assert actual == expected`,
`FAILED rel.py::nodeid`, `N passed`).

Supports:
  - Directory, file, `file.py::func`, and `file.py::Class::method` nodeid targets
  - In-memory file content overlays (`overlays: Mapping[str, str]`) for zero-disk
    speculative patch verification inside the forked CoW child
  - AST `assert a == b` / comparison rewriting so `AssertionError` carries live
    evaluated `assert <actual!r> <op> <expected!r>` values
  - Live stack frame capture (`f_locals` types & reprs + assertion actual/expected)
    for Move 3's `the_assertion_is_the_demand_v1` & `the_relation_is_read_from_the_failing_run_v1`
  - `unittest.TestCase` subclasses, plain `Test*` classes, `def test_*` functions,
    and `tmp_path` directory injection.
"""
from __future__ import annotations

import ast
import importlib.abc
import importlib.machinery
import importlib.util
import inspect
import json
import os
import pathlib
import select
import shutil
import signal
import sys
import tempfile
import time
import traceback
import unittest
from typing import Any, Mapping, Sequence


class _AssertValueRewrite(ast.NodeTransformer):
    """Rewrite `assert lhs <op> rhs` (when msg is None) so failures print live operand values."""

    _OP_SYMS: dict[type[ast.cmpop], str] = {
        ast.Eq: "==",
        ast.NotEq: "!=",
        ast.Lt: "<",
        ast.LtE: "<=",
        ast.Gt: ">",
        ast.GtE: ">=",
        ast.Is: "is",
        ast.IsNot: "is not",
        ast.In: "in",
        ast.NotIn: "not in",
    }

    def visit_Assert(self, node: ast.Assert) -> ast.AST:
        self.generic_visit(node)
        if node.msg is not None:
            return node
        test = node.test
        if (
            isinstance(test, ast.Compare)
            and len(test.ops) == 1
            and len(test.comparators) == 1
            and type(test.ops[0]) in self._OP_SYMS
        ):
            op_cls = type(test.ops[0])
            op_str = self._OP_SYMS[op_cls]
            # Build:
            # _pb_l = <left>; _pb_r = <right>
            # if not (_pb_l <op> _pb_r): raise AssertionError(f"assert {_pb_l!r} <op> {_pb_r!r}")
            assign_l = ast.Assign(
                targets=[ast.Name(id="_pb_assert_lhs", ctx=ast.Store())],
                value=test.left,
            )
            assign_r = ast.Assign(
                targets=[ast.Name(id="_pb_assert_rhs", ctx=ast.Store())],
                value=test.comparators[0],
            )
            cmp_expr = ast.Compare(
                left=ast.Name(id="_pb_assert_lhs", ctx=ast.Load()),
                ops=[op_cls()],
                comparators=[ast.Name(id="_pb_assert_rhs", ctx=ast.Load())],
            )
            msg_expr = ast.JoinedStr(
                values=[
                    ast.Constant(value="assert "),
                    ast.FormattedValue(
                        value=ast.Name(id="_pb_assert_lhs", ctx=ast.Load()),
                        conversion=114,
                    ),
                    ast.Constant(value=f" {op_str} "),
                    ast.FormattedValue(
                        value=ast.Name(id="_pb_assert_rhs", ctx=ast.Load()),
                        conversion=114,
                    ),
                ]
            )
            raise_stmt = ast.If(
                test=ast.UnaryOp(op=ast.Not(), operand=cmp_expr),
                body=[
                    ast.Raise(
                        exc=ast.Call(
                            func=ast.Name(id="AssertionError", ctx=ast.Load()),
                            args=[msg_expr],
                            keywords=[],
                        ),
                        cause=None,
                    )
                ],
                orelse=[],
            )
            block = ast.If(
                test=ast.Constant(value=True),
                body=[assign_l, assign_r, raise_stmt],
                orelse=[],
            )
            ast.copy_location(block, node)
            for sub in ast.walk(block):
                if not hasattr(sub, "lineno"):
                    sub.lineno = node.lineno  # type: ignore[attr-defined]
                    sub.col_offset = node.col_offset  # type: ignore[attr-defined]
            return block
        return node


class _InMemoryOverlayFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Zero-disk `sys.meta_path` overlay loader for candidate patches inside `os.fork()` child."""

    def __init__(self, abs_overlays: Mapping[str, str]) -> None:
        self._overlays = {str(pathlib.Path(k).resolve()): v for k, v in abs_overlays.items()}

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: Any = None,
    ) -> importlib.machinery.ModuleSpec | None:
        search_dirs = list(path) if path is not None else list(sys.path)
        tail = fullname.rsplit(".", 1)[-1]
        for base in search_dirs:
            if not base:
                continue
            bpath = pathlib.Path(base)
            pkg_init = str((bpath / tail / "__init__.py").resolve())
            if pkg_init in self._overlays:
                return importlib.machinery.ModuleSpec(
                    fullname, self, origin=pkg_init, is_package=True
                )
            mod_file = str((bpath / f"{tail}.py").resolve())
            if mod_file in self._overlays:
                return importlib.machinery.ModuleSpec(
                    fullname, self, origin=mod_file, is_package=False
                )
        return None

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> None:
        return None

    def exec_module(self, module: Any) -> None:
        origin = str(module.__spec__.origin)
        if module.__spec__.submodule_search_locations is not None:
            module.__path__ = [str(pathlib.Path(origin).parent)]
        src = self._overlays[origin]
        code = compile(src, origin, "exec")
        exec(code, module.__dict__)  # noqa: S102


def _discover_test_targets(
    repo_root: pathlib.Path,
    targets: Sequence[str],
) -> list[tuple[pathlib.Path, str | None, str | None]]:
    """Expand targets into `(abs_file_path, optional_class_name, optional_func_name)`."""
    specs: list[tuple[pathlib.Path, str | None, str | None]] = []
    raw_targets = list(targets) if targets else ["."]
    seen: set[tuple[str, str | None, str | None]] = set()

    for raw in raw_targets:
        parts = str(raw).split("::")
        path_part = parts[0]
        cls_name = parts[1] if len(parts) >= 3 else None
        fn_name = parts[2] if len(parts) >= 3 else (parts[1] if len(parts) == 2 else None)
        cand = (repo_root / path_part).resolve() if not os.path.isabs(path_part) else pathlib.Path(path_part).resolve()
        if cand.is_file() and cand.suffix == ".py":
            key = (str(cand), cls_name, fn_name)
            if key not in seen:
                seen.add(key)
                specs.append((cand, cls_name, fn_name))
        elif cand.is_dir():
            for p in sorted(cand.rglob("*.py")):
                rel_parts = p.relative_to(cand).parts
                if any(pt in (".git", "__pycache__", "node_modules", ".venv", "venv") for pt in rel_parts):
                    continue
                nm = p.name.lower()
                if nm.startswith("test_") or nm.endswith("_test.py") or nm.startswith("_brain_metamorphic_witness"):
                    key = (str(p.resolve()), None, None)
                    if key not in seen:
                        seen.add(key)
                        specs.append((p.resolve(), None, None))
    return specs


def _format_failure_block(
    repo_root: pathlib.Path,
    nodeid: str,
    exc: BaseException,
) -> tuple[str, list[dict[str, Any]]]:
    """Format pytest-compatible traceback lines + extract structured frame data."""
    lines: list[str] = [f"____ {nodeid} ____"]
    frames_info: list[dict[str, Any]] = []
    tb = exc.__traceback__
    while tb is not None:
        fr = tb.tb_frame
        fname = fr.f_code.co_filename
        lineno = tb.tb_lineno
        func = fr.f_code.co_name
        if "_stdlib_cow_test_runner" not in fname and "importlib" not in fname and "unittest" not in fname:
            try:
                rel = pathlib.Path(fname).resolve().relative_to(repo_root).as_posix()
            except Exception:
                rel = fname
            lines.append(f"{rel}:{lineno}: in {func}")
            # Capture safe scalar/small reprs of local variables for live demand synthesis
            loc_snap: dict[str, Any] = {}
            for k, v in list(fr.f_locals.items())[:24]:
                if k.startswith("__"):
                    continue
                try:
                    r = repr(v)
                    if len(r) <= 240:
                        loc_snap[k] = r
                except Exception:
                    continue
            frames_info.append({
                "rel_path": rel,
                "lineno": lineno,
                "func": func,
                "locals_repr": loc_snap,
            })
        tb = tb.tb_next

    exc_name = type(exc).__name__
    exc_msg = str(exc)
    for idx, msg_ln in enumerate(exc_msg.splitlines() or [""]):
        if idx == 0:
            lines.append(f"E   {exc_name}: {msg_ln}" if msg_ln else f"E   {exc_name}")
        else:
            lines.append(f"E   {msg_ln}")
    return "\n".join(lines), frames_info


def _execute_suite_in_current_process(
    repo_root: pathlib.Path,
    targets: Sequence[str],
    overlays: Mapping[str, str] | None = None,
    capture_frames: bool = False,
) -> dict[str, Any]:
    """Run discovered tests inside an already-isolated child process."""
    os.chdir(str(repo_root))
    # A stale `.pyc` from a previous run in the same directory reports the OLD source. Measured
    # 2026-11-26: after a verified patch was applied, the runner still reported the pre-patch
    # assertion, so the post-state could never be confirmed. The runner never needs a bytecode
    # cache (each child is a fresh fork), so caching is disabled outright rather than invalidated.
    sys.dont_write_bytecode = True
    for _cache in repo_root.rglob("__pycache__"):
        try:
            shutil.rmtree(_cache, ignore_errors=True)
        except OSError:
            pass
    src_dir = repo_root / "src"
    for p in ([str(src_dir), str(repo_root)] if src_dir.is_dir() else [str(repo_root)]):
        if p in sys.path:
            sys.path.remove(p)
        sys.path.insert(0, p)

    # Evict any previously cached modules belonging to `repo_root` OR sharing a top-level
    # module/package name inside `repo_root` (so earlier temporary repos never shadow `repo_root`)!
    local_top_names: set[str] = set()
    for base_d in ([src_dir, repo_root] if src_dir.is_dir() else [repo_root]):
        for entry in base_d.iterdir():
            if entry.is_file() and entry.suffix == ".py":
                local_top_names.add(entry.stem)
            elif entry.is_dir() and (entry / "__init__.py").is_file():
                local_top_names.add(entry.name)
    root_prefix = str(repo_root)
    for mod_name, mod_obj in list(sys.modules.items()):
        top_pkg = mod_name.split(".", 1)[0]
        if top_pkg in local_top_names:
            sys.modules.pop(mod_name, None)
            continue
        mod_file = getattr(mod_obj, "__file__", None)
        if mod_file and str(pathlib.Path(mod_file).resolve()).startswith(root_prefix):
            sys.modules.pop(mod_name, None)

    abs_overlays: dict[str, str] = {}
    if overlays:
        for rel_or_abs, content in overlays.items():
            ap = (repo_root / rel_or_abs).resolve() if not os.path.isabs(rel_or_abs) else pathlib.Path(rel_or_abs).resolve()
            abs_overlays[str(ap)] = content
        sys.meta_path.insert(0, _InMemoryOverlayFinder(abs_overlays))

    specs = _discover_test_targets(repo_root, targets)
    passed = 0
    failed_nodeids: list[str] = []
    blocks: list[str] = []
    failure_frames: dict[str, list[dict[str, Any]]] = {}
    covered_map: dict[str, set[int]] = {}

    prev_trace = sys.gettrace()
    if capture_frames:
        def _cov_tracer(frame: Any, event: str, _arg: Any) -> Any:
            if event == "call":
                fn = frame.f_code.co_filename
                if not fn.startswith(root_prefix):
                    return None
                return _cov_tracer
            if event == "line":
                fn = frame.f_code.co_filename
                if fn.startswith(root_prefix):
                    rel_f = fn[len(root_prefix):].lstrip("/")
                    covered_map.setdefault(rel_f, set()).add(frame.f_lineno)
            return _cov_tracer

        sys.settrace(_cov_tracer)

    try:
        for idx, (tfile, want_cls, want_fn) in enumerate(specs):
            try:
                rel_tfile = tfile.relative_to(repo_root).as_posix()
            except ValueError:
                rel_tfile = tfile.name

            try:
                raw_src = abs_overlays.get(str(tfile))
                if raw_src is None:
                    raw_src = tfile.read_text(encoding="utf-8")
                tree = ast.parse(raw_src, filename=str(tfile))
                tree = _AssertValueRewrite().visit(tree)
                ast.fix_missing_locations(tree)
                code = compile(tree, str(tfile), "exec")
                mod_name = f"_pb_test_mod_{idx}_{tfile.stem}"
                spec = importlib.util.spec_from_file_location(mod_name, str(tfile))
                if spec is None:
                    raise ImportError(f"Cannot create module spec for {rel_tfile}")
                mod = importlib.util.module_from_spec(spec)
                exec(code, mod.__dict__)  # noqa: S102
            except BaseException as exc:  # noqa: BLE001
                failed_nodeids.append(rel_tfile)
                blk, frs = _format_failure_block(repo_root, rel_tfile, exc)
                blocks.append(blk)
                blocks.append(f"ERROR {rel_tfile} - {type(exc).__name__}: {exc}")
                if capture_frames:
                    failure_frames[rel_tfile] = frs
                continue

            # Collect plain `def test_*` functions and `Test*` / `unittest.TestCase` classes
            for obj_name, obj in list(mod.__dict__.items()):
                if want_cls is None and inspect.isfunction(obj) and obj_name.startswith("test_"):
                    if want_fn is not None and obj_name != want_fn:
                        continue
                    nid = f"{rel_tfile}::{obj_name}"
                    try:
                        sig = inspect.signature(obj)
                        with tempfile.TemporaryDirectory(prefix="pb_tmp_path_") as td:
                            kw: dict[str, Any] = {}
                            if "tmp_path" in sig.parameters:
                                kw["tmp_path"] = pathlib.Path(td)
                            obj(**kw)
                        passed += 1
                    except BaseException as exc:  # noqa: BLE001
                        failed_nodeids.append(nid)
                        blk, frs = _format_failure_block(repo_root, nid, exc)
                        blocks.append(blk)
                        blocks.append(f"FAILED {nid}")
                        if capture_frames:
                            failure_frames[nid] = frs

                elif inspect.isclass(obj) and (
                    issubclass(obj, unittest.TestCase) or obj_name.startswith("Test")
                ):
                    if want_cls is not None and obj_name != want_cls:
                        continue
                    if obj is unittest.TestCase:
                        continue
                    for m_name in dir(obj):
                        if not m_name.startswith("test_"):
                            continue
                        if want_fn is not None and m_name != want_fn:
                            continue
                        nid = f"{rel_tfile}::{obj_name}::{m_name}"
                        try:
                            if issubclass(obj, unittest.TestCase):
                                case = obj(m_name)
                                res = unittest.TestResult()
                                case.run(res)
                                if res.failures or res.errors:
                                    _tc, tb_str = (res.failures + res.errors)[0]
                                    blocks.append(f"____ {nid} ____\n{tb_str}\nFAILED {nid}")
                                    failed_nodeids.append(nid)
                                else:
                                    passed += 1
                            else:
                                inst = obj()
                                if hasattr(inst, "setup_method"):
                                    inst.setup_method()
                                try:
                                    m_fn = getattr(inst, m_name)
                                    sig = inspect.signature(m_fn)
                                    with tempfile.TemporaryDirectory(prefix="pb_tmp_path_") as td:
                                        kw = {"tmp_path": pathlib.Path(td)} if "tmp_path" in sig.parameters else {}
                                        m_fn(**kw)
                                    passed += 1
                                finally:
                                    if hasattr(inst, "teardown_method"):
                                        inst.teardown_method()
                        except BaseException as exc:  # noqa: BLE001
                            failed_nodeids.append(nid)
                            blk, frs = _format_failure_block(repo_root, nid, exc)
                            blocks.append(blk)
                            blocks.append(f"FAILED {nid}")
                            if capture_frames:
                                failure_frames[nid] = frs
    finally:
        if capture_frames:
            sys.settrace(prev_trace)

    summary_parts: list[str] = []
    if failed_nodeids:
        summary_parts.append(f"{len(failed_nodeids)} failed")
    if passed:
        summary_parts.append(f"{passed} passed")
    if not summary_parts:
        summary_parts.append("0 passed")
    blocks.append(", ".join(summary_parts))

    rc = 0 if (passed > 0 and not failed_nodeids) else (5 if passed == 0 and not failed_nodeids else 1)
    return {
        "ok": rc == 0,
        "rc": rc,
        "passed": passed,
        "failed_nodeids": failed_nodeids,
        "output": "\n".join(blocks),
        "failure_frames": failure_frames,
        "covered_lines": {k: sorted(v) for k, v in covered_map.items()} if capture_frames else {},
    }


def run_targets_cow_fork(
    repo_root: str | pathlib.Path,
    targets: Sequence[str] = (),
    *,
    overlays: Mapping[str, str] | None = None,
    timeout_s: float = 15.0,
    capture_frames: bool = False,
) -> dict[str, Any]:
    """Execute Python test targets inside an isolated `os.fork()` CoW child (`~1.5 ms`)."""
    root = pathlib.Path(repo_root).resolve()
    t0 = time.monotonic()
    r_fd, w_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(r_fd)
        # Redirect child stdout/stderr to `/dev/null` so noisy SUT prints cannot corrupt parent stdio
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        os.close(devnull)
        try:
            payload = _execute_suite_in_current_process(
                root,
                targets,
                overlays=overlays,
                capture_frames=capture_frames,
            )
            data = json.dumps(payload).encode("utf-8")
        except BaseException as exc:  # noqa: BLE001
            data = json.dumps({
                "ok": False,
                "rc": 2,
                "passed": 0,
                "failed_nodeids": [],
                "output": f"INTERNAL_RUNNER_ERROR: {type(exc).__name__}: {exc}\n{traceback.format_exc()}",
                "failure_frames": {},
            }).encode("utf-8")
        view = memoryview(data)
        sent = 0
        while sent < len(data):
            try:
                sent += os.write(w_fd, view[sent:])
            except OSError:
                break
        os.close(w_fd)
        os._exit(0)

    os.close(w_fd)
    chunks: list[bytes] = []
    deadline = t0 + max(1.0, float(timeout_s))
    timed_out = False
    while True:
        rem = deadline - time.monotonic()
        if rem <= 0:
            timed_out = True
            break
        rdy, _, _ = select.select([r_fd], [], [], min(rem, 0.25))
        if rdy:
            buf = os.read(r_fd, 65536)
            if not buf:
                break
            chunks.append(buf)

    os.close(r_fd)
    if timed_out:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    try:
        os.waitpid(pid, 0)
    except ChildProcessError:
        pass

    elapsed_s = round(time.monotonic() - t0, 4)
    if timed_out:
        return {
            "ok": False,
            "rc": 124,
            "passed": 0,
            "failed_nodeids": [],
            "output": "TIMEOUT",
            "elapsed_s": elapsed_s,
            "failure_frames": {},
        }

    raw_bytes = b"".join(chunks)
    if not raw_bytes:
        return {
            "ok": False,
            "rc": 2,
            "passed": 0,
            "failed_nodeids": [],
            "output": "CHILD_EXITED_WITHOUT_PAYLOAD",
            "elapsed_s": elapsed_s,
            "failure_frames": {},
        }
    res = json.loads(raw_bytes.decode("utf-8", errors="replace"))
    res["elapsed_s"] = elapsed_s
    return res
