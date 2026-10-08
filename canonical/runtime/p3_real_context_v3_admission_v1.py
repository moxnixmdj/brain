"""P3 real-context to synthesis-V3 sound admission bridge v1.

The verified synthesis V3 policy already proves ceiling performance for contexts
inside its explicit contract. This bridge does not reinterpret that contract.
It only checks the remaining real-context admission seam:

  * the concrete V3 runtime itself passes;
  * an independently checked semantic truth certificate proves that the supplied
    required-uncertainty set is complete for this context; and
  * an independently checked semantic truth certificate proves that no additional
    load-bearing semantic requirement lies outside the V3 contract.

Anything unproved stays UNKNOWN and cannot be admitted.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import synthesis_certified_visible_support_policy_v3 as v3

SCHEMA = "PROJECT_BRAIN_P3_REAL_CONTEXT_V3_ADMISSION_V1"

REQUIRED_CERTIFICATES = (
    "REQUIRED_UNCERTAINTY_SET_COMPLETE",
    "NO_LOAD_BEARING_SEMANTICS_OUTSIDE_V3",
)


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


def _certificate_truth(value: Any, *, predicate_id: str) -> tuple[bool, str]:
    if not isinstance(value, Mapping):
        return False, "CERTIFICATE_MAPPING_REQUIRED"
    if value.get("predicate_id") != predicate_id:
        return False, "CERTIFICATE_PREDICATE_ID_MISMATCH"
    if value.get("truthful_precommitment_observation") is not True:
        return False, "TRUTHFUL_PRECOMMITMENT_OBSERVATION_REQUIRED"
    if value.get("pass") is not True:
        return False, "CERTIFICATE_PASS_REQUIRED"
    if value.get("predicate_truth") != "TRUE":
        return False, "PREDICATE_NOT_PROVED_TRUE"
    # Semantic truth is deliberately not adequacy.
    if value.get("policy_adequacy_authority") is not False:
        return False, "CERTIFICATE_AUTHORITY_BOUNDARY_INVALID"
    if value.get("terminal_authority") is not False:
        return False, "CERTIFICATE_TERMINAL_AUTHORITY_INVALID"
    return True, "PASS"


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")

    context_id = payload.get("context_id")
    if not isinstance(context_id, str) or not context_id.strip():
        return _fail("CONTEXT_ID_REQUIRED")

    v3_input = payload.get("v3_input")
    if not isinstance(v3_input, Mapping):
        return _fail("V3_INPUT_REQUIRED")

    semantic_certificates = payload.get("semantic_certificates")
    if not isinstance(semantic_certificates, Mapping):
        return _fail("SEMANTIC_CERTIFICATES_REQUIRED")

    unresolved = []
    certificate_audit = {}
    for predicate_id in REQUIRED_CERTIFICATES:
        ok, reason = _certificate_truth(
            semantic_certificates.get(predicate_id),
            predicate_id=predicate_id,
        )
        certificate_audit[predicate_id] = {"pass": ok, "reason": reason}
        if not ok:
            unresolved.append(predicate_id)

    # Run the actual verified V3 implementation. Certificates may never bypass a
    # mechanical V3 failure.
    v3_result = v3.solve(v3_input)
    if v3_result.get("status") != "PASS":
        return {
            **_fail(
                "V3_RUNTIME_FAIL_CLOSED",
                context_id=context_id,
                unresolved_semantic_predicates=sorted(unresolved),
                v3_result=v3_result,
            ),
            "certificate_audit": certificate_audit,
        }

    audit = v3_result.get("audit") or {}
    required_v3_audit = {
        "all_selected_claims_supported": True,
        "all_claim_evidence_relations_resolved": True,
        "all_selected_detected_conflicts_rendered": True,
        "all_required_uncertainty_preserved": True,
        "all_rendered_items_provenance_bound": True,
        "audience_profile_applied": True,
        "exact_complete_item_order_applied": True,
    }
    failed_audit = [
        name for name, expected in required_v3_audit.items()
        if audit.get(name) is not expected
    ]
    if audit.get("dropped_material_item_count") != 0:
        failed_audit.append("dropped_material_item_count")
    if audit.get("new_material_claim_count") != 0:
        failed_audit.append("new_material_claim_count")
    if failed_audit:
        return _fail(
            "V3_AUDIT_INCOMPLETE",
            context_id=context_id,
            failed_audit=sorted(set(failed_audit)),
            v3_result=v3_result,
        )

    if unresolved:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "UNKNOWN__SEMANTIC_ADMISSION_INCOMPLETE",
            "context_id": context_id,
            "unresolved_semantic_predicates": sorted(unresolved),
            "certificate_audit": certificate_audit,
            "v3_runtime_pass": True,
            "v3_result": v3_result,
            "v3_admission_authorized": False,
            "top_law_eligible": False,
            "policy_adequacy_authority": False,
            "db_admission_authority": False,
            "u_subtraction_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "next_action": (
                "PROVE_ONLY_THE_LISTED_SELECTED_SEMANTIC_PREDICATES_WITH_"
                "SOURCE_ALIGNED_TRUTH_CERTIFICATES_OR_USE_A_STRONGER_DIRECT_E2E_ROUTE"
            ),
        }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__P3_REAL_CONTEXT_SOUNDLY_ADMITTED_TO_SYNTHESIS_V3",
        "context_id": context_id,
        "unresolved_semantic_predicates": [],
        "certificate_audit": certificate_audit,
        "v3_runtime_pass": True,
        "v3_result": v3_result,
        "v3_admission_authorized": True,
        "top_law_eligible": True,
        # This bridge establishes membership only. The separately verified V3
        # top-law is still the adequacy certificate.
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "REAL_CONTEXT_MEMBERSHIP_ONLY__SYNTHESIS_V3_TOP_LAW_MUST_BE_BOUND_"
            "SEPARATELY_FOR_ADEQUACY_AND_EXISTING_D_B_ADMISSION_MUST_PROMOTE"
        ),
    }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return evaluate(args or {})
