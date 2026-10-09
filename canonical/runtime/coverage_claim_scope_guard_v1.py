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
    "mission_blob_sha",
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


def validate_claim(claim: Mapping[str, Any], *, current_mission_blob_sha: str) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(claim, Mapping):
        return {"pass": False, "errors": ["CLAIM_NOT_OBJECT"], "terminal_credit_delta": 0}

    for field in CORE_FIELDS:
        value = claim.get(field)
        if not isinstance(value, str) or not value:
            errors.append("INVALID_FIELD:" + field)

    if claim.get("claim_kind") not in ALLOWED_KINDS:
        errors.append("CLAIM_KIND_NOT_ALLOWED")
    if claim.get("mission_blob_sha") != current_mission_blob_sha:
        errors.append("MISSION_BINDING_STALE")

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
        "status": "PASS__FROZEN_CLAIM_SCOPE" if not errors else "FAIL_CLOSED",
        "errors": errors,
        "claim_id": expected,
        "claim_soundness_only": True,
        "global_mission_completion_derivable": False,
        "terminal_credit_delta": 0,
    }
