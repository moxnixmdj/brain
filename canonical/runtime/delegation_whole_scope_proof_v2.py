"""Whole-dimension information-safe proof for TASK_TO_DELEGATION_GRAPH_001.

The candidate sees only declared task contracts, worker capabilities, resource
capacities, evidence ownership rules and live receipts. Hidden acceptance computes
an independent minimum-cost task set, minimum-wave capability/resource schedule,
ownership/fan-in completeness, and serial/naive-fanout ablations.

No ideal plan, assignment, hidden baseline score or reference action is candidate-visible.
"""
from __future__ import annotations

from collections import defaultdict, deque
from itertools import combinations, permutations
import math
import random
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_DELEGATION_WHOLE_DIMENSION_INFORMATION_SAFE_PROOF_V2"
CLASSES=(
    "BASE_PARALLEL",
    "RESOURCE_CONFLICT",
    "WORKER_UNAVAILABLE",
    "STEP_UNAVAILABLE",
    "WORKER_CAPABILITY_REMOVED",
    "RESOURCE_CAPACITY_CHANGED",
)


def generate_case(seed:int, ordinal:int)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool) or not isinstance(ordinal,int) or ordinal<0:
        raise ValueError("INPUT")
    r=random.Random((seed<<21)^ordinal^0xD311A7)
    s=str(r.randrange(10000,99999))
    raw,x,y,z,draft,final=[f"{k}_{s}" for k in ("RAW","X","Y","Z","DRAFT","FINAL")]
    caps={k:f"{k}_{s}" for k in ("PARSE","REASON","RETRIEVE","INTEGRATE","VERIFY","BACKUP")}
    ids={k:f"{k}_{s}" for k in ("A","B","B2","C","D","D2","E")}
    res_reason=f"REASON_NS_{s}";res_retrieve=f"RETRIEVE_NS_{s}";res_final=f"FINAL_NS_{s}"
    cls=CLASSES[ordinal%len(CLASSES)]
    shared=f"SHARED_NS_{s}"
    if cls=="RESOURCE_CONFLICT":
        res_reason=res_retrieve=shared

    steps=[
        {"id":ids["A"],"requires":[raw],"produces":[x],"cost":1.0,"capability":caps["PARSE"],"writes":[f"PARSE_NS_{s}"],"evidence_outputs":[f"EV_A_{s}"]},
        {"id":ids["B"],"requires":[x],"produces":[y],"cost":1.0,"capability":caps["REASON"],"writes":[res_reason],"evidence_outputs":[f"EV_B_{s}"]},
        {"id":ids["B2"],"requires":[x],"produces":[y],"cost":3.0,"capability":caps["BACKUP"],"writes":[res_reason],"evidence_outputs":[f"EV_B2_{s}"]},
        {"id":ids["C"],"requires":[x],"produces":[z],"cost":1.0,"capability":caps["RETRIEVE"],"writes":[res_retrieve],"evidence_outputs":[f"EV_C_{s}"]},
        {"id":ids["D"],"requires":[y,z],"produces":[draft],"cost":1.0,"capability":caps["INTEGRATE"],"writes":[res_final],"evidence_outputs":[f"EV_D_{s}"]},
        {"id":ids["D2"],"requires":[y,z],"produces":[draft],"cost":4.0,"capability":caps["BACKUP"],"writes":[res_final],"evidence_outputs":[f"EV_D2_{s}"]},
        {"id":ids["E"],"requires":[draft],"produces":[final],"cost":1.0,"capability":caps["VERIFY"],"writes":[res_final],"evidence_outputs":[f"EV_E_{s}"]},
    ]
    workers=[
        {"id":f"W1_{s}","capabilities":[caps["PARSE"],caps["REASON"]]},
        {"id":f"W2_{s}","capabilities":[caps["RETRIEVE"],caps["INTEGRATE"]]},
        {"id":f"W3_{s}","capabilities":[caps["RETRIEVE"],caps["INTEGRATE"]]},
        {"id":f"W4_{s}","capabilities":[caps["VERIFY"],caps["BACKUP"]]},
        {"id":f"W5_{s}","capabilities":[caps["BACKUP"],caps["REASON"]]},
    ]
    task={
        "initial_facts":[raw],
        "required_outputs":[final],
        "steps":steps,
        "workers":workers,
        "resource_capacities":{res_reason:1,res_retrieve:1,res_final:1,shared:2},
        "evidence_rules":{
            "producer_owns_output":True,
            "fanin_preserves_all_ancestor_evidence":True,
        },
    }
    receipt=None
    if cls=="WORKER_UNAVAILABLE":
        receipt={"receipt_id":f"R-{seed}-{ordinal}","kind":cls,"entity_id":f"W2_{s}","completed_task_ids":[ids["A"]]}
    elif cls=="STEP_UNAVAILABLE":
        receipt={"receipt_id":f"R-{seed}-{ordinal}","kind":cls,"entity_id":ids["B"],"completed_task_ids":[ids["A"]]}
    elif cls=="WORKER_CAPABILITY_REMOVED":
        receipt={"receipt_id":f"R-{seed}-{ordinal}","kind":cls,"entity_id":f"W2_{s}","capability":caps["INTEGRATE"],"completed_task_ids":[ids["A"]]}
    elif cls=="RESOURCE_CAPACITY_CHANGED":
        task["resource_capacities"][shared]=2
        # Make the two branch writes share a capacity-2 resource initially.
        for row in steps:
            if row["id"] in {ids["B"],ids["C"]}:
                row["writes"]=[shared]
        receipt={"receipt_id":f"R-{seed}-{ordinal}","kind":cls,"entity_id":shared,"capacity":1,"completed_task_ids":[ids["A"]]}
    elif cls in {"BASE_PARALLEL","RESOURCE_CONFLICT"}:
        # Still exercise receipt-free baseline plus a benign post-completion worker event.
        receipt={"receipt_id":f"R-{seed}-{ordinal}","kind":"WORKER_UNAVAILABLE","entity_id":f"W5_{s}","completed_task_ids":[ids["A"]]}

    return {
        "schema":SCHEMA,
        "behavior_id":"TASK_TO_DELEGATION_GRAPH_001",
        "case_id":f"DELEGATION-V2-{seed}-{ordinal}",
        "case_class":cls,
        "task":task,
        "_oracle":{"receipt":receipt},
    }


