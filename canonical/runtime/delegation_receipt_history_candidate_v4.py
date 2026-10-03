"""Total cumulative live-receipt delegation carrier V4.

V4 preserves the exact V2 finite planner/scheduler while making supported
receipt-history semantics explicit and total over declared entities. Repeated
monotone disable/removal events are idempotent instead of being misclassified
as unknown after an earlier receipt removed the entity from effective state.

This module grants no terminal, acceptance, capability, family, execution, or
promotion authority.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any, Mapping

from canonical.runtime import delegation_whole_scope_candidate_v2 as v2

SEMANTICS = "CUMULATIVE_TOTAL_SUPPORTED_HISTORY_V4"
ALLOWED_RECEIPT_KINDS = {
    "STEP_UNAVAILABLE",
    "WORKER_UNAVAILABLE",
    "WORKER_CAPABILITY_REMOVED",
    "RESOURCE_CAPACITY_CHANGED",
}


class DelegationReceiptHistoryV4Error(ValueError):
    pass


def _strings(value: Any, name: str) -> list[str]:
    vals = list(value or [])
    if any(not isinstance(x, str) or not x for x in vals):
        raise DelegationReceiptHistoryV4Error(name + "_INVALID")
    return vals


def _normalize_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    kind = receipt.get("kind")
    if kind not in ALLOWED_RECEIPT_KINDS:
        raise DelegationReceiptHistoryV4Error("RECEIPT_KIND_UNSUPPORTED:" + str(kind))
    rid = receipt.get("receipt_id")
    entity = receipt.get("entity_id")
    if not isinstance(rid, str) or not rid:
        raise DelegationReceiptHistoryV4Error("RECEIPT_ID_INVALID")
    if not isinstance(entity, str) or not entity:
        raise DelegationReceiptHistoryV4Error("RECEIPT_ENTITY_INVALID")

    row: dict[str, Any] = {
        "receipt_id": rid,
        "kind": kind,
        "entity_id": entity,
        "completed_task_ids": _strings(
            receipt.get("completed_task_ids"), "COMPLETED_TASK_IDS"
        ),
    }
    if kind == "WORKER_CAPABILITY_REMOVED":
        capability = receipt.get("capability")
        if not isinstance(capability, str) or not capability:
            raise DelegationReceiptHistoryV4Error("RECEIPT_CAPABILITY_INVALID")
        row["capability"] = capability
    if kind == "RESOURCE_CAPACITY_CHANGED":
        capacity = receipt.get("capacity")
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
            raise DelegationReceiptHistoryV4Error("RECEIPT_RESOURCE_CAPACITY_INVALID")
        row["capacity"] = capacity
    return row


def _history_from_previous(previous: Mapping[str, Any]) -> list[dict[str, Any]]:
    if previous.get("receipt_history_semantics") != SEMANTICS:
        raise DelegationReceiptHistoryV4Error("PREVIOUS_HISTORY_SEMANTICS_MISMATCH")
    raw = previous.get("receipt_history")
    ids = previous.get("receipt_history_ids")
    if not isinstance(raw, list) or not isinstance(ids, list):
        raise DelegationReceiptHistoryV4Error("PREVIOUS_RECEIPT_HISTORY_INVALID")

    history: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, Mapping):
            raise DelegationReceiptHistoryV4Error(
                "PREVIOUS_RECEIPT_HISTORY_ITEM_INVALID"
            )
        row = _normalize_receipt(item)
        rid = row["receipt_id"]
        if rid in seen:
            raise DelegationReceiptHistoryV4Error("DUPLICATE_RECEIPT_ID:" + rid)
        seen.add(rid)
        history.append(row)
    expected_ids = [x["receipt_id"] for x in history]
    if ids != expected_ids:
        raise DelegationReceiptHistoryV4Error("PREVIOUS_RECEIPT_HISTORY_IDS_MISMATCH")
    return history


def _stable_completed(history: list[Mapping[str, Any]]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for receipt in history:
        for sid in receipt.get("completed_task_ids", []):
            if sid not in seen:
                seen.add(sid)
                out.append(str(sid))
    return out


def _base_indexes(task: Mapping[str, Any]):
    steps = task.get("steps")
    workers = task.get("workers")
    if not isinstance(steps, list) or not isinstance(workers, list):
        raise DelegationReceiptHistoryV4Error("TASK_STEPS_OR_WORKERS_INVALID")

    step_by_id: dict[str, Mapping[str, Any]] = {}
    for row in steps:
        if not isinstance(row, Mapping):
            raise DelegationReceiptHistoryV4Error("TASK_STEP_NOT_OBJECT")
        sid = row.get("id")
        if not isinstance(sid, str) or not sid or sid in step_by_id:
            raise DelegationReceiptHistoryV4Error(
                "TASK_STEP_ID_INVALID_OR_DUPLICATE"
            )
        step_by_id[sid] = row

    worker_by_id: dict[str, Mapping[str, Any]] = {}
    for row in workers:
        if not isinstance(row, Mapping):
            raise DelegationReceiptHistoryV4Error("TASK_WORKER_NOT_OBJECT")
        wid = row.get("id")
        if not isinstance(wid, str) or not wid or wid in worker_by_id:
            raise DelegationReceiptHistoryV4Error(
                "TASK_WORKER_ID_INVALID_OR_DUPLICATE"
            )
        worker_by_id[wid] = row

    known_resources = set(str(k) for k in dict(task.get("resource_capacities") or {}))
    for row in steps:
        for resource in _strings(row.get("writes"), "STEP_WRITES"):
            known_resources.add(resource)
    return step_by_id, worker_by_id, known_resources


def _apply_history(
    task: Mapping[str, Any], history: list[Mapping[str, Any]]
) -> tuple[dict[str, Any], list[str]]:
    """Replay the full finite history from immutable base state.

    Disable/removal effects are set-union accumulators, hence idempotent and
    persistent. Resource capacity changes are ordered last-write-wins state
    updates. No supported earlier effect can be resurrected by a later receipt.
    """
    out = deepcopy(dict(task))
    step_by_id, worker_by_id, known_resources = _base_indexes(task)

    disabled_steps: set[str] = set()
    unavailable_workers: set[str] = set()
    removed_capabilities: dict[str, set[str]] = defaultdict(set)
    resource_caps = dict(out.get("resource_capacities") or {})

    for raw in history:
        receipt = _normalize_receipt(raw)
        kind = receipt["kind"]
        entity = receipt["entity_id"]
        if kind == "STEP_UNAVAILABLE":
            if entity not in step_by_id:
                raise DelegationReceiptHistoryV4Error(
                    "RECEIPT_STEP_UNKNOWN:" + entity
                )
            disabled_steps.add(entity)
        elif kind == "WORKER_UNAVAILABLE":
            if entity not in worker_by_id:
                raise DelegationReceiptHistoryV4Error(
                    "RECEIPT_WORKER_UNKNOWN:" + entity
                )
            unavailable_workers.add(entity)
        elif kind == "WORKER_CAPABILITY_REMOVED":
            if entity not in worker_by_id:
                raise DelegationReceiptHistoryV4Error(
                    "RECEIPT_WORKER_UNKNOWN:" + entity
                )
            capability = receipt["capability"]
            base_caps = set(_strings(
                worker_by_id[entity].get("capabilities"), "WORKER_CAPABILITIES"
            ))
            if capability not in base_caps:
                raise DelegationReceiptHistoryV4Error(
                    "RECEIPT_CAPABILITY_UNKNOWN:" + entity + ":" + capability
                )
            removed_capabilities[entity].add(capability)
        elif kind == "RESOURCE_CAPACITY_CHANGED":
            if entity not in known_resources:
                raise DelegationReceiptHistoryV4Error(
                    "RECEIPT_RESOURCE_UNKNOWN:" + entity
                )
            resource_caps[entity] = receipt["capacity"]

    materialized_steps: list[dict[str, Any]] = []
    for raw in out["steps"]:
        row = deepcopy(dict(raw))
        sid = row["id"]
        row["available"] = (
            row.get("available", True) is True and sid not in disabled_steps
        )
        materialized_steps.append(row)
    out["steps"] = materialized_steps

    materialized_workers: list[dict[str, Any]] = []
    for raw in out["workers"]:
        row = deepcopy(dict(raw))
        wid = row["id"]
        if wid in unavailable_workers:
            continue
        caps = [
            cap
            for cap in _strings(row.get("capabilities"), "WORKER_CAPABILITIES")
            if cap not in removed_capabilities.get(wid, set())
        ]
        row["capabilities"] = caps
        materialized_workers.append(row)
    out["workers"] = materialized_workers
    out["resource_capacities"] = resource_caps
    return out, _stable_completed(history)


def _current_provenance(receipt: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "kind": receipt["kind"],
        "entity_id": receipt["entity_id"],
        "completed_task_ids": list(receipt.get("completed_task_ids", [])),
    }
    if "capability" in receipt:
        out["capability"] = receipt["capability"]
    if "capacity" in receipt:
        out["capacity"] = receipt["capacity"]
    return out


def solve_initial(public: Mapping[str, Any]) -> dict[str, Any]:
    out = v2.solve_initial(public)
    out["receipt_history"] = []
    out["receipt_history_ids"] = []
    out["receipt_history_semantics"] = SEMANTICS
    return out


def solve_after_receipt(
    public: Mapping[str, Any], previous: Mapping[str, Any]
) -> dict[str, Any]:
    task = public.get("task")
    receipt = public.get("receipt")
    if not isinstance(task, Mapping) or not isinstance(receipt, Mapping):
        raise DelegationReceiptHistoryV4Error("TASK_OR_RECEIPT_MISSING")
    if previous.get("status") != "PASS":
        raise DelegationReceiptHistoryV4Error("PRIOR_PLAN_NOT_PASS")

    history = _history_from_previous(previous)
    current = _normalize_receipt(receipt)
    if current["receipt_id"] in {x["receipt_id"] for x in history}:
        raise DelegationReceiptHistoryV4Error(
            "DUPLICATE_RECEIPT_ID:" + current["receipt_id"]
        )
    history.append(current)

    effective_task, completed = _apply_history(task, history)
    out = v2._solve(effective_task, {"completed_task_ids": completed})
    out["receipt_id"] = current["receipt_id"]
    out["revision_provenance"] = _current_provenance(current)
    out["receipt_history"] = history
    out["receipt_history_ids"] = [x["receipt_id"] for x in history]
    out["receipt_history_semantics"] = SEMANTICS
    out["terminal_authority"] = False
    return out
