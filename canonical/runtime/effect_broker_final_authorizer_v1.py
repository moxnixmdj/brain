"""Single fail-closed authorization stack for Project Brain effects.

This is the only verdict shape intended to be eligible for a future effect
carrier. It composes: structural broker admission -> exact receipt-byte
resolution -> schema-specific semantic verification. It performs no side effect.
"""
from __future__ import annotations
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from canonical.runtime.effect_broker_contract_v1 import admit
from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes
from canonical.runtime.effect_broker_semantic_gate_v1 import authorize_semantics

SCHEMA = "PROJECT_BRAIN_EFFECT_FINAL_AUTHORIZATION_V1"


def _deny(stage: str, reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "DENY_FAIL_CLOSED",
        "allowed": False,
        "failed_stage": stage,
        "reason": reason,
        "acceptance_credit_delta": 0,
    }


def authorize_effect(
    request: Mapping[str, Any],
    grant: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Authorize an effect request; never executes the effect itself."""
    structural = admit(request, grant)
    if structural.get("allowed") is not True:
        return _deny("STRUCTURAL_ADMISSION", str(structural.get("reason", "DENIED")))

    try:
        authority = resolve_receipt_bytes(
            grant.get("authority_receipt"),
            repo_root=repo_root,
        )
        composition = resolve_receipt_bytes(
            grant.get("composition_receipt"),
            repo_root=repo_root,
        )
    except Exception as exc:
        return _deny(
            "RECEIPT_BYTE_IDENTITY",
            type(exc).__name__ + ":" + str(exc),
        )

    semantic = authorize_semantics(
        request=request,
        resolved_authority_receipt=authority,
        resolved_composition_receipt=composition,
    )
    if semantic.get("allowed") is not True:
        return _deny(
            "SEMANTIC_VERIFICATION",
            str(semantic.get("reason", "DENIED")),
        )

    return {
        "schema": SCHEMA,
        "status": "ALLOW_FINAL_AUTHORIZATION",
        "allowed": True,
        "request_sha256": request.get("request_sha256"),
        "grant_sha256": grant.get("grant_sha256"),
        "mission_id": request.get("mission_id"),
        "capsule_head_sha256": request.get("capsule_head_sha256"),
        "effect_kind": request.get("effect_kind"),
        "resource": request.get("resource"),
        "operation": request.get("operation"),
        "payload_sha256": request.get("payload_sha256"),
        "authority_receipt_git_blob_sha": authority["git_blob_sha"],
        "authority_receipt_byte_sha256": authority["byte_sha256"],
        "authority_verifier_id": semantic["authority_verifier_id"],
        "authority_proof_digest": semantic["authority_proof_digest"],
        "composition_receipt_git_blob_sha": composition["git_blob_sha"],
        "composition_receipt_byte_sha256": composition["byte_sha256"],
        "composition_verifier_id": semantic["composition_verifier_id"],
        "composition_proof_digest": semantic["composition_proof_digest"],
        "effect_carrier_atomic_enforcement_still_required": True,
        "acceptance_credit_delta": 0,
    }
