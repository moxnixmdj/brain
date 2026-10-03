"""Tool Discovery policy V7: V6 plus finite-cost firewall.

V6 repairs stale discovery metadata across tool-version changes. V7 closes the
remaining numeric-order hole inherited from V5: NaN and infinities are Python
floats, but they do not form the finite nonnegative total order required by the
least-cost proof. Decision-relevant source and tool costs are therefore
validated before V6/V5 may order or select them.

Zero acceptance/family/execution/promotion credit is granted here.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v6 as v6


def _finite_nonnegative_cost(value: Any) -> bool:
    return bool(
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and float(value) >= 0.0
    )


def _validate_tool_row(row: Any) -> str | None:
    if not isinstance(row, Mapping):
        return "TOOL_METADATA_NOT_OBJECT"
    if not _finite_nonnegative_cost(row.get("cost")):
        return "TOOL_COST_NOT_FINITE_NONNEGATIVE"
    return None


def _cost_firewall(public: Mapping[str, Any]) -> str | None:
    sources = public.get("discovery_sources", [])
    if not isinstance(sources, list):
        # Preserve the exact V5/V6 shape error downstream.
        return None
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        if not _finite_nonnegative_cost(source.get("cost")):
            return "DISCOVERY_SOURCE_COST_NOT_FINITE_NONNEGATIVE"

    visible = public.get("visible_tools", [])
    if not isinstance(visible, list):
        return None
    for row in visible:
        err = _validate_tool_row(row)
        if err:
            return err

    receipts = public.get("discovery_receipts", [])
    if not isinstance(receipts, list):
        return None
    for rec in receipts:
        if not isinstance(rec, Mapping) or rec.get("kind") != "DISCOVERY_RESULT":
            continue
        tools = rec.get("tools")
        if not isinstance(tools, list):
            # Preserve the exact receipt-shape failure downstream.
            continue
        for row in tools:
            err = _validate_tool_row(row)
            if err:
                return err
    return None


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    # Preserve V6's episode-restart semantics as the first causal boundary.
    ev = v6._version_change(public)
    if ev is not None:
        return v6.next_action(public)

    err = _cost_firewall(public)
    if err:
        return {"action": "ESCALATE", "reason": err}
    return v6.next_action(public)
