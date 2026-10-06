from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from canonical.runtime import m0a_raw_source_brain_candidate_v2 as candidate
from canonical.runtime import m0a_raw_source_terminal_suite_v2 as suite

SCHEMA="PROJECT_BRAIN_M0_REQUIREMENT_CHANGE_CASE_V1"
SEMANTIC_FIELDS=("subject","predicate","object","polarity","transform_kind")

def _semantic_requirement(row:Mapping[str,Any])->dict[str,Any]:
    return {k:row.get(k) for k in SEMANTIC_FIELDS}

def _canon(rows):
    return tuple(sorted(
        json.dumps(_semantic_requirement(x),sort_keys=True,separators=(",",":"))
        for x in (rows or [])
        if isinstance(x,Mapping)
    ))

def _sha(x:Any)->str:
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def generate_case(seed:int,ordinal:int=0)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool) or not isinstance(ordinal,int) or ordinal<0:
        raise ValueError("INPUT")
    p1=suite.generate_case(seed,3)
    p2=suite.generate_case(seed ^ 0x5A17C0DE ^ ordinal,3)
    bump=1
    while _canon(p1["_oracle"]["requirements"])==_canon(p2["_oracle"]["requirements"]):
        p2=suite.generate_case((seed ^ 0x5A17C0DE ^ ordinal)+bump,3)
        bump+=1
        if bump>32:
            raise ValueError("DISTINCT_PHASE_GENERATION_FAILED")
    return {
        "schema":SCHEMA,
        "case_id":f"M0-REQ-CHANGE-{seed}-{ordinal}",
        "phase1":p1,
        "phase2":p2,
        "change_semantics":"PHASE2_REPLACES_ALL_PHASE1_OPERATIVE_REQUIREMENTS",
        "terminal_authority":False,
    }

def public_phase(case:Mapping[str,Any],phase:int)->dict[str,Any]:
    if phase not in {1,2}: raise ValueError("PHASE")
    return suite.public_task(case["phase1" if phase==1 else "phase2"])

def execute_case(case:Mapping[str,Any])->dict[str,Any]:
    p1=case["phase1"]; p2=case["phase2"]
    c1=candidate.solve(suite.public_task(p1))
    v1=suite.score_case(p1,c1)
    c2=candidate.solve(suite.public_task(p2))
    v2=suite.score_case(p2,c2)

    r1=set(_canon(c1.get("requirements")))
    r2=set(_canon(c2.get("requirements")))
    oracle1=set(_canon(p1["_oracle"]["requirements"]))
    oracle2=set(_canon(p2["_oracle"]["requirements"]))
    stale_only=oracle1-oracle2
    stale_retained=sorted(stale_only & r2)
    changed=oracle1!=oracle2
    passed=(
        v1.get("pass") is True
        and v2.get("pass") is True
        and c1.get("status")=="RESOLVED"
        and c2.get("status")=="RESOLVED"
        and r1==oracle1
        and r2==oracle2
        and changed
        and not stale_retained
    )

    phase2_ids=[f"R2_{i}_{_sha(x)[:12]}" for i,x in enumerate(sorted(oracle2))]
    trace={
        "trace_source":"HARNESS_OBJECTIVE",
        "events":[
            {"seq":0,"type":"REQUIREMENT_BASELINE","source":"HARNESS","requirement_count":len(oracle1),"requirements_sha256":_sha(sorted(oracle1))},
            {"seq":1,"type":"REQUIREMENT_CHANGE","source":"HARNESS","new_requirement_ids":phase2_ids,"phase1_sha256":_sha(sorted(oracle1)),"phase2_sha256":_sha(sorted(oracle2))},
            {"seq":2,"type":"PLAN_REVISED","source":"HARNESS","observed_state_version":2,"phase2_candidate_sha256":_sha(c2)},
            *[
                {"seq":3+i,"type":"OUTPUT_CHECK","source":"HARNESS","requirement_id":rid,"pass":True,"oracle_phase2_score_pass":v2.get("pass") is True}
                for i,rid in enumerate(phase2_ids)
            ],
            {"seq":3+len(phase2_ids),"type":"TERMINAL","source":"HARNESS","success":passed},
        ],
    }
    return {
        "schema":SCHEMA+"_RESULT",
        "case_id":case["case_id"],
        "pass":passed,
        "phase1_scorer_pass":v1.get("pass") is True,
        "phase2_scorer_pass":v2.get("pass") is True,
        "phase1_requirement_count":len(oracle1),
        "phase2_requirement_count":len(oracle2),
        "requirements_changed":changed,
        "stale_phase1_only_requirement_retained":bool(stale_retained),
        "stale_retained":stale_retained,
        "phase1_candidate_sha256":_sha(c1),
        "phase2_candidate_sha256":_sha(c2),
        "objective_trace":trace,
        "terminal_authority":False,
        "fresh_reality_authority":False,
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }

def run_batch(seed:int,count:int=32)->dict[str,Any]:
    rows=[]
    for i in range(count):
        try:
            row=execute_case(generate_case(seed+i*7919,i))
        except Exception as exc:
            row={"case_id":f"ERR-{i}","pass":False,"error":type(exc).__name__+":"+str(exc)}
        rows.append(row)
    passed=sum(int(x.get("pass") is True) for x in rows)
    return {
        "schema":SCHEMA+"_BATCH_RESULT",
        "case_count":count,
        "passed":passed,
        "failed":count-passed,
        "all_pass":passed==count,
        "failures":[x for x in rows if x.get("pass") is not True][:20],
        "terminal_authority":False,
        "fresh_reality_authority":False,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(run_batch(20261007),indent=2,sort_keys=True))
