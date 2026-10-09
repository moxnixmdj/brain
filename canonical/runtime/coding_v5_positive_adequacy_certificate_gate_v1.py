"""Fail-closed candidate gate for V5 coding positive-adequacy certificates.

This does not prove adequacy. It defines the minimum machine-checkable shape a
candidate must satisfy before independent exact-byte verification can promote it.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CODING_V5_POSITIVE_ADEQUACY_CERTIFICATE_GATE_V1"
POLICY_ID = "ADVANCED_AGENTIC_SOFTWARE_ENGINEERING_MINI_SWE_SUPERPOWERS_V1"
ALLOWED_TARGETS = {
    "CODING_CURSORBENCH_GE_57_8",
    "CODING_FRONTIERCODE_GE_54_4",
}
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _receipt(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, Mapping):
        errors.append(label + "_RECEIPT_NOT_OBJECT")
        return
    if value.get("verified") is not True:
        errors.append(label + "_RECEIPT_NOT_VERIFIED")
    if value.get("independent") is not True:
        errors.append(label + "_RECEIPT_NOT_INDEPENDENT")
    path = value.get("source_path")
    sha = value.get("source_sha")
    if not isinstance(path, str) or not path.strip():
        errors.append(label + "_RECEIPT_SOURCE_PATH_MISSING")
    if not isinstance(sha, str) or not SHA40.fullmatch(sha):
        errors.append(label + "_RECEIPT_SOURCE_SHA_INVALID")


def evaluate(payload: Any) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": ["PAYLOAD_NOT_OBJECT"],
            "candidate_adequacy_certificate_ready": False,
            "promotion_authority": False,
            "terminal_credit_delta": 0,
        }

    if payload.get("policy_id") != POLICY_ID:
        errors.append("EXACT_V5_POLICY_ID_MISMATCH")

    binding = payload.get("policy_binding")
    if not isinstance(binding, Mapping):
        errors.append("POLICY_BINDING_NOT_OBJECT")
    else:
        path = binding.get("path")
        sha = binding.get("git_blob_sha")
        if not isinstance(path, str) or not path.strip():
            errors.append("POLICY_PATH_MISSING")
        if not isinstance(sha, str) or not SHA40.fullmatch(sha):
            errors.append("POLICY_BLOB_SHA_INVALID")
        if binding.get("exact_v5_completion_contract") is not True:
            errors.append("EXACT_V5_COMPLETION_CONTRACT_NOT_BOUND")
        if binding.get("transitive_policy_pins_complete") is not True:
            errors.append("TRANSITIVE_POLICY_PINS_NOT_PROVED_COMPLETE")

    targets = payload.get("target_predicates")
    if (
        not isinstance(targets, list)
        or not targets
        or any(not isinstance(x, str) or x not in ALLOWED_TARGETS for x in targets)
        or len(set(targets)) != len(targets)
    ):
        errors.append("TARGET_PREDICATES_INVALID")

    condition = payload.get("policy_condition")
    if not isinstance(condition, Mapping):
        errors.append("POLICY_CONDITION_NOT_OBJECT")
    else:
        pid = condition.get("predicate_id")
        if not isinstance(pid, str) or not pid.strip():
            errors.append("POLICY_CONDITION_PREDICATE_ID_INVALID")
        if condition.get("membership_phase") != "PRE_EXECUTION":
            errors.append("POLICY_CONDITION_NOT_PRE_EXECUTION")
        if condition.get("depends_on_acceptance_outcome") is not False:
            errors.append("POSTHOC_ACCEPTANCE_OUTCOME_CONDITION_FORBIDDEN")
        if condition.get("decision_basis_sound") is not True:
            errors.append("POLICY_CONDITION_DECISION_BASIS_UNPROVED")
        if condition.get("target_relevance_proved") is not True:
            errors.append("POLICY_CONDITION_TARGET_RELEVANCE_UNPROVED")
        _receipt(condition.get("target_relevance_receipt"), "TARGET_RELEVANCE", errors)

    resources = payload.get("resource_admissibility")
    if not isinstance(resources, Mapping) or resources.get("proved") is not True:
        errors.append("RESOURCE_ADMISSIBILITY_UNPROVED")
    else:
        _receipt(resources.get("receipt"), "RESOURCE_ADMISSIBILITY", errors)

    constraints = payload.get("load_bearing_constraints")
    if not isinstance(constraints, Mapping) or constraints.get("preserved") is not True:
        errors.append("LOAD_BEARING_CONSTRAINTS_UNPROVED")
    else:
        _receipt(constraints.get("receipt"), "LOAD_BEARING_CONSTRAINTS", errors)

    proof = payload.get("adequacy_proof")
    if not isinstance(proof, Mapping):
        errors.append("ADEQUACY_PROOF_NOT_OBJECT")
        mode = None
    else:
        mode = proof.get("mode")
        if proof.get("empirical_generalization_used") is not False:
            errors.append("EMPIRICAL_GENERALIZATION_FORBIDDEN")

        if mode == "FORMAL_ALL_MEMBERS":
            if proof.get("adequate_for_every_member") is not True:
                errors.append("FORMAL_WHOLE_CELL_ADEQUACY_UNPROVED")
            if proof.get("membership_rule_total_for_declared_cell") is not True:
                errors.append("FORMAL_CELL_MEMBERSHIP_RULE_INCOMPLETE")
            _receipt(proof.get("theorem_receipt"), "FORMAL_ADEQUACY_THEOREM", errors)

        elif mode == "FINITE_COMPLETE_CELL":
            count = proof.get("member_count")
            verified_count = proof.get("verified_member_count")
            if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                errors.append("FINITE_CELL_MEMBER_COUNT_INVALID")
            if proof.get("cell_membership_complete") is not True:
                errors.append("FINITE_CELL_COMPLETENESS_UNPROVED")
            _receipt(proof.get("cell_completeness_receipt"), "FINITE_CELL_COMPLETENESS", errors)
            if (
                not isinstance(verified_count, int)
                or isinstance(verified_count, bool)
                or not isinstance(count, int)
                or verified_count != count
            ):
                errors.append("FINITE_CELL_VERIFIED_MEMBER_COUNT_MISMATCH")
            if proof.get("all_members_independently_verified_success") is not True:
                errors.append("FINITE_CELL_NOT_ALL_SUCCESS")
            if proof.get("exact_v5_identity_on_every_member") is not True:
                errors.append("FINITE_CELL_POLICY_IDENTITY_NOT_EXACT_V5")
            _receipt(proof.get("member_results_receipt"), "FINITE_CELL_RESULTS", errors)

        else:
            errors.append("ADEQUACY_PROOF_MODE_INVALID")

    passed = not errors
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": (
            "CANDIDATE_V5_POSITIVE_ADEQUACY_CERTIFICATE_SHAPE_READY__"
            "INDEPENDENT_EXACT_BYTE_VERIFICATION_STILL_REQUIRED"
            if passed
            else "FAIL_CLOSED"
        ),
        "policy_id": payload.get("policy_id"),
        "proof_mode": mode,
        "candidate_adequacy_certificate_ready": passed,
        "errors": sorted(set(errors)),
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
        "rule": (
            "ONE_SUCCESS_CANNOT_GENERALIZE_TO_A_CLASS__POSTHOC_ACCEPTANCE_OUTCOME_"
            "CELLS_ARE_FORBIDDEN__A_CANDIDATE_REQUIRES_EITHER_A_FORMAL_ALL_MEMBERS_"
            "ADEQUACY_THEOREM_OR_COMPLETE_FINITE_CELL_EVIDENCE_UNDER_EXACT_V5"
        ),
    }
