"""D-finality V2 with content-bound closure and clean-room replay evidence.

V1 checked useful booleans but did not prove that closure lists were complete,
that control claims were receipt-bound, or that clean-room replays were
genuinely distinct and bound to the same closure state.

V2 closes those gaps. A pass proves a D-finality certificate only. It grants no
terminal authority or terminal credit.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_D_FINALITY_GATE_V2"


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _valid_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "D_FINALITY_OPEN",
        "reason": reason,
        "d_finality": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def route_binding_digest(row: Mapping[str, Any]) -> str:
    return _sha({
        "active_manifest_sha256": row.get("active_manifest_sha256"),
        "route_root_sha256": row.get("route_root_sha256"),
        "independently_verified": row.get("independently_verified"),
        "verifier_id": row.get("verifier_id"),
        "result_sha256": row.get("result_sha256"),
    })


def control_receipt_digest(row: Mapping[str, Any]) -> str:
    return _sha({
        "name": row.get("name"),
        "identity_sha256": row.get("identity_sha256"),
        "owned_or_sealed": row.get("owned_or_sealed"),
        "right_to_use": row.get("right_to_use"),
        "independently_verified": row.get("independently_verified"),
        "verifier_id": row.get("verifier_id"),
    })


def closure_certificate_digest(row: Mapping[str, Any]) -> str:
    return _sha({
        "closure_kind": row.get("closure_kind"),
        "route_root_sha256": row.get("route_root_sha256"),
        "item_identity_sha256": sorted(row.get("item_identity_sha256") or []),
        "complete": row.get("complete"),
        "independently_verified": row.get("independently_verified"),
        "verifier_id": row.get("verifier_id"),
        "method_id": row.get("method_id"),
        "result_sha256": row.get("result_sha256"),
    })


def environment_receipt_digest(row: Mapping[str, Any]) -> str:
    return _sha({
        "zero_ambient_authority": row.get("zero_ambient_authority"),
        "general_network_available": row.get("general_network_available"),
        "environment_image_sha256": row.get("environment_image_sha256"),
        "launcher_policy_sha256": row.get("launcher_policy_sha256"),
        "independently_verified": row.get("independently_verified"),
        "verifier_id": row.get("verifier_id"),
    })


def isolation_receipt_digest(row: Mapping[str, Any]) -> str:
    return _sha({
        "performed": row.get("performed"),
        "donor_root_sha256": row.get("donor_root_sha256"),
        "post_isolation_route_root_sha256": row.get(
            "post_isolation_route_root_sha256"
        ),
        "independently_verified": row.get("independently_verified"),
        "verifier_id": row.get("verifier_id"),
        "result_sha256": row.get("result_sha256"),
    })


def replay_receipt_digest(row: Mapping[str, Any]) -> str:
    return _sha({
        "replay_id": row.get("replay_id"),
        "carrier_id": row.get("carrier_id"),
        "verifier_id": row.get("verifier_id"),
        "active_manifest_sha256": row.get("active_manifest_sha256"),
        "route_root_sha256": row.get("route_root_sha256"),
        "dependency_closure_receipt_sha256": row.get(
            "dependency_closure_receipt_sha256"
        ),
        "effect_closure_receipt_sha256": row.get(
            "effect_closure_receipt_sha256"
        ),
        "environment_receipt_sha256": row.get("environment_receipt_sha256"),
        "isolation_receipt_sha256": row.get("isolation_receipt_sha256"),
        "pass": row.get("pass"),
        "independently_verified": row.get("independently_verified"),
        "result_sha256": row.get("result_sha256"),
    })


def _validate_closure(kind, route_root, rows, certificate):
    if not isinstance(rows, list):
        return False, "CLOSURE_ITEMS_INVALID", []
    identities = []
    names = set()
    for row in rows:
        if not isinstance(row, Mapping):
            return False, "CLOSURE_ITEM_INVALID", []
        if not _nonempty(row.get("name")):
            return False, "CLOSURE_ITEM_NAME_INVALID", []
        if row["name"] in names:
            return False, "CLOSURE_ITEM_NAME_DUPLICATE", []
        names.add(row["name"])
        if not _valid_sha(row.get("identity_sha256")):
            return False, "CLOSURE_ITEM_IDENTITY_INVALID", []
        identities.append(row["identity_sha256"])
        if row.get("owned_or_sealed") is not True or row.get("right_to_use") is not True:
            return False, "UNOWNED_OR_UNCONTROLLED_RESOURCE", []
        if row.get("independently_verified") is not True or not _nonempty(row.get("verifier_id")):
            return False, "CLOSURE_ITEM_CONTROL_UNVERIFIED", []
        if row.get("control_receipt_sha256") != control_receipt_digest(row):
            return False, "CLOSURE_ITEM_CONTROL_RECEIPT_MISMATCH", []
    if len(identities) != len(set(identities)):
        return False, "CLOSURE_ITEM_IDENTITY_DUPLICATE", []

    if not isinstance(certificate, Mapping):
        return False, "CLOSURE_CERTIFICATE_MISSING", []
    if certificate.get("closure_kind") != kind:
        return False, "CLOSURE_CERTIFICATE_KIND_MISMATCH", []
    if certificate.get("route_root_sha256") != route_root:
        return False, "CLOSURE_CERTIFICATE_ROUTE_MISMATCH", []
    if sorted(certificate.get("item_identity_sha256") or []) != sorted(identities):
        return False, "CLOSURE_CERTIFICATE_ITEM_SET_MISMATCH", []
    if (
        certificate.get("complete") is not True
        or certificate.get("independently_verified") is not True
        or not _nonempty(certificate.get("verifier_id"))
        or not _nonempty(certificate.get("method_id"))
        or not _valid_sha(certificate.get("result_sha256"))
    ):
        return False, "CLOSURE_COMPLETENESS_UNPROVED", []
    if certificate.get("receipt_sha256") != closure_certificate_digest(certificate):
        return False, "CLOSURE_CERTIFICATE_SELF_DIGEST_MISMATCH", []
    return True, "OK", sorted(identities)


def verify_finality(state: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(state, Mapping):
            return _fail("STATE_NOT_MAPPING")
        active_manifest = state.get("active_manifest_sha256")
        route_root = state.get("route_root_sha256")
        if not _valid_sha(active_manifest):
            return _fail("ACTIVE_MANIFEST_INVALID")
        if not _valid_sha(route_root):
            return _fail("ROUTE_ROOT_INVALID")

        binding = state.get("route_root_binding")
        if (
            not isinstance(binding, Mapping)
            or binding.get("active_manifest_sha256") != active_manifest
            or binding.get("route_root_sha256") != route_root
            or binding.get("independently_verified") is not True
            or not _nonempty(binding.get("verifier_id"))
            or not _valid_sha(binding.get("result_sha256"))
        ):
            return _fail("ROUTE_ROOT_BINDING_INVALID")
        if binding.get("receipt_sha256") != route_binding_digest(binding):
            return _fail("ROUTE_ROOT_BINDING_SELF_DIGEST_MISMATCH")

        dep_ok, dep_reason, dep_ids = _validate_closure(
            "dependency", route_root,
            state.get("dependency_closure"),
            state.get("dependency_closure_certificate"),
        )
        if not dep_ok:
            return _fail(dep_reason, closure="dependency")
        eff_ok, eff_reason, effect_ids = _validate_closure(
            "effect", route_root,
            state.get("effect_closure"),
            state.get("effect_closure_certificate"),
        )
        if not eff_ok:
            return _fail(eff_reason, closure="effect")

        dep_cert = state["dependency_closure_certificate"]
        eff_cert = state["effect_closure_certificate"]

        env = state.get("replay_environment")
        if (
            not isinstance(env, Mapping)
            or env.get("zero_ambient_authority") is not True
            or env.get("general_network_available") is not False
            or not _valid_sha(env.get("environment_image_sha256"))
            or not _valid_sha(env.get("launcher_policy_sha256"))
            or env.get("independently_verified") is not True
            or not _nonempty(env.get("verifier_id"))
        ):
            return _fail("ZERO_AMBIENT_REPLAY_ENVIRONMENT_UNPROVED")
        if env.get("receipt_sha256") != environment_receipt_digest(env):
            return _fail("REPLAY_ENVIRONMENT_SELF_DIGEST_MISMATCH")

        isolation = state.get("donor_isolation")
        if (
            not isinstance(isolation, Mapping)
            or isolation.get("performed") is not True
            or not _valid_sha(isolation.get("donor_root_sha256"))
            or isolation.get("post_isolation_route_root_sha256") != route_root
            or isolation.get("independently_verified") is not True
            or not _nonempty(isolation.get("verifier_id"))
            or not _valid_sha(isolation.get("result_sha256"))
        ):
            return _fail("DONOR_ISOLATION_UNPROVED")
        if isolation.get("receipt_sha256") != isolation_receipt_digest(isolation):
            return _fail("DONOR_ISOLATION_SELF_DIGEST_MISMATCH")

        replays = state.get("clean_room_replays")
        if not isinstance(replays, list) or len(replays) < 2:
            return _fail("CLEAN_ROOM_REPLAY_COUNT_INSUFFICIENT")
        replay_ids = set()
        carriers = set()
        verifiers = set()
        replay_receipts = []
        for row in replays:
            if not isinstance(row, Mapping):
                return _fail("CLEAN_ROOM_REPLAY_INVALID")
            for key in ("replay_id", "carrier_id", "verifier_id"):
                if not _nonempty(row.get(key)):
                    return _fail("CLEAN_ROOM_REPLAY_IDENTITY_INVALID")
            if row["replay_id"] in replay_ids:
                return _fail("CLEAN_ROOM_REPLAY_ID_DUPLICATE")
            replay_ids.add(row["replay_id"])
            carriers.add(row["carrier_id"])
            verifiers.add(row["verifier_id"])
            if (
                row.get("pass") is not True
                or row.get("independently_verified") is not True
                or not _valid_sha(row.get("result_sha256"))
                or row.get("active_manifest_sha256") != active_manifest
                or row.get("route_root_sha256") != route_root
                or row.get("dependency_closure_receipt_sha256") != dep_cert["receipt_sha256"]
                or row.get("effect_closure_receipt_sha256") != eff_cert["receipt_sha256"]
                or row.get("environment_receipt_sha256") != env["receipt_sha256"]
                or row.get("isolation_receipt_sha256") != isolation["receipt_sha256"]
            ):
                return _fail("CLEAN_ROOM_REPLAY_BINDING_INVALID")
            if row.get("receipt_sha256") != replay_receipt_digest(row):
                return _fail("CLEAN_ROOM_REPLAY_SELF_DIGEST_MISMATCH")
            replay_receipts.append(row["receipt_sha256"])

        if len(carriers) < 2:
            return _fail("CLEAN_ROOM_CARRIER_DIVERSITY_INSUFFICIENT")
        if len(verifiers) < 2:
            return _fail("CLEAN_ROOM_VERIFIER_DIVERSITY_INSUFFICIENT")

        core = {
            "active_manifest_sha256": active_manifest,
            "route_root_sha256": route_root,
            "route_root_binding_receipt_sha256": binding["receipt_sha256"],
            "dependency_ids": dep_ids,
            "dependency_closure_receipt_sha256": dep_cert["receipt_sha256"],
            "effect_ids": effect_ids,
            "effect_closure_receipt_sha256": eff_cert["receipt_sha256"],
            "replay_environment_receipt_sha256": env["receipt_sha256"],
            "donor_isolation_receipt_sha256": isolation["receipt_sha256"],
            "clean_room_replay_receipt_sha256": sorted(replay_receipts),
        }
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__D_FINALITY_V2_CONTENT_BOUND_CLOSED_REPLAY",
            "reason": None,
            **core,
            "finality_receipt_sha256": _sha(core),
            "d_finality": True,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "incremental_spend_usd": 0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
