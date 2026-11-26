#!/usr/bin/env python3
"""Execution-Traced Mass Adapter & Capsule Compiler (`K3 = 0`).

Supersedes static AST literal scraping (`ast_adapter_derivation_v1.py`, which hit
a `3.7%` `15/406` ceiling) and `functools.wraps` module-attribute patching (which
misses `from module import fn` bindings and `tmp_path` fixtures) by intercepting
live C-level Python call frames during `canonical/tests/test_<stem>.py` execution:

  - Uses PEP 669 `sys.monitoring` (`PY_START`) on Python 3.12+ with automatic
    C-level `sys.setprofile` fallback on Python 3.11, capturing every call to
    public functions defined in the target module regardless of how the test
    imported them (`import mod` vs `from mod import fn`).
  - Freezes scalar literals, nested containers, repository-relative `Path`s,
    `@dataclass` arguments, and bounded temporary scratch fixtures (`<= 24` files,
    `<= 65,536` bytes) into portable, self-contained replay specifications.
  - Enforces three fail-closed admission gates before any adapter is accepted:
      1. **Two-Run Isolated Scratch Determinism**: `digest(run_1) == digest(run_2)`
         across two fresh temporary directories `d1 != d2`.
      2. **Content-SHA256 Non-Destructive Guard** (`scan_and_diff_against_memory_v1`
         + byte SHA-256 invariance): proves zero mutation/deletion of any
         referenced repository file.
      3. **Provenance Capsule Witness** (`composition_state_capsule_v1`): compiles
         the verified replay into a hash-chained provenance capsule verified by
         `verify_capsule`.

Authority: NONE. Grants zero capability/ownership/terminal credit (`capability_credit_delta = 0`),
never writes `BOUND_CAPABILITY_REGISTRY_V1.json`, makes `0` model calls, `$0` spend.
"""
from __future__ import annotations

import contextlib
import copy
import dataclasses
import hashlib
import importlib
import inspect
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.composition_state_capsule_v1 import (  # noqa: E402
    append_macrostep,
    empty_capsule,
    verify_capsule,
)
from canonical.runtime.scan_and_diff_against_memory_v1 import signature as content_signature  # noqa: E402

SCHEMA = "PROJECT_BRAIN_EXECUTION_TRACED_CALLABLE_COMPILER_V1"
AUTHORITY = "NONE__SANDBOX_PRODUCER_VERIFICATION_ONLY"
KILL_FLOOR_SURVIVAL_RATE = 0.40

_MAX_SCRATCH_FILES = 24
_MAX_SCRATCH_BYTES = 65536
_MAX_COLLECTION_LEN = 96


def _canon_digest(value: Any, scratch_dir: str = "") -> str:
    """Deterministic SHA-256 of an arbitrary Python return value with scratch-path scrubbing."""

    def _norm(v: Any, depth: int = 0) -> Any:
        if depth > 8:
            return type(v).__name__
        if v is None or isinstance(v, (bool, int)):
            return v
        if isinstance(v, float):
            if v != v:  # NaN
                return "NaN"
            return round(v, 8)
        if isinstance(v, str):
            return v.replace(scratch_dir, "<SCRATCH>") if scratch_dir and scratch_dir in v else v
        if isinstance(v, bytes):
            return {"__bytes_sha256__": hashlib.sha256(v).hexdigest(), "len": len(v)}
        if isinstance(v, pathlib.Path):
            s = v.as_posix()
            if scratch_dir and scratch_dir in s:
                s = s.replace(scratch_dir, "<SCRATCH>")
            return {"__path__": s}
        if dataclasses.is_dataclass(v) and not isinstance(v, type):
            return {
                "__dataclass__": type(v).__qualname__,
                "fields": {
                    f.name: _norm(getattr(v, f.name), depth + 1)
                    for f in dataclasses.fields(v)
                    if not f.name.startswith("_") and "elapsed" not in f.name and "ms" not in f.name
                },
            }
        if isinstance(v, Mapping):
            out: dict[str, Any] = {}
            for k in sorted(v.keys(), key=lambda x: str(x)):
                ks = str(k)
                # Scrub wall-clock timing keys so deterministic logic isn't penalized for ns jitter
                if ks in {"elapsed_ms", "elapsed_s", "duration_ms", "wall_clock_ms", "timestamp", "created_at_utc"} or ks.endswith(("_ms", "_us", "_ns")):
                    continue
                out[ks] = _norm(v[k], depth + 1)
            return out
        if isinstance(v, (list, tuple)):
            return [_norm(x, depth + 1) for x in v[:256]]
        if isinstance(v, (set, frozenset)):
            items = [_norm(x, depth + 1) for x in v]
            return sorted(items, key=lambda x: json.dumps(x, sort_keys=True, default=str))
        # Custom object with stable __dict__
        if hasattr(v, "__dict__"):
            d = {
                k: _norm(val, depth + 1)
                for k, val in vars(v).items()
                if not k.startswith("_") and not callable(val)
            }
            return {"__obj__": type(v).__qualname__, "attrs": d}
        return type(v).__qualname__

    normalized = _norm(value)
    blob = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _snapshot_scratch_tree(scratch_root: pathlib.Path) -> dict[str, str] | None:
    """Capture `<= 24` files (`<= 64 KB` total) inside `scratch_root` as `{rel_posix: hex_bytes}`."""
    if not scratch_root.exists():
        return {}
    files: dict[str, str] = {}
    total_bytes = 0
    for p in sorted(scratch_root.rglob("*")):
        if p.is_symlink() or not p.is_file():
            continue
        if "__pycache__" in p.parts:
            continue
        try:
            raw = p.read_bytes()
        except OSError:
            return None
        total_bytes += len(raw)
        if len(files) >= _MAX_SCRATCH_FILES or total_bytes > _MAX_SCRATCH_BYTES:
            return None
        files[p.relative_to(scratch_root).as_posix()] = raw.hex()
    return files


