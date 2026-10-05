from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_SYNTHESIS_CAUSAL_CEILING_REDUCER_V1"

QUALITY_COMPONENTS = (
    "claim_to_source_fidelity",
    "uncertainty_and_disagreement_preservation",
    "audience_adaptation",
    "format_and_style_constraints",
    "compression_without_decision_relevant_loss",
)

REQUIRED_PREMISES = {
    "claim_to_source_fidelity": frozenset({
        "C0_ALL_MATERIAL_CLAIMS_HAVE_VALID_SUPPORT",
        "C0_ALL_MATERIAL_CLAIMS_HAVE_NONEMPTY_PROVENANCE",
        "C2_NO_NEW_MATERIAL_CLAIMS",
        "C2_PROVENANCE_SURVIVES_TO_REALIZED_MATERIAL_CLAIMS",
    }),
    "uncertainty_and_disagreement_preservation": frozenset({
        "C0_ALL_REQUIRED_UNCERTAINTY_AND_DISAGREEMENT_UNITS_IDENTIFIED",
        "C2_ALL_REQUIRED_UNCERTAINTY_AND_DISAGREEMENT_UNITS_REALIZED",
    }),
    "audience_adaptation": frozenset({
        "C1_ALL_EXPLICIT_AUDIENCE_REQUIREMENTS_ADMITTED_OR_SATISFIED",
        "C2_ALL_EXPLICIT_AUDIENCE_REQUIREMENTS_REALIZED",
    }),
    "format_and_style_constraints": frozenset({
        "C2_ALL_EXPLICIT_FORMAT_STYLE_CONSTRAINTS_REALIZED",
    }),
    "compression_without_decision_relevant_loss": frozenset({
        "C1_ALL_REQUIRED_DECISION_RELEVANT_UNITS_SELECTED",
        "C2_NO_SELECTED_DECISION_RELEVANT_UNIT_DROPPED",
        "C2_OUTPUT_BUDGET_PASS",
    }),
}

UNSUPPORTED_ZERO_PREMISES = frozenset({
    "C0_ALL_MATERIAL_CLAIMS_HAVE_VALID_SUPPORT",
    "C2_NO_NEW_MATERIAL_CLAIMS",
})


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "acceptance_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def reduce_ceiling(certificate: Any) -> dict[str, Any]:
    """Compose verified C0/C1/C2 postconditions into the frozen quality ceiling.

    This function proves no semantic premise itself. It is deliberately a
    fail-closed logical reducer over a separately verified, scope-complete
    premise certificate.
    """
    if not isinstance(certificate, Mapping):
        return _fail("CERTIFICATE_NOT_MAPPING")
    expected_fields = {"scope_complete", "independent_or_objective", "premises"}
    if set(certificate) != expected_fields:
        return _fail("CERTIFICATE_FIELDS_MISMATCH")
    if certificate.get("scope_complete") is not True:
        return _fail("SCOPE_NOT_COMPLETE")
    if certificate.get("independent_or_objective") is not True:
        return _fail("INDEPENDENCE_NOT_ESTABLISHED")

    premises = certificate.get("premises")
    if not isinstance(premises, list):
        return _fail("PREMISES_NOT_LIST")
    if any(not isinstance(p, str) or not p or p != p.strip() for p in premises):
        return _fail("PREMISE_INVALID")
    if len(premises) != len(set(premises)):
        return _fail("PREMISE_DUPLICATE")

    known = set().union(*REQUIRED_PREMISES.values(), UNSUPPORTED_ZERO_PREMISES)
    unknown = sorted(set(premises) - known)
    if unknown:
        return _fail("UNKNOWN_PREMISE:" + ",".join(unknown))

    have = set(premises)
    missing_by_component = {
        component: sorted(required - have)
        for component, required in REQUIRED_PREMISES.items()
    }
    component_ceiling = {
        component: 1.0 if not missing else None
        for component, missing in missing_by_component.items()
    }
    unsupported_zero = UNSUPPORTED_ZERO_PREMISES <= have
    all_components_one = all(v == 1.0 for v in component_ceiling.values())
    matched_quality = 1.0 if all_components_one and unsupported_zero else None
    missing_union = sorted(
        set().union(
            *(set(v) for v in missing_by_component.values()),
            UNSUPPORTED_ZERO_PREMISES - have,
        )
    )

    return {
        "schema": SCHEMA,
        "status": "CEILING_PROVED" if matched_quality == 1.0 else "OPEN",
        "component_ceiling": component_ceiling,
        "unsupported_material_claim_count": 0 if unsupported_zero else None,
        "matched_quality": matched_quality,
        "missing_by_component": missing_by_component,
        "missing_premises": missing_union,
        "scope_complete": True,
        "independent_or_objective": True,
        "acceptance_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