def public_initial(case:Mapping[str,Any])->dict[str,Any]:
    return {"schema":case["schema"],"case_id":case["case_id"],"task":case["task"]}


def public_after_receipt(case:Mapping[str,Any])->dict[str,Any]:
    return {"schema":case["schema"],"case_id":case["case_id"],"task":case["task"],"receipt":dict(case["_oracle"]["receipt"])}


def _effective(task,receipt,completed):
    disabled=set();unavailable=set();removed=defaultdict(set)
    caps={str(k):int(v) for k,v in task["resource_capacities"].items()}
    if receipt:
        kind=receipt["kind"];ent=str(receipt["entity_id"])
        if kind=="STEP_UNAVAILABLE":disabled.add(ent)
        elif kind=="WORKER_UNAVAILABLE":unavailable.add(ent)
        elif kind=="WORKER_CAPABILITY_REMOVED":removed[ent].add(str(receipt["capability"]))
        elif kind=="RESOURCE_CAPACITY_CHANGED":caps[ent]=int(receipt["capacity"])
    steps={}
    for row in task["steps"]:
        sid=row["id"]
        steps[sid]={
            "requires":set(row["requires"]),"produces":set(row["produces"]),
            "cost":float(row["cost"]),"capability":row["capability"],
            "writes":set(row["writes"]),"evidence":set(row["evidence_outputs"]),
            "available":sid not in disabled and sid not in completed and row.get("available",True) is True,
        }
    workers={}
    for row in task["workers"]:
        if row["id"] in unavailable:continue
        wc=set(row["capabilities"])-removed.get(row["id"],set())
        if wc:workers[row["id"]]=wc
    return steps,workers,caps


def _completed_facts(task,completed):
    facts=set(task["initial_facts"]);raw={x["id"]:x for x in task["steps"]}
    for sid in completed:
        row=raw[sid]
        if not set(row["requires"]).issubset(facts):
            raise ValueError("COMPLETED_PRECONDITION")
        facts.update(row["produces"])
    return facts


