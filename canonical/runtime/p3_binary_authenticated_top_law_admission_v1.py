"""Authenticated strict P3 binary top-law admission through robust CEGAR.

This adapter is the real positive leaf for the strict explicit P3 binary class:
raw upstream root bytes are recomputed by the strict membership compiler, then
the resulting membership atom is injected as a trusted constraint into the
existing robust policy-adequacy CEGAR kernel. The policy condition is backed by
the independently verified normalized top-law adequacy certificate.

No caller semantic constraint, policy condition, verifier binding, or policy ID
is accepted.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.p3_binary_explicit_contract_membership_v1 import compile_membership
from canonical.runtime.p3_robust_policy_adequacy_cegar_v1 import solve as solve_cegar

SCHEMA = "PROJECT_BRAIN_P3_BINARY_AUTHENTICATED_TOP_LAW_ADMISSION_V1"
POLICY_ID = "P3_BOUND_BINARY_GROUNDED_DECISION_TOP_LAW_POLICY_V1"
CONDITION = {"op": "ATOM", "id": "P3_BOUND_BINARY_EXPLICIT_TOP_LAW_MEMBERSHIP_V1"}
BINDING = {
    "adequacy_certificate_path":
        "canonical/governance/P3_BINARY_TOP_LAW_POLICY_ADEQUACY_CERTIFICATE_20261008_V1.json",
    "adequacy_certificate_blob_sha": "7b27ac7bce607651c71e395aa275317761ddea7a",
    "independent_verification_path":
        "canonical/verification/P3_BINARY_TOP_LAW_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_20261008_V1.json",
    "independent_verification_blob_sha": "3c6e1e38bb8da9022577029067ee159318ec6c79",
}


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "policy_adequacy_authenticated": False,
        "selected_class_membership_authenticated": False,
        "root_task_authority_self_proved": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != {"raw_source", "source_id"}:
        return _fail("PAYLOAD_FIELDS_INVALID")
    raw = payload.get("raw_source")
    source_id = payload.get("source_id")
    if not isinstance(raw, (str, bytes)):
        return _fail("RAW_SOURCE_REQUIRED")
    if not isinstance(source_id, str) or not source_id.strip():
        return _fail("SOURCE_ID_REQUIRED")

    membership = compile_membership(raw, source_id=source_id)
    if membership.get("pass") is not True:
        return _fail("STRICT_P3_BINARY_MEMBERSHIP_REJECTED", membership=membership)
    if (
        membership.get("selected_class_membership_authenticated") is not True
        or membership.get("membership_self_assertion_permitted") is not False
        or membership.get("semantic_extractor_required") is not False
        or membership.get("policy_adequacy_authority") is not False
    ):
        return _fail("MEMBERSHIP_AUTHORITY_BOUNDARY_INVALID", membership=membership)

    problem = {
        "decision_basis": [CONDITION["id"]],
        "policy_conditions": {POLICY_ID: dict(CONDITION)},
        "policy_adequacy_bindings": {POLICY_ID: dict(BINDING)},
        "formal_source_constraints": [dict(CONDITION)],
        "proposed_refinements": [dict(CONDITION)],
        "discriminators": [],
    }
    result = solve_cegar(problem)
    if (
        result.get("pass") is not True
        or result.get("common_policy_certified") is not True
        or result.get("selected_policy_id") != POLICY_ID
    ):
        return _fail("AUTHENTICATED_TOP_LAW_CEGAR_REJECTED", cegar=result)

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__STRICT_P3_BINARY_MEMBERSHIP_TO_AUTHENTICATED_TOP_LAW_POLICY",
        "policy_id": POLICY_ID,
        "policy_condition": dict(CONDITION),
        "policy_adequacy_authenticated": True,
        "selected_class_membership_authenticated": True,
        "membership_receipt": membership.get("membership_receipt"),
        "raw_source_sha256": membership.get("raw_source_sha256"),
        "normalized_contract_sha256": membership.get("normalized_contract_sha256"),
        "cegar": result,
        "root_task_authority": membership.get("task_root_authority"),
        "root_task_authority_self_proved": False,
        "scope": "STRICT_EXPLICIT_P3_BINARY_JSON_SOURCE_CLASS_ONLY",
        "whole_p3_closed": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "REAL_AUTHENTICATED_POLICY_ADEQUACY_LEAF_ONLY_FOR_STRICT_EXPLICIT_P3_BINARY_ROOT_TASKS;"
            "NO_FREE_FORM_P3_SCOPE_OR_GLOBAL_U_CREDIT"
        ),
    }
