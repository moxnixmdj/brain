"""Fail-closed verifier for an official AutomationBench private result receipt.

The frozen target is the 40.0% Claude Opus 5.5 AutomationBench result run by
Zapier without fallback models. The public Opus source does not itself bind that
result to an exact benchmark version or denominator, so this verifier requires an
owner-attested exact reference match or comparability bridge instead of assuming
that the current public v1.0.6 harness or a 657-task partner split is identical.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from typing import Any, Mapping

IN_SCHEMA = "PROJECT_BRAIN_AUTOMATIONBENCH_PRIVATE_OWNER_RECEIPT_V1"
OUT_SCHEMA = "PROJECT_BRAIN_AUTOMATIONBENCH_PRIVATE_OWNER_RECEIPT_VERDICT_V1"
TARGET_THRESHOLD_PERCENT = Decimal("40.0")
_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_ALLOWED_ISSUERS = {
    "ZAPIER",
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

    benchmark_version = receipt.get("benchmark_version")
    if not isinstance(benchmark_version, str) or not benchmark_version:
        errors.append("BENCHMARK_VERSION_REQUIRED")

    population = receipt.get("population")
    if not isinstance(population, Mapping):
        errors.append("POPULATION_ATTESTATION_MISSING")
        population = {}
    if population.get("kind") != "PRIVATE_HELD_OUT":
        errors.append("PRIVATE_HELD_OUT_SCOPE_REQUIRED")
    if not _sha256(population.get("population_identity_sha256")):
        errors.append("PRIVATE_POPULATION_IDENTITY_SHA256_REQUIRED")
    denominator = _int(population.get("denominator"))
    if denominator is None or denominator <= 0:
        errors.append("DENOMINATOR_INVALID")

    tool_mode = receipt.get("tool_mode")
    if not isinstance(tool_mode, str) or not tool_mode:
        errors.append("TOOL_MODE_REQUIRED")
    max_steps = _int(receipt.get("max_steps_per_task"))
    if max_steps is None or max_steps <= 0:
        errors.append("MAX_STEPS_REQUIRED")
    if receipt.get("task_success_metric") != "task_completed_correctly":
        errors.append("TASK_SUCCESS_METRIC_MISMATCH")
    if receipt.get("fallback_models_used") is not False:
        errors.append("NO_FALLBACK_MODELS_REQUIRED")

    candidate = receipt.get("candidate")
    if not isinstance(candidate, Mapping):
        errors.append("CANDIDATE_BINDING_MISSING")
        candidate = {}
    if not _sha256(candidate.get("content_sha256")):
        errors.append("CANDIDATE_CONTENT_SHA256_REQUIRED")

    owner = receipt.get("owner_attestation")
    if not isinstance(owner, Mapping):
        errors.append("OWNER_ATTESTATION_MISSING")
        owner = {}
    if owner.get("issuer_kind") not in _ALLOWED_ISSUERS:
        errors.append("OWNER_ISSUER_NOT_AUTHORIZED")
    if not isinstance(owner.get("receipt_path"), str) or not owner.get("receipt_path"):
        errors.append("OWNER_RECEIPT_PATH_REQUIRED")
    if not _sha256(owner.get("receipt_sha256")):
        errors.append("OWNER_RECEIPT_SHA256_REQUIRED")
    if owner.get("independent_verified") is not True:
        errors.append("INDEPENDENT_OWNER_VERIFICATION_REQUIRED")
    if not isinstance(owner.get("run_epoch"), str) or not owner.get("run_epoch"):
        errors.append("RUN_EPOCH_REQUIRED")

    match = owner.get("target_reference_match")
    if not isinstance(match, Mapping):
        errors.append("TARGET_REFERENCE_MATCH_ATTESTATION_MISSING")
        match = {}
    if match.get("reference_system") != "Claude Opus 5.5":
        errors.append("TARGET_REFERENCE_SYSTEM_MISMATCH")
    if _dec(match.get("reference_score_percent")) != TARGET_THRESHOLD_PERCENT:
        errors.append("TARGET_REFERENCE_SCORE_MISMATCH")
    if match.get("reference_origin") != "ZAPIER_RUN_REPORTED_BY_ANTHROPIC":
        errors.append("TARGET_REFERENCE_ORIGIN_MISMATCH")
    if match.get("exact_epoch_or_owner_bridge") is not True:
        errors.append("EXACT_REFERENCE_EPOCH_OR_OWNER_BRIDGE_REQUIRED")
    if match.get("population_scope_comparable") is not True:
        errors.append("REFERENCE_POPULATION_SCOPE_MATCH_REQUIRED")
    if match.get("scoring_semantics_comparable") is not True:
        errors.append("REFERENCE_SCORING_SEMANTICS_MATCH_REQUIRED")
    if match.get("tool_protocol_comparable") is not True:
        errors.append("REFERENCE_TOOL_PROTOCOL_MATCH_REQUIRED")
    if match.get("step_limit_comparable") is not True:
        errors.append("REFERENCE_STEP_LIMIT_MATCH_REQUIRED")
    if match.get("fallback_policy_comparable") is not True:
        errors.append("REFERENCE_FALLBACK_POLICY_MATCH_REQUIRED")
    if not _sha256(match.get("binding_sha256")):
        errors.append("REFERENCE_MATCH_BINDING_SHA256_REQUIRED")

    success_count = _int(receipt.get("success_count"))
    if success_count is None or success_count < 0:
        errors.append("SUCCESS_COUNT_INVALID")
    elif denominator is not None and denominator > 0 and success_count > denominator:
        errors.append("SUCCESS_COUNT_EXCEEDS_DENOMINATOR")

    reported = _dec(receipt.get("aggregate_score_percent"))
    if reported is None or reported < 0 or reported > 100:
        errors.append("AGGREGATE_SCORE_PERCENT_INVALID")

    if errors:
        return _fail(*errors)

    assert denominator is not None and denominator > 0
    assert success_count is not None
    assert reported is not None
    assert isinstance(benchmark_version, str)
    assert isinstance(tool_mode, str)
    assert max_steps is not None

    recomputed = (Decimal(success_count) * Decimal(100)) / Decimal(denominator)
    if abs(reported - recomputed) > Decimal("0.05"):
        return _fail("REPORTED_SCORE_INCONSISTENT_WITH_SUCCESS_COUNT_AND_DENOMINATOR")

    required_successes = _ceil(
        (TARGET_THRESHOLD_PERCENT * Decimal(denominator)) / Decimal(100)
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
        "benchmark_version": benchmark_version,
        "population_kind": "PRIVATE_HELD_OUT",
        "population_identity_sha256": population["population_identity_sha256"],
        "denominator": denominator,
        "tool_mode": tool_mode,
        "max_steps_per_task": max_steps,
        "task_success_metric": "task_completed_correctly",
        "fallback_models_used": False,
        "candidate_content_sha256": candidate["content_sha256"],
        "owner_issuer_kind": owner["issuer_kind"],
        "owner_receipt_path": owner["receipt_path"],
        "owner_receipt_sha256": owner["receipt_sha256"],
        "owner_run_epoch": owner["run_epoch"],
        "target_reference_binding_sha256": match["binding_sha256"],
        "success_count": success_count,
        "aggregate_score_percent_reported": str(reported),
        "aggregate_score_percent_recomputed": str(recomputed),
        "threshold_percent": str(TARGET_THRESHOLD_PERCENT),
        "threshold_success_count": required_successes,
        "rule": (
            "PRIVATE_HELDOUT_ONLY__OWNER_CONTENT_ADDRESSED_RECEIPT__"
            "EXACT_OPUS55_40_REFERENCE_EPOCH_MATCH_OR_OWNER_BRIDGE__"
            "NO_PUBLIC_VERSION_OR_657_DENOMINATOR_ASSUMPTION__"
            "NO_FALLBACK_MODELS__EXACT_SUCCESS_COUNT_ARITHMETIC"
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
