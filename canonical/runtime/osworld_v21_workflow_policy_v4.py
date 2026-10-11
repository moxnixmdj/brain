"""Capability-first workflow coordinator V4.

V2 preserves V1's fail-closed ordered-clause semantics and upgrades only the
receipt-to-later-action bridge to bounded relational/aggregate dataflow V3.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

from canonical.runtime.osworld_v21_web_app_policy_overlay_v1 import decide as base_decide
from canonical.runtime.osworld_v21_receipt_dataflow_v3 import materialize_explicit_references
from canonical.runtime.osworld_v21_workflow_policy_v1 import split_explicit_subgoals

SCHEMA = "PROJECT_BRAIN_OSWORLD_V21_WORKFLOW_POLICY_V4"

_OBSERVE_VERBS = re.compile(r"\b(check|review|read|inspect|look up|lookup|find|identify|retrieve|list|show|see|examine)\b", re.I)
_MUTATE_VERBS = re.compile(
    r"\b(send|reply|update|change|edit|create|delete|remove|submit|post|like|add|"
    r"schedule|book|purchase|buy|pay|attach|upload|download|fill|set|write|replace|"
    r"install|uninstall|disable|enable|export|save|move|rename)\b",
    re.I,
)

def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _history(state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = state.get("history")
    return [row for row in raw if isinstance(row, Mapping)] if isinstance(raw, list) else []

def _receipt(row: Mapping[str, Any]) -> Mapping[str, Any] | None:
    r = row.get("policy_receipt")
    if isinstance(r, Mapping) and r.get("schema") == SCHEMA and isinstance(r.get("clause_index"), int):
        return r
    return None

def _current_index(state: Mapping[str, Any], workflow_sha: str, count: int) -> int:
    for row in reversed(_history(state)):
        r = _receipt(row)
        if r is None or r.get("workflow_sha256") != workflow_sha:
            continue
        i = r.get("clause_index")
        if isinstance(i, int) and not isinstance(i, bool) and 0 <= i < count:
            return i
    return 0

def _rows(state: Mapping[str, Any], workflow_sha: str, *, clause_index: int | None = None, before: int | None = None):
    out = []
    for row in _history(state):
        r = _receipt(row)
        if r is None or r.get("workflow_sha256") != workflow_sha:
            continue
        i = r.get("clause_index")
        if clause_index is not None and i != clause_index:
            continue
        if before is not None and (not isinstance(i, int) or i >= before):
            continue
        out.append(row)
    return out

def _observation_complete(instruction: str, rows: list[Mapping[str, Any]]) -> bool:
    if not _OBSERVE_VERBS.search(instruction) or _MUTATE_VERBS.search(instruction):
        return False
    for row in rows:
        for key in ("web_app_result", "browser_result", "app_result", "guest_result"):
            result = row.get(key)
            if isinstance(result, Mapping) and result.get("ok") is True:
                return True
    return False

def _done(out: Mapping[str, Any]) -> bool:
    a = out.get("actions")
    return (
        isinstance(a, list) and len(a) == 1 and isinstance(a[0], Mapping)
        and str(a[0].get("type") or "").strip().upper() == "DONE"
    )

def _wrap(out: Mapping[str, Any], *, workflow_sha: str, clauses: list[str], clause_index: int, dataflow=None):
    result = dict(out)
    base = result.get("_policy_receipt")
    receipt = {
        "schema": SCHEMA,
        "route": "EXPLICIT_ORDERED_SUBGOAL_COMPOSITION_WITH_RELATIONAL_DATAFLOW_V3",
        "workflow_sha256": workflow_sha,
        "clause_index": clause_index,
        "clause_count": len(clauses),
        "clause_sha256": _sha(clauses[clause_index]),
        "task_specific_policy_data": False,
        "external_model_dependency": False,
    }
    if isinstance(base, Mapping):
        receipt["base_policy_receipt"] = dict(base)
    if isinstance(dataflow, Mapping):
        receipt["dataflow"] = dict(dataflow)
    result["_policy_receipt"] = receipt
    return result

def decide(state: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(state, Mapping):
        raise ValueError("STATE_NOT_OBJECT")
    instruction = state.get("instruction")
    if not isinstance(instruction, str) or not instruction.strip():
        return base_decide(state)

    clauses = split_explicit_subgoals(instruction)
    if len(clauses) <= 1:
        return base_decide(state)

    workflow_sha = _sha("\n".join(clauses))
    index = _current_index(state, workflow_sha, len(clauses))

    for _ in range(len(clauses)):
        local_rows = _rows(state, workflow_sha, clause_index=index)
        if index < len(clauses) - 1 and _observation_complete(clauses[index], local_rows):
            index += 1
            continue

        prior = _rows(state, workflow_sha, before=index)
        flow = materialize_explicit_references(clauses[index], prior)
        if flow.get("pass") is not True:
            return _wrap(
                {"response": "cross-clause reference unresolved", "actions": [{"type": "WAIT"}]},
                workflow_sha=workflow_sha, clauses=clauses, clause_index=index, dataflow=flow,
            )

        local = dict(state)
        local["instruction"] = str(flow.get("text") or clauses[index])
        local["history"] = local_rows
        out = base_decide(local)
        if not isinstance(out, Mapping):
            raise ValueError("BASE_POLICY_OUTPUT_NOT_OBJECT")
        if _done(out) and index < len(clauses) - 1:
            index += 1
            continue
        return _wrap(out, workflow_sha=workflow_sha, clauses=clauses, clause_index=index, dataflow=flow)

    raise RuntimeError("WORKFLOW_ADVANCE_LOOP_EXHAUSTED")
