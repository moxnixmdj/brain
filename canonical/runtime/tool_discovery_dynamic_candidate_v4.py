"""Complete-interface-first dynamic Tool Discovery policy V4.

V3 can select or probe a currently visible route before querying an unqueried
authoritative discovery source. Under a complete discovery-interface contract,
that ordering is insufficient for a universal least-cost claim: a cheaper
sufficient route may still be undiscovered.

V4 makes one deliberately small semantic change. During a stable decision
episode it exhausts every available unqueried discovery source before any
PROBE or SELECT. Once source exhaustion is evidenced by discovery receipts, it
delegates unchanged filtering, current-epoch evidence handling, probing,
least-cost ordering, selection, version invalidation, and escalation to V3.

This module grants no acceptance, capability, family, execution, or promotion
credit. A complete discovery-interface instance and independent verification
remain separate obligations.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3


def _required(public: Mapping[str, Any]) -> list[str]:
    return sorted({
        str(x)
        for x in public.get("required_capabilities", [])
        if str(x)
    })


def _queried_sources(public: Mapping[str, Any]) -> set[str]:
    return {
        str(row.get("source_id") or "")
        for row in public.get("discovery_receipts", [])
        if isinstance(row, Mapping)
        and row.get("kind") == "DISCOVERY_RESULT"
        and str(row.get("source_id") or "")
    }


def _unqueried_available_sources(
    public: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    queried = _queried_sources(public)
    rows = [
        row
        for row in public.get("discovery_sources", [])
        if isinstance(row, Mapping)
        and row.get("available") is True
        and str(row.get("source_id") or "")
        and str(row.get("source_id") or "") not in queried
    ]
    rows.sort(
        key=lambda row: (
            float(row.get("cost", 0.0)),
            str(row.get("source_id") or ""),
        )
    )
    return rows


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    required = _required(public)
    if not required:
        return v3.next_action(public)

    sources = _unqueried_available_sources(public)
    if sources:
        return {
            "action": "DISCOVER",
            "source_id": str(sources[0].get("source_id") or ""),
            "query": " ".join(required),
        }

    # Only after every currently available authoritative discovery source has a
    # receipt do we allow the unchanged V3 evidence/probe/select/escalate logic
    # to act. Under a separately verified complete-interface instance this
    # prevents a visible expensive route from preempting a cheaper undiscovered
    # sufficient route.
    return v3.next_action(public)
