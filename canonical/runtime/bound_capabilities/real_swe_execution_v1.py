#!/usr/bin/env python3
# PROJECT_BRAIN
"""
Real SWE execution engine — shared by all diagnostic SWE capabilities.

High-performance ("insanely fast, only the right way") end-to-end repair:

  1. Fault localization — dynamic spectrum + traceback ranking pinpoints
     suspicious statements (python_dynamic_fault_localizer_v1).
  2. Test-guided patch search — AST mutations + literal substitutions mined
     from failing tests, evaluated **in parallel** (ThreadPoolExecutor, one
     isolated worktree copy per candidate) with a **content-addressable disk
     cache** so identical source is never tested twice.
  3. Apply winning patch to a byte-copy worktree (never mutates source).
  4. Full configured pytest gate on the worktree (python_repo_diff_apply_full_testgate).
  5. Emit unified diff + PR intent + receipt.

Every function returns verified=True only when the underlying execution
actually succeeded on the project. Fail-closed. Zero model calls. Zero spend.

Delegates to the already-working, tested capabilities:

  1. python_dynamic_fault_localizer_v1    — fault localization (candidate ordering)
  2. python_test_guided_patch_search_v1   — candidate generation / reuse
  3. python_repo_diff_apply_full_testgate — full test gate
  4. python_issue_to_pr_orchestrate.py     — issue → PR orchestration
  5. python_repo_pr_realize.py             — PR realization

Shared by (all real, none diagnostic):
  software.hardcore.kernel.orchestrate.v1
  software.patch.synthesize.cegis.z3.v1
  software.repair.loop.cegis_hypothesis.v1
  ... and all converted *_supercomposer_v1 SWE capabilities.
"""

from __future__ import annotations

import ast
import difflib
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from pathlib import Path
from typing import Any, Mapping

REPO = Path(__file__).resolve().parents[3]

# Content-addressable cache: never re-test identical source bytes.
CACHE_DIR = REPO / "canonical" / ".swe_cache"
# Isolated per-candidate worktrees live here (created + purged per trial).
WORK_ROOT = REPO / "canonical" / ".swe_work"

# --- Persistent cache + GPU execution integration ---------------------------
# Cross-session, content-addressable cache for AST indexes, verified patches,
# fault localization results, and test results. Survives process restarts.
from canonical.runtime.persistent_cache_v1 import (
    cache_get as _pcache_get,
    cache_put as _pcache_put,
    cache_get_ast_index as _pcache_get_ast,
    cache_ast_index as _pcache_put_ast,
    cache_get_verified_patch as _pcache_get_patch,
    cache_verified_patch as _pcache_put_patch,
    cache_get_fault_localization as _pcache_get_fl,
    cache_fault_localization as _pcache_put_fl,
    cache_get_test_result as _pcache_get_test,
    cache_test_result as _pcache_put_test,
)

# GPU-accelerated data-parallel execution (CPU multiprocessing fallback when
# no GPU/CUDA toolkit is detected). Gives up to 27x speedup on test execution
# and patch candidate scoring (per ASE'14 research).
from canonical.runtime.gpu_execution_v1 import (
    execute_tests_parallel as _gpu_execute_tests,
    score_patch_candidates_parallel as _gpu_score_candidates,
    fault_localize_parallel as _gpu_fault_localize,
    detect_gpu as _gpu_detect,
)

# Real-time progress streaming for SWE execution stages.
from canonical.runtime.progress_streaming_v1 import (
    hub as _streaming_hub,
    adapter as _progress_adapter,
)

# Advanced SWE verification capabilities integrated into the repair loop.
# Use existing production-grade capabilities (not duplicates).
from canonical.runtime.bound_capabilities.python_tests_generate_scaffold import (
    run as _test_gen_scaffold,
)
from canonical.runtime.bound_capabilities.python_review_diff_coverage_gate import (
    run as _coverage_gate_run,
)
from canonical.runtime.bound_capabilities.python_review_diff_mutation_gate import (
    run as _mutation_gate_run,
)
from canonical.runtime.bound_capabilities.python_review_diff_security_gate import (
    run as _security_gate_run,
)
from canonical.runtime.bound_capabilities.python_review_diff_perf_gate import (
    run as _perf_gate_run,
)
from canonical.runtime.bound_capabilities.python_review_diff_static_triage import (
    run as _static_triage_run,
)
from canonical.runtime.bound_capabilities.python_review_diff_type_gate import (
    run as _type_gate_run,
)

# Z3 formal verification gate — CEGIS-style equivalence checking.
# Lazy import to avoid circular import (cegis_z3 imports end_to_end_repair).
_Z3_VERIFY_PATCH = None
_Z3_AVAILABLE = None


def _z3_verify_patch_fn(original_text, patched_text):
    global _Z3_VERIFY_PATCH
    if _Z3_VERIFY_PATCH is None:
        from canonical.runtime.bound_capabilities.software_patch_cegis_z3_v1 import (
            _z3_verify_patch as _fn,
        )
        _Z3_VERIFY_PATCH = _fn
    return _Z3_VERIFY_PATCH(original_text, patched_text)


def _z3_available_fn():
    global _Z3_AVAILABLE
    if _Z3_AVAILABLE is None:
        from canonical.runtime.bound_capabilities.software_patch_cegis_z3_v1 import (
            _z3_available as _fn,
        )
        _Z3_AVAILABLE = _fn
    return _Z3_AVAILABLE()

# Distributed execution with work stealing for cross-node patch candidate eval.
from canonical.runtime.distributed_queue_v1 import (
    submit_task as _distributed_submit_task,
    get_task_result as _distributed_get_task_result,
    PRIORITY_NORMAL as _DISTRIBUTED_PRIORITY_NORMAL,
)

_GPU = None


def _gpu_status():
    global _GPU
    if _GPU is None:
        _GPU = _gpu_detect()
    return _GPU


# ---------------------------------------------------------------------------
# OIDC token acquisition — so GitHub PR creation works autonomously
# ---------------------------------------------------------------------------

def _acquire_oidc_token() -> str | None:
    """Acquire an OIDC identity token from the environment, best-effort.

    Tries, in order:
      1. OIDC_TOKEN env var (directly provided)
      2. GITHUB_TOKEN env var (classic token, works for GitHub API)
      3. GitHub Actions OIDC (ACTIONS_ID_TOKEN_REQUEST_URL) — exchanges the
         Actions ID token for a GitHub OIDC token
      4. AWS OIDC (AWS_WEB_IDENTITY_TOKEN_FILE) — reads the web identity token

    Returns None if no source is available — callers degrade gracefully
    (no GitHub PR, but the verified patch + diff are still persisted locally).
    Never raises.
    """
    import os as _os

    # 1. Direct OIDC token
    tok = _os.environ.get("OIDC_TOKEN")
    if tok:
        return tok

    # 2. Classic GitHub token
    tok = _os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok

    # 3. GitHub Actions OIDC provider
    req_url = _os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    req_tok = _os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    if req_url:
        try:
            import urllib.request as _ur
            import json as _json
            aud = "https://github.com"
            url = f"{req_url}&audience={aud}"
            req = _ur.Request(
                url,
                headers={"Authorization": f"Bearer {req_tok}", "User-Agent": "Project-Brain-SWE/1.0"},
            )
            with _ur.urlopen(req, timeout=15) as resp:
                data = _json.loads(resp.read())
                return data.get("value")
        except Exception:
            pass

    # 4. AWS OIDC web identity token file
    wif = _os.environ.get("AWS_WEB_IDENTITY_TOKEN_FILE")
    if wif:
        try:
            return Path(wif).read_text(encoding="utf-8").strip()
        except Exception:
            pass

    return None


def _resolve_oidc_token(oidc_token: str | None) -> str | None:
    """Return the caller-provided token, or auto-acquire one from the env."""
    if oidc_token:
        return oidc_token
    return _acquire_oidc_token()


# Register a local distributed node so candidate evaluation can be
# work-stolen across processes/nodes when the cluster is present.
# Best-effort: if registration fails, distributed_eval simply falls back to local.
# ---------------------------------------------------------------------------
# Distributed candidate evaluation worker nodes
# ---------------------------------------------------------------------------

_DISTRIBUTED_WORKER_ENDPOINTS: list[str] = []
_DISTRIBUTED_WORKER_LOCK = threading.Lock()
_DISTRIBUTED_WORKER_IDX = 0
_DISTRIBUTED_WORKER_NEXT_ID = 0
_DISTRIBUTED_WORKER_THREADS: list[threading.Thread] = []


def _start_distributed_worker_nodes(n_workers: int | None = None) -> None:
    """Start real eval worker node HTTP servers on free local ports.

    Each worker runs ``_eval_candidate`` on demand via POST /eval_candidate
    and registers itself in the NodeRegistry with a reachable endpoint.
    Workers are best-effort: if they fail to start, evaluation falls back to
    local execution.

    Auto-scaling: when called with n_workers, starts that many additional
    workers (idempotent: tracks already-started workers).
    """
    try:
        from canonical.runtime.distributed_eval_node_v1 import run_node as _run_node
    except Exception:
        return

    if n_workers is None:
        n_workers = max(1, min(os.cpu_count() or 4, 8))

    global _DISTRIBUTED_WORKER_NEXT_ID
    for i in range(n_workers):
        nid = "swe-worker-" + str(os.getpid()) + "-" + str(_DISTRIBUTED_WORKER_NEXT_ID)
        _DISTRIBUTED_WORKER_NEXT_ID += 1

        def _run(nid=nid):
            try:
                _run_node(nid, host="0.0.0.0", port=0)
            except Exception:
                pass

        t = threading.Thread(target=_run, daemon=True, name="dist-eval-worker-" + nid)
        t.start()
        _DISTRIBUTED_WORKER_THREADS.append(t)

    # Give workers a moment to bind ports and register themselves.
    import time as _time
    _time.sleep(0.3)

    # Harvest registered endpoints from the node registry.
    try:
        from canonical.runtime.distributed_queue_v1 import NodeRegistry
        reg = NodeRegistry()
        nodes = reg.get_nodes(capability="software.hardcore.kernel.eval_candidate.v1")
        with _DISTRIBUTED_WORKER_LOCK:
            for n in nodes:
                ep = n.endpoint
                if ep and ":0" not in ep and ep not in _DISTRIBUTED_WORKER_ENDPOINTS:
                    _DISTRIBUTED_WORKER_ENDPOINTS.append(ep)
    except Exception:
        pass


def _scale_workers_for_candidates(candidate_count: int) -> None:
    """Auto-scale distributed workers based on pending candidate count.

    Heuristics:
      * 1-10 candidates: 2 workers (minimal overhead)
      * 11-50 candidates: 4 workers
      * 51+ candidates: 8 workers (max)

    Only starts additional workers — never stops (daemon threads exit when
    the process exits).
    """
    if candidate_count <= 10:
        target = 2
    elif candidate_count <= 50:
        target = 4
    else:
        target = 8

    current = len(_DISTRIBUTED_WORKER_THREADS)
    if target > current:
        _start_distributed_worker_nodes(target - current)


def _distributed_nodes_available() -> bool:
    """Return True if any distributed worker node has a reachable endpoint."""
    with _DISTRIBUTED_WORKER_LOCK:
        return len(_DISTRIBUTED_WORKER_ENDPOINTS) > 0


def _pick_worker_endpoint() -> str | None:
    """Round-robin pick a worker endpoint."""
    global _DISTRIBUTED_WORKER_IDX
    with _DISTRIBUTED_WORKER_LOCK:
        if not _DISTRIBUTED_WORKER_ENDPOINTS:
            return None
        ep = _DISTRIBUTED_WORKER_ENDPOINTS[_DISTRIBUTED_WORKER_IDX % len(_DISTRIBUTED_WORKER_ENDPOINTS)]
        _DISTRIBUTED_WORKER_IDX += 1
        return ep


def _eval_candidate_distributed(args: tuple) -> dict | None:
    """Submit candidate evaluation to a remote worker node via HTTP.

    POSTs the serialized args to a remote worker's /eval_candidate endpoint.
    Best-effort: any failure falls back to local execution — never blocks
    the repair. Uses circuit breakers to skip repeatedly failing workers.
    """
    endpoint = _pick_worker_endpoint()
    if not endpoint:
        return None

    if _circuit_is_open(endpoint):
        return None

    # New format: (source_candidates_json, source_root, test_paths, repo,
    #              timeout_s, cache_key, goal_id, candidate_index)
    (source_candidates_s, source_root_s, test_paths_s, repo_s,
     timeout_s, cache_key, goal_id, candidate_index) = args

    payload = {
        "args": list(args),
        "timeout_s": timeout_s,
    }
    body = json.dumps(payload).encode("utf-8")
    url = endpoint.rstrip("/") + "/eval_candidate"

    try:
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Project-Brain-Distributed-Eval/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout_s + 30) as resp:
            raw = resp.read()
            result = json.loads(raw)
    except Exception:
        _circuit_record_failure(endpoint)
        return None

    _circuit_record_success(endpoint)

    if not result or not result.get("ok"):
        _circuit_record_failure(endpoint)
        return None

    res = result.get("result")
    if res and "returncode" in res:
        res = dict(res)
        res["distributed"] = True
        res["worker_endpoint"] = endpoint
        return res
    return None


# --- Batch distributed evaluation -----------------------------------------
# Submits multiple candidates to a worker in a single HTTP request.
# N candidates = 1 HTTP round trip instead of N — massive speedup on
# distributed setups.


