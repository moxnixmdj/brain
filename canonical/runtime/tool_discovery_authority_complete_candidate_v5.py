"""Authority-derived complete-interface adapter for tool discovery V5.

V5 removes the caller-asserted registry-completeness seam from the universal route.
When the matched harness exposes a TOOL_AUTHORITY object, V5 mechanically derives
the discovery registry from every action in that authority and then delegates to
the already hardened V4 policy. A caller-supplied smaller registry is overwritten.

The authority boundary is exactly the frozen same-harness/tool-authority boundary:
an action absent from that authority is unavailable to both matched routes. Each
DISCOVERY_SOURCE action must itself declare exhaustive current-list semantics.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from canonical.runtime import tool_discovery_complete_interface_candidate_v4 as v4


class ToolDiscoveryV5Error(ValueError):
    pass


def _canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(v: Any) -> str:
    return hashlib.sha256(_canon(v).encode("utf-8")).hexdigest()


def registry_from_tool_authority(public: Mapping[str, Any]) -> dict[str, Any]:
    authority = public.get("tool_authority")
    if not isinstance(authority, Mapping):
        raise ToolDiscoveryV5Error("TOOL_AUTHORITY_MISSING")
    if authority.get("kind") != "TOOL_AUTHORITY":
        raise ToolDiscoveryV5Error("TOOL_AUTHORITY_KIND_INVALID")

    epoch = authority.get("epoch")
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
        raise ToolDiscoveryV5Error("TOOL_AUTHORITY_EPOCH_INVALID")

    actions = authority.get("actions")
    if not isinstance(actions, list):
        raise ToolDiscoveryV5Error("TOOL_AUTHORITY_ACTIONS_INVALID")

    normalized_actions: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    action_ids: set[str] = set()
    source_ids: set[str] = set()

    for raw in actions:
        if not isinstance(raw, Mapping):
            raise ToolDiscoveryV5Error("TOOL_AUTHORITY_ACTION_NOT_OBJECT")
        aid = raw.get("action_id")
        kind = raw.get("kind")
        if not isinstance(aid, str) or not aid or aid in action_ids:
            raise ToolDiscoveryV5Error("TOOL_AUTHORITY_ACTION_ID_INVALID_OR_DUPLICATE")
        if not isinstance(kind, str) or not kind:
            raise ToolDiscoveryV5Error("TOOL_AUTHORITY_ACTION_KIND_INVALID:" + aid)
        action_ids.add(aid)

        normalized_actions.append({
            "action_id": aid,
            "kind": kind,
            "source_id": raw.get("source_id"),
            "epoch": raw.get("epoch"),
            "cost": raw.get("cost"),
            "available": raw.get("available") is True,
            "authorized": raw.get("authorized") is True,
            "result_semantics": raw.get("result_semantics"),
        })

        if kind != "DISCOVERY_SOURCE":
            continue

        sid = raw.get("source_id")
        sep = raw.get("epoch")
        cost = raw.get("cost")
        if not isinstance(sid, str) or not sid or sid in source_ids:
            raise ToolDiscoveryV5Error("DISCOVERY_SOURCE_ID_INVALID_OR_DUPLICATE")
        if raw.get("result_semantics") != "EXHAUSTIVE_CURRENT_TOOL_LIST":
            raise ToolDiscoveryV5Error("DISCOVERY_SOURCE_RESULT_NOT_EXHAUSTIVE:" + sid)
        if not isinstance(sep, int) or isinstance(sep, bool) or sep < 0:
            raise ToolDiscoveryV5Error("DISCOVERY_SOURCE_EPOCH_INVALID:" + sid)
        if not isinstance(cost, (int, float)) or isinstance(cost, bool) or float(cost) < 0:
            raise ToolDiscoveryV5Error("DISCOVERY_SOURCE_COST_INVALID:" + sid)

        source_ids.add(sid)
        sources.append({
            "source_id": sid,
            "epoch": sep,
            "cost": float(cost),
            "available": raw.get("available") is True,
            "authorized": raw.get("authorized") is True,
        })

    declared = authority.get("action_manifest_sha256")
    expected = _sha(sorted(normalized_actions, key=lambda x: x["action_id"]))
    if declared != expected:
        raise ToolDiscoveryV5Error("TOOL_AUTHORITY_MANIFEST_MISMATCH")

    source_rows = sorted(sources, key=lambda x: x["source_id"])
    return {
        "kind": "COMPLETE_DISCOVERY_REGISTRY",
        "complete": True,
        "epoch": epoch,
        "sources": source_rows,
        "source_manifest_sha256": _sha(source_rows),
    }


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    if "tool_authority" not in public:
        return v4.next_action(public)

    try:
        registry = registry_from_tool_authority(public)
    except ToolDiscoveryV5Error as exc:
        return {"action": "ESCALATE", "reason": str(exc)}

    derived = dict(public)
    # Deliberately overwrite any caller-supplied subset or stale registry.
    derived["discovery_registry"] = registry
    return v4.next_action(derived)
