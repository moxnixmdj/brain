from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

from canonical.runtime.coverage_claim_authorization_guard_v1 import authorize_claim

GOOD_SCHEMA = "PROJECT_BRAIN_CCRT_GOOD_CELL_CERTIFICATE_V1"
GOOD_VERIFY_SCHEMA = "PROJECT_BRAIN_CCRT_GOOD_CELL_INDEPENDENT_VERIFICATION_V1"


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _sha64(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def _fail(reason: str, *, details: Any = None) -> dict[str, Any]:
    out = {
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "r2_invariant_preserved": False,
        "r2_globally_closed": False,
        "terminal_credit_delta": 0,
    }
    if details is not None:
        out["details"] = details
    return out


def _registry_entry(registry: Mapping[str, Any], verifier_id: str) -> Mapping[str, Any] | None:
    rows = registry.get("verifiers") if isinstance(registry, Mapping) else None
    if not isinstance(rows, list):
        return None
    matches = [
        row for row in rows
        if isinstance(row, Mapping) and row.get("verifier_id") == verifier_id
    ]
    return matches[0] if len(matches) == 1 else None


def initialize(
    claim: Mapping[str, Any],
    *,
    current_mission_semantics_sha256: str,
    authorization_policy: Mapping[str, Any],
    authorization: Mapping[str, Any],
    authorization_git_blob_sha: str,
    authorization_verification: Mapping[str, Any],
) -> dict[str, Any]:
    auth = authorize_claim(
        claim,
        current_mission_semantics_sha256=current_mission_semantics_sha256,
        policy=authorization_policy,
        authorization=authorization,
        authorization_git_blob_sha=authorization_git_blob_sha,
        verification=authorization_verification,
    )
    if auth.get("pass") is not True:
        return _fail("CLAIM_NOT_MISSION_AUTHORIZED", details=auth)
    return {
        "pass": True,
        "status": "PASS__EMPTY_G_MINUS_INITIALIZED",
        "claim_id": claim["claim_id"],
        "mission_semantics_sha256": current_mission_semantics_sha256,
        "scope_sha256": claim["scope_sha256"],
        "semantics_sha256": claim["semantics_sha256"],
        "cells": [],
        "g_minus_cell_count": 0,
        "r2_invariant_preserved": True,
        "r2_globally_closed": False,
        "terminal_credit_delta": 0,
    }


def admit(
    state: Mapping[str, Any],
    claim: Mapping[str, Any],
    *,
    current_mission_semantics_sha256: str,
    authorization_policy: Mapping[str, Any],
    authorization: Mapping[str, Any],
    authorization_git_blob_sha: str,
    authorization_verification: Mapping[str, Any],
    verifier_registry: Mapping[str, Any],
    certificate: Mapping[str, Any],
    independent_verification: Mapping[str, Any],
) -> dict[str, Any]:
    auth = authorize_claim(
        claim,
        current_mission_semantics_sha256=current_mission_semantics_sha256,
        policy=authorization_policy,
        authorization=authorization,
        authorization_git_blob_sha=authorization_git_blob_sha,
        verification=authorization_verification,
    )
    if auth.get("pass") is not True:
        return _fail("CLAIM_NOT_MISSION_AUTHORIZED", details=auth)

    if not isinstance(state, Mapping) or state.get("pass") is not True:
        return _fail("STATE_INVALID")
    for field in ("claim_id", "mission_semantics_sha256", "scope_sha256", "semantics_sha256"):
        expected = claim.get(field)
        if field == "mission_semantics_sha256":
            expected = current_mission_semantics_sha256
        if state.get(field) != expected:
            return _fail("STATE_CLAIM_BINDING_MISMATCH:" + field)

    if not isinstance(certificate, Mapping) or certificate.get("schema") != GOOD_SCHEMA:
        return _fail("GOOD_CERTIFICATE_SCHEMA_INVALID")

    required_equal = {
        "claim_id": claim.get("claim_id"),
        "mission_semantics_sha256": current_mission_semantics_sha256,
        "scope_sha256": claim.get("scope_sha256"),
        "claim_semantics_sha256": claim.get("semantics_sha256"),
    }
    for field, expected in required_equal.items():
        if certificate.get(field) != expected:
            return _fail("GOOD_CERTIFICATE_CLAIM_MISMATCH:" + field)

    cell_id = certificate.get("cell_id")
    result_sha = certificate.get("behavior_or_result_sha256")
    verifier_id = certificate.get("verifier_id")
    if not isinstance(cell_id, str) or not cell_id:
        return _fail("GOOD_CELL_ID_INVALID")
    if not _sha64(result_sha):
        return _fail("GOOD_RESULT_SHA256_INVALID")
    if certificate.get("accepted") is not True:
        return _fail("GOOD_CELL_NOT_ACCEPTED")
    if certificate.get("actual_claim_satisfaction_verified") is not True:
        return _fail("ACTUAL_CLAIM_SATISFACTION_NOT_VERIFIED")

    entry = _registry_entry(verifier_registry, str(verifier_id))
    if entry is None:
        return _fail("GOAL_SATISFACTION_VERIFIER_NOT_REGISTERED")
    if certificate.get("verifier_path") != entry.get("path"):
        return _fail("GOAL_SATISFACTION_VERIFIER_PATH_MISMATCH")
    if certificate.get("verifier_git_blob_sha") != entry.get("git_blob_sha"):
        return _fail("GOAL_SATISFACTION_VERIFIER_BLOB_MISMATCH")
    if certificate.get("verifier_status") != entry.get("success_status"):
        return _fail("GOAL_SATISFACTION_VERIFIER_STATUS_MISMATCH")
    verifier_output_sha = certificate.get("verifier_output_sha256")
    if not _sha64(verifier_output_sha):
        return _fail("VERIFIER_OUTPUT_SHA256_INVALID")

    cert_sha = _sha256(certificate)
    if not isinstance(independent_verification, Mapping) or independent_verification.get("schema") != GOOD_VERIFY_SCHEMA:
        return _fail("GOOD_INDEPENDENT_VERIFICATION_SCHEMA_INVALID")
    verify_required = {
        "subject_certificate_sha256": cert_sha,
        "claim_id": claim.get("claim_id"),
        "cell_id": cell_id,
        "behavior_or_result_sha256": result_sha,
    }
    for field, expected in verify_required.items():
        if independent_verification.get(field) != expected:
            return _fail("GOOD_INDEPENDENT_VERIFICATION_MISMATCH:" + field)
    if independent_verification.get("pass") is not True:
        return _fail("GOOD_INDEPENDENT_VERIFICATION_NOT_PASS")
    if independent_verification.get("independent_verified") is not True:
        return _fail("GOOD_CELL_NOT_INDEPENDENTLY_VERIFIED")
    if independent_verification.get("claim_semantics_binding_verified") is not True:
        return _fail("GOOD_CELL_CLAIM_SEMANTICS_NOT_VERIFIED")
    if independent_verification.get("goal_satisfaction_semantics_verified") is not True:
        return _fail("GOOD_CELL_GOAL_SATISFACTION_SEMANTICS_NOT_VERIFIED")
    independent_id = independent_verification.get("independent_verifier_id")
    if not isinstance(independent_id, str) or not independent_id or independent_id == verifier_id:
        return _fail("GOOD_CELL_INDEPENDENT_VERIFIER_INVALID")

    rows = state.get("cells")
    if not isinstance(rows, list):
        return _fail("STATE_CELLS_INVALID")
    existing = [row for row in rows if isinstance(row, Mapping) and row.get("cell_id") == cell_id]
    if existing:
        if len(existing) == 1 and existing[0].get("certificate_sha256") == cert_sha:
            return {
                **deepcopy(dict(state)),
                "status": "PASS__IDEMPOTENT_GOOD_CELL_ALREADY_ADMITTED",
                "r2_invariant_preserved": True,
                "r2_globally_closed": False,
                "terminal_credit_delta": 0,
            }
        return _fail("CONFLICTING_GOOD_CELL_ID")

    new_rows = deepcopy(rows)
    new_rows.append({
        "cell_id": cell_id,
        "behavior_or_result_sha256": result_sha,
        "certificate_sha256": cert_sha,
        "verifier_id": verifier_id,
        "verifier_git_blob_sha": entry.get("git_blob_sha"),
        "independent_verifier_id": independent_id,
    })
    new_rows.sort(key=lambda x: x["cell_id"])
    return {
        **{k: deepcopy(v) for k, v in state.items() if k not in {"cells", "g_minus_cell_count", "status"}},
        "pass": True,
        "status": "PASS__GOOD_CELL_ADMITTED_TO_G_MINUS",
        "cells": new_rows,
        "g_minus_cell_count": len(new_rows),
        "r2_invariant_preserved": True,
        "r2_globally_closed": False,
        "terminal_credit_delta": 0,
    }
