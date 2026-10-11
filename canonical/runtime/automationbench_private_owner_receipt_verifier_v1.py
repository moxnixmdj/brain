"""Fail-closed verifier for the frozen AutomationBench >= 40 predicate.

Admissible result surfaces:
1. Zapier's official private v1.0.6 leaderboard strict `task_completed_correctly`.
2. Artificial Analysis' AutomationBench-AA `Tasks Completed`, but only when the
   receipt binds the same private 657-task v1.0.6 population and the published
   assertion partition showing semantic equivalence to all-assertions-pass.

Both routes use API mode, a 50-turn cap, deterministic final-state grading, a
frozen content-addressed Brain candidate, and exact success-count arithmetic.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from typing import Any, Mapping

IN_SCHEMA = "PROJECT_BRAIN_AUTOMATIONBENCH_PRIVATE_OWNER_RECEIPT_V1"
OUT_SCHEMA = "PROJECT_BRAIN_AUTOMATIONBENCH_PRIVATE_OWNER_RECEIPT_VERDICT_V1"

TARGET_THRESHOLD_PERCENT = Decimal("40.0")
TARGET_VERSION = "1.0.6"
TARGET_DENOMINATOR = 657
TARGET_TOOL_MODE = "api"
TARGET_MAX_STEPS = 50

SURFACE_ZAPIER = "ZAPIER_PRIVATE_LEADERBOARD"
SURFACE_AA = "ARTIFICIAL_ANALYSIS_AUTOMATIONBENCH_AA"

_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_ALLOWED_ISSUERS = {
    "ZAPIER",
    "ARTIFICIAL_ANALYSIS",
    "OFFICIALLY_DELEGATED_AUTOMATIONBENCH_EVALUATOR",
}


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": OUT_SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "decision": "UNRESOLVED",
        "predicate": "AUTOMATIONBENCH_GE_40",
        "predicate_satisfied": False,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def _dec(v: Any) -> Decimal | None:
    if isinstance(v, bool) or not isinstance(v, (int, float, str, Decimal)):
        return None
    try:
        out = Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None
    return out if out.is_finite() else None


def _int(v: Any) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _sha256(v: Any) -> bool:
    return isinstance(v, str) and _HEX64.fullmatch(v) is not None


def _ceil(x: Decimal) -> int:
    return int(x.to_integral_value(rounding=ROUND_CEILING))


def evaluate(receipt: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        return _fail("INPUT_NOT_OBJECT")
    errors: list[str] = []

    if receipt.get("schema") != IN_SCHEMA:
        errors.append("SCHEMA_INVALID")
    if receipt.get("benchmark_name") != "AutomationBench":
        errors.append("BENCHMARK_NAME_MISMATCH")
    if receipt.get("benchmark_version") != TARGET_VERSION:
        errors.append("BENCHMARK_VERSION_MISMATCH")

    surface = receipt.get("evaluation_surface")
    if surface not in {SURFACE_ZAPIER, SURFACE_AA}:
        errors.append("EVALUATION_SURFACE_INVALID")

    population = receipt.get("population")
    if not isinstance(population, Mapping):
        errors.append("POPULATION_ATTESTATION_MISSING")
        population = {}
    if population.get("kind") != "PRIVATE_HELD_OUT":
        errors.append("PRIVATE_HELD_OUT_SCOPE_REQUIRED")
    if population.get("zapier_private_v1_0_6_657") is not True:
        errors.append("ZAPIER_PRIVATE_V1_0_6_657_BINDING_REQUIRED")
    if not _sha256(population.get("population_identity_sha256")):
        errors.append("PRIVATE_POPULATION_IDENTITY_SHA256_REQUIRED")
    denominator = _int(population.get("denominator"))
    if denominator != TARGET_DENOMINATOR:
        errors.append("PRIVATE_POPULATION_DENOMINATOR_MISMATCH")

    if receipt.get("tool_mode") != TARGET_TOOL_MODE:
        errors.append("TOOL_MODE_MISMATCH")
    if receipt.get("max_steps_per_task") != TARGET_MAX_STEPS:
        errors.append("MAX_STEPS_MISMATCH")

    metric = receipt.get("task_success_metric")
    if surface == SURFACE_ZAPIER:
        if metric != "task_completed_correctly":
            errors.append("ZAPIER_STRICT_METRIC_MISMATCH")
    elif surface == SURFACE_AA:
        if metric != "tasks_completed":
            errors.append("AA_TASKS_COMPLETED_METRIC_REQUIRED")

    fallback_used = receipt.get("fallback_models_used")
    if not isinstance(fallback_used, bool):
        errors.append("FALLBACK_POLICY_MUST_BE_EXPLICIT_BOOLEAN")

    candidate = receipt.get("candidate")
    if not isinstance(candidate, Mapping):
        errors.append("CANDIDATE_BINDING_MISSING")
        candidate = {}
    if not _sha256(candidate.get("content_sha256")):
        errors.append("CANDIDATE_CONTENT_SHA256_REQUIRED")
    if candidate.get("all_execution_components_bound") is not True:
        errors.append("ALL_EXECUTION_COMPONENTS_MUST_BE_BOUND")

    owner = receipt.get("owner_attestation")
    if not isinstance(owner, Mapping):
        errors.append("OWNER_ATTESTATION_MISSING")
        owner = {}
    issuer = owner.get("issuer_kind")
    if issuer not in _ALLOWED_ISSUERS:
        errors.append("OWNER_ISSUER_NOT_AUTHORIZED")

    if surface == SURFACE_ZAPIER:
        if issuer not in {"ZAPIER", "OFFICIALLY_DELEGATED_AUTOMATIONBENCH_EVALUATOR"}:
            errors.append("ZAPIER_SURFACE_ISSUER_MISMATCH")
        if owner.get("official_v1_0_6_private_leaderboard_surface") is not True:
            errors.append("OFFICIAL_V1_0_6_PRIVATE_SURFACE_ATTESTATION_REQUIRED")

    if surface == SURFACE_AA:
        if issuer != "ARTIFICIAL_ANALYSIS":
            errors.append("AA_SURFACE_ISSUER_MISMATCH")
        if owner.get("automationbench_aa_private_657_v1_0_6_in_collaboration_with_zapier") is not True:
            errors.append("AA_ZAPIER_PRIVATE_COLLABORATION_BINDING_REQUIRED")
        if owner.get("every_assertion_classified_objective_or_guardrail") is not True:
            errors.append("AA_ASSERTION_PARTITION_BINDING_REQUIRED")
        if owner.get("tasks_completed_requires_every_objective_and_no_guardrail_violation") is not True:
            errors.append("AA_STRICT_COMPLETION_SEMANTICS_REQUIRED")
        if owner.get("deterministic_final_state_grading") is not True:
            errors.append("AA_DETERMINISTIC_FINAL_STATE_GRADING_REQUIRED")

    if not isinstance(owner.get("receipt_path"), str) or not owner.get("receipt_path"):
        errors.append("OWNER_RECEIPT_PATH_REQUIRED")
    if not _sha256(owner.get("receipt_sha256")):
        errors.append("OWNER_RECEIPT_SHA256_REQUIRED")
    if owner.get("independent_verified") is not True:
        errors.append("INDEPENDENT_OWNER_VERIFICATION_REQUIRED")
    if not isinstance(owner.get("run_epoch"), str) or not owner.get("run_epoch"):
        errors.append("RUN_EPOCH_REQUIRED")

    success_count = _int(receipt.get("success_count"))
    if success_count is None or success_count < 0:
        errors.append("SUCCESS_COUNT_INVALID")
    elif success_count > TARGET_DENOMINATOR:
        errors.append("SUCCESS_COUNT_EXCEEDS_DENOMINATOR")

    reported = _dec(receipt.get("aggregate_score_percent"))
    if reported is None or reported < 0 or reported > 100:
        errors.append("AGGREGATE_SCORE_PERCENT_INVALID")

    if errors:
        return _fail(*errors)

    assert success_count is not None
    assert reported is not None
    assert isinstance(fallback_used, bool)
    assert isinstance(surface, str)
    assert isinstance(metric, str)

    recomputed = (Decimal(success_count) * Decimal(100)) / Decimal(TARGET_DENOMINATOR)
    if abs(reported - recomputed) > Decimal("0.05"):
        return _fail("REPORTED_SCORE_INCONSISTENT_WITH_SUCCESS_COUNT_AND_DENOMINATOR")

    required_successes = _ceil(
        (TARGET_THRESHOLD_PERCENT * Decimal(TARGET_DENOMINATOR)) / Decimal(100)
    )
    predicate_satisfied = success_count >= required_successes

    return {
        "schema": OUT_SCHEMA,
        "status": "PASS",
        "pass": True,
        "errors": [],
        "predicate": "AUTOMATIONBENCH_GE_40",
        "decision": "PASS_LOCKED" if predicate_satisfied else "FAIL_LOCKED",
        "predicate_satisfied": predicate_satisfied,
        "benchmark_name": "AutomationBench",
        "benchmark_version": TARGET_VERSION,
        "evaluation_surface": surface,
        "population_kind": "PRIVATE_HELD_OUT",
        "denominator": TARGET_DENOMINATOR,
        "tool_mode": TARGET_TOOL_MODE,
        "max_steps_per_task": TARGET_MAX_STEPS,
        "source_task_success_metric": metric,
        "normalized_task_success_metric": "task_completed_correctly",
        "metric_equivalence_basis": (
            "DIRECT_ZAPIER_TASK_COMPLETED_CORRECTLY"
            if surface == SURFACE_ZAPIER
            else "AA_TASKS_COMPLETED_EQUALS_ALL_OBJECTIVES_TRUE_AND_NO_GUARDRAIL_VIOLATION__EVERY_ASSERTION_PARTITIONED_AS_OBJECTIVE_OR_GUARDRAIL"
        ),
        "fallback_models_used": fallback_used,
        "candidate_content_sha256": candidate["content_sha256"],
        "all_execution_components_bound": True,
        "owner_issuer_kind": issuer,
        "owner_receipt_path": owner["receipt_path"],
        "owner_receipt_sha256": owner["receipt_sha256"],
        "owner_run_epoch": owner["run_epoch"],
        "success_count": success_count,
        "aggregate_score_percent_reported": str(reported),
        "aggregate_score_percent_recomputed": str(recomputed),
        "threshold_percent": str(TARGET_THRESHOLD_PERCENT),
        "threshold_success_count": required_successes,
        "rule": (
            "ZAPIER_PRIVATE_V1_0_6_657_ONLY__API_MODE__50_TURNS__"
            "STRICT_FULL_TASK_COMPLETION_NORMALIZED_TO_TASK_COMPLETED_CORRECTLY__"
            "ZAPIER_OR_AA_EXACT_PRIVATE_SURFACE__"
            "FROZEN_CONTENT_ADDRESSED_CANDIDATE__OWNER_RECEIPT__"
            "EXACT_SUCCESS_COUNT_ARITHMETIC__NO_PUBLIC_600_SUBSTITUTION"
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
