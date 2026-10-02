"""Brain-owned M4 research-control compiler.

This module does not invent task semantics. It consumes an already-normalized
material requirement graph, exactly matching the ITERATIVE_RESEARCH_EVIDENCE_CONTROL
contract's declared input boundary.

It composes:
- deterministic query focus from one unresolved requirement,
- verified research-action selection from explicit coverage/cost/reliability,
- exact stop when every material requirement is resolved,
- fail-closed escalation when requirement semantics or source/action coverage are unknown.

Unknown-domain semantic interpretation remains upstream in M0/JIT knowledge. This
module owns research-loop control, not arbitrary natural-language understanding.
"""
from __future__ import annotations
from dataclasses import asdict
from typing import Any, Mapping, Sequence

from canonical.runtime.bound_capabilities import research_query_focus
from canonical.runtime.shared_decision_primitives import ResearchAction, next_research_action

SCHEMA="BRAIN_M4_RESEARCH_CONTROL_V1"

def _requirements(rows:Any)->tuple[list[dict[str,Any]],list[str]]:
    errors=[]
    if not isinstance(rows,list) or not rows:
        return [],["MATERIAL_REQUIREMENT_GRAPH_MISSING"]
    out=[]
    seen=set()
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            errors.append(f"REQUIREMENT_INVALID:{i}"); continue
        rid=row.get("id")
        text=row.get("text")
        if not isinstance(rid,str) or not rid.strip():
            errors.append(f"REQUIREMENT_ID_INVALID:{i}"); continue
        if rid in seen:
            errors.append(f"REQUIREMENT_ID_DUPLICATE:{rid}"); continue
        seen.add(rid)
        if not isinstance(text,str) or not text.strip():
            errors.append(f"REQUIREMENT_TEXT_MISSING:{rid}"); continue
        if row.get("material") is not True:
            errors.append(f"REQUIREMENT_MATERIALITY_NOT_EXPLICIT:{rid}")
        out.append({"id":rid,"text":text.strip(),"material":True})
    return out,errors

def _actions(rows:Any,known:set[str])->tuple[list[ResearchAction],list[str]]:
    errors=[]
    if not isinstance(rows,list):
        return [],["RESEARCH_ACTIONS_NOT_LIST"]
    out=[]
    seen=set()
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            errors.append(f"ACTION_INVALID:{i}"); continue
        aid=row.get("id")
        covers=row.get("covers")
        if not isinstance(aid,str) or not aid.strip():
            errors.append(f"ACTION_ID_INVALID:{i}"); continue
        if aid in seen:
            errors.append(f"ACTION_ID_DUPLICATE:{aid}"); continue
        seen.add(aid)
        if not isinstance(covers,list) or not covers or any(not isinstance(x,str) or not x for x in covers):
            errors.append(f"ACTION_COVERAGE_INVALID:{aid}"); continue
        if not set(covers)<=known:
            errors.append(f"ACTION_COVERS_UNKNOWN_REQUIREMENT:{aid}")
        try:
            cost=float(row.get("cost"))
            reliability=float(row.get("reliability",1.0))
        except Exception:
            errors.append(f"ACTION_NUMERIC_INVALID:{aid}"); continue
        verified=row.get("verified") is True
        out.append(ResearchAction(
            aid,frozenset(covers),cost,reliability,verified
        ))
    return out,errors

def control(
    *,
    objective:str,
    material_requirements:Any,
    resolved_requirement_ids:Any,
    candidate_actions:Any,
)->dict[str,Any]:
    if not isinstance(objective,str) or not objective.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":["OBJECTIVE_REQUIRED"],"terminal_authority":False}

    reqs,errors=_requirements(material_requirements)
    known={r["id"] for r in reqs}
    if not isinstance(resolved_requirement_ids,(list,set,tuple,frozenset)) or any(
        not isinstance(x,str) for x in resolved_requirement_ids
    ):
        errors.append("RESOLVED_REQUIREMENTS_INVALID")
        resolved=set()
    else:
        resolved=set(resolved_requirement_ids)
    unknown_resolved=resolved-known
    if unknown_resolved:
        errors.append("RESOLVED_UNKNOWN_REQUIREMENTS:"+",".join(sorted(unknown_resolved)))

    actions,action_errors=_actions(candidate_actions,known)
    errors.extend(action_errors)
    if errors:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors)),
            "terminal_authority":False,
        }

    material={r["id"] for r in reqs}
    decision=next_research_action(material,resolved,actions)
    if decision.status=="STOP":
        return {
            "schema":SCHEMA,
            "status":"STOP",
            "reason":decision.reason,
            "unresolved_requirement_ids":[],
            "terminal_authority":False,
            "semantic_authority":False,
            "rule":"STOP_IFF_ALL_EXPLICIT_MATERIAL_REQUIREMENTS_RESOLVED",
        }
    if decision.status!="ACT" or decision.action_id is None:
        return {
            "schema":SCHEMA,
            "status":"ESCALATE",
            "reason":decision.reason,
            "unresolved_requirement_ids":sorted(decision.unresolved),
            "terminal_authority":False,
            "semantic_authority":False,
        }

    chosen=next(a for a in actions if a.action_id==decision.action_id)
    target_ids=sorted(chosen.covers & decision.unresolved)
    if not target_ids:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":["SELECTED_ACTION_ADDS_NO_UNRESOLVED_COVERAGE"],
            "terminal_authority":False,
        }
    # Deterministically focus the first still-unresolved requirement that the
    # chosen verified action claims to cover. No query semantics are invented.
    target_id=target_ids[0]
    target=next(r for r in reqs if r["id"]==target_id)
    focused=research_query_focus.focus(target["text"])
    if focused.get("status")!="FOCUSED":
        return {
            "schema":SCHEMA,
            "status":"ESCALATE",
            "reason":"REQUIREMENT_QUERY_FOCUS_UNRESOLVED",
            "target_requirement_id":target_id,
            "query_focus":focused,
            "terminal_authority":False,
            "semantic_authority":False,
        }

    return {
        "schema":SCHEMA,
        "status":"ACT",
        "selected_action_id":decision.action_id,
        "target_requirement_id":target_id,
        "query":focused["query"],
        "query_focus":focused,
        "unresolved_requirement_ids":sorted(decision.unresolved),
        "selected_action":asdict(chosen),
        "terminal_authority":False,
        "semantic_authority":False,
        "dependency_boundary":{
            "requirement_semantics":"UPSTREAM_M0_OR_EXPLICIT_CONTRACT",
            "source_action_coverage":"MUST_BE_PREVERIFIED_OR_ACTION_IS_INELIGIBLE",
            "research_control":"OWNED_HERE",
        },
    }
