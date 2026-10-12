"""Exact structural bridge from the zero-ambient launcher envelope to both
Project Brain effect-broker admission and the Root3 proof-carrying effect guard.

This module intentionally grants no material commit authority. It proves that a
launcher-visible typed request is the same payload/resource/operation admitted by
the content-addressed broker grant and the same effect admitted by the exact
Root3 authority policy. Receipt-byte verification and carrier enforcement stay
separate promotion gates.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys
from collections.abc import Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_ROOT3_EFFECT_BROKER_BRIDGE_V1"
ENVELOPE_TYPE = "root3_brokered_effect"

_COMPATIBLE_CLASSES = {
    "INFORMATION_READ": frozenset({"network_request", "external_tool_call"}),
    "REPO_WRITE": frozenset({"durable_write", "state_append", "evidence_append"}),
    "PACKAGE_ENV_MUTATION": frozenset({"process_exec"}),
    "EXTERNAL_MUTATION": frozenset({"network_request", "external_tool_call"}),
    "FINAL_OUTPUT": frozenset({"final_output"}),
}
_COMPOSITION_CLASSES = frozenset({"state_append", "evidence_append", "final_output"})


class BridgeError(ValueError):
    pass


def _load_sibling(module_name: str, filename: str):
    path = pathlib.Path(__file__).resolve().with_name(filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise BridgeError("MODULE_LOAD_FAILED:" + filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _sha256(value: Any) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise BridgeError(label + "_INVALID")
    return value.strip()


def _expected_provenance(generic_request: Mapping[str, Any]) -> set[str]:
    return {
        "effect_request_sha256:" + str(generic_request["request_sha256"]),
        "mission_id:" + str(generic_request["mission_id"]),
        "action_ref:" + str(generic_request["action_ref"]),
    }


def _verify_cross_contract_binding(
    generic_request: Mapping[str, Any],
    root3_request: Mapping[str, Any],
) -> dict[str, Any]:
    for field in ("resource", "operation", "payload_sha256"):
        if generic_request.get(field) != root3_request.get(field):
            raise BridgeError("CROSS_CONTRACT_" + field.upper() + "_MISMATCH")

    effect_kind = _token(generic_request.get("effect_kind"), "GENERIC_EFFECT_KIND")
    effect_class = _token(root3_request.get("effect_class"), "ROOT3_EFFECT_CLASS")
    allowed = _COMPATIBLE_CLASSES.get(effect_kind)
    if allowed is None or effect_class not in allowed:
        raise BridgeError(
            "CROSS_CONTRACT_EFFECT_CLASS_INCOMPATIBLE:"
            + effect_kind
            + ":"
            + effect_class
        )

    provenance = root3_request.get("provenance_refs")
    if not isinstance(provenance, list) or any(not isinstance(x, str) for x in provenance):
        raise BridgeError("ROOT3_PROVENANCE_REFS_INVALID")
    missing = sorted(_expected_provenance(generic_request) - set(provenance))
    if missing:
        raise BridgeError("CROSS_CONTRACT_PROVENANCE_BINDING_MISSING:" + ",".join(missing))

    if effect_class in _COMPOSITION_CLASSES:
        if root3_request.get("pre_state_sha256") != generic_request.get(
            "capsule_head_sha256"
        ):
            raise BridgeError("CROSS_CONTRACT_PRE_STATE_MISMATCH")

    return {
        "effect_kind": effect_kind,
        "effect_class": effect_class,
        "resource": generic_request["resource"],
        "operation": generic_request["operation"],
        "payload_sha256": generic_request["payload_sha256"],
        "provenance_binding_complete": True,
        "composition_pre_state_bound": effect_class in _COMPOSITION_CLASSES,
    }


def admit(
    envelope: Mapping[str, Any],
    effect_grant: Mapping[str, Any],
    root3_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a content-bound structural permit or fail closed.

    The trusted parent supplies the effect grant and Root3 policy. The child may
    only emit the envelope through the zero-ambient launcher stdout protocol.
    This function never performs the requested effect.
    """
    try:
        if not isinstance(envelope, Mapping):
            raise BridgeError("ENVELOPE_NOT_OBJECT")
        if set(envelope) != {"type", "request_id", "effect_request", "root3_request"}:
            raise BridgeError("ENVELOPE_FIELDS_NOT_EXACT")
        if envelope.get("type") != ENVELOPE_TYPE:
            raise BridgeError("ENVELOPE_TYPE_INVALID")

        generic_request_raw = envelope.get("effect_request")
        root3_request = envelope.get("root3_request")
        if not isinstance(generic_request_raw, Mapping):
            raise BridgeError("EFFECT_REQUEST_NOT_OBJECT")
        if not isinstance(root3_request, Mapping):
            raise BridgeError("ROOT3_REQUEST_NOT_OBJECT")

        effect_broker = _load_sibling(
            "project_brain_bridge_effect_broker", "effect_broker_contract_v1.py"
        )
        root3 = _load_sibling(
            "project_brain_bridge_root3_guard", "root3_proof_carrying_effect_v1.py"
        )

        generic_request = effect_broker.verify_request(generic_request_raw)
        request_id = _token(envelope.get("request_id"), "REQUEST_ID")
        if request_id != generic_request["request_sha256"]:
            raise BridgeError("REQUEST_ID_NOT_EXACT_EFFECT_REQUEST_SHA256")

        broker_verdict = effect_broker.admit(generic_request, effect_grant)
        if broker_verdict.get("status") != "ALLOW_PRECOMMIT" or broker_verdict.get(
            "allowed"
        ) is not True:
            raise BridgeError(
                "EFFECT_BROKER_DENIED:" + str(broker_verdict.get("reason") or "UNKNOWN")
            )

        cross = _verify_cross_contract_binding(generic_request, root3_request)

        root3_verdict = root3.verify_effect_request(
            {**root3_request, "request_id": root3_request.get("request_id", request_id)},
            root3_policy,
        )
        if root3_verdict.get("status") != "PASS_STRUCTURAL_PRECOMMIT":
            raise BridgeError(
                "ROOT3_GUARD_DENIED:" + str(root3_verdict.get("reason") or "UNKNOWN")
            )

        material = {
            "schema": SCHEMA,
            "effect_request_sha256": generic_request["request_sha256"],
            "effect_grant_sha256": broker_verdict["grant_sha256"],
            "root3_request_sha256": root3_verdict["request_sha256"],
            "root3_policy_sha256": root3_verdict["policy_sha256"],
            "root3_permit_sha256": root3_verdict["permit_sha256"],
            "cross_contract": cross,
        }
        return {
            **material,
            "status": "PASS_STRUCTURAL_BRIDGED_PRECOMMIT",
            "bridge_permit_sha256": _sha256(material),
            "launcher_envelope_bound": True,
            "effect_broker_bound": True,
            "root3_guard_bound": True,
            "receipt_byte_verification_still_required": True,
            "carrier_enforcement_still_required": True,
            "material_effects_committed": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "material_effects_committed": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
        }
