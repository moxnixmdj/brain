#!/usr/bin/env python3
"""Causal subtype guard for positive Root1 operational gaps.

A system-level acceptance failure proves that an operative system is insufficient.
It does not, by itself, prove that the underlying useful capability mechanism is
missing. This guard keeps route/composition failures on integration repair and
authorizes underlying-capability acquisition only after a valid execution route
actually exercises the target behavior and independent semantic adjudication
attributes failure to that behavior.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ROOT1_CAUSAL_SUBTYPE_GUARD_V1"


class Root1CausalSubtypeError(ValueError):
    pass


def _nonneg_int(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise Root1CausalSubtypeError(name + "_INVALID")
    try:
        result = int(value)
    except Exception as exc:
        raise Root1CausalSubtypeError(name + "_INVALID") from exc
    if result < 0:
        raise Root1CausalSubtypeError(name + "_INVALID")
    return result


def _base(status: str, *, operational_gap: bool, reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "root1_operational_gap": operational_gap,
        "underlying_capability_acquisition_authorized": False,
        "integration_repair_authorized": False,
        "reason": reason,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "fresh_reality_authority": False,
        "promotion_authority": False,
    }


def classify_root1_causal_subtype(
    evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Classify what a positive operational gap actually proves.

    Fail closed. Underlying capability acquisition is authorized only when:
      * a valid candidate response reached the target behavior;
      * the execution surface was independently verified ready;
      * semantic acceptance was independent;
      * at least one semantic failure was observed; and
      * causal attribution binds that failure to the underlying behavior.

    Route/policy/composition failures with zero valid candidate responses are
    operative-system gaps, but not evidence of a missing underlying capability.
    """
    if not isinstance(evidence, Mapping):
        return _base(
            "ROOT1_SUBTYPE_UNPROVED_FAIL_CLOSED",
            operational_gap=False,
            reason="EVIDENCE_MAPPING_REQUIRED",
        )

    if (
        evidence.get("positive_operational_gap") is not True
        or evidence.get("operative_failure_demonstrated") is not True
    ):
        return _base(
            "ROOT1_SUBTYPE_UNPROVED_FAIL_CLOSED",
            operational_gap=False,
            reason="POSITIVE_OPERATIVE_GAP_NOT_ESTABLISHED",
        )

    valid = _nonneg_int(
        evidence.get("valid_candidate_response_count", 0),
        "VALID_CANDIDATE_RESPONSE_COUNT",
    )
    policy = _nonneg_int(
        evidence.get("policy_block_count", 0),
        "POLICY_BLOCK_COUNT",
    )
    route = _nonneg_int(
        evidence.get("runtime_or_composition_failure_count", 0),
        "RUNTIME_OR_COMPOSITION_FAILURE_COUNT",
    )
    semantic_fail = _nonneg_int(
        evidence.get("independently_adjudicated_semantic_failure_count", 0),
        "INDEPENDENTLY_ADJUDICATED_SEMANTIC_FAILURE_COUNT",
    )
    observed = _nonneg_int(
        evidence.get("observed_case_count", valid + policy + route),
        "OBSERVED_CASE_COUNT",
    )

    if valid + policy + route > observed:
        raise Root1CausalSubtypeError("COUNTS_EXCEED_OBSERVED_CASE_COUNT")
    if semantic_fail > valid:
        raise Root1CausalSubtypeError("SEMANTIC_FAILURES_EXCEED_VALID_RESPONSES")

    counts = {
        "observed_case_count": observed,
        "valid_candidate_response_count": valid,
        "policy_block_count": policy,
        "runtime_or_composition_failure_count": route,
        "independently_adjudicated_semantic_failure_count": semantic_fail,
    }

    if valid == 0 and (policy + route) > 0 and semantic_fail == 0:
        out = _base(
            "ROOT1_OPERATIVE_ROUTE_GAP_ONLY",
            operational_gap=True,
            reason="NO_VALID_CANDIDATE_RESPONSE_REACHED_SEMANTIC_ADJUDICATION",
        )
        out.update({
            "causal_subtype": "OPERATIVE_ROUTE_OR_COMPOSITION_GAP",
            "integration_repair_authorized": True,
            "counts": counts,
            "hard_rule": (
                "SYSTEM_LEVEL_ACCEPTANCE_FAILURE_IS_NOT_PROOF_OF_MISSING_"
                "UNDERLYING_USEFUL_CAPABILITY"
            ),
        })
        return out

    semantic_gate = all((
        evidence.get("underlying_behavior_exercised") is True,
        evidence.get("independent_semantic_acceptance") is True,
        evidence.get("execution_surface_verified_ready") is True,
        evidence.get("failure_attributed_to_underlying_behavior") is True,
    ))
    if valid > 0 and semantic_fail > 0 and semantic_gate:
        out = _base(
            "ROOT1_UNDERLYING_CAPABILITY_GAP_ESTABLISHED",
            operational_gap=True,
            reason=(
                "VALID_ROUTE_REACHED_INDEPENDENT_SEMANTIC_ADJUDICATION_"
                "AND_FAILED_UNDERLYING_BEHAVIOR"
            ),
        )
        out.update({
            "causal_subtype": "UNDERLYING_USEFUL_CAPABILITY_GAP",
            "underlying_capability_acquisition_authorized": True,
            "counts": counts,
        })
        return out

    out = _base(
        "ROOT1_SUBTYPE_UNPROVED_FAIL_CLOSED",
        operational_gap=True,
        reason=(
            "EVIDENCE_DOES_NOT_CAUSALLY_DISTINGUISH_ROUTE_FAILURE_FROM_"
            "UNDERLYING_CAPABILITY_FAILURE"
        ),
    )
    out.update({
        "causal_subtype": "UNRESOLVED",
        "counts": counts,
    })
    return out


def livebench_v6_current_projection() -> dict[str, Any]:
    """Project only the already-canonical sanitized 72-case aggregate."""
    return classify_root1_causal_subtype({
        "positive_operational_gap": True,
        "operative_failure_demonstrated": True,
        "observed_case_count": 72,
        "valid_candidate_response_count": 0,
        "policy_block_count": 43,
        "runtime_or_composition_failure_count": 29,
        "independently_adjudicated_semantic_failure_count": 0,
    })


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return classify_root1_causal_subtype(args or {})
