from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

ALLOWED_KINDS = frozenset({
    "CHECKPOINT_ACCEPTANCE",
    "PROPERTY_CERTIFICATE",
    "BOUNDED_SUBGOAL",
    "EXECUTION_OBLIGATION",
})
CORE_FIELDS = (
    "claim_kind",
    "mission_semantics_sha256",
    "scope_sha256",
    "target_predicate_sha256",
    "semantics_sha256",
    "epoch",
    "authority_id",
)


def compute_claim_id(claim: Mapping[str, Any]) -> str:
    core = {k: claim.get(k) for k in CORE_FIELDS}
    raw = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return sha256(raw).hexdigest()


def _sha64(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def validate_claim(
    claim: Mapping[str, Any],
    *,
    current_mission_semantics_sha256: str,
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(claim, Mapping):
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": ["CLAIM_NOT_OBJECT"],
            "structural_scope_valid": False,
            "mission_authorized": False,
            "terminal_credit_delta": 0,
        }

    for field in CORE_FIELDS:
        value = claim.get(field)
        if not isinstance(value, str) or not value:
            errors.append("INVALID_FIELD:" + field)

    if claim.get("claim_kind") not in ALLOWED_KINDS:
        errors.append("CLAIM_KIND_NOT_ALLOWED")

    if claim.get("mission_semantics_sha256") != current_mission_semantics_sha256:
        errors.append("MISSION_SEMANTICS_BINDING_STALE")

    for field in (
        "mission_semantics_sha256",
        "scope_sha256",
        "target_predicate_sha256",
        "semantics_sha256",
    ):
        if not _sha64(claim.get(field)):
            errors.append("INVALID_SHA256:" + field)

    expected = compute_claim_id(claim)
    if claim.get("claim_id") != expected:
        errors.append("CLAIM_ID_MISMATCH")

    if claim.get("terminal_credit_delta", 0) != 0:
        errors.append("NONZERO_CREDIT_FORBIDDEN")

    return {
        "pass": not errors,
        "status": "PASS__FROZEN_CLAIM_STRUCTURE_V2" if not errors else "FAIL_CLOSED",
        "errors": errors,
        "claim_id": expected,
        "structural_scope_valid": not errors,
        "mission_authorized": False,
        "claim_soundness_proved": False,
        "global_mission_completion_derivable": False,
        "terminal_credit_delta": 0,
    }
