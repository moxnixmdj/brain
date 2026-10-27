"""Aggregate-only ARC-AGI-2 audit for conservative combined solver V1."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from canonical.runtime.arc_conservative_combined_solver_v1 import score_public_task

SCHEMA = "PROJECT_BRAIN_ARC_AGI2_COMBINED_SOLVER_AGGREGATE_AUDIT_V1"


def _corpus_sha256(files: list[Path]) -> str:
    h = hashlib.sha256()
    for path in files:
        raw = path.read_bytes()
        h.update(path.name.encode("utf-8"))
        h.update(b"\0")
        h.update(hashlib.sha256(raw).digest())
    return h.hexdigest()


def _exact_from_attempts(attempts: list[dict[str, Any]], expected: list[Any]) -> bool:
    return bool(expected) and all(
        any(
            len(candidate.get("predictions", [])) > i
            and candidate["predictions"][i] == expected[i]
            for candidate in attempts
        )
        for i in range(len(expected))
    )


def _score_one(path_s: str) -> dict[str, Any]:
    path = Path(path_s)
    task = json.loads(path.read_text(encoding="utf-8"))
    result = score_public_task(
        task,
        attempts=2,
        max_depth=3,
        max_semantic_states_per_depth=4000,
        max_equivalent_programs_per_semantics=4,
        max_grid_cells=10000,
    )
    expected = [row.get("output") for row in task.get("test", [])]
    attempts = result.get("attempts", [])
    direct_attempts = [row for row in attempts if row.get("source") == "ARC_V16_DIRECT"]
    exact = result.get("exact_task_solved") is True
    direct_exact = _exact_from_attempts(direct_attempts, expected)
    return {
        "exact": exact,
        "direct_exact": direct_exact,
        "inventor_increment": exact and not direct_exact,
        "inventor_used": result.get("inventor_used") is True,
        "inventor_selected": any(row.get("source") == "PROGRAM_INVENTOR" for row in attempts),
        "direct_bundle_count": min(int(result.get("direct_unique_bundle_count", 0)), 2),
        "status": str(result.get("status")),
    }


def run(data_dir: Path, *, workers: int = 8) -> dict[str, Any]:
    files = sorted(data_dir.glob("*.json"))
    if not files:
        raise SystemExit("NO_TASK_FILES")
    if isinstance(workers, bool) or not isinstance(workers, int) or workers < 1:
        raise SystemExit("WORKERS_INVALID")

    solved = 0
    direct_only_solved = 0
    inventor_increment = 0
    inventor_used = 0
    inventor_selected = 0
    direct_bundle_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    start = time.perf_counter()

    with ProcessPoolExecutor(max_workers=workers) as pool:
        for row in pool.map(_score_one, [str(path) for path in files]):
            solved += int(row["exact"])
            direct_only_solved += int(row["direct_exact"])
            inventor_increment += int(row["inventor_increment"])
            inventor_used += int(row["inventor_used"])
            inventor_selected += int(row["inventor_selected"])
            direct_bundle_counts[str(row["direct_bundle_count"])] += 1
            status_counts[row["status"]] += 1

    elapsed = time.perf_counter() - start
    total = len(files)
    return {
        "schema": SCHEMA,
        "status": "AGGREGATE_AUDIT_COMPLETE__ZERO_TASK_LEVEL_DISCLOSURE",
        "task_files": total,
        "exact_tasks_solved_combined": solved,
        "exact_task_solve_rate_combined": solved / total,
        "exact_tasks_solved_by_selected_direct_attempts": direct_only_solved,
        "exact_task_solve_rate_selected_direct_attempts": direct_only_solved / total,
        "program_inventor_incremental_tasks_solved": inventor_increment,
        "program_inventor_incremental_rate": inventor_increment / total,
        "tasks_where_inventor_was_invoked": inventor_used,
        "tasks_where_inventor_attempt_was_selected": inventor_selected,
        "direct_unique_bundle_count_capped_at_two": dict(sorted(direct_bundle_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "wall_clock_seconds": elapsed,
        "workers": workers,
        "corpus_sha256": _corpus_sha256(files),
        "search_config": {
            "max_depth": 3,
            "attempts": 2,
            "max_semantic_states_per_depth": 4000,
            "max_equivalent_programs_per_semantics": 4,
            "max_grid_cells": 10000
        },
        "task_ids_emitted": False,
        "task_grids_emitted": False,
        "task_programs_emitted": False,
        "per_task_results_emitted": False,
        "external_learned_capability_calls": 0,
        "donor_runtime_required": False,
        "private_score_claimed": False,
        "promotion_authority": False,
        "terminal_authority": False
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
