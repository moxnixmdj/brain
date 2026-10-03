"""Fail-closed conditional TB4 attainability recompiler.

This module performs arithmetic only. It does not read benchmark instructions,
run Terminal-Bench, or grant acceptance credit.
"""
from __future__ import annotations

NON_GPU_REOPENED = (
    "terminal-bench/distributed-dedup",
    "terminal-bench/formal-crypto",
    "terminal-bench/lake-temp-glm",
    "terminal-bench/live-database-cutover",
    "terminal-bench/medical-claims-processing",
    "terminal-bench/shadow-relay",
    "terminal-bench/takens-embedding-lean",
    "terminal-bench/uefi-bootkit",
    "terminal-bench/wdm-design",
)

GPU_BLOCKED = (
    "terminal-bench/fp8-rmsnorm-gemm",
    "terminal-bench/jax-speedrun-gpu",
    "terminal-bench/math-eval-grader",
)


def recompile(
    *,
    probe_passed: bool,
    prior_remaining_creditable_tasks: int = 36,
    trials_per_task: int = 5,
    required_successes: int = 220,
) -> dict[str, object]:
    if prior_remaining_creditable_tasks < 0 or trials_per_task <= 0 or required_successes < 0:
        raise ValueError("invalid score inputs")

    if not probe_passed:
        upper = prior_remaining_creditable_tasks * trials_per_task
        return {
            "probe_passed": False,
            "reopened_task_count": 0,
            "remaining_creditable_task_count": prior_remaining_creditable_tasks,
            "upper_bound_successes": upper,
            "required_successes": required_successes,
            "attainability_state": "PRIOR_IMPOSSIBILITY_VERDICT_UNCHANGED",
            "execution_authority": False,
            "acceptance_credit_delta": 0,
        }

    reopened = len(NON_GPU_REOPENED)
    remaining = prior_remaining_creditable_tasks + reopened
    upper = remaining * trials_per_task
    state = (
        "NOT_FALSIFIED__ROUTE_REOPENED_FOR_MINIMUM_REALITY_SELECTION"
        if upper >= required_successes
        else "IMPOSSIBLE"
    )
    return {
        "probe_passed": True,
        "reopened_task_count": reopened,
        "remaining_creditable_task_count": remaining,
        "upper_bound_successes": upper,
        "required_successes": required_successes,
        "headroom_successes": upper - required_successes,
        "attainability_state": state,
        "execution_authority": False,
        "acceptance_credit_delta": 0,
    }
