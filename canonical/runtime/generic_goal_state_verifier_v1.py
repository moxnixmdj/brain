"""Independent generic goal-state verifier for Project Brain.

This verifier checks post-action observations against the compiled goal contract.
It is intentionally separate from argument binding and tool execution.

Current verified predicate families:
- observe: relevant state is actually observable;
- update: explicit field assignment is present in post-action state;
- create: a grounded created-object name exists in post-action state.

Delete/associate/notify remain fail-closed until a generic independent state
predicate can be derived for them.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from canonical.runtime.generic_goal_tool_effect_planner_v1 import compile_goal_contract
from canonical.runtime.generic_tool_argument_binder_v1 import (
    canonical_field,
    extract_grounding_facts,
    extract_records,
)

SCHEMA = "PROJECT_BRAIN_GENERIC_GOAL_STATE_VERIFIER_V1"
_CANONICAL_GROUPS = {"name","text","date","status","priority","project","workspace","section","task","tag","person","email","amount","id"}


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def _words(value: Any) -> set[str]:
    return {
        x.lower()
        for x in re.findall(r"[A-Za-z0-9_-]+", str(value or ""))
        if len(x) > 2
    }


def _record_text(record: Mapping[str, Any]) -> str:
    pieces: list[str] = []
    for key, value in record.items():
        if isinstance(value, (str, int, float, bool)):
            pieces.extend([str(key), str(value)])
    return " ".join(pieces)


def _record_relevant(record: Mapping[str, Any], resource_terms: Sequence[str]) -> bool:
    terms = set(str(x).lower() for x in resource_terms or [])
    if not terms:
        return True
    return bool(terms & _words(_record_text(record)))


def _assignment_from_clause(clause: str) -> tuple[str, str] | None:
    m = re.search(
        r"\b(?:set|change|update|mark)\s+(?:the\s+)?(.{1,80}?)\s+(?:to|as)\s+([^,.;]+)",
        clause,
        flags=re.I,
    )
    if not m:
        return None
    field_phrase = m.group(1).strip()
    expected = m.group(2).strip()
    group = canonical_field(field_phrase)
    if group == re.sub(r"[^a-z0-9]+", "_", field_phrase.lower()).strip("_"):
        for piece in reversed(re.findall(r"[A-Za-z0-9_]+", field_phrase)):
            candidate = canonical_field(piece)
            if candidate in _CANONICAL_GROUPS:
                group = candidate
                break
    return group, expected


def _field_values(record: Mapping[str, Any], group: str) -> list[Any]:
    out: list[Any] = []
    for key, value in record.items():
        if canonical_field(key) == group and isinstance(value, (str, int, float, bool)):
            out.append(value)
    return out


def _verify_observe(intent: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    matches = [
        r for r in records
        if _record_relevant(r, intent.get("resource_terms") or [])
    ]
    return {
        "verified": bool(matches),
        "reason": None if matches else "NO_RELEVANT_POST_ACTION_STATE_OBSERVED",
        "matching_record_count": len(matches),
    }


def _verify_update(intent: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    assignment = _assignment_from_clause(str(intent.get("clause") or ""))
    if assignment is None:
        return {
            "verified": False,
            "reason": "EXPLICIT_UPDATE_PREDICATE_NOT_DERIVABLE",
        }
    field_group, expected = assignment
    expected_norm = _norm(expected)
    candidates = [
        r for r in records
        if _record_relevant(r, intent.get("resource_terms") or [])
    ]
    for record in candidates:
        for value in _field_values(record, field_group):
            actual = _norm(value)
            if actual == expected_norm:
                return {
                    "verified": True,
                    "reason": None,
                    "field_group": field_group,
                    "expected": expected,
                    "actual": value,
                }
    return {
        "verified": False,
        "reason": "POST_ACTION_FIELD_VALUE_NOT_OBSERVED",
        "field_group": field_group,
        "expected": expected,
        "candidate_count": len(candidates),
    }


def _verify_create(
    intent: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    grounding_facts: Mapping[str, list[str]],
) -> dict[str, Any]:
    names = [x for x in grounding_facts.get("name", []) if str(x).strip()]
    if not names:
        return {
            "verified": False,
            "reason": "CREATED_OBJECT_NAME_NOT_GROUNDED",
        }
    expected = _norm(names[0])
    for record in records:
        for value in _field_values(record, "name"):
            actual = _norm(value)
            if actual == expected:
                return {
                    "verified": True,
                    "reason": None,
                    "expected_name": names[0],
                    "actual_name": value,
                }
    return {
        "verified": False,
        "reason": "CREATED_OBJECT_NOT_OBSERVED",
        "expected_name": names[0],
    }


def verify_goal_state(
    *,
    goal: str,
    context_observations: Sequence[Any],
    verification_observations: Sequence[Any],
) -> dict[str, Any]:
    contract = compile_goal_contract(goal)
    if contract.get("status") not in {"COMPILED", "NO_POSITIVE_ACTION_REQUIRED"}:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "UNRESOLVED",
            "reason": str(contract.get("reason") or "GOAL_CONTRACT_UNRESOLVED"),
            "intent_results": [],
        }

    positive = [
        x for x in contract.get("intents") or []
        if not x.get("forbidden")
    ]
    if not positive:
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "VERIFIED_NO_POSITIVE_ACTION_REQUIRED",
            "intent_results": [],
        }

    records = extract_records(verification_observations)
    facts = extract_grounding_facts(goal, context_observations)
    results: list[dict[str, Any]] = []

    for intent in positive:
        action = str(intent.get("action_class") or "")
        if action == "observe":
            detail = _verify_observe(intent, records)
        elif action == "update":
            detail = _verify_update(intent, records)
        elif action == "create":
            detail = _verify_create(intent, records, facts)
        else:
            detail = {
                "verified": False,
                "reason": "GENERIC_VERIFIER_UNSUPPORTED_ACTION_CLASS:" + action,
            }
        results.append({
            "intent_id": intent.get("id"),
            "action_class": action,
            **detail,
        })

    ok = all(x.get("verified") is True for x in results)
    return {
        "schema": SCHEMA,
        "pass": ok,
        "status": "VERIFIED" if ok else "UNRESOLVED",
        "reason": None if ok else "ONE_OR_MORE_GOAL_PREDICATES_UNVERIFIED",
        "intent_results": results,
        "verification_record_count": len(records),
    }