def _optimal_plan(task,receipt=None,completed=()):
    steps,_,_=_effective(task,receipt,set(completed))
    initial=_completed_facts(task,completed);required=set(task["required_outputs"])
    ids=sorted(s for s,x in steps.items() if x["available"])
    best=None
    for k in range(len(ids)+1):
        for subset in combinations(ids,k):
            for order in permutations(subset):
                facts=set(initial);producer={};deps={};ok=True
                for sid in order:
                    row=steps[sid]
                    if not row["requires"].issubset(facts):
                        ok=False;break
                    deps[sid]=sorted({producer[f] for f in row["requires"] if f not in initial and f in producer})
                    for f in row["produces"]:
                        if f not in facts:producer[f]=sid
                    facts|=row["produces"]
                if not ok or not required.issubset(facts):continue
                cost=sum(steps[s]["cost"] for s in order)
                plan={"task_ids":list(order),"dependencies":deps,"total_cost":cost}
                # Whole-contract optimum is over executable *and schedulable*
                # plans. A cheaper fact-producing plan that no declared workers
                # can execute is not a valid optimum.
                try:
                    _min_waves(task,plan,receipt,completed)
                except ValueError as exc:
                    if str(exc)=="NO_SCHEDULE":
                        continue
                    raise
                key=(cost,len(order),tuple(order))
                if best is None or key<best[0]:
                    best=(key,plan)
    if best is None:raise ValueError("NO_PLAN")
    return best[1]


def _resource_ok(tasks,steps,caps):
    use=defaultdict(int)
    for sid in tasks:
        for r in steps[sid]["writes"]:use[r]+=1
    return all(use[r]<=caps.get(r,1) for r in use)


def _wave_options(ready,steps,workers,caps):
    out=[]
    for k in range(1,min(len(ready),len(workers))+1):
        for tasks in combinations(sorted(ready),k):
            if not _resource_ok(tasks,steps,caps):continue
            for ws in permutations(sorted(workers),k):
                m=dict(zip(tasks,ws))
                if all(steps[s]["capability"] in workers[w] for s,w in m.items()):
                    out.append(m)
    return out


def _min_waves(task,plan,receipt=None,completed=()):
    steps,workers,caps=_effective(task,receipt,set(completed))
    ids=plan["task_ids"];deps=plan["dependencies"];target=frozenset(ids)
    q=deque([(frozenset(),0)]);seen={frozenset()}
    while q:
        done,d=q.popleft()
        if done==target:return d
        ready=[s for s in ids if s not in done and set(deps[s]).issubset(done)]
        for m in _wave_options(ready,steps,workers,caps):
            nd=frozenset(set(done)|set(m))
            if nd not in seen:
                seen.add(nd);q.append((nd,d+1))
    raise ValueError("NO_SCHEDULE")


def _validate_candidate(task,cand,opt,receipt=None,completed=()):
    if cand.get("status")!="PASS":return False,"STATUS"
    ids=cand.get("task_ids");deps=cand.get("dependencies");waves=cand.get("waves");assignment=cand.get("assignment")
    if ids!=opt["task_ids"]:return False,"TASK_SET_OR_ORDER"
    if deps!=opt["dependencies"]:return False,"DEPENDENCIES"
    if not isinstance(waves,list) or len(waves)!=_min_waves(task,opt,receipt,completed):return False,"WAVE_COUNT"
    steps,workers,caps=_effective(task,receipt,set(completed))
    seen=set()
    for wave in waves:
        if not isinstance(wave,list) or not wave:return False,"WAVE_INVALID"
        if not _resource_ok(wave,steps,caps):return False,"RESOURCE_CONFLICT"
        used=set()
        for sid in wave:
            if sid in seen:return False,"DUPLICATE_WORK"
            if not set(deps[sid]).issubset(seen):return False,"DEPENDENCY_VIOLATION"
            wid=assignment.get(sid) if isinstance(assignment,Mapping) else None
            if wid not in workers or steps[sid]["capability"] not in workers[wid]:return False,"CAPABILITY_ASSIGNMENT"
            if wid in used:return False,"WORKER_DOUBLE_BOOKED"
            used.add(wid)
        seen.update(wave)
    if seen!=set(ids):return False,"WAVE_COVERAGE"

    # Ownership and fan-in are load-bearing acceptance, not decoration.
    owners=cand.get("evidence_owners");fanin=cand.get("fanin_evidence");terminal=set(cand.get("terminal_evidence") or [])
    if not isinstance(owners,Mapping) or not isinstance(fanin,Mapping):return False,"EVIDENCE_FIELDS"
    raw={x["id"]:x for x in task["steps"]}
    expected_owners={}
    for sid in list(completed)+ids:
        for ev in raw[sid]["evidence_outputs"]:
            if ev in expected_owners and expected_owners[ev]!=sid:return False,"ORACLE_OWNER_CONFLICT"
            expected_owners[ev]=sid
    if dict(owners)!=dict(sorted(expected_owners.items())):return False,"OWNERSHIP_MISMATCH"

    # Every terminal result must preserve all evidence from completed + selected work.
    expected_terminal=set(expected_owners)
    if terminal!=expected_terminal:return False,"FANIN_EVIDENCE_LOSS"

    # Baselines: correctness is already exact. Require a strict advantage over at least
    # one naive baseline: serial wall-clock or fanout work/cost.
    serial=len(ids)
    candidate_waves=len(waves)
    naive_cost=sum(x["cost"] for x in steps.values() if x["available"])
    candidate_cost=float(cand.get("total_cost",math.inf))
    if not (candidate_waves<serial or candidate_cost<naive_cost):
        return False,"NO_BASELINE_ADVANTAGE"
    return True,"PASS"


