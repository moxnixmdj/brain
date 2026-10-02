"""Brain candidate for bounded information-safe evidence synthesis."""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.bounded_claim_support import build_support_graph


def solve(public_case:Mapping[str,Any])->dict[str,Any]:
    task=public_case.get("task")
    if not isinstance(task,Mapping):
        return {"status":"FAIL_CLOSED","reason":"TASK_INVALID","selected_evidence_ids":[]}
    claims=task.get("claims")
    evidence=task.get("evidence")
    required=task.get("required_claim_ids")
    budget=task.get("max_evidence_units")
    if not isinstance(claims,list) or not isinstance(evidence,list) or not isinstance(required,list):
        return {"status":"FAIL_CLOSED","reason":"ROWS_INVALID","selected_evidence_ids":[]}
    if not isinstance(budget,int) or isinstance(budget,bool) or budget<0:
        return {"status":"FAIL_CLOSED","reason":"BUDGET_INVALID","selected_evidence_ids":[]}

    graph=build_support_graph(claims,evidence)
    if graph.get("status") not in {"COMPILED","COMPILED_WITH_UNKNOWNS"}:
        return {"status":"FAIL_CLOSED","reason":"SUPPORT_GRAPH_INVALID","selected_evidence_ids":[]}
    if graph.get("unresolved"):
        return {"status":"ESCALATE","reason":"UNRESOLVED_EVIDENCE_RELATIONS","selected_evidence_ids":[]}

    by_claim={cid:{"SUPPORTS":[],"CONFLICTS":[]} for cid in required}
    for edge in graph.get("edges",[]):
        cid=edge.get("claim_id")
        if cid not in by_claim:
            continue
        relation=edge.get("relation")
        if relation in by_claim[cid]:
            by_claim[cid][relation].append(str(edge.get("evidence_id")))

    essential=[]
    unsupported=[]
    for cid in required:
        supports=sorted(set(by_claim[cid]["SUPPORTS"]))
        conflicts=sorted(set(by_claim[cid]["CONFLICTS"]))
        if not supports:
            unsupported.append(cid)
        else:
            essential.append(supports[0])
        essential.extend(conflicts)

    selected=[]
    seen=set()
    for eid in essential:
        if eid not in seen:
            seen.add(eid)
            selected.append(eid)

    if len(selected)>budget:
        return {
            "status":"BUDGET_INSUFFICIENT",
            "reason":"ESSENTIAL_EVIDENCE_EXCEEDS_BUDGET",
            "selected_evidence_ids":selected[:budget],
            "unsupported_claim_ids":unsupported,
        }

    return {
        "status":"INSUFFICIENT" if unsupported else "SYNTHESIZED",
        "selected_evidence_ids":selected,
        "unsupported_claim_ids":unsupported,
        "claim_states":{
            cid:(
                "UNSUPPORTED" if not by_claim[cid]["SUPPORTS"]
                else "CONFLICTED" if by_claim[cid]["CONFLICTS"]
                else "SUPPORTED"
            )
            for cid in required
        },
        "reason":"MINIMAL_REQUIRED_SUPPORT_PLUS_MATERIAL_CONFLICT",
    }
