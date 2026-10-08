"""P3 real-context to synthesis-V3 sound admission bridge v2.

V2 removes the broad negative premise "no load-bearing semantics outside V3".
The independently verified P3 scope certificate proves the load-bearing scope is
the exact union of six dimensions. Three are discharged mechanically by the V3
runtime; the three genuinely semantic context bindings remain explicit selected
truth certificates.

This module proves membership only. Adequacy comes from the separately verified
V3 top-law and promotion remains with existing fail-closed D_B admission.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import synthesis_certified_visible_support_policy_v3 as v3

SCHEMA = "PROJECT_BRAIN_P3_REAL_CONTEXT_V3_ADMISSION_V2"

SEMANTIC_CERTIFICATES = (
    "REQUIRED_UNCERTAINTY_SET_COMPLETE",
    "SELECTION_AND_ORDER_DECISION_RELEVANCE_COMPLETE",
    "AUDIENCE_FORMAT_PROFILE_COMPLETE",
)

MECHANICAL_DIMENSIONS = (
    "CLAIM_TO_SOURCE_FIDELITY",
    "REQUIRED_EVIDENCE_COVERAGE",
    "COMPRESSION_WITHOUT_DECISION_RELEVANT_LOSS",
)

SEMANTIC_DIMENSIONS = {
    "REQUIRED_UNCERTAINTY_SET_COMPLETE": "UNCERTAINTY_DISAGREEMENT_PRESERVATION",
    "SELECTION_AND_ORDER_DECISION_RELEVANCE_COMPLETE": "COMPRESSION_WITHOUT_DECISION_RELEVANT_LOSS",
    "AUDIENCE_FORMAT_PROFILE_COMPLETE": "AUDIENCE_ADAPTATION_AND_FORMAT_STYLE",
}


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "v3_admission_authorized": False,
        "top_law_eligible": False,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _truth_certificate(value: Any, predicate_id: str) -> tuple[bool, str]:
    if not isinstance(value, Mapping):
        return False, "CERTIFICATE_MAPPING_REQUIRED"
    if value.get("predicate_id") != predicate_id:
        return False, "CERTIFICATE_PREDICATE_ID_MISMATCH"
    if value.get("pass") is not True:
        return False, "CERTIFICATE_PASS_REQUIRED"
    if value.get("predicate_truth") != "TRUE":
        return False, "PREDICATE_NOT_PROVED_TRUE"
    if value.get("truthful_precommitment_observation") is not True:
        return False, "TRUTHFUL_PRECOMMITMENT_OBSERVATION_REQUIRED"
    if value.get("policy_adequacy_authority") is not False:
        return False, "SEMANTIC_CERTIFICATE_MUST_NOT_SELF_CERTIFY_ADEQUACY"
    if value.get("terminal_authority") is not False:
        return False, "SEMANTIC_CERTIFICATE_TERMINAL_AUTHORITY_INVALID"
    # Caller-supplied certificate flags are not independently recomputed
    # evidence of this quantified semantic completeness proposition.
    # Fail closed until a trusted source-bound semantic proof verifier exists.
    return False, "SELECTED_SEMANTIC_COMPLETENESS_NOT_RECOMPUTED"


def _v3_mechanical_audit(result: Mapping[str, Any]) -> tuple[bool, list[str]]:
    audit = result.get("audit") or {}
    required_true = (
        "all_selected_claims_supported",
        "all_claim_evidence_relations_resolved",
        "all_selected_detected_conflicts_rendered",
        "all_required_uncertainty_preserved",
        "all_rendered_items_provenance_bound",
        "audience_profile_applied",
        "exact_complete_item_order_applied",
    )
    failures = [name for name in required_true if audit.get(name) is not True]
    if audit.get("dropped_material_item_count") != 0:
        failures.append("dropped_material_item_count")
    if audit.get("new_material_claim_count") != 0:
        failures.append("new_material_claim_count")
    return not failures, sorted(set(failures))


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")

    context_id = payload.get("context_id")
    if not isinstance(context_id, str) or not context_id.strip():
        return _fail("CONTEXT_ID_REQUIRED")

    v3_input = payload.get("v3_input")
    if not isinstance(v3_input, Mapping):
        return _fail("V3_INPUT_REQUIRED")

    certs = payload.get("semantic_certificates")
    if not isinstance(certs, Mapping):
        return _fail("SEMANTIC_CERTIFICATES_REQUIRED")

    cert_audit: dict[str, dict[str, Any]] = {}
    unresolved = []
    for predicate_id in SEMANTIC_CERTIFICATES:
        ok, reason = _truth_certificate(certs.get(predicate_id), predicate_id)
        cert_audit[predicate_id] = {
            "pass": ok,
            "reason": reason,
            "scope_dimension": SEMANTIC_DIMENSIONS[predicate_id],
        }
        if not ok:
            unresolved.append(predicate_id)

    result = v3.solve(v3_input)
    if result.get("status") != "PASS":
        return {
            **_fail(
                "V3_RUNTIME_FAIL_CLOSED",
                context_id=context_id,
                unresolved_semantic_predicates=sorted(unresolved),
                v3_result=result,
            ),
            "certificate_audit": cert_audit,
        }

    mechanical_ok, failed_mechanical = _v3_mechanical_audit(result)
    if not mechanical_ok:
        return {
            **_fail(
                "V3_MECHANICAL_DIMENSION_AUDIT_FAILED",
                context_id=context_id,
                failed_mechanical_predicates=failed_mechanical,
                v3_result=result,
            ),
            "certificate_audit": cert_audit,
        }

    dimension_audit = {
        "CLAIM_TO_SOURCE_FIDELITY": {
            "pass": True,
            "basis": "V3_ALL_SELECTED_CLAIMS_SUPPORTED__RELATIONS_RESOLVED__PROVENANCE_BOUND__ZERO_NEW_MATERIAL_CLAIMS",
        },
        "REQUIRED_EVIDENCE_COVERAGE": {
            "pass": True,
            "basis": "V2_REQUIRED_CLAIMS_CANNOT_BE_EXCLUDED__V3_SELECTED_SUPPORT_AUDIT_PASS",
        },
        "UNCERTAINTY_DISAGREEMENT_PRESERVATION": {
            "pass": "REQUIRED_UNCERTAINTY_SET_COMPLETE" not in unresolved,
            "basis": "TRUTH_CERTIFICATE_PLUS_V3_ALL_REQUIRED_UNCERTAINTY_PRESERVED",
        },
        "AUDIENCE_ADAPTATION": {
            "pass": "AUDIENCE_FORMAT_PROFILE_COMPLETE" not in unresolved,
            "basis": "TRUTH_CERTIFICATE_PLUS_V3_AUDIENCE_PROFILE_APPLIED",
        },
        "FORMAT_STYLE_CONSTRAINTS": {
            "pass": "AUDIENCE_FORMAT_PROFILE_COMPLETE" not in unresolved,
            "basis": "TRUTH_CERTIFICATE_PLUS_GROUNDED_REALIZER_FAIL_CLOSED_CONSTRAINT_EXECUTION",
        },
        "COMPRESSION_WITHOUT_DECISION_RELEVANT_LOSS": {
            "pass": "SELECTION_AND_ORDER_DECISION_RELEVANCE_COMPLETE" not in unresolved,
            "basis": "TRUTH_CERTIFICATE_PLUS_ZERO_DROPPED_MATERIAL_ITEMS_AND_EXACT_ITEM_ORDER",
        },
    }

    if unresolved:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "UNKNOWN__FINITE_P3_CONTEXT_SEMANTIC_BINDINGS_INCOMPLETE",
            "context_id": context_id,
            "unresolved_semantic_predicates": sorted(unresolved),
            "certificate_audit": cert_audit,
            "dimension_audit": dimension_audit,
            "v3_runtime_pass": True,
            "v3_admission_authorized": False,
            "top_law_eligible": False,
            "policy_adequacy_authority": False,
            "db_admission_authority": False,
            "u_subtraction_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "next_action": (
                "PROVE_ONLY_THE_LISTED_POLICY_CHANGING_PREDICATES_WITH_"
                "SELECTED_SEMANTIC_TRUTH_CERTIFICATES_OR_USE_A_STRONGER_DIRECT_E2E_CERTIFICATE"
            ),
        }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__P3_REAL_CONTEXT_SOUNDLY_ADMITTED_TO_SYNTHESIS_V3_V2",
        "context_id": context_id,
        "unresolved_semantic_predicates": [],
        "certificate_audit": cert_audit,
        "dimension_audit": dimension_audit,
        "six_dimension_coverage_complete": all(x["pass"] for x in dimension_audit.values()),
        "v3_runtime_pass": True,
        "v3_admission_authorized": True,
        "top_law_eligible": True,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "FINITE_SIX_DIMENSION_MEMBERSHIP_ONLY__NO_OPEN_ENDED_NEGATIVE_SEMANTIC_PREMISE__"
            "SEPARATE_VERIFIED_V3_TOP_LAW_SUPPLIES_ADEQUACY_AND_EXISTING_D_B_ADMISSION_PROMOTES"
        ),
    }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return evaluate(args or {})
