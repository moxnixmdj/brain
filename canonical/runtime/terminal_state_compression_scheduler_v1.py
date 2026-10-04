#!/usr/bin/env python3
"""Fail-closed state-compression scheduler and shadow-reality lease gate.

This module is scheduling/governance preproof only. It grants no execution,
fresh-reality, promotion, family, capability, ownership, or acceptance credit.

It addresses two failure modes:
1. ranking decisive probes by probability of success even when success
   probability is uncalibrated but every outcome compresses the state space;
2. globally serializing all empirical collection behind unrelated zero-reality
   work when a separately authorized, precommitted, escrowed shadow run could
   be causally isolated.

Shadow collection remains blocked unless an explicit independent shadow-reality
authority receipt is bound. This module cannot create that authority.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TERMINAL_STATE_COMPRESSION_SCHEDULER_V1"

REQUIRED_SHADOW_PREMISES = (
    "generic_isolation_kernel_pass",
    "benchmark_thin_adapter_pass",
    "candidate_frozen",
    "executor_independent",
    "executed_hashes_equal_precommit",
    "outputs_bound_to_precommit",
    "outputs_escrowed",
    "outputs_hidden_from_candidate",
    "unrelated_work_cannot_mutate_candidate",
    "zero_incremental_spend_guard",
    "route_result_not_used_for_acceptance_before_fixed_point",
)


def robust_state_compression_priority(
    *,
    guaranteed_progress: float,
    guaranteed_deletion: float,
    guaranteed_information: float,
    critical_path_seconds: float,
    correlation_penalty: float = 0.0,
    calibrated_expected_closure: float = 0.0,
) -> float:
    """Priority without inventing a point success probability."""
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
    """Preserve unknown probability rather than inventing a point estimate."""
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
    """Check a proposed per-route shadow-collection lease."""
    missing = [k for k in REQUIRED_SHADOW_PREMISES if receipt.get(k) is not True]

    authority = receipt.get("explicit_shadow_reality_authority") is True
    if not authority:
        missing.append("explicit_shadow_reality_authority")

    if receipt.get("acceptance_credit_before_fixed_point") is True:
        missing.append("acceptance_credit_before_fixed_point_must_be_false")
    if receipt.get("promotion_before_fixed_point") is True:
        missing.append("promotion_before_fixed_point_must_be_false")
    if receipt.get("candidate_can_read_shadow_outputs") is True:
        missing.append("candidate_can_read_shadow_outputs_must_be_false")

    ready = not missing
    return {
        "schema": SCHEMA,
        "shadow_collection_ready": ready,
        "missing": sorted(set(missing)),
        "acceptance_credit_authorized": False,
        "promotion_authority": False,
        "fresh_reality_authority_granted_by_this_module": False,
        "requires_separate_independent_shadow_authority": True,
    }


def makespan_bound(zero_reality_seconds: float, shadow_empirical_seconds: float) -> dict[str, float]:
    """Compare serial and fully independent shadow-overlap critical-path bounds."""
    for value in (zero_reality_seconds, shadow_empirical_seconds):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("durations must be numeric")
        if value < 0:
            raise ValueError("durations must be >= 0")
    serial = zero_reality_seconds + shadow_empirical_seconds
    overlapped = max(zero_reality_seconds, shadow_empirical_seconds)
    saved = serial - overlapped
    return {
        "serial_seconds": serial,
        "overlapped_lower_bound_seconds": overlapped,
        "maximum_structural_seconds_saved": saved,
    }
