"""Generic forbidden-action guard and execution-trace verifier.

This module is benchmark-agnostic. It prevents a planned mutation from being
executed when it could violate a forbidden intent, and later verifies
non-execution from a complete mutation trace.

The guard is deliberately conservative: when two same-class intents may target
the same resource and cannot be disambiguated by strong explicit anchors, the
mutation is blocked rather than guessed safe.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.generic_tool_argument_binder_v1 import extract_grounding_facts

SCHEMA = "PROJECT_BRAIN_GENERIC_GOAL_CONSTRAINT_GUARD_V1"

_ANCHOR_GROUPS = (
    "email",
    "id_literal",
    "project_name",
    "workspace_name",
    "section_name",
    "task_name",
    "tag_name",
)


def _anchor_sets(intent: Mapping[str, Any]) -> dict[str, set[str]]:
    clause = str(intent.get("clause") or "")
    facts = extract_grounding_facts(clause, [])
    out: dict[str, set[str]] = {}
    for group in _ANCHOR_GROUPS:
        values = {
            str(x).strip().lower()
            for x in (facts.get(group) or [])
            if str(x).strip()
        }
        if values:
            out[group] = values
    return out


def intents_may_conflict(
    positive_intent: Mapping[str, Any],
    forbidden_intent: Mapping[str, Any],
) -> bool:
    """Return True when executing the positive intent could violate forbidden."""
    if bool(positive_intent.get("forbidden")):
        raise ValueError("POSITIVE_INTENT_REQUIRED")
    if not bool(forbidden_intent.get("forbidden")):
        raise ValueError("FORBIDDEN_INTENT_REQUIRED")

    pa = str(positive_intent.get("action_class") or "")
    fa = str(forbidden_intent.get("action_class") or "")
    if not pa or pa != fa:
        return False

    pr = {str(x).lower() for x in (positive_intent.get("resource_terms") or [])}
    fr = {str(x).lower() for x in (forbidden_intent.get("resource_terms") or [])}
    if pr and fr and not (pr & fr):
        return False

    panchors = _anchor_sets(positive_intent)
    fanchors = _anchor_sets(forbidden_intent)
    for group in sorted(set(panchors) & set(fanchors)):
        if panchors[group] and fanchors[group] and panchors[group].isdisjoint(fanchors[group]):
            return False

    # Same action class + overlapping/unknown resource identity remains unsafe.
    return True


def mutation_step_guard(
    *,
    step: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Adjudicate one planned mutation step against forbidden intents."""
    if str(step.get("role") or "") != "mutation":
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "NOT_A_MUTATION",
            "conflicts": [],
        }

    intents = list(contract.get("intents") or [])
    by_id = {str(x.get("id") or ""): x for x in intents}
    positive = by_id.get(str(step.get("intent_id") or ""))
    if not isinstance(positive, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "UNRESOLVED",
            "reason": "MUTATION_INTENT_NOT_FOUND_IN_CONTRACT",
            "conflicts": [],
        }

    forbidden = [x for x in intents if bool(x.get("forbidden"))]
    conflicts = [
        str(x.get("id") or "")
        for x in forbidden
        if intents_may_conflict(positive, x)
    ]
    return {
        "schema": SCHEMA,
        "pass": not conflicts,
        "status": "SAFE" if not conflicts else "BLOCKED",
        "positive_intent_id": positive.get("id"),
        "conflicts": conflicts,
        **({} if not conflicts else {
            "reason": "POTENTIAL_FORBIDDEN_ACTION_CONFLICT"
        }),
    }


def verify_forbidden_execution_trace(
    *,
    contract: Mapping[str, Any],
    execution_trace: Sequence[Mapping[str, Any]],
    trace_complete: bool,
) -> dict[str, Any]:
    """Verify forbidden intents using a complete record of executed mutations."""
    forbidden = [
        x for x in (contract.get("intents") or [])
        if bool(x.get("forbidden"))
    ]
    if not forbidden:
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "NO_FORBIDDEN_INTENTS",
            "constraint_results": [],
        }
    if not trace_complete:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "UNRESOLVED",
            "reason": "EXECUTION_TRACE_NOT_COMPLETE",
            "constraint_results": [
                {
                    "intent_id": x.get("id"),
                    "action_class": x.get("action_class"),
                    "verified": False,
                    "reason": "EXECUTION_TRACE_NOT_COMPLETE",
                }
                for x in forbidden
            ],
        }

    intents = list(contract.get("intents") or [])
    by_id = {str(x.get("id") or ""): x for x in intents}
    executed_positive: list[Mapping[str, Any]] = []
    for row in execution_trace:
        intent = by_id.get(str(row.get("intent_id") or ""))
        if isinstance(intent, Mapping) and not bool(intent.get("forbidden")):
            executed_positive.append(intent)

    results: list[dict[str, Any]] = []
    for constraint in forbidden:
        conflicts = [
            str(x.get("id") or "")
            for x in executed_positive
            if intents_may_conflict(x, constraint)
        ]
        verified = not conflicts
        results.append({
            "intent_id": constraint.get("id"),
            "action_class": constraint.get("action_class"),
            "verified": verified,
            "reason": None if verified else "CONFLICTING_MUTATION_EXECUTED",
            "conflicting_positive_intent_ids": conflicts,
        })

    return {
        "schema": SCHEMA,
        "pass": all(x["verified"] for x in results),
        "status": "VERIFIED" if all(x["verified"] for x in results) else "VIOLATED",
        "constraint_results": results,
    }
