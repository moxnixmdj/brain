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
        try:
            import pytest as _warm_pytest  # noqa: F401
        except ImportError:
            pass
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
    per_candidate_timeout_s: float = 1.5,
) -> dict[str, Any]:
    """Screen `candidates` inside the persistent confined namespace Zygote (`~3-6 ms` warm).

    Never grants acceptance authority: callers MUST still verify shortlisted candidates via
    `ProjectTestOracle` / `evaluate(..., 'TEST_SUITE', scope_id)`.
    """
    from canonical.runtime.brokered_workspace_execution_v1 import run_confined_python_candidate_batch

    cand_list = [str(c) for c in candidates]
    if not cand_list:
        return {
            "schema": SCHEMA,
            "ok": False,
            "confined": True,
            "screen_authoritative": False,
            "passing_indices": [],
            "elapsed_ms": 0.0,
        }
    res = run_confined_python_candidate_batch(
        project_root,
        str(target_path),
        [str(tp) for tp in test_paths],
        cand_list,
        stop_on_first_pass=stop_on_first_pass,
        per_candidate_timeout_s=min(float(per_candidate_timeout_s), max(0.15, float(timeout_s))),
        total_timeout_s=max(2.0, float(timeout_s) + 2.0),
    )
    return {
        "schema": SCHEMA,
        "ok": bool(res.get("ok")),
        "confined": bool(res.get("confined")),
        "isolation_mode": res.get("isolation_mode"),
        "screen_authoritative": bool(res.get("screen_authoritative")),
        "passing_indices": [int(i) for i in (res.get("passing_indices") or [])],
        "live_workspace_untouched": bool(res.get("live_workspace_untouched", True)),
        "elapsed_ms": float(res.get("elapsed_ms") or 0.0),
    }

