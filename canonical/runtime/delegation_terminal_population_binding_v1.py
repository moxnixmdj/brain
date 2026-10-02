"""Frozen post-beacon terminal population binding for TASK_TO_DELEGATION_GRAPH_001.

Selection follows GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.  The
candidate is frozen before the beacon, receives only public task/receipt state,
and every selected case is scored exactly once with no replacement or tuning
replay.
"""
from __future__ import annotations

import hashlib
from typing import Any

from canonical.runtime import delegation_whole_scope_candidate_v2 as candidate
from canonical.runtime import delegation_whole_scope_proof_v2 as proof

BEHAVIOR_ID="TASK_TO_DELEGATION_GRAPH_001"
ROUTE_POPULATION_VERSION="DELEGATION_WHOLE_SCOPE_TERMINAL_POP_V1"
SAMPLE_COUNT=512
REQUIRED_CLASSES={
    "BASE_PARALLEL",
    "RESOURCE_CONFLICT",
    "WORKER_UNAVAILABLE",
    "STEP_UNAVAILABLE",
    "WORKER_CAPABILITY_REMOVED",
    "RESOURCE_CAPACITY_CHANGED",
}

def derive_seed(commitment:str, beacon:str, index:int)->int:
    if not isinstance(commitment,str) or not commitment:
        raise ValueError("COMMITMENT_REQUIRED")
    if not isinstance(beacon,str) or not beacon:
        raise ValueError("BEACON_REQUIRED")
    if not isinstance(index,int) or isinstance(index,bool) or not 0 <= index < SAMPLE_COUNT:
        raise ValueError("INDEX_OUT_OF_RANGE")
    case_id=f"{BEHAVIOR_ID}::{ROUTE_POPULATION_VERSION}::slot::{index}"
    raw=("PROJECT_BRAIN_TERMINAL_V2\0"+commitment+"\0"+beacon+"\0"+case_id).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8],"big")

def run_population(commitment:str, beacon:str)->dict[str,Any]:
    results=[]
    classes=set()
    for index in range(SAMPLE_COUNT):
        seed=derive_seed(commitment,beacon,index)
        try:
            case=proof.generate_case(seed,index)
            classes.add(str(case.get("case_class") or ""))
            public0=proof.public_initial(case)
            if "_oracle" in public0:
                raise AssertionError("INITIAL_PUBLIC_ORACLE_LEAK")
            first=candidate.solve_initial(public0)
            public1=proof.public_after_receipt(case)
            if "_oracle" in public1:
                raise AssertionError("RECEIPT_PUBLIC_ORACLE_LEAK")
            revised=candidate.solve_after_receipt(public1,first)
            verdict=proof.score_episode(case,first,revised)
            passed=bool(verdict.get("pass"))
            reason=str(verdict.get("reason",""))
        except Exception as exc:
            passed=False
            reason=type(exc).__name__+":"+str(exc)
        results.append({"slot":index,"seed":seed,"pass":passed,"reason":reason})

    failed=[r for r in results if not r["pass"]]
    missing=sorted(REQUIRED_CLASSES-classes)
    passed=(not failed) and (not missing) and len(results)==SAMPLE_COUNT
    return {
        "schema":"PROJECT_BRAIN_DELEGATION_TERMINAL_POPULATION_RESULT_V1",
        "behavior_id":BEHAVIOR_ID,
        "route_population_version":ROUTE_POPULATION_VERSION,
        "sample_count":SAMPLE_COUNT,
        "executed_count":len(results),
        "pass":passed,
        "failed_slots":[r["slot"] for r in failed],
        "coverage_missing":missing,
        "covered_case_classes":sorted(classes),
        "results":results,
        "adaptive_case_selection":False,
        "replay_for_tuning":False,
        "case_replacement":False,
        "acceptance_rule":"ALL_512_CASES_EXACT_PASS_AND_ALL_SIX_FROZEN_DELEGATION_CASE_CLASSES_PRESENT",
        "terminal_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }
