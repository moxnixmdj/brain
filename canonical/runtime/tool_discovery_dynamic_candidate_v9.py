"""Tool Discovery policy V9: V8 authority soundness plus least-cost frontier semantics.

V8 hardens transferable discovery against stale authority/tool epochs, incomplete
catalog authority, malformed route metadata, and nonfinite costs. Its final
decision still iterates tools in (cost, tool_id) order, which can falsely
escalate or probe an unresolved equal-cost peer even when another peer at the
same global minimum cost is already verified sufficient.

V9 preserves V8 for every structural/restart/discovery check and recomputes only
the terminal route decision over the entire minimum-cost non-falsified frontier:
1. select a verified sufficient peer if any exists on the minimum-cost frontier;
2. otherwise consume a safe unresolved fact anywhere on that frontier;
3. otherwise escalate because the least-cost frontier is irreducibly unresolved;
4. never skip a strictly cheaper unresolved frontier for a more expensive route.

Zero acceptance/family/capability/execution/promotion credit is granted here.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5
from canonical.runtime import tool_discovery_dynamic_candidate_v8 as v8

_DECISION_REASONS = {
    "CHEAPER_ADMISSIBLE_ROUTE_UNRESOLVED_NO_SAFE_PROBE",
    "NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY",
}


def _frontier_action(public: Mapping[str, Any]) -> dict[str, Any]:
    required, _ = v5._requirements(public)
    if not required:
        return {"action": "ESCALATE", "reason": "NO_REQUIRED_CAPABILITIES"}

    authority_epoch = v8._authority_epoch(public)
    if authority_epoch is None:
        return {"action": "ESCALATE", "reason": "AUTHORITY_EPOCH_INVALID"}

    sources, source_set_digest, err = v8._active_sources(
        public, authority_epoch=authority_epoch
    )
    if err:
        return {"action": "ESCALATE", "reason": err}

    receipts, err = v8._valid_receipts(
        public,
        sources,
        authority_epoch=authority_epoch,
        source_set_digest=source_set_digest,
    )
    if err:
        return {"action": "ESCALATE", "reason": err}

    for source in sources:
        sid = str(source.get("source_id"))
        if sid not in receipts:
            return {
                "action": "DISCOVER",
                "source_id": sid,
                "query": str(source.get("catalog_query")),
                "authority_epoch": authority_epoch,
            }

    tools, err = v8._catalog_v8(public, receipts)
    if err:
        return {"action": "ESCALATE", "reason": err}

    evidence, err = v8._evidence_v8(
        public, tools, authority_epoch=authority_epoch
    )
    if err:
        return {"action": "ESCALATE", "reason": err}

    constraint = public.get("constraint")
    rows: list[dict[str, Any]] = []
    for tool in tools:
        if not (
            tool.get("available") is True
            and tool.get("authorized") is True
            and v5._pred(constraint, tool)
        ):
            continue
        tid = str(tool.get("tool_id") or "")
        unknown: list[str] = []
        falsified = False
        for cap in required:
            value = evidence.get((tid, cap))
            if value is False:
                falsified = True
                break
            if value is None:
                unknown.append(cap)
        if falsified:
            continue
        rows.append({
            "tool": tool,
            "tool_id": tid,
            "cost": float(tool["cost"]),
            "unknown": unknown,
        })

    if not rows:
        return {
            "action": "ESCALATE",
            "reason": "NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY",
        }

    frontier_cost = min(row["cost"] for row in rows)
    frontier = sorted(
        (row for row in rows if row["cost"] == frontier_cost),
        key=lambda row: row["tool_id"],
    )

    verified = [row for row in frontier if not row["unknown"]]
    if verified:
        return {"action": "SELECT", "tool_id": verified[0]["tool_id"]}

    probes: list[tuple[str, str]] = []
    for row in frontier:
        for cap in row["unknown"]:
            if v5._probe_allowed(row["tool"], cap):
                probes.append((row["tool_id"], cap))
    if probes:
        tid, cap = min(probes)
        return {"action": "PROBE", "tool_id": tid, "capability": cap}

    return {
        "action": "ESCALATE",
        "reason": "LEAST_COST_FRONTIER_UNRESOLVED_NO_SAFE_PROBE",
        "frontier_cost": frontier_cost,
        "tool_ids": [row["tool_id"] for row in frontier],
    }


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    guarded = v8.next_action(public)

    # Preserve every V8 structural/restart/discovery failure exactly. Recompute
    # only terminal route choice/probe/escalation under a complete valid catalog.
    if guarded.get("action") == "DISCOVER":
        return guarded
    if (
        guarded.get("action") == "ESCALATE"
        and guarded.get("reason") not in _DECISION_REASONS
    ):
        return guarded

    return _frontier_action(public)