def freeze_value(
    val: Any,
    *,
    root: pathlib.Path,
    scratch_root: pathlib.Path,
    depth: int = 0,
) -> tuple[str, Any] | None:
    """Freeze a live Python argument into a portable JSON-serializable spec, or `None` if unportable."""
    if depth > 6:
        return None
    scratch_posix = scratch_root.resolve().as_posix()
    if val is None or isinstance(val, (bool, int, float)):
        if isinstance(val, float) and (val != val or val in (float("inf"), float("-inf"))):
            return None
        return ("lit", val)
    if isinstance(val, str):
        if len(val) > 32768:
            return None
        if scratch_posix in val:
            tree = _snapshot_scratch_tree(scratch_root.resolve())
            if tree is None:
                return None
            rel_suffix = val.split(scratch_posix, 1)[1].lstrip("/")
            return ("scratch_str", {"subpath": rel_suffix, "tree": tree})
        return ("lit", val)
    if isinstance(val, bytes):
        if len(val) > 16384:
            return None
        return ("bytes", val.hex())
    if isinstance(val, pathlib.Path):
        resolved = val.resolve()
        res_posix = resolved.as_posix()
        if res_posix == scratch_posix or res_posix.startswith(scratch_posix + "/"):
            tree = _snapshot_scratch_tree(scratch_root.resolve())
            if tree is None:
                return None
            rel_suffix = res_posix[len(scratch_posix) :].lstrip("/")
            return ("scratch_path", {"subpath": rel_suffix, "tree": tree})
        try:
            rel_repo = resolved.relative_to(root.resolve()).as_posix()
            return ("repo_path", rel_repo)
        except ValueError:
            return None
    if dataclasses.is_dataclass(val) and not isinstance(val, type):
        cls = type(val)
        mod_name = getattr(cls, "__module__", "")
        cls_name = getattr(cls, "__name__", "")
        if not mod_name or mod_name == "__main__" or "." not in cls_name and not hasattr(sys.modules.get(mod_name), cls_name):
            return None
        fields_spec: dict[str, Any] = {}
        for f in dataclasses.fields(val):
            fv = freeze_value(getattr(val, f.name), root=root, scratch_root=scratch_root, depth=depth + 1)
            if fv is None:
                return None
            fields_spec[f.name] = fv
        return ("dataclass", {"module": mod_name, "class": cls_name, "fields": fields_spec})
    if isinstance(val, (list, tuple)):
        if len(val) > _MAX_COLLECTION_LEN:
            return None
        items = []
        for item in val:
            fi = freeze_value(item, root=root, scratch_root=scratch_root, depth=depth + 1)
            if fi is None:
                return None
            items.append(fi)
        return ("tuple" if isinstance(val, tuple) else "list", items)
    if isinstance(val, (set, frozenset)):
        if len(val) > _MAX_COLLECTION_LEN:
            return None
        items = []
        for item in sorted(val, key=repr):
            fi = freeze_value(item, root=root, scratch_root=scratch_root, depth=depth + 1)
            if fi is None:
                return None
            items.append(fi)
        return ("frozenset" if isinstance(val, frozenset) else "set", items)
    if isinstance(val, dict):
        if len(val) > _MAX_COLLECTION_LEN:
            return None
        sub: dict[str, Any] = {}
        for k, v in val.items():
            if not isinstance(k, (str, int)):
                return None
            fv = freeze_value(v, root=root, scratch_root=scratch_root, depth=depth + 1)
            if fv is None:
                return None
            sub[str(k)] = [ "int_key" if isinstance(k, int) and not isinstance(k, bool) else "str_key", k, fv ]
        return ("dict", sub)
    return None


