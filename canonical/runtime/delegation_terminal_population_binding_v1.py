"""Frozen pre-beacon terminal population binding for TASK_TO_DELEGATION_GRAPH_001.

Cases are selected only after a global commitment and unpredictable beacon exist.
No failed case is replaced, and no terminal result may be replayed for tuning.
The candidate sees only the frozen public task/receipt surfaces; optimal plans,
assignments, schedules, ownership/fan-in truth and baseline comparisons remain
inside the independent oracle.
"""
from __future__ import annotations

import hashlib
from typing import Any

from canonical.runtime import delegation_whole_scope_candidate_v2 as candidate
from canonical.runtime import delegation_whole_scope_proof_v2 as proof

BEHAVIOR_ID="TASK_TO_DELEGATION_GRAPH_001"
ROUTE_POPULATION_VERSION="DELEGATION_WHOLE_SCOPE_TERMINAL_POP_V1"
SAMPLE_COUNT=192
_REQUIRED_CLASSES=set(proof.CLASSES)


def derive_seed(commitment:str, beacon:str, index:int)->int:
    if not isinstance(commitment,str) or not commitment:
        raise ValueError("COMMITMENT_REQUIRED")
    if not isinstance(beacon,str) or not beacon:
        raise ValueError("BEACON_REQUIRED")
    if not isinstance(index,int) or isinstance(index,bool) or not (0 <= index < SAMPLE_COUNT):
        raise ValueError("INDEX_OUT_OF_RANGE")
    case_id=f"{BEHAVIOR_ID}::{ROUTE_POPULATION_VERSION}::slot::{index}"
    raw=("PROJECT_BRAIN_TERMINAL_V2\0"+commitment+"\0"+beacon+"\0"+case_id).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8],"big")


def run_population(commitment:str, beacon:str)->dict[str,Any]:
    results=[]
    classes=set()
    for index in range(SAMPLE_COUNT):
        seed=derive_seed(commitment,beacon,index)
        case=proof.generate_case(seed,index)
        public0=proof.public_initial(case)
        public1=proof.public_after_receipt(case)
        if "_oracle" in public0 or "_oracle" in public1:
            raise AssertionError("PUBLIC_TASK_ORACLE_LEAK")
        try:
            first=candidate.solve_initial(public0)
            second=candidate.solve_after_receipt(public1,first)
            verdict=proof.score_episode(case,first,second)
            passed=bool(verdict.get("pass"))
            reason=str(verdict.get("reason",""))
        except Exception as exc:
            passed=False
            reason=type(exc).__name__+":"+str(exc)
        cls=str(case.get("case_class") or "")
        classes.add(cls)
        results.append({
            "slot":index,
            "seed":seed,
            "case_class":cls,
            "pass":passed,
            "reason":reason,
        })

    missing_classes=sorted(_REQUIRED_CLASSES-classes)
    failed=[row for row in results if not row["pass"]]
    class_counts={name:sum(1 for row in results if row["case_class"]==name) for name in sorted(_REQUIRED_CLASSES)}
    passed=(not failed) and (not missing_classes) and len(results)==SAMPLE_COUNT
    return {
        "schema":"PROJECT_BRAIN_DELEGATION_TERMINAL_POPULATION_RESULT_V1",
        "behavior_id":BEHAVIOR_ID,
        "route_population_version":ROUTE_POPULATION_VERSION,
        "sample_count":SAMPLE_COUNT,
        "executed_count":len(results),
        "pass":passed,
        "failed_slots":[row["slot"] for row in failed],
        "coverage_missing":missing_classes,
        "class_counts":class_counts,
        "results":results,
        "case_replacement":False,
        "replay_for_tuning":False,
        "acceptance_rule":"ALL_192_CASES_EXACT_HIDDEN_ORACLE_PASS_AND_ALL_SIX_FROZEN_RECEIPT_RESOURCE_CLASSES_PRESENT",
    }
