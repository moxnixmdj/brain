from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.coverage_claim_scope_guard_v2 import validate_claim

RECEIPT_SCHEMA = "PROJECT_BRAIN_CCRT_CLAIM_AUTHORIZATION_RECEIPT_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_CCRT_CLAIM_AUTHORIZATION_INDEPENDENT_VERIFICATION_V1"


def authorize_claim(
    claim: Mapping[str, Any],
    *,
    current_mission_semantics_sha256: str,
    policy: Mapping[str, Any],
    authorization: Mapping[str, Any],
    authorization_git_blob_sha: str,
    verification: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    structural = validate_claim(
        claim,
        current_mission_semantics_sha256=current_mission_semantics_sha256,
    )
    if structural.get("pass") is not True:
        errors.extend("STRUCTURAL_" + x for x in structural.get("errors", []))

    mission_policy = policy.get("mission_semantic_authority") if isinstance(policy, Mapping) else None
    issuer = policy.get("authorized_issuer") if isinstance(policy, Mapping) else None
    if not isinstance(mission_policy, Mapping):
        errors.append("MISSION_POLICY_MISSING")
    elif mission_policy.get("mission_semantics_sha256") != current_mission_semantics_sha256:
        errors.append("POLICY_MISSION_SEMANTICS_STALE")
    if not isinstance(issuer, Mapping):
        errors.append("AUTHORIZED_ISSUER_MISSING")
        issuer_id = None
    else:
        issuer_id = issuer.get("authority_id")
        if not isinstance(issuer_id, str) or not issuer_id:
            errors.append("AUTHORIZED_ISSUER_ID_INVALID")

    if not isinstance(authorization, Mapping) or authorization.get("schema") != RECEIPT_SCHEMA:
        errors.append("AUTHORIZATION_RECEIPT_SCHEMA_INVALID")
    else:
        for field in (
            "claim_id",
            "claim_kind",
            "mission_semantics_sha256",
            "scope_sha256",
            "target_predicate_sha256",
            "semantics_sha256",
            "epoch",
            "authority_id",
        ):
            if authorization.get(field) != claim.get(field):
                errors.append("AUTHORIZATION_CLAIM_MISMATCH:" + field)
        if authorization.get("authority_id") != issuer_id:
            errors.append("AUTHORIZATION_ISSUER_NOT_MISSION_AUTHORITY")
        if authorization.get("authorized") is not True:
            errors.append("CLAIM_NOT_AUTHORIZED")

    if not isinstance(authorization_git_blob_sha, str) or len(authorization_git_blob_sha) != 40:
        errors.append("AUTHORIZATION_BLOB_SHA_INVALID")

    if not isinstance(verification, Mapping) or verification.get("schema") != VERIFY_SCHEMA:
        errors.append("AUTHORIZATION_VERIFICATION_SCHEMA_INVALID")
    else:
        if verification.get("subject_git_blob_sha") != authorization_git_blob_sha:
            errors.append("AUTHORIZATION_VERIFICATION_SUBJECT_MISMATCH")
        if verification.get("claim_id") != claim.get("claim_id"):
            errors.append("AUTHORIZATION_VERIFICATION_CLAIM_MISMATCH")
        if verification.get("pass") is not True:
            errors.append("AUTHORIZATION_VERIFICATION_NOT_PASS")
        if verification.get("independent_verified") is not True:
            errors.append("AUTHORIZATION_NOT_INDEPENDENTLY_VERIFIED")
        if verification.get("mission_authorization_semantics_verified") is not True:
            errors.append("MISSION_AUTHORIZATION_SEMANTICS_NOT_VERIFIED")
        independent_id = verification.get("independent_verifier_id")
        if not isinstance(independent_id, str) or not independent_id:
            errors.append("INDEPENDENT_VERIFIER_ID_INVALID")
        elif independent_id == issuer_id:
            errors.append("INDEPENDENT_VERIFIER_NOT_DISTINCT")

    return {
        "pass": not errors,
        "status": "PASS__MISSION_AUTHORIZED_FROZEN_CLAIM" if not errors else "FAIL_CLOSED",
        "errors": errors,
        "claim_id": claim.get("claim_id"),
        "structural_scope_valid": structural.get("pass") is True,
        "mission_authorized": not errors,
        "g_minus_claim_eligible": not errors,
        "actual_claim_satisfaction_verified": False,
        "global_mission_completion_derivable": False,
        "terminal_credit_delta": 0,
    }
