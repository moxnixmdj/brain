#!/usr/bin/env python3
"""Fail-closed lower-bound certificates for Finance Agent v2.

The published Finance Agent v2 methodology explicitly binds the reported score
as the mean of three run scores. That supports an unconditional run-score-mass
certificate.

A task-run score-mass certificate is also implemented, but it is conditional on
an authoritative binding that each run score is the arithmetic mean of its 450
equally weighted task scores. The public benchmark page identifies 450 test
questions and per-question scoring, but this module refuses to invent the
within-run aggregation rule.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_CEILING
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_FINANCE_AGENT_V2_SCORE_MASS_V1"
RUNS = 3
TEST_TASKS_PER_RUN = 450
TOTAL_TASK_RUN_EXECUTIONS = RUNS * TEST_TASKS_PER_RUN
THRESHOLD_PERCENT = Decimal("58.59")

# Unconditional consequence of reported_score = mean(run_scores).
RUN_SCORE_MASS_THRESHOLD_PERCENT = THRESHOLD_PERCENT * Decimal(RUNS)

# Conditional consequence if equal task averaging within each run is bound.
TASK_SCORE_MASS_THRESHOLD = (
    Decimal(TOTAL_TASK_RUN_EXECUTIONS) * THRESHOLD_PERCENT / Decimal("100")
)


def _d(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def aggregate_run_score_certificate(
    records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Aggregate independently certified lower bounds on run scores in percent.

    Missing runs contribute zero lower-bound score. This route does not require
    knowledge of within-run task weighting.
    """
    seen: set[int] = set()
    proved_mass = Decimal("0")
    for raw in records:
        run_id = int(raw["run_id"])
        if run_id < 1 or run_id > RUNS:
            raise ValueError("RUN_ID_OUT_OF_RANGE")
        if run_id in seen:
            raise ValueError("DUPLICATE_RUN_BOUND")
        seen.add(run_id)

        lower_bound_percent = _d(raw["lower_bound_percent"])
        if lower_bound_percent < Decimal("0") or lower_bound_percent > Decimal("100"):
            raise ValueError("RUN_LOWER_BOUND_OUT_OF_RANGE")
        proved_mass += lower_bound_percent

    residual = max(Decimal("0"), RUN_SCORE_MASS_THRESHOLD_PERCENT - proved_mass)
    return {
        "schema": SCHEMA,
        "certificate_kind": "RUN_SCORE_MASS",
        "runs": RUNS,
        "threshold_percent": str(THRESHOLD_PERCENT),
        "required_run_score_mass_percent": str(RUN_SCORE_MASS_THRESHOLD_PERCENT),
        "certified_run_count": len(seen),
        "uncertified_run_count": RUNS - len(seen),
        "certified_run_score_mass_lower_bound_percent": str(proved_mass),
        "residual_run_score_mass_percent": str(residual),
        "reported_score_lower_bound_percent": str(proved_mass / Decimal(RUNS)),
        "forced_pass": proved_mass >= RUN_SCORE_MASS_THRESHOLD_PERCENT,
        "hard_nonclaim": (
            "UNCERTIFIED_RUNS_CONTRIBUTE_ZERO ONLY TO THE LOWER BOUND; "
            "THEIR TRUE SCORES ARE NOT CLAIMED TO BE ZERO"
        ),
    }


def minimum_full_score_task_run_executions_if_equal_task_average_bound() -> int:
    return int(TASK_SCORE_MASS_THRESHOLD.to_integral_value(rounding=ROUND_CEILING))


def minimum_uniform_full_score_tasks_across_all_runs_if_equal_task_average_bound() -> int:
    required = TASK_SCORE_MASS_THRESHOLD / Decimal(RUNS)
    return int(required.to_integral_value(rounding=ROUND_CEILING))


def aggregate_task_score_certificate(
    records: Iterable[Mapping[str, Any]],
    *,
    equal_task_average_authoritatively_bound: bool,
) -> dict[str, Any]:
    """Conditional task-level certificate.

    Fails closed unless an authoritative benchmark binding establishes that each
    run score is the arithmetic mean of 450 equally weighted task scores.
    """
    if not equal_task_average_authoritatively_bound:
        raise ValueError("EQUAL_TASK_AVERAGE_AGGREGATION_NOT_BOUND")

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
            raise ValueError("TASK_LOWER_BOUND_OUT_OF_RANGE")
        proved_mass += lower_bound

    residual = max(Decimal("0"), TASK_SCORE_MASS_THRESHOLD - proved_mass)
    return {
        "schema": SCHEMA,
        "certificate_kind": "TASK_SCORE_MASS_CONDITIONAL",
        "equal_task_average_authoritatively_bound": True,
        "test_tasks_per_run": TEST_TASKS_PER_RUN,
        "runs": RUNS,
        "total_task_run_executions": TOTAL_TASK_RUN_EXECUTIONS,
        "threshold_percent": str(THRESHOLD_PERCENT),
        "required_task_score_mass": str(TASK_SCORE_MASS_THRESHOLD),
        "certified_task_run_count": len(seen),
        "uncertified_task_run_count": TOTAL_TASK_RUN_EXECUTIONS - len(seen),
        "certified_task_score_mass_lower_bound": str(proved_mass),
        "full_population_percent_lower_bound": str(
            Decimal("100") * proved_mass / Decimal(TOTAL_TASK_RUN_EXECUTIONS)
        ),
        "residual_task_score_mass": str(residual),
        "forced_pass": proved_mass >= TASK_SCORE_MASS_THRESHOLD,
        "minimum_full_score_task_run_executions":
            minimum_full_score_task_run_executions_if_equal_task_average_bound(),
        "minimum_uniform_full_score_tasks_across_all_runs":
            minimum_uniform_full_score_tasks_across_all_runs_if_equal_task_average_bound(),
        "hard_nonclaims": [
            "NO_PRIVATE_TASK_OR_RUBRIC CONTENT IS INFERRED",
            "NO_CATEGORY COUNT OR DISTRIBUTION IS INFERRED",
            "TASK LEVEL CREDIT IS INVALID UNLESS EQUAL TASK AVERAGING IS AUTHORITATIVELY BOUND",
        ],
    }
