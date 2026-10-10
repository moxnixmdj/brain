#!/usr/bin/env python3
"""Typed minimum certificate basis for the current 26 terminal predicates.

This module is fail-closed and scheduling/preproof only. It does not grant
execution, promotion, fresh-reality, family, capability, ownership, or
acceptance credit.

Purpose:
- collapse generic stronger-proof route explosion into the exact proof
  dimensions that remain causally necessary;
- make Root2 and Root3 obligations explicit and machine-checkable; and
- reject certificates that omit the dimension actually required by the
  frozen predicate classification.
"""
from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_TYPED_MINIMUM_CERTIFICATE_BASIS_V1"

COMPARATOR_STRENGTH = "COMPARATOR_STRENGTH"
SCOPE_COMPLETENESS = "SCOPE_COMPLETENESS"

ROOT2_ONLY = {
    "CODING_TB4_GE_66_4",
    "CODING_FRONTIERCODE_GE_54_4",
    "CODING_CURSORBENCH_GE_57_8",
    "PROWORK_GDPVAL_GE_1846",
    "PROWORK_AA_BRIEFCASE_GE_1822",
    "AUTOMATIONBENCH_GE_40",
    "HLE_TOOLS_GE_67_7",
    "TB_SCIENCE_GE_58_7",
    "CHARTOGRAPHY_TOOLS_GE_89",
    "OSWORLD_2_1_PARTIAL_GE_81_8",
    "FINANCE_ACCOUNTING_INDEX_GE_61",
    "FINANCE_AGENT_V2_GE_58_59",
    "LIVEBENCH_IF_GE_65_7",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
    "MYSTERYMECHANISM_GE_49_55",
    "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
}

ROOT3_ONLY = {
    "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
    "VISION_DENSE_NONCHART_SCOPE",
    "FINANCE_UNCOVERED_SCOPE_AUDIT",
    "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
    "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
    "COMPOSITION_COMPONENT_SCOPED_PROOFS",
    "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
}

ROOT2_AND_ROOT3 = {
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
    "IF_SCOPE_BOUNDARY_NONINFERIOR",
    "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
}

UNRESOLVED = ROOT2_ONLY | ROOT3_ONLY | ROOT2_AND_ROOT3

RELATIVE_ELO = {
    "PROWORK_GDPVAL_GE_1846",
    "PROWORK_AA_BRIEFCASE_GE_1822",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
}

PURE_ABSOLUTE_ROUTES = {
    "FORMAL_ENTAILMENT",
    "OBJECTIVE_CEILING_OR_FLOOR",
    "EXHAUSTIVE_FINITE_UNIVERSE",
    "SCOPE_SAFE_STRONGER_PROOF",
}

KNOWN_ROUTE_KINDS = PURE_ABSOLUTE_ROUTES | {
    "RELATIVE_SCORE_BRIDGE",
    "EXISTING_CONTENT_ADDRESSED_COMPARATOR_EVIDENCE",
    "OWNER_RESULT",
    "MATCHED_EMPIRICAL_COMPARISON",
    "ACCOUNT_OR_PROTOCOL_FACT",
    "SCOPE_CERTIFICATE",
    "UPSTREAM_SCOPE_RECEIPT",
}

FRESH_REALITY_ROUTES = {"MATCHED_EMPIRICAL_COMPARISON"}

ALLOWED_SCOPE_RELATIONS = {"EXACT", "SUPERSET"}


def _norm(x: Any) -> str:
    return " ".join(str(x or "").strip().split())


def _valid_sha256(x: Any) -> bool:
    s = _norm(x)
    return len(s) == 64 and all(c in "0123456789abcdefABCDEF" for c in s)


def required_dimensions(predicate_id: str) -> tuple[str, ...]:
    pid = _norm(predicate_id)
    if pid in ROOT2_ONLY:
        return (COMPARATOR_STRENGTH,)
    if pid in ROOT3_ONLY:
        return (SCOPE_COMPLETENESS,)
    if pid in ROOT2_AND_ROOT3:
        return (COMPARATOR_STRENGTH, SCOPE_COMPLETENESS)
    raise ValueError("UNKNOWN_OR_PROVED_PREDICATE")


def _obligation_id(predicate_id: str, dimension: str) -> str:
    raw = f"{predicate_id}\0{dimension}".encode()
    return "TCB1:" + hashlib.sha256(raw).hexdigest()[:24]


def compile_basis() -> dict[str, Any]:
    obligations = []
    for pid in sorted(UNRESOLVED):
        for dim in required_dimensions(pid):
            obligations.append(
                {
                    "obligation_id": _obligation_id(pid, dim),
                    "predicate_id": pid,
                    "dimension": dim,
                    "state": "OPEN",
                    "credit": 0,
                }
            )
    return {
        "schema": SCHEMA,
        "status": "COMPILED_CURRENT_26_TYPED_MINIMUM_CERTIFICATE_BASIS__ZERO_CREDIT",
        "predicate_count": len(UNRESOLVED),
        "root2_only_count": len(ROOT2_ONLY),
        "root3_only_count": len(ROOT3_ONLY),
        "root2_and_root3_count": len(ROOT2_AND_ROOT3),
        "typed_obligation_count": len(obligations),
        "obligations": obligations,
        "rule": (
            "A_PREDICATE_CAN_CLOSE_ONLY_IF_EVERY_REQUIRED_DIMENSION_HAS_AN_"
            "INDEPENDENTLY_VERIFIED_PREDICATE_SPECIFIC_CERTIFICATE_OR_AN_"
            "ALREADY_ADMISSIBLE_RECEIPT"
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_authorized": False,
    }


def route_admissible(
    predicate_id: str,
    route_kind: str,
    *,
    explicit_relative_score_bridge: bool = False,
    fresh_reality_authorized: bool = False,
) -> tuple[bool, str]:
    pid = _norm(predicate_id)
    route = _norm(route_kind).upper()
    if pid not in UNRESOLVED:
        raise ValueError("UNKNOWN_OR_PROVED_PREDICATE")
    if route not in KNOWN_ROUTE_KINDS:
        raise ValueError("UNKNOWN_ROUTE_KIND")
    if (
        pid in RELATIVE_ELO
        and route in PURE_ABSOLUTE_ROUTES
        and not explicit_relative_score_bridge
    ):
        return False, "PURE_ABSOLUTE_ROUTE_CANNOT_TRANSPORT_TO_FIXED_RELATIVE_ELO"
    if route in FRESH_REALITY_ROUTES and not fresh_reality_authorized:
        return False, "FRESH_REALITY_CURRENTLY_NOT_AUTHORIZED"
    return True, "ADMISSIBLE_CANDIDATE_ONLY"


def check_typed_certificate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Mechanical typed gate. This is not a semantic theorem prover."""
    reasons: list[str] = []
    pid = _norm(candidate.get("target_predicate"))
    if pid not in UNRESOLVED:
        reasons.append("UNKNOWN_OR_PROVED_TARGET_PREDICATE")
        required: tuple[str, ...] = ()
    else:
        required = required_dimensions(pid)

    dims_raw: Sequence[Any] = candidate.get("proved_dimensions") or ()
    dims = {_norm(x).upper() for x in dims_raw}
    for dim in required:
        if dim not in dims:
            reasons.append(f"MISSING_REQUIRED_DIMENSION:{dim}")

    if not _valid_sha256(candidate.get("target_contract_sha256")):
        reasons.append("INVALID_OR_MISSING_TARGET_CONTRACT_SHA256")
    if candidate.get("semantic_implication_proved") is not True:
        reasons.append("SEMANTIC_IMPLICATION_NOT_PROVED")
    if candidate.get("independent_verification_pass") is not True:
        reasons.append("INDEPENDENT_VERIFICATION_NOT_BOUND")
    if candidate.get("source_content_addressed") is not True:
        reasons.append("SOURCE_NOT_CONTENT_ADDRESSED")

    if COMPARATOR_STRENGTH in required:
        if candidate.get("metric_threshold_implication_proved") is not True:
            reasons.append("COMPARATOR_METRIC_THRESHOLD_IMPLICATION_NOT_PROVED")

    if SCOPE_COMPLETENESS in required:
        scope = _norm(candidate.get("scope_relation")).upper()
        if scope not in ALLOWED_SCOPE_RELATIONS:
            reasons.append("SCOPE_RELATION_MUST_BE_EXACT_OR_SUPERSET")
        if candidate.get("scope_completeness_proved") is not True:
            reasons.append("SCOPE_COMPLETENESS_NOT_PROVED")

    route = _norm(candidate.get("route_kind")).upper()
    if route:
        try:
            admissible, route_reason = route_admissible(
                pid,
                route,
                explicit_relative_score_bridge=bool(
                    candidate.get("explicit_relative_score_bridge")
                ),
                fresh_reality_authorized=bool(
                    candidate.get("fresh_reality_authorized")
                ),
            )
            if not admissible:
                reasons.append(route_reason)
        except ValueError as exc:
            reasons.append(str(exc))

    complete = not reasons
    return {
        "schema": SCHEMA,
        "target_predicate": pid,
        "required_dimensions": list(required),
        "typed_certificate_mechanically_complete": complete,
        "reasons": reasons,
        "acceptance_credit_authorized": False,
        "requires_separate_predicate_specific_activation": True,
    }


def current_counts_are_exact() -> bool:
    return (
        len(ROOT2_ONLY) == 16
        and len(ROOT3_ONLY) == 7
        and len(ROOT2_AND_ROOT3) == 3
        and len(UNRESOLVED) == 26
        and len(compile_basis()["obligations"]) == 29
    )
