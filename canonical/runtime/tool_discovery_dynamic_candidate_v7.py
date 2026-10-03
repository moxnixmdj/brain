"""Tool Discovery policy V7: V6 plus cost-frontier decision semantics.

V6 preserves V5's discovery, evidence, safe-probe, and version-restart repairs.
V5/V6 still decide one tool at a time in (cost, tool_id) order. That creates a
real counterexample: an unresolved unprobeable route can block a verified
sufficient peer at the same minimum cost, even though selecting the verified
peer is still globally least-cost.

V7 decides by *cost frontier*:
1. all strictly cheaper non-falsified routes remain load-bearing;
2. within the current minimum cost frontier, any verified sufficient route may
   be selected immediately;
3. otherwise consume a safe unresolved fact anywhere on that frontier;
4. only if the whole frontier remains unresolved and has no safe observation
   may the policy escalate for matched evidence.

This matches the least-cost objective without inventing a canonical tie identity.
Zero acceptance/family/execution/promotion credit is granted here.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5
from canonical.runtime import tool_discovery_dynamic_candidate_v6 as v6

_DECISION_REASONS={
    "CHEAPER_ADMISSIBLE_ROUTE_UNRESOLVED_NO_SAFE_PROBE",
    "NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY",
}


def _frontier_action(public: Mapping[str, Any]) -> dict[str, Any]:
    required,query=v5._requirements(public)
    if query is None or not required:
        return {"action":"ESCALATE","reason":query or "INVALID_REQUIREMENTS"}
    decision_epoch=v5._decision_epoch(public)
    if decision_epoch is None:
        return {"action":"ESCALATE","reason":"DECISION_EPOCH_INVALID"}

    sources,source_set_digest,err=v5._active_sources(public)
    if err:
        return {"action":"ESCALATE","reason":err}
    receipts,err=v5._valid_receipts(
        public,sources,
        decision_epoch=decision_epoch,
        source_set_digest=source_set_digest,
        query=query,
    )
    if err:
        return {"action":"ESCALATE","reason":err}
    for source in sources:
        sid=str(source.get("source_id"))
        if sid not in receipts:
            return {"action":"DISCOVER","source_id":sid,"query":query}

    tools,err=v5._catalog(public,receipts)
    if err:
        return {"action":"ESCALATE","reason":err}
    evidence,err=v5._evidence(public,tools)
    if err:
        return {"action":"ESCALATE","reason":err}

    constraint=public.get("constraint")
    admissible=[]
    for tool in tools:
        cost=tool.get("cost")
        if (
            isinstance(cost,bool)
            or not isinstance(cost,(int,float))
            or not math.isfinite(float(cost))
            or float(cost)<0
        ):
            return {"action":"ESCALATE","reason":"TOOL_COST_INVALID"}
        if (
            tool.get("available") is True
            and tool.get("authorized") is True
            and v5._pred(constraint,tool)
        ):
            admissible.append(tool)

    rows=[]
    for tool in admissible:
        tid=str(tool.get("tool_id") or "")
        unknown=[]
        falsified=False
        for cap in required:
            value=evidence.get((tid,cap))
            if value is False:
                falsified=True
                break
            if value is None:
                unknown.append(cap)
        if falsified:
            continue
        rows.append({
            "tool":tool,
            "tool_id":tid,
            "cost":float(tool["cost"]),
            "unknown":unknown,
        })

    if not rows:
        return {
            "action":"ESCALATE",
            "reason":"NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY",
        }

    frontier_cost=min(row["cost"] for row in rows)
    frontier=sorted(
        (row for row in rows if row["cost"]==frontier_cost),
        key=lambda row:row["tool_id"],
    )

    verified=[row for row in frontier if not row["unknown"]]
    if verified:
        return {"action":"SELECT","tool_id":verified[0]["tool_id"]}

    probe_candidates=[]
    for row in frontier:
        for cap in row["unknown"]:
            if v5._probe_allowed(row["tool"],cap):
                probe_candidates.append((row["tool_id"],cap))
    if probe_candidates:
        tid,cap=min(probe_candidates)
        return {"action":"PROBE","tool_id":tid,"capability":cap}

    return {
        "action":"ESCALATE",
        "reason":"LEAST_COST_FRONTIER_UNRESOLVED_NO_SAFE_PROBE",
        "frontier_cost":frontier_cost,
        "tool_ids":[row["tool_id"] for row in frontier],
    }


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    guarded=v6.next_action(public)

    # Preserve V6's restart boundary and all V5 structural fail-closed checks.
    if guarded.get("action")=="DISCOVER":
        return guarded
    if guarded.get("action")=="ESCALATE" and guarded.get("reason") not in _DECISION_REASONS:
        return guarded

    # SELECT/PROBE and the two terminal decision reasons are all recomputed as
    # one cost-frontier decision. This removes only the invalid per-ID tie
    # ordering; strictly cheaper unresolved routes remain blockers.
    return _frontier_action(public)
