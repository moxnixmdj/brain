"""P1 typed trajectory causal localizer V7.

V7 removes a load-bearing V6 assumption: a failed ancestor is not automatically a
uniquely identified cause merely because another failed check is downstream.

Failed checks may declare visible failure_semantics:
  DIRECT_CONTRACT   - locally violated contract, potentially causal.
  DERIVED_UPSTREAM  - visible symptom derived from an upstream failure.
  UNKNOWN           - directness is not established.

Only DERIVED_UPSTREAM failures are deleted as symptoms. Multiple remaining
direct/unknown failures are treated as non-identifiable unless a visible
conjunctive dependency establishes a joint interaction. Hidden cause labels and
intervention outcomes remain unavailable to the candidate.
"""
from __future__ import annotations
from typing import Any, Mapping

ALLOWED_KINDS={
    "AUTHORITY","SCHEMA","PROVENANCE","INVARIANT","STATE_TRANSITION",
    "TOOL_CONTRACT","DEPENDENCY","SCOPE",
}
ALLOWED_FAILURE_SEMANTICS={"DIRECT_CONTRACT","DERIVED_UPSTREAM","UNKNOWN"}

def _list_str(value:Any)->list[str]|None:
    if not isinstance(value,list) or any(not isinstance(x,str) or not x for x in value):
        return None
    return list(value)

def _failed_checks(row:Mapping[str,Any])->list[dict[str,Any]]|None:
    checks=row.get("checks")
    if not isinstance(checks,list):
        return None
    out=[]
    for item in checks:
        if not isinstance(item,Mapping):
            return None
        kind=item.get("kind"); cid=item.get("id"); passed=item.get("pass")
        evidence=_list_str(item.get("evidence"))
        semantics=item.get("failure_semantics","UNKNOWN")
        if kind not in ALLOWED_KINDS or not isinstance(cid,str) or not cid:
            return None
        if type(passed) is not bool or evidence is None:
            return None
        if semantics not in ALLOWED_FAILURE_SEMANTICS:
            return None
        if not passed and not evidence:
            return None
        if not passed:
            out.append({"kind":kind,"id":cid,"evidence":evidence,"failure_semantics":semantics})
    return out

