"""Adaptive replan and reassignment from explicit state updates.

Composes existing exact planning and worker-assignment primitives. No semantic
inference is performed here: invalidated facts, observations, step contracts, and
worker capabilities must already be explicit.
"""
from __future__ import annotations
from dataclasses import replace
from typing import Iterable, Mapping, Sequence
from canonical.runtime.m3_contract_task_decomposition import ContractStep, compile_task_plan
from canonical.runtime.shared_decision_primitives import Task, Worker, assign_ready_tasks

def adaptive_replan(
    *,
    current_facts: Iterable[str],
    invalidated_facts: Iterable[str],
    observed_facts: Iterable[str],
    required_outputs: Iterable[str],
    steps: Sequence[ContractStep],
    unavailable_step_ids: Iterable[str] = (),
    workers: Sequence[Worker] | None = None,
    task_capabilities: Mapping[str, frozenset[str]] | None = None,
) -> dict:
    try:
        current=set(current_facts); invalidated=set(invalidated_facts)
        observed=set(observed_facts); unavailable=set(unavailable_step_ids)
        required=set(required_outputs)
    except Exception:
        return {"status":"FAIL_CLOSED","reason":"STATE_INPUT_NOT_ITERABLE","terminal_authority":False}
    groups=(current,invalidated,observed,unavailable,required)
    if any(any(not isinstance(x,str) or not x.strip() for x in group) for group in groups):
        return {"status":"FAIL_CLOSED","reason":"IDENTITIES_INVALID","terminal_authority":False}

    updated=(current-invalidated)|observed
    patched=[]
    for step in steps:
        if not isinstance(step,ContractStep):
            return {"status":"FAIL_CLOSED","reason":"STEP_TYPE_INVALID","terminal_authority":False}
        patched.append(replace(step,available=step.available and step.task_id not in unavailable))

    plan=compile_task_plan(initial_facts=updated,required_outputs=required,steps=patched)
    if plan.get("status")!="PASS":
        return {
            "status":"ESCALATE" if plan.get("status")=="ESCALATE" else "FAIL_CLOSED",
            "reason":"REPLAN_FAILED","planner":plan,"updated_facts":sorted(updated),
            "terminal_authority":False,
        }

    result={
        "status":"PASS","updated_facts":sorted(updated),"task_ids":plan["task_ids"],
        "dependencies":plan["dependencies"],"total_cost":plan["total_cost"],
        "ready_assignments":{},
        "reason":"EXPLICIT_STATE_UPDATE__EXACT_REPLAN__EXPLICIT_CAPABILITY_REASSIGNMENT",
        "semantic_authority":False,"terminal_authority":False,
    }
    if workers is None:
        return result
    if task_capabilities is None:
        return {"status":"FAIL_CLOSED","reason":"TASK_CAPABILITIES_REQUIRED_WITH_WORKERS","terminal_authority":False}

    tasks=[]
    for tid in plan["task_ids"]:
        req=task_capabilities.get(tid)
        if not isinstance(req,frozenset) or any(not isinstance(x,str) or not x.strip() for x in req):
            return {"status":"FAIL_CLOSED","reason":f"TASK_CAPABILITY_METADATA_INVALID:{tid}","terminal_authority":False}
        tasks.append(Task(tid,frozenset(plan["dependencies"].get(tid,[])),req))
    assignments=assign_ready_tasks(tasks,workers,completed=())
    ready={task.task_id for task in tasks if not task.deps}
    if ready and not assignments:
        return {
            "status":"ESCALATE","reason":"NO_CAPABLE_WORKER_FOR_READY_REPLAN_TASK",
            "task_ids":plan["task_ids"],"dependencies":plan["dependencies"],
            "terminal_authority":False,
        }
    result["ready_assignments"]=assignments
    return result
