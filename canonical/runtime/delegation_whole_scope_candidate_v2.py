"""Whole-dimension information-safe delegation candidate V2.

Consumes only explicit task contracts, worker/tool capabilities, resource constraints,
evidence ownership rules, and live receipts. It does not import the proof evaluator
or hidden optimum. Planning is exact over monotonic explicit fact contracts and has
no static task-count semantic cutoff; runtime cost is allowed to scale with the
declared finite graph.
"""
from __future__ import annotations

from collections import defaultdict, deque
from heapq import heappop, heappush
from itertools import combinations, permutations
import math
from typing import Any, Mapping, Sequence


class DelegationV2Error(ValueError):
    pass


def _ids(values, name):
    vals=list(values or [])
    if any(not isinstance(x,str) or not x.strip() for x in vals):
        raise DelegationV2Error(name+"_INVALID")
    return vals


def _effective(task:Mapping[str,Any], receipt:Mapping[str,Any]|None, completed:set[str]):
    disabled_steps=set()
    unavailable_workers=set()
    removed=defaultdict(set)
    resource_caps={str(k):int(v) for k,v in dict(task.get("resource_capacities") or {}).items()}
    if any(v<1 for v in resource_caps.values()):
        raise DelegationV2Error("RESOURCE_CAPACITY_INVALID")
    if receipt:
        kind=receipt.get("kind")
        entity=str(receipt.get("entity_id") or "")
        if kind=="STEP_UNAVAILABLE":
            disabled_steps.add(entity)
        elif kind=="WORKER_UNAVAILABLE":
            unavailable_workers.add(entity)
        elif kind=="WORKER_CAPABILITY_REMOVED":
            removed[entity].add(str(receipt.get("capability") or ""))
        elif kind=="RESOURCE_CAPACITY_CHANGED":
            cap=receipt.get("capacity")
            if not isinstance(cap,int) or isinstance(cap,bool) or cap<1:
                raise DelegationV2Error("RECEIPT_RESOURCE_CAPACITY_INVALID")
            resource_caps[entity]=cap

    steps={}
    for row in task.get("steps",[]):
        if not isinstance(row,Mapping):
            raise DelegationV2Error("STEP_NOT_OBJECT")
        sid=row.get("id")
        if not isinstance(sid,str) or not sid or sid in steps:
            raise DelegationV2Error("STEP_ID_INVALID_OR_DUPLICATE")
        req=frozenset(_ids(row.get("requires",[]),"STEP_REQUIRES"))
        prod=frozenset(_ids(row.get("produces",[]),"STEP_PRODUCES"))
        cap=row.get("capability")
        cost=row.get("cost")
        if not prod or not isinstance(cap,str) or not cap:
            raise DelegationV2Error("STEP_CONTRACT_INVALID:"+sid)
        if not isinstance(cost,(int,float)) or isinstance(cost,bool) or not math.isfinite(float(cost)) or float(cost)<0:
            raise DelegationV2Error("STEP_COST_INVALID:"+sid)
        writes=frozenset(_ids(row.get("writes",[]),"STEP_WRITES"))
        evidence=frozenset(_ids(row.get("evidence_outputs",[]),"STEP_EVIDENCE"))
        if not evidence:
            raise DelegationV2Error("STEP_EVIDENCE_EMPTY:"+sid)
        steps[sid]={
            "requires":req,"produces":prod,"capability":cap,"cost":float(cost),
            "writes":writes,"evidence":evidence,
            "available":row.get("available",True) is True and sid not in disabled_steps and sid not in completed,
        }

    workers={}
    for row in task.get("workers",[]):
        if not isinstance(row,Mapping):
            raise DelegationV2Error("WORKER_NOT_OBJECT")
        wid=row.get("id")
        if not isinstance(wid,str) or not wid or wid in workers:
            raise DelegationV2Error("WORKER_ID_INVALID_OR_DUPLICATE")
        if wid in unavailable_workers:
            continue
        caps=set(_ids(row.get("capabilities",[]),"WORKER_CAPABILITIES"))
        caps-=removed.get(wid,set())
        if caps:
            workers[wid]=frozenset(caps)
    if not workers:
        raise DelegationV2Error("NO_EFFECTIVE_WORKERS")
    return steps,workers,resource_caps


