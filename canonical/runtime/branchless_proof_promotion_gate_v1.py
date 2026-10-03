"""Fail-closed reuse gate for independently verified exact proof capsules.

A verified proof may be reused across branch/base drift only when every
load-bearing payload blob and every dependency-cone blob is byte-identical to
the independently verified capsule. Unrelated repository drift is intentionally
ignored. This gate grants no acceptance, capability, family, execution, or
promotion credit; a current projection/integration check is still required.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_BRANCHLESS_PROOF_PROMOTION_GATE_V1"
HEX = set("0123456789abcdef")


def _sha(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 40 and set(v.lower()) <= HEX


def _blob_map(raw: Any, label: str, *, require_nonempty: bool) -> tuple[dict[str, str], list[str]]:
    if not isinstance(raw, list):
        return {}, [f"{label}_BLOBS_NOT_LIST"]
    if require_nonempty and not raw:
        return {}, [f"{label}_BLOBS_REQUIRED"]
    out: dict[str, str] = {}
    errors: list[str] = []
    for i, row in enumerate(raw):
        if not isinstance(row, Mapping):
            errors.append(f"{label}_BLOB_NOT_OBJECT:{i}")
            continue
        path = row.get("path")
        sha = row.get("git_blob_sha")
        if not isinstance(path, str) or not path or not _sha(sha):
            errors.append(f"{label}_BLOB_INVALID:{i}")
            continue
        if path in out:
            errors.append(f"{label}_BLOB_DUPLICATE:{path}")
            continue
        out[path] = str(sha)
    return out, errors


def _receipt(raw: Any, label: str) -> list[str]:
    if not isinstance(raw, Mapping):
        return [f"{label}_RECEIPT_REQUIRED"]
    errors: list[str] = []
    if raw.get("independent") is not True:
        errors.append(f"{label}_RECEIPT_NOT_INDEPENDENT")
    if not str(raw.get("status", "")).startswith("INDEPENDENT"):
        errors.append(f"{label}_RECEIPT_STATUS_NOT_PASS")
    if not isinstance(raw.get("path"), str) or not raw.get("path") or not _sha(raw.get("git_blob_sha")):
        errors.append(f"{label}_RECEIPT_NOT_CONTENT_ADDRESSED")
    return errors


def _fail(errors: list[str]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "reuse_verified_proof": False,
        "full_proof_reverification_required": True,
        "errors": sorted(set(errors)),
        "integration_projection_reverification_required": True,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def evaluate(doc: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, Mapping) or doc.get("schema") != SCHEMA:
        return _fail(["SCHEMA_INVALID"])

    verified = doc.get("verified_capsule")
    current = doc.get("current_snapshot")
    if not isinstance(verified, Mapping) or not isinstance(current, Mapping):
        return _fail(["VERIFIED_CAPSULE_AND_CURRENT_SNAPSHOT_REQUIRED"])

    errors: list[str] = []
    scope_id = verified.get("scope_id")
    if not isinstance(scope_id, str) or not scope_id or current.get("scope_id") != scope_id:
        errors.append("SCOPE_ID_MISMATCH")

    verified_payload, e = _blob_map(verified.get("payload_blobs"), "VERIFIED_PAYLOAD", require_nonempty=True)
    errors += e
    current_payload, e = _blob_map(current.get("payload_blobs"), "CURRENT_PAYLOAD", require_nonempty=True)
    errors += e
    verified_cone, e = _blob_map(verified.get("dependency_cone_blobs"), "VERIFIED_DEPENDENCY_CONE", require_nonempty=False)
    errors += e
    current_cone, e = _blob_map(current.get("dependency_cone_blobs"), "CURRENT_DEPENDENCY_CONE", require_nonempty=False)
    errors += e

    errors += _receipt(verified.get("verification_receipt"), "VERIFICATION")
    errors += _receipt(verified.get("dependency_cone_receipt"), "DEPENDENCY_CONE")

    if verified.get("verification_complete") is not True:
        errors.append("VERIFICATION_NOT_COMPLETE")
    if verified.get("counterexample_suite_pass") is not True:
        errors.append("COUNTEREXAMPLE_SUITE_NOT_PASS")
    if verified.get("promotion_authority") not in (None, False):
        errors.append("CAPSULE_SELF_ASSERTS_PROMOTION_AUTHORITY")
    if verified.get("execution_authority") not in (None, False):
        errors.append("CAPSULE_SELF_ASSERTS_EXECUTION_AUTHORITY")

    if errors:
        return _fail(errors)

    payload_changes = sorted(
        path for path in set(verified_payload) | set(current_payload)
        if verified_payload.get(path) != current_payload.get(path)
    )
    cone_changes = sorted(
        path for path in set(verified_cone) | set(current_cone)
        if verified_cone.get(path) != current_cone.get(path)
    )

    reuse = not payload_changes and not cone_changes
    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_CAPSULE_REUSE_ADMISSIBLE" if reuse else "PASS__REVERIFY_REQUIRED",
        "reuse_verified_proof": reuse,
        "full_proof_reverification_required": not reuse,
        "verified_base_commit": verified.get("base_commit"),
        "current_base_commit": current.get("base_commit"),
        "base_commit_drift_ignored_only_because_exact_load_bearing_bytes_match": bool(
            reuse and verified.get("base_commit") != current.get("base_commit")
        ),
        "payload_changes": payload_changes,
        "dependency_cone_changes": cone_changes,
        "integration_projection_reverification_required": True,
        "rule": (
            "BRANCH_OR_BASE_IDENTITY_IS_NOT_LOAD_BEARING_WHEN_EXACT_VERIFIED_PAYLOAD_AND_DEPENDENCY_CONE_BYTES_MATCH__"
            "ANY_LOAD_BEARING_BYTE_OR_CONE_CHANGE_REQUIRES_REVERIFICATION__"
            "CURRENT_INTEGRATION_PROJECTION_MUST_STILL_BE_VERIFIED"
        ),
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
