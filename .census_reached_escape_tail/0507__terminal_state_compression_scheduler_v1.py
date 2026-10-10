#!/usr/bin/env python3
"""Fail-closed state-compression scheduler and shadow-reality lease gate.

This module is scheduling/governance preproof only. It grants no terminal
execution, promotion, family, capability, ownership, or acceptance credit.

A shadow collection may overlap unrelated zero-reality work only when a
separate independently-authorized shadow lease exists, the generic precommit
isolation theorem is instantiated, the benchmark thin adapter passes, the
result is sealed from every candidate-mutating or scheduling process, and
release is impossible before the zero-reality fixed point.

The purpose is to reduce makespan without creating score-informed adaptation.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.generic_precommit_isolation_theorem_v1 import (
    verify_benchmark_thin_adapter,
    verify_generic_isolation,
)

SCHEMA = "PROJECT_BRAIN_TERMINAL_STATE_COMPRESSION_SCHEDULER_V2"

REQUIRED_POLICY_PREMISES = (
    "candidate_frozen",
    "outputs_bound_to_precommit",
    "outputs_escrowed",
    "outputs_hidden_from_candidate",
    "outputs_hidden_from_optimizer_until_release",
    "outputs_hidden_from_candidate_mutators_until_release",
    "unrelated_work_cannot_mutate_candidate",
    "zero_incremental_spend_guard",
    "route_result_not_used_for_acceptance_before_fixed_point",
    "release_requires_zero_reality_fixed_point",
    "release_requires_independent_verification",
    "one_use_lease",
    "shadow_authority_receipt_content_addressed",
)


def _is_sha256(value: Any) -> bool:
    s = str(value or "")
    return len(s) == 64 and all(c in "0123456789abcdefABCDEF" for c in s)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def robust_state_compression_priority(
    *,
    guaranteed_progress: float,
    guaranteed_deletion: float,
    guaranteed_information: float,
    critical_path_seconds: float,
    correlation_penalty: float = 0.0,
    calibrated_expected_closure: float = 0.0,
) -> float:
    """Rank by guaranteed state compression without inventing success odds."""
    terms = (
        guaranteed_progress,
        guaranteed_deletion,
        guaranteed_information,
        calibrated_expected_closure,
    )
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in terms):
        raise TypeError("priority terms must be numeric")
    if any(x < 0 for x in terms):
        raise ValueError("priority terms must be >= 0")
    if isinstance(critical_path_seconds, bool) or not isinstance(
        critical_path_seconds, (int, float)
    ):
        raise TypeError("critical_path_seconds must be numeric")
    if critical_path_seconds <= 0:
        raise ValueError("critical_path_seconds must be > 0")
    if isinstance(correlation_penalty, bool) or not isinstance(
        correlation_penalty, (int, float)
    ):
        raise TypeError("correlation_penalty must be numeric")
    if correlation_penalty < 0:
        raise ValueError("correlation_penalty must be >= 0")

    numerator = (
        guaranteed_progress
        + guaranteed_deletion
        + guaranteed_information
        + calibrated_expected_closure
    )
    return numerator / (critical_path_seconds * (1.0 + correlation_penalty))


def classify_probability_state(
    *,
    deterministic_entailment: bool = False,
    falsified_until_wake: bool = False,
    calibrated_bernoulli_history: bool = False,
) -> str:
    """Preserve unknown probability rather than manufacturing a point value."""
    truthy = sum(
        bool(x)
        for x in (
            deterministic_entailment,
            falsified_until_wake,
            calibrated_bernoulli_history,
        )
    )
    if truthy > 1:
        raise ValueError("probability classifications are mutually exclusive")
    if deterministic_entailment:
        return "ONE"
    if falsified_until_wake:
        return "ZERO_UNTIL_MATERIAL_WAKE"
    if calibrated_bernoulli_history:
        return "CALIBRATED_EXTERNALLY__USE_BOUND_POSTERIOR_RECEIPT"
    return "UNKNOWN__NO_POINT_ESTIMATE"


def verify_shadow_reality_lease(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Verify a proposed one-use shadow-collection lease fail-closed.

    Boolean assertions about isolation and benchmark equivalence are not
    accepted directly. Their underlying receipts are re-evaluated with the
    independently verified generic theorem implementation.
    """
    reasons: list[str] = []

    isolation_receipt = receipt.get("isolation_receipt")
    if not isinstance(isolation_receipt, Mapping):
        reasons.append("MISSING_ISOLATION_RECEIPT")
        isolation = {"generic_isolation_kernel_pass": False, "reasons": []}
    else:
        isolation = verify_generic_isolation(isolation_receipt)
        if not isolation["generic_isolation_kernel_pass"]:
            reasons.append("GENERIC_ISOLATION_KERNEL_FAIL")

    adapter_receipt = receipt.get("benchmark_adapter")
    if not isinstance(adapter_receipt, Mapping):
        reasons.append("MISSING_BENCHMARK_ADAPTER")
        adapter = {"benchmark_thin_adapter_pass": False, "missing": []}
    else:
        adapter = verify_benchmark_thin_adapter(adapter_receipt)
        if not adapter["benchmark_thin_adapter_pass"]:
            reasons.append("BENCHMARK_THIN_ADAPTER_FAIL")

    for key in REQUIRED_POLICY_PREMISES:
        if receipt.get(key) is not True:
            reasons.append(f"MISSING_POLICY_PREMISE:{key}")

    if receipt.get("explicit_shadow_reality_authority") is not True:
        reasons.append("EXPLICIT_SHADOW_REALITY_AUTHORITY_MISSING")

    if not _is_sha256(receipt.get("shadow_authority_receipt_sha256")):
        reasons.append("SHADOW_AUTHORITY_RECEIPT_SHA256_INVALID")
    if not _is_sha256(receipt.get("lease_nonce_sha256")):
        reasons.append("LEASE_NONCE_SHA256_INVALID")
    if not _nonempty(receipt.get("lease_id")):
        reasons.append("LEASE_ID_MISSING")
    if not _nonempty(receipt.get("benchmark_id")):
        reasons.append("BENCHMARK_ID_MISSING")
    if not _nonempty(receipt.get("escrow_sink_id")):
        reasons.append("ESCROW_SINK_ID_MISSING")

    if receipt.get("lease_consumed") is not False:
        reasons.append("LEASE_MUST_BE_UNCONSUMED_AT_ISSUANCE")
    if receipt.get("execution_ordinal") != 0:
        reasons.append("EXECUTION_ORDINAL_MUST_START_AT_ZERO")

    if receipt.get("acceptance_credit_before_fixed_point") is not False:
        reasons.append("ACCEPTANCE_CREDIT_BEFORE_FIXED_POINT_MUST_BE_FALSE")
    if receipt.get("promotion_before_fixed_point") is not False:
        reasons.append("PROMOTION_BEFORE_FIXED_POINT_MUST_BE_FALSE")
    if receipt.get("candidate_can_read_shadow_outputs") is not False:
        reasons.append("CANDIDATE_OUTPUT_VISIBILITY_MUST_BE_FALSE")
    if receipt.get("optimizer_can_read_shadow_outputs_before_release") is not False:
        reasons.append("OPTIMIZER_OUTPUT_VISIBILITY_MUST_BE_FALSE")

    ready = not reasons
    return {
        "schema": SCHEMA,
        "shadow_collection_ready": ready,
        "reasons": sorted(set(reasons)),
        "generic_isolation_kernel_pass": bool(
            isolation.get("generic_isolation_kernel_pass")
        ),
        "benchmark_thin_adapter_pass": bool(
            adapter.get("benchmark_thin_adapter_pass")
        ),
        "acceptance_credit_authorized": False,
        "terminal_execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_promotion_authority": False,
        "shadow_collection_authority_granted_by_this_module": False,
        "requires_separate_independent_shadow_authority": True,
    }


