"""Frozen post-beacon terminal population binding V2 for TASK_TO_DELEGATION_GRAPH_001.

V2 composes both independently verified proof dimensions required by the repaired
scope relation:
1) whole-dimension receipt/resource/evidence/baseline behavior;
2) structurally varied DAG/fanin/fanout/alternative-plan behavior.

The candidate is frozen before the beacon. Every selected case is executed once,
with no replacement, adaptive selection, or tuning replay.
"""
from __future__ import annotations

import hashlib
from typing import Any

from canonical.runtime import delegation_whole_scope_candidate_v2 as candidate
from canonical.runtime import delegation_whole_scope_proof_v2 as interaction_proof
from canonical.runtime import delegation_structural_variety_proof_v3 as structural_proof

BEHAVIOR_ID="TASK_TO_DELEGATION_GRAPH_001"
ROUTE_POPULATION_VERSION="DELEGATION_SCOPE_REPAIRED_TERMINAL_POP_V2"
SAMPLE_COUNT=512
INTERACTION_COUNT=256
STRUCTURAL_COUNT=SAMPLE_COUNT-INTERACTION_COUNT
INTERACTION_CLASSES={
    "BASE_PARALLEL",
    "RESOURCE_CONFLICT",
    "WORKER_UNAVAILABLE",
    "STEP_UNAVAILABLE",
    "WORKER_CAPABILITY_REMOVED",
    "RESOURCE_CAPACITY_CHANGED",
}
STRUCTURAL_CLASSES={
    "CHAIN",
    "FORK_JOIN",
    "FANOUT_JOIN",
    "DUAL_ROOT_FANIN",
    "ALTERNATIVE_PLAN",
}


def derive_seed(commitment:str, beacon:str, population:str, index:int)->int:
    if not isinstance(commitment,str) or not commitment:
        raise ValueError("COMMITMENT_REQUIRED")
    if not isinstance(beacon,str) or not beacon:
        raise ValueError("BEACON_REQUIRED")
    if population not in {"interaction","structural"}:
        raise ValueError("POPULATION_INVALID")
    limit=INTERACTION_COUNT if population=="interaction" else STRUCTURAL_COUNT
    if not isinstance(index,int) or isinstance(index,bool) or not 0 <= index < limit:
        raise ValueError("INDEX_OUT_OF_RANGE")
    case_id=f"{BEHAVIOR_ID}::{ROUTE_POPULATION_VERSION}::{population}::slot::{index}"
    raw=("PROJECT_BRAIN_TERMINAL_V2\0"+commitment+"\0"+beacon+"\0"+case_id).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8],"big")


def _interaction_case(commitment:str,beacon:str,index:int)->dict[str,Any]:
    seed=derive_seed(commitment,beacon,"interaction",index)
    case=interaction_proof.generate_case(seed,index)
    public0=interaction_proof.public_initial(case)
    if "_oracle" in public0:
        raise AssertionError("INITIAL_PUBLIC_ORACLE_LEAK")
    first=candidate.solve_initial(public0)
    public1=interaction_proof.public_after_receipt(case)
    if "_oracle" in public1:
        raise AssertionError("RECEIPT_PUBLIC_ORACLE_LEAK")
    revised=candidate.solve_after_receipt(public1,first)
    verdict=interaction_proof.score_episode(case,first,revised)
    return {
        "population":"interaction",
        "index":index,
        "seed":seed,
        "case_class":str(case.get("case_class") or ""),
        "pass":bool(verdict.get("pass")),
        "reason":str(verdict.get("reason","")),
    }


def _structural_case(commitment:str,beacon:str,index:int)->dict[str,Any]:
    seed=derive_seed(commitment,beacon,"structural",index)
    case=structural_proof.generate_case(seed,index)
    public=structural_proof.public_case(case)
    if "_oracle" in public:
        raise AssertionError("STRUCTURAL_PUBLIC_ORACLE_LEAK")
    result=candidate.solve_initial(public)
    verdict=structural_proof.score_case(case,result)
    return {
        "population":"structural",
        "index":index,
        "seed":seed,
        "case_class":str(case.get("case_class") or ""),
        "pass":bool(verdict.get("pass")),
        "reason":str(verdict.get("reason","")),
    }


def run_population(commitment:str,beacon:str)->dict[str,Any]:
    rows=[]
    interaction_classes=set()
    structural_classes=set()
    for index in range(INTERACTION_COUNT):
        try:
            row=_interaction_case(commitment,beacon,index)
        except Exception as exc:
            row={
                "population":"interaction","index":index,
                "seed":derive_seed(commitment,beacon,"interaction",index),
                "case_class":"","pass":False,
                "reason":type(exc).__name__+":"+str(exc),
            }
        rows.append(row)
        if row["case_class"]:
            interaction_classes.add(row["case_class"])
    for index in range(STRUCTURAL_COUNT):
        try:
            row=_structural_case(commitment,beacon,index)
        except Exception as exc:
            row={
                "population":"structural","index":index,
                "seed":derive_seed(commitment,beacon,"structural",index),
                "case_class":"","pass":False,
                "reason":type(exc).__name__+":"+str(exc),
            }
        rows.append(row)
        if row["case_class"]:
            structural_classes.add(row["case_class"])

    failed=[x for x in rows if not x["pass"]]
    missing_interaction=sorted(INTERACTION_CLASSES-interaction_classes)
    missing_structural=sorted(STRUCTURAL_CLASSES-structural_classes)
    passed=(
        len(rows)==SAMPLE_COUNT
        and not failed
        and not missing_interaction
        and not missing_structural
    )
    return {
        "schema":"PROJECT_BRAIN_DELEGATION_TERMINAL_POPULATION_RESULT_V2",
        "behavior_id":BEHAVIOR_ID,
        "route_population_version":ROUTE_POPULATION_VERSION,
        "sample_count":SAMPLE_COUNT,
        "interaction_count":INTERACTION_COUNT,
        "structural_count":STRUCTURAL_COUNT,
        "executed_count":len(rows),
        "pass":passed,
        "failed_slots":[f"{x['population']}:{x['index']}" for x in failed],
        "interaction_coverage_missing":missing_interaction,
        "structural_coverage_missing":missing_structural,
        "covered_interaction_classes":sorted(interaction_classes),
        "covered_structural_classes":sorted(structural_classes),
        "results":rows,
        "adaptive_case_selection":False,
        "replay_for_tuning":False,
        "case_replacement":False,
        "acceptance_rule":"ALL_512_CASES_EXACT_PASS__ALL_SIX_INTERACTION_CLASSES_AND_ALL_FIVE_STRUCTURAL_CLASSES_PRESENT",
        "terminal_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }
