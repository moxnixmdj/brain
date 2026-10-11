"""Fail-closed grounding of derived AutomationBench communication content.

This module resolves only derivations that are explicitly requested by the task
and uniquely supported by already-observed structured state. It does not call a
model, inspect rubric assertions, or invent missing values.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_AUTOMATIONBENCH_COMMUNICATION_GROUNDER_V1"


def _s(value: Any) -> str:
    return str(value or "").strip()


def _records(values: Sequence[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            row = dict(value)
            if any(
                str(k).lower() in {
                    "id", "gid", "name", "title", "subject", "body", "body_plain",
                    "text", "due_on", "duedate", "due_date",
                }
                for k in row
            ):
                out.append(row)
            for child in row.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for value in values:
        walk(value)
    return out


def _ci_get(row: Mapping[str, Any], *names: str) -> Any:
    lookup = {str(k).lower(): v for k, v in row.items()}
    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]
    return None


def _source_task_names(records: Sequence[Mapping[str, Any]]) -> list[str]:
    out: list[str] = []
    for row in records:
        text = " ".join(
            _s(row.get(k))
            for k in ("body", "body_plain", "text", "description", "subject", "title")
        )
        match = re.search(r"(?:create\s+task|task)\s*:\s*([^\n.]+)", text, re.I)
        if match:
            value = match.group(1).strip()
            if value and value not in out:
                out.append(value)
    return out


def resolve_communication(
    communication: Mapping[str, Any],
    *,
    prompt: str,
    observations: Sequence[Any],
) -> dict[str, Any]:
    """Return a communication obligation with derived content when provable."""
    if not isinstance(communication, Mapping):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "grounding_complete": False,
            "reason": "COMMUNICATION_NOT_OBJECT",
        }

    result = dict(communication)
    if result.get("grounding_complete") is True:
        result.update({
            "schema": SCHEMA,
            "status": "PASS__ALREADY_GROUNDED",
            "provenance_bound": True,
            "provenance": ["TASK_PROMPT_LITERAL"],
        })
        return result

    clause = _s(result.get("source_clause"))
    low = clause.lower()
    records = _records(observations)

    requests_task_name = bool(
        re.search(r"\btask\s+name\b", low)
        or re.search(r"\bname\s+of\s+the\s+task\b", low)
    )
    requests_due = bool(
        re.search(r"\bdue\s+date\b", low)
        or re.search(r"\bdue_on\b", low)
    )

    refers_to_created_task = bool(
        re.search(r"\bonce\s+it(?:'s|\s+is)\s+created\b", low)
        or re.search(r"\bwhen\s+it(?:'s|\s+is)\s+created\b", low)
        or re.search(r"\bafter\s+(?:the\s+)?task\s+is\s+created\b", low)
    )

    if (requests_task_name and requests_due) or refers_to_created_task:
        target_names = _source_task_names(records)
        candidates: list[dict[str, Any]] = []
        for row in records:
            name = _s(_ci_get(row, "name", "title"))
            due = _s(_ci_get(row, "due_on", "dueDate", "due_date"))
            gid = _s(_ci_get(row, "gid", "id", "Id"))
            if not name or not due or not gid:
                continue
            if target_names and not any(
                name.lower() == target.lower() for target in target_names
            ):
                continue
            candidates.append({"gid": gid, "name": name, "due": due})

        # Require a unique semantic record. Duplicate envelopes of the same
        # task collapse by (gid, name, due); distinct tasks remain ambiguous.
        unique = {
            (row["gid"], row["name"], row["due"]): row
            for row in candidates
        }
        if len(unique) == 1:
            task = next(iter(unique.values()))
            result.update({
                "schema": SCHEMA,
                "status": (
                    "PASS__DERIVED_CREATED_TASK_NOTIFICATION"
                    if refers_to_created_task
                    else "PASS__DERIVED_FROM_OBSERVED_TASK"
                ),
                "content_literal": f"{task['name']}\nDue: {task['due']}",
                "content_has_placeholder": False,
                "grounding_complete": True,
                "missing": [],
                "provenance_bound": True,
                "provenance": [
                    f"TASK_GID:{task['gid']}",
                    f"TASK_NAME:{task['name']}",
                    f"TASK_DUE:{task['due']}",
                ],
            })
            return result

        result.update({
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "grounding_complete": False,
            "reason": (
                "TASK_RECORD_AMBIGUOUS"
                if len(unique) > 1
                else "TASK_RECORD_NOT_GROUNDED"
            ),
        })
        return result

    result.update({
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "grounding_complete": False,
        "reason": "DERIVATION_PATTERN_UNSUPPORTED",
    })
    return result
