#!/usr/bin/env python3
"""Classify GitHub Actions outcomes without confusing carrier failure with code failure."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PREASSIGNMENT = "INFRASTRUCTURE_PRE_ASSIGNMENT_FAILURE"
EXECUTED_FAILURE = "EXECUTED_FAILURE_REQUIRES_LOG_ANALYSIS"
EXECUTED_SUCCESS = "EXECUTED_SUCCESS"
PENDING = "PENDING_EXECUTION"
MIXED = "MIXED_OR_INCOMPLETE_EXECUTION"
UNKNOWN = "UNKNOWN_NO_JOBS"

_PENDING_STATES = {"queued", "in_progress", "waiting", "pending", "requested"}
_FAILURE_CONCLUSIONS = {"failure", "timed_out", "cancelled", "action_required"}


def _steps_count(job: dict[str, Any]) -> int | None:
    steps = job.get("steps")
    return len(steps) if isinstance(steps, list) else None


def _preassignment(job: dict[str, Any]) -> bool:
    return (
        int(job.get("runner_id") or 0) == 0
        and not str(job.get("runner_name") or "").strip()
        and _steps_count(job) == 0
    )


def _result(
    classification: str,
    jobs: list[dict[str, Any]],
    alternate: bool,
) -> dict[str, Any]:
    return {
        "schema": "PROJECT_BRAIN_CI_CARRIER_OUTCOME_CLASSIFICATION_V1",
        "classification": classification,
        "job_count": len(jobs),
        "preassignment_job_count": sum(1 for job in jobs if _preassignment(job)),
        "executed_job_count": sum(1 for job in jobs if not _preassignment(job)),
        "semantic_failure_observed": classification == EXECUTED_FAILURE,
        "branch_repair_authorized_from_this_signal": False,
        "same_carrier_retry_authorized_without_health_change": False,
        "alternate_verification_carrier_required": alternate,
        "rule": "NO_EXECUTION_WITNESS_MEANS_NO_SEMANTIC_NEGATIVE_EVIDENCE",
    }


def classify_jobs(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a fail-closed semantic classification for one workflow run's jobs."""
    if not jobs:
        return _result(UNKNOWN, jobs, alternate=False)

    states = {str(job.get("status") or "").strip().lower() for job in jobs}
    if states & _PENDING_STATES:
        return _result(PENDING, jobs, alternate=False)

    pre = [job for job in jobs if _preassignment(job)]
    executed = [job for job in jobs if not _preassignment(job)]

    if len(pre) == len(jobs):
        return _result(PREASSIGNMENT, jobs, alternate=True)

    failed_executed = [
        job
        for job in executed
        if str(job.get("conclusion") or "").strip().lower()
        in _FAILURE_CONCLUSIONS
    ]
    if failed_executed:
        return _result(EXECUTED_FAILURE, jobs, alternate=False)

    if executed and not pre and all(
        str(job.get("conclusion") or "").strip().lower() == "success"
        for job in executed
    ):
        return _result(EXECUTED_SUCCESS, jobs, alternate=False)

    return _result(MIXED, jobs, alternate=bool(pre))


def _extract_jobs(doc: Any) -> list[dict[str, Any]]:
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict) and isinstance(doc.get("jobs"), list):
        return doc["jobs"]
    raise ValueError("input must be a jobs array or an object containing jobs[]")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="GitHub Actions jobs JSON")
    args = parser.parse_args()
    doc = json.loads(args.input.read_text(encoding="utf-8"))
    result = classify_jobs(_extract_jobs(doc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