def score_episode(case,initial,revised):
    task=case["task"]
    opt0=_optimal_plan(task)
    ok,reason=_validate_candidate(task,initial,opt0)
    if not ok:return {"pass":False,"reason":"INITIAL_"+reason}
    receipt=case["_oracle"]["receipt"];completed=list(receipt["completed_task_ids"])
    if set(completed)&set(revised.get("task_ids") or []):return {"pass":False,"reason":"COMPLETED_WORK_REPLAYED"}
    expected_prov={"kind":receipt["kind"],"entity_id":receipt["entity_id"],"completed_task_ids":completed}
    if receipt.get("capability") is not None:expected_prov["capability"]=receipt["capability"]
    if receipt.get("capacity") is not None:expected_prov["capacity"]=receipt["capacity"]
    if revised.get("receipt_id")!=receipt["receipt_id"] or revised.get("revision_provenance")!=expected_prov:
        return {"pass":False,"reason":"RECEIPT_PROVENANCE"}
    opt1=_optimal_plan(task,receipt,completed)
    ok,reason=_validate_candidate(task,revised,opt1,receipt,completed)
    if not ok:return {"pass":False,"reason":"REVISED_"+reason}
    changed=(
        initial.get("task_ids")!=revised.get("task_ids") or
        initial.get("assignment")!=revised.get("assignment") or
        initial.get("waves")!=revised.get("waves")
    )
    if receipt["kind"]!="WORKER_UNAVAILABLE" or receipt["entity_id"] not in set(initial.get("assignment",{}).values()):
        # Benign/unselected worker receipts may legitimately preserve the plan.
        if receipt["kind"] in {"STEP_UNAVAILABLE","WORKER_CAPABILITY_REMOVED","RESOURCE_CAPACITY_CHANGED"} and not changed:
            return {"pass":False,"reason":"LOAD_BEARING_RECEIPT_DID_NOT_CHANGE_PLAN"}
    return {"pass":True,"reason":"PASS","case_class":case["case_class"]}


def run_batch(seed:int,count:int,initial_solver,update_solver):
    rows=[]
    for i in range(count):
        case=generate_case(seed,i)
        try:
            first=initial_solver(public_initial(case))
            second=update_solver(public_after_receipt(case),first)
            v=score_episode(case,first,second)
        except Exception as exc:
            v={"pass":False,"reason":"EXCEPTION:"+type(exc).__name__+":"+str(exc)}
        rows.append({"case_id":case["case_id"],"class":case["case_class"],**v})
    passed=sum(int(bool(x["pass"])) for x in rows)
    return {
        "schema":"PROJECT_BRAIN_DELEGATION_WHOLE_DIMENSION_PREFLIGHT_RESULT_V2",
        "case_count":count,"passed":passed,"failed":count-passed,"all_pass":passed==count,
        "failures":[x for x in rows if not x["pass"]],
        "terminal_authority":False,"capability_credit_delta":0,"family_credit_delta":0,
        "incremental_spend_usd":0,
    }
