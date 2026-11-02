#!/usr/bin/env python3
"""Copy-On-Write (`os.fork()`) Prewarmed Zygote Engine (`zygote_worker_pool_v1`).

Eliminates cold Python startup, module import, and Unified-Model JSON parse overhead
for isolated worker invocations by pre-loading:
  - `brain_unified_model_v1.open_model()` + `unrunnable_capabilities()`
  - `live_integrated_brain_v1.load_verified_registry()`
  - `UpstreamRoutingLedger` RAM-cached shape table
  - `CompiledWorkflowStore` inverted skill index

Each dispatched task runs inside an ephemeral `os.fork()` child sharing the parent's
read-only pages via Linux Copy-On-Write (~1-2 ms fork+pipe round-trip), so mutations,
file descriptors, or crashes in a worker never pollute the parent or sibling runs.
Zero model calls (K3 = 0), $0 spend.
"""
from __future__ import annotations

import json
import os
import pathlib
import struct
import time
from typing import Any, Callable, Mapping

SCHEMA = "PROJECT_BRAIN_ZYGOTE_WORKER_POOL_V1"


def _write_frame(fd: int, payload: Mapping[str, Any]) -> None:
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    header = struct.pack(">I", len(data))
    view = memoryview(header + data)
    written = 0
    while written < len(view):
        written += os.write(fd, view[written:])


def _read_frame(fd: int) -> dict[str, Any]:
    hdr = bytearray()
    while len(hdr) < 4:
        chunk = os.read(fd, 4 - len(hdr))
        if not chunk:
            raise EOFError("ZYGOTE_PIPE_EOF_HEADER")
        hdr.extend(chunk)
    (size,) = struct.unpack(">I", bytes(hdr))
    body = bytearray()
    while len(body) < size:
        chunk = os.read(fd, size - len(body))
        if not chunk:
            raise EOFError("ZYGOTE_PIPE_EOF_BODY")
        body.extend(chunk)
    return json.loads(body.decode("utf-8"))


