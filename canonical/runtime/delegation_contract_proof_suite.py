"""Contract-native direct proof oracle for TASK_TO_DELEGATION_GRAPH_001.

This is proof machinery, not capability credit. It scores a candidate task/delegation
graph against hidden explicit step contracts and worker capabilities using an
independent exhaustive oracle for:
- complete production of required outputs,
- minimum total selected-step cost,
- correct dependency ordering,
- capability-compatible worker assignments,
- minimum feasible parallel wave count.

The current bounded proof population is intentionally finite and exact. Raw semantic
task decomposition outside explicit contracts is not claimed.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations, permutations
from typing import Any, Mapping, Sequence
import math

SCHEMA="PROJECT_BRAIN_TASK_TO_DELEGATION_GRAPH_DIRECT_PROOF_V1"

def _valid_id(v:Any)->bool:
    return isinstance(v,str) and bool(v.strip())

def _step_map(hidden:Mapping[str,Any])->dict[str,dict[str,Any]]:
    out={}
    for s in hidden.get("steps",[]):
        sid=s.get("id")
        if not _valid_id(sid) or sid in out:
            raise ValueError("STEP_ID_INVALID_OR_DUPLICATE")
        req=set(s.get("requires",[])); prod=set(s.get("produces",[]))
        cost=s.get("cost")
        cap=s.get("capability")
        if not req.issubset(set(hidden.get("fact_universe",[]))) or not prod:
            raise ValueError("STEP_FACTS_INVALID:"+sid)
        if not isinstance(cost,(int,float)) or isinstance(cost,bool) or not math.isfinite(float(cost)) or float(cost)<0:
            raise ValueError("STEP_COST_INVALID:"+sid)
        if not _valid_id(cap):
            raise ValueError("STEP_CAPABILITY_INVALID:"+sid)
        out[sid]={"requires":req,"produces":prod,"cost":float(cost),"capability":cap}
    return out

def _worker_map(hidden:Mapping[str,Any])->dict[str,set[str]]:
    out={}
    for w in hidden.get("workers",[]):
        wid=w.get("id")
        if not _valid_id(wid) or wid in out:
            raise ValueError("WORKER_ID_INVALID_OR_DUPLICATE")
        caps=set(w.get("capabilities",[]))
        if not caps or any(not _valid_id(x) for x in caps):
            raise ValueError("WORKER_CAPABILITIES_INVALID:"+str(wid))
        out[wid]=caps
    return out

def _independent_optimal_plan(hidden:Mapping[str,Any])->dict[str,Any]:
    steps=_step_map(hidden)
    initial=set(hidden.get("initial_facts",[]))
    required=set(hidden.get("required_outputs",[]))
    if not required:
        raise ValueError("REQUIRED_OUTPUTS_EMPTY")
    best=None
    ids=sorted(steps)
    # Exhaust all step subsets and executable orders. Bound is kept small by frozen proof generator.
    if len(ids)>9:
        raise ValueError("PROOF_POPULATION_STEP_BOUND_EXCEEDED")
    for k in range(len(ids)+1):
        for subset in combinations(ids,k):
            for order in permutations(subset):
                facts=set(initial); executable=True
                deps={}; producer={}
                for tid in order:
                    s=steps[tid]
                    if not s["requires"].issubset(facts):
                        executable=False; break
                    d=set()
                    for f in s["requires"]:
                        if f not in initial and f in producer:
                            d.add(producer[f])
                    deps[tid]=sorted(d)
                    for f in s["produces"]:
                        if f not in facts:
                            producer[f]=tid
                    facts|=s["produces"]
                if not executable or not required.issubset(facts):
                    continue
                cost=sum(steps[t]["cost"] for t in order)
                key=(cost,len(order),tuple(order))
                if best is None or key<best[0]:
                    best=(key,{"task_ids":list(order),"dependencies":deps,"total_cost":cost})
    if best is None:
        raise ValueError("NO_EXECUTABLE_PLAN")
    return best[1]

def _validate_candidate_plan(hidden:Mapping[str,Any], candidate:Mapping[str,Any], optimum:Mapping[str,Any])->tuple[bool,str]:
    steps=_step_map(hidden)
    ids=candidate.get("task_ids")
    deps=candidate.get("dependencies")
    if not isinstance(ids,list) or len(ids)!=len(set(ids)) or any(x not in steps for x in ids):
        return False,"TASK_SET_INVALID"
    if set(ids)!=set(optimum["task_ids"]):
        return False,"NONOPTIMAL_OR_INCOMPLETE_TASK_SET"
    if abs(sum(steps[x]["cost"] for x in ids)-float(optimum["total_cost"]))>1e-9:
        return False,"NONOPTIMAL_COST"
    if not isinstance(deps,Mapping) or set(deps)!=set(ids):
        return False,"DEPENDENCY_MAP_INVALID"
    initial=set(hidden.get("initial_facts",[])); facts=set(initial); completed=set(); producer={}
    for tid in ids:
        ds=set(deps.get(tid,[]))
        if not ds.issubset(completed):
            return False,"DEPENDENCY_ORDER_VIOLATION"
        s=steps[tid]
        if not s["requires"].issubset(facts):
            return False,"PRECONDITION_NOT_SATISFIED"
        expected=set()
        for f in s["requires"]:
            if f not in initial and f in producer:
                expected.add(producer[f])
        if ds!=expected:
            return False,"DEPENDENCY_TRACE_INCOMPLETE_OR_SPURIOUS"
        for f in s["produces"]:
            if f not in facts:
                producer[f]=tid
        facts|=s["produces"]; completed.add(tid)
    if not set(hidden.get("required_outputs",[])).issubset(facts):
        return False,"OUTPUTS_INCOMPLETE"
    return True,"PASS"

def _ready(completed:set[str], selected:set[str], deps:Mapping[str,Sequence[str]])->list[str]:
    return sorted(t for t in selected-completed if set(deps[t]).issubset(completed))

def _wave_matchings(ready:list[str], steps:Mapping[str,Mapping[str,Any]], workers:Mapping[str,set[str]]):
    # Enumerate nonempty task->distinct-worker matchings for a wave.
    for k in range(1,min(len(ready),len(workers))+1):
        for tasks in combinations(ready,k):
            for wids in permutations(sorted(workers),k):
                pairs=dict(zip(tasks,wids))
                if all(steps[t]["capability"] in workers[w] for t,w in pairs.items()):
                    yield pairs

def _minimum_waves(hidden:Mapping[str,Any], task_ids:Sequence[str], deps:Mapping[str,Sequence[str]])->int:
    steps=_step_map(hidden); workers=_worker_map(hidden); selected=set(task_ids)
    frontier={frozenset():0}; seen={frozenset()}
    while frontier:
        nxt={}
        for state,depth in frontier.items():
            completed=set(state)
            if completed==selected:
                return depth
            ready=_ready(completed,selected,deps)
            for pairs in _wave_matchings(ready,steps,workers):
                ns=frozenset(completed|set(pairs))
                if ns not in seen:
                    seen.add(ns); nxt[ns]=depth+1
        frontier=nxt
    raise ValueError("NO_FEASIBLE_WORKER_SCHEDULE")

def _validate_schedule(hidden:Mapping[str,Any], candidate:Mapping[str,Any])->tuple[bool,str,int]:
    steps=_step_map(hidden); workers=_worker_map(hidden)
    task_ids=candidate["task_ids"]; deps=candidate["dependencies"]
    assignment=candidate.get("assignment"); waves=candidate.get("waves")
    if not isinstance(assignment,Mapping) or set(assignment)!=set(task_ids):
        return False,"ASSIGNMENT_INVALID",0
    for t,w in assignment.items():
        if w not in workers or steps[t]["capability"] not in workers[w]:
            return False,"WORKER_CAPABILITY_MISMATCH",0
    if not isinstance(waves,list) or not waves:
        return False,"WAVES_INVALID",0
    completed=set(); seen=set()
    for wave in waves:
        if not isinstance(wave,list) or not wave or len(wave)!=len(set(wave)):
            return False,"WAVE_INVALID",0
        used_workers=set()
        for t in wave:
            if t not in task_ids or t in seen:
                return False,"WAVE_TASK_INVALID_OR_DUPLICATE",0
            if not set(deps[t]).issubset(completed):
                return False,"WAVE_DEPENDENCY_VIOLATION",0
            w=assignment[t]
            if w in used_workers:
                return False,"WORKER_DOUBLE_BOOKED",0
            used_workers.add(w)
        completed|=set(wave); seen|=set(wave)
    if seen!=set(task_ids):
        return False,"WAVE_COVERAGE_INCOMPLETE",0
    optimum=_minimum_waves(hidden,task_ids,deps)
    if len(waves)!=optimum:
        return False,"NONOPTIMAL_PARALLEL_WAVE_COUNT",optimum
    return True,"PASS",optimum

def score(hidden:Mapping[str,Any], candidate:Mapping[str,Any])->dict[str,Any]:
    try:
        optimum=_independent_optimal_plan(hidden)
        ok,reason=_validate_candidate_plan(hidden,candidate,optimum)
        if not ok:
            return {"schema":SCHEMA,"pass":False,"reason":reason,"terminal_authority":False}
        sok,sreason,optwaves=_validate_schedule(hidden,candidate)
        return {
            "schema":SCHEMA,
            "pass":bool(sok),
            "reason":sreason,
            "oracle_min_cost":optimum["total_cost"],
            "oracle_min_waves":optwaves,
            "terminal_authority":False,
        }
    except Exception as exc:
        return {"schema":SCHEMA,"pass":False,"reason":type(exc).__name__+":"+str(exc),"terminal_authority":False}

def preflight_case()->tuple[dict[str,Any],dict[str,Any]]:
    hidden={
        "fact_universe":["RAW","X","Y","Z","FINAL"],
        "initial_facts":["RAW"],
        "required_outputs":["FINAL"],
        "steps":[
            {"id":"A","requires":["RAW"],"produces":["X"],"cost":1,"capability":"PARSE"},
            {"id":"B","requires":["X"],"produces":["Y"],"cost":1,"capability":"REASON"},
            {"id":"C","requires":["X"],"produces":["Z"],"cost":1,"capability":"RETRIEVE"},
            {"id":"D","requires":["Y","Z"],"produces":["FINAL"],"cost":1,"capability":"INTEGRATE"},
            {"id":"DISTRACTOR","requires":["RAW"],"produces":["Z"],"cost":9,"capability":"RETRIEVE"},
        ],
        "workers":[
            {"id":"W1","capabilities":["PARSE","REASON"]},
            {"id":"W2","capabilities":["RETRIEVE","INTEGRATE"]},
        ],
    }
    good={
        "task_ids":["A","B","C","D"],
        "dependencies":{"A":[],"B":["A"],"C":["A"],"D":["B","C"]},
        "assignment":{"A":"W1","B":"W1","C":"W2","D":"W2"},
        "waves":[["A"],["B","C"],["D"]],
    }
    return hidden,good
