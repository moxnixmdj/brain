"""Deterministic aggregation for the frozen synthesis matched-quality metric.

This module does NOT score raw synthesis artifacts. It freezes only the aggregation
semantics for already-normalized, independently bound dimension scores.

The frozen acceptance protocol keeps required-claim coverage as a separate metric.
The quality aggregate is deliberately non-compensatory: a strong dimension cannot
hide a weak one.
"""
from __future__ import annotations

import math
from numbers import Real
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_SYNTHESIS_MATCHED_QUALITY_METRIC_V1"

QUALITY_COMPONENTS = (
    "claim_to_source_fidelity",
    "uncertainty_and_disagreement_preservation",
    "audience_adaptation",
    "format_and_style_constraints",
    "compression_without_decision_relevant_loss",
)

def _normalized_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError("NON_NUMERIC_COMPONENT")
    x = float(value)
    if not math.isfinite(x):
        raise ValueError("NONFINITE_COMPONENT")
    if not 0.0 <= x <= 1.0:
        raise ValueError("COMPONENT_OUT_OF_RANGE")
    return x

def aggregate(
    components: Mapping[str, Any],
    *,
    unsupported_material_claims: int = 0,
) -> dict[str, Any]:
    """Return the frozen case-level synthesis matched-quality aggregate.

    Preconditions:
    - exactly the five frozen non-coverage quality dimensions are supplied;
    - each component is normalized to [0, 1] by a separately frozen scorer;
    - required_claim_coverage is scored separately and is not accepted here.

    Rule:
    - any unsupported material claim hard-zeros quality;
    - otherwise matched_quality is the minimum component score.

    This function creates no comparator result and no acceptance credit.
    """
    if not isinstance(components, Mapping):
        raise ValueError("COMPONENTS_NOT_MAPPING")

    got = set(components)
    expected = set(QUALITY_COMPONENTS)
    if got != expected:
        missing = sorted(expected - got)
        extra = sorted(got - expected)
        raise ValueError(f"COMPONENT_SET_MISMATCH:missing={missing}:extra={extra}")

    if isinstance(unsupported_material_claims, bool) or not isinstance(unsupported_material_claims, int):
        raise ValueError("UNSUPPORTED_CLAIM_COUNT_NOT_INT")
    if unsupported_material_claims < 0:
        raise ValueError("UNSUPPORTED_CLAIM_COUNT_NEGATIVE")

    normalized = {k: _normalized_number(components[k]) for k in QUALITY_COMPONENTS}

    if unsupported_material_claims > 0:
        score = 0.0
        reason = "UNSUPPORTED_MATERIAL_CLAIM_HARD_ZERO"
    else:
        score = min(normalized.values())
        reason = "MINIMUM_FROZEN_QUALITY_DIMENSION"

    return {
        "schema": SCHEMA,
        "valid": True,
        "matched_quality": score,
        "aggregation": "MIN_NONCOMPENSATORY",
        "quality_components": normalized,
        "unsupported_material_claims": unsupported_material_claims,
        "required_claim_coverage_included": False,
        "reason": reason,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
