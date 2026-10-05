"""Fail-closed semantic authorization boundary for Project Brain effects.

This module intentionally grants no semantic authority by default. Receipt-byte
identity and structural broker admission are necessary but not sufficient. A
receipt schema becomes admissible only when its schema-specific deterministic
verifier is pinned in BUILTIN_VERIFIERS and returns an exact request-bound
verdict. Unknown schemas and malformed verifier outputs deny closed.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

SCHEMA_VERDICT = "PROJECT_BRAIN_EFFECT_SEMANTIC_GATE_VERDICT_V1"
ROLES = {"authority", "composition"}


class SemanticGateError(ValueError):
    pass


Verifier = Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]]

# Security boundary: production authorization uses this immutable module-level
# table only. There is deliberately no runtime registration API. Concrete
# schemas must be added by code review together with deterministic tests.
BUILTIN_VERIFIERS: dict[tuple[str, str], Verifier] = {}


def _deny(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA_VERDICT,
        "status": "DENY_FAIL_CLOSED",
        "allowed": False,
        "reason": reason,
        "acceptance_credit_delta": 0,
    }


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise SemanticGateError(label + "_INVALID")
    return value.strip()


def _request_binding(request: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(request, Mapping):
        raise SemanticGateError("REQUEST_INVALID")
    return {
        "request_sha256": _token(request.get("request_sha256"), "REQUEST_SHA256"),
        "mission_id": _token(request.get("mission_id"), "MISSION_ID"),
        "capsule_head_sha256": _token(request.get("capsule_head_sha256"), "CAPSULE_HEAD_SHA256"),
        "effect_kind": _token(request.get("effect_kind"), "EFFECT_KIND"),
        "resource": _token(request.get("resource"), "RESOURCE"),
        "operation": _token(request.get("operation"), "OPERATION"),
        "payload_sha256": _token(request.get("payload_sha256"), "PAYLOAD_SHA256"),
    }


def _verify_one(
    *,
    role: str,
    resolved_receipt: Mapping[str, Any],
    request: Mapping[str, Any],
) -> dict[str, Any]:
    if role not in ROLES:
        raise SemanticGateError("ROLE_UNKNOWN")
    if not isinstance(resolved_receipt, Mapping):
        raise SemanticGateError(role.upper() + "_RECEIPT_INVALID")
    document = resolved_receipt.get("document")
    if not isinstance(document, Mapping):
        raise SemanticGateError(role.upper() + "_DOCUMENT_MISSING")
    schema = document.get("schema")
    if not isinstance(schema, str) or not schema:
        raise SemanticGateError(role.upper() + "_SCHEMA_MISSING")

    verifier = BUILTIN_VERIFIERS.get((role, schema))
    if verifier is None:
        raise SemanticGateError(role.upper() + "_SCHEMA_UNVERIFIED:" + schema)

    binding = _request_binding(request)
    verdict = verifier(document, binding)
    if not isinstance(verdict, Mapping):
        raise SemanticGateError(role.upper() + "_VERIFIER_OUTPUT_INVALID")

    required = {
        "verified": True,
        "role": role,
        "receipt_schema": schema,
        **binding,
    }
    for key, expected in required.items():
        if verdict.get(key) != expected:
            raise SemanticGateError(role.upper() + "_VERIFIER_BINDING_MISMATCH:" + key)

    allowed_keys = set(required) | {"verifier_id", "proof_digest"}
    if set(verdict) != allowed_keys:
        raise SemanticGateError(role.upper() + "_VERIFIER_OUTPUT_UNBOUND_FIELDS")
    _token(verdict.get("verifier_id"), role.upper() + "_VERIFIER_ID")
    _token(verdict.get("proof_digest"), role.upper() + "_PROOF_DIGEST")
    return dict(verdict)


def authorize_semantics(
    *,
    request: Mapping[str, Any],
    resolved_authority_receipt: Mapping[str, Any],
    resolved_composition_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Return ALLOW only after both pinned semantic verifiers succeed exactly."""
    try:
        binding = _request_binding(request)
        authority = _verify_one(
            role="authority",
            resolved_receipt=resolved_authority_receipt,
            request=request,
        )
        composition = _verify_one(
            role="composition",
            resolved_receipt=resolved_composition_receipt,
            request=request,
        )
        return {
            "schema": SCHEMA_VERDICT,
            "status": "ALLOW_SEMANTICALLY_VERIFIED",
            "allowed": True,
            **binding,
            "authority_verifier_id": authority["verifier_id"],
            "authority_proof_digest": authority["proof_digest"],
            "composition_verifier_id": composition["verifier_id"],
            "composition_proof_digest": composition["proof_digest"],
            "effect_carrier_enforcement_still_required": True,
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return _deny(type(exc).__name__ + ":" + str(exc))
