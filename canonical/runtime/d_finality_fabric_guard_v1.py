"""Fail-closed D-finality guard for the canonical Cognitive Fabric V1.

This module does not create D-final authority. It constrains an already-active
D execution epoch at the canonical front door so a caller cannot bypass the
live-capability invoker with direct provider-carrier modes, mutable catalog/meta
surfaces, or implicit post-dispatch learning.

Outside a D epoch every function is a no-op to preserve experimental/live
behavior.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import d_finality_execution_epoch_v1 as d_finality

SCHEMA = "PROJECT_BRAIN_D_FINALITY_FABRIC_GUARD_V1"

# These surfaces select or inspect mutable/open-world state rather than one
# already-bound D capability identity. They require a later snapshot-specific
# contract before being admissible inside a D epoch.
BLOCKED_META_MODES = frozenset({
    "CATALOG",
    "ONE_SHOT_REALITY_CLOSURE",
    "OWNERSHIP_CATALOG",
})

# These provider carriers can select a member capability dynamically. Inside a
# D epoch they must be invoked through LIVE_CAPABILITY so the exact ownership
# identity is checked before dispatch.
IDENTITY_BYPASS_CARRIER_MODES = frozenset({
    "H100_INFERENCE",
    "CERTIFIED_ROUTE",
})

# These mutate durable capability state and/or can widen future authority.
# They remain unavailable inside a D epoch until their effect/state channels
# are explicitly snapshot/broker bound.
UNSNAPSHOTTED_MUTATING_MODES = frozenset({
    "LEARNING_EPISODE",
    "IMPROVEMENT_CYCLE",
})


class DFinalityFabricGuardError(ValueError):
    pass


def active() -> bool:
    return d_finality.has_active_epoch()


def authorize_requested_mode(requested_mode: str) -> dict[str, Any]:
    mode = str(requested_mode or "").strip().upper()
    if not active():
        return {
            "schema": SCHEMA,
            "active": False,
            "status": "NO_ACTIVE_D_EPOCH",
        }
    if mode in BLOCKED_META_MODES:
        raise DFinalityFabricGuardError(
            "D_FINALITY_META_OR_MUTABLE_SURFACE_NOT_SNAPSHOT_BOUND:" + mode
        )
    return {
        "schema": SCHEMA,
        "active": True,
        "status": "PASS__REQUESTED_MODE_NOT_PREBLOCKED",
        "requested_mode": mode,
    }


def authorize_dispatch(mode: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = str(mode or "").strip().upper()
    if not active():
        return {
            "schema": SCHEMA,
            "active": False,
            "status": "NO_ACTIVE_D_EPOCH",
            "mode": normalized,
        }
    if not isinstance(payload, Mapping):
        raise DFinalityFabricGuardError("D_FINALITY_PAYLOAD_NOT_OBJECT")

    if normalized in BLOCKED_META_MODES:
        raise DFinalityFabricGuardError(
            "D_FINALITY_META_OR_MUTABLE_SURFACE_NOT_SNAPSHOT_BOUND:" + normalized
        )
    if normalized in UNSNAPSHOTTED_MUTATING_MODES:
        raise DFinalityFabricGuardError(
            "D_FINALITY_MUTATING_MODE_NOT_STATE_EFFECT_BOUND:" + normalized
        )
    if normalized in IDENTITY_BYPASS_CARRIER_MODES:
        raise DFinalityFabricGuardError(
            "D_FINALITY_IDENTITY_BYPASS_CARRIER_FORBIDDEN_USE_LIVE_CAPABILITY:"
            + normalized
        )

    checked_identity: str
    if normalized == "LIVE_CAPABILITY":
        checked_identity = str(payload.get("capability_id") or "").strip()
        if not checked_identity:
            raise DFinalityFabricGuardError(
                "D_FINALITY_LIVE_CAPABILITY_ID_REQUIRED"
            )
        d_finality.require_capability(checked_identity)
    elif normalized == "BOUND_CAPABILITY":
        local_id = str(payload.get("capability_id") or "").strip()
        if not local_id:
            raise DFinalityFabricGuardError(
                "D_FINALITY_BOUND_CAPABILITY_ID_REQUIRED"
            )
        checked_identity = "bound:" + local_id
        d_finality.require_capability(checked_identity)
    else:
        checked_identity = "engine:" + normalized
        d_finality.require_capability(checked_identity)

    return {
        "schema": SCHEMA,
        "active": True,
        "status": "PASS__D_EPOCH_DISPATCH_AUTHORIZED",
        "mode": normalized,
        "checked_identity": checked_identity,
        "epoch_sha256": d_finality.current_epoch().epoch_sha256,
    }


def implicit_learning_allowed() -> bool:
    """Implicit state mutation is never allowed inside a D epoch."""
    return not active()
