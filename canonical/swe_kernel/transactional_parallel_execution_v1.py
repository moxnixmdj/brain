"""Wave 3 Spine — Transactional CoW Rollback, Kernel Confinement, Parallel Frontier & Measured-Latency Routing (`K3 = 0`).

Composes existing runtime organs into a zero-LLM parallel & transactional execution spine:
  1. `canonical_tree_attestation_v1.tree_manifest` + `create_zero_copy_cow_workspace`:
     All mutating actions stage inside a zero-copy CoW directory; failed or unverified
     actions discard the CoW clone leaving **0 changed bytes** in the live workspace.
  2. `confine_v1`: Linux user+net+mount namespace confinement (`unshare -Urmn`) for
     untrusted subprocesses with honest `confined` reporting.
  3. `capability_parallel_frontier_v2.plan_parallel_frontier` + `ZygotePrewarmedPool.run_parallel_sharded`:
     Partitions write-disjoint tasks into parallel waves and runs them concurrently across
     forked CoW Zygote workers.
  4. `LatencyReliabilityCostRouter`: Rolling empirical latency + Wilson lower-confidence-bound
     reliability router scoring candidates by `expected_gain / max(measured_ms, 0.5) * reliability_lcb`.
"""
from __future__ import annotations

import math
import os
import pathlib
import shutil
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

from canonical.swe_kernel.cow_impact_repair_engine_v1 import create_zero_copy_cow_workspace
from canonical.swe_kernel.zygote_worker_pool_v1 import ZygotePrewarmedPool

SCHEMA = "PROJECT_BRAIN_TRANSACTIONAL_PARALLEL_EXECUTION_V1"
DEFAULT_EXCLUDE_DIRS = frozenset({".git", "__pycache__", ".pytest_cache", ".mypy_cache", "node_modules", ".venv"})


def snapshot_workspace_manifest(
    workspace_root: str | pathlib.Path,
    *,
    exclude_dirs: frozenset[str] = DEFAULT_EXCLUDE_DIRS,
) -> dict[str, Any]:
    """Compute a deterministic SHA-256 tree manifest via `canonical_tree_attestation_v1.tree_manifest`."""
    from canonical.runtime.canonical_tree_attestation_v1 import tree_manifest

    return dict(tree_manifest(pathlib.Path(workspace_root).resolve(), exclude_dirs=set(exclude_dirs)))


