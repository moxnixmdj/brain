"""Brain candidate for trajectory causal-localization proof V2.

Generates repairs directly from the visible step contracts. No evaluator,
oracle, hidden cause label, or predeclared repair candidate list is imported.
"""
from __future__ import annotations
from typing import Any, Mapping


def _terminal_after(task:Mapping[str,Any], step_index:int, replacement:int)->int:
    rows=task.get("trajectory")
    if not isinstance(rows,list) or not rows:
        raise ValueError("TRAJECTORY_INVALID")
    total=int(task["initial_state"])
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            raise ValueError("TRAJECTORY_ROW_INVALID")
        value=replacement if i==step_index else row.get("observed_delta")
        if not isinstance(value,int) or isinstance(value,bool):
            raise ValueError("DELTA_INVALID")
        total+=value
    return total


def solve(public_case:Mapping[str,Any])->dict[str,Any]:
    task=public_case.get("task")
    if not isinstance(task,Mapping):
        return {"status":"FAIL_CLOSED","reason":"TASK_INVALID"}
    rows=task.get("trajectory")
    target=task.get("terminal_target")
    if not isinstance(rows,list) or not isinstance(target,int) or isinstance(target,bool):
        return {"status":"FAIL_CLOSED","reason":"TRAJECTORY_OR_TARGET_INVALID"}

    rescuers=[]
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            return {"status":"FAIL_CLOSED","reason":"TRAJECTORY_ROW_INVALID"}
        aid=row.get("action_id")
        got=row.get("observed_delta")
        expected=row.get("contract_delta")
        if not isinstance(aid,str) or not isinstance(got,int) or not isinstance(expected,int):
            return {"status":"FAIL_CLOSED","reason":"STEP_CONTRACT_INVALID"}
        if got==expected:
            continue
        if _terminal_after(task,i,expected)==target:
            rescuers.append({"action_id":aid,"replacement_delta":expected})

    rescuers=sorted(rescuers,key=lambda x:(x["action_id"],x["replacement_delta"]))
    if not rescuers:
        return {
            "status":"ESCALATE",
            "reason":"NO_SINGLE_STEP_CONTRACT_RESTORATION_RESCUES_TERMINAL_STATE",
        }
    if len(rescuers)>1:
        return {
            "status":"AMBIGUOUS",
            "repairs":rescuers,
            "cause_action_id":None,
            "reason":"MULTIPLE_GENERATED_COUNTERFACTUAL_REPAIRS_RESCUE_TERMINAL_STATE",
        }
    repair=rescuers[0]
    return {
        "status":"IDENTIFIED",
        "cause_action_id":repair["action_id"],
        "repair":repair,
        "evidence_action_ids":[repair["action_id"]],
        "reason":"UNIQUE_GENERATED_COUNTERFACTUAL_REPAIR_RESCUES_TERMINAL_STATE",
    }