def verify_shadow_execution_result(
    lease_receipt: Mapping[str, Any],
    result_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify post-run escrow semantics without revealing or promoting score."""
    lease = verify_shadow_reality_lease(lease_receipt)
    reasons = [] if lease["shadow_collection_ready"] else ["LEASE_NOT_READY"]

    if result_receipt.get("lease_id") != lease_receipt.get("lease_id"):
        reasons.append("LEASE_ID_MISMATCH")
    if result_receipt.get("execution_count") != 1:
        reasons.append("ONE_USE_EXECUTION_COUNT_MUST_EQUAL_ONE")
    if result_receipt.get("lease_consumed_after_execution") is not True:
        reasons.append("LEASE_NOT_MARKED_CONSUMED")
    if result_receipt.get("result_content_addressed") is not True:
        reasons.append("RESULT_NOT_CONTENT_ADDRESSED")
    if not _is_sha256(result_receipt.get("result_sha256")):
        reasons.append("RESULT_SHA256_INVALID")
    if result_receipt.get("result_escrowed") is not True:
        reasons.append("RESULT_NOT_ESCROWED")
    if result_receipt.get("result_visible_to_candidate") is not False:
        reasons.append("RESULT_VISIBLE_TO_CANDIDATE")
    if result_receipt.get("result_visible_to_optimizer") is not False:
        reasons.append("RESULT_VISIBLE_TO_OPTIMIZER")
    if result_receipt.get("incremental_spend_usd") != 0:
        reasons.append("NONZERO_INCREMENTAL_SPEND")
    if result_receipt.get("acceptance_credit_delta") != 0:
        reasons.append("PREMATURE_ACCEPTANCE_CREDIT")
    if result_receipt.get("promotion_performed") is not False:
        reasons.append("PREMATURE_PROMOTION")

    passed = not reasons
    return {
        "schema": SCHEMA,
        "shadow_result_escrow_valid": passed,
        "reasons": sorted(set(reasons)),
        "score_release_authorized": False,
        "acceptance_credit_authorized": False,
        "promotion_authority": False,
    }


def makespan_bound(
    zero_reality_seconds: float, shadow_empirical_seconds: float
) -> dict[str, float]:
    """Compare serial and fully independent overlap critical-path bounds."""
    for value in (zero_reality_seconds, shadow_empirical_seconds):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("durations must be numeric")
        if value < 0:
            raise ValueError("durations must be >= 0")
    serial = zero_reality_seconds + shadow_empirical_seconds
    overlapped = max(zero_reality_seconds, shadow_empirical_seconds)
    saved = serial - overlapped
    ratio = (serial / overlapped) if overlapped > 0 else 1.0
    return {
        "serial_seconds": serial,
        "overlapped_seconds": overlapped,
        "maximum_structural_seconds_saved": saved,
        "structural_speedup_upper_bound": ratio,
    }