def execute_transactional_cow_action(
    workspace_root: str | pathlib.Path,
    action_fn: Callable[[pathlib.Path], Mapping[str, Any]],
    *,
    verify_fn: Callable[[pathlib.Path, Mapping[str, Any]], bool] | None = None,
    exclude_dirs: frozenset[str] = DEFAULT_EXCLUDE_DIRS,
) -> dict[str, Any]:
    """Stage `action_fn` inside a zero-copy CoW clone; commit ONLY if verified, else rollback with 0 byte drift."""
    t0 = time.perf_counter_ns()
    ws = pathlib.Path(workspace_root).resolve()
    pre_manifest = snapshot_workspace_manifest(ws, exclude_dirs=exclude_dirs)

    with tempfile.TemporaryDirectory(prefix="brain-tx-cow-") as td:
        cow_root = pathlib.Path(td) / "stage"
        clone_stats = create_zero_copy_cow_workspace(ws, cow_root)
        action_out: dict[str, Any] = {}
        err_msg: str | None = None
        try:
            raw_out = action_fn(cow_root)
            action_out = dict(raw_out) if isinstance(raw_out, Mapping) else {"result": raw_out}
        except Exception as exc:
            err_msg = f"{type(exc).__name__}:{exc}"

        if err_msg is not None:
            verified = False
        elif verify_fn is not None:
            try:
                verified = bool(verify_fn(cow_root, action_out))
            except Exception as exc:
                verified = False
                err_msg = f"VERIFY_ERROR:{type(exc).__name__}:{exc}"
        else:
            verified = bool(
                action_out.get("pass") is True
                or action_out.get("verified") is True
                or action_out.get("ok") is True
            )

        if not verified:
            post_rollback_manifest = snapshot_workspace_manifest(ws, exclude_dirs=exclude_dirs)
            return {
                "schema": SCHEMA + "/transaction",
                "committed": False,
                "rolled_back": True,
                "zero_byte_drift_verified": (
                    post_rollback_manifest["tree_sha256"] == pre_manifest["tree_sha256"]
                ),
                "pre_manifest_sha256": pre_manifest["tree_sha256"],
                "post_manifest_sha256": post_rollback_manifest["tree_sha256"],
                "error": err_msg,
                "action_output": action_out,
                "clone": clone_stats,
                "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
            }

        # Verified! Sync delta (`cow_manifest` vs `pre_manifest`) atomically into `ws`.
        cow_manifest = snapshot_workspace_manifest(cow_root, exclude_dirs=exclude_dirs)
        pre_files = {row["path"]: row["sha256"] for row in pre_manifest.get("files", [])}
        cow_files = {row["path"]: row["sha256"] for row in cow_manifest.get("files", [])}

        files_updated: list[str] = []
        files_deleted: list[str] = []
        for rel_p, new_sha in cow_files.items():
            if pre_files.get(rel_p) != new_sha:
                dst = ws / rel_p
                dst.parent.mkdir(parents=True, exist_ok=True)
                tmp_dst = dst.with_name(f".{dst.name}.tx.{os.getpid()}")
                shutil.copy2(cow_root / rel_p, tmp_dst)
                os.replace(tmp_dst, dst)
                files_updated.append(rel_p)

        for rel_p in set(pre_files) - set(cow_files):
            target = ws / rel_p
            if target.is_file():
                target.unlink()
                files_deleted.append(rel_p)

        post_commit_manifest = snapshot_workspace_manifest(ws, exclude_dirs=exclude_dirs)
        return {
            "schema": SCHEMA + "/transaction",
            "committed": True,
            "rolled_back": False,
            "files_updated": sorted(files_updated),
            "files_deleted": sorted(files_deleted),
            "pre_manifest_sha256": pre_manifest["tree_sha256"],
            "post_manifest_sha256": post_commit_manifest["tree_sha256"],
            "action_output": action_out,
            "clone": clone_stats,
            "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
        }


