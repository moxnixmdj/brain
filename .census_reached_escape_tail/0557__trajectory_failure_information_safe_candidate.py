"""Brain candidate for information-safe trajectory causal localization.

Consumes only the public normalized trajectory and explicit falsifiable repair
actions. It never imports the proof oracle or hidden rescue labels.
"""
from __future__ import annotations

from typing import Any, Mapping


def _terminal_after_repair(task:Mapping[str,Any], repair:Mapping[str,Any])->int:
    trajectory=task.get("trajectory")
    if not isinstance(trajectory,list) or not trajectory:
        raise ValueError("TRAJECTORY_INVALID")
    positions={}
    deltas=[]
    for i,row in enumerate(trajectory):
        aid=row.get("action_id")
        if not isinstance(aid,str) or aid in positions:
            raise ValueError("ACTION_ID_INVALID_OR_DUPLICATE")
        positions[aid]=i
        got=row.get("observed_delta")
        expected=row.get("contract_delta")
        if not isinstance(got,int) or isinstance(got,bool) or not isinstance(expected,int) or isinstance(expected,bool):
            raise ValueError("DELTA_INVALID")
        deltas.append(got)
    aid=repair.get("action_id")
    replacement=repair.get("replacement_delta")
    if aid not in positions or not isinstance(replacement,int) or isinstance(replacement,bool):
        raise ValueError("REPAIR_INVALID")
    deltas[positions[aid]]=replacement
    return int(task["initial_state"])+sum(deltas)


def solve(public_case:Mapping[str,Any])->dict[str,Any]:
    task=public_case.get("task")
    if not isinstance(task,Mapping):
        return {"status":"FAIL_CLOSED","reason":"TASK_INVALID"}
    repairs=task.get("repair_candidates")
    if not isinstance(repairs,list) or not repairs:
        return {"status":"FAIL_CLOSED","reason":"REPAIRS_INVALID"}
    target=task.get("terminal_target")
    if not isinstance(target,int) or isinstance(target,bool):
        return {"status":"FAIL_CLOSED","reason":"TARGET_INVALID"}

    rescuers=[]
    for repair in repairs:
        if not isinstance(repair,Mapping):
            return {"status":"FAIL_CLOSED","reason":"REPAIR_NOT_OBJECT"}
        try:
            if _terminal_after_repair(task,repair)==target:
                rescuers.append(repair)
        except Exception as exc:
            return {"status":"FAIL_CLOSED","reason":type(exc).__name__+":"+str(exc)}

    if not rescuers:
        return {"status":"ESCALATE","reason":"NO_FALSIFIABLE_REPAIR_RESCUES_TERMINAL_STATE"}

    if len(rescuers)>1:
        return {
            "status":"AMBIGUOUS",
            "repair_ids":sorted(str(x["repair_id"]) for x in rescuers),
            "cause_action_id":None,
            "reason":"MULTIPLE_COUNTERFACTUAL_RESCUES__UNIQUE_CAUSE_NONIDENTIFIABLE",
        }

    repair=rescuers[0]
    aid=str(repair["action_id"])
    return {
        "status":"IDENTIFIED",
        "cause_action_id":aid,
        "repair_id":str(repair["repair_id"]),
        "evidence_action_ids":[aid],
        "reason":"UNIQUE_COUNTERFACTUAL_TERMINAL_RESCUE",
    }
