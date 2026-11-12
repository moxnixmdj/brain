"""Aggregate-only one-shot ARC-AGI-2 public evaluation audit.

The pre-exposure contract forbids task-level emission. This evaluator therefore
reads/scorers tasks internally but emits only aggregate counts, rates, resource
totals, and a corpus content hash.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from canonical.runtime.arc_visual_program_invention_adapter_v1 import score_public_task

SCHEMA = "PROJECT_BRAIN_ARC_AGI2_PROGRAM_INVENTOR_AGGREGATE_AUDIT_V1"


def _corpus_sha256(files: list[Path]) -> str:
    h = hashlib.sha256()
    for path in files:
        raw = path.read_bytes()
        h.update(path.name.encode("utf-8"))
        h.update(b"\0")
        h.update(hashlib.sha256(raw).digest())
    return h.hexdigest()


def _score_one(args: tuple[str, int, int, int, int, int]) -> dict[str, Any]:
    path_s, max_depth, attempts, max_states, max_equiv, max_cells = args
    path = Path(path_s)
    task = json.loads(path.read_text(encoding="utf-8"))
    result = score_public_task(
        task,
        max_depth=max_depth,
        attempts=attempts,
        max_semantic_states_per_depth=max_states,
        max_equivalent_programs_per_semantics=max_equiv,
        max_grid_cells=max_cells,
    )
    outer = result.get("program_invention", {})
    invention = outer.get("invention", {}) if isinstance(outer, dict) else {}
    return {
        "status": str(result.get("status")),
        "solved": result.get("exact_task_solved") is True,
        "invention_status": str(invention.get("status")),
        "generated_program_count": int(invention.get("generated_program_count", 0) or 0),
        "semantic_states_by_depth": dict(invention.get("semantic_states_by_depth", {}) or {}),
    }


def run(
    data_dir: Path,
    *,
    max_depth: int = 3,
    attempts: int = 2,
    max_semantic_states_per_depth: int = 4000,
    max_equivalent_programs_per_semantics: int = 4,
    max_grid_cells: int = 10000,
    workers: int = 8,
) -> dict[str, Any]:
    files = sorted(data_dir.glob("*.json"))
    if not files:
        raise SystemExit("NO_TASK_FILES")
    if isinstance(workers, bool) or not isinstance(workers, int) or workers < 1:
        raise SystemExit("WORKERS_INVALID")

    status_counts: Counter[str] = Counter()
    invention_status_counts: Counter[str] = Counter()
    solved = 0
    scored = 0
    exact_training_program = 0
    generated_programs = 0
    max_generated = 0
    state_totals: Counter[str] = Counter()
    start = time.perf_counter()

    args = [
        (str(path), max_depth, attempts, max_semantic_states_per_depth, max_equivalent_programs_per_semantics, max_grid_cells)
        for path in files
    ]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for row in pool.map(_score_one, args):
            scored += 1
            status_counts[row["status"]] += 1
            solved += int(row["solved"])
            istatus = row["invention_status"]
            invention_status_counts[istatus] += 1
            exact_training_program += int(istatus == "EXACT_PROGRAMS_FOUND")
            n = row["generated_program_count"]
            generated_programs += n
            max_generated = max(max_generated, n)
            for depth, count in row["semantic_states_by_depth"].items():
                state_totals[str(depth)] += int(count)

    elapsed = time.perf_counter() - start
    return {
        "schema": SCHEMA,
        "status": "AGGREGATE_AUDIT_COMPLETE__ZERO_TASK_LEVEL_DISCLOSURE",
        "task_files": len(files),
        "scored_tasks": scored,
        "exact_tasks_solved": solved,
        "exact_task_solve_rate": solved / scored if scored else 0.0,
        "tasks_with_exact_training_program": exact_training_program,
        "status_counts": dict(sorted(status_counts.items())),
        "invention_status_counts": dict(sorted(invention_status_counts.items())),
        "aggregate_generated_program_count": generated_programs,
        "max_generated_program_count_single_task": max_generated,
        "aggregate_semantic_states_by_depth": dict(sorted(state_totals.items())),
        "wall_clock_seconds": elapsed,
        "workers": workers,
        "corpus_sha256": _corpus_sha256(files),
        "search_config": {
            "max_depth": max_depth,
            "attempts": attempts,
            "max_semantic_states_per_depth": max_semantic_states_per_depth,
            "max_equivalent_programs_per_semantics": max_equivalent_programs_per_semantics,
            "max_grid_cells": max_grid_cells,
        },
        "task_ids_emitted": False,
        "task_grids_emitted": False,
        "task_programs_emitted": False,
        "per_task_results_emitted": False,
        "external_learned_capability_calls": 0,
        "donor_runtime_required": False,
        "private_score_claimed": False,
        "promotion_authority": False,
        "terminal_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    result = run(args.data_dir)
    body = json.dumps(result, indent=2, sort_keys=True)
    print(body)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(body + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
