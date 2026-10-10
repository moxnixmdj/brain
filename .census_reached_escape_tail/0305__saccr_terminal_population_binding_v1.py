"""Frozen post-beacon terminal population binding for the active SA-CCR contract.

This module selects terminal cases only after a global candidate/evaluator
commitment and unpredictable beacon exist. It never replaces a failed case.
The candidate receives only proof.public_task(case); hidden oracle payload stays
inside the independent scorer.
"""
from __future__ import annotations

import hashlib
from typing import Any

from canonical.runtime import saccr_credit_information_safe_candidate as candidate
from canonical.runtime import saccr_credit_information_safe_proof as proof

BEHAVIOR_ID = "SA_CCR_CREDIT_EFFECTIVE_NOTIONAL_AND_ADDON_001"
ROUTE_POPULATION_VERSION = "SA_CCR_ACTIVE_CONTRACT_TERMINAL_POP_V1"
SAMPLE_COUNT = 512

_SINGLE = {"AAA","AA","A","BBB","BB","B","CCC"}
_INDEX = {"IG","SG"}

def derive_seed(commitment: str, beacon: str, index: int) -> int:
    if not isinstance(commitment,str) or not commitment:
        raise ValueError("COMMITMENT_REQUIRED")
    if not isinstance(beacon,str) or not beacon:
        raise ValueError("BEACON_REQUIRED")
    if not isinstance(index,int) or isinstance(index,bool) or not (0 <= index < SAMPLE_COUNT):
        raise ValueError("INDEX_OUT_OF_RANGE")
    case_id=f"{BEHAVIOR_ID}::{ROUTE_POPULATION_VERSION}::slot::{index}"
    raw=("PROJECT_BRAIN_TERMINAL_V2\0"+commitment+"\0"+beacon+"\0"+case_id).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8],"big")

def _coverage(case: dict[str,Any], acc: dict[str,set[str]]) -> None:
    rows=case["task"]["trades"]
    refs={}
    for r in rows:
        rating=str(r["credit_rating"]).upper()
        acc["index_or_single"].add("INDEX" if r["is_index"] else "SINGLE")
        (acc["index_ratings"] if r["is_index"] else acc["single_ratings"]).add(rating)
        acc["direction"].add(str(int(r["direction"])))
        acc["margin_state"].add("MARGINED" if r["margined_mpor"] is not None else "UNMARGINED")
        acc["start_branch"].add("NONPOSITIVE" if float(r["start"]) <= 0 else "POSITIVE")
        if r["margined_mpor"] is None:
            residual=max(float(r["end"])-float(r["start"]),0.04)
            acc["maturity_branch"].add("UNMARGINED_LT1" if residual < 1.0 else "UNMARGINED_GE1")
        else:
            acc["maturity_branch"].add("MARGINED_LT004" if float(r["margined_mpor"]) < 0.04 else "MARGINED_GE004")
        refs[str(r["reference"])]=refs.get(str(r["reference"]),0)+1
    if len(refs) >= 2:
        acc["aggregation"].add("MULTI_REFERENCE")
    if any(v >= 2 for v in refs.values()):
        acc["aggregation"].add("REPEATED_REFERENCE")

def run_population(commitment: str, beacon: str) -> dict[str,Any]:
    cov={k:set() for k in (
        "index_or_single","single_ratings","index_ratings","direction","margin_state",
        "start_branch","maturity_branch","aggregation"
    )}
    results=[]
    for i in range(SAMPLE_COUNT):
        seed=derive_seed(commitment,beacon,i)
        case=proof.generate_case(seed)
        public=proof.public_task(case)
        if "_oracle" in public:
            raise AssertionError("PUBLIC_TASK_ORACLE_LEAK")
        try:
            out=candidate.solve(public)
            verdict=proof.score_case(case,out)
            passed=bool(verdict.get("pass"))
            reason=str(verdict.get("reason",""))
        except Exception as exc:
            passed=False
            reason=type(exc).__name__+":"+str(exc)
        results.append({"slot":i,"seed":seed,"pass":passed,"reason":reason})
        _coverage(case,cov)

    missing=[]
    requirements={
        "index_or_single":{"INDEX","SINGLE"},
        "single_ratings":_SINGLE,
        "index_ratings":_INDEX,
        "direction":{"-1","1"},
        "margin_state":{"MARGINED","UNMARGINED"},
        "start_branch":{"NONPOSITIVE","POSITIVE"},
        "maturity_branch":{"UNMARGINED_LT1","UNMARGINED_GE1","MARGINED_LT004","MARGINED_GE004"},
        "aggregation":{"MULTI_REFERENCE","REPEATED_REFERENCE"},
    }
    for key,needed in requirements.items():
        absent=sorted(needed-cov[key])
        if absent:
            missing.append(key+":"+",".join(absent))

    failed=[r for r in results if not r["pass"]]
    passed=(not failed) and (not missing) and len(results)==SAMPLE_COUNT
    return {
        "schema":"PROJECT_BRAIN_SACCR_TERMINAL_POPULATION_RESULT_V1",
        "behavior_id":BEHAVIOR_ID,
        "route_population_version":ROUTE_POPULATION_VERSION,
        "sample_count":SAMPLE_COUNT,
        "executed_count":len(results),
        "pass":passed,
        "failed_slots":[r["slot"] for r in failed],
        "coverage_missing":missing,
        "coverage":{k:sorted(v) for k,v in cov.items()},
        "results":results,
        "case_replacement":False,
        "acceptance_rule":"ALL_512_CASES_EXACT_PASS_AND_ALL_FROZEN_METHOD_BRANCH_COVERAGE_PRESENT",
    }
