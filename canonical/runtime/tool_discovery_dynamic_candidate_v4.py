"""Tool Discovery policy V4: global least-cost soundness repair.

V3 could select a sufficient visible tool while an unqueried authoritative source
still contained a cheaper sufficient tool.  Without a verified lower bound on every
unqueried source, global least-cost selection is information-theoretically impossible.

V4 therefore exhausts every available declared discovery source before any capability
probe or selection.  After discovery is complete it delegates the already-verified
constraint/evidence/epoch mechanics to V3.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3


def _queried_sources(public: Mapping[str, Any]) -> set[str]:
    return {
        str(x.get("source_id"))
        for x in public.get("discovery_receipts", [])
        if isinstance(x, Mapping) and x.get("kind") == "DISCOVERY_RESULT"
    }


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    required = sorted(
        {str(x) for x in public.get("required_capabilities", []) if str(x)}
    )
    if not required:
        return {"action": "ESCALATE", "reason": "NO_REQUIRED_CAPABILITIES"}

    queried = _queried_sources(public)
    sources = [
        s
        for s in public.get("discovery_sources", [])
        if isinstance(s, Mapping)
        and s.get("available") is True
        and str(s.get("source_id") or "") not in queried
    ]
    sources.sort(
        key=lambda s: (
            float(s.get("cost", 0.0)),
            str(s.get("source_id") or ""),
        )
    )
    if sources:
        return {
            "action": "DISCOVER",
            "source_id": str(sources[0].get("source_id") or ""),
            "query": " ".join(required),
        }

    return v3.next_action(public)