def solve(public_case:Mapping[str,Any])->dict[str,Any]:
    task=public_case.get("task")
    if not isinstance(task,Mapping):
        return {"status":"FAIL_CLOSED","reason":"TASK_INVALID"}
    rows=task.get("trajectory")
    terminal_failed=_list_str(task.get("terminal_failed_resources"))
    if not isinstance(rows,list) or not rows or terminal_failed is None or not terminal_failed:
        return {"status":"FAIL_CLOSED","reason":"TRAJECTORY_OR_TERMINAL_FAILURE_INVALID"}

    by_id={}; order={}; failed={}; reads={}; writes={}; explicit_deps={}; composition={}
    for idx,row in enumerate(rows):
        if not isinstance(row,Mapping):
            return {"status":"FAIL_CLOSED","reason":"TRAJECTORY_ROW_INVALID"}
        aid=row.get("action_id"); rds=_list_str(row.get("reads")); wrs=_list_str(row.get("writes"))
        deps=_list_str(row.get("depends_on")); comp=row.get("dependency_composition","SEQUENTIAL")
        fc=_failed_checks(row)
        if (not isinstance(aid,str) or not aid or aid in by_id or rds is None or wrs is None
            or deps is None or fc is None or comp not in {"SEQUENTIAL","CONJUNCTIVE","ALTERNATIVE"}):
            return {"status":"FAIL_CLOSED","reason":"STEP_SCHEMA_INVALID"}
        if any(d not in by_id for d in deps):
            return {"status":"FAIL_CLOSED","reason":"NON_TOPOLOGICAL_DEPENDENCY"}
        by_id[aid]=row; order[aid]=idx; failed[aid]=fc; reads[aid]=set(rds); writes[aid]=set(wrs)
        explicit_deps[aid]=set(deps); composition[aid]=comp

    deps={k:set(v) for k,v in explicit_deps.items()}
    last_writer={}
    for row in rows:
        aid=row["action_id"]
        for resource in reads[aid]:
            p=last_writer.get(resource)
            if p is not None:
                deps[aid].add(p)
        for resource in writes[aid]:
            last_writer[resource]=aid

    terminal_actions={last_writer[r] for r in terminal_failed if r in last_writer}
    if not terminal_actions:
        return {"status":"ESCALATE","reason":"NO_PRODUCER_FOR_TERMINAL_FAILED_RESOURCE"}

    relevant=set(); stack=list(terminal_actions)
    while stack:
        aid=stack.pop()
        if aid in relevant:
            continue
        relevant.add(aid); stack.extend(deps[aid])

    relevant_failed={aid for aid in relevant if failed[aid]}
    if not relevant_failed:
        return {"status":"ESCALATE","reason":"NO_CONTRACT_VIOLATION_ON_TERMINAL_CAUSAL_SLICE"}

    ancestor_cache={}
    def ancestors(aid:str)->set[str]:
        if aid in ancestor_cache:
            return ancestor_cache[aid]
        out=set(); todo=list(deps[aid])
        while todo:
            x=todo.pop()
            if x in out:
                continue
            out.add(x); todo.extend(deps[x])
        ancestor_cache[aid]=out
        return out

    # This is the V7 epistemic boundary. A derived symptom is not a candidate
    # cause. A direct or unknown failure remains causally live until evidence
    # distinguishes it.
    live=[]
    for aid in relevant_failed:
        if any(x["failure_semantics"]!="DERIVED_UPSTREAM" for x in failed[aid]):
            live.append(aid)
    live=sorted(live,key=lambda x:order[x])
    if not live:
        return {"status":"ESCALATE","reason":"ONLY_DERIVED_FAILURES_ON_TERMINAL_CAUSAL_SLICE"}

    def detail(aid:str)->dict[str,Any]:
        checks=[x for x in failed[aid] if x["failure_semantics"]!="DERIVED_UPSTREAM"]
        checks=sorted(checks,key=lambda x:(x["kind"],x["id"]))
        kinds=sorted({x["kind"] for x in checks})
        evidence=sorted({e for x in checks for e in x["evidence"]})
        repairs=sorted({f"restore:{aid}:{x['kind']}" for x in checks})
        return {
            "action_id":aid,
            "mechanism_classes":kinds,
            "supporting_receipts":evidence,
            "repair_targets":repairs,
        }

    if len(live)==1:
        aid=live[0]; d=detail(aid)
        return {
            "status":"IDENTIFIED","cause_action_id":aid,"cause_action_ids":[aid],
            "critical_action_id":aid,"mechanism_classes":d["mechanism_classes"],
            "supporting_receipts":d["supporting_receipts"],"repair_targets":d["repair_targets"],
            "reason":"UNIQUE_NONDERIVED_FAILURE_ON_TERMINAL_CAUSAL_SLICE",
        }

    live_set=set(live)
    pairwise_independent=all(
        a==b or (a not in ancestors(b) and b not in ancestors(a))
        for a in live for b in live
    )
    conjunctive=[]
    if pairwise_independent:
        for aid in relevant:
            if composition[aid]!="CONJUNCTIVE":
                continue
            if live_set.issubset(ancestors(aid)|({aid} if aid in live_set else set())):
                conjunctive.append(aid)

    if conjunctive:
        details=[detail(x) for x in live]
        return {
            "status":"INTERACTION","cause_action_id":live[0],"cause_action_ids":live,
            "critical_action_id":live[0],
            "interaction_witness_action_ids":sorted(conjunctive,key=lambda x:order[x]),
            "mechanism_by_action":{d["action_id"]:d["mechanism_classes"] for d in details},
            "supporting_receipts":sorted({e for d in details for e in d["supporting_receipts"]}),
            "repair_targets":sorted({r for d in details for r in d["repair_targets"]}),
            "reason":"MULTIPLE_INDEPENDENT_NONDERIVED_FAILURES_JOIN_UNDER_VISIBLE_CONJUNCTIVE_DEPENDENCY",
        }

    return {
        "status":"AMBIGUOUS","cause_action_id":None,"cause_action_ids":live,
        "critical_action_id":None,"candidates":[detail(x) for x in live],
        "reason":"MULTIPLE_CAUSALLY_COMPATIBLE_NONDERIVED_FAILURES_WITHOUT_VISIBLE_DISCRIMINATOR",
        "information_request":"ACQUIRE_INTERVENTION_OR_ADDITIONAL_CAUSAL_DISCRIMINATOR",
    }
