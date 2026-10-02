"""Brain candidate for dynamic task delegation and receipt-driven reassignment.

The candidate uses only candidate-visible task contracts, declared worker
capabilities, and the observed receipt. It never imports the proof evaluator or a
hidden oracle.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import m3_contract_task_decomposition as m3
from canonical.runtime import shared_decision_primitives as sdp


class DelegationCandidateError(ValueError):
    pass


def _effective_workers(task: Mapping[str, Any], receipt: Mapping[str, Any] | None):
    out = []
    for row in task.get("workers", []):
        wid = str(row.get("id") or "")
        caps = {str(x) for x in row.get("capabilities", [])}
        if receipt and receipt.get("kind") == "WORKER_UNAVAILABLE" and wid == str(receipt.get("entity_id")):
            continue
        if receipt and receipt.get("kind") == "WORKER_CAPABILITY_REMOVED" and wid == str(receipt.get("entity_id")):
            caps.discard(str(receipt.get("capability") or ""))
        if caps:
            out.append(sdp.Worker(wid, frozenset(caps)))
    return out


def _effective_steps(task: Mapping[str, Any], receipt: Mapping[str, Any] | None, completed: set[str]):
    disabled = set()
    if receipt and receipt.get("kind") == "STEP_UNAVAILABLE":
        disabled.add(str(receipt.get("entity_id") or ""))
    steps = []
    cap_by_id = {}
    produces_by_id = {}
    for row in task.get("steps", []):
        sid = str(row.get("id") or "")
        cap = str(row.get("capability") or "")
        produces = frozenset(str(x) for x in row.get("produces", []))
        cap_by_id[sid] = cap
        produces_by_id[sid] = produces
        if sid in completed:
            continue
        steps.append(m3.ContractStep(
            task_id=sid,
            requires=frozenset(str(x) for x in row.get("requires", [])),
            produces=produces,
            cost=float(row.get("cost", 0.0)),
            available=(row.get("available", True) is True and sid not in disabled),
            verified=True,
        ))
    return steps, cap_by_id, produces_by_id


def _plan(task: Mapping[str, Any], receipt: Mapping[str, Any] | None = None) -> dict[str, Any]:
    completed = set(str(x) for x in ((receipt or {}).get("completed_task_ids") or []))
    steps, cap_by_id, produces_by_id = _effective_steps(task, receipt, completed)

    initial = set(str(x) for x in task.get("initial_facts", []))
    for sid in completed:
        if sid not in produces_by_id:
            raise DelegationCandidateError("COMPLETED_TASK_UNKNOWN:" + sid)
        initial |= produces_by_id[sid]

    plan = m3.compile_task_plan(
        initial_facts=initial,
        required_outputs=task.get("required_outputs", []),
        steps=steps,
    )
    if plan.get("status") != "PASS":
        return plan

    task_ids = list(plan["task_ids"])
    deps = {str(k): list(v) for k, v in plan["dependencies"].items()}
    tasks = [
        sdp.Task(
            task_id=sid,
            deps=frozenset(deps[sid]),
            required_capabilities=frozenset([cap_by_id[sid]]),
        )
        for sid in task_ids
    ]
    workers = _effective_workers(task, receipt)

    done: set[str] = set()
    assignment: dict[str, str] = {}
    waves: list[list[str]] = []
    while done != set(task_ids):
        wave_assignment = sdp.assign_ready_tasks(tasks, workers, done)
        wave = sorted(wave_assignment)
        if not wave:
            raise DelegationCandidateError("NO_FEASIBLE_READY_ASSIGNMENT")
        waves.append(wave)
        assignment.update(wave_assignment)
        done.update(wave)

    return {
        "status": "PASS",
        "task_ids": task_ids,
        "dependencies": deps,
        "assignment": assignment,
        "waves": waves,
        "total_cost": plan["total_cost"],
    }


def solve_initial(public: Mapping[str, Any]) -> dict[str, Any]:
    task = public.get("task")
    if not isinstance(task, Mapping):
        raise DelegationCandidateError("TASK_MISSING")
    return _plan(task)


def solve_after_receipt(public: Mapping[str, Any], previous: Mapping[str, Any]) -> dict[str, Any]:
    task = public.get("task")
    receipt = public.get("receipt")
    if not isinstance(task, Mapping) or not isinstance(receipt, Mapping):
        raise DelegationCandidateError("TASK_OR_RECEIPT_MISSING")
    if previous.get("status") != "PASS":
        raise DelegationCandidateError("PRIOR_PLAN_NOT_PASS")
    out = _plan(task, receipt)
    if out.get("status") != "PASS":
        return out
    provenance = {
        "kind": str(receipt.get("kind") or ""),
        "entity_id": str(receipt.get("entity_id") or ""),
        "completed_task_ids": [str(x) for x in receipt.get("completed_task_ids", [])],
    }
    if receipt.get("capability") is not None:
        provenance["capability"] = str(receipt.get("capability"))
    out["receipt_id"] = str(receipt.get("receipt_id") or "")
    out["revision_provenance"] = provenance
    return out
