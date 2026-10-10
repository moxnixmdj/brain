from __future__ import annotations

import math
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TB4_BUILDKITE_RESOURCE_REOPEN_VERDICT_V1"

def _num(v: Any, name: str, errors: list[str]) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
        errors.append("INVALID_" + name.upper())
        return 0.0
    return float(v)

def evaluate(cut: Mapping[str, Any], receipt: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if cut.get("schema") != "PROJECT_BRAIN_TB4_MINIMUM_CARRIER_RECOVERY_CUT_V1":
        errors.append("CUT_SCHEMA")
    if receipt.get("schema") != "PROJECT_BRAIN_BUILDKITE_ZERO_CASE_RUNTIME_RECEIPT_20261006_V1":
        errors.append("RECEIPT_SCHEMA")

    env = cut.get("minimum_carrier_envelope")
    score = cut.get("frozen_score_math")
    measured = receipt.get("measured_runtime")
    if not isinstance(env, Mapping):
        errors.append("CARRIER_ENVELOPE_MISSING")
        env = {}
    if not isinstance(score, Mapping):
        errors.append("SCORE_MATH_MISSING")
        score = {}
    if not isinstance(measured, Mapping):
        errors.append("MEASURED_RUNTIME_MISSING")
        measured = {}

    nproc = _num(measured.get("nproc"), "nproc", errors)
    mem_kb = _num(measured.get("mem_total_kb"), "mem_total_kb", errors)
    disk_kb = _num(measured.get("free_disk_kb"), "free_disk_kb", errors)
    mem_mb = mem_kb / 1024.0
    disk_mb = disk_kb / 1024.0

    if nproc < float(env.get("cpus_at_least", 10**9)):
        errors.append("CPU_ENVELOPE_NOT_MET")
    if mem_mb < float(env.get("usable_memory_mb_at_least", 10**9)):
        errors.append("MEMORY_ENVELOPE_NOT_MET")
    if disk_mb < float(env.get("free_storage_mb_at_least", 10**9)):
        errors.append("DISK_ENVELOPE_NOT_MET")
    if float(env.get("gpus_required", 0)) != 0:
        errors.append("RECOVERY_ENVELOPE_UNEXPECTEDLY_REQUIRES_GPU")
    if measured.get("ordinary_container_run") != "PASS":
        errors.append("DOCKER_RUNTIME_NOT_VERIFIED")
    if measured.get("eight_cpu_container_limit_acceptance") != "PASS":
        errors.append("EIGHT_CPU_CONTAINER_LIMIT_NOT_VERIFIED")
    if not measured.get("docker_compose"):
        errors.append("DOCKER_COMPOSE_NOT_VERIFIED")
    if receipt.get("provider_execution", {}).get("state") != "passed":
        errors.append("PROVIDER_BUILD_NOT_PASSED")
    if receipt.get("provider_execution", {}).get("queue", {}).get("instance_shape") != "LINUX_AMD64_8X32":
        errors.append("WRONG_INSTANCE_SHAPE")
    if receipt.get("accounting", {}).get("terminal_cases_consumed") != 0:
        errors.append("TERMINAL_CASES_CONSUMED")

    chosen = cut.get("minimum_recovery_set")
    if not isinstance(chosen, list) or len(chosen) != 8 or len(set(chosen)) != 8:
        errors.append("MINIMUM_RECOVERY_SET_NOT_EXACT_EIGHT")

    trials = score.get("trials_per_task")
    current = score.get("current_remaining_creditable_tasks")
    required = score.get("required_successes")
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in (trials, current, required)):
        errors.append("INVALID_SCORE_MATH")
        trials = current = required = 0
    projected_tasks = current + len(chosen) if isinstance(chosen, list) else 0
    projected_successes = projected_tasks * trials
    resource_envelope_bound = not errors

    billing_status = receipt.get("billing_truth_boundary", {}).get("billing_hard_stop_status")
    zero_cost_hard_stop_bound = billing_status == "VERIFIED"
    task_identity_bound = False
    protocol_equivalence_bound = False
    full_route_reopened = (
        resource_envelope_bound
        and zero_cost_hard_stop_bound
        and task_identity_bound
        and protocol_equivalence_bound
        and projected_successes >= required
    )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__RESOURCE_ENVELOPE_BOUND__ATTAINABILITY_CONDITIONALLY_REOPENS_AT_220__NONRESOURCE_PREMISES_OPEN__ZERO_CREDIT"
            if resource_envelope_bound
            else "FAIL_CLOSED"
        ),
        "pass": resource_envelope_bound,
        "errors": sorted(set(errors)),
        "measured": {
            "nproc": nproc,
            "usable_memory_mb_approx": mem_mb,
            "free_storage_mb_approx": disk_mb,
        },
        "required_envelope": {
            "cpus_at_least": env.get("cpus_at_least"),
            "usable_memory_mb_at_least": env.get("usable_memory_mb_at_least"),
            "free_storage_mb_at_least": env.get("free_storage_mb_at_least"),
            "gpus_required": env.get("gpus_required"),
        },
        "minimum_recovery_task_count": len(chosen) if isinstance(chosen, list) else 0,
        "current_creditable_task_count": current,
        "projected_creditable_task_count_if_eight_bind": projected_tasks,
        "current_upper_bound_successes": current * trials,
        "projected_upper_bound_successes_if_eight_bind": projected_successes,
        "required_successes": required,
        "resource_envelope_bound": resource_envelope_bound,
        "task_identity_bound": task_identity_bound,
        "protocol_equivalence_bound": protocol_equivalence_bound,
        "zero_cost_hard_stop_bound": zero_cost_hard_stop_bound,
        "full_attainability_route_reopened": full_route_reopened,
        "execution_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }
