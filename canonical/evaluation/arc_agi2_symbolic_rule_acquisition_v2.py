"""ARC-AGI-2 acquisition audit for binary-predicate symbolic rule inducer V2."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from canonical.runtime.visual_symbolic_rule_inducer_v2 import score_public_task

SCHEMA = "PROJECT_BRAIN_ARC_AGI2_SYMBOLIC_RULE_ACQUISITION_AUDIT_V2"


def _partition(files: list[Path], name: str) -> list[Path]:
    ordered = sorted(
        files,
        key=lambda p: (hashlib.sha256(p.name.encode("utf-8")).hexdigest(), p.name),
    )
    if len(ordered) != 1000:
        raise SystemExit(f"TRAINING_TASK_COUNT_MISMATCH:{len(ordered)}")
    if name == "acquisition":
        return ordered[:800]
    if name == "development":
        return ordered[800:900]
    if name == "qualification":
        raise SystemExit("QUALIFICATION_PARTITION_REQUIRES_SEPARATE_FROZEN_AUTHORITY")
    raise SystemExit("PARTITION_INVALID")


def _score_one(args: tuple[str, int, int, int, int]) -> dict[str, Any]:
    path_s, max_depth, max_predicates, max_subproblems, max_nodes = args
    task = json.loads(Path(path_s).read_text(encoding="utf-8"))
    result = score_public_task(
        task,
        attempts=2,
        max_depth=max_depth,
        max_predicates_per_node=max_predicates,
        max_search_subproblems=max_subproblems,
        max_generated_split_nodes=max_nodes,
    )
    induction = result.get("induction", {}) if isinstance(result, dict) else {}
    best = induction.get("best_rule") if isinstance(induction, dict) else None
    return {
        "status": str(result.get("status")),
        "solved": result.get("exact_task_solved") is True,
        "induction_status": str(induction.get("status")),
        "best_depth": None if not isinstance(best, dict) else int(best.get("depth", 0)),
        "best_nodes": None if not isinstance(best, dict) else int(best.get("node_count", 0)),
        "best_cost": None if not isinstance(best, dict) else float(best.get("cost", 0.0)),
        "generated_split_nodes": int(induction.get("generated_split_nodes", 0) or 0),
        "search_subproblems": int(induction.get("search_subproblems", 0) or 0),
        "search_bound_hit": induction.get("search_bound_hit") is True,
    }


def _corpus_hash(files: list[Path]) -> str:
    h = hashlib.sha256()
    for path in files:
        raw = path.read_bytes()
        h.update(path.name.encode("utf-8"))
        h.update(b"\0")
        h.update(hashlib.sha256(raw).digest())
    return h.hexdigest()


def run(
    data_dir: Path,
    *,
    partition: str,
    max_depth: int = 4,
    max_predicates_per_node: int = 12,
    max_search_subproblems: int = 5000,
    max_generated_split_nodes: int = 20000,
    workers: int = 8,
) -> dict[str, Any]:
    all_files = sorted(data_dir.glob("*.json"))
    selected = _partition(all_files, partition)
    if isinstance(workers, bool) or not isinstance(workers, int) or workers < 1:
        raise SystemExit("WORKERS_INVALID")

    status_counts: Counter[str] = Counter()
    induction_status_counts: Counter[str] = Counter()
    rule_depth_counts: Counter[str] = Counter()
    exact = 0
    exact_rules = 0
    bound_hits = 0
    total_nodes = 0
    total_cost = 0.0
    best_rule_count = 0
    total_generated_splits = 0
    total_subproblems = 0
    start = time.perf_counter()

    args = [
        (
            str(path),
            max_depth,
            max_predicates_per_node,
            max_search_subproblems,
            max_generated_split_nodes,
        )
        for path in selected
    ]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for row in pool.map(_score_one, args):
            status_counts[row["status"]] += 1
            induction_status_counts[row["induction_status"]] += 1
            exact += int(row["solved"])
            exact_rules += int(row["induction_status"] == "EXACT_RULES_FOUND")
            bound_hits += int(row["search_bound_hit"])
            total_generated_splits += row["generated_split_nodes"]
            total_subproblems += row["search_subproblems"]
            if row["best_depth"] is not None:
                rule_depth_counts[str(row["best_depth"])] += 1
                total_nodes += row["best_nodes"]
                total_cost += row["best_cost"]
                best_rule_count += 1

    elapsed = time.perf_counter() - start
    return {
        "schema": SCHEMA,
        "status": "ACQUISITION_AUDIT_COMPLETE" if partition == "acquisition" else "DEVELOPMENT_HOLDOUT_AGGREGATE_COMPLETE",
        "partition": partition,
        "task_count": len(selected),
        "exact_tasks_solved": exact,
        "exact_task_solve_rate": exact / len(selected),
        "tasks_with_exact_training_rule": exact_rules,
        "exact_training_rule_rate": exact_rules / len(selected),
        "search_bound_hit_tasks": bound_hits,
        "status_counts": dict(sorted(status_counts.items())),
        "induction_status_counts": dict(sorted(induction_status_counts.items())),
        "best_rule_depth_counts": dict(sorted(rule_depth_counts.items())),
        "mean_best_rule_nodes": None if not best_rule_count else total_nodes / best_rule_count,
        "mean_best_rule_cost": None if not best_rule_count else total_cost / best_rule_count,
        "aggregate_generated_split_nodes": total_generated_splits,
        "aggregate_search_subproblems": total_subproblems,
        "search_config": {
            "max_depth": max_depth,
            "max_predicates_per_node": max_predicates_per_node,
            "max_search_subproblems": max_search_subproblems,
            "max_generated_split_nodes": max_generated_split_nodes
        },
        "workers": workers,
        "wall_clock_seconds": elapsed,
        "partition_corpus_sha256": _corpus_hash(selected),
        "task_ids_emitted": False,
        "task_grids_emitted": False,
        "per_task_results_emitted": False,
        "external_learned_capability_calls": 0,
        "donor_runtime_required": False,
        "promotion_authority": False,
        "terminal_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("--partition", choices=("acquisition", "development"), required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    result = run(args.data_dir, partition=args.partition)
    body = json.dumps(result, indent=2, sort_keys=True)
    print(body)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(body + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
