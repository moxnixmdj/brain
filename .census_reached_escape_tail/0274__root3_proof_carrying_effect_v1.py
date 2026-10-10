"""Fail-closed proof-carrying effect contract for the Root3 broker route.

This module deliberately proves only structural admission properties. It does not
claim that an external invariant receipt is semantically sound; instead it makes
that receipt, the exact authority grant, and the exact policy bytes load-bearing
inputs to a deterministic precommit token.

The wire adapter is intentionally aligned with zero_ambient_authority_launcher_v1:
the child emits PROJECT_BRAIN_EFFECT_REQUEST_V1:<json>, the launcher parses the
JSON object, and this verifier is the next parent-side gate. Ordinary stdout has
no effect authority and an unknown request type fails closed.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_ROOT3_PROOF_CARRYING_EFFECT_V1"
REQUEST_SCHEMA = "PROJECT_BRAIN_ROOT3_EFFECT_REQUEST_V1"
POLICY_SCHEMA = "PROJECT_BRAIN_ROOT3_EFFECT_POLICY_V1"

WIRE_TYPE_TO_CLASS = {
    "artifact_commit": "durable_write",
    "network_request": "network_request",
    "process_exec": "process_exec",
    "external_tool_call": "external_tool_call",
    "state_append": "state_append",
    "evidence_append": "evidence_append",
    "final_output": "final_output",
}
EFFECT_CLASSES = frozenset(WIRE_TYPE_TO_CLASS.values())
_COMPOSITION_CLASSES = frozenset({"state_append", "evidence_append", "final_output"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class EffectContractError(ValueError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EffectContractError(label + "_INVALID")
    return value.strip()


def _digest(value: Any, label: str) -> str:
    text = _token(value, label)
    if _SHA256.fullmatch(text) is None:
        raise EffectContractError(label + "_INVALID")
    return text


def _string_list(value: Any, label: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise EffectContractError(label + "_INVALID")
    out = [_token(item, label + "_ITEM") for item in value]
    if len(out) != len(set(out)):
        raise EffectContractError(label + "_DUPLICATE")
    if nonempty and not out:
        raise EffectContractError(label + "_EMPTY")
    return out


def _normalize_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, Mapping):
        raise EffectContractError("POLICY_NOT_OBJECT")
    if policy.get("schema") != POLICY_SCHEMA:
        raise EffectContractError("POLICY_SCHEMA_MISMATCH")

    epoch = _token(policy.get("authority_epoch"), "POLICY_AUTHORITY_EPOCH")
    rules = policy.get("rules")
    if not isinstance(rules, list) or not rules:
        raise EffectContractError("POLICY_RULES_INVALID")

    normalized_rules: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for index, raw in enumerate(rules):
        if not isinstance(raw, Mapping):
            raise EffectContractError(f"POLICY_RULE_{index}_INVALID")
        effect_class = _token(raw.get("effect_class"), f"POLICY_RULE_{index}_EFFECT_CLASS")
        if effect_class not in EFFECT_CLASSES:
            raise EffectContractError(f"POLICY_RULE_{index}_UNKNOWN_EFFECT_CLASS")
        rule = {
            "subject": _token(raw.get("subject"), f"POLICY_RULE_{index}_SUBJECT"),
            "effect_class": effect_class,
            "resource": _token(raw.get("resource"), f"POLICY_RULE_{index}_RESOURCE"),
            "operation": _token(raw.get("operation"), f"POLICY_RULE_{index}_OPERATION"),
            "scope": _token(raw.get("scope"), f"POLICY_RULE_{index}_SCOPE"),
        }
        key = (
            rule["subject"],
            rule["effect_class"],
            rule["resource"],
            rule["operation"],
            rule["scope"],
        )
        if key in seen:
            raise EffectContractError(f"POLICY_RULE_{index}_DUPLICATE")
        seen.add(key)
        normalized_rules.append(rule)

    return {
        "schema": POLICY_SCHEMA,
        "authority_epoch": epoch,
        "rules": normalized_rules,
    }


def _normalize_request(request: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        raise EffectContractError("REQUEST_NOT_OBJECT")

    # Launcher-wire objects use type/request_id and do not need to repeat schema.
    if "type" in request:
        wire_type = _token(request.get("type"), "REQUEST_TYPE")
        request_id = _token(request.get("request_id"), "REQUEST_ID")
        effect_class = WIRE_TYPE_TO_CLASS.get(wire_type)
        if effect_class is None:
            raise EffectContractError("REQUEST_UNKNOWN_WIRE_TYPE")
    else:
        if request.get("schema") != REQUEST_SCHEMA:
            raise EffectContractError("REQUEST_SCHEMA_MISMATCH")
        request_id = _token(request.get("request_id"), "REQUEST_ID")
        effect_class = _token(request.get("effect_class"), "REQUEST_EFFECT_CLASS")
        if effect_class not in EFFECT_CLASSES:
            raise EffectContractError("REQUEST_UNKNOWN_EFFECT_CLASS")

    normalized: dict[str, Any] = {
        "schema": REQUEST_SCHEMA,
        "request_id": request_id,
        "subject": _token(request.get("subject"), "REQUEST_SUBJECT"),
        "authority_epoch": _token(request.get("authority_epoch"), "REQUEST_AUTHORITY_EPOCH"),
        "effect_class": effect_class,
        "resource": _token(request.get("resource"), "REQUEST_RESOURCE"),
        "operation": _token(request.get("operation"), "REQUEST_OPERATION"),
        "scope": _token(request.get("scope"), "REQUEST_SCOPE"),
        "payload_sha256": _digest(request.get("payload_sha256"), "REQUEST_PAYLOAD_SHA256"),
        "provenance_refs": _string_list(
            request.get("provenance_refs", []),
            "REQUEST_PROVENANCE_REFS",
            nonempty=effect_class in _COMPOSITION_CLASSES,
        ),
    }

    if effect_class in _COMPOSITION_CLASSES:
        normalized["pre_state_sha256"] = _digest(
            request.get("pre_state_sha256"), "REQUEST_PRE_STATE_SHA256"
        )
        normalized["post_state_sha256"] = _digest(
            request.get("post_state_sha256"), "REQUEST_POST_STATE_SHA256"
        )
        receipt = request.get("invariant_receipt")
        if not isinstance(receipt, Mapping):
            raise EffectContractError("REQUEST_INVARIANT_RECEIPT_INVALID")
        normalized["invariant_receipt"] = {
            "path": _token(receipt.get("path"), "REQUEST_INVARIANT_RECEIPT_PATH"),
            "git_blob_sha": _token(
                receipt.get("git_blob_sha"), "REQUEST_INVARIANT_RECEIPT_GIT_BLOB_SHA"
            ),
            "cross_component_state_preserved": receipt.get(
                "cross_component_state_preserved"
            )
            is True,
            "evidence_provenance_complete": receipt.get(
                "evidence_provenance_complete"
            )
            is True,
            "zero_critical_composition_failures": receipt.get(
                "zero_critical_composition_failures"
            )
            is True,
            "independent_or_objective": receipt.get("independent_or_objective") is True,
        }
        if not all(
            normalized["invariant_receipt"][key]
            for key in (
                "cross_component_state_preserved",
                "evidence_provenance_complete",
                "zero_critical_composition_failures",
                "independent_or_objective",
            )
        ):
            raise EffectContractError("REQUEST_INVARIANT_RECEIPT_NOT_ALL_TRUE")

    return normalized


def verify_effect_request(
    request: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a content-bound precommit permit or fail closed.

    Exact tuple matching is intentional. No prefix, wildcard, ambient fallback,
    implicit inheritance, diagnostic-output interpretation, or closest-rule
    behavior exists in this reference contract.
    """

    try:
        normalized_policy = _normalize_policy(policy)
        normalized_request = _normalize_request(request)

        if normalized_request["authority_epoch"] != normalized_policy["authority_epoch"]:
            raise EffectContractError("AUTHORITY_EPOCH_MISMATCH")

        wanted = (
            normalized_request["subject"],
            normalized_request["effect_class"],
            normalized_request["resource"],
            normalized_request["operation"],
            normalized_request["scope"],
        )
        granted = {
            (
                rule["subject"],
                rule["effect_class"],
                rule["resource"],
                rule["operation"],
                rule["scope"],
            )
            for rule in normalized_policy["rules"]
        }
        if wanted not in granted:
            raise EffectContractError("NO_EXACT_AUTHORITY_GRANT")

        policy_digest = _sha256(normalized_policy)
        request_digest = _sha256(normalized_request)
        permit_material = {
            "schema": SCHEMA,
            "policy_sha256": policy_digest,
            "request_sha256": request_digest,
            "request_id": normalized_request["request_id"],
            "authority_epoch": normalized_policy["authority_epoch"],
            "exact_grant_match": True,
            "composition_receipt_required": normalized_request["effect_class"]
            in _COMPOSITION_CLASSES,
        }
        permit_sha256 = _sha256(permit_material)

        return {
            "schema": SCHEMA,
            "status": "PASS_STRUCTURAL_PRECOMMIT",
            "request_id": normalized_request["request_id"],
            "effect_class": normalized_request["effect_class"],
            "policy_sha256": policy_digest,
            "request_sha256": request_digest,
            "permit_sha256": permit_sha256,
            "exact_grant_match": True,
            "no_wildcard_or_ambient_fallback": True,
            "auxiliary_output_has_zero_positive_authority": True,
            "composition_receipt_bound": normalized_request["effect_class"]
            in _COMPOSITION_CLASSES,
            "semantic_receipt_byte_verification_still_required": normalized_request[
                "effect_class"
            ]
            in _COMPOSITION_CLASSES,
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }
