from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.coverage_claim_scope_guard_v1 import (
    ALLOWED_KINDS,
    CORE_FIELDS,
    compute_claim_id,
)

MISSION_AUTHORITY_PATH = "canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"
CURRENT_POINTER_SCHEMA = "PROJECT_BRAIN_CURRENT_MISSION_OBJECTIVE_POINTER_V1"
MISSION_AUTHORITY_SCHEMA = "PROJECT_BRAIN_REAL_MISSION_OBJECTIVE_V1"
EXPECTED_REAL_OBJECTIVE = "BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE"


def validate_claim(
    claim: Mapping[str, Any],
    *,
    current_pointer: Mapping[str, Any],
    mission_authority: Mapping[str, Any],
    mission_authority_blob_sha: str,
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(claim, Mapping):
        return {"pass": False, "errors": ["CLAIM_NOT_OBJECT"], "terminal_credit_delta": 0}
    if not isinstance(current_pointer, Mapping):
        return {"pass": False, "errors": ["CURRENT_POINTER_NOT_OBJECT"], "terminal_credit_delta": 0}
    if not isinstance(mission_authority, Mapping):
        return {"pass": False, "errors": ["MISSION_AUTHORITY_NOT_OBJECT"], "terminal_credit_delta": 0}

    for field in CORE_FIELDS:
        value = claim.get(field)
        if not isinstance(value, str) or not value:
            errors.append("INVALID_FIELD:" + field)

    if claim.get("claim_kind") not in ALLOWED_KINDS:
        errors.append("CLAIM_KIND_NOT_ALLOWED")

    if not isinstance(mission_authority_blob_sha, str) or len(mission_authority_blob_sha) != 40:
        errors.append("MISSION_AUTHORITY_BLOB_INVALID")
    elif claim.get("mission_blob_sha") != mission_authority_blob_sha:
        errors.append("MISSION_AUTHORITY_BINDING_STALE")

    if current_pointer.get("schema") != CURRENT_POINTER_SCHEMA:
        errors.append("CURRENT_POINTER_SCHEMA_INVALID")
    if mission_authority.get("schema") != MISSION_AUTHORITY_SCHEMA:
        errors.append("MISSION_AUTHORITY_SCHEMA_INVALID")

    source = current_pointer.get("authoritative_source")
    if not isinstance(source, Mapping) or source.get("path") != MISSION_AUTHORITY_PATH:
        errors.append("MISSION_AUTHORITY_PATH_DRIFT")

    authority_objective = mission_authority.get("real_objective")
    pointer_objective = current_pointer.get("real_objective")
    if authority_objective != EXPECTED_REAL_OBJECTIVE:
        errors.append("MISSION_AUTHORITY_OBJECTIVE_DRIFT")
    if pointer_objective != EXPECTED_REAL_OBJECTIVE:
        errors.append("CURRENT_POINTER_OBJECTIVE_DRIFT")

    if mission_authority.get("status") != "ACTIVE_CANONICAL_MISSION_OBJECTIVE_OVERRIDE":
        errors.append("MISSION_AUTHORITY_NOT_ACTIVE")
    if current_pointer.get("status") != "ACTIVE":
        errors.append("CURRENT_POINTER_NOT_ACTIVE")

    for field in ("scope_sha256", "target_predicate_sha256", "semantics_sha256"):
        value = claim.get(field)
        if isinstance(value, str):
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                errors.append("INVALID_SHA256:" + field)

    expected = compute_claim_id(claim)
    if claim.get("claim_id") != expected:
        errors.append("CLAIM_ID_MISMATCH")
    if claim.get("terminal_credit_delta", 0) != 0:
        errors.append("NONZERO_CREDIT_FORBIDDEN")

    return {
        "pass": not errors,
        "status": "PASS__FROZEN_CLAIM_SCOPE__STABLE_MISSION_AUTHORITY"
        if not errors else "FAIL_CLOSED",
        "errors": errors,
        "claim_id": expected,
        "mission_authority_blob_sha": mission_authority_blob_sha,
        "mission_authority_path": MISSION_AUTHORITY_PATH,
        "mutable_pointer_projection_is_claim_identity": False,
        "claim_soundness_only": True,
        "global_mission_completion_derivable": False,
        "terminal_credit_delta": 0,
    }
