"""Tool Discovery policy V8: converge transferable catalogs with finite-cost and strict-evidence firewalls.

V7-transfer fixes later-task reuse, but inherits two proof-breaking input semantics:
1. non-finite tool/source costs can enter the least-cost order;
2. malformed SAFE_CAPABILITY_PROBE receipts are coerced instead of rejected
   (supported=None becomes negative evidence; bool epochs can equal integer epochs).

V8 preserves V7's restart boundary and task-independent catalog receipts, then
fail-closes these two ambiguity classes before delegating to V7.

This module grants zero acceptance/capability/family/execution/promotion credit.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v7 as v7


def _finite_nonnegative_cost(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        x = float(value)
    except (OverflowError, TypeError, ValueError):
        return False
    return math.isfinite(x) and x >= 0.0


def _cost_firewall(public: Mapping[str, Any]) -> str | None:
    sources = public.get("discovery_sources", [])
    if isinstance(sources, list):
        for source in sources:
            if isinstance(source, Mapping) and not _finite_nonnegative_cost(source.get("cost")):
                return "DISCOVERY_SOURCE_COST_NOT_FINITE_NONNEGATIVE"

    visible = public.get("visible_tools", [])
    if isinstance(visible, list):
        for row in visible:
            if isinstance(row, Mapping) and not _finite_nonnegative_cost(row.get("cost")):
                return "TOOL_COST_NOT_FINITE_NONNEGATIVE"

    receipts = public.get("discovery_receipts", [])
    if isinstance(receipts, list):
        for rec in receipts:
            if not isinstance(rec, Mapping) or rec.get("kind") != "DISCOVERY_RESULT":
                continue
            tools = rec.get("tools")
            if not isinstance(tools, list):
                continue
            for row in tools:
                if isinstance(row, Mapping) and not _finite_nonnegative_cost(row.get("cost")):
                    return "TOOL_COST_NOT_FINITE_NONNEGATIVE"
    return None


def _probe_receipt_firewall(public: Mapping[str, Any]) -> str | None:
    receipts = public.get("prior_probe_receipts", [])
    if not isinstance(receipts, list):
        # Preserve V5/V7's exact container-shape verdict downstream.
        return None

    for rec in receipts:
        if not isinstance(rec, Mapping):
            return "PROBE_RECEIPT_NOT_OBJECT"
        if rec.get("kind") != "SAFE_CAPABILITY_PROBE":
            continue

        tid = rec.get("tool_id")
        cap = rec.get("capability")
        epoch = rec.get("epoch")
        supported = rec.get("supported")

        if not isinstance(tid, str) or not tid:
            return "PROBE_RECEIPT_TOOL_ID_INVALID"
        if not isinstance(cap, str) or not cap:
            return "PROBE_RECEIPT_CAPABILITY_ID_INVALID"
        if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
            return "PROBE_RECEIPT_EPOCH_INVALID"
        if not isinstance(supported, bool):
            return "PROBE_RECEIPT_SUPPORTED_NOT_BOOL"
    return None


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    # Version/authority invalidation is causally prior to every other check.
    ev = v7._restart_event(public)
    if ev is not None:
        return v7.next_action(public)

    err = _cost_firewall(public)
    if err:
        return {"action": "ESCALATE", "reason": err}

    err = _probe_receipt_firewall(public)
    if err:
        return {"action": "ESCALATE", "reason": err}

    return v7.next_action(public)