def run_confined_command(
    argv: Sequence[str],
    *,
    cwd: str | pathlib.Path,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Run `argv` through `canonical.runtime.confine_v1` (Linux namespace jail when available)."""
    from canonical.runtime import confine_v1

    work_dir = pathlib.Path(cwd).resolve()
    is_avail = bool(confine_v1.available())
    if is_avail:
        proc = confine_v1.run([str(x) for x in argv], cwd=work_dir, timeout=timeout)
        return {
            "schema": SCHEMA + "/confined_exec",
            "confined": True,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    import subprocess

    proc = subprocess.run(
        [str(x) for x in argv],
        cwd=str(work_dir),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "schema": SCHEMA + "/confined_exec",
        "confined": False,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def execute_parallel_frontier_in_zygote(
    frontier: Sequence[Mapping[str, Any]],
    *,
    root: str | pathlib.Path,
    task_runner: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    zygote: ZygotePrewarmedPool | None = None,
    timeout_s: float = 15.0,
) -> dict[str, Any]:
    """Partition `frontier` into write-disjoint parallel waves via `capability_parallel_frontier_v2` & run in Zygote."""
    from canonical.runtime.capability_parallel_frontier_v2 import plan_parallel_frontier

    t0 = time.perf_counter_ns()
    work_root = pathlib.Path(root).resolve()
    plan = plan_parallel_frontier([dict(item) for item in frontier], root=work_root)
    pool = zygote or ZygotePrewarmedPool()

    # Build lookup by `task_id` or `capability_id` or index
    items = [dict(item) for item in frontier]
    by_id: dict[str, dict[str, Any]] = {}
    for idx, it in enumerate(items):
        tid = str(it.get("task_id") or it.get("id") or it.get("capability_id") or f"task_{idx}")
        by_id[tid] = it

    raw_waves = plan.get("waves") or plan.get("parallel_groups") or []
    wave_results: list[dict[str, Any]] = []
    if raw_waves:
        for wave in raw_waves:
            wave_tasks: list[dict[str, Any]] = []
            entries = wave.get("tasks") if isinstance(wave, Mapping) else wave
            for entry in entries or []:
                if isinstance(entry, Mapping):
                    tid = str(entry.get("task_id") or entry.get("id") or entry.get("capability_id") or "")
                    wave_tasks.append(by_id.get(tid, dict(entry)))
                else:
                    tid = str(entry)
                    if tid in by_id:
                        wave_tasks.append(by_id[tid])
            if not wave_tasks:
                continue
            shards = [(lambda t=task: dict(task_runner(t))) for task in wave_tasks]
            wave_out = pool.run_parallel_sharded(shards, timeout_s=timeout_s)
            wave_results.append(wave_out)
    else:
        shards = [(lambda t=task: dict(task_runner(t))) for task in items]
        wave_results.append(pool.run_parallel_sharded(shards, timeout_s=timeout_s))

    return {
        "schema": SCHEMA + "/parallel_frontier",
        "plan": plan,
        "wave_count": len(wave_results),
        "waves": wave_results,
        "elapsed_ms": round((time.perf_counter_ns() - t0) / 1e6, 3),
    }


# ---------------------------------------------------------------------------
# Measured Latency + Wilson LCB Reliability Cost Router
# ---------------------------------------------------------------------------


def wilson_lower_bound(successes: int, failures: int, z: float = 1.28) -> float:
    """80% Wilson score lower confidence bound with Laplace prior `(s+1, f+0.25)` so unseen probes start fair."""
    s = max(0.0, float(successes)) + 1.0
    f = max(0.0, float(failures)) + 0.25
    n = s + f
    phat = s / n
    denom = 1.0 + (z * z) / n
    center = phat + (z * z) / (2.0 * n)
    rad = z * math.sqrt((phat * (1.0 - phat) + (z * z) / (4.0 * n)) / n)
    return max(0.01, (center - rad) / denom)


class LatencyReliabilityCostRouter:
    """Empirical cost-per-bit router scoring `expected_gain / max(measured_ms, 0.5) * reliability_lcb`."""

    def __init__(self, *, ema_alpha: float = 0.35) -> None:
        self.ema_alpha = float(ema_alpha)
        self._stats: dict[str, dict[str, float]] = {}

    def record_observation(self, key: str, *, elapsed_ms: float, ok: bool) -> dict[str, float]:
        ms = max(0.05, float(elapsed_ms))
        row = self._stats.get(key)
        if row is None:
            row = {"ema_ms": ms, "successes": 0.0, "failures": 0.0}
            self._stats[key] = row
        else:
            row["ema_ms"] = self.ema_alpha * ms + (1.0 - self.ema_alpha) * row["ema_ms"]
        if ok:
            row["successes"] += 1.0
        else:
            row["failures"] += 1.0
        return dict(row)

    def score_candidate(
        self,
        key: str,
        *,
        expected_gain: float,
        default_cost_ms: float = 10.0,
    ) -> dict[str, float]:
        row = self._stats.get(key)
        measured_ms = float(row["ema_ms"]) if row is not None else max(0.5, float(default_cost_ms))
        succ = int(row["successes"]) if row is not None else 0
        fail = int(row["failures"]) if row is not None else 0
        rel_lcb = wilson_lower_bound(succ, fail)
        eff_cost = max(0.5, measured_ms)
        utility_rate = (max(0.0, float(expected_gain)) / eff_cost) * rel_lcb
        return {
            "measured_ms": round(measured_ms, 4),
            "reliability_lcb": round(rel_lcb, 4),
            "utility_per_ms": round(utility_rate, 6),
        }

    def rank_candidates(self, candidates: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        """Rank candidate dicts containing `id`/`probe_id`, `expected_gain`, and optional `cost_ms`."""
        scored: list[dict[str, Any]] = []
        for cand in candidates:
            c = dict(cand)
            cid = str(c.get("probe_id") or c.get("capability_id") or c.get("id") or "")
            gain = float(c.get("expected_gain") if c.get("expected_gain") is not None else 1.0)
            def_ms = float(c.get("cost_ms") if c.get("cost_ms") is not None else 10.0)
            metrics = self.score_candidate(cid, expected_gain=gain, default_cost_ms=def_ms)
            c.update(metrics)
            scored.append(c)
        scored.sort(key=lambda d: (-d["utility_per_ms"], d["measured_ms"], str(d.get("probe_id") or d.get("id") or "")))
        return scored


_DEFAULT_COST_ROUTER = LatencyReliabilityCostRouter()


def default_cost_router() -> LatencyReliabilityCostRouter:
    return _DEFAULT_COST_ROUTER