def thaw_value(
    spec: Sequence[Any],
    *,
    root: pathlib.Path,
    replay_scratch: pathlib.Path,
    materialized_trees: set[str],
) -> Any:
    """Reconstruct a live Python argument from its frozen specification inside `replay_scratch`."""
    kind, payload = spec[0], spec[1]
    if kind == "lit":
        return copy.deepcopy(payload)
    if kind == "bytes":
        return bytes.fromhex(payload)
    if kind == "repo_path":
        return (root / str(payload)).resolve()
    if kind in ("scratch_path", "scratch_str"):
        tree: Mapping[str, str] = payload["tree"]
        tree_sig = hashlib.sha256(json.dumps(tree, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        base_dir = replay_scratch / f"fixture_{tree_sig}"
        if tree_sig not in materialized_trees:
            base_dir.mkdir(parents=True, exist_ok=True)
            for rel_f, hex_b in tree.items():
                dst = base_dir / rel_f
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(bytes.fromhex(hex_b))
            materialized_trees.add(tree_sig)
        sub = str(payload.get("subpath") or "")
        target = (base_dir / sub) if sub else base_dir
        if not sub and not tree:
            target.mkdir(parents=True, exist_ok=True)
        return target if kind == "scratch_path" else target.as_posix()
    if kind == "dataclass":
        mod = importlib.import_module(payload["module"])
        cls = getattr(mod, payload["class"])
        kwargs = {
            fname: thaw_value(fspec, root=root, replay_scratch=replay_scratch, materialized_trees=materialized_trees)
            for fname, fspec in payload["fields"].items()
        }
        return cls(**kwargs)
    if kind == "list":
        return [
            thaw_value(x, root=root, replay_scratch=replay_scratch, materialized_trees=materialized_trees)
            for x in payload
        ]
    if kind == "tuple":
        return tuple(
            thaw_value(x, root=root, replay_scratch=replay_scratch, materialized_trees=materialized_trees)
            for x in payload
        )
    if kind == "set":
        return {
            thaw_value(x, root=root, replay_scratch=replay_scratch, materialized_trees=materialized_trees)
            for x in payload
        }
    if kind == "frozenset":
        return frozenset(
            thaw_value(x, root=root, replay_scratch=replay_scratch, materialized_trees=materialized_trees)
            for x in payload
        )
    if kind == "dict":
        out: dict[Any, Any] = {}
        for _ks, orig_k, fv in payload.values():
            out[orig_k] = thaw_value(
                fv, root=root, replay_scratch=replay_scratch, materialized_trees=materialized_trees
            )
        return out
    raise ValueError(f"UNKNOWN_FROZEN_SPEC_KIND:{kind}")


def _collect_referenced_repo_files(spec: Sequence[Any], root: pathlib.Path, acc: set[pathlib.Path]) -> None:
    kind, payload = spec[0], spec[1]
    if kind == "repo_path":
        p = (root / str(payload)).resolve()
        if p.is_file():
            acc.add(p)
    elif kind in ("list", "tuple", "set", "frozenset"):
        for x in payload:
            _collect_referenced_repo_files(x, root, acc)
    elif kind == "dict":
        for _ks, _ok, fv in payload.values():
            _collect_referenced_repo_files(fv, root, acc)
    elif kind == "dataclass":
        for fv in payload["fields"].values():
            _collect_referenced_repo_files(fv, root, acc)


def _exercise_test_module(tmod: Any, scratch_root: pathlib.Path, should_stop: Any) -> int:
    """Execute tests inside `tmod` quietly (supporting `unittest.TestCase`, pytest `test_*`, and `Test*` classes)."""
    ran = 0
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        suite = unittest.defaultTestLoader.loadTestsFromModule(tmod)
        if suite.countTestCases() > 0:
            for group in list(suite)[:4]:
                unittest.TextTestRunner(stream=buf, verbosity=0).run(group)
                ran += 1
                if should_stop():
                    return ran

        # Plain pytest-style `test_*` functions (including `tmp_path` fixtures)
        for idx, (tname, tf) in enumerate(inspect.getmembers(tmod, inspect.isfunction)):
            if not tname.startswith("test_"):
                continue
            try:
                sig = inspect.signature(tf)
                params = list(sig.parameters.values())
                call_kwargs: dict[str, Any] = {}
                ok = True
                for p in params:
                    if p.name in ("tmp_path", "tmpdir"):
                        sub = scratch_root / f"tp_{idx}_{tname}"
                        sub.mkdir(parents=True, exist_ok=True)
                        call_kwargs[p.name] = sub
                    elif p.default is not inspect.Parameter.empty:
                        continue
                    else:
                        ok = False
                        break
                if ok:
                    tf(**call_kwargs)
                    ran += 1
            except BaseException:
                pass
            if should_stop():
                return ran

        # Plain pytest-style `class Test*:` without `unittest.TestCase`
        for cname, cls in inspect.getmembers(tmod, inspect.isclass):
            if not cname.startswith("Test") or issubclass(cls, unittest.TestCase):
                continue
            try:
                inst = cls()
            except Exception:
                continue
            for idx, (mname, mf) in enumerate(inspect.getmembers(inst, inspect.ismethod)):
                if not mname.startswith("test_"):
                    continue
                try:
                    sig = inspect.signature(mf)
                    call_kwargs = {}
                    ok = True
                    for p in sig.parameters.values():
                        if p.name in ("tmp_path", "tmpdir"):
                            sub = scratch_root / f"tc_{idx}_{mname}"
                            sub.mkdir(parents=True, exist_ok=True)
                            call_kwargs[p.name] = sub
                        elif p.default is not inspect.Parameter.empty:
                            continue
                        else:
                            ok = False
                            break
                    if ok:
                        mf(**call_kwargs)
                        ran += 1
                except BaseException:
                    pass
                if should_stop():
                    return ran
    return ran


def derive_verified_module_adapter(
    module_rel_path: str,
    *,
    root: pathlib.Path = ROOT,
    max_captured_calls: int = 16,
) -> dict[str, Any]:
    """Intercept real calls to `module_rel_path` from `canonical/tests/test_<stem>.py`,
    then verify 2-run scratch replay determinism + repo SHA-256 invariance + provenance capsule."""
    root = pathlib.Path(root).resolve()
    rel = module_rel_path.strip().replace("\\", "/")
    mod_file = (root / rel).resolve()
    if not mod_file.is_file():
        return {"schema": SCHEMA, "pass": False, "module": rel, "reason": "MODULE_FILE_MISSING", "model_calls": 0}

    stem = mod_file.stem
    test_rel = f"canonical/tests/test_{stem}.py"
    test_file = (root / test_rel).resolve()
    if not test_file.is_file():
        return {"schema": SCHEMA, "pass": False, "module": rel, "reason": "TEST_FILE_MISSING", "model_calls": 0}

    mod_dot = rel[:-3].replace("/", ".") if rel.endswith(".py") else rel.replace("/", ".")
    test_dot = f"canonical.tests.test_{stem}"

    mod_parent_str = str(mod_file.parent)
    root_str = str(root)
    is_sandbox_root = root != ROOT
    saved_mods = dict(sys.modules) if is_sandbox_root else None
    added_paths: list[str] = []
    for p_str in (mod_parent_str, root_str):
        if p_str not in sys.path:
            sys.path.insert(0, p_str)
            added_paths.append(p_str)
    try:
        if not is_sandbox_root:
            mod = importlib.import_module(mod_dot)
            tmod = importlib.import_module(test_dot)
        else:
            importlib.invalidate_caches()
            pkg_prefix = mod_dot.split(".", 1)[0]
            for k in [k for k in sys.modules if k == pkg_prefix or k.startswith(f"{pkg_prefix}.")]:
                sys.modules.pop(k, None)
            mspec = importlib.util.spec_from_file_location(mod_dot, mod_file)
            tspec = importlib.util.spec_from_file_location(f"_custom_test_{stem}", test_file)
            if mspec is None or mspec.loader is None or tspec is None or tspec.loader is None:
                raise ImportError("SPEC_UNLOADABLE")
            mod = importlib.util.module_from_spec(mspec)
            sys.modules[mod_dot] = mod
            mspec.loader.exec_module(mod)
            tmod = importlib.util.module_from_spec(tspec)
            tspec.loader.exec_module(tmod)
    except BaseException as exc:
        if is_sandbox_root:
            for p_str in added_paths:
                if p_str in sys.path:
                    sys.path.remove(p_str)
            if saved_mods is not None:
                for k in list(sys.modules):
                    if k not in saved_mods:
                        sys.modules.pop(k, None)
                sys.modules.update(saved_mods)
        return {
            "schema": SCHEMA,
            "pass": False,
            "module": rel,
            "reason": f"IMPORT_FAILED:{type(exc).__name__}",
            "model_calls": 0,
        }
    if is_sandbox_root:
        for p_str in added_paths:
            if p_str in sys.path:
                sys.path.remove(p_str)
        if saved_mods is not None:
            for k in list(sys.modules):
                if k not in saved_mods:
                    sys.modules.pop(k, None)
            sys.modules.update(saved_mods)

    public_fns: dict[str, Any] = {
        name: fn
        for name, fn in inspect.getmembers(mod, inspect.isfunction)
        if not name.startswith("_") and getattr(fn, "__module__", "") == mod.__name__
    }
    if not public_fns:
        return {"schema": SCHEMA, "pass": False, "module": rel, "reason": "NO_PUBLIC_FUNCTIONS", "model_calls": 0}

    target_filename = str(mod_file)
    captured: list[dict[str, Any]] = []
    seen_call_sigs: set[str] = set()
    tracer_mechanism = "pep669_sys_monitoring" if hasattr(sys, "monitoring") else "cpython_sys_setprofile"

    with tempfile.TemporaryDirectory(prefix="brain_trace_cap_") as trace_td:
        scratch_path = pathlib.Path(trace_td).resolve()

        def _capture_frame(frame: Any) -> None:
            if len(captured) >= max_captured_calls:
                return
            code = frame.f_code
            if code.co_filename != target_filename:
                return
            fname = code.co_name
            fn_obj = public_fns.get(fname)
            if fn_obj is None:
                return
            try:
                sig = inspect.signature(fn_obj)
            except (TypeError, ValueError):
                return
            pos_specs: list[Any] = []
            kw_specs: dict[str, Any] = {}
            flocals = frame.f_locals
            for pname, param in sig.parameters.items():
                if pname not in flocals:
                    return
                raw_val = flocals[pname]
                if param.kind == inspect.Parameter.VAR_POSITIONAL:
                    f_var = freeze_value(tuple(raw_val), root=root, scratch_root=scratch_path)
                    if f_var is None:
                        return
                    pos_specs.extend(f_var[1])
                elif param.kind == inspect.Parameter.VAR_KEYWORD:
                    f_kw = freeze_value(dict(raw_val), root=root, scratch_root=scratch_path)
                    if f_kw is None:
                        return
                    for _ks, orig_k, sub_spec in f_kw[1].values():
                        if not isinstance(orig_k, str):
                            return
                        kw_specs[orig_k] = sub_spec
                elif param.kind == inspect.Parameter.KEYWORD_ONLY:
                    f_kwo = freeze_value(raw_val, root=root, scratch_root=scratch_path)
                    if f_kwo is None:
                        return
                    kw_specs[pname] = f_kwo
                else:
                    f_pos = freeze_value(raw_val, root=root, scratch_root=scratch_path)
                    if f_pos is None:
                        return
                    pos_specs.append(f_pos)
            call_key = hashlib.sha256(
                json.dumps([fname, pos_specs, kw_specs], sort_keys=True).encode("utf-8")
            ).hexdigest()[:20]
            if call_key not in seen_call_sigs:
                seen_call_sigs.add(call_key)
                captured.append({"fn_name": fname, "pos_specs": pos_specs, "kw_specs": kw_specs})

        cwd_before = os.getcwd()
        if hasattr(sys, "monitoring"):
            mon = sys.monitoring
            tool_id = 4
            try:
                mon.use_tool_id(tool_id, "brain_exec_adapter_tracer")
                mon.register_callback(
                    tool_id,
                    mon.events.PY_START,
                    lambda code, _offset: _capture_frame(sys._getframe(1))
                    if code.co_filename == target_filename
                    else None,
                )
                mon.set_events(tool_id, mon.events.PY_START)
                _exercise_test_module(tmod, scratch_path, lambda: len(captured) >= max_captured_calls)
            finally:
                try:
                    mon.set_events(tool_id, 0)
                    mon.register_callback(tool_id, mon.events.PY_START, None)
                    mon.free_tool_id(tool_id)
                except Exception:
                    pass
                os.chdir(cwd_before)
        else:
            prev_prof = sys.getprofile()

            def _prof_hook(frame: Any, event: str, _arg: Any) -> None:
                if event == "call":
                    _capture_frame(frame)

            sys.setprofile(_prof_hook)
            try:
                _exercise_test_module(tmod, scratch_path, lambda: len(captured) >= max_captured_calls)
            finally:
                sys.setprofile(prev_prof)
                os.chdir(cwd_before)

    if not captured:
        return {
            "schema": SCHEMA,
            "pass": False,
            "module": rel,
            "test_file": test_rel,
            "tracer": tracer_mechanism,
            "reason": "NO_PORTABLE_CALL_FRAMES_CAPTURED",
            "model_calls": 0,
        }

    # Verify candidates via 2-run isolated replay + repo SHA-256 non-destructiveness + capsule witness
    for cand in captured:
        fname = cand["fn_name"]
        pos_specs = cand["pos_specs"]
        kw_specs = cand["kw_specs"]
        fn_obj = public_fns[fname]

        ref_files: set[pathlib.Path] = {mod_file}
        for sp in pos_specs:
            _collect_referenced_repo_files(sp, root, ref_files)
        for sp in kw_specs.values():
            _collect_referenced_repo_files(sp, root, ref_files)

        pre_hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in ref_files if p.is_file()}
        pre_sigs = {p: content_signature(str(p)) for p in list(ref_files)[:4] if p.is_file()}

        try:
            with (
                tempfile.TemporaryDirectory(prefix="brain_rep1_") as d1_str,
                tempfile.TemporaryDirectory(prefix="brain_rep2_") as d2_str,
            ):
                d1 = pathlib.Path(d1_str).resolve()
                d2 = pathlib.Path(d2_str).resolve()
                cwd0 = os.getcwd()
                buf = io.StringIO()
                try:
                    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                        os.chdir(d1)
                        mat1: set[str] = set()
                        args1 = [thaw_value(s, root=root, replay_scratch=d1, materialized_trees=mat1) for s in pos_specs]
                        kwargs1 = {
                            k: thaw_value(v, root=root, replay_scratch=d1, materialized_trees=mat1)
                            for k, v in kw_specs.items()
                        }
                        t0 = time.perf_counter_ns()
                        out1 = fn_obj(*args1, **kwargs1)
                        replay_ms = (time.perf_counter_ns() - t0) / 1_000_000.0

                        os.chdir(d2)
                        mat2: set[str] = set()
                        args2 = [thaw_value(s, root=root, replay_scratch=d2, materialized_trees=mat2) for s in pos_specs]
                        kwargs2 = {
                            k: thaw_value(v, root=root, replay_scratch=d2, materialized_trees=mat2)
                            for k, v in kw_specs.items()
                        }
                        out2 = fn_obj(*args2, **kwargs2)
                finally:
                    os.chdir(cwd0)
        except BaseException:
            continue

        if out1 is None:
            continue

        dig1 = _canon_digest(out1, d1.as_posix())
        dig2 = _canon_digest(out2, d2.as_posix())
        if dig1 != dig2:
            continue

        # Gate 2: Non-destructive byte SHA-256 + content-validator signature invariance
        post_hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in pre_hashes if p.is_file()}
        post_sigs = {p: content_signature(str(p)) for p in pre_sigs if p.is_file()}
        if post_hashes != pre_hashes or post_sigs != pre_sigs:
            return {
                "schema": SCHEMA,
                "pass": False,
                "module": rel,
                "reason": "WORKSPACE_MUTATION_REJECTED_BY_CONTENT_SHA256_GUARD",
                "model_calls": 0,
            }

        # Gate 3: Compile hash-chained provenance capsule witness
        action_sha = hashlib.sha256(
            json.dumps({"module": rel, "entrypoint": fname, "pos": pos_specs, "kw": kw_specs}, sort_keys=True).encode(
                "utf-8"
            )
        ).hexdigest()
        cap = empty_capsule()
        cap = append_macrostep(
            cap,
            producer=f"traced:{mod_dot}:{fname}",
            action_ref=action_sha,
            requires=[],
            provides=[f"effect:traced_return:{stem}:{fname}"],
            values={
                f"effect:traced_return:{stem}:{fname}": {
                    "module": rel,
                    "entrypoint": fname,
                    "output_digest": dig1,
                    "non_destructive_sha256_verified": True,
                }
            },
            evidence_refs=[f"replay_sha256:{dig1}"],
            lineage={f"effect:traced_return:{stem}:{fname}": [f"evidence:replay_sha256:{dig1}", f"action:{action_sha}"]},
        )
        cap_verdict = verify_capsule(cap)
        if cap_verdict.get("status") != "PASS":
            continue

        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "pass": True,
            "module": rel,
            "module_dot": mod_dot,
            "stem": stem,
            "test_file": test_rel,
            "tracer": tracer_mechanism,
            "entrypoint": fname,
            "captured_frames": len(captured),
            "pos_specs": pos_specs,
            "kw_specs": kw_specs,
            "output_type": type(out1).__name__,
            "replay_digest": dig1,
            "two_run_deterministic": True,
            "non_destructive_sha256_verified": True,
            "capsule_head_hash": cap["head_hash"],
            "replay_latency_ms": round(replay_ms, 4),
            "capability_credit_delta": 0,
            "model_calls": 0,
            "incremental_spend_usd": 0,
        }

    return {
        "schema": SCHEMA,
        "pass": False,
        "module": rel,
        "test_file": test_rel,
        "tracer": tracer_mechanism,
        "captured_frames": len(captured),
        "reason": "NO_CANDIDATE_SURVIVED_TWO_RUN_REPLAY",
        "model_calls": 0,
    }


