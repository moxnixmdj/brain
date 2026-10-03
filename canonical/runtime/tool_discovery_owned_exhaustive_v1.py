"""Owned exhaustive Tool Discovery composition V1.

Composes:
- ToolUniverseGateway V1: the sole invocation authority and exact identity enumerator.
- Dynamic Tool Discovery V4: discovery-first, cost-ordered probe/select policy.

The wrapper makes registry-epoch stability explicit. Any registry replacement invalidates
an in-flight episode before V4 can reuse discovery or probe receipts.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4
from canonical.runtime.tool_universe_gateway_v1 import (
    GatewayError,
    ToolUniverseGateway,
)

SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_OWNED_EXHAUSTIVE_V1"


def _public(gateway: ToolUniverseGateway, state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "required_capabilities": list(state.get("required_capabilities", [])),
        "constraint": state.get("constraint"),
        "visible_tools": [],
        "discovery_sources": [gateway.discovery_source()],
        "discovery_receipts": [dict(x) for x in state.get("discovery_receipts", [])],
        "prior_probe_receipts": [dict(x) for x in state.get("prior_probe_receipts", [])],
        "version_events": [],
    }


def next_action(gateway: ToolUniverseGateway, state: Mapping[str, Any]) -> dict[str, Any]:
    episode_epoch = state.get("episode_registry_epoch")
    if episode_epoch != gateway.epoch:
        return {
            "action": "ESCALATE",
            "reason": "REGISTRY_EPOCH_CHANGED_RESTART_EPISODE",
            "current_registry_epoch": gateway.epoch,
        }
    return v4.next_action(_public(gateway, state))


def apply_discovery(
    gateway: ToolUniverseGateway,
    state: dict[str, Any],
    action: Mapping[str, Any],
) -> dict[str, Any]:
    if state.get("episode_registry_epoch") != gateway.epoch:
        raise GatewayError("EPOCH_CHANGED_RESTART_EPISODE")
    source = gateway.discovery_source()
    if action.get("action") != "DISCOVER":
        raise GatewayError("EXPECTED_DISCOVER_ACTION")
    if action.get("source_id") != source["source_id"]:
        raise GatewayError("DISCOVERY_SOURCE_MISMATCH")
    receipt = gateway.discover()
    state.setdefault("discovery_receipts", []).append(receipt)
    return receipt


def record_probe_result(
    gateway: ToolUniverseGateway,
    state: dict[str, Any],
    action: Mapping[str, Any],
    *,
    supported: bool,
) -> dict[str, Any]:
    if state.get("episode_registry_epoch") != gateway.epoch:
        raise GatewayError("EPOCH_CHANGED_RESTART_EPISODE")
    if action.get("action") != "PROBE":
        raise GatewayError("EXPECTED_PROBE_ACTION")
    tid = str(action.get("tool_id") or "")
    cap = str(action.get("capability") or "")
    if not cap:
        raise GatewayError("EMPTY_CAPABILITY")
    gateway.gate_invoke(tid, episode_epoch=gateway.epoch)
    receipt = {
        "kind": "SAFE_CAPABILITY_PROBE",
        "tool_id": tid,
        "capability": cap,
        "epoch": 0,
        "supported": bool(supported),
    }
    state.setdefault("prior_probe_receipts", []).append(receipt)
    return receipt


def gate_selection(
    gateway: ToolUniverseGateway,
    state: Mapping[str, Any],
    action: Mapping[str, Any],
):
    if action.get("action") != "SELECT":
        raise GatewayError("EXPECTED_SELECT_ACTION")
    epoch = state.get("episode_registry_epoch")
    if not isinstance(epoch, int) or isinstance(epoch, bool):
        raise GatewayError("INVALID_EPISODE_EPOCH")
    return gateway.gate_invoke(str(action.get("tool_id") or ""), episode_epoch=epoch)


def new_episode(
    gateway: ToolUniverseGateway,
    *,
    required_capabilities: list[str],
    constraint: Any = None,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "episode_registry_epoch": gateway.epoch,
        "required_capabilities": list(required_capabilities),
        "constraint": constraint,
        "discovery_receipts": [],
        "prior_probe_receipts": [],
    }