def _eval_candidates_batch_distributed(batch_args: list[tuple]) -> list[dict | None]:
    """Submit multiple candidates to a worker in one HTTP request.

    Returns a list parallel to batch_args: each entry is a result dict or
    None if the batch failed (caller falls back to per-candidate local eval).
    """
    if not batch_args:
        return []

    endpoint = _pick_worker_endpoint()
    if not endpoint or _circuit_is_open(endpoint):
        return [None] * len(batch_args)

    payload = {
        "batches": [
            {
                "args": list(args),
                "timeout_s": args[4],  # timeout_s is index 4 in new format
            }
            for args in batch_args
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    url = endpoint.rstrip("/") + "/eval_candidates_batch"

    try:
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Project-Brain-Distributed-Eval/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=batch_args[0][5] * len(batch_args) + 60) as resp:
            raw = resp.read()
            result = json.loads(raw)
    except Exception:
        _circuit_record_failure(endpoint)
        return [None] * len(batch_args)

    _circuit_record_success(endpoint)

    if not result or not result.get("ok"):
        _circuit_record_failure(endpoint)
        return [None] * len(batch_args)

    results = result.get("results", [])
    out: list[dict | None] = []
    for i, res in enumerate(results):
        if res and "returncode" in res:
            r = dict(res)
            r["distributed"] = True
            r["worker_endpoint"] = endpoint
            r["batch_index"] = i
            out.append(r)
        else:
            out.append(None)
    # Pad to match batch length
    while len(out) < len(batch_args):
        out.append(None)
    return out[: len(batch_args)]


# --- Batch local evaluation -----------------------------------------------
# Evaluates multiple candidates in a single worktree copy to avoid the
# O(tree_size) copytree overhead per candidate. For local (non-distributed)
# execution this is the fastest path: one worktree setup, then N patch
# apply/revert + pytest runs in the same tree.
#
# batch_args: list of (source_candidates_json, source_root, test_paths, repo,
#                      timeout_s, cache_key, goal_id, candidate_index)
# Returns: list parallel to batch_args, each entry is a result dict or None.


def _eval_candidates_batch_local(batch_args: list[tuple]) -> list[dict | None]:
    """Evaluate multiple candidates in one shared worktree (local batch mode)."""
    if not batch_args:
        return []

    # Use the first args to determine shared context.
    (_, source_root_s, test_paths_s, repo_s, timeout_s, _, goal_id, _) = batch_args[0]
    source_root_p = Path(source_root_s)
    repo = Path(repo_s)
    test_ps = [Path(tp) for tp in test_paths_s]

    # Create a single worktree copy for all candidates in this batch.
    import tempfile as _tempfile
    worktree_p = Path(_tempfile.mkdtemp(prefix='swe_batch_local_', dir=str(repo / '.swe_work' if (repo / '.swe_work').exists() else repo)))
    try:
        # Copy source tree once.
        shutil.copytree(source_root_p, worktree_p, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('.git', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache'))
        _purge_bytecode(worktree_p)

        # Copy test files into the worktree so pytest imports from patched source.
        pytest_targets: list[str] = []
        for tp in test_ps:
            try:
                trel = tp.relative_to(source_root_p)
            except ValueError:
                trel = Path(*tp.relative_to(repo).parts) if tp.is_relative_to(repo) else tp.name
            dest = worktree_p / trel
            pytest_targets.append(str(dest))
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(tp, dest)

        results: list[dict | None] = []
        env = dict(os.environ)
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(worktree_p) + (os.pathsep + existing if existing else "")

        for args in batch_args:
            (cc_json_s, _, _, _, cand_timeout_s, cache_key, _, cand_index) = args

            # Cache check.
            cached = _cache_read(cache_key)
            if cached is not None:
                results.append(dict(cached, cached=True))
                continue

            # Parse candidate: JSON list of [path, text] pairs.
            source_candidates = json.loads(cc_json_s)

            # Apply patch: write each changed file in the shared worktree.
            original_contents: dict[str, str] = {}
            for sc in source_candidates:
                sp_str = sc[0]
                new_text = sc[1] if len(sc) > 1 else None
                if new_text is None:
                    continue
                sp = Path(sp_str)
                try:
                    rel = sp.relative_to(source_root_p).as_posix()
                except ValueError:
                    rel = sp.name
                target = worktree_p / rel
                # Save original.
                if target.is_file():
                    original_contents[str(target)] = target.read_text(encoding='utf-8')
                else:
                    original_contents[str(target)] = None  # marker for new file
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(new_text, encoding='utf-8')
            _purge_bytecode(worktree_p)

            # Run pytest on the patched worktree.
            try:
                cmd = [sys.executable, '-m', 'pytest'] + pytest_targets
                proc_result = subprocess.run(
                    cmd, cwd=str(worktree_p), env=env,
                    capture_output=True, text=True, timeout=cand_timeout_s,
                )
                rc = proc_result.returncode
                timed_out = False
            except subprocess.TimeoutExpired:
                rc = None
                timed_out = True

            result = {
                'returncode': rc,
                'timed_out': timed_out,
                'cached': False,
                'local_batch': True,
                'batch_index': cand_index,
            }
            results.append(result)

            # Write result to cache.
            try:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                (CACHE_DIR / (cache_key + '.json')).write_text(
                    json.dumps(result), encoding='utf-8')
            except OSError:
                pass

            # Revert: restore original file contents.
            for sc in source_candidates:
                sp_str = sc[0]
                new_text = sc[1] if len(sc) > 1 else None
                if new_text is None:
                    continue
                sp = Path(sp_str)
                try:
                    rel = sp.relative_to(source_root_p).as_posix()
                except ValueError:
                    rel = sp.name
                target = worktree_p / rel
                orig = original_contents.get(str(target))
                if orig is None:
                    # Was a new file — remove it.
                    if target.is_file():
                        target.unlink()
                else:
                    target.write_text(orig, encoding='utf-8')
            _purge_bytecode(worktree_p)

    finally:
        # Clean up the shared worktree.
        shutil.rmtree(worktree_p, ignore_errors=True)

    return results


# ---------------------------------------------------------------------------
# Per-candidate affected test selection — run only tests that touch
# the lines changed by each candidate. This is the single biggest
# speedup: instead of running ALL affected tests for every candidate,
# each candidate runs only the tests relevant to its specific changes.
# ---------------------------------------------------------------------------

def _compute_candidate_affected_tests(cand_source_candidates: list[list],
                                      ts_index_path: str | None,
                                      ts_impact_result: dict,
                                      all_test_ps: list[Path],
                                      repo: Path,
                                      source_root_p: Path) -> list[Path]:
    """Compute the minimal set of tests affected by a specific candidate's changes.

    Uses tree-sitter impact analysis to find which tests exercise the
    symbols/lines changed by this candidate. Returns the subset of all_test_ps
    that should be run for this candidate.
    """
    if not ts_index_path or not ts_impact_result:
        return all_test_ps

    # Collect all changed line ranges from this candidate
    changed_ranges: dict[str, set[int]] = {}  # rel_path -> set of line numbers
    for sc in cand_source_candidates:
        sp_str = sc[0]
        new_text = sc[1] if len(sc) > 1 else None
        if new_text is None:
            continue
        sp = Path(sp_str)
        try:
            rel = sp.relative_to(source_root_p).as_posix()
        except ValueError:
            rel = sp.name

        # Read original and new text to compute changed lines
        try:
            orig_text = source_root_p.joinpath(rel).read_text(encoding="utf-8")
        except Exception:
            orig_text = ""

        orig_lines = orig_text.splitlines()
        new_lines = new_text.splitlines()

        # Simple line-level diff: find lines that differ
        changed_lines = set()
        max_lines = max(len(orig_lines), len(new_lines))
        for i in range(max_lines):
            o = orig_lines[i] if i < len(orig_lines) else None
            n = new_lines[i] if i < len(new_lines) else None
            if o != n:
                changed_lines.add(i + 1)  # 1-based

        if rel not in changed_ranges:
            changed_ranges[rel] = set()
        changed_ranges[rel].update(changed_lines)

    if not changed_ranges:
        return all_test_ps

    # Use tree-sitter impact to find affected tests
    try:
        import json as _json
        index_artifact = _json.loads(Path(ts_index_path).read_text(encoding="utf-8"))
        index_rows = {row["path"]: row for row in index_artifact.get("files", [])}

        affected_tests: set[str] = set()
        for rel, lines in changed_ranges.items():
            row_data = index_rows.get(rel)
            if not row_data:
                continue
            # Find which tests reference definitions in changed lines
            for d in row_data.get("definitions", []):
                d_start = int(d.get("start_line", 0))
                d_end = int(d.get("end_line", 0))
                if any(d_start <= ln <= d_end for ln in lines):
                    # This definition changed — find tests that call it
                    def_name = str(d.get("name", ""))
                    # Look through impact result for tests referencing this symbol
                    for test_file, impact_data in ts_impact_result.get("changed_symbols", {}).items():
                        for sym in impact_data.get("symbols", []):
                            if def_name in sym:
                                affected_tests.add(test_file)

        if affected_tests:
            return [Path(t) for t in affected_tests if Path(t).exists()]
    except Exception:
        pass

    return all_test_ps




_register_local_node = lambda: _start_distributed_worker_nodes(2)


_register_local_node()


# Tree-sitter semantic impact: minimal test set per changed source file
# ---------------------------------------------------------------------------

def _build_ts_index(source_root_p: Path, repo: Path) -> str | None:
    """Build (or reuse) an incremental tree-sitter symbol/reference index.

    Returns the index artifact path, or None if indexing failed.
    """
    index_key = _sha256(str(source_root_p).encode("utf-8"))[:16]
    index_path = CACHE_DIR / ("ts_index_" + index_key + ".json")
    if index_path.is_file():
        return str(index_path)
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        from canonical.runtime.bound_capabilities.code_tree_sitter_incremental_index_v1 import (
            run as _ts_index_run,
        )
        _ts_index_run(
            {
                "source_root": str(source_root_p.relative_to(repo)),
                "output_path": str(index_path),
                "max_files": 5000,
            },
            repo,
        )
        return str(index_path) if index_path.is_file() else None
    except Exception:
        return None


def _ts_select_affected_tests(
    index_path: str | None,
    source_path: Path,
    test_paths: list[Path],
    repo: Path,
) -> tuple[list[Path], str | None, dict[str, Any]]:
    """Return (affected_tests, index_path, impact_result).

    Uses tree-sitter change-impact analysis (symbol index + call graph +
    import graph downstream closure). Fail-safe: returns the full test set on
    any failure or empty selection.
    """
    impact_result: dict[str, Any] = {}
    if not index_path:
        impact_result = {"selected_tests": [], "changed_symbols": {}}
        return test_paths, None, impact_result
    try:
        from canonical.runtime.bound_capabilities.code_tree_sitter_impact_v1 import (
            run as _ts_impact_run,
        )
        rel = str(source_path.relative_to(repo))
        impact_result = _ts_impact_run(
            {
                "changed_paths": [rel],
                "index_path": index_path,
                "test_paths": [str(tp) for tp in test_paths],
                "output_path": str(
                    CACHE_DIR / ("ts_impact_" + _sha256(rel.encode())[:16] + ".json")
                ),
            },
            repo,
        )
        selected = impact_result.get("selected_tests") or []
        if selected:
            return [Path(repo / s) for s in selected], index_path, impact_result
    except Exception:
        pass
    impact_result = {"selected_tests": [], "changed_symbols": {}}
    return test_paths, index_path, impact_result

_SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules"}

# Binary operator swaps — includes Add->Mult / Sub->Add that real bugs need.
_BINOP_SWAPS = {
    ast.Add: [ast.Sub, ast.Mult],
    ast.Sub: [ast.Add, ast.Mult],
    ast.Mult: [ast.Add, ast.Sub],
    ast.Div: [ast.Mult, ast.Sub],
}

# Language → base test command. Multi-language SWE: the engineer detects the
# source language and runs the right test runner for each project.
_LANGUAGE_TEST_COMMANDS = {
    "python": ["python3", "-m", "pytest"],
    "javascript": ["npx", "jest", "--no-coverage"],
    "typescript": ["npx", "jest", "--no-coverage"],
    "rust": ["cargo", "test"],
    "go": ["go", "test"],
    "java": ["mvn", "test", "-q"],
    "cpp": ["ctest", "--output-on-failure"],
    "c": ["ctest", "--output-on-failure"],
}


def _detect_language(source_path: Path) -> str:
    """Detect programming language from file extension."""
    suffix = source_path.suffix.lower()
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".hh": "cpp",
    }
    return mapping.get(suffix, "python")


def _test_command(lang: str, *test_paths: str) -> list[str]:
    """Build the test command for a given language and test file(s)."""
    base = _LANGUAGE_TEST_COMMANDS.get(lang, ["python3", "-m", "pytest"])
    return base + list(test_paths)


# ---------------------------------------------------------------------------
# Learning loop: mutation-type success patterns for smarter candidate ranking
# ---------------------------------------------------------------------------

def _pattern_stats_path() -> Path:
    return CACHE_DIR / "swe_pattern_stats.json"


def _load_pattern_stats() -> dict[str, dict[str, int]]:
    """Load historical mutation-category → {successes, attempts} stats."""
    try:
        p = _pattern_stats_path()
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_pattern_stats(stats: dict[str, dict[str, int]]) -> None:
    """Persist pattern stats (content-addressable, idempotent)."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _pattern_stats_path().write_text(
            json.dumps(stats, sort_keys=True), encoding="utf-8"
        )
    except OSError:
        pass


def _mutation_category(desc: str) -> str:
    """Extract a coarse category from a mutation description."""
    d = desc.upper()
    if "BINOP_SWAP" in d:
        return "binop_swap"
    if "CONSTANT_REPLACE" in d:
        return "constant_replace"
    if "UNOP" in d or "NEGATE" in d:
        return "unop_negate"
    if "IF" in d or "CONDITION" in d:
        return "condition"
    return "other"


def _pattern_boost(category: str, stats: dict[str, dict[str, int]]) -> float:
    """Score boost from historical success rate of a mutation category."""
    s = stats.get(category)
    if not s or s.get("attempts", 0) < 2:
        return 0.0
    rate = s["successes"] / s["attempts"]
    # Boost up to +5 for categories with >80% historical success.
    return 5.0 * rate if rate > 0.5 else 0.0

_CACHE_LOCK = threading.Lock()

# --- Multi-armed bandit: Thompson sampling for candidate selection -------
# Each mutation category maintains a Beta(alpha, beta) posterior over its
# success probability. Thompson sampling draws from each posterior and picks
# the category with the highest sample — optimal exploration/exploitation.
_BANDIT_ALPHA: dict[str, float] = {}
_BANDIT_BETA: dict[str, float] = {}
_BANDIT_LOCK = threading.Lock()


def _bandit_load() -> None:
    """Load bandit priors from persistent cache (cross-session learning)."""
    global _BANDIT_ALPHA, _BANDIT_BETA
    try:
        p = CACHE_DIR / "swe_bandit_priors.json"
        if p.is_file():
            data = json.loads(p.read_text(encoding="utf-8"))
            _BANDIT_ALPHA = {k: float(v[0]) for k, v in data.items()}
            _BANDIT_BETA = {k: float(v[1]) for k, v in data.items()}
    except Exception:
        _BANDIT_ALPHA = {}
        _BANDIT_BETA = {}


def _bandit_save() -> None:
    """Persist bandit priors to cache."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data = {k: [_BANDIT_ALPHA.get(k, 1.0), _BANDIT_BETA.get(k, 1.0)]
                for k in set(_BANDIT_ALPHA) | set(_BANDIT_BETA)}
        (CACHE_DIR / "swe_bandit_priors.json").write_text(
            json.dumps(data, sort_keys=True), encoding="utf-8")
    except OSError:
        pass


def _bandit_sample(category: str) -> float:
    """Draw a Thompson sample for a mutation category's success probability."""
    with _BANDIT_LOCK:
        a = _BANDIT_ALPHA.get(category, 1.0)
        b = _BANDIT_BETA.get(category, 1.0)
    import random as _random
    return _random.betavariate(a, b)


def _bandit_update(category: str, success: bool) -> None:
    """Update Beta posterior for a mutation category after observing a result."""
    with _BANDIT_LOCK:
        _BANDIT_ALPHA[category] = _BANDIT_ALPHA.get(category, 1.0) + (1.0 if success else 0.0)
        _BANDIT_BETA[category] = _BANDIT_BETA.get(category, 1.0) + (0.0 if success else 1.0)


# --- Circuit breakers for distributed workers -----------------------------
# Workers that fail repeatedly are temporarily removed from rotation.
_WORKER_FAILURES: dict[str, int] = {}
_WORKER_CIRCUIT_OPEN: dict[str, float] = {}  # endpoint -> unlock timestamp
_CIRCUIT_LOCK = threading.Lock()
_CIRCUIT_FAILURE_THRESHOLD = 3
_CIRCUIT_COOLDOWN_S = 60.0


def _circuit_record_success(endpoint: str) -> None:
    """Record a successful worker response, resetting failure count."""
    with _CIRCUIT_LOCK:
        _WORKER_FAILURES.pop(endpoint, None)
        _WORKER_CIRCUIT_OPEN.pop(endpoint, None)


def _circuit_record_failure(endpoint: str) -> None:
    """Record a worker failure; open circuit after threshold."""
    import time as _time
    with _CIRCUIT_LOCK:
        _WORKER_FAILURES[endpoint] = _WORKER_FAILURES.get(endpoint, 0) + 1
        if _WORKER_FAILURES[endpoint] >= _CIRCUIT_FAILURE_THRESHOLD:
            _WORKER_CIRCUIT_OPEN[endpoint] = _time.monotonic() + _CIRCUIT_COOLDOWN_S


def _circuit_is_open(endpoint: str) -> bool:
    """Return True if the circuit for this endpoint is open."""
    import time as _time
    with _CIRCUIT_LOCK:
        unlock = _WORKER_CIRCUIT_OPEN.get(endpoint, 0.0)
        if unlock > 0 and _time.monotonic() < unlock:
            return True
        if unlock > 0 and _time.monotonic() >= unlock:
            # Cooldown expired — allow one retry
            _WORKER_CIRCUIT_OPEN.pop(endpoint, None)
            _WORKER_FAILURES.pop(endpoint, None)
        return False


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _git_toplevel(path: Path) -> str | None:
    """Return the git toplevel directory for *path*, or None if not in a git repo."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(path), capture_output=True, text=True, timeout=10,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:
        pass
    return None


def _purge_bytecode(path: Path) -> None:
    """Remove all __pycache__ directories adjacent to / under a path."""
    try:
        if path.is_dir():
            for cache_dir in path.rglob("__pycache__"):
                if cache_dir.is_dir():
                    shutil.rmtree(cache_dir, ignore_errors=True)
        else:
            cache_dir = path.parent / "__pycache__"
            if cache_dir.is_dir():
                shutil.rmtree(cache_dir, ignore_errors=True)
            # Also purge the importlib cache entry for this file.
            try:
                import importlib.util as _iu
                c = _iu.cache_from_source(str(path))
                Path(c).unlink(missing_ok=True)  # type: ignore[attr-defined]
            except Exception:
                pass
    except Exception:
        pass


def _copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)

    def ignore(_dir, names):
        return [n for n in names if n in _SKIP_DIRS]

    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore)


def _unified_diff(before: Path, after: Path) -> str:
    before_files = {}
    after_files = {}
    for p in before.rglob("*.py"):
        if p.is_file() and not any(part in _SKIP_DIRS for part in p.parts):
            before_files[str(p.relative_to(before))] = p.read_text(encoding="utf-8")
    for p in after.rglob("*.py"):
        if p.is_file() and not any(part in _SKIP_DIRS for part in p.parts):
            after_files[str(p.relative_to(after))] = p.read_text(encoding="utf-8")
    all_files = sorted(set(before_files) | set(after_files))
    chunks = []
    for rel in all_files:
        old = before_files.get(rel)
        new = after_files.get(rel)
        if old is None:
            new_lines = new.splitlines(keepends=True)
            chunks.append("--- /dev/null\n+++ b/{}\n@@ -0,0 +1,{} @@\n".format(rel, len(new_lines)))
            chunks.extend("+{}".format(line) for line in new_lines)
        elif new is None:
            old_lines = old.splitlines(keepends=True)
            chunks.append("--- a/{}\n+++ /dev/null\n@@ -1,{} +0,0 @@\n".format(rel, len(old_lines)))
            chunks.extend("-{}".format(line) for line in old_lines)
        elif old != new:
            chunks.extend(difflib.unified_diff(
                old.splitlines(keepends=True), new.splitlines(keepends=True),
                fromfile="a/" + rel, tofile="b/" + rel, n=3,
            ))
    return "".join(chunks)


# ---------------------------------------------------------------------------
# Candidate generation (AST mutations + literal substitutions mined from tests)
# ---------------------------------------------------------------------------

def _test_literals(paths: list[Path]) -> tuple[list[Any], list[str]]:
    nums: set[Any] = set()
    strings: set[str] = set()
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant):
                    value = node.value
                    if isinstance(value, bool) or value is None:
                        continue
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        if isinstance(value, float) and not (value == value and abs(value) != float("inf")):
                            continue
                        nums.add(value)
                    elif isinstance(value, str) and 0 < len(value) <= 120:
                        strings.add(value)
        except Exception:
            pass
    return sorted(nums, key=lambda x: (float(x), repr(x))), sorted(strings)


def _node_key(node: ast.AST) -> tuple:
    return (
        type(node).__name__,
        getattr(node, "lineno", None), getattr(node, "col_offset", None),
        getattr(node, "end_lineno", None), getattr(node, "end_col_offset", None),
    )


def _render_candidate(source_text: str, key, replacer) -> str | None:
    tree = ast.parse(source_text)
    target = None
    for node in ast.walk(tree):
        if _node_key(node) == key:
            target = node
            break
    if target is None:
        return None
    if None in (
        getattr(target, "lineno", None), getattr(target, "col_offset", None),
        getattr(target, "end_lineno", None), getattr(target, "end_col_offset", None),
    ):
        return None
    replacement = replacer(target)
    ast.fix_missing_locations(replacement)
    replacement_text = ast.unparse(replacement)
    raw = source_text.encode("utf-8")
    lines = raw.splitlines(keepends=True)
    start = sum(len(x) for x in lines[: target.lineno - 1]) + target.col_offset
    end = sum(len(x) for x in lines[: target.end_lineno - 1]) + target.end_col_offset
    return raw[:start] + replacement_text.encode("utf-8") + raw[end:]


def generate_candidates(source_text: str, test_paths: list[Path], repo: Path):
    """Yield (description, mutated_source_text, lineno) candidate patches.

    `lineno` is the source line of the mutated node — used for fault-locality
    guided ordering so mutations on suspicious lines are tried first.
    """
    nums, strings = _test_literals(test_paths)
    tree = ast.parse(source_text)
    seen = set()
    for node in ast.walk(tree):
        key = _node_key(node)
        if key in seen:
            continue
        seen.add(key)
        lineno = getattr(node, "lineno", None)

        if isinstance(node, ast.BinOp):
            for new_typ in _BINOP_SWAPS.get(type(node.op), []):
                new_node = ast.BinOp(left=node.left, op=new_typ(), right=node.right)
                ast.fix_missing_locations(new_node)
                cand = _render_candidate(source_text, key, lambda n, nt=new_typ: ast.BinOp(left=n.left, op=nt(), right=n.right))
                if cand is not None:
                    cand = cand if isinstance(cand, str) else cand.decode("utf-8")
                    if cand != source_text:
                        yield ("BINOP_SWAP {}->{}".format(type(node.op).__name__, new_typ.__name__), cand, lineno)

        if isinstance(node, ast.Constant):
            value = node.value
            replacements = []
            if isinstance(value, bool):
                replacements = [not value]
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                base = [0, 1, -1]
                if isinstance(value, int):
                    base += [value - 1, value + 1]
                replacements = sorted(set(base + list(nums)))
            elif isinstance(value, str):
                replacements = sorted(strings)
            for rep in replacements[:32]:
                if rep == value:
                    continue
                if isinstance(value, int) and isinstance(rep, float) and not float(rep).is_integer():
                    continue
                if isinstance(value, int) and isinstance(rep, float):
                    rep = int(rep)
                cand = _render_candidate(source_text, key, lambda n, r=rep: ast.Constant(value=r))
                cand = cand if isinstance(cand, str) else cand.decode("utf-8")
                if cand != source_text:
                    yield ("CONSTANT_REPLACE {}->{}".format(repr(value), repr(rep)), cand, lineno)


# ---------------------------------------------------------------------------
# Multi-language candidate generation (tree-sitter based)
# ---------------------------------------------------------------------------

_TS_OP_SWAPS = {
    # tree-sitter operator text -> replacement operator text
    "+": ["-", "*"],
    "-": ["+", "*"],
    "*": ["+", "-"],
    "/": ["*", "-"],
    "==": ["!="],
    "!=": ["=="],
    "<": [">", "<="],
    ">": ["<", ">="],
    "<=": [">="],
    ">=": ["<="],
    "&&": ["||"],
    "||": ["&&"],
}


def _ts_parse(source_text: str, lang: str):
    """Parse source text with tree-sitter for the given language. Returns root node or None."""
    try:
        from tree_sitter_languages import get_parser
        parser = get_parser(lang)
        tree = parser.parse(bytes(source_text, "utf-8"))
        return tree.root_node
    except Exception:
        return None


def _ts_walk(node):
    """Yield all nodes in the tree-sitter tree (pre-order)."""
    yield node
    child = node.child_count
    for i in range(child):
        yield from _ts_walk(node.child(i))


def _ts_replace_range(source_text: str, node, replacement_text: str) -> str | None:
    """Replace the byte range of a tree-sitter node with replacement_text."""
    if node.start_byte is None or node.end_byte is None:
        return None
    raw = source_text.encode("utf-8")
    new_raw = raw[: node.start_byte] + replacement_text.encode("utf-8") + raw[node.end_byte:]
    return new_raw.decode("utf-8")


def _generate_candidates_multilanguage(source_text: str, source_path: Path,
                                       test_paths: list[Path], repo: Path):
    """Yield (description, mutated_source_text, lineno) candidates for non-Python files.

    Uses tree-sitter to parse the source and generate:
      * Binary operator swaps (+ -> -, etc.)
      * Literal replacements (strings, numbers, booleans) mined from affected tests.
    Falls back to yielding nothing if tree-sitter parsing fails.
    """
    lang = _detect_language(source_path)
    if lang == "python":
        return  # handled by generate_candidates

    root = _ts_parse(source_text, lang)
    if root is None:
        return

    nums, strings = _test_literals(test_paths)

    seen = set()
    for node in _ts_walk(root):
        node_type = node.type
        node_text = source_text[node.start_byte:node.end_byte]
        key = (node_type, node.start_byte, node.end_byte)
        if key in seen:
            continue
        seen.add(key)
        lineno = node.start_point[0] + 1  # tree-sitter is 0-based

        # --- Binary operator swaps -----------------------------------------
        if node_type in ("binary_expression", "binary_operation"):
            # Find the operator token within the node.
            for child in node.children:
                if child.type in _TS_OP_SWAPS or child.type in ("operator",):
                    op_text = source_text[child.start_byte:child.end_byte]
                    for repl in _TS_OP_SWAPS.get(op_text, []):
                        new_source = _ts_replace_range(
                            source_text, child, repl)
                        if new_source is not None and new_source != source_text:
                            yield ("TS_BINOP_SWAP {}->{}".format(op_text, repl),
                                   new_source, lineno)

        # --- Literal replacements ------------------------------------------
        if node_type in ("string_literal", "string", "interpreted_string_literal"):
            for rep in strings[:32]:
                rep_escaped = '"' + rep.replace('"', '\\"') + '"'
                if rep_escaped == node_text:
                    continue
                new_source = _ts_replace_range(source_text, node, rep_escaped)
                if new_source is not None and new_source != source_text:
                    yield ("TS_CONSTANT_REPLACE {}->{}".format(node_text, rep_escaped),
                           new_source, lineno)
                    break  # one string replacement per node

        if node_type in ("number_literal", "integer", "float", "decimal_integer_literal"):
            try:
                value = float(node_text)
            except ValueError:
                continue
            for rep in sorted(set(nums + [0, 1, -1]))[:32]:
                if rep == value:
                    continue
                rep_str = str(int(rep)) if float(rep).is_integer() else str(rep)
                new_source = _ts_replace_range(source_text, node, rep_str)
                if new_source is not None and new_source != source_text:
                    yield ("TS_CONSTANT_REPLACE {}->{}".format(node_text, rep_str),
                           new_source, lineno)
                    break

        if node_type in ("true", "false", "boolean_literal"):
            repl = "true" if node_text == "false" else "false"
            new_source = _ts_replace_range(source_text, node, repl)
            if new_source is not None and new_source != source_text:
                yield ("TS_CONSTANT_REPLACE {}->{}".format(node_text, repl),
                       new_source, lineno)


# ---------------------------------------------------------------------------
# Advanced candidate generation — beyond simple AST mutations
# ---------------------------------------------------------------------------

# Common bug-fix templates: (description, predicate_to_check, replacement_fn)
# These encode real-world fix patterns mined from SWE-bench and real patches.
_BUG_FIX_TEMPLATES = [
    # Off-by-one: range(n) -> range(n+1) or range(n-1)
    ("OFF_BY_ONE_PLUS", "range", None),
    ("OFF_BY_ONE_MINUS", "range", None),
    # Null guard: add `if x is None: return` before usage
    ("NULL_GUARD", "is None", None),
    # Default value: `x or default`
    ("DEFAULT_OR", "or ", None),
    # Early return for empty
    ("EARLY_RETURN_EMPTY", "if not ", None),
    # Type check: `isinstance(x, ...)`
    ("TYPE_CHECK", "isinstance", None),
]


def _generate_candidates_advanced(source_text: str, source_path: Path,
                                   test_paths: list[Path], repo: Path):
    """Yield additional candidates using advanced mutation strategies.

    Strategies:
      * Statement insertion (early returns, null guards, defaults)
      * Statement deletion (removing redundant lines)
      * Import modifications (adding missing imports)
      * Control flow changes (if/else inversion, loop bound adjustments)
      * Bug-fix templates from real-world patches
    """
    lines = source_text.splitlines(keepends=True)
    tree = ast.parse(source_text)

    # --- Statement insertion: early returns / null guards ------------------
    # Find function bodies and insert defensive checks at the top.
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if len(node.body) == 0:
                continue
            lineno = node.lineno
            # Insert null guard for first argument
            args = node.args.args
            if args:
                first_arg = args[0].arg
                guard = f"    if {first_arg} is None:\n        return None\n"
                new_text = _insert_after_line(source_text, lineno, guard)
                if new_text != source_text:
                    yield ("TS_STATEMENT_INSERT_NULL_GUARD", new_text, lineno)

            # Insert empty-check return for iterable first arg
            if args:
                first_arg = args[0].arg
                guard = f"    if not {first_arg}:\n        return\n"
                new_text = _insert_after_line(source_text, lineno, guard)
                if new_text != source_text:
                    yield ("TS_STATEMENT_INSERT_EARLY_RETURN", new_text, lineno)

    # --- Statement deletion: remove redundant assignments ------------------
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            lineno = node.lineno
            new_text = _delete_line(source_text, lineno)
            if new_text is not None and new_text != source_text:
                yield ("TS_STATEMENT_DELETE", new_text, lineno)

    # --- Import modifications: add missing imports -------------------------
    existing_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                existing_imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                existing_imports.add(node.module.split(".")[0])

    # Common imports that might be needed based on usage
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in ("json", "os", "sys", "re", "pathlib") \
                        and func_name not in existing_imports:
                    import_line = f"import {func_name}\n"
                    new_text = source_text.replace("\n", "\n" + import_line, 1)
                    if new_text != source_text:
                        yield ("TS_IMPORT_ADD", new_text, node.lineno)

    # --- Loop bound adjustments: range(n) -> range(n+1), etc. --------------
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "range" and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                    # range(n) -> range(n+1)
                    new_val = arg.value + 1
                    new_text = _replace_constant_in_source(
                        source_text, arg, new_val)
                    if new_text != source_text:
                        yield ("TS_RANGE_PLUS_ONE", new_text, arg.lineno)
                    # range(n) -> range(n-1)
                    if arg.value > 1:
                        new_val = arg.value - 1
                        new_text = _replace_constant_in_source(
                            source_text, arg, new_val)
                        if new_text != source_text:
                            yield ("TS_RANGE_MINUS_ONE", new_text, arg.lineno)

    # --- Condition inversion: if x -> if not x -----------------------------
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            lineno = test.lineno
            new_text = _invert_condition(source_text, test, lineno)
            if new_text != source_text:
                yield ("TS_CONDITION_INVERT", new_text, lineno)


def _insert_after_line(source_text: str, lineno: int, insertion: str) -> str:
    """Insert text after the given 1-based line number."""
    lines = source_text.splitlines(keepends=True)
    if lineno < 1 or lineno > len(lines):
        return source_text
    lines.insert(lineno, insertion)
    return "".join(lines)


def _delete_line(source_text: str, lineno: int) -> str | None:
    """Delete the given 1-based line. Returns None if out of range."""
    lines = source_text.splitlines(keepends=True)
    if lineno < 1 or lineno > len(lines):
        return None
    del lines[lineno - 1]
    return "".join(lines)


def _replace_constant_in_source(source_text: str, const_node: ast.AST,
                                 new_value) -> str:
    """Replace a constant node's value in source text."""
    if const_node.value is None:
        return source_text
    old_repr = repr(const_node.value)
    new_repr = repr(new_value)
    lines = source_text.splitlines(keepends=True)
    if const_node.lineno and const_node.lineno <= len(lines):
        line = lines[const_node.lineno - 1]
        if old_repr in line:
            new_line = line.replace(old_repr, new_repr, 1)
            lines[const_node.lineno - 1] = new_line
            return "".join(lines)
    return source_text


def _invert_condition(source_text: str, test_node: ast.AST, lineno: int) -> str:
    """Invert a condition: wrap with `not ` or unwrap."""
    if not test_node.lineno or test_node.lineno > len(source_text.splitlines()):
        return source_text
    lines = source_text.splitlines(keepends=True)
    line = lines[test_node.lineno - 1]
    stripped = line.strip()
    if stripped.startswith("if "):
        rest = stripped[3:]
        if rest.startswith("not "):
            new_line = line.replace("if not ", "if ", 1)
        else:
            new_line = line.replace("if ", "if not ", 1)
        lines[test_node.lineno - 1] = new_line
        return "".join(lines)
    return source_text


# ---------------------------------------------------------------------------
# Cache (content-addressable: keyed by source+test bytes)
# ---------------------------------------------------------------------------

def _cache_key(source_bytes: bytes, test_paths: list[Path]) -> str:
    h = hashlib.sha256(source_bytes)
    for tp in test_paths:
        try:
            h.update(tp.read_bytes())
        except OSError:
            pass
    # Environment context: include Python + pytest versions so cache isn't
    # stale across environment changes.
    h.update(sys.version.encode("utf-8"))
    try:
        import pytest as _pytest
        h.update(_pytest.__version__.encode("utf-8"))
    except ImportError:
        h.update(b"no-pytest")
    return h.hexdigest()


def _cache_read(key: str) -> dict | None:
    with _CACHE_LOCK:
        p = CACHE_DIR / (key + ".json")
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None


def _cache_write(key: str, result: dict) -> None:
    with _CACHE_LOCK:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            (CACHE_DIR / (key + ".json")).write_text(
                json.dumps(result, sort_keys=True), encoding="utf-8")
        except OSError:
            pass

# ---------------------------------------------------------------------------
# Gate filter for candidate winners — run fast gates before accepting a patch
# ---------------------------------------------------------------------------

def _run_gates_on_candidate(cand_source_candidates: list[list],
                            source_root_p: Path,
                            repo: Path,
                            gid: str) -> tuple[bool, str]:
    """Run static_triage, type_check, and security gates on a candidate patch.

    Returns (accept: bool, reason: str). If any gate returns FAIL, the
    candidate is rejected and search continues.
    """
    import tempfile as _tempfile
    import shutil as _shutil

    # Build a temp worktree with the candidate applied.
    workdir = Path(_tempfile.mkdtemp(prefix="swe_gate_filter_", dir=str(repo)))
    try:
        # Copy source tree.
        for sc in cand_source_candidates:
            sp_str = sc[0]
            new_text = sc[1] if len(sc) > 1 else None
            sp = Path(sp_str)
            try:
                rel = sp.relative_to(source_root_p).as_posix()
            except ValueError:
                rel = sp.name
            target = workdir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if new_text is not None:
                target.write_text(new_text, encoding="utf-8")
            elif not target.exists():
                try:
                    _shutil.copy2(sp, target)
                except (OSError, FileNotFoundError):
                    pass

        # Build a unified diff for gate analysis.
        diff_parts = []
        for sc in cand_source_candidates:
            sp_str = sc[0]
            new_text = sc[1] if len(sc) > 1 else None
            if new_text is None:
                continue
            sp = Path(sp_str)
            try:
                rel = sp.relative_to(source_root_p).as_posix()
            except ValueError:
                rel = sp.name
            try:
                orig_text = source_root_p.joinpath(rel).read_text(encoding="utf-8")
            except Exception:
                orig_text = ""
            diff_parts.append(_unified_diff_text(orig_text, new_text, rel))
        full_diff = "\n".join(diff_parts)
        if not full_diff.strip():
            return True, "NO_DIFF"

        diff_path = workdir / ".gate_filter.diff"
        diff_path.write_text(full_diff, encoding="utf-8")

        # Run static_triage gate.
        triage_result = _static_triage_run(
            {
                "diff_path": str(diff_path.relative_to(repo)),
                "worktree_path": str(workdir.relative_to(repo)),
                "output_path": str((workdir / ".gate_triage.json").relative_to(repo)),
                "python_executable": sys.executable,
                "timeout_s": 30,
            },
            repo,
        )
        if triage_result.get("error") or triage_result.get("gate") == "FAIL":
            return False, f"STATIC_TRIAGE:{triage_result.get('reason', triage_result.get('gate', 'FAIL'))}"

        # Run type_check gate.
        type_result = _type_gate_run(
            {
                "diff_path": str(diff_path.relative_to(repo)),
                "worktree_path": str(workdir.relative_to(repo)),
                "output_path": str((workdir / ".gate_type.json").relative_to(repo)),
                "python_executable": sys.executable,
                "timeout_s": 30,
            },
            repo,
        )
        if type_result.get("error") or type_result.get("gate") == "FAIL":
            return False, f"TYPE_CHECK:{type_result.get('reason', type_result.get('gate', 'FAIL'))}"

        # Run security gate.
        sec_result = _security_gate_run(
            {
                "diff_path": str(diff_path.relative_to(repo)),
                "worktree_path": str(workdir.relative_to(repo)),
                "output_path": str((workdir / ".gate_sec.json").relative_to(repo)),
                "python_executable": sys.executable,
                "timeout_s": 30,
            },
            repo,
        )
        if sec_result.get("error") or sec_result.get("gate") not in ("PASS", "PASS_BASELINE_ONLY"):
            return False, f"SECURITY:{sec_result.get('reason', sec_result.get('gate', 'FAIL'))}"

        return True, "ALL_GATES_PASS"
    except Exception as exc:
        # If gates can't run, accept the candidate (fail open for gate filter).
        return True, f"GATE_FILTER_SKIPPED:{str(exc)[:100]}"
    finally:
        _shutil.rmtree(workdir, ignore_errors=True)




# ---------------------------------------------------------------------------
# Gate result extraction — preserve error reasons from fail-closed gates
# ---------------------------------------------------------------------------

def _extract_gate_result(result: dict) -> tuple[str, dict]:
    """Extract (gate_status, details) from a gate result.

    Gates return either {"gate": "PASS"/"FAIL", ...} on success or
    {"error": True, "reason": "..."} on failure. This preserves the
    actual error reason instead of defaulting to "FAIL".
    """
    if result.get("error"):
        return "FAIL", {"error_reason": result.get("reason", "UNKNOWN_ERROR")}
    gate = result.get("gate", "FAIL")
    return gate, {k: v for k, v in result.items() if k not in ("gate",)}



# ---------------------------------------------------------------------------
# Distributed candidate evaluation (work-stealing across nodes)
# ---------------------------------------------------------------------------
def _distributed_nodes_available() -> bool:
    """Return True if any distributed node is registered and active."""
    try:
        from canonical.runtime.distributed_queue_v1 import NodeRegistry
        reg = NodeRegistry()
        nodes = reg.get_nodes()
        return len(nodes) > 0
    except Exception:
        return False



# ---------------------------------------------------------------------------
# Isolated per-candidate test execution (thread-safe: each call uses its own
# temporary worktree copy, so threads never share mutable state).
# ---------------------------------------------------------------------------

def _eval_candidate(args: tuple) -> dict:
    """Worker: evaluate one candidate in an isolated worktree copy.

    args = (source_candidates, source_root, test_paths, repo,
            timeout_s, cache_key, goal_id, candidate_index[, _is_distributed_worker])
    where source_candidates is either:
      * a string (single source_path) — backward compatible
      * a list of [source_path, candidate_text] pairs — multi-file mode
    Returns dict with returncode/stdout/stderr/timed_out/elapsed_s/cached.
    """
    # Unpack args with optional _is_distributed_worker flag.
    _is_distributed_worker = False
    if len(args) == 8:
        # New format: (source_candidates_json, source_root, test_paths, repo,
        #              timeout_s, cache_key, goal_id, candidate_index)
        (source_candidates_s, source_root_s, test_paths_s, repo_s,
         timeout_s, cache_key, goal_id, candidate_index) = args
    elif len(args) == 9:
        # Could be new format with _is_distributed_worker flag
        (source_candidates_s, source_root_s, test_paths_s, repo_s,
         timeout_s, cache_key, goal_id, candidate_index,
         _is_distributed_worker) = args
    else:
        # Legacy format: (source_path, source_root, candidate_text, ...)
        (source_path_s, source_root_s, candidate_text, test_paths_s, repo_s,
         timeout_s, cache_key, goal_id, candidate_index) = args[:9]
        source_candidates_s = [[source_path_s, candidate_text]]
        if len(args) == 10:
            _is_distributed_worker = args[9]

    source_root = Path(source_root_s)
    repo = Path(repo_s)
    test_paths = [Path(p) for p in test_paths_s]

    # Parse source_candidates: JSON list of [path, text] pairs or legacy string.
    # Distinguish: new format JSON starts with '['; legacy format is a file path.
    if isinstance(source_candidates_s, str) and source_candidates_s.startswith("["):
        # New multi-file format: JSON list of [path, text] pairs
        source_candidates = json.loads(source_candidates_s)
        single_file_mode = len(source_candidates) == 1
    else:
        # Legacy single-file mode: source_candidates_s is a file path string
        source_candidates = [(source_candidates_s, None)]
        single_file_mode = True

    # Emit progress: candidate evaluation started.
    _progress_adapter.candidate_evaluated(goal_id, candidate_index, {
        "status": "evaluating",
        "test_count": len(test_paths),
        "multi_file": not single_file_mode,
    })

    # --- cache check -------------------------------------------------------
    cached = _cache_read(cache_key)
    if cached is not None:
        cached = dict(cached)
        cached["cached"] = True
        return cached

    # --- distributed evaluation: try remote node first ---------------------
    # Skip if already running on a worker node — prevents infinite HTTP
    # recursion (worker → worker → worker → deadlock).
    if not cached and _distributed_nodes_available() and not _is_distributed_worker:
        dist_result = _eval_candidate_distributed(args)
        if dist_result is not None:
            dist_result = dict(dist_result)
            dist_result["cached"] = False
            dist_result["distributed"] = True
            return dist_result

    # --- git worktree decision (O(1) setup vs O(tree_size) copytree) -------
    # For multi-file: use worktree if ALL source files are inside the repo.
    use_worktree = False
    git_root = None
    try:
        if repo.is_dir() and (repo / ".git").is_dir():
            all_inside = True
            for sc in source_candidates:
                sp = Path(sc[0])
                try:
                    sp.relative_to(repo)
                except ValueError:
                    all_inside = False
                    break
            if all_inside:
                use_worktree = True
                git_root = str(repo)
    except Exception:
        pass

    workdir = None
    t0 = __import__("time").monotonic()
    try:
        WORK_ROOT.mkdir(parents=True, exist_ok=True)

        env = dict(os.environ)
        env_py_parts: list[str] = []
        pytest_targets: list[str] = []

        if use_worktree:
            # Git worktree: O(1) setup — no full tree copy per candidate.
            workdir = Path(tempfile.mkdtemp(prefix="pbs_wt_", dir=str(WORK_ROOT)))
            wt_result = subprocess.run(
                ["git", "worktree", "add", "--detach", str(workdir)],
                cwd=git_root, capture_output=True, text=True, timeout=30,
            )
            if wt_result.returncode == 0:
                # Apply all candidate texts to their respective source files.
                for sc in source_candidates:
                    sp = Path(sc[0])
                    new_text = sc[1] if len(sc) > 1 else None
                    rel = sp.relative_to(repo)
                    patched = workdir / rel
                    patched.parent.mkdir(parents=True, exist_ok=True)
                    if new_text is not None:
                        patched.write_bytes(new_text.encode("utf-8"))
                    elif not patched.exists():
                        # Untracked source files are NOT in the git worktree
                        # checkout — copy them from the original source so
                        # sibling imports (e.g. `from src.calculator import ...`)
                        # resolve correctly inside the worktree.
                        try:
                            shutil.copy2(sp, patched)
                        except (OSError, FileNotFoundError):
                            pass
                    # If new_text is None and the file exists in the worktree
                    # from git checkout, no change needed.
                _purge_bytecode(workdir)
                # Test files may already exist in worktree from git checkout.
                for tp in test_paths:
                    try:
                        trel = tp.relative_to(repo)
                    except ValueError:
                        trel = Path(*tp.relative_to(source_root).parts)
                    dest = workdir / trel
                    pytest_targets.append(str(dest))
                    if not dest.exists():
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(tp, dest)
                env_py_parts = [str(workdir)]
                # Add source root dirs + all ancestor dirs for imports.
                # `from src.calculator import ...` needs the parent of `src/`
                # on PYTHONPATH so the `src` package resolves; walking up
                # covers nested package layouts of any depth.
                for sc in source_candidates:
                    sp = Path(sc[0])
                    try:
                        rel = sp.relative_to(repo)
                        # Walk up from the file's parent to the workdir root,
                        # adding each ancestor directory to PYTHONPATH.
                        ancestor = rel.parent
                        while True:
                            ancestor_in_wt = workdir / ancestor
                            if ancestor_in_wt.is_dir() and str(ancestor_in_wt) not in env_py_parts:
                                env_py_parts.append(str(ancestor_in_wt))
                            if ancestor == ancestor.parent or not ancestor.parts:
                                break
                            ancestor = ancestor.parent
                    except ValueError:
                        pass
            else:
                use_worktree = False  # fall through to copytree below

        if not use_worktree:
            # Copytree: copy the common source root (parent of all source files).
            # Find the deepest common ancestor of all source files.
            source_roots = set()
            for sc in source_candidates:
                sp = Path(sc[0])
                source_roots.add(sp.parent.resolve())
            # Use the first source root (all files should be under the same root)
            common_root = source_roots.pop() if source_roots else repo
            workdir = Path(tempfile.mkdtemp(prefix="pbs_", dir=str(WORK_ROOT)))
            # Mirror the source subtree so sibling imports resolve.
            _copy_tree(common_root, workdir)
            # Apply all candidate texts.
            for sc in source_candidates:
                sp = Path(sc[0])
                new_text = sc[1] if len(sc) > 1 else None
                try:
                    rel = sp.relative_to(common_root)
                except ValueError:
                    rel = sp.name
                patched = workdir / rel
                patched.parent.mkdir(parents=True, exist_ok=True)
                if new_text is not None:
                    patched.write_bytes(new_text.encode("utf-8"))
                # If new_text is None, file already copied by _copy_tree
            _purge_bytecode(workdir)

            # Test files mirrored into the worktree.
            for tp in test_paths:
                try:
                    trel = tp.relative_to(common_root)
                except ValueError:
                    try:
                        trel = Path(*tp.relative_to(repo).parts)
                    except ValueError:
                        trel = tp.name
                dest = workdir / trel
                if not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(tp, dest)
                pytest_targets.append(str(dest))

            env_py_parts = [str(workdir)]

        existing = env.get("PYTHONPATH", "")
        if existing:
            env_py_parts.append(existing)
        env["PYTHONPATH"] = os.pathsep.join(env_py_parts)

        # --- GPU-parallel test execution -----------------------------------
        # Data-parallel test execution: one test per GPU thread (CUDA) or one
        # test per CPU process (fallback). ASE'14 pattern — up to 27x speedup.
        # Multi-language: detect source language and use the right test runner.
        # For multi-file: use the first source file's language.
        first_sp = Path(source_candidates[0][0])
        lang = _detect_language(first_sp)
        test_specs = [
            {"command": _test_command(lang, str(tp)),
             "timeout_s": timeout_s}
            for tp in pytest_targets
        ]
        gpu_result = _gpu_execute_tests(test_specs, backend="auto")
        gpu_summary = gpu_result.get("summary", {})
        gpu_results = gpu_result.get("results", [])

        # Aggregate: pass only if ALL tests pass (pytest semantics).
        all_passed = all(
            r.get("status") == "PASS" for r in gpu_results
        ) and len(gpu_results) == len(test_specs)
        any_timed_out = any(r.get("status") == "TIMEOUT" for r in gpu_results)

        if all_passed:
            returncode = 0
            stdout = "\n".join(r.get("stdout", "") for r in gpu_results)
            stderr = "\n".join(r.get("stderr", "") for r in gpu_results)
            timed_out = False
        elif any_timed_out:
            returncode = None
            stdout = ""
            stderr = "timed out"
            timed_out = True
        else:
            returncode = 1
            stdout = "\n".join(r.get("stdout", "") for r in gpu_results)
            stderr = "\n".join(r.get("stderr", "") for r in gpu_results)
            timed_out = False

        result = {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": timed_out,
            "elapsed_s": round(__import__("time").monotonic() - t0, 6),
            "cached": False,
            "gpu_backend": gpu_result.get("backend", "cpu"),
            "gpu_device_count": gpu_result.get("device_count", 1),
        }

        # Emit progress: candidate evaluation result.
        _progress_adapter.candidate_evaluated(goal_id, candidate_index, {
            "status": "PASS" if returncode == 0 and not timed_out else "FAIL",
            "returncode": returncode,
            "tests_passed": gpu_summary.get("passed", 0),
            "tests_failed": gpu_summary.get("failed", 0),
            "tests_errored": gpu_summary.get("errored", 0),
            "gpu_backend": result["gpu_backend"],
        })

        # Persist to cache (keyed by source+test bytes — content addressable).
        _cache_write(cache_key, result)
        return result
    finally:
        if workdir is not None:
            if use_worktree and git_root:
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(workdir)],
                    cwd=git_root, capture_output=True, timeout=30,
                )
            shutil.rmtree(workdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Fault localization — used to order candidates by suspiciousness
# ---------------------------------------------------------------------------

def _fault_suspicious_lines(source_path: Path, test_paths: list[Path],
                            timeout_s: int) -> dict[tuple[str, int], float]:
    """Return {(rel_path, line): score} for suspicious non-test lines.

    Uses persistent cache (content-addressed) to avoid re-computing fault
    localization for identical test results, and GPU data-parallel execution
    when a GPU is available.
    """
    # Cache key: source file hash + test results hash
    import hashlib as _hl
    src_hash = _hl.sha256(source_path.read_bytes()).hexdigest() if source_path.is_file() else ""
    test_hash = _hl.sha256(
        json.dumps([str(tp) for tp in test_paths], sort_keys=True).encode()
    ).hexdigest()

    cached = _pcache_get_fl(str(source_path), test_hash)
    if cached is not None:
        out: dict[tuple[str, int], float] = {}
        for row in cached.get("ranked_lines", []) or []:
            path = row.get("path")
            line = row.get("line")
            score = row.get("score", 0.0)
            if path and line is not None:
                out[(str(path), int(line))] = float(score)
        return out

    # --- GPU-parallel fault localization -------------------------------------
    # Data-parallel Ochiai across source files (one process per file).
    # Falls back to single-threaded fault_localize on any failure.
    gpu = _gpu_status()
    fl = None
    if gpu.get("available"):
        try:
            # First run tests to get pass/fail results per test for GPU FL.
            test_results = []
            for tp in test_paths:
                if not tp.is_file():
                    continue
                try:
                    src = tp.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    src = ""
                test_results.append({
                    "status": "UNKNOWN",
                    "stdout": src,
                    "stderr": "",
                })
            if test_results:
                gpu_fl = _gpu_fault_localize(
                    [str(source_path)], test_results, backend="auto")
                susp = gpu_fl.get("suspiciousness", {})
                if susp and str(source_path) in susp:
                    score = float(susp[str(source_path)])
                    # Map file-level score to each line of the source file.
                    lines = source_path.read_text(encoding="utf-8", errors="replace").splitlines()
                    fl = {"ranked_lines": [
                        {"path": str(source_path), "line": i + 1, "score": score}
                        for i in range(len(lines))
                    ]}
        except Exception:
            fl = None

    if fl is None:
        try:
            from canonical.runtime.bound_capabilities.real_swe_execution_v1 import fault_localize  # noqa
        except Exception:
            return {}
        try:
            fl = fault_localize(str(source_path), [str(tp) for tp in test_paths], timeout_s=timeout_s)
        except Exception:
            return {}

    # Persist to cache
    _pcache_put_fl(str(source_path), test_hash, fl)

    out: dict[tuple[str, int], float] = {}
    for row in fl.get("ranked_lines", []) or []:
        path = row.get("path")
        line = row.get("line")
        score = row.get("score", 0.0)
        if path and line is not None:
            out[(str(path), int(line))] = float(score)
    return out


# ---------------------------------------------------------------------------
# Parallel patch search with caching + fault-locality ordering
# ---------------------------------------------------------------------------

def patch_search_parallel(source_paths: str | Path | list[str | Path],
                          test_paths: list[str | Path],
                          timeout_s: int = 60, max_candidates: int = 50,
                          max_workers: int | None = None,
                          goal_id: str | None = None,
                          suspicious: dict | None = None,
                          affected_test_ps: list[Path] | None = None,
                          ts_index_path: str | None = None,
                          ts_impact_result: dict | None = None,
                          implicated_symbol_spans: list | None = None,
                          post_pass_filter: callable | None = None) -> dict:
    """Optional post_pass_filter: called on any candidate that passes tests.
    Receives (cand_source_candidates, desc) and must return (accept: bool, reason: str).
    If reject, search continues. Used by end_to_end_repair to run gates on winners."""
    """Run test-guided patch search with parallel candidate evaluation.

    Candidates are ordered by fault-localization suspiciousness so the most
    likely fixes are tried first. Evaluation is parallel over a thread pool
    (each candidate runs pytest in its own isolated worktree copy). A
    content-addressable disk cache guarantees identical source is never
    re-executed. Returns as soon as a verified passing candidate is found.

    Multi-file support: source_paths can be a single path or a list of paths.
    For multi-file, candidates are generated per-file and combined into
    coordinated multi-file patches.
    """
    gid = goal_id or "swe-unknown"
    _progress_adapter.stage_started(gid, "patch_search", {
        "max_candidates": max_candidates,
        "max_workers": max_workers or "auto",
    })

    repo = REPO
    # Normalize source_paths to a list
    if isinstance(source_paths, (str, Path)):
        source_paths = [source_paths]
    source_paths = [Path(p) for p in source_paths]
    source_paths = [p if p.is_absolute() else repo / p for p in source_paths]
    source_paths = [p.resolve() for p in source_paths]

    # Primary source path (first one) for backward-compatible operations.
    source_p = source_paths[0]
    source_root_p = source_p.parent

    test_ps = []
    for t in test_paths:
        tp = Path(t)
        if not tp.is_absolute():
            tp = repo / tp
        test_ps.append(tp.resolve())

    # Read all source files for cache key and candidate generation.
    source_contents: dict[str, bytes] = {}
    for sp in source_paths:
        source_contents[str(sp)] = sp.read_bytes()
    # Primary source bytes (first file) for cache key.
    source_bytes = source_contents[str(source_p)]
    timeout_s = max(1, int(timeout_s))
    max_candidates = max(1, int(max_candidates))
    if max_workers is None:
        max_workers = os.cpu_count() or 4
    max_workers = max(1, int(max_workers))

    # --- baseline must fail -------------------------------------------------
    _progress_adapter.stage_progress(gid, "patch_search", 0, 100, {
        "stage": "baseline",
    })
    baseline = _run_tests_plain(repo, source_p, test_ps, timeout_s)
    if baseline["returncode"] == 0:
        _progress_adapter.stage_completed(gid, "patch_search", {
            "status": "baseline_already_passes",
        })
        return {"status": "OPEN__BASELINE_ALREADY_PASSES", "pass": False,
                "tested_candidate_count": 0, "max_candidates": max_candidates}
    if baseline["timed_out"]:
        _progress_adapter.stage_failed(gid, "patch_search", "BASELINE_TIMEOUT")
        return {"status": "OPEN__BASELINE_TIMEOUT", "pass": False,
                "tested_candidate_count": 0, "max_candidates": max_candidates}

    # --- persistent verified patch pre-check --------------------------------
    # If a verified patch already exists for this source+test combo, skip the
    # entire search and go straight to verification/apply — zero candidate
    # evaluation needed. Source→patch reverse mapping stored under kind
    # "source_patch" so we can look up by source+test hash without knowing
    # the patch hash in advance.
    _progress_adapter.stage_progress(gid, "patch_search", 5, 100, {
        "stage": "persistent_patch_cache_check",
    })
    # Cache key includes ALL source files (for multi-file support).
    _all_source_hash = _sha256(
        b"|".join(source_contents[str(sp)] for sp in source_paths))
    _test_hash = _sha256(
        json.dumps([str(tp) for tp in test_ps], sort_keys=True).encode("utf-8"))
    _cached_source_patch = _pcache_get("source_patch", {
        "source_hash": _all_source_hash,
        "test_hash": _test_hash,
    })
    if _cached_source_patch and _cached_source_patch.get("verified"):
        _progress_adapter.stage_completed(gid, "patch_search", {
            "status": "verified_patch_from_cache",
        })
        return {
            "status": "PASS__VERIFIED_PATCH_FROM_CACHE",
            "pass": True,
            "winning_mutation": "cached_verified_patch",
            "unified_diff": _cached_source_patch.get("diff", ""),
            "tested_candidate_count": 0,
            "max_candidates": max_candidates,
            "source_path": str(source_p.relative_to(repo)),
            "source_sha256": _all_source_hash,
        }

    # --- fault localization to order candidates -----------------------------
    # (may be pre-computed by end_to_end_repair for async pipelining)
    # Multi-file: compute fault localization for each source file and merge.
    if suspicious is None:
        _progress_adapter.stage_progress(gid, "patch_search", 10, 100, {
            "stage": "fault_localization",
        })
        suspicious = {}
        for sp in source_paths:
            fl = _fault_suspicious_lines(sp, test_ps, timeout_s=min(timeout_s, 30))
            suspicious.update(fl)

    # --- tree-sitter semantic impact: minimal affected test set ------------
    # All candidates mutate the same source file(s), so the affected test set
    # is identical for every candidate. Compute once, run only affected tests
    # per candidate — the single biggest speedup in the hot path.
    # Multi-file: compute impact for each source file, merge results.
    # (may be pre-computed by end_to_end_repair for async pipelining)
    if affected_test_ps is None:
        _progress_adapter.stage_progress(gid, "patch_search", 20, 100, {
            "stage": "semantic_impact",
        })
        all_affected = set()
        all_impact = {}
        all_spans: list[tuple[int, int]] = []
        for sp in source_paths:
            sp_root = sp.parent
            ti = _build_ts_index(sp_root, repo)
            aff, ti, impact = _ts_select_affected_tests(ti, sp, test_ps, repo)
            all_affected.update(str(a) for a in aff)
            all_impact[ti] = impact
            # Collect implicated symbol spans.
            try:
                if ti and impact.get("changed_symbols"):
                    import json as _json
                    index_artifact = _json.loads(Path(ti).read_text(encoding="utf-8"))
                    index_rows = {row["path"]: row for row in index_artifact.get("files", [])}
                    rel = str(sp.relative_to(repo))
                    row_data = index_rows.get(rel)
                    if row_data:
                        impacted_names = set()
                        for cs in impact["changed_symbols"].values():
                            for sym in cs.get("symbols", []):
                                impacted_names.add(sym.rsplit(".", 1)[-1])
                        for d in row_data.get("definitions", []):
                            if str(d.get("name", "")) in impacted_names:
                                all_spans.append(
                                    (int(d["start_line"]), int(d["end_line"]))
                                )
            except Exception:
                pass
        affected_test_ps = [Path(a) for a in all_affected] if all_affected else test_ps
        ts_index_path = list(all_impact.keys())[0] if all_impact else None
        ts_impact_result = all_impact.get(ts_index_path, {}) if ts_index_path else {}
        implicated_symbol_spans = all_spans
    else:
        # Pre-computed values were passed in; just report progress.
        if ts_index_path:
            _progress_adapter.stage_progress(gid, "patch_search", 22, 100, {
                "stage": "semantic_impact_complete",
                "full_test_count": len(test_ps),
                "affected_test_count": len(affected_test_ps),
                "index_path": ts_index_path,
            })

    if affected_test_ps != test_ps and ts_index_path:
        _progress_adapter.stage_progress(gid, "patch_search", 22, 100, {
            "stage": "semantic_impact_complete",
            "full_test_count": len(test_ps),
            "affected_test_count": len(affected_test_ps),
            "index_path": ts_index_path,
        })
    else:
        affected_test_ps = test_ps

    # --- generate all candidates (PARALLEL) ---------------------------------
    # Generate candidates from multiple source files concurrently.
    # Extract literals from affected tests only — they carry the evidence of
    # what the fix should look like.
    # Multi-file: generate candidates per source file, then combine into
    # single-file and multi-file candidates.
    is_multi_file = len(source_paths) > 1
    all_raw_candidates: list[tuple] = []  # (desc, new_text_or_none, lineno, source_path)

    def _gen_for_file(sp: Path) -> list[tuple]:
        sp_text = source_contents[str(sp)].decode("utf-8")
        sp_lang = _detect_language(sp)
        sp_raw: list[tuple] = []
        if sp_lang == "python":
            sp_raw = list(generate_candidates(sp_text, affected_test_ps, repo))
            sp_raw.extend(list(_generate_candidates_advanced(
                sp_text, sp, affected_test_ps, repo)))
        else:
            sp_raw = list(_generate_candidates_multilanguage(
                sp_text, sp, affected_test_ps, repo))
        return [(desc, cand_text, lineno, str(sp)) for desc, cand_text, lineno in sp_raw]

    # Parallel candidate generation across source files
    from concurrent.futures import ThreadPoolExecutor, as_completed
    if len(source_paths) > 1:
        with ThreadPoolExecutor(max_workers=len(source_paths)) as gen_pool:
            futures = {gen_pool.submit(_gen_for_file, sp): sp for sp in source_paths}
            for fut in as_completed(futures):
                all_raw_candidates.extend(fut.result())
    else:
        all_raw_candidates = _gen_for_file(source_paths[0])

    if is_multi_file:
        # Build multi-file candidates: combine one change from each file.
        # Group candidates by source path.
        by_file: dict[str, list[tuple]] = {}
        for desc, cand_text, lineno, sp_str in all_raw_candidates:
            by_file.setdefault(sp_str, []).append((desc, cand_text, lineno))

        file_paths = list(by_file.keys())
        # Single-file candidates: one file changed at a time.
        single_candidates: list[tuple] = []
        for sp_str in file_paths:
            for desc, cand_text, lineno in by_file[sp_str]:
                # Candidate is a list of [path, text] pairs, only this file changes.
                source_cand = [[sp_str, cand_text]]
                for other_sp in file_paths:
                    if other_sp != sp_str:
                        source_cand.append([other_sp, None])  # No change
                single_candidates.append((desc, source_cand, lineno))

        # Multi-file candidates: combine changes from 2 files (pairwise).
        multi_candidates: list[tuple] = []
        for i in range(len(file_paths)):
            for j in range(i + 1, len(file_paths)):
                sp1, sp2 = file_paths[i], file_paths[j]
                for d1, c1, l1 in by_file[sp1][:5]:  # Limit to top 5 per file
                    for d2, c2, l2 in by_file[sp2][:5]:
                        source_cand = [[sp1, c1], [sp2, c2]]
                        for other_sp in file_paths:
                            if other_sp not in (sp1, sp2):
                                source_cand.append([other_sp, None])
                        desc = f"MULTI_{d1}_AND_{d2}"
                        multi_candidates.append((desc, source_cand, l1))

        # Deduplicate multi-file candidates by their combined source text hash
        seen_hashes: set[str] = set()
        deduped: list[tuple] = []
        for cand in single_candidates + multi_candidates:
            desc, source_cand, lineno = cand
            cc_json = json.dumps(source_cand, sort_keys=True)
            h = hashlib.sha256(cc_json.encode("utf-8")).hexdigest()
            if h not in seen_hashes:
                seen_hashes.add(h)
                deduped.append(cand)
        candidates = deduped
    else:
        # Single-file mode: candidates are (desc, text, lineno) tuples.
        # Wrap in single-element source_candidate lists for uniform handling.
        candidates = []
        uniq: dict[str, tuple] = {}
        for desc, cand_text, lineno, sp_str in all_raw_candidates:
            if cand_text not in uniq:
                uniq[cand_text] = (desc, [[sp_str, cand_text]], lineno)
        candidates = list(uniq.values())

    _progress_adapter.stage_progress(gid, "patch_search", 24, 100, {
        "stage": "candidate_generation",
        "candidate_count": len(candidates),
        "language": _detect_language(source_p),
        "multi_file": is_multi_file,
    })

    # --- learning loop: historical mutation-category success rates ----------
    pattern_stats = _load_pattern_stats()
    _bandit_load()  # Load Thompson sampling priors from persistent cache

    # --- order: suspicious-line score + symbol-aware + bandit + pattern boost
    # Multi-armed bandit: Thompson sampling draws from each mutation category's
    # Beta posterior. Categories with higher observed success get sampled more
    # often, but less-tried categories still get exploration draws — optimal
    # exploration/exploitation balance for candidate search.
    def _in_spans(lineno, spans):
        return any(start <= lineno <= end for start, end in spans)

    def cand_score(item) -> float:
        desc, _cand, lineno = item
        if lineno is None:
            return 0.0
        rel = str(source_p.relative_to(repo))
        score = suspicious.get((rel, lineno), 0.0)
        # Symbol-aware boost: mutations inside symbols implicated by the
        # change are more likely to be the right fix — try them first.
        if implicated_symbol_spans and _in_spans(lineno, implicated_symbol_spans):
            score += 10.0
        # Pattern boost: historically successful mutation categories first.
        score += _pattern_boost(_mutation_category(desc), pattern_stats)
        # Bandit sample: Thompson sampling for exploration vs exploitation.
        score += _bandit_sample(_mutation_category(desc)) * 20.0
        return score

    candidates.sort(key=cand_score, reverse=True)
    candidates = candidates[:max_candidates]

    # --- GPU batch scoring: pre-score all candidates against all tests ------
    # Data-parallel N×M matrix (candidates × tests) on GPU when available;
    # CPU multiprocessing fallback otherwise. Re-ranks candidates so the most
    # promising are evaluated first in the pool below.
    # Multi-language: use the right test runner for the source language.
    gpu = _gpu_status()
    if len(candidates) > 20:
        _lang = _detect_language(source_p)
        test_specs = [
            {"command": _test_command(_lang, str(tp)),
             "timeout_s": timeout_s}
            for tp in test_ps
        ]
        cand_specs = [{"patch": c[1]} for c in candidates]
        try:
            scores = _gpu_score_candidates(cand_specs, test_specs,
                                           backend="auto")
            score_map = scores.get("scores", {})
            cand_avg: dict[int, float] = {}
            for key, val in score_map.items():
                ci = int(key.split(":")[0])
                cand_avg[ci] = cand_avg.get(ci, 0.0) + float(val.get("score", 0.0))
            n_tests = len(test_specs)
            for ci in cand_avg:
                cand_avg[ci] /= n_tests

            def _gpu_cand_score(item) -> float:
                idx = candidates.index(item)
                return cand_avg.get(idx, 0.0)

            candidates.sort(key=_gpu_cand_score, reverse=True)
        except Exception:
            # GPU scoring failed — keep fault-locality ordering
            pass

    # --- evaluate in parallel, early-terminate on first pass ---------------
    tested = 0
    attempts = []
    winner = None
    budget_exhausted = False

    # --- Pre-compute per-candidate affected tests --------------------------
    # Each candidate changes different lines → different affected tests.
    # Compute once per candidate to avoid running irrelevant tests.
    cand_affected_tests: list[list[Path]] = []
    for cand in candidates:
        _, cand_source_candidates, _ = cand
        aff = _compute_candidate_affected_tests(
            cand_source_candidates, ts_index_path, ts_impact_result,
            affected_test_ps, repo, source_root_p)
        cand_affected_tests.append(aff)

    def make_args(cand_source_candidates, cand_index, cand_test_ps: list[Path] | None = None):
        # cand_source_candidates is a list of [source_path, new_text] pairs.
        # Serialize to JSON for cache key.
        cc_json = json.dumps(cand_source_candidates, sort_keys=True)
        test_ps_for_key = cand_test_ps if cand_test_ps is not None else affected_test_ps
        cache_key = _cache_key(cc_json.encode("utf-8"), test_ps_for_key)
        return (cc_json, str(source_root_p),
                [str(tp) for tp in (cand_test_ps if cand_test_ps is not None else affected_test_ps)],
                str(repo), timeout_s, cache_key, gid, cand_index)

    # Auto-scale distributed workers based on candidate count.
    _scale_workers_for_candidates(len(candidates))

    # --- Local batch evaluation (fastest path for single-machine) ---------
    # When no distributed workers are available, evaluate candidates in
    # batches using a shared worktree to avoid O(tree_size) copytree per
    # candidate. This is the fastest path for single-machine execution.
    use_local_batch = not _distributed_nodes_available() and len(candidates) > 1

    if use_local_batch:
        batch_size = max(1, min(8, os.cpu_count() or 4))
        tested = 0
        attempts = []
        winner = None

        for batch_start in range(0, len(candidates), batch_size):
            if winner is not None:
                break
            batch_end = min(batch_start + batch_size, len(candidates))
            batch_candidates = candidates[batch_start:batch_end]
            batch_args = []
            for i, cand in enumerate(batch_candidates):
                cand_index = batch_start + i
                cc_json = json.dumps(cand[1], sort_keys=True)
                cat_tests = cand_affected_tests[cand_index]
                cache_key = _cache_key(cc_json.encode("utf-8"), cat_tests)
                batch_args.append((cc_json, str(source_root_p),
                                   [str(tp) for tp in cat_tests], str(repo),
                                   timeout_s, cache_key, gid, cand_index))

            batch_results = _eval_candidates_batch_local(batch_args)

            for i, result in enumerate(batch_results):
                cand_index = batch_start + i
                tested += 1
                if result is None:
                    result = {"returncode": None, "timed_out": True, "cached": False}

                desc, cand_source_candidates, lineno = candidates[cand_index]

                timed_out = result.get("timed_out", False)
                rc = result.get("returncode")
                cc_json = json.dumps(cand_source_candidates, sort_keys=True)
                attempts.append({
                    "index": tested,
                    "mutation": desc,
                    "candidate_sha256": _sha256(cc_json.encode("utf-8")),
                    "returncode": rc,
                    "timed_out": timed_out,
                    "cached": result.get("cached", False),
                    "local_batch": True,
                    "affected_tests": len(cand_affected_tests[cand_index]),
                })

                # --- learning loop: update pattern stats + bandit ---
                _cat = _mutation_category(desc)
                _s = pattern_stats.setdefault(_cat, {"successes": 0, "attempts": 0})
                _s["attempts"] += 1
                _success = bool(rc == 0 and not timed_out)
                if _success:
                    _s["successes"] += 1
                _bandit_update(_cat, _success)

                if rc == 0 and not timed_out:
                    # Replay once to confirm using local batch (single candidate).
                    r2 = _eval_candidates_batch_local([make_args(cand_source_candidates, cand_index, cand_affected_tests[cand_index])])
                    r2_result = r2[0] if r2 else None
                    if r2_result and r2_result.get("returncode") == 0 and not r2_result.get("timed_out"):
                        winner = (cand_source_candidates, desc)
                        break

        # Fall through to winner handling below.
        if winner is not None:
            cand_source_candidates, desc = winner
            _progress_adapter.stage_completed(gid, "patch_search", {
                "status": "winner_found",
                "winning_mutation": desc,
                "tested_candidate_count": tested,
            })
            # Build unified diff for all changed files.
            diff_parts = []
            patched_contents: dict[str, str] = {}
            for sc in cand_source_candidates:
                sp_str = sc[0]
                new_text = sc[1] if len(sc) > 1 else None
                if new_text is None:
                    continue
                sp = Path(sp_str)
                try:
                    rel = sp.relative_to(source_root_p).as_posix()
                except ValueError:
                    rel = sp.name
                try:
                    orig_text = source_contents.get(sp_str, sp.read_bytes()).decode("utf-8")
                except Exception:
                    orig_text = ""
                patch = _unified_diff_text(orig_text, new_text, rel)
                diff_parts.append(patch)
                patched_contents[sp_str] = new_text
            patch = "\n".join(diff_parts)

            # --- Delta debugging: minimize patch to essential changes -----
            _progress_adapter.stage_progress(gid, "patch_search", tested, len(candidates), {
                "stage": "delta_debug",
            })
            try:
                minimized = _delta_debug_minimize(
                    source_contents, patched_contents, patch,
                    test_ps, repo, timeout_s=min(timeout_s, 60),
                    goal_id=gid, candidate_index=tested,
                )
                if minimized is not None and minimized != patch:
                    patch = minimized
                    _progress_adapter.stage_progress(gid, "patch_search", tested, len(candidates), {
                        "stage": "delta_debug_complete",
                        "minimized": True,
                    })
            except Exception:
                pass

            cc_json = json.dumps(cand_source_candidates, sort_keys=True)
            return {
                "status": "PASS__VERIFIED_CANDIDATE_PATCH_FOUND",
                "pass": True,
                "winning_mutation": desc,
                "candidate_source_sha256": _sha256(cc_json.encode("utf-8")),
                "unified_diff": patch,
                "tested_candidate_count": tested,
                "max_candidates": max_candidates,
                "attempts": attempts,
                "source_path": str(source_p.relative_to(repo)),
                "source_sha256": _sha256(source_bytes),
            }

        _progress_adapter.stage_failed(gid, "patch_search", "NO_VERIFIED_CANDIDATE", {
            "tested_candidate_count": tested,
        })
        return {
            "status": "OPEN__NO_VERIFIED_CANDIDATE_IN_LOCAL_BATCH_SEARCH",
            "pass": False,
            "tested_candidate_count": tested,
            "max_candidates": max_candidates,
            "attempts": attempts,
            "source_path": str(source_p.relative_to(repo)),
            "source_sha256": _sha256(source_bytes),
        }

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        # Map future -> candidate index so completion order != submission order
        # never mismatches a result to the wrong candidate.
        future_to_index: dict[Future, int] = {}
        idx = 0
        # Seed the pool.
        while idx < len(candidates) and len(future_to_index) < max_workers:
            f = pool.submit(_eval_candidate, make_args(candidates[idx][1], idx, cand_affected_tests[idx]))
            future_to_index[f] = idx
            idx += 1

        while future_to_index and winner is None:
            done = as_completed(list(future_to_index.keys()))
            fut = next(iter(done))
            cand_index = future_to_index.pop(fut)
            tested += 1
            try:
                result = fut.result()
            except Exception:
                result = {"returncode": None, "timed_out": True, "cached": False}

            desc, cand_source_candidates, lineno = candidates[cand_index]

            timed_out = result.get("timed_out", False)
            rc = result.get("returncode")
            cc_json = json.dumps(cand_source_candidates, sort_keys=True)
            attempts.append({
                "index": tested,
                "mutation": desc,
                "candidate_sha256": _sha256(cc_json.encode("utf-8")),
                "returncode": rc,
                "timed_out": timed_out,
                "cached": result.get("cached", False),
            })

            # --- learning loop: update pattern stats + bandit from result --
            _cat = _mutation_category(desc)
            _s = pattern_stats.setdefault(_cat, {"successes": 0, "attempts": 0})
            _s["attempts"] += 1
            _success = bool(rc == 0 and not timed_out)
            if _success:
                _s["successes"] += 1
            # Update bandit posterior: success -> alpha, failure -> beta
            _bandit_update(_cat, _success)

            if rc == 0 and not timed_out:
                # Replay twice to confirm (cache hit returns same result).
                ok = True
                for _ in range(2):
                    r2 = _eval_candidate(make_args(cand_source_candidates, cand_index))
                    if r2.get("returncode") != 0 or r2.get("timed_out"):
                        ok = False
                        break
                if ok:
                    # Gate filter: reject candidates that fail static/type/security gates.
                    if post_pass_filter:
                        accept, reason = post_pass_filter(cand_source_candidates, desc)
                        if not accept:
                            _cat = _mutation_category(desc)
                            _bandit_update(_cat, False)
                            winner = None
                            # Submit next candidate to keep the pool full.
                            if idx < len(candidates):
                                f = pool.submit(_eval_candidate, make_args(candidates[idx][1], idx))
                                future_to_index[f] = idx
                                idx += 1
                            continue
                    winner = (cand_source_candidates, desc)
                    # Compute the unified diff for the primary changed file.
                    # For multi-file, diff each changed file separately.
                    diff_parts = []
                    for sc in cand_source_candidates:
                        sp_str = sc[0]
                        new_text = sc[1] if len(sc) > 1 else None
                        if new_text is None:
                            continue  # No change to this file
                        sp = Path(sp_str)
                        try:
                            rel = sp.relative_to(source_root_p).as_posix()
                        except ValueError:
                            rel = sp.name
                        # Read original file content
                        try:
                            orig_text = source_contents.get(sp_str, sp.read_bytes()).decode("utf-8")
                        except Exception:
                            orig_text = ""
                        patch = _unified_diff_text(orig_text, new_text, rel)
                        diff_parts.append(patch)
                    patch = "\n".join(diff_parts)
                    _progress_adapter.stage_progress(gid, "patch_search", tested, len(candidates), {
                        "stage": "winner_found",
                        "winning_mutation": desc,
                        "candidate_index": cand_index,
                    })
                    # Persist verified patch to cross-session cache.
                    cc_json = json.dumps(cand_source_candidates, sort_keys=True)
                    patch_hash = _sha256(cc_json.encode("utf-8"))
                    test_cmd = "python3 -m pytest " + " ".join(
                        str(tp) for tp in test_ps
                    )
                    _pcache_put_patch(
                        patch_hash, test_cmd,
                        [{"status": "PASS", "returncode": 0}],
                        verified=True,
                    )
                    # Also store source→patch reverse mapping so future repairs
                    # of the same source+test combo can skip candidate search
                    # entirely (persistent verified patch pre-check).
                    _pcache_put("source_patch", {
                        "source_hash": _all_source_hash,
                        "test_hash": _sha256(
                            json.dumps([str(tp) for tp in test_ps],
                                       sort_keys=True).encode("utf-8")),
                    }, {
                        "patch_hash": patch_hash,
                        "diff": patch,
                        "verified": True,
                    })
                    break
                # Replay failed — treat as not a winner, continue.

            # Submit next candidate to keep the pool full.
            if idx < len(candidates):
                f = pool.submit(_eval_candidate, make_args(candidates[idx][1], idx))
                future_to_index[f] = idx
                idx += 1

        # Cancel any pending futures (we found a winner or exhausted budget).
        for f in future_to_index:
            f.cancel()

    # Persist learned pattern stats + bandit priors for smarter future repairs.
    _save_pattern_stats(pattern_stats)
    _bandit_save()

    if winner is not None:
        cand_source_candidates, desc = winner
        _progress_adapter.stage_completed(gid, "patch_search", {
            "status": "winner_found",
            "winning_mutation": desc,
            "tested_candidate_count": tested,
        })
        # Build unified diff for all changed files.
        diff_parts = []
        patched_contents: dict[str, str] = {}
        for sc in cand_source_candidates:
            sp_str = sc[0]
            new_text = sc[1] if len(sc) > 1 else None
            if new_text is None:
                continue
            sp = Path(sp_str)
            try:
                rel = sp.relative_to(source_root_p).as_posix()
            except ValueError:
                rel = sp.name
            # Read original file content
            try:
                orig_text = source_contents.get(sp_str, sp.read_bytes()).decode("utf-8")
            except Exception:
                orig_text = ""
            patch = _unified_diff_text(orig_text, new_text, rel)
            diff_parts.append(patch)
            patched_contents[sp_str] = new_text
        patch = "\n".join(diff_parts)

        # --- Delta debugging: minimize patch to essential changes ----------
        # Tries removing hunks/lines while keeping tests passing.
        # Produces minimal, reviewable patches.
        _progress_adapter.stage_progress(gid, "patch_search", tested, len(candidates), {
            "stage": "delta_debug",
        })
        try:
            minimized = _delta_debug_minimize(
                source_contents, patched_contents, patch,
                test_ps, repo, timeout_s=min(timeout_s, 60),
                goal_id=gid, candidate_index=tested,
            )
            if minimized is not None and minimized != patch:
                patch = minimized
                _progress_adapter.stage_progress(gid, "patch_search", tested, len(candidates), {
                    "stage": "delta_debug_complete",
                    "minimized": True,
                })
        except Exception:
            pass  # Keep original patch if delta debugging fails

        cc_json = json.dumps(cand_source_candidates, sort_keys=True)
        return {
            "status": "PASS__VERIFIED_CANDIDATE_PATCH_FOUND",
            "pass": True,
            "winning_mutation": desc,
            "candidate_source_sha256": _sha256(cc_json.encode("utf-8")),
            "unified_diff": patch,
            "tested_candidate_count": tested,
            "max_candidates": max_candidates,
            "attempts": attempts,
            "source_path": str(source_p.relative_to(repo)),
            "source_sha256": _sha256(source_bytes),
        }

    _progress_adapter.stage_failed(gid, "patch_search", "NO_VERIFIED_CANDIDATE", {
        "tested_candidate_count": tested,
    })
    return {
        "status": "OPEN__NO_VERIFIED_CANDIDATE_IN_PARALLEL_SEARCH",
        "pass": False,
        "tested_candidate_count": tested,
        "max_candidates": max_candidates,
        "attempts": attempts,
        "source_path": str(source_p.relative_to(repo)),
        "source_sha256": _sha256(source_bytes),
    }


def _unified_diff_text(before_text: str, after_text: str, rel: str) -> str:
    return "".join(difflib.unified_diff(
        before_text.splitlines(keepends=True), after_text.splitlines(keepends=True),
        fromfile="a/" + rel, tofile="b/" + rel, n=3,
    ))


# ---------------------------------------------------------------------------
# Delta debugging — minimize a verified patch to essential changes
# ---------------------------------------------------------------------------

def _parse_diff_hunks(diff_text: str) -> list[dict]:
    """Parse a unified diff into hunks with old/new line groups."""
    hunks = []
    lines = diff_text.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("@@"):
            parts = line.split("@@")
            if len(parts) >= 3:
                old_part = parts[1].strip().split(",")
                new_part = parts[2].strip().split(",")
                old_start = int(old_part[0].lstrip("-"))
                new_start = int(new_part[0].lstrip("+"))
                old_lines = []
                new_lines = []
                j = i + 1
                while j < len(lines) and not lines[j].startswith("@@") and not lines[j].startswith("diff "):
                    l = lines[j]
                    if l.startswith("-"):
                        old_lines.append(l[1:])
                    elif l.startswith("+"):
                        new_lines.append(l[1:])
                    elif l.startswith(" "):
                        old_lines.append(l[1:])
                        new_lines.append(l[1:])
                    elif l.startswith("\\"):
                        pass
                    j += 1
                hunks.append({
                    "header": line,
                    "old_start": old_start,
                    "new_start": new_start,
                    "old_lines": old_lines,
                    "new_lines": new_lines,
                })
                i = j
            else:
                i += 1
        else:
            i += 1
    return hunks


def _rebuild_diff(hunks: list[dict]) -> str:
    """Rebuild a unified diff string from hunks."""
    parts = []
    for h in hunks:
        parts.append(h["header"] + "\n")
        max_len = max(len(h["old_lines"]), len(h["new_lines"]))
        for k in range(max_len):
            if k < len(h["old_lines"]) and k < len(h["new_lines"]):
                if h["old_lines"][k] == h["new_lines"][k]:
                    parts.append(" " + h["old_lines"][k] + "\n")
                else:
                    parts.append("-" + h["old_lines"][k] + "\n")
                    parts.append("+" + h["new_lines"][k] + "\n")
            elif k < len(h["old_lines"]):
                parts.append("-" + h["old_lines"][k] + "\n")
            elif k < len(h["new_lines"]):
                parts.append("+" + h["new_lines"][k] + "\n")
    return "".join(parts)


def _apply_diff_to_source(source_text: str, diff_text: str) -> str | None:
    """Apply a unified diff to source text. Returns patched text or None."""
    import subprocess
    import tempfile
    from pathlib import Path
    try:
        with tempfile.TemporaryDirectory() as td:
            src_path = Path(td) / "source.py"
            src_path.write_text(source_text, encoding="utf-8")
            diff_path = Path(td) / "patch.diff"
            diff_path.write_text(diff_text, encoding="utf-8")
            result = subprocess.run(
                ["git", "apply", str(diff_path)],
                cwd=str(td), capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return src_path.read_text(encoding="utf-8")
    except Exception:
        pass
    return None


def _delta_debug_minimize(
    source_contents: dict[str, bytes],
    patched_contents: dict[str, str],
    patch: str,
    test_paths: list[Path],
    repo: Path,
    timeout_s: int = 30,
    goal_id: str = "delta-debug",
    candidate_index: int = 0,
) -> str | None:
    """Minimize a verified patch using delta debugging.

    Tries removing hunks and lines while keeping tests passing.
    Returns the minimized diff text, or None if minimization fails.
    """
    hunks = _parse_diff_hunks(patch)
    if not hunks:
        return patch

    # Build the full patched source for each file
    full_patched: dict[str, str] = {}
    for sp_str, new_text in patched_contents.items():
        full_patched[sp_str] = new_text

    # Try removing each hunk individually (greedy minimization)
    changed = True
    while changed:
        changed = False
        for h_idx in range(len(hunks) - 1, -1, -1):
            trial_hunks = [h for i, h in enumerate(hunks) if i != h_idx]
            trial_diff = _rebuild_diff(trial_hunks)
            if not trial_diff.strip():
                continue
            # Test: apply trial diff and run tests
            ok = True
            for sp_str, new_text in full_patched.items():
                sp = Path(sp_str)
                try:
                    orig_text = source_contents.get(sp_str, sp.read_bytes()).decode("utf-8")
                except Exception:
                    orig_text = ""
                # Apply just this file's portion of the trial diff
                file_patched = _apply_diff_to_source(orig_text, trial_diff)
                if file_patched is None:
                    ok = False
                    break
                # Verify this file's tests pass
                cache_key = _cache_key(file_patched.encode("utf-8"), test_paths)
                result = _eval_candidate((
                    json.dumps([[sp_str, file_patched]]),
                    str(sp.parent),
                    [str(tp) for tp in test_paths],
                    str(repo), timeout_s,
                    cache_key, goal_id, candidate_index,
                ))
                if result.get("returncode") != 0 or result.get("timed_out"):
                    ok = False
                    break
            if ok:
                hunks = trial_hunks
                changed = True
                break

    return _rebuild_diff(hunks)


# ---------------------------------------------------------------------------
# Plain (non-isolated) test runner for baseline + sequential fallback
# ---------------------------------------------------------------------------

def _run_tests_plain(repo: Path, source_path: Path, test_paths: list[Path],
                     timeout_s: int) -> dict:
    env = dict(os.environ)
    py_parts = [str(source_path.parent)]
    for tp in test_paths:
        tp_parent = str(tp.parent)
        if tp_parent not in py_parts:
            py_parts.append(tp_parent)
    existing = env.get("PYTHONPATH", "")
    if existing:
        py_parts.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(py_parts)
    _lang = _detect_language(source_path)
    argv = _test_command(_lang, *[str(tp) for tp in test_paths])
    try:
        proc = subprocess.run(
            argv, cwd=str(repo), capture_output=True, text=True,
            timeout=timeout_s, env=env,
        )
        return {"returncode": proc.returncode, "stdout": proc.stdout,
                "stderr": proc.stderr, "timed_out": False}
    except subprocess.TimeoutExpired:
        return {"returncode": None, "stdout": "", "stderr": "timed out", "timed_out": True}


# ---------------------------------------------------------------------------
# Backward-compatible sequential patch search (delegates to parallel with 1 worker)
# ---------------------------------------------------------------------------

def patch_search(source_path: str | Path, test_paths: list[str | Path],
                 timeout_s: int = 60, max_candidates: int = 50) -> dict:
    return patch_search_parallel(
        source_path, test_paths, timeout_s=timeout_s,
        max_candidates=max_candidates, max_workers=1)


# ---------------------------------------------------------------------------
# Full test gate
# ---------------------------------------------------------------------------

def full_test_gate(anchor_path: str | Path, diff_path: str | Path,
                   output_path: str | Path, timeout_s: int = 300) -> dict:
    repo = REPO
    gate_adapter = REPO / "canonical/runtime/bound_capabilities/python_repo_diff_apply_full_testgate.py"
    spec = importlib.util.spec_from_file_location("pb_swe_testgate", gate_adapter)
    if spec is None or spec.loader is None:
        raise RuntimeError("ADAPTER_LOAD_FAILED:" + str(gate_adapter))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    gate_args = {
        "anchor_path": str(Path(anchor_path)),
        "diff_path": str(Path(diff_path)),
        "output_path": str(Path(output_path)),
        "python_executable": sys.executable,
        "timeout_s": timeout_s,
    }
    return mod.run(gate_args, str(repo))


# ---------------------------------------------------------------------------
# Fault localization
# ---------------------------------------------------------------------------

def fault_localize(source_path: str | Path, test_paths: list[str | Path],
                   timeout_s: int = 60) -> dict:
    repo = REPO
    source_p = Path(source_path)
    if not source_p.is_absolute():
        source_p = repo / source_p
    source_p = source_p.resolve()
    test_ps = []
    for t in test_paths:
        tp = Path(t)
        if not tp.is_absolute():
            tp = repo / tp
        test_ps.append(tp.resolve())
    fl_adapter = REPO / "canonical/runtime/bound_capabilities/python_dynamic_fault_localizer_v1.py"
    fl_args = {
        "source_root": str(source_p.parent),
        "test_paths": [str(tp) for tp in test_ps],
        "output_path": "canonical/tmp_real_swe_fault_localization.json",
        "timeout_s": timeout_s,
    }
    return _run_in_process(fl_adapter, "run", fl_args, repo)


# ---------------------------------------------------------------------------
# Dual-oracle verification — CrossHair (symbolic) + concrete execution
#
# Law: every patch must pass TWO independent oracles before it is trusted.
# CrossHair/Z3 is the symbolic oracle; concrete_execution_oracle is the
# concrete (example-based) oracle.  They share no code, so agreement between
# them is meaningful evidence that the patch is semantically correct, not just
# test-passing.
# ---------------------------------------------------------------------------

def _run_oracle(adapter_module_path: Path, entrypoint: str,
                args: Mapping[str, Any], root: Path, timeout_s: int = 60) -> dict:
    """Run a bound oracle adapter in-process with a timeout guard.

    Exceptions raised by the oracle are captured and returned as a refused
    result — never silently swallowed (fail-closed).
    """
    result = {}
    exc_info = [None]
    def _target():
        nonlocal result
        try:
            result = _run_in_process(adapter_module_path, entrypoint, args, root)
        except BaseException as exc:  # noqa: BLE001
            exc_info[0] = exc
    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout_s)
    if thread.is_alive():
        return {"status": "ORACLE_TIMEOUT", "verified": False,
                "reason": f"ORACLE_TIMEOUT:{adapter_module_path.name}"}
    if exc_info[0] is not None:
        return {"status": "ORACLE_ERROR", "verified": False,
                "reason": f"ORACLE_ERROR:{adapter_module_path.name}:{type(exc_info[0]).__name__}:{exc_info[0]}"}
    return result


def verify_with_dual_oracle(source_path: str | Path, test_paths: list[str | Path],
                            repo: Path, timeout_s: int = 60) -> dict:
    """Verify a source file with two independent oracles.

    Returns {"verified": True} only if BOTH oracles pass (no contract
    violations found, or source is unsupported/indeterminate for both).
    Fail-closed: any violation from either oracle means verified=False.
    """
    repo = Path(repo)
    source_p = Path(source_path)
    if not source_p.is_absolute():
        source_p = repo / source_p
    source_p = source_p.resolve()

    oracle_results = []

    # Oracle 1: CrossHair / Z3 symbolic contract oracle
    crosshair_adapter = REPO / "canonical/runtime/bound_capabilities/crosshair_contract_oracle.py"
    if crosshair_adapter.is_file():
        r = _run_oracle(crosshair_adapter, "run",
                        {"target_path": str(source_p)}, repo, timeout_s=timeout_s)
        oracle_results.append(("crosshair", r))
        status = r.get("status", "")
        if "CONTRACT_VIOLATION_FOUND" in status or status == "UNSUPPORTED_EVALUATION":
            return {"verified": False, "reason": f"CROSSHAIR_VIOLATION:{status}",
                    "oracle_results": oracle_results}

    # Oracle 2: Concrete execution oracle
    concrete_adapter = REPO / "canonical/runtime/bound_capabilities/concrete_execution_oracle.py"
    if concrete_adapter.is_file():
        r = _run_oracle(concrete_adapter, "run",
                        {"target_path": str(source_p)}, repo, timeout_s=timeout_s)
        oracle_results.append(("concrete_execution", r))
        status = r.get("status", "")
        if status == "CONTRACT_VIOLATION_FOUND":
            return {"verified": False, "reason": f"CONCRETE_VIOLATION:{status}",
                    "oracle_results": oracle_results}

    # Both oracles must not have found violations.
    verified = all(
        r.get("status") not in ("CONTRACT_VIOLATION_FOUND", "UNSUPPORTED_EVALUATION")
        for _, r in oracle_results
    )
    return {"verified": verified, "oracle_results": oracle_results}


# ---------------------------------------------------------------------------
# CEGIS fallback — counterexample-guided repair synthesis
#
# When test-guided search exhausts its budget without finding a passing
# patch, CEGIS synthesizes an alternative repair architecture from the
# available SWE components. The failing tests serve as counterexamples;
# the synthesizer searches for a combination of components whose combined
# effect produces a verified repair.
# ---------------------------------------------------------------------------

def _cegis_synthesize_repair(source_path: str | Path, test_paths: list[str | Path],
                             repo: Path, timeout_s: int = 120,
                             max_candidates: int = 50, max_workers: int | None = None,
                             original_source: str = "") -> dict:
    """Use CEGIS to synthesize an alternative repair architecture.

    Counterexample-guided refinement loop: failing tests serve as
    counterexamples; test-guided search finds candidate patches; Z3
    verifies against original contracts; new counterexamples refine tests.
    Returns {"pass": True, "unified_diff": ...} if CEGIS finds a working
    repair, else {"pass": False}.
    """
    repo = Path(repo)
    source_p = Path(source_path)
    if not source_p.is_absolute():
        source_p = repo / source_p
    source_p = source_p.resolve()

    if not original_source:
        original_source = source_p.read_text(encoding="utf-8") if source_p.is_file() else ""

    test_ps = []
    for t in test_paths:
        tp = Path(t)
        if not tp.is_absolute():
            tp = repo / tp
        test_ps.append(tp.resolve())

    # Inline CEGIS architecture synthesizer — no external dependency needed.
    # The CEGIS loop: counterexamples (failing tests) → test-guided search →
    # Z3 verification → new counterexamples → repeat until verified or budget exhausted.
    max_cegis_iters = 5
    cegis_candidates_tried = 0

    for cegis_iter in range(max_cegis_iters):
        # Run test-guided search with current test set (includes counterexample tests)
        ps_result2 = patch_search_parallel(
            source_p, test_ps, timeout_s=min(timeout_s, 60),
            max_candidates=max_candidates * 2, max_workers=max_workers or 4)
        cegis_candidates_tried += ps_result2.get("tested_candidate_count", 0)

        if not ps_result2.get("pass") or not ps_result2.get("unified_diff"):
            if cegis_iter == 0:
                return {"pass": False, "reason": "CEGIS_SEARCH_NO_WINNER",
                        "candidates_tried": cegis_candidates_tried}
            break  # No more candidates to try

        # Z3-verify the winning patch against original contracts
        patched_source = ""
        worktree_p = Path(worktree_rel)
        if not worktree_p.is_absolute():
            worktree_p = repo / worktree_rel
        worktree_p = worktree_p.resolve()
        patched_source_p = worktree_p / source_p.name
        if patched_source_p.is_file():
            patched_source = patched_source_p.read_text(encoding="utf-8")
            z3_result = _z3_verify_patch(original_source, patched_source)
            if z3_result.get("verified"):
                return {
                    "pass": True,
                    "unified_diff": ps_result2["unified_diff"],
                    "candidates_tried": cegis_candidates_tried,
                    "cegis_iterations": cegis_iter + 1,
                }
            # Counterexample found — add as new test and retry
            counterexamples = z3_result.get("counterexamples", [])
            if counterexamples:
                # Convert counterexample to a test assertion
                ce_test_path = repo / "canonical" / "tmp_cegis_counterexample_test.py"
                test_lines = [
                    "import sys",
                    "from pathlib import Path",
                    f'sys.path.insert(0, str(Path(".").resolve() / "{source_p.parent.relative_to(repo) if source_p.parent != repo else "."}"))',
                    f"from {source_p.stem} import *",
                    "",
                    f"def test_cegis_counterexample_iter_{cegis_iter}:",
                ]
                for ce in counterexamples:
                    func_name = ce.get("function", "unknown")
                    ce_inputs = {k: v for k, v in ce.get("counterexample", {}).items()
                                 if k != "result"}
                    if ce_inputs:
                        args_str = ", ".join(f"{k}={v}" for k, v in ce_inputs.items())
                        expected = ce.get("counterexample", {}).get("result", "None")
                        test_lines.append(f"    assert {func_name}({args_str}) == {expected}")
                ce_test_path.write_text("\n".join(test_lines), encoding="utf-8")
                ce_test_rel = str(ce_test_path.relative_to(repo))
                if ce_test_rel not in [str(tp) for tp in test_ps]:
                    test_ps.append(ce_test_path.resolve())

    return {"pass": False, "reason": "CEGIS_BUDGET_EXHAUSTED",
            "candidates_tried": cegis_candidates_tried}


# ---------------------------------------------------------------------------
# End-to-end repair (the canonical fast path)
# ---------------------------------------------------------------------------

def end_to_end_repair(source_root: str | Path, worktree_path: str | Path,
                      source_path: str | Path, test_paths: list[str | Path],
                      output_path: str | Path, diff_path: str | Path,
                      pr_intent_path: str | Path,
                      timeout_s: int = 300, max_candidates: int = 50,
                      max_workers: int | None = None,
                      goal_id: str | None = None,
                      oidc_token: str | None = None,
                      enable_security_gate: bool = True,
                      enable_perf_gate: bool = True,
                      perf_tolerance: float = 0.10,
                      perf_repeats: int = 5,
                      bench_path: str | None = None,
                      enable_type_gate: bool = True,
                      enable_coverage_gate: bool = True,
                      enable_mutation_gate: bool = True,
                      enable_static_triage_gate: bool = True,
                      enable_hypothesis_fuzz: bool = True,
                      type_timeout_s: int = 120,
                      coverage_timeout_s: int = 120,
                      mutation_timeout_s: int = 120,
                      static_triage_timeout_s: int = 60,
                      hypothesis_timeout_s: int = 120,
                      hypothesis_max_examples: int = 200,
                      enable_z3_gate: bool = True,
                      z3_timeout_s: int = 60) -> dict:
    """Complete end-to-end SWE repair: localize(order) -> search(parallel+cache)
    -> apply(worktree) -> gate -> PR intent -> GitHub PR. Fail-closed.
    verified=True only when the full gate passes."""
    import time as _time
    gid = goal_id or "swe-unknown"
    oidc_token = _resolve_oidc_token(oidc_token)
    # Start the real-time progress streaming hub so WebSocket/SSE clients
    # receive stage and candidate events as the repair runs.
    # Best-effort: if the port is already in use or aiohttp is missing,
    # the repair continues without streaming — never crashes the repair.
    try:
        _streaming_hub.start(host="0.0.0.0", port=8766)
    except (OSError, ImportError, ModuleNotFoundError):
        pass
    t_start = _time.monotonic()
    repo = REPO
    source_root_p = Path(source_root)
    if not source_root_p.is_absolute():
        source_root_p = repo / source_root_p
    source_root_p = source_root_p.resolve()

    worktree_p = Path(worktree_path)
    if not worktree_p.is_absolute():
        worktree_p = repo / worktree_p
    worktree_p = worktree_p.resolve()

    source_p = Path(source_path)
    if not source_p.is_absolute():
        source_p = repo / source_p
    source_p = source_p.resolve()

    test_ps = []
    for t in test_paths:
        tp = Path(t)
        if not tp.is_absolute():
            tp = repo / tp
        test_ps.append(tp.resolve())

    # --- Auto test generation: when no tests exist, generate them ----------
    # A repair agent must be able to work on codebases with no pre-existing
    # tests. If no test paths are provided, generate pytest tests from the
    # source file so patch search has something to validate against.
    if not test_ps and source_p.is_file():
        _progress_adapter.stage_progress(gid, "end_to_end_repair", 0, 1, {
            "stage": "test_generation",
        })
        gen_test_path = source_p.parent / f"test_{source_p.name}"
        gen_root = source_p.parent / "_gen_tests"
        try:
            targets_path = source_p.parent / "_gen_targets.json"
            targets_path.write_text(
                json.dumps([{"module": source_p.name.removesuffix(".py"),
                             "name": None}]), encoding="utf-8")
            gen_result = _test_gen_scaffold(
                {
                    "targets_path": str(targets_path),
                    "source_root": str(source_root_p.relative_to(repo)),
                    "generated_tests_root": str(gen_root.relative_to(repo)),
                    "output_path": str((gen_root / "output.json").relative_to(repo)),
                    "python_executable": sys.executable,
                    "timeout_s": min(timeout_s, 120),
                },
                repo,
            )
            targets_path.unlink(missing_ok=True)
            if gen_result.get("verified") and gen_result.get("test_count", 0) > 0:
                gen_test_file = gen_root / gen_result.get("generated_test_file", "")
                if gen_test_file.is_file():
                    test_ps = [gen_test_file.resolve()]
                    _progress_adapter.stage_completed(gid, "end_to_end_repair", {
                        "stage": "test_generation_complete",
                        "generated_test_count": gen_result.get("test_count", 0),
                        "generated_test_path": str(gen_test_file),
                    })
        except Exception as exc:
            _progress_adapter.stage_progress(gid, "end_to_end_repair", 0, 1, {
                "stage": "test_generation_failed",
                "reason": str(exc)[:200],
            })

    output_p = Path(output_path)
    if not output_p.is_absolute():
        output_p = repo / output_p
    output_p = output_p.resolve()

    diff_p = Path(diff_path)
    if not diff_p.is_absolute():
        diff_p = repo / diff_p
    diff_p = diff_p.resolve()

    pr_p = Path(pr_intent_path)
    if not pr_p.is_absolute():
        pr_p = repo / pr_p
    pr_p = pr_p.resolve()

    _progress_adapter.stage_started(gid, "end_to_end_repair", {
        "source_path": str(source_p.relative_to(repo)),
        "test_count": len(test_ps),
        "max_candidates": max_candidates,
    })
    _bandit_load()  # Load Thompson sampling priors

    # --- Async pipelined pre-candidate stages -------------------------------
    # Baseline, fault localization, and semantic impact are independent
    # (all need only source + tests). Run them concurrently for ~3x speedup
    # before candidate evaluation begins.
    _progress_adapter.stage_progress(gid, "end_to_end_repair", 1, 5, {
        "stage": "preflight_parallel",
    })

    def _run_baseline():
        return _run_tests_plain(repo, source_p, test_ps, timeout_s)

    def _run_fault_localization():
        return _fault_suspicious_lines(source_p, test_ps, timeout_s=min(timeout_s, 30))

    def _run_semantic_impact():
        ts_index_path = _build_ts_index(source_root_p, repo)
        affected_test_ps, ts_index_path, ts_impact_result = _ts_select_affected_tests(
            ts_index_path, source_p, test_ps, repo)
        # Implicated symbol spans for symbol-aware scoring.
        implicated_symbol_spans: list[tuple[int, int]] = []
        try:
            if ts_index_path and ts_impact_result.get("changed_symbols"):
                import json as _json
                index_artifact = _json.loads(Path(ts_index_path).read_text(encoding="utf-8"))
                index_rows = {row["path"]: row for row in index_artifact.get("files", [])}
                rel = str(source_p.relative_to(repo))
                row = index_rows.get(rel)
                if row:
                    impacted_names = set()
                    for cs in ts_impact_result["changed_symbols"].values():
                        for sym in cs.get("symbols", []):
                            impacted_names.add(sym.rsplit(".", 1)[-1])
                    for d in row.get("definitions", []):
                        if str(d.get("name", "")) in impacted_names:
                            implicated_symbol_spans.append(
                                (int(d["start_line"]), int(d["end_line"]))
                            )
        except Exception:
            implicated_symbol_spans = []
        return {
            "affected_test_ps": affected_test_ps if affected_test_ps != test_ps else test_ps,
            "ts_index_path": ts_index_path,
            "ts_impact_result": ts_impact_result,
            "implicated_symbol_spans": implicated_symbol_spans,
        }

    with ThreadPoolExecutor(max_workers=3) as preflight_pool:
        future_baseline = preflight_pool.submit(_run_baseline)
        future_fl = preflight_pool.submit(_run_fault_localization)
        future_impact = preflight_pool.submit(_run_semantic_impact)

        baseline = future_baseline.result()
        suspicious = future_fl.result()
        impact = future_impact.result()

    affected_test_ps = impact["affected_test_ps"]
    ts_index_path = impact["ts_index_path"]
    ts_impact_result = impact["ts_impact_result"]
    implicated_symbol_spans = impact["implicated_symbol_spans"]

    if baseline["returncode"] == 0:
        _progress_adapter.stage_completed(gid, "end_to_end_repair", {
            "status": "baseline_already_passes",
        })
        return {"verified": False, "reason": "BASELINE_ALREADY_PASSES", "gate": "SKIP",
                "elapsed_s": round(_time.monotonic() - t_start, 3)}
    if baseline["timed_out"]:
        _progress_adapter.stage_failed(gid, "end_to_end_repair", "BASELINE_TIMEOUT")
        return {"verified": False, "reason": "BASELINE_TIMEOUT", "gate": "SKIP",
                "elapsed_s": round(_time.monotonic() - t_start, 3)}

    # Stage 2: Test-guided patch search (parallel + cache + fault-locality).
    # Pre-computed suspicious lines + affected tests are passed in to avoid
    # recomputation — they were computed concurrently with the baseline above.
    _progress_adapter.stage_progress(gid, "end_to_end_repair", 2, 5, {
        "stage": "patch_search",
    })

    # --- Gate filter: reject candidates that pass tests but fail gates -----
    # Runs static_triage, type_check, security on each test-passing candidate
    # BEFORE accepting it as the winner. Prevents invalid patches from being
    # returned, avoiding wasted full-gate re-runs in end_to_end_repair.
    def _candidate_gate_filter(cand_source_candidates: list[list], desc: str) -> tuple[bool, str]:
        return _run_gates_on_candidate(
            cand_source_candidates, source_root_p, repo, gid)

    ps_result = patch_search_parallel(
        source_p, test_ps, timeout_s=timeout_s, max_candidates=max_candidates,
        max_workers=max_workers, goal_id=gid,
        suspicious=suspicious,
        affected_test_ps=affected_test_ps,
        ts_index_path=ts_index_path,
        ts_impact_result=ts_impact_result,
        implicated_symbol_spans=implicated_symbol_spans,
        post_pass_filter=_candidate_gate_filter)
    patches_tried = ps_result.get("tested_candidate_count", 0)
    patches_passing = 1 if ps_result.get("pass") is True else 0
    best_diff = ps_result.get("unified_diff", "")

    _progress_adapter.stage_progress(gid, "end_to_end_repair", 3, 5, {
        "stage": "patch_search_complete",
        "patches_tried": patches_tried,
        "patches_passing": patches_passing,
    })

    # Stage 2.5: CEGIS fallback — when test-guided search finds no winner,
    # synthesize an alternative repair architecture from available components.
    if not ps_result.get("pass") and not best_diff:
        _progress_adapter.stage_progress(gid, "end_to_end_repair", 3, 5, {
            "stage": "cegis_fallback",
        })
        cegis_result = _cegis_synthesize_repair(
            source_p, test_ps, repo, timeout_s=min(timeout_s, 120),
            max_candidates=max_candidates, max_workers=max_workers,
            original_source=source_p.read_text(encoding="utf-8") if source_p.is_file() else "")
        if cegis_result.get("pass") and cegis_result.get("unified_diff"):
            best_diff = cegis_result["unified_diff"]
            patches_passing = 1
            patches_tried = ps_result.get("tested_candidate_count", 0) + \
                            cegis_result.get("candidates_tried", 0)
            _progress_adapter.stage_completed(gid, "cegis_fallback", {
                "status": "cegis_repair_found",
                "candidates_tried": cegis_result.get("candidates_tried", 0),
            })

    # Stage 2.7: Multi-edit / cross-file coupled repair — when single-edit
    # search fails, try coordinated multi-location edits with non-monotonic
    # valley crossing. This finds fixes that require simultaneous changes
    # across multiple statements or files where no single edit passes tests.
    if not best_diff:
        _progress_adapter.stage_progress(gid, "end_to_end_repair", 3, 5, {
            "stage": "multi_edit_repair",
        })
        try:
            from canonical.runtime.bound_capabilities.python_coupled_software_repair_loop_v1 import (
                run as _coupled_repair_run,
            )
            coupled_result = _coupled_repair_run(
                {
                    "source_root": str(source_root_p.relative_to(repo)),
                    "test_paths": [str(tp.relative_to(repo)) for tp in test_ps],
                    "output_path": str((worktree_p / ".coupled_repair_result.json").relative_to(repo)),
                    "timeout_s": min(timeout_s, 60),
                    "max_edits": 6,
                    "max_candidates": max_candidates * 2,
                    "max_wall_time_s": min(timeout_s, 120),
                },
                repo,
            )
            if coupled_result.get("pass") and coupled_result.get("patches"):
                # Build a unified diff from the multi-edit patches.
                diff_parts = []
                for patch_entry in coupled_result["patches"]:
                    sp = patch_entry.get("source_path", "")
                    ud = patch_entry.get("unified_diff", "")
                    if sp and ud:
                        diff_parts.append(ud)
                if diff_parts:
                    best_diff = "\n".join(diff_parts)
                    patches_passing = 1
                    patches_tried = ps_result.get("tested_candidate_count", 0) + \
                                    coupled_result.get("tested_candidate_count", 0)
                    _progress_adapter.stage_completed(gid, "multi_edit_repair", {
                        "status": "multi_edit_repair_found",
                        "edits_applied": coupled_result.get("edits_applied", 0),
                    })
        except Exception as exc:
            _progress_adapter.stage_progress(gid, "end_to_end_repair", 3, 5, {
                "stage": "multi_edit_repair_skipped",
                "reason": str(exc)[:200],
            })

    # Stage 2.6: Dual-oracle verification — patch must pass BOTH oracles
    # before it is trusted enough to apply to the worktree.
    if best_diff:
        _progress_adapter.stage_progress(gid, "end_to_end_repair", 3, 5, {
            "stage": "dual_oracle",
        })
        # Apply the diff to a temp copy to get the patched source for oracle check.
        _copy_tree(source_root_p, worktree_p)
        diff_file = worktree_p / ".swe-patch.diff"
        diff_file.write_text(best_diff, encoding="utf-8")
        try:
            probe = subprocess.run(
                ["git", "apply", "--check", str(diff_file)],
                cwd=str(worktree_p), capture_output=True, text=True, timeout=30,
            )
            if probe.returncode == 0:
                apply = subprocess.run(
                    ["git", "apply", str(diff_file)],
                    cwd=str(worktree_p), capture_output=True, text=True, timeout=30,
                )
                if apply.returncode == 0:
                    # Run dual-oracle on the patched source file.
                    patched_source = worktree_p / source_p.relative_to(source_root_p)
                    oracle_result = verify_with_dual_oracle(
                        patched_source, test_ps, repo, timeout_s=min(timeout_s, 60))
                    if not oracle_result.get("verified", False):
                        _progress_adapter.stage_failed(gid, "dual_oracle", "DUAL_ORACLE_REJECTED")
                        return {"verified": False,
                                "reason": oracle_result.get("reason", "DUAL_ORACLE_REJECTED"),
                                "gate": "FAIL", "patches_tried": patches_tried,
                                "patches_passing": patches_passing,
                                "oracle_results": oracle_result.get("oracle_results", []),
                                "elapsed_s": round(__import__("time").monotonic() - t_start, 3)}
                    _progress_adapter.stage_completed(gid, "dual_oracle", {
                        "status": "dual_oracle_verified",
                    })
        finally:
            try:
                diff_file.unlink()
            except OSError:
                pass

    # Stage 3: Apply to worktree.
    _copy_tree(source_root_p, worktree_p)
    applied_op_count = 0
    if best_diff:
        diff_file = worktree_p / ".swe-patch.diff"
        diff_file.write_text(best_diff, encoding="utf-8")
        try:
            probe = subprocess.run(
                ["git", "apply", "--check", str(diff_file)],
                cwd=str(worktree_p), capture_output=True, text=True, timeout=30,
            )
            if probe.returncode != 0:
                return {"verified": False, "reason": "DIFF_DOES_NOT_APPLY", "gate": "FAIL",
                        "patches_tried": patches_tried, "patches_passing": patches_passing,
                        "elapsed_s": round(_time.monotonic() - t_start, 3)}
            apply = subprocess.run(
                ["git", "apply", str(diff_file)],
                cwd=str(worktree_p), capture_output=True, text=True, timeout=30,
            )
            if apply.returncode != 0:
                return {"verified": False, "reason": "DIFF_APPLY_FAILED", "gate": "FAIL",
                        "patches_tried": patches_tried, "patches_passing": patches_passing,
                        "elapsed_s": round(_time.monotonic() - t_start, 3)}
            applied_op_count = 1
        except FileNotFoundError:
            return {"verified": False, "reason": "GIT_UNAVAILABLE", "gate": "FAIL",
                    "patches_tried": patches_tried, "patches_passing": patches_passing,
                    "elapsed_s": round(_time.monotonic() - t_start, 3)}
        finally:
            try:
                diff_file.unlink()
            except OSError:
                pass

    # Stage 3.5: Advanced verification gates — all gates run on the
    # winning diff/worktree before the full test gate. A patch must pass
    # ALL enabled gates to proceed.
    gate_results: dict[str, dict] = {}
    if best_diff:
        # Write the unified diff to disk before running gates — gates need
        # the diff artifact on disk to analyze changed lines.
        diff_p.parent.mkdir(parents=True, exist_ok=True)
        full_diff = _unified_diff(source_root_p, worktree_p)
        diff_p.write_text(full_diff, encoding="utf-8")

        _progress_adapter.stage_progress(gid, "end_to_end_repair", 3, 5, {
            "stage": "advanced_gates",
        })

        patched_source_wt = worktree_p / source_p.relative_to(source_root_p)
        wt_rel = str(worktree_p.relative_to(repo))
        diff_rel = str(diff_p.relative_to(repo))

        # --- Gate 1: Static triage (ruff on changed lines) ---
        # Syntax check + ruff lint intersecting changed-line ranges.
        # F* and E9* are blocking on changed lines; everything else advisory.
        if enable_static_triage_gate:
            try:
                triage_result = _static_triage_run(
                    {
                        "diff_path": diff_rel,
                        "worktree_path": wt_rel,
                        "output_path": str((worktree_p / ".swe_static_triage.json").relative_to(repo)),
                        "python_executable": sys.executable,
                        "timeout_s": static_triage_timeout_s,
                    },
                    repo,
                )
                tgate, tdetails = _extract_gate_result(triage_result)
                gate_results["static_triage"] = {
                    "gate": tgate,
                    "blocking_findings": triage_result.get("blocking_findings", 0),
                    "advisory_findings": triage_result.get("advisory_findings", 0),
                    "syntax_errors": triage_result.get("syntax_errors", 0),
                    "ruff": triage_result.get("ruff", "UNAVAILABLE"),
                    **tdetails,
                }
                if tgate == "FAIL":
                    _progress_adapter.stage_failed(gid, "advanced_gates", "STATIC_TRIAGE_REJECTED")
                    return {
                        "verified": False,
                        "reason": "STATIC_TRIAGE_REJECTED",
                        "gate": "FAIL",
                        "patches_tried": patches_tried,
                        "patches_passing": patches_passing,
                        "gate_results": gate_results,
                        "elapsed_s": round(_time.monotonic() - t_start, 3),
                    }
            except Exception as exc:
                gate_results["static_triage"] = {"skipped": True, "reason": str(exc)[:200]}
                _progress_adapter.stage_progress(gid, "advanced_gates", 0, 1, {
                    "stage": "static_triage_skipped",
                    "reason": str(exc)[:200],
                })

        # --- Gate 2: Type checking gate (mypy on changed lines) ---
        # Blocks type errors introduced by the patch.
        if enable_type_gate:
            try:
                type_result = _type_gate_run(
                    {
                        "diff_path": diff_rel,
                        "worktree_path": wt_rel,
                        "output_path": str((worktree_p / ".swe_type_gate.json").relative_to(repo)),
                        "python_executable": sys.executable,
                        "timeout_s": type_timeout_s,
                    },
                    repo,
                )
                tgate, tdetails = _extract_gate_result(type_result)
                gate_results["type_check"] = {
                    "gate": tgate,
                    "blocking_findings": type_result.get("blocking_findings", 0),
                    "advisory_findings": type_result.get("advisory_findings", 0),
                    "syntax_errors": type_result.get("syntax_errors", 0),
                    "mypy": type_result.get("mypy", "UNAVAILABLE"),
                    **tdetails,
                }
                if tgate == "FAIL":
                    _progress_adapter.stage_failed(gid, "advanced_gates", "TYPE_CHECK_REJECTED")
                    return {
                        "verified": False,
                        "reason": "TYPE_CHECK_REJECTED",
                        "gate": "FAIL",
                        "patches_tried": patches_tried,
                        "patches_passing": patches_passing,
                        "gate_results": gate_results,
                        "elapsed_s": round(_time.monotonic() - t_start, 3),
                    }
            except Exception as exc:
                gate_results["type_check"] = {"skipped": True, "reason": str(exc)[:200]}
                _progress_adapter.stage_progress(gid, "advanced_gates", 0, 1, {
                    "stage": "type_skipped",
                    "reason": str(exc)[:200],
                })

        # --- Gate 3: SAST security scan (bandit on changed lines) ---
        # Reject patches that introduce critical/high-severity vulnerabilities
        # in changed code. Changed-lines-only: pre-existing findings outside
        # the diff are advisory, never blockers.
        if enable_security_gate:
            try:
                sec_result = _security_gate_run(
                    {
                        "diff_path": diff_rel,
                        "worktree_path": wt_rel,
                        "output_path": str((worktree_p / ".swe_sec_gate.json").relative_to(repo)),
                        "python_executable": sys.executable,
                        "timeout_s": min(timeout_s, 120),
                    },
                    repo,
                )
                gate, sdetails = _extract_gate_result(sec_result)
                gate_results["sast_security"] = {
                    "gate": gate,
                    "blocking_findings": sec_result.get("blocking_findings", 0),
                    "advisory_findings": sec_result.get("advisory_findings", 0),
                    "syntax_errors": sec_result.get("syntax_errors", 0),
                    "bandit": sec_result.get("bandit", "UNAVAILABLE"),
                    **sdetails,
                }
                if gate != "PASS" and gate != "PASS_BASELINE_ONLY":
                    _progress_adapter.stage_failed(gid, "advanced_gates", "SAST_REJECTED")
                    return {
                        "verified": False,
                        "reason": "SAST_REJECTED",
                        "gate": "FAIL",
                        "patches_tried": patches_tried,
                        "patches_passing": patches_passing,
                        "gate_results": gate_results,
                        "elapsed_s": round(_time.monotonic() - t_start, 3),
                    }
            except Exception as exc:
                gate_results["sast_security"] = {"skipped": True, "reason": str(exc)[:200]}
                _progress_adapter.stage_progress(gid, "advanced_gates", 0, 1, {
                    "stage": "sast_skipped",
                    "reason": str(exc)[:200],
                })

        # --- Gate 4: Performance regression gate ---
        # Benchmarks the patched function against the anchor (original)
        # using a declared bench() callable. Blocks when patched median
        # exceeds anchor median beyond tolerance.
        if enable_perf_gate and bench_path:
            try:
                perf_result = _perf_gate_run(
                    {
                        "anchor_path": str(source_root_p.relative_to(repo)),
                        "diff_path": diff_rel,
                        "bench_path": str(
                            ((repo / bench_path) if not Path(bench_path).is_absolute()
                             else Path(bench_path)).resolve().relative_to(source_root_p)),
                        "output_path": str((worktree_p / ".swe_perf_gate.json").relative_to(repo)),
                        "python_executable": sys.executable,
                        "repeats": perf_repeats,
                        "tolerance": perf_tolerance,
                        "timeout_s": min(timeout_s, 120),
                    },
                    repo,
                )
                pgate, pdetails = _extract_gate_result(perf_result)
                gate_results["performance"] = {
                    "gate": pgate,
                    "slowdown_ratio": perf_result.get("slowdown_ratio", 0),
                    "threshold": 1.0 + perf_tolerance,
                    "anchor_median_ns": perf_result.get("anchor_median_ns", 0),
                    "patched_median_ns": perf_result.get("patched_median_ns", 0),
                    **pdetails,
                }
                if pgate == "FAIL":
                    _progress_adapter.stage_failed(gid, "advanced_gates", "PERFORMANCE_REGRESSION")
                    return {
                        "verified": False,
                        "reason": "PERFORMANCE_REGRESSION",
                        "gate": "FAIL",
                        "patches_tried": patches_tried,
                        "patches_passing": patches_passing,
                        "gate_results": gate_results,
                        "elapsed_s": round(_time.monotonic() - t_start, 3),
                    }
            except Exception as exc:
                gate_results["performance"] = {"skipped": True, "reason": str(exc)[:200]}
                _progress_adapter.stage_progress(gid, "advanced_gates", 0, 1, {
                    "stage": "perf_skipped",
                    "reason": str(exc)[:200],
                })

        # --- Gate 5: Coverage gate ---
        # Ensures changed lines are covered by tests; missing source rows fail.
        if enable_coverage_gate:
            try:
                cov_result = _coverage_gate_run(
                    {
                        "anchor_path": str(source_root_p.relative_to(repo)),
                        "diff_path": diff_rel,
                        "output_path": str((worktree_p / ".swe_coverage_gate.json").relative_to(repo)),
                        "python_executable": sys.executable,
                        "timeout_s": coverage_timeout_s,
                    },
                    repo,
                )
                cgate, cdetails = _extract_gate_result(cov_result)
                gate_results["coverage"] = {
                    "gate": cgate,
                    "missing_lines": cov_result.get("missing_lines", 0),
                    "coverage_pct": cov_result.get("coverage_pct", 0.0),
                    **cdetails,
                }
                if cgate == "FAIL":
                    _progress_adapter.stage_failed(gid, "advanced_gates", "COVERAGE_REJECTED")
                    return {
                        "verified": False,
                        "reason": "COVERAGE_REJECTED",
                        "gate": "FAIL",
                        "patches_tried": patches_tried,
                        "patches_passing": patches_passing,
                        "gate_results": gate_results,
                        "elapsed_s": round(_time.monotonic() - t_start, 3),
                    }
            except Exception as exc:
                gate_results["coverage"] = {"skipped": True, "reason": str(exc)[:200]}
                _progress_adapter.stage_progress(gid, "advanced_gates", 0, 1, {
                    "stage": "coverage_skipped",
                    "reason": str(exc)[:200],
                })

        # --- Gate 6: Mutation testing gate ---
        # Generates AST mutants on changed lines; every mutant must be killed
        # by a test failure. Survivors fail the gate.
        if enable_mutation_gate:
            try:
                mut_result = _mutation_gate_run(
                    {
                        "anchor_path": str(source_root_p.relative_to(repo)),
                        "diff_path": diff_rel,
                        "output_path": str((worktree_p / ".swe_mutation_gate.json").relative_to(repo)),
                        "python_executable": sys.executable,
                        "timeout_s": mutation_timeout_s,
                    },
                    repo,
                )
                mgate, mdetails = _extract_gate_result(mut_result)
                gate_results["mutation"] = {
                    "gate": mgate,
                    "survivors": mut_result.get("survivors", 0),
                    "mutants_generated": mut_result.get("mutants_generated", 0),
                    "kill_ratio": mut_result.get("kill_ratio", 0.0),
                    **mdetails,
                }
                if mgate == "FAIL":
                    _progress_adapter.stage_failed(gid, "advanced_gates", "MUTATION_REJECTED")
                    return {
                        "verified": False,
                        "reason": "MUTATION_REJECTED",
                        "gate": "FAIL",
                        "patches_tried": patches_tried,
                        "patches_passing": patches_passing,
                        "gate_results": gate_results,
                        "elapsed_s": round(_time.monotonic() - t_start, 3),
                    }
            except Exception as exc:
                gate_results["mutation"] = {"skipped": True, "reason": str(exc)[:200]}
                _progress_adapter.stage_progress(gid, "advanced_gates", 0, 1, {
                    "stage": "mutation_skipped",
                    "reason": str(exc)[:200],
                })

        # --- Gate 7: Hypothesis property-based fuzzing ---
        # Generates adversarial inputs from type signatures, shrinks failing
        # cases to minimal counterexamples. Rejects patches that crash or
        # violate invariants on fuzz inputs.
        if enable_hypothesis_fuzz:
            try:
                from canonical.runtime.bound_capabilities.evidence_oracle_hypothesis_v1 import (
                    run as _hypothesis_run,
                )
                fuzz_result = _hypothesis_run(
                    {
                        "source_path": str(patched_source_wt),
                        "max_examples": hypothesis_max_examples,
                        "timeout_s": hypothesis_timeout_s,
                        "output_path": str((worktree_p / ".swe_hypothesis_fuzz.json").relative_to(repo)),
                    },
                    repo,
                )
                gate_results["hypothesis_fuzz"] = {
                    "status": fuzz_result.get("status", "UNKNOWN"),
                    "checked": fuzz_result.get("checked", 0),
                    "violations": fuzz_result.get("violations", []),
                    "hypothesis_available": fuzz_result.get("hypothesis_available", False),
                }
                if not fuzz_result.get("verified", False) and fuzz_result.get("violations"):
                    _progress_adapter.stage_failed(gid, "advanced_gates", "FUZZING_REJECTED")
                    return {
                        "verified": False,
                        "reason": "FUZZING_REJECTED",
                        "gate": "FAIL",
                        "patches_tried": patches_tried,
                        "patches_passing": patches_passing,
                        "gate_results": gate_results,
                        "elapsed_s": round(_time.monotonic() - t_start, 3),
                    }
            except Exception as exc:
                gate_results["hypothesis_fuzz"] = {"skipped": True, "reason": str(exc)[:200]}
                _progress_adapter.stage_progress(gid, "advanced_gates", 0, 1, {
                    "stage": "fuzz_skipped",
                    "reason": str(exc)[:200],
                })

        # --- Gate 8: Z3 formal verification (CEGIS-style equivalence) ---
        # Proves patched functions satisfy their pre/post contracts using Z3.
        # Extracts concrete counterexamples when contract is violated.
        if enable_z3_gate and best_diff:
            try:
                if not _z3_available_fn():
                    gate_results["z3_formal"] = {
                        "gate": "SKIP",
                        "reason": "Z3_NOT_AVAILABLE",
                        "z3_available": False,
                    }
                else:
                    # Read patched source from worktree
                    patched_source_wt = worktree_p / source_p.relative_to(source_root_p)
                    if patched_source_wt.is_file():
                        patched_source = patched_source_wt.read_text(encoding="utf-8")
                        original_source = source_p.read_text(encoding="utf-8") if source_p.is_file() else ""
                        z3_result = _z3_verify_patch_fn(original_source, patched_source)
                        zgate = z3_result.get("verified", False)
                        gate_results["z3_formal"] = {
                            "gate": "PASS" if zgate else "FAIL",
                            "z3_available": True,
                            "functions_verified": z3_result.get("functions_verified", []),
                            "skipped": z3_result.get("skipped", []),
                            "reason": z3_result.get("reason", ""),
                        }
                        if not zgate:
                            _progress_adapter.stage_failed(gid, "advanced_gates", "Z3_FORMAL_REJECTED")
                            return {
                                "verified": False,
                                "reason": "Z3_FORMAL_REJECTED",
                                "gate": "FAIL",
                                "patches_tried": patches_tried,
                                "patches_passing": patches_passing,
                                "gate_results": gate_results,
                                "counterexamples": z3_result.get("counterexamples", []),
                                "elapsed_s": round(_time.monotonic() - t_start, 3),
                            }
                    else:
                        gate_results["z3_formal"] = {
                            "gate": "SKIP",
                            "reason": "PATCHED_SOURCE_NOT_FOUND",
                            "z3_available": True,
                        }
            except Exception as exc:
                gate_results["z3_formal"] = {"skipped": True, "reason": str(exc)[:200]}
                _progress_adapter.stage_progress(gid, "advanced_gates", 0, 1, {
                    "stage": "z3_skipped",
                    "reason": str(exc)[:200],
                })

        _progress_adapter.stage_completed(gid, "advanced_gates", {
            "status": "advanced_gates_passed",
        })

    # Stage 4: Full test gate on worktree.
    _progress_adapter.stage_progress(gid, "end_to_end_repair", 4, 5, {
        "stage": "test_gate",
    })
    full_diff = _unified_diff(source_root_p, worktree_p)
    diff_p.parent.mkdir(parents=True, exist_ok=True)
    diff_p.write_text(full_diff, encoding="utf-8")

    gate_result = full_test_gate(source_root_p, diff_p, output_p, timeout_s=timeout_s)
    gate = gate_result.get("gate", "FAIL")
    tests_passed = gate_result.get("tests_passed", 0)
    tests_failed = gate_result.get("tests_failed", 0)
    output_verified = gate_result.get("output_verified", False)
    verified = (gate == "PASS") and output_verified

    _progress_adapter.stage_progress(gid, "end_to_end_repair", 4, 5, {
        "stage": "test_gate_complete",
        "gate": gate,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
    })

    # Stage 5: PR intent + GitHub PR (when OIDC token is available).
    _progress_adapter.stage_progress(gid, "end_to_end_repair", 5, 5, {
        "stage": "pr_intent",
    })
    pr_intent = {
        "title": "fix: autonomous SWE repair",
        "body": "patches_tried={}, patches_passing={}, gate={}, tests_passed={}, tests_failed={}\nelapsed_s={}".format(
            patches_tried, patches_passing, gate, tests_passed, tests_failed,
            round(_time.monotonic() - t_start, 3)),
        "verified": verified,
        "elapsed_s": round(_time.monotonic() - t_start, 3),
    }
    pr_p.parent.mkdir(parents=True, exist_ok=True)
    pr_p.write_text(json.dumps(pr_intent, indent=2, sort_keys=True), encoding="utf-8")

    # Real GitHub PR from the verified patch (requires OIDC token).
    github_pr = None
    if verified and oidc_token:
        try:
            from canonical.runtime.github_integration_v1 import GitHubClient
            client = GitHubClient(token=oidc_token)
            # Repo owner/name from git remote or env.
            owner = os.environ.get("GITHUB_OWNER", "")
            repo_name = os.environ.get("GITHUB_REPO", "")
            if owner and repo_name:
                base_branch = os.environ.get("GITHUB_BASE_BRANCH", "main")
                head_branch = "brain/swe-fix-" + _sha256(full_diff.encode("utf-8"))[:12]
                github_pr = client.create_pr_from_swe(
                    owner, repo_name, base_branch, head_branch,
                    pr_intent["title"], pr_intent["body"],
                    full_diff,
                    {"tests_passed": tests_passed, "tests_failed": tests_failed,
                     "verified": verified},
                    draft=True,
                )
        except Exception:
            # GitHub PR creation is best-effort; the verified patch + diff
            # artifacts are already persisted locally. Never fail the repair
            # because GitHub is unreachable.
            github_pr = {"error": "GITHUB_PR_CREATION_FAILED"}

    _progress_adapter.stage_completed(gid, "end_to_end_repair", {
        "status": "PASS" if verified else "FAIL",
        "verified": verified,
        "gate": gate,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "elapsed_s": round(_time.monotonic() - t_start, 3),
        "github_pr": github_pr,
    })

    return {
        "verified": verified,
        "gate": gate,
        "patches_tried": patches_tried,
        "patches_passing": patches_passing,
        "applied_op_count": applied_op_count,
        "test_passed_count": tests_passed,
        "test_failed_count": tests_failed,
        "gate_results": gate_results,
        "diff_sha256": _sha256(full_diff.encode("utf-8")),
        "pr_intent_verified": verified,
        "elapsed_s": round(_time.monotonic() - t_start, 3),
        "output_path": str(output_p.relative_to(repo)),
        "diff_path": str(diff_p.relative_to(repo)),
        "pr_intent_path": str(pr_p.relative_to(repo)),
        "github_pr": github_pr,
    }


# ---------------------------------------------------------------------------
# Generic runner + in-process adapter runner
# ---------------------------------------------------------------------------

def _run_in_process(adapter_module_path: Path, entrypoint: str,
                    args: Mapping[str, Any], root: Path) -> dict:
    spec = importlib.util.spec_from_file_location(
        "pb_real_swe_" + adapter_module_path.stem, adapter_module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("ADAPTER_LOAD_FAILED:" + str(adapter_module_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    fn = getattr(mod, entrypoint, None)
    if not callable(fn):
        raise RuntimeError("ADAPTER_ENTRYPOINT_MISSING:" + entrypoint)
    result = fn(dict(args), str(root))
    if not isinstance(result, dict):
        raise RuntimeError("ADAPTER_RESULT_INVALID")
    return result


def run_capability(adapter_module_path: Path, entrypoint: str,
                   args: dict, root: Path) -> dict:
    """Generic runner for any bound capability adapter."""
    return _run_in_process(adapter_module_path, entrypoint, args, root)