def invoke_verified_traced_adapter(
    adapter_record: Mapping[str, Any],
    *,
    override_args: Sequence[Any] | None = None,
    override_kwargs: Mapping[str, Any] | None = None,
    root: pathlib.Path = ROOT,
) -> dict[str, Any]:
    """Execute a previously verified execution-traced adapter inside an isolated scratch sandbox."""
    if not adapter_record.get("pass"):
        return {"schema": SCHEMA, "pass": False, "reason": "ADAPTER_NOT_VERIFIED", "model_calls": 0}
    root = pathlib.Path(root).resolve()
    mod_dot = str(adapter_record["module_dot"])
    fname = str(adapter_record["entrypoint"])
    mod = importlib.import_module(mod_dot)
    fn_obj = getattr(mod, fname)

    with tempfile.TemporaryDirectory(prefix="brain_traced_inv_") as td_str:
        td = pathlib.Path(td_str).resolve()
        cwd0 = os.getcwd()
        buf = io.StringIO()
        try:
            os.chdir(td)
            mat: set[str] = set()
            if override_args is not None or override_kwargs is not None:
                args = list(override_args or ())
                kwargs = dict(override_kwargs or {})
            else:
                args = [
                    thaw_value(s, root=root, replay_scratch=td, materialized_trees=mat)
                    for s in adapter_record.get("pos_specs", ())
                ]
                kwargs = {
                    k: thaw_value(v, root=root, replay_scratch=td, materialized_trees=mat)
                    for k, v in (adapter_record.get("kw_specs") or {}).items()
                }
            t0 = time.perf_counter_ns()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                result = fn_obj(*args, **kwargs)
            elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
            dig = _canon_digest(result, td.as_posix())
        finally:
            os.chdir(cwd0)

    matches_witness = (
        dig == adapter_record.get("replay_digest")
        if (override_args is None and override_kwargs is None)
        else None
    )
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "pass": True,
        "module": adapter_record["module"],
        "entrypoint": fname,
        "output_type": type(result).__name__,
        "output_digest": dig,
        "matches_recorded_witness": matches_witness,
        "result": result,
        "elapsed_ms": round(elapsed_ms, 4),
        "capability_credit_delta": 0,
        "model_calls": 0,
    }


