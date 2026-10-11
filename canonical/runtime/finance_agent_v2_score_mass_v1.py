#!/usr/bin/env python3
"""Fail-closed score-mass lower-bound certificate for Finance Agent v2.

This module proves only aggregate threshold arithmetic. It never guesses private
questions, rubrics, category counts, hidden conventions, or unobserved scores.
Uncertified task-run executions contribute a lower bound of zero.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_CEILING
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_FINANCE_AGENT_V2_SCORE_MASS_V1"
TEST_TASKS_PER_RUN = 450
RUNS = 3
TOTAL_TASK_RUN_EXECUTIONS = TEST_TASKS_PER_RUN * RUNS
THRESHOLD_PERCENT = Decimal("58.59")
THRESHOLD_FRACTION = THRESHOLD_PERCENT / Decimal("100")
THRESHOLD_SCORE_MASS = Decimal(TOTAL_TASK_RUN_EXECUTIONS) * THRESHOLD_FRACTION


def _d(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def minimum_full_score_executions() -> int:
    return int(THRESHOLD_SCORE_MASS.to_integral_value(rounding=ROUND_CEILING))


def minimum_uniform_full_score_tasks_across_all_runs() -> int:
    required = THRESHOLD_SCORE_MASS / Decimal(RUNS)
    return int(required.to_integral_value(rounding=ROUND_CEILING))


def aggregate_certificate(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    seen: set[tuple[int, str]] = set()
    per_run_counts = {run_id: 0 for run_id in range(1, RUNS + 1)}
    proved_mass = Decimal("0")

    for raw in records:
        run_id = int(raw["run_id"])
        if run_id not in per_run_counts:
            raise ValueError("RUN_ID_OUT_OF_RANGE")

        task_id = str(raw["task_id"]).strip()
        if not task_id:
            raise ValueError("TASK_ID_EMPTY")

        key = (run_id, task_id)
        if key in seen:
            raise ValueError("DUPLICATE_TASK_RUN_BOUND")
        seen.add(key)

        per_run_counts[run_id] += 1
        if per_run_counts[run_id] > TEST_TASKS_PER_RUN:
            raise ValueError("MORE_THAN_450_BOUNDS_IN_ONE_RUN")

        lower_bound = _d(raw["lower_bound"])
        if lower_bound < Decimal("0") or lower_bound > Decimal("1"):
            raise ValueError("LOWER_BOUND_OUT_OF_RANGE")
        proved_mass += lower_bound

    if len(seen) > TOTAL_TASK_RUN_EXECUTIONS:
        raise ValueError("MORE_BOUNDS_THAN_TOTAL_TASK_RUN_EXECUTIONS")

    full_population_lower_bound = (
        Decimal("100") * proved_mass / Decimal(TOTAL_TASK_RUN_EXECUTIONS)
    )
    residual = max(Decimal("0"), THRESHOLD_SCORE_MASS - proved_mass)
    forced_pass = proved_mass >= THRESHOLD_SCORE_MASS

    return {
        "schema": SCHEMA,
        "test_tasks_per_run": TEST_TASKS_PER_RUN,
        "runs": RUNS,
        "total_task_run_executions": TOTAL_TASK_RUN_EXECUTIONS,
        "threshold_percent": str(THRESHOLD_PERCENT),
        "threshold_score_mass": str(THRESHOLD_SCORE_MASS),
        "certified_task_run_count": len(seen),
        "uncertified_task_run_count": TOTAL_TASK_RUN_EXECUTIONS - len(seen),
        "certified_score_mass_lower_bound": str(proved_mass),
        "full_population_percent_lower_bound": str(full_population_lower_bound),
        "residual_score_mass_to_force_pass": str(residual),
        "forced_pass": forced_pass,
        "minimum_full_score_executions": minimum_full_score_executions(),
        "minimum_uniform_full_score_tasks_across_all_runs":
            minimum_uniform_full_score_tasks_across_all_runs(),
        "hard_nonclaims": [
            "UNCERTIFIED_EXECUTIONS_ARE_NOT_ASSUMED_TO_SCORE_ZERO_IN_REALITY; ZERO_IS_ONLY_THEIR LOWER BOUND",
            "NO_PRIVATE_TASK_OR_RUBRIC_CONTENT_IS_INFERRED",
            "NO_CATEGORY_COUNT_OR_CATEGORY_SCORE_DISTRIBUTION_IS_INFERRED",
            "A_LOWER_BOUND_RECORD_REQUIRES INDEPENDENT EVIDENCE THAT THE NAMED TASK-RUN SCORE IS AT LEAST THAT VALUE",
        ],
    }