def _completed_state(task:Mapping[str,Any], completed:Sequence[str]):
    raw={}
    for row in task.get("steps",[]):
        raw[str(row.get("id"))]=row
    facts=set(_ids(task.get("initial_facts",[]),"INITIAL_FACTS"))
    evidence_owners={}
    completed_set=set()
    for sid in completed:
        if sid in completed_set or sid not in raw:
            raise DelegationV2Error("COMPLETED_TASK_INVALID:"+str(sid))
        row=raw[sid]
        req=set(_ids(row.get("requires",[]),"COMPLETED_REQUIRES"))
        if not req.issubset(facts):
            raise DelegationV2Error("COMPLETED_PRECONDITION_INVALID:"+sid)
        facts.update(_ids(row.get("produces",[]),"COMPLETED_PRODUCES"))
        for ev in _ids(row.get("evidence_outputs",[]),"COMPLETED_EVIDENCE"):
            prior=evidence_owners.get(ev)
            if prior is not None and prior!=sid:
                raise DelegationV2Error("EVIDENCE_OWNER_CONFLICT:"+ev)
            evidence_owners[ev]=sid
        completed_set.add(sid)
    return frozenset(facts),evidence_owners


def _derive_dependencies(task:Mapping[str,Any], steps:Mapping[str,Mapping[str,Any]], completed:Sequence[str], seq:Sequence[str]):
    initial,_=_completed_state(task,completed)
    facts=set(initial)
    producer={}
    deps={}
    for sid in seq:
        row=steps[sid]
        if not row["requires"].issubset(facts):
            raise DelegationV2Error("SEQUENCE_PRECONDITION_INVALID:"+sid)
        direct=set()
        for fact in sorted(row["requires"]):
            if fact in initial:
                continue
            if fact not in producer:
                raise DelegationV2Error("DEPENDENCY_DERIVATION_GAP:"+sid+":"+fact)
            direct.add(producer[fact])
        deps[sid]=sorted(direct)
        for fact in sorted(row["produces"]):
            if fact not in facts:
                producer[fact]=sid
        facts.update(row["produces"])
    return deps


def _plan(task:Mapping[str,Any], steps:Mapping[str,Mapping[str,Any]], workers:Mapping[str,frozenset[str]], caps:Mapping[str,int], completed:Sequence[str]):
    """Exact minimum feasible plan under the declared finite task model.

    Search order is (total_cost, task_count, lexical_sequence).  Unlike the prior
    fact-state Dijkstra, feasibility is part of the goal predicate: a cheaper
    fact-producing sequence that cannot be assigned/scheduled is skipped rather
    than incorrectly terminating the search.
    """
    initial,_=_completed_state(task,completed)
    required=frozenset(_ids(task.get("required_outputs",[]),"REQUIRED_OUTPUTS"))
    if not required:
        raise DelegationV2Error("REQUIRED_OUTPUTS_EMPTY")
    eligible=sorted(s for s,x in steps.items() if x["available"])
    heap=[(0.0,0,(),frozenset(initial))]
    seen_sequences={()}

    while heap:
        cost,count,seq,facts=heappop(heap)
        if required.issubset(facts):
            deps=_derive_dependencies(task,steps,completed,seq)
            try:
                _schedule(list(seq),deps,steps,workers,caps)
            except DelegationV2Error as exc:
                if str(exc)!="NO_RESOURCE_AND_CAPABILITY_FEASIBLE_SCHEDULE":
                    raise
            else:
                return list(seq),deps,float(cost)

        used=set(seq)
        for sid in eligible:
            if sid in used:
                continue
            row=steps[sid]
            if not row["requires"].issubset(facts):
                continue
            nf=facts|row["produces"]
            if nf==facts:
                continue
            ns=seq+(sid,)
            if ns in seen_sequences:
                continue
            seen_sequences.add(ns)
            heappush(heap,(cost+row["cost"],count+1,ns,nf))
    raise DelegationV2Error("NO_EXECUTABLE_FEASIBLE_PLAN")

def _resource_ok(subset,steps,caps):
    use=defaultdict(int)
    for sid in subset:
        for res in steps[sid]["writes"]:
            use[res]+=1
    return all(use[r] <= caps.get(r,1) for r in use)


def _matchings(ready,steps,workers,caps):
    wids=sorted(workers)
    rows=[]
    for k in range(1,min(len(ready),len(wids))+1):
        for tasks in combinations(sorted(ready),k):
            if not _resource_ok(tasks,steps,caps):
                continue
            for ws in permutations(wids,k):
                m=dict(zip(tasks,ws))
                if all(steps[s]["capability"] in workers[w] for s,w in m.items()):
                    rows.append(m)
    rows.sort(key=lambda m:(-len(m),tuple(sorted(m.items()))))
    return rows


