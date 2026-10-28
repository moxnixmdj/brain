#!/usr/bin/env python3
# PROJECT_BRAIN
"""
software.hardcore.kernel.orchestrate.v1 — real end-to-end software engineering pipeline.

Autonomous SWE repair loop delegating to the shared high-performance engine
(real_swe_execution_v1.end_to_end_repair):

  1. Fault localization — dynamic spectrum + traceback ranking (orders candidates).
  2. Test-guided patch search — AST mutations + literal substitutions mined from
     failing tests, evaluated **in parallel** with a content-addressable disk
     cache so identical source is never tested twice ("insanely fast").
  3. Applies the winning patch to a byte-copy worktree (never mutates source).
  4. Runs the full configured pytest suite on the worktree — gate PASS requires
     at least one passing test, zero failures/errors, unchanged diff.
  5. Emits a unified diff + PR intent + receipt.

Returns ``verified: True`` only when the full test gate passes. Fail-closed:
any environmental break, refused op, or failing gate aborts before any write.

All paths confined to repo by _safe_path.

Inputs (kwargs; every path confined to repo by _safe_path):
  task_path       JSON: {"issue_id","title","body","failing_tests":[...]}
  source_root     tree to change (relative to repo, read-only)
  worktree_path   (re)created byte-copy of source_root; patched there
  output_path     final summary JSON
  diff_path       unified diff artifact (source_root -> worktree bytes)
  pr_intent_path  PR title/body/checklist JSON artifact
  source_path     single source file to patch (relative to repo)
  test_paths      list of test file paths (relative to repo)
  test_command    pytest command string (default: "python3 -m pytest") — kept
                  for interface compatibility; real pytest is always used.
  timeout_s       per-stage wall-clock cap (default 300)
  max_candidates  max patch candidates to try (default 50)
  max_workers     parallel candidate workers (default: min(cpu, 8))

result_fields: adapter, capability_id, task_id, patches_tried,
patches_passing, applied_op_count, test_selected_count, test_passed_count,
test_failed_count, diff_sha256, pr_intent_verified, verified, gate,
elapsed_s, output_path, diff_path, pr_intent_path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_HARDCORE_SWE_END_TO_END_V1"
CAPABILITY_ID = "software.hardcore.kernel.orchestrate.v1"
PROVIDES = ["software.hardcore.kernel.verified"]
REQUIRES: list[str] = []

REPO = Path(__file__).resolve().parents[3]

_SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules"}


def _fail(reason: str) -> dict:
    return {
        "error": True,
        "capability": CAPABILITY_ID,
        "reason": reason,
    }


def _sha256(b: bytes) -> str:
    import hashlib
    return hashlib.sha256(b).hexdigest()


def _safe_path(repo: Path, rel: str, must_exist: bool = False) -> Path | dict:
    if not rel or not isinstance(rel, str):
        return _fail("MISSING_OR_INVALID_PATH_ARGUMENT")
    p = (repo / rel).resolve()
    if p != repo and repo not in p.parents:
        return _fail("PATH_ESCAPE:" + rel)
    if must_exist and not p.exists():
        return _fail("PATH_MISSING:" + rel)
    return p


def run(args: dict[str, Any], root: str | Path) -> dict[str, Any]:
    repo = Path(root).resolve()
    task_path = _safe_path(repo, args.get("task_path"), must_exist=True)
    if isinstance(task_path, dict):
        return task_path
    source_root = _safe_path(repo, args.get("source_root"), must_exist=True)
    if isinstance(source_root, dict):
        return source_root
    worktree_path = _safe_path(repo, args.get("worktree_path"))
    if isinstance(worktree_path, dict):
        return worktree_path
    output_path = _safe_path(repo, args.get("output_path"))
    if isinstance(output_path, dict):
        return output_path
    diff_path = _safe_path(repo, args.get("diff_path"))
    if isinstance(diff_path, dict):
        return diff_path
    pr_intent_path = _safe_path(repo, args.get("pr_intent_path"))
    if isinstance(pr_intent_path, dict):
        return pr_intent_path
    timeout_s = int(args.get("timeout_s", 300))
    max_candidates = int(args.get("max_candidates", 50))
    max_workers = args.get("max_workers")
    max_workers = int(max_workers) if max_workers is not None else None

    task_raw = task_path.read_text(encoding="utf-8")
    task = json.loads(task_raw)
    task_id = str(task.get("issue_id") or args.get("task_id") or "swe-task")

    source_path = Path(args.get("source_path") or "")
    if not source_path.is_absolute():
        source_path = repo / source_path
    source_path = source_path.resolve()

    test_paths = args.get("test_paths") or []
    test_paths = [repo / tp if not Path(tp).is_absolute() else Path(tp) for tp in test_paths]
    test_paths = [tp.resolve() for tp in test_paths]

    # Delegate to the shared high-performance engine (parallel + cached).
    from canonical.runtime.bound_capabilities.real_swe_execution_v1 import end_to_end_repair

    result = end_to_end_repair(
        source_root=str(source_root.relative_to(repo)),
        worktree_path=str(worktree_path.relative_to(repo)),
        source_path=str(source_path.relative_to(repo)),
        test_paths=[str(tp.relative_to(repo)) for tp in test_paths],
        output_path=str(output_path.relative_to(repo)),
        diff_path=str(diff_path.relative_to(repo)),
        pr_intent_path=str(pr_intent_path.relative_to(repo)),
        timeout_s=timeout_s,
        max_candidates=max_candidates,
        max_workers=max_workers,
    )

    gate = result.get("gate", "FAIL")
    verified = bool(result.get("verified", False))

    # Enrich result with orchestrator fields.
    full_diff_bytes = b""
    try:
        diff_file = repo / result["diff_path"]
        full_diff_bytes = diff_file.read_bytes()
    except (OSError, KeyError):
        pass
    if isinstance(full_diff_bytes, str):
        full_diff_bytes = full_diff_bytes.encode("utf-8")

    enriched = {
        "adapter": "hardcore_software_engineering_orchestrator_v1",
        "capability_id": CAPABILITY_ID,
        "task_id": task_id,
        "patches_tried": result.get("patches_tried", 0),
        "patches_passing": result.get("patches_passing", 0),
        "applied_op_count": result.get("applied_op_count", 0),
        "test_selected_count": result.get("test_passed_count", 0) + result.get("test_failed_count", 0),
        "test_passed_count": result.get("test_passed_count", 0),
        "test_failed_count": result.get("test_failed_count", 0),
        "diff_sha256": result.get("diff_sha256", _sha256(full_diff_bytes)),
        "pr_intent_verified": bool(result.get("pr_intent_verified", False)),
        "verified": verified,
        "gate": gate,
        "elapsed_s": result.get("elapsed_s", 0),
        "output_path": result.get("output_path", ""),
        "diff_path": result.get("diff_path", ""),
        "pr_intent_path": result.get("pr_intent_path", ""),
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
    return enriched
