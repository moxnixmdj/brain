"""Pre-beacon terminal population executor V2 for TASK_TO_DELEGATION_GRAPH_001.

This module binds two independently verified, information-safe population families
to one frozen terminal population:
- dynamic/resource/failure/evidence cases from whole-scope V2
- structurally varied DAG cases from V3

The candidate is frozen before any beacon. Terminal seeds are derived only from the
frozen commitment, the later public beacon, and slot ID. No case replacement,
adaptive selection, or tuning replay is permitted.
"""
from __future__ import annotations

import hashlib
from typing import Any

from canonical.runtime import delegation_whole_scope_candidate_v2 as candidate
from canonical.runtime import delegation_whole_scope_proof_v2 as dynamic_proof
from canonical.runtime import delegation_structural_variety_proof_v3 as structural_proof

BEHAVIOR_ID="TASK_TO_DELEGATION_GRAPH_001"
ROUTE_POPULATION_VERSION="DELEGATION_TERMINAL_POPULATION_V2"
SAMPLE_COUNT=512
DYNAMIC_COUNT=256
STRUCTURAL_COUNT=256

DYNAMIC_CLASSES={
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
REQUIRED_CLASS_TAGS={
    *("DYNAMIC:"+x for x in DYNAMIC_CLASSES),
    *("STRUCTURAL:"+x for x in STRUCTURAL_CLASSES),
}


def case_id(index:int)->str:
    if not isinstance(index,int) or isinstance(index,bool) or not 0 <= index < SAMPLE_COUNT:
        raise ValueError("INDEX_OUT_OF_RANGE")
    return f"{BEHAVIOR_ID}::{ROUTE_POPULATION_VERSION}::slot::{index}"


def derive_seed(commitment:str, beacon:str, index:int)->int:
    if not isinstance(commitment,str) or not commitment:
        raise ValueError("COMMITMENT_REQUIRED")
    if not isinstance(beacon,str) or not beacon:
        raise ValueError("BEACON_REQUIRED")
    cid=case_id(index)
    raw=("PROJECT_BRAIN_TERMINAL_V2\0"+commitment+"\0"+beacon+"\0"+cid).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8],"big")


def _dynamic_case(seed:int, ordinal:int)->dict[str,Any]:
    case=dynamic_proof.generate_case(seed,ordinal)
    public0=dynamic_proof.public_initial(case)
    if "_oracle" in public0:
        raise AssertionError("DYNAMIC_INITIAL_ORACLE_LEAK")
    first=candidate.solve_initial(public0)
    public1=dynamic_proof.public_after_receipt(case)
    if "_oracle" in public1:
        raise AssertionError("DYNAMIC_RECEIPT_ORACLE_LEAK")
    revised=candidate.solve_after_receipt(public1,first)
    verdict=dynamic_proof.score_episode(case,first,revised)
    return {
        "pass":bool(verdict.get("pass")),
        "reason":str(verdict.get("reason","")),
        "class_tag":"DYNAMIC:"+str(case.get("case_class") or ""),
    }


def _structural_case(seed:int, ordinal:int)->dict[str,Any]:
    case=structural_proof.generate_case(seed,ordinal)
    public=structural_proof.public_case(case)
    if "_oracle" in public:
        raise AssertionError("STRUCTURAL_ORACLE_LEAK")
    out=candidate.solve_initial(public)
    verdict=structural_proof.score_case(case,out)
    return {
        "pass":bool(verdict.get("pass")),
        "reason":str(verdict.get("reason","")),
        "class_tag":"STRUCTURAL:"+str(case.get("case_class") or ""),
    }


def run_population(commitment:str, beacon:str)->dict[str,Any]:
    rows=[]
    covered=set()
    for index in range(SAMPLE_COUNT):
        seed=derive_seed(commitment,beacon,index)
        try:
            if index < DYNAMIC_COUNT:
                verdict=_dynamic_case(seed,index)
                family="DYNAMIC"
                local_ordinal=index
            else:
                local_ordinal=index-DYNAMIC_COUNT
                verdict=_structural_case(seed,local_ordinal)
                family="STRUCTURAL"
            covered.add(verdict["class_tag"])
            passed=verdict["pass"]
            reason=verdict["reason"]
            class_tag=verdict["class_tag"]
        except Exception as exc:
            family="DYNAMIC" if index < DYNAMIC_COUNT else "STRUCTURAL"
            local_ordinal=index if index < DYNAMIC_COUNT else index-DYNAMIC_COUNT
            passed=False
            reason=type(exc).__name__+":"+str(exc)
            class_tag=family+":UNKNOWN"
        rows.append({
            "slot":index,
            "seed":seed,
            "family":family,
            "local_ordinal":local_ordinal,
            "class_tag":class_tag,
            "pass":passed,
            "reason":reason,
        })

    failures=[r for r in rows if not r["pass"]]
    missing=sorted(REQUIRED_CLASS_TAGS-covered)
    passed=(not failures) and (not missing) and len(rows)==SAMPLE_COUNT
    return {
        "schema":"PROJECT_BRAIN_DELEGATION_TERMINAL_POPULATION_RESULT_V2",
        "behavior_id":BEHAVIOR_ID,
        "route_population_version":ROUTE_POPULATION_VERSION,
        "sample_count":SAMPLE_COUNT,
        "dynamic_count":DYNAMIC_COUNT,
        "structural_count":STRUCTURAL_COUNT,
        "executed_count":len(rows),
        "pass":passed,
        "failed_slots":[r["slot"] for r in failures],
        "coverage_missing":missing,
        "covered_class_tags":sorted(covered),
        "results":rows,
        "adaptive_case_selection":False,
        "replay_for_tuning":False,
        "case_replacement":False,
        "allowed_failed_cases":0,
        "acceptance_rule":"ALL_512_CASES_PASS_HIDDEN_ORACLE_AND_ALL_11_FROZEN_DYNAMIC_AND_STRUCTURAL_CLASS_FAMILIES_PRESENT",
        "terminal_acceptance_proof_mode":"THEORETICAL_CEILING_OR_MACHINE_CHECKED_FORMAL_PROOF",
        "ceiling_definition":"100_PERCENT_HIDDEN_ORACLE_CORRECTNESS_WITH_REQUIRED_BASELINE_ADVANTAGE_AND_ZERO_PROVENANCE_RESOURCE_OR_FANIN_FAILURES_ON_THE_FROZEN_SCOPE_EQUIVALENT_POST_FREEZE_POPULATION",
        "terminal_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "incremental_spend_usd":0,
    }