class ZygotePrewarmedPool:
    """Pre-warmed Copy-On-Write fork dispatcher over the Brain's front door and stores."""

    def __init__(
        self,
        *,
        artifact_path: str | pathlib.Path | None = None,
        ledger_db_path: str | pathlib.Path | None = None,
        workflow_db_path: str | pathlib.Path | None = None,
    ) -> None:
        self.artifact_path = pathlib.Path(artifact_path) if artifact_path else None
        self.ledger_db_path = pathlib.Path(ledger_db_path) if ledger_db_path else None
        self.workflow_db_path = pathlib.Path(workflow_db_path) if workflow_db_path else None
        self._warmed = False
        self._warm_ms = 0.0
        self._model: Any = None
        self._registry_count = 0

    def prewarm(self) -> dict[str, Any]:
        t0 = time.perf_counter_ns()
        import pytest as _warm_pytest  # noqa: F401
        from canonical.runtime import brain_unified_model_v1 as bum
        from canonical.runtime import live_integrated_brain_v1 as lib
        from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as ctc
        from canonical.swe_kernel.upstream_routing_ledger_v1 import default_ledger

        self._model = bum.open_model(self.artifact_path)
        self._model.unrunnable_capabilities()
        reg = lib.load_verified_registry()
        self._registry_count = len(reg)
        default_ledger(self.ledger_db_path).lookup_shape("warmup probe sentence")
        ctc._load_cached_skills(self.workflow_db_path)
        self._warmed = True
        self._warm_ms = round((time.perf_counter_ns() - t0) / 1e6, 3)
        return {
            "schema": SCHEMA,
            "warmed": True,
            "warm_ms": self._warm_ms,
            "capabilities": len(self._model.capabilities),
            "verified_registry": self._registry_count,
            "fork_supported": hasattr(os, "fork"),
        }

    def run_isolated(self, fn: Callable[[], Mapping[str, Any]], *, timeout_s: float = 30.0) -> dict[str, Any]:
        """Execute `fn` in an isolated `os.fork()` CoW child and return its JSON dict."""
        if not self._warmed:
            self.prewarm()
        t0 = time.perf_counter_ns()
        if not hasattr(os, "fork"):
            out = dict(fn())
            out["zygote_isolated"] = False
            out["zygote_dispatch_ms"] = round((time.perf_counter_ns() - t0) / 1e6, 3)
            return out

        r_fd, w_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(r_fd)
            try:
                res = dict(fn())
                _write_frame(w_fd, {"ok": True, "result": res})
            except BaseException as exc:  # noqa: BLE001
                try:
                    _write_frame(w_fd, {"ok": False, "error": f"{type(exc).__name__}:{exc}"})
                except Exception:
                    pass
            finally:
                try:
                    os.close(w_fd)
                except OSError:
                    pass
                os._exit(0)

        os.close(w_fd)
        try:
            deadline = time.monotonic() + max(0.1, float(timeout_s))
            frame = _read_frame(r_fd)
            _, status = os.waitpid(pid, 0)
            _ = deadline, status
        finally:
            try:
                os.close(r_fd)
            except OSError:
                pass

        if not frame.get("ok"):
            return {
                "schema": SCHEMA,
                "ok": False,
                "pass": False,
                "error": frame.get("error"),
                "zygote_isolated": True,
                "zygote_dispatch_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
            }
        result = dict(frame["result"])
        result["zygote_isolated"] = True
        result["zygote_dispatch_ms"] = round((time.perf_counter_ns() - t0) / 1e6, 3)
        return result

    def route_isolated(self, goal: str, *, top_k: int = 5) -> dict[str, Any]:
        """Route `goal` inside an isolated CoW child at warm RAM speed (~1.5 ms)."""
        if not self._warmed:
            self.prewarm()
        model = self._model
        return self.run_isolated(lambda: model.route(goal, top_k=top_k))

    def solve_or_learn_isolated(self, request: Mapping[str, Any] | str, **kwargs: Any) -> dict[str, Any]:
        """Run `solve_or_learn` inside an isolated CoW child with pre-warmed caches."""
        if not self._warmed:
            self.prewarm()
        from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn
        return self.run_isolated(lambda: solve_or_learn(request, **kwargs))

    def run_parallel_sharded(
        self,
        shard_fns: list[Callable[[], Mapping[str, Any]]],
        *,
        winner_predicate: Callable[[dict[str, Any]], bool] | None = None,
        timeout_s: float = 15.0,
    ) -> dict[str, Any]:
        """Fork `N` concurrent CoW workers in parallel; return first winner immediately & `SIGTERM` siblings."""
        import select
        import signal

        if not self._warmed:
            self.prewarm()
        t0 = time.perf_counter_ns()
        if not shard_fns:
            return {"schema": SCHEMA, "found_winner": False, "results": [], "elapsed_ms": 0.0}

        if not hasattr(os, "fork") or len(shard_fns) == 1:
            results: list[dict[str, Any]] = []
            for idx, fn in enumerate(shard_fns):
                r = self.run_isolated(fn, timeout_s=timeout_s)
                r["shard_index"] = idx
                results.append(r)
                if winner_predicate is not None and winner_predicate(r):
                    return {
                        "schema": SCHEMA,
                        "found_winner": True,
                        "winning_shard": idx,
                        "winner": r,
                        "results": results,
                        "siblings_cancelled": 0,
                        "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
                    }
            return {
                "schema": SCHEMA,
                "found_winner": False,
                "results": results,
                "siblings_cancelled": 0,
                "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
            }

        fd_to_child: dict[int, tuple[int, int]] = {}  # r_fd -> (pid, shard_idx)
        for idx, fn in enumerate(shard_fns):
            r_fd, w_fd = os.pipe()
            pid = os.fork()
            if pid == 0:
                # Close pipes opened for earlier sibling forks
                for prev_r in list(fd_to_child):
                    try:
                        os.close(prev_r)
                    except OSError:
                        pass
                os.close(r_fd)
                try:
                    res = dict(fn())
                    _write_frame(w_fd, {"ok": True, "result": res})
                except BaseException as exc:  # noqa: BLE001
                    try:
                        _write_frame(w_fd, {"ok": False, "error": f"{type(exc).__name__}:{exc}"})
                    except Exception:
                        pass
                finally:
                    try:
                        os.close(w_fd)
                    except OSError:
                        pass
                    os._exit(0)
            os.close(w_fd)
            fd_to_child[r_fd] = (pid, idx)

        deadline = time.monotonic() + max(0.1, float(timeout_s))
        collected: list[dict[str, Any]] = []
        winner: dict[str, Any] | None = None
        winning_shard = -1
        cancelled = 0

        try:
            while fd_to_child:
                rem = deadline - time.monotonic()
                if rem <= 0:
                    break
                ready, _, _ = select.select(list(fd_to_child.keys()), [], [], min(rem, 0.25))
                for r_fd in ready:
                    pid, s_idx = fd_to_child.pop(r_fd)
                    try:
                        frame = _read_frame(r_fd)
                    except Exception as exc:
                        frame = {"ok": False, "error": f"{type(exc).__name__}:{exc}"}
                    finally:
                        try:
                            os.close(r_fd)
                        except OSError:
                            pass
                        try:
                            os.waitpid(pid, 0)
                        except ChildProcessError:
                            pass

                    item = dict(frame.get("result") or {}) if frame.get("ok") else {"ok": False, "error": frame.get("error")}
                    item["shard_index"] = s_idx
                    item["zygote_isolated"] = True
                    collected.append(item)
                    if winner_predicate is not None and frame.get("ok") and winner_predicate(item):
                        winner = item
                        winning_shard = s_idx
                        break
                if winner is not None:
                    break
        finally:
            # Cancel & reap any still-running sibling workers immediately!
            for r_fd, (sib_pid, _) in list(fd_to_child.items()):
                fd_to_child.pop(r_fd, None)
                try:
                    os.kill(sib_pid, signal.SIGTERM)
                    cancelled += 1
                except OSError:
                    pass
                try:
                    os.close(r_fd)
                except OSError:
                    pass
                try:
                    os.waitpid(sib_pid, 0)
                except ChildProcessError:
                    pass

        return {
            "schema": SCHEMA,
            "found_winner": winner is not None,
            "winning_shard": winning_shard,
            "winner": winner,
            "results": sorted(collected, key=lambda d: int(d.get("shard_index", 0))),
            "siblings_cancelled": cancelled,
            "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
        }


_DEFAULT_POOL: ZygotePrewarmedPool | None = None


def default_zygote_pool() -> ZygotePrewarmedPool:
    global _DEFAULT_POOL
    if _DEFAULT_POOL is None:
        _DEFAULT_POOL = ZygotePrewarmedPool()
        _DEFAULT_POOL.prewarm()
    return _DEFAULT_POOL


def screen_python_candidates_cow(
    project_root: str | pathlib.Path,
    target_path: str,
    test_paths: list[str] | tuple[str, ...],
    candidates: list[str] | tuple[str, ...],
    *,
    stop_on_first_pass: bool = True,
    timeout_s: float = 8.0,
) -> dict[str, Any]:
    """Screen `candidates` inside ONE `os.fork()` CoW child + hardlink CoW sandbox (~2-5 ms total).

    Never grants acceptance authority: callers MUST still verify shortlisted candidates via
    `ProjectTestOracle` / `evaluate(..., 'TEST_SUITE', scope_id)`.
    """
    import contextlib
    import importlib
    import importlib.util
    import inspect
    import io
    import select
    import signal
    import sys
    import tempfile
    import unittest
    from canonical.swe_kernel.cow_impact_repair_engine_v1 import create_zero_copy_cow_workspace

    t0 = time.perf_counter_ns()
    cand_list = list(candidates)
    if not cand_list or not hasattr(os, "fork"):
        return {
            "schema": SCHEMA,
            "ok": False,
            "screen_authoritative": False,
            "passing_indices": list(range(len(cand_list))),
            "elapsed_ms": 0.0,
        }

    root_p = pathlib.Path(project_root).resolve()
    tpaths = [str(tp) for tp in test_paths]

    r_fd, w_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(r_fd)
        try:
            passing: list[int] = []
            authoritative = True
            with tempfile.TemporaryDirectory(prefix="brain_zygote_screen_") as td:
                cow_dir = pathlib.Path(td) / "ws"
                create_zero_copy_cow_workspace(root_p, cow_dir)
                cow_str = str(cow_dir.resolve())
                sys.dont_write_bytecode = True
                for pc in list(cow_dir.rglob("__pycache__")):
                    import shutil as _shutil

                    _shutil.rmtree(pc, ignore_errors=True)
                ws_roots = {p.stem for p in cow_dir.rglob("*.py")} | {
                    p.parent.name for p in cow_dir.rglob("__init__.py")
                }
                for mname in list(sys.modules):
                    top = mname.split(".", 1)[0]
                    if top in ws_roots:
                        sys.modules.pop(mname, None)
                sys.path.insert(0, cow_str)
                if (cow_dir / "src").is_dir():
                    sys.path.insert(0, str((cow_dir / "src").resolve()))
                os.chdir(cow_str)
                target_fp = cow_dir / target_path

                for idx, cand_src in enumerate(cand_list):
                    # Unlink hardlink BEFORE writing candidate bytes so `root_p` is never mutated!
                    target_fp.unlink(missing_ok=True)
                    target_fp.write_text(cand_src, encoding="utf-8")

                    for mname, mod in list(sys.modules.items()):
                        mfile = getattr(mod, "__file__", None) or ""
                        if mfile.startswith(cow_str) or mname.split(".", 1)[0] in ws_roots:
                            sys.modules.pop(mname, None)
                    importlib.invalidate_caches()

                    cand_ok = True
                    ran_count = 0
                    sink = io.StringIO()
                    try:
                        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                            for tp_idx, rel_tp in enumerate(tpaths):
                                tfp = cow_dir / rel_tp
                                mod_name = f"_brain_zyg_test_{idx}_{tp_idx}"
                                spec = importlib.util.spec_from_file_location(mod_name, tfp)
                                if spec is None or spec.loader is None:
                                    authoritative = False
                                    cand_ok = False
                                    break
                                mod = importlib.util.module_from_spec(spec)
                                sys.modules[mod_name] = mod
                                spec.loader.exec_module(mod)

                                suite = unittest.defaultTestLoader.loadTestsFromModule(mod)
                                n_ut = suite.countTestCases()
                                if n_ut > 0:
                                    res_ut = unittest.TextTestRunner(stream=sink, verbosity=0).run(suite)
                                    ran_count += int(res_ut.testsRun)
                                    if not res_ut.wasSuccessful():
                                        cand_ok = False
                                        break
                                else:
                                    # Plain function / top-level assert style tests
                                    fn_tests = [
                                        obj
                                        for nm, obj in vars(mod).items()
                                        if nm.startswith("test_") and inspect.isfunction(obj)
                                    ]
                                    if fn_tests:
                                        for fn_t in fn_tests:
                                            sig = inspect.signature(fn_t)
                                            req_params = [
                                                p
                                                for p in sig.parameters.values()
                                                if p.default is inspect.Parameter.empty
                                                and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
                                            ]
                                            if req_params:
                                                # Pytest fixture needed -> fall back to full ProjectTestOracle
                                                authoritative = False
                                                cand_ok = False
                                                break
                                            fn_t()
                                            ran_count += 1
                                        if not cand_ok or not authoritative:
                                            break
                                    else:
                                        # Top-level assertions executed cleanly during `exec_module`
                                        src_tp = tfp.read_text(encoding="utf-8", errors="replace")
                                        if "assert " in src_tp:
                                            ran_count += 1
                                        else:
                                            authoritative = False
                                            cand_ok = False
                                            break
                    except BaseException:  # noqa: BLE001
                        cand_ok = False

                    if not authoritative:
                        break
                    if cand_ok and ran_count > 0:
                        passing.append(idx)
                        if stop_on_first_pass:
                            break

            _write_frame(
                w_fd,
                {
                    "ok": True,
                    "screen_authoritative": authoritative,
                    "passing_indices": passing,
                },
            )
        except BaseException as exc:  # noqa: BLE001
            try:
                _write_frame(
                    w_fd,
                    {"ok": False, "screen_authoritative": False, "error": f"{type(exc).__name__}:{exc}"},
                )
            except Exception:
                pass
        finally:
            try:
                os.close(w_fd)
            except OSError:
                pass
            os._exit(0)

    os.close(w_fd)
    frame: dict[str, Any] = {"ok": False, "screen_authoritative": False}
    try:
        ready, _, _ = select.select([r_fd], [], [], max(0.2, float(timeout_s)))
        if ready:
            frame = _read_frame(r_fd)
        else:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    except Exception:
        frame = {"ok": False, "screen_authoritative": False}
    finally:
        try:
            os.close(r_fd)
        except OSError:
            pass
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass

    elapsed_ms = round((time.perf_counter_ns() - t0) / 1e6, 3)
    if not frame.get("ok") or not frame.get("screen_authoritative"):
        return {
            "schema": SCHEMA,
            "ok": False,
            "screen_authoritative": False,
            "passing_indices": list(range(len(cand_list))),
            "elapsed_ms": elapsed_ms,
        }
    return {
        "schema": SCHEMA,
        "ok": True,
        "screen_authoritative": True,
        "passing_indices": [int(i) for i in (frame.get("passing_indices") or [])],
        "elapsed_ms": elapsed_ms,
    }