def compile_source_only_batch_subprocess_guarded(
    *,
    root: pathlib.Path = ROOT,
    limit: int | None = 120,
    per_module_timeout_s: float = 6.0,
) -> dict[str, Any]:
    """Evaluate `SOURCE_ONLY` modules with `canonical/tests/test_<stem>.py` from
    `PROMOTION_LEDGER_20261127_V1.json`, isolating each module with a strict timeout
    so hanging/slow subprocess tests cannot stall the census."""
    root = pathlib.Path(root).resolve()
    ledger_path = root / "canonical" / "verification" / "PROMOTION_LEDGER_20261127_V1.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    candidates = [
        row
        for row in ledger.get("rows", [])
        if row.get("category") == "SOURCE_ONLY"
        and (root / "canonical" / "tests" / f"test_{row['stem']}.py").is_file()
    ]
    if limit is not None:
        # Deterministic stratified stride across the entire sorted candidate list
        # so the census spans the full alphabet/domain distribution rather than a prefix!
        n = len(candidates)
        k = min(max(1, int(limit)), n)
        if k < n:
            selected = [candidates[(i * n) // k] for i in range(k)]
        else:
            selected = list(candidates)
    else:
        selected = list(candidates)

    worker_snippet = (
        "import json, pathlib, sys\n"
        "from canonical.runtime.execution_traced_callable_compiler_v1 import derive_verified_module_adapter\n"
        "root = pathlib.Path(sys.argv[1]).resolve()\n"
        "rel = sys.argv[2]\n"
        "res = derive_verified_module_adapter(rel, root=root)\n"
        # Strip bulky pos_specs/kw_specs trees from summary JSON if huge, keep compact metadata
        "slim = {k: v for k, v in res.items() if k not in ('pos_specs', 'kw_specs')}\n"
        "print('__TRACED_ADAPTER__' + json.dumps(slim, sort_keys=True))\n"
    )

    t_start = time.perf_counter()
    passed_rows: list[dict[str, Any]] = []
    failed_reasons: dict[str, int] = {}
    latencies_ms: list[float] = []

    def _eval_one(row: Mapping[str, Any]) -> tuple[Mapping[str, Any], dict[str, Any]]:
        rel = str(row["path"])
        try:
            proc = subprocess.run(
                [sys.executable, "-c", worker_snippet, str(root), rel],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=per_module_timeout_s,
                check=False,
            )
            marker_lines = [
                ln[len("__TRACED_ADAPTER__") :]
                for ln in proc.stdout.splitlines()
                if ln.startswith("__TRACED_ADAPTER__")
            ]
            if marker_lines:
                verdict = json.loads(marker_lines[-1])
            else:
                verdict = {"pass": False, "module": rel, "reason": f"SUBPROCESS_EXIT_{proc.returncode}"}
        except subprocess.TimeoutExpired:
            verdict = {"pass": False, "module": rel, "reason": "MODULE_TEST_TIMEOUT"}
        return row, verdict

    max_workers = min(8, max(1, os.cpu_count() or 4))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        outcomes = list(pool.map(_eval_one, selected))

    for row, verdict in outcomes:
        if verdict.get("pass"):
            verdict["domains"] = list(row.get("domains") or [])
            passed_rows.append(verdict)
            latencies_ms.append(float(verdict.get("replay_latency_ms") or 0.0))
        else:
            r = str(verdict.get("reason") or "UNKNOWN")
            failed_reasons[r] = failed_reasons.get(r, 0) + 1

    total_attempted = len(selected)
    survived_count = len(passed_rows)
    survival_rate = round(survived_count / max(1, total_attempted), 4)
    sorted_lat = sorted(latencies_ms)
    replay_p50_ms = round(sorted_lat[len(sorted_lat) // 2], 4) if sorted_lat else 0.0
    replay_p95_ms = round(sorted_lat[min(len(sorted_lat) - 1, int(0.95 * len(sorted_lat)))], 4) if sorted_lat else 0.0

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "status": "PASS" if survival_rate >= KILL_FLOOR_SURVIVAL_RATE else "BELOW_KILL_FLOOR",
        "total_source_only_with_tests_in_repo": len(candidates),
        "attempted_count": total_attempted,
        "survived_two_run_and_sha256_guard_count": survived_count,
        "survival_rate": survival_rate,
        "ast_literal_baseline_survival_rate": 0.0369,
        "lift_multiple_vs_ast_literal_baseline": round(survival_rate / 0.0369, 2),
        "kill_floor_survival_rate": KILL_FLOOR_SURVIVAL_RATE,
        "exceeds_kill_floor": survival_rate >= KILL_FLOOR_SURVIVAL_RATE,
        "replay_p50_ms": replay_p50_ms,
        "replay_p95_ms": replay_p95_ms,
        "failure_breakdown": dict(sorted(failed_reasons.items())),
        "verified_adapters": passed_rows,
        "wall_clock_s": round(time.perf_counter() - t_start, 3),
        "capability_credit_delta": 0,
        "model_calls": 0,
        "network_calls": 0,
        "incremental_spend_usd": 0,
    }


def run(payload: Mapping[str, Any] | None = None, root: pathlib.Path | None = None) -> dict[str, Any]:
    rr = pathlib.Path(root or ROOT).resolve()
    req = dict(payload or {})
    if req.get("module"):
        return derive_verified_module_adapter(str(req["module"]), root=rr)
    limit = int(req.get("limit", 60))
    return compile_source_only_batch_subprocess_guarded(root=rr, limit=limit)
