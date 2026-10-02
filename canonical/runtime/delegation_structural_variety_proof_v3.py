"""Structurally varied information-safe proof for TASK_TO_DELEGATION_GRAPH_001.

This supplements the whole-dimension V2 receipt/resource/evidence proof with fresh
DAG families: chains, fork-join, fanout-join, dual-root fan-in, and alternative
plans. The candidate sees only the explicit task contract. Acceptance reuses the
independent V2 oracle, never the candidate implementation.
"""
from __future__ import annotations

from collections import Counter
import random
from typing import Any, Mapping

from canonical.runtime import delegation_whole_scope_proof_v2 as oracle

SCHEMA="PROJECT_BRAIN_DELEGATION_STRUCTURAL_VARIETY_PROOF_V3"
CLASSES=("CHAIN","FORK_JOIN","FANOUT_JOIN","DUAL_ROOT_FANIN","ALTERNATIVE_PLAN")


def _step(sid, requires, produces, cost, cap, suffix):
    return {
        "id": sid,
        "requires": list(requires),
        "produces": list(produces),
        "cost": float(cost),
        "capability": cap,
        "writes": [f"RES_{sid}_{suffix}"],
        "evidence_outputs": [f"EV_{sid}_{suffix}"],
    }


def generate_case(seed:int, ordinal:int)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool) or not isinstance(ordinal,int) or ordinal<0:
        raise ValueError("INPUT")
    r=random.Random((seed<<23)^ordinal^0xD36A9)
    suffix=str(r.randrange(100000,999999))
    cls=CLASSES[ordinal%len(CLASSES)]
    raw=f"RAW_{suffix}"; final=f"FINAL_{suffix}"
    initial=[raw]
    steps=[]

    if cls=="CHAIN":
        a,b=f"A_{suffix}",f"B_{suffix}"
        steps=[
            _step(f"S1_{suffix}",[raw],[a],1,"C1",suffix),
            _step(f"S2_{suffix}",[a],[b],1,"C2",suffix),
            _step(f"S3_{suffix}",[b],[final],1,"C3",suffix),
        ]
    elif cls=="FORK_JOIN":
        a,b,c=f"A_{suffix}",f"B_{suffix}",f"C_{suffix}"
        steps=[
            _step(f"S1_{suffix}",[raw],[a],1,"C1",suffix),
            _step(f"S2_{suffix}",[a],[b],1,"C2",suffix),
            _step(f"S3_{suffix}",[a],[c],1,"C3",suffix),
            _step(f"S4_{suffix}",[b,c],[final],1,"C4",suffix),
        ]
    elif cls=="FANOUT_JOIN":
        a,b,c,d=f"A_{suffix}",f"B_{suffix}",f"C_{suffix}",f"D_{suffix}"
        steps=[
            _step(f"S1_{suffix}",[raw],[a],1,"C1",suffix),
            _step(f"S2_{suffix}",[a],[b],1,"C2",suffix),
            _step(f"S3_{suffix}",[a],[c],1,"C3",suffix),
            _step(f"S4_{suffix}",[a],[d],1,"C4",suffix),
            _step(f"S5_{suffix}",[b,c,d],[final],1,"C5",suffix),
        ]
    elif cls=="DUAL_ROOT_FANIN":
        raw2=f"RAW2_{suffix}"; initial=[raw,raw2]
        a,b,c=f"A_{suffix}",f"B_{suffix}",f"C_{suffix}"
        steps=[
            _step(f"S1_{suffix}",[raw],[a],1,"C1",suffix),
            _step(f"S2_{suffix}",[raw2],[b],1,"C2",suffix),
            _step(f"S3_{suffix}",[a,b],[c],1,"C3",suffix),
            _step(f"S4_{suffix}",[c],[final],1,"C4",suffix),
        ]
    else:
        a,b,c=f"A_{suffix}",f"B_{suffix}",f"C_{suffix}"
        steps=[
            _step(f"S1_{suffix}",[raw],[a],1,"C1",suffix),
            _step(f"S2_CHEAP_{suffix}",[a],[b],1,"C2",suffix),
            _step(f"S2_ALT_{suffix}",[a],[b],4,"C2B",suffix),
            _step(f"S3_{suffix}",[a],[c],1,"C3",suffix),
            _step(f"S4_{suffix}",[b,c],[final],1,"C4",suffix),
        ]

    # Expensive direct decoy makes the naive-fanout baseline strictly worse even
    # for serial topologies while preserving a valid alternative plan.
    steps.append(_step(f"DECOY_{suffix}",initial,[final],99,"C_DECOY",suffix))
    caps=sorted({s["capability"] for s in steps})
    workers=[
        {"id":f"W{i}_{suffix}","capabilities":caps}
        for i in range(1,6)
    ]
    resources={s["writes"][0]:1 for s in steps}
    task={
        "initial_facts":initial,
        "required_outputs":[final],
        "steps":steps,
        "workers":workers,
        "resource_capacities":resources,
        "evidence_rules":{
            "producer_owns_output":True,
            "fanin_preserves_all_ancestor_evidence":True,
        },
    }
    return {
        "schema":SCHEMA,
        "behavior_id":"TASK_TO_DELEGATION_GRAPH_001",
        "case_id":f"DELEGATION-STRUCT-{seed}-{ordinal}",
        "case_class":cls,
        "task":task,
    }


def public_case(case:Mapping[str,Any])->dict[str,Any]:
    return {"schema":case["schema"],"case_id":case["case_id"],"task":case["task"]}


def score_case(case:Mapping[str,Any], candidate:Mapping[str,Any])->dict[str,Any]:
    try:
        opt=oracle._optimal_plan(case["task"])
        ok,reason=oracle._validate_candidate(case["task"],candidate,opt)
        return {"pass":bool(ok),"reason":reason,"case_class":case["case_class"]}
    except Exception as exc:
        return {"pass":False,"reason":type(exc).__name__+":"+str(exc),"case_class":case["case_class"]}


def run_batch(seed:int,count:int,solver)->dict[str,Any]:
    rows=[]
    for i in range(count):
        case=generate_case(seed,i)
        try:
            verdict=score_case(case,solver(public_case(case)))
        except Exception as exc:
            verdict={"pass":False,"reason":"CANDIDATE_EXCEPTION:"+type(exc).__name__+":"+str(exc),"case_class":case["case_class"]}
        rows.append({"case_id":case["case_id"],**verdict})
    passed=sum(int(x["pass"]) for x in rows)
    classes=Counter(x["case_class"] for x in rows if x["pass"])
    return {
        "schema":"PROJECT_BRAIN_DELEGATION_STRUCTURAL_VARIETY_PREFLIGHT_RESULT_V3",
        "case_count":count,
        "passed":passed,
        "failed":count-passed,
        "all_pass":passed==count,
        "class_pass_counts":dict(sorted(classes.items())),
        "failures":[x for x in rows if not x["pass"]],
        "terminal_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "incremental_spend_usd":0,
    }