def _schedule(task_ids,deps,steps,workers,caps):
    target=frozenset(task_ids)
    q=deque([(frozenset(),[],{})])
    seen={frozenset()}
    while q:
        done,waves,assign=q.popleft()
        if done==target:
            return waves,assign
        ready=[s for s in task_ids if s not in done and set(deps[s]).issubset(done)]
        for matching in _matchings(ready,steps,workers,caps):
            nd=frozenset(set(done)|set(matching))
            if nd in seen:
                continue
            seen.add(nd)
            na=dict(assign);na.update(matching)
            q.append((nd,waves+[sorted(matching)],na))
    raise DelegationV2Error("NO_RESOURCE_AND_CAPABILITY_FEASIBLE_SCHEDULE")


def _evidence(task:Mapping[str,Any], task_ids, deps, steps, completed):
    _,owners=_completed_state(task,completed)
    for sid in task_ids:
        for ev in sorted(steps[sid]["evidence"]):
            prior=owners.get(ev)
            if prior is not None and prior!=sid:
                raise DelegationV2Error("EVIDENCE_OWNER_CONFLICT:"+ev)
            owners[ev]=sid

    completed_evidence={}
    raw={str(x.get("id")):x for x in task.get("steps",[]) if isinstance(x,Mapping)}
    for sid in completed:
        completed_evidence[sid]=set(_ids(raw[sid].get("evidence_outputs",[]),"COMPLETED_EVIDENCE"))

    lineage={}
    selected=set(task_ids)
    for sid in task_ids:
        seen=set()
        stack=list(deps[sid])
        while stack:
            d=stack.pop()
            if d in seen:
                continue
            seen.add(d)
            stack.extend(deps.get(d,[]))
        ev=set()
        for d in seen:
            ev.update(steps[d]["evidence"])
        # Facts produced by completed work are initial for replanning, but their evidence
        # must still be carried into every downstream terminal fan-in.
        for d in completed:
            ev.update(completed_evidence.get(d,set()))
        lineage[sid]=sorted(ev)

    sinks=[s for s in task_ids if not any(s in deps[t] for t in task_ids)]
    terminal_evidence=set()
    for s in sinks:
        terminal_evidence.update(lineage[s])
        terminal_evidence.update(steps[s]["evidence"])
    for d in completed:
        terminal_evidence.update(completed_evidence.get(d,set()))
    return dict(sorted(owners.items())),lineage,sorted(terminal_evidence)


def _solve(task:Mapping[str,Any], receipt:Mapping[str,Any]|None=None):
    completed=[str(x) for x in ((receipt or {}).get("completed_task_ids") or [])]
    steps,workers,caps=_effective(task,receipt,set(completed))
    ids,deps,cost=_plan(task,steps,workers,caps,completed)
    waves,assignment=_schedule(ids,deps,steps,workers,caps)
    owners,fanin,terminal_evidence=_evidence(task,ids,deps,steps,completed)
    return {
        "status":"PASS",
        "task_ids":ids,
        "dependencies":deps,
        "assignment":assignment,
        "waves":waves,
        "wave_count":len(waves),
        "total_cost":cost,
        "evidence_owners":owners,
        "fanin_evidence":fanin,
        "terminal_evidence":terminal_evidence,
        "resource_capacities":dict(sorted(caps.items())),
        "terminal_authority":False,
    }


def solve_initial(public:Mapping[str,Any])->dict[str,Any]:
    task=public.get("task")
    if not isinstance(task,Mapping):
        raise DelegationV2Error("TASK_MISSING")
    return _solve(task)


def solve_after_receipt(public:Mapping[str,Any], previous:Mapping[str,Any])->dict[str,Any]:
    task=public.get("task");receipt=public.get("receipt")
    if not isinstance(task,Mapping) or not isinstance(receipt,Mapping):
        raise DelegationV2Error("TASK_OR_RECEIPT_MISSING")
    if previous.get("status")!="PASS":
        raise DelegationV2Error("PRIOR_PLAN_NOT_PASS")
    out=_solve(task,receipt)
    out["receipt_id"]=str(receipt.get("receipt_id") or "")
    prov={
        "kind":str(receipt.get("kind") or ""),
        "entity_id":str(receipt.get("entity_id") or ""),
        "completed_task_ids":[str(x) for x in receipt.get("completed_task_ids",[])],
    }
    if receipt.get("capability") is not None:
        prov["capability"]=str(receipt.get("capability"))
    if receipt.get("capacity") is not None:
        prov["capacity"]=receipt.get("capacity")
    out["revision_provenance"]=prov
    return out
