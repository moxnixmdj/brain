"""Proof-carrying precommit contract for the Project Brain effect broker.

The confined child may request effects, but this module only returns ALLOW when
an exact content-addressed grant binds the exact request and independent/objective
receipts claim both authority and composition invariants. Actual receipt-byte
verification and carrier enforcement remain separate promotion gates.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

SCHEMA_REQUEST = "PROJECT_BRAIN_EFFECT_REQUEST_V1"
SCHEMA_GRANT = "PROJECT_BRAIN_EFFECT_GRANT_V1"
SCHEMA_VERDICT = "PROJECT_BRAIN_EFFECT_BROKER_VERDICT_V1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
BLOB_RE = re.compile(r"^[0-9a-f]{40,64}$")
EFFECT_KINDS = {
    "INFORMATION_READ",
    "REPO_WRITE",
    "PACKAGE_ENV_MUTATION",
    "EXTERNAL_MUTATION",
    "FINAL_OUTPUT",
}


class BrokerError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _token(value: Any, label: str, max_len: int = 512) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_len or "\x00" in value:
        raise BrokerError(label + "_INVALID")
    return value.strip()


def make_request(
    *,
    mission_id: str,
    capsule_head_sha256: str,
    action_ref: str,
    effect_kind: str,
    resource: str,
    operation: str,
    payload: Any,
) -> dict[str, Any]:
    mid = _token(mission_id, "MISSION_ID", 256)
    head = _token(capsule_head_sha256, "CAPSULE_HEAD", 64)
    if not SHA256_RE.fullmatch(head):
        raise BrokerError("CAPSULE_HEAD_NOT_SHA256")
    kind = _token(effect_kind, "EFFECT_KIND", 64)
    if kind not in EFFECT_KINDS:
        raise BrokerError("EFFECT_KIND_UNKNOWN:" + kind)
    resource = _token(resource, "RESOURCE", 1024)
    operation = _token(operation, "OPERATION", 128)
    action_ref = _token(action_ref, "ACTION_REF", 512)
    payload_bytes = _canon(payload)
    if len(payload_bytes) > 8_000_000:
        raise BrokerError("PAYLOAD_TOO_LARGE")
    core = {
        "schema": SCHEMA_REQUEST,
        "mission_id": mid,
        "capsule_head_sha256": head,
        "action_ref": action_ref,
        "effect_kind": kind,
        "resource": resource,
        "operation": operation,
        "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
        "payload_bytes": len(payload_bytes),
        "payload": payload,
    }
    return {**core, "request_sha256": _sha(core)}


def verify_request(request: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(request, Mapping) or request.get("schema") != SCHEMA_REQUEST:
        raise BrokerError("REQUEST_SCHEMA_INVALID")
    expected = make_request(
        mission_id=request.get("mission_id"),
        capsule_head_sha256=request.get("capsule_head_sha256"),
        action_ref=request.get("action_ref"),
        effect_kind=request.get("effect_kind"),
        resource=request.get("resource"),
        operation=request.get("operation"),
        payload=request.get("payload"),
    )
    if dict(request) != expected:
        raise BrokerError("REQUEST_CONTENT_OR_HASH_MISMATCH")
    return expected


def _receipt(value: Any, label: str, required_true: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BrokerError(label + "_INVALID")
    path = _token(value.get("path"), label + "_PATH", 1024)
    blob = _token(value.get("git_blob_sha"), label + "_BLOB", 64)
    if not BLOB_RE.fullmatch(blob):
        raise BrokerError(label + "_BLOB_INVALID")
    out = {"path": path, "git_blob_sha": blob}
    for field in required_true:
        if value.get(field) is not True:
            raise BrokerError(label + "_" + field.upper() + "_NOT_TRUE")
        out[field] = True
    if set(value) != set(out):
        raise BrokerError(label + "_UNBOUND_FIELDS")
    return out


def make_grant(
    *,
    request: Mapping[str, Any],
    authority_receipt: Mapping[str, Any],
    composition_receipt: Mapping[str, Any],
    max_payload_bytes: int,
) -> dict[str, Any]:
    req = verify_request(request)
    authority = _receipt(
        authority_receipt,
        "AUTHORITY_RECEIPT",
        (
            "scope_complete",
            "allow_implies_zero_critical_authority_violation",
            "independent_or_objective",
        ),
    )
    composition = _receipt(
        composition_receipt,
        "COMPOSITION_RECEIPT",
        (
            "scope_complete",
            "state_and_provenance_invariants_hold",
            "independent_or_objective",
        ),
    )
    try:
        limit = int(max_payload_bytes)
    except Exception as exc:
        raise BrokerError("MAX_PAYLOAD_BYTES_INVALID") from exc
    if limit < 0 or limit > 8_000_000:
        raise BrokerError("MAX_PAYLOAD_BYTES_OUT_OF_RANGE")
    if int(req["payload_bytes"]) > limit:
        raise BrokerError("REQUEST_EXCEEDS_GRANT_PAYLOAD_LIMIT")
    core = {
        "schema": SCHEMA_GRANT,
        "request_sha256": req["request_sha256"],
        "mission_id": req["mission_id"],
        "capsule_head_sha256": req["capsule_head_sha256"],
        "effect_kind": req["effect_kind"],
        "resource": req["resource"],
        "operation": req["operation"],
        "payload_sha256": req["payload_sha256"],
        "max_payload_bytes": limit,
        "authority_receipt": authority,
        "composition_receipt": composition,
    }
    return {**core, "grant_sha256": _sha(core)}


def admit(request: Mapping[str, Any], grant: Mapping[str, Any]) -> dict[str, Any]:
    try:
        req = verify_request(request)
        if not isinstance(grant, Mapping) or grant.get("schema") != SCHEMA_GRANT:
            raise BrokerError("GRANT_SCHEMA_INVALID")
        expected = make_grant(
            request=req,
            authority_receipt=grant.get("authority_receipt"),
            composition_receipt=grant.get("composition_receipt"),
            max_payload_bytes=grant.get("max_payload_bytes"),
        )
        if dict(grant) != expected:
            raise BrokerError("GRANT_CONTENT_OR_HASH_MISMATCH")
        return {
            "schema": SCHEMA_VERDICT,
            "status": "ALLOW_PRECOMMIT",
            "allowed": True,
            "request_sha256": req["request_sha256"],
            "grant_sha256": expected["grant_sha256"],
            "mission_id": req["mission_id"],
            "capsule_head_sha256": req["capsule_head_sha256"],
            "effect_kind": req["effect_kind"],
            "resource": req["resource"],
            "operation": req["operation"],
            "independent_receipt_byte_verification_still_required": True,
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA_VERDICT,
            "status": "DENY_FAIL_CLOSED",
            "allowed": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }
