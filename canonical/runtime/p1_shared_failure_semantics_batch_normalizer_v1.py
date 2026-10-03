"""Fail-closed normalizer/validator for the one-batch P1 minimum-reality observation.

This module does not infer failure semantics. It accepts only source-bound cases whose
failed checks explicitly carry DIRECT_CONTRACT or DERIVED_UPSTREAM semantics and
non-empty supporting evidence. It preserves all eligible cases in the selected source
batch and grants no execution or terminal credit by itself.
"""
from __future__ import annotations
import copy
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_P1_SHARED_FAILURE_SEMANTICS_BATCH_NORMALIZER_V1"
BEHAVIOR_ID="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
SURFACES=(
 "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
 "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
 "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
)
SEMANTICS={"DIRECT_CONTRACT","DERIVED_UPSTREAM"}

def _fail(reason:str)->dict[str,Any]:
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":reason}

def normalize_case(record:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(record,Mapping):
        return _fail("RECORD_NOT_OBJECT")
    if record.get("behavior_id")!=BEHAVIOR_ID:
        return _fail("BEHAVIOR_ID_DRIFT")
    surface=record.get("surface_id")
    if surface not in SURFACES:
        return _fail("SURFACE_NOT_FROZEN")
    batch_id=record.get("source_batch_id")
    if not isinstance(batch_id,str) or not batch_id:
        return _fail("SOURCE_BATCH_ID_REQUIRED")
    task=record.get("task")
    if not isinstance(task,Mapping):
        return _fail("TASK_INVALID")
    rows=task.get("trajectory")
    if not isinstance(rows,list) or not rows:
        return _fail("TRAJECTORY_INVALID")
    semantics_seen=set()
    failed_count=0
    for row in rows:
        if not isinstance(row,Mapping):
            return _fail("ROW_INVALID")
        checks=row.get("checks")
        if not isinstance(checks,list):
            return _fail("CHECKS_INVALID")
        for check in checks:
            if not isinstance(check,Mapping) or type(check.get("pass")) is not bool:
                return _fail("CHECK_INVALID")
            if check["pass"] is False:
                failed_count+=1
                if "failure_semantics" not in check:
                    return _fail("FAILURE_SEMANTICS_MISSING__NO_DEFAULT_ALLOWED")
                sem=check.get("failure_semantics")
                if sem not in SEMANTICS:
                    return _fail("FAILURE_SEMANTICS_INVALID")
                ev=check.get("evidence")
                if not isinstance(ev,list) or not ev or any(not isinstance(x,str) or not x for x in ev):
                    return _fail("FAILED_CHECK_SUPPORTING_RECEIPTS_REQUIRED")
                semantics_seen.add(sem)
    if failed_count==0:
        return _fail("NO_FAILED_CHECKS")
    return {
      "schema":SCHEMA,
      "status":"PASS__SOURCE_BOUND_EXPLICIT_FAILURE_SEMANTICS",
      "behavior_id":BEHAVIOR_ID,
      "surface_id":surface,
      "source_batch_id":batch_id,
      "semantics_seen":sorted(semantics_seen),
      "public_case":{"behavior_id":BEHAVIOR_ID,"task":copy.deepcopy(task)},
    }

def validate_batch(records:list[Mapping[str,Any]])->dict[str,Any]:
    if not isinstance(records,list) or not records:
        return _fail("BATCH_EMPTY")
    normalized=[]
    for r in records:
        x=normalize_case(r)
        if x.get("status")!="PASS__SOURCE_BOUND_EXPLICIT_FAILURE_SEMANTICS":
            return _fail("CASE_FAIL_CLOSED:"+str(x.get("reason")))
        normalized.append(x)
    batch_ids={x["source_batch_id"] for x in normalized}
    if len(batch_ids)!=1:
        return _fail("MULTIPLE_SOURCE_BATCH_IDS")
    surfaces={x["surface_id"] for x in normalized}
    if surfaces!=set(SURFACES):
        return _fail("ALL_THREE_FROZEN_SURFACES_REQUIRED")
    semantics={s for x in normalized for s in x["semantics_seen"]}
    if semantics!=SEMANTICS:
        return _fail("DIRECT_AND_DERIVED_SEMANTICS_BOTH_REQUIRED")
    return {
      "schema":SCHEMA,
      "status":"PASS__SHARED_BATCH_PREEXECUTION_SCHEMA",
      "source_batch_id":next(iter(batch_ids)),
      "surface_ids":list(SURFACES),
      "case_count":len(normalized),
      "semantics":sorted(semantics),
      "normalized_cases":normalized,
      "execution_authority":False,
      "capability_credit_delta":0,
      "family_credit_delta":0,
    }
