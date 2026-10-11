"""Capability-first ordered-subgoal coordinator for OSWorld 2.1.

This layer composes existing model-independent state/app/web policies across
explicitly ordered subgoals. It never branches on benchmark task IDs, consumes
reference trajectories, or invents latent subgoals from vague prose.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

from canonical.runtime.osworld_v21_web_app_policy_overlay_v1 import decide as base_decide
from canonical.runtime.osworld_v21_receipt_dataflow_v1 import materialize_explicit_references

SCHEMA = "PROJECT_BRAIN_OSWORLD_V21_WORKFLOW_POLICY_V1"
MAX_CLAUSES = 12


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _mask_quoted(text: str) -> str:
    out = list(text)
    quote: str | None = None
    pairs = {'"': '"', "'": "'", "“": "”"}
    closing: str | None = None
    escape = False
    for i, ch in enumerate(text):
        if escape:
            escape = False
            if quote is not None:
                out[i] = " "
            continue
        if ch == "\\" and quote is not None:
            out[i] = " "
            escape = True
            continue
        if quote is None:
            if ch in pairs:
                quote = ch
                closing = pairs[ch]
                out[i] = " "
        else:
            out[i] = " "
            if ch == closing:
                quote = None
                closing = None
    return "".join(out)


def _strip_marker(value: str) -> str:
    return re.sub(r"^\s*(?:[-*]\s+|\d+[.)]\s+)", "", value).strip()


def split_explicit_subgoals(instruction: str) -> list[str]:
    text = str(instruction or "").strip()
    if not text:
        return []

    # Convert explicit line-list markers to a semicolon-like boundary while
    # preserving ordinary wrapped prose as one clause.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    marked = [bool(re.match(r"^(?:[-*]\s+|\d+[.)]\s+)", line)) for line in lines]
    if len(lines) >= 2 and sum(marked) >= 2:
        text = "; ".join(_strip_marker(line) for line in lines)

    masked = _mask_quoted(text)
    pattern = re.compile(r";|\b(?:and\s+then|then)\b", re.I)
    spans = [m.span() for m in pattern.finditer(masked)]
    if not spans:
        return [text]

    parts: list[str] = []
    start = 0
    for a, b in spans:
        part = _strip_marker(text[start:a])
        if part:
            parts.append(part)
        start = b
    tail = _strip_marker(text[start:])
    if tail:
        parts.append(tail)

    if len(parts) <= 1:
        return [text]
    if len(parts) > MAX_CLAUSES:
        # Fail closed to the existing whole-goal policy instead of silently
        # truncating a long workflow.
        return [text]
    return parts


def _history(state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = state.get("history")
    if not isinstance(raw, list):
        return []
    return [row for row in raw if isinstance(row, Mapping)]


def _workflow_receipt(row: Mapping[str, Any]) -> Mapping[str, Any] | None:
    receipt = row.get("policy_receipt")
    if (
        isinstance(receipt, Mapping)
        and receipt.get("schema") == SCHEMA
        and isinstance(receipt.get("clause_index"), int)
    ):
        return receipt
    return None


def _current_index(state: Mapping[str, Any], workflow_sha: str, count: int) -> int:
    for row in reversed(_history(state)):
        receipt = _workflow_receipt(row)
        if receipt is None or receipt.get("workflow_sha256") != workflow_sha:
            continue
        index = receipt.get("clause_index")
        if isinstance(index, int) and not isinstance(index, bool) and 0 <= index < count:
            return index
    return 0


_OBSERVE_VERBS = re.compile(r"\b(check|review|read|inspect|look up|lookup|find|identify|retrieve|list|show|see|examine)\b", re.I)
_MUTATE_VERBS = re.compile(
    r"\b(send|reply|update|change|edit|create|delete|remove|submit|post|like|add|"
    r"schedule|book|purchase|buy|pay|attach|upload|download|fill|set|write|replace|"
    r"install|uninstall|disable|enable|export|save|move|rename)\b",
    re.I,
)


def _prior_clause_rows(
    state: Mapping[str, Any], *, workflow_sha: str, before_index: int
) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for row in _history(state):
        receipt = _workflow_receipt(row)
        if (
            receipt is not None
            and receipt.get("workflow_sha256") == workflow_sha
            and isinstance(receipt.get("clause_index"), int)
            and receipt.get("clause_index") < before_index
        ):
            rows.append(row)
    return rows


def _observation_only_clause_complete(
    instruction: str,
    rows: list[Mapping[str, Any]],
) -> bool:
    if not _OBSERVE_VERBS.search(instruction) or _MUTATE_VERBS.search(instruction):
        return False
    return any(
        isinstance(row.get("web_app_result"), Mapping)
        and row["web_app_result"].get("ok") is True
        for row in rows
    )


def _clause_history(
    state: Mapping[str, Any], *, workflow_sha: str, clause_index: int
) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for row in _history(state):
        receipt = _workflow_receipt(row)
        if (
            receipt is not None
            and receipt.get("workflow_sha256") == workflow_sha
            and receipt.get("clause_index") == clause_index
        ):
            rows.append(row)
    return rows


def _done(out: Mapping[str, Any]) -> bool:
    actions = out.get("actions")
    return (
        isinstance(actions, list)
        and len(actions) == 1
        and isinstance(actions[0], Mapping)
        and str(actions[0].get("type") or "").strip().upper() == "DONE"
    )


def _wrap(
    out: Mapping[str, Any],
    *,
    workflow_sha: str,
    clauses: list[str],
    clause_index: int,
    dataflow: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result = dict(out)
    base_receipt = result.get("_policy_receipt")
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "route": "EXPLICIT_ORDERED_SUBGOAL_COMPOSITION",
        "workflow_sha256": workflow_sha,
        "clause_index": clause_index,
        "clause_count": len(clauses),
        "clause_sha256": _sha(clauses[clause_index]),
        "task_specific_policy_data": False,
        "external_model_dependency": False,
    }
    if isinstance(base_receipt, Mapping):
        receipt["base_policy_receipt"] = dict(base_receipt)
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

    # A clause can return DONE only after its underlying state machine has seen
    # explicit completion evidence. For non-final clauses, consume that local
    # completion and immediately ask the next clause for its first sound action.
    for _ in range(len(clauses)):
        clause_rows = _clause_history(
            state, workflow_sha=workflow_sha, clause_index=index
        )
        if (
            index < len(clauses) - 1
            and _observation_only_clause_complete(clauses[index], clause_rows)
        ):
            index += 1
            continue

        prior_rows = _prior_clause_rows(
            state, workflow_sha=workflow_sha, before_index=index
        )
        dataflow = materialize_explicit_references(clauses[index], prior_rows)
        if dataflow.get("pass") is not True:
            return _wrap(
                {
                    "response": "cross-clause reference unresolved",
                    "actions": [{"type": "WAIT"}],
                },
                workflow_sha=workflow_sha,
                clauses=clauses,
                clause_index=index,
                dataflow=dataflow,
            )

        local = dict(state)
        local["instruction"] = str(dataflow.get("text") or clauses[index])
        local["history"] = clause_rows
        out = base_decide(local)
        if not isinstance(out, Mapping):
            raise ValueError("BASE_POLICY_OUTPUT_NOT_OBJECT")
        if _done(out) and index < len(clauses) - 1:
            index += 1
            continue
        return _wrap(
            out,
            workflow_sha=workflow_sha,
            clauses=clauses,
            clause_index=index,
            dataflow=dataflow,
        )

    raise RuntimeError("WORKFLOW_ADVANCE_LOOP_EXHAUSTED")
