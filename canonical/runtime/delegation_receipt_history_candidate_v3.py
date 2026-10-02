"""Persistent live-receipt delegation candidate V3.

Repairs a scope gap in V2: solve_after_receipt() previously recomputed from the
base task plus only the newest receipt, so a later receipt could resurrect a
worker/step/capability/resource state invalidated by an earlier receipt.

V3 preserves V2's exact finite-graph planner/scheduler and accumulates the
declared live receipt history monotonically. It does not grant terminal,
acceptance, capability, family, execution, or promotion authority.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from canonical.runtime import delegation_whole_scope_candidate_v2 as v2

ALLOWED_RECEIPT_KINDS = {
    "STEP_UNAVAILABLE",
    "WORKER_UNAVAILABLE",
    "WORKER_CAPABILITY_REMOVED",
    "RESOURCE_CAPACITY_CHANGED",
}


class DelegationReceiptHistoryError(ValueError):
    pass


def _strings(value: Any, name: str) -> list[str]:
    vals = list(value or [])
    if any(not isinstance(x, str) or not x for x in vals):
        raise DelegationReceiptHistoryError(name + "_INVALID")
    return vals


def _normalize_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    kind = receipt.get("kind")
    if kind not in ALLOWED_RECEIPT_KINDS:
        raise DelegationReceiptHistoryError("RECEIPT_KIND_UNSUPPORTED:" + str(kind))
    receipt_id = receipt.get("receipt_id")
    entity_id = receipt.get("entity_id")
    if not isinstance(receipt_id, str) or not receipt_id:
        raise DelegationReceiptHistoryError("RECEIPT_ID_INVALID")
    if not isinstance(entity_id, str) or not entity_id:
        raise DelegationReceiptHistoryError("RECEIPT_ENTITY_INVALID")

    out: dict[str, Any] = {
        "receipt_id": receipt_id,
        "kind": kind,
        "entity_id": entity_id,
        "completed_task_ids": _strings(receipt.get("completed_task_ids"), "COMPLETED_TASK_IDS"),
    }
    if kind == "WORKER_CAPABILITY_REMOVED":
        capability = receipt.get("capability")
        if not isinstance(capability, str) or not capability:
            raise DelegationReceiptHistoryError("RECEIPT_CAPABILITY_INVALID")
        out["capability"] = capability
    if kind == "RESOURCE_CAPACITY_CHANGED":
        capacity = receipt.get("capacity")
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
            raise DelegationReceiptHistoryError("RECEIPT_RESOURCE_CAPACITY_INVALID")
        out["capacity"] = capacity
    return out


def _history_from_previous(previous: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = previous.get("receipt_history", [])
    if not isinstance(raw, list):
        raise DelegationReceiptHistoryError("PREVIOUS_RECEIPT_HISTORY_INVALID")
    history = []
    seen = set()
    for item in raw:
        if not isinstance(item, Mapping):
            raise DelegationReceiptHistoryError("PREVIOUS_RECEIPT_HISTORY_ITEM_INVALID")
        row = _normalize_receipt(item)
        rid = row["receipt_id"]
        if rid in seen:
            raise DelegationReceiptHistoryError("DUPLICATE_RECEIPT_ID:" + rid)
        seen.add(rid)
        history.append(row)
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


def _apply_history(task: Mapping[str, Any], history: list[Mapping[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    """Materialize the cumulative declared state induced by all live receipts."""
    out = deepcopy(dict(task))
    steps = out.get("steps")
    workers = out.get("workers")
    if not isinstance(steps, list) or not isinstance(workers, list):
        raise DelegationReceiptHistoryError("TASK_STEPS_OR_WORKERS_INVALID")

    step_by_id = {
        row.get("id"): row
        for row in steps
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    worker_by_id = {
        row.get("id"): row
        for row in workers
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    resource_caps = dict(out.get("resource_capacities") or {})

    for receipt in history:
        kind = receipt["kind"]
        entity = receipt["entity_id"]
        if kind == "STEP_UNAVAILABLE":
            row = step_by_id.get(entity)
            if row is None:
                raise DelegationReceiptHistoryError("RECEIPT_STEP_UNKNOWN:" + entity)
            row["available"] = False
        elif kind == "WORKER_UNAVAILABLE":
            if entity not in worker_by_id:
                raise DelegationReceiptHistoryError("RECEIPT_WORKER_UNKNOWN:" + entity)
            out["workers"] = [
                row for row in out["workers"]
                if not (isinstance(row, Mapping) and row.get("id") == entity)
            ]
            worker_by_id.pop(entity, None)
        elif kind == "WORKER_CAPABILITY_REMOVED":
            row = worker_by_id.get(entity)
            if row is None:
                raise DelegationReceiptHistoryError("RECEIPT_WORKER_UNKNOWN:" + entity)
            capability = receipt["capability"]
            row["capabilities"] = [
                cap for cap in _strings(row.get("capabilities"), "WORKER_CAPABILITIES")
                if cap != capability
            ]
        elif kind == "RESOURCE_CAPACITY_CHANGED":
            resource_caps[entity] = receipt["capacity"]

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
    out["receipt_history_semantics"] = "CUMULATIVE_MONOTONIC_DECLARED_STATE"
    return out


def solve_after_receipt(public: Mapping[str, Any], previous: Mapping[str, Any]) -> dict[str, Any]:
    task = public.get("task")
    receipt = public.get("receipt")
    if not isinstance(task, Mapping) or not isinstance(receipt, Mapping):
        raise DelegationReceiptHistoryError("TASK_OR_RECEIPT_MISSING")
    if previous.get("status") != "PASS":
        raise DelegationReceiptHistoryError("PRIOR_PLAN_NOT_PASS")

    history = _history_from_previous(previous)
    current = _normalize_receipt(receipt)
    if current["receipt_id"] in {x["receipt_id"] for x in history}:
        raise DelegationReceiptHistoryError("DUPLICATE_RECEIPT_ID:" + current["receipt_id"])
    history.append(current)

    effective_task, completed = _apply_history(task, history)
    synthetic = {"completed_task_ids": completed}
    out = v2._solve(effective_task, synthetic)
    out["receipt_id"] = current["receipt_id"]
    out["revision_provenance"] = _current_provenance(current)
    out["receipt_history"] = history
    out["receipt_history_ids"] = [x["receipt_id"] for x in history]
    out["receipt_history_semantics"] = "CUMULATIVE_MONOTONIC_DECLARED_STATE"
    out["terminal_authority"] = False
    return out
