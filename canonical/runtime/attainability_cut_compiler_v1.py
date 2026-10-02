"""Fail-closed attainability compiler for scarce acceptance actions."""
from __future__ import annotations
from typing import Any, Mapping
SCHEMA = "PROJECT_BRAIN_ATTAINABILITY_CUT_VERDICT_V1"

def _fail(code: str) -> dict[str, Any]:
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":[code],"attainability_state":"INVALID","reality_execution_authorized":False}

def evaluate(spec: Mapping[str, Any]) -> dict[str, Any]:
    for key in ("total_task_count","trials_per_task","required_successes"):
        v=spec.get(key)
        if isinstance(v,bool) or not isinstance(v,int) or v<0:
            return _fail("INVALID_"+key.upper())
    incompatible=spec.get("hardware_incompatible_task_identities")
    zero_rows=spec.get("irreversibly_zero_hardware_compatible_tasks")
    completed=spec.get("completed_creditable_tasks",[])
    if not isinstance(incompatible,list) or not isinstance(zero_rows,list) or not isinstance(completed,list):
        return _fail("TASK_SETS_NOT_LISTS")
    incompatible_ids=list(incompatible)
    zero_ids=[r.get("task_identity_sha256") for r in zero_rows if isinstance(r,Mapping)]
    completed_ids=[r.get("task_identity_sha256") for r in completed if isinstance(r,Mapping)]
    all_ids=incompatible_ids+zero_ids+completed_ids
    if any(not isinstance(x,str) or not x for x in all_ids):
        return _fail("INVALID_TASK_IDENTITY")
    if len(all_ids)!=len(set(all_ids)):
        return _fail("TASK_SET_OVERLAP_OR_DUPLICATE")
    if len(all_ids)>spec["total_task_count"]:
        return _fail("ACCOUNTED_TASKS_EXCEED_TOTAL")
    completed_successes=0
    for row in completed:
        s=row.get("successes")
        if isinstance(s,bool) or not isinstance(s,int) or s<0 or s>spec["trials_per_task"]:
            return _fail("INVALID_COMPLETED_SUCCESS_COUNT")
        completed_successes+=s
    remaining=spec["total_task_count"]-len(incompatible_ids)-len(zero_ids)-len(completed_ids)
    lower=completed_successes
    upper=lower+remaining*spec["trials_per_task"]
    required=spec["required_successes"]
    state="PROVED" if lower>=required else ("IMPOSSIBLE" if upper<required else "OPEN")
    return {"schema":SCHEMA,"status":"ACTIVE_FAIL_CLOSED","pass":True,"errors":[],"lower_bound_successes":lower,"upper_bound_successes":upper,"required_successes":required,"remaining_creditable_task_count":remaining,"hardware_incompatible_task_count":len(incompatible_ids),"irreversibly_zero_hardware_compatible_task_count":len(zero_ids),"completed_creditable_task_count":len(completed_ids),"attainability_state":state,"reality_execution_authorized":state=="OPEN","rule":"REALITY_ONLY_WHEN_LOWER_LT_THRESHOLD_LE_UPPER"}
