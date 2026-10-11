"""Identity-bound generic post-state verifier for Project Brain.

V2 verifies both positive goals and negative constraints. It is independent from
planning, argument binding, and execution.

Supported positive predicate families:
- observe
- update
- create
- delete (strong 404/not-found evidence only)
- associate
- notify

Forbidden actions are constraints, not discarded intents. Where a constraint
cannot be independently established from post-state evidence, verification
fails closed rather than assuming compliance.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence

from canonical.runtime.generic_goal_tool_effect_planner_v1 import compile_goal_contract
from canonical.runtime.generic_tool_argument_binder_v1 import (
    canonical_field,
    extract_grounding_facts,
    extract_records,
)

SCHEMA = "PROJECT_BRAIN_GENERIC_GOAL_STATE_VERIFIER_V2"
_CANONICAL_GROUPS = {
    "name","text","date","status","priority","project","workspace","section",
    "task","tag","person","email","amount","id",
}
_RELATION_GROUPS = ("project","workspace","section","task","tag","person")


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
        elif isinstance(value, Mapping):
            pieces.append(_record_text(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    pieces.append(_record_text(item))
                elif isinstance(item, (str, int, float, bool)):
                    pieces.append(str(item))
    return " ".join(pieces)


def _raw_text(observations: Sequence[Any]) -> str:
    chunks: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, str):
            chunks.append(value)
            try:
                walk(json.loads(value))
            except Exception:
                return
        elif isinstance(value, Mapping):
            for key, child in value.items():
                chunks.append(str(key))
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, (int, float, bool)):
            chunks.append(str(value))

    for observation in observations:
        walk(observation)
    return " ".join(chunks)


def _record_id(record: Mapping[str, Any]) -> str | None:
    for key, value in record.items():
        if canonical_field(key) == "id" and isinstance(value, (str, int)):
            text = str(value).strip()
            if text:
                return text
    return None


def _record_names(record: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    for key, value in record.items():
        if canonical_field(key) == "name" and isinstance(value, (str, int, float)):
            text = str(value).strip()
            if text:
                out.append(text)
    return out


def _record_relevant(record: Mapping[str, Any], resource_terms: Sequence[str]) -> bool:
    terms = {str(x).lower() for x in resource_terms or []}
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


def _target_signature(
    intent: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
) -> dict[str, str] | None:
    ranked: list[tuple[int, str, str, dict[str, str]]] = []
    terms = set(str(x).lower() for x in intent.get("resource_terms") or [])
    clause_words = _words(intent.get("clause") or "")
    for record in records:
        text = _record_text(record)
        words = _words(text)
        score = 3 * len(terms & words) + len(clause_words & words)
        rid = _record_id(record)
        names = _record_names(record)
        if rid:
            score += 2
        if score <= 0:
            continue
        signature: dict[str, str] = {}
        if rid:
            signature["id"] = rid
        if names:
            signature["name"] = names[0]
        if not signature:
            continue
        ranked.append((
            score,
            signature.get("id", ""),
            signature.get("name", ""),
            signature,
        ))
    ranked.sort(key=lambda x: (-x[0], x[1], x[2]))
    if not ranked:
        return None
    top = ranked[0][0]
    signatures = {
        json.dumps(row[3], sort_keys=True)
        for row in ranked if row[0] == top
    }
    if len(signatures) != 1:
        return None
    return ranked[0][3]


def _same_target(record: Mapping[str, Any], signature: Mapping[str, str]) -> bool:
    if signature.get("id"):
        return _record_id(record) == signature["id"]
    wanted = _norm(signature.get("name"))
    return bool(wanted) and any(_norm(x) == wanted for x in _record_names(record))


def _verify_observe(
    intent: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    matches = [
        r for r in records
        if _record_relevant(r, intent.get("resource_terms") or [])
    ]
    return {
        "verified": bool(matches),
        "reason": None if matches else "NO_RELEVANT_POST_ACTION_STATE_OBSERVED",
        "matching_record_count": len(matches),
    }


def _verify_update(
    intent: Mapping[str, Any],
    context_records: Sequence[Mapping[str, Any]],
    post_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    assignment = _assignment_from_clause(str(intent.get("clause") or ""))
    if assignment is None:
        return {"verified": False, "reason": "EXPLICIT_UPDATE_PREDICATE_NOT_DERIVABLE"}
    signature = _target_signature(intent, context_records)
    if signature is None:
        return {"verified": False, "reason": "UPDATE_TARGET_IDENTITY_NOT_UNIQUELY_GROUNDED"}
    field_group, expected = assignment
    expected_norm = _norm(expected)
    candidates = [r for r in post_records if _same_target(r, signature)]
    for record in candidates:
        for value in _field_values(record, field_group):
            if _norm(value) == expected_norm:
                return {
                    "verified": True,
                    "reason": None,
                    "target": dict(signature),
                    "field_group": field_group,
                    "expected": expected,
                    "actual": value,
                }
    return {
        "verified": False,
        "reason": "TARGET_POST_ACTION_FIELD_VALUE_NOT_OBSERVED",
        "target": dict(signature),
        "field_group": field_group,
        "expected": expected,
    }


def _verify_create(
    intent: Mapping[str, Any],
    post_records: Sequence[Mapping[str, Any]],
    grounding_facts: Mapping[str, list[str]],
) -> dict[str, Any]:
    names = [x for x in grounding_facts.get("name", []) if str(x).strip()]
    if not names:
        return {"verified": False, "reason": "CREATED_OBJECT_NAME_NOT_GROUNDED"}
    expected_name = _norm(names[0])
    candidates = [
        record for record in post_records
        if any(_norm(value) == expected_name for value in _field_values(record, "name"))
    ]
    if not candidates:
        return {
            "verified": False,
            "reason": "CREATED_OBJECT_NOT_OBSERVED",
            "expected_name": names[0],
        }

    # Verify additional explicit scalar facts when the created record exposes
    # the corresponding field. This prevents name-only false positives while
    # avoiding claims about fields not observable on the selected read surface.
    checked: dict[str, Any] = {"name": names[0]}
    for group in ("date","status","priority","amount","email"):
        values = [x for x in grounding_facts.get(group, []) if str(x).strip()]
        if not values:
            continue
        expected = _norm(values[0])
        exposed = [
            value
            for record in candidates
            for value in _field_values(record, group)
        ]
        if exposed and not any(_norm(value) == expected for value in exposed):
            return {
                "verified": False,
                "reason": "CREATED_OBJECT_FIELD_MISMATCH:" + group,
                "expected": values[0],
                "observed": exposed,
            }
        if exposed:
            checked[group] = values[0]

    return {
        "verified": True,
        "reason": None,
        "expected_name": names[0],
        "checked_fields": checked,
    }


def _verify_delete(
    intent: Mapping[str, Any],
    context_records: Sequence[Mapping[str, Any]],
    verification_observations: Sequence[Any],
) -> dict[str, Any]:
    signature = _target_signature(intent, context_records)
    if signature is None:
        return {"verified": False, "reason": "DELETE_TARGET_IDENTITY_NOT_UNIQUELY_GROUNDED"}
    raw = _norm(_raw_text(verification_observations))
    strong_absence = (
        re.search(r"\b404\b", raw) is not None
        or "not found" in raw
        or "does not exist" in raw
        or "missing record" in raw
    )
    if not strong_absence:
        return {
            "verified": False,
            "reason": "DELETE_ABSENCE_NOT_STRONGLY_PROVED",
            "target": dict(signature),
        }
    return {"verified": True, "reason": None, "target": dict(signature)}


def _relation_anchors(
    goal: str,
    context_records: Sequence[Mapping[str, Any]],
    facts: Mapping[str, list[str]],
) -> dict[str, set[str]]:
    anchors: dict[str, set[str]] = {}
    for group in _RELATION_GROUPS:
        names = {
            _norm(x)
            for x in facts.get(group + "_name", [])
            if _norm(x)
        }
        if group == "task":
            names |= {
                _norm(x)
                for x in facts.get("name", [])
                if _norm(x)
            }
        values = set(names)
        for record in context_records:
            record_names = {_norm(x) for x in _record_names(record)}
            if names and record_names & names:
                rid = _record_id(record)
                if rid:
                    values.add(_norm(rid))
        if values:
            anchors[group] = values
    return anchors


def _verify_associate(
    goal: str,
    context_records: Sequence[Mapping[str, Any]],
    post_records: Sequence[Mapping[str, Any]],
    facts: Mapping[str, list[str]],
) -> dict[str, Any]:
    anchors = _relation_anchors(goal, context_records, facts)
    if len(anchors) < 2:
        return {"verified": False, "reason": "ASSOCIATION_ENDPOINTS_NOT_GROUNDED"}
    for record in post_records:
        text = _norm(_record_text(record))
        matched = [
            group for group, values in anchors.items()
            if any(value and value in text for value in values)
        ]
        if len(set(matched)) >= 2:
            return {
                "verified": True,
                "reason": None,
                "matched_relation_groups": sorted(set(matched)),
            }
    return {
        "verified": False,
        "reason": "ASSOCIATION_RELATION_NOT_OBSERVED",
        "grounded_relation_groups": sorted(anchors),
    }


def _verify_notify(
    post_records: Sequence[Mapping[str, Any]],
    facts: Mapping[str, list[str]],
) -> dict[str, Any]:
    recipients = [_norm(x) for x in facts.get("email", []) if _norm(x)]
    if not recipients:
        return {"verified": False, "reason": "NOTIFICATION_RECIPIENT_NOT_GROUNDED"}
    subject_values = [_norm(x) for x in facts.get("name", []) if _norm(x)]
    for record in post_records:
        text = _norm(_record_text(record))
        if not any(recipient in text for recipient in recipients):
            continue
        if subject_values and not any(subject in text for subject in subject_values):
            continue
        return {
            "verified": True,
            "reason": None,
            "recipient": recipients[0],
        }
    return {
        "verified": False,
        "reason": "SENT_NOTIFICATION_NOT_OBSERVED",
        "recipient": recipients[0],
    }


def _verify_forbidden_delete(
    intent: Mapping[str, Any],
    context_records: Sequence[Mapping[str, Any]],
    post_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    signature = _target_signature(intent, context_records)
    if signature is None:
        return {"verified": False, "reason": "FORBIDDEN_DELETE_TARGET_NOT_GROUNDED"}
    survived = any(_same_target(record, signature) for record in post_records)
    return {
        "verified": survived,
        "reason": None if survived else "FORBIDDEN_DELETE_TARGET_NOT_OBSERVED_POST_ACTION",
        "target": dict(signature),
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
            "constraint_results": [],
        }

    intents = list(contract.get("intents") or [])
    positive = [x for x in intents if not x.get("forbidden")]
    forbidden = [x for x in intents if x.get("forbidden")]
    context_records = extract_records(context_observations)
    post_records = extract_records(verification_observations)
    facts = extract_grounding_facts(goal, context_observations)
    results: list[dict[str, Any]] = []

    for intent in positive:
        action = str(intent.get("action_class") or "")
        if action == "observe":
            detail = _verify_observe(intent, post_records)
        elif action == "update":
            detail = _verify_update(intent, context_records, post_records)
        elif action == "create":
            detail = _verify_create(intent, post_records, facts)
        elif action == "delete":
            detail = _verify_delete(intent, context_records, verification_observations)
        elif action == "associate":
            detail = _verify_associate(
                goal, context_records, post_records, facts
            )
        elif action == "notify":
            detail = _verify_notify(post_records, facts)
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

    constraints: list[dict[str, Any]] = []
    for intent in forbidden:
        action = str(intent.get("action_class") or "")
        if action == "delete":
            detail = _verify_forbidden_delete(
                intent, context_records, post_records
            )
        else:
            detail = {
                "verified": False,
                "reason": "FORBIDDEN_ACTION_VERIFICATION_UNSUPPORTED:" + action,
            }
        constraints.append({
            "intent_id": intent.get("id"),
            "action_class": action,
            **detail,
        })

    ok = (
        all(x.get("verified") is True for x in results)
        and all(x.get("verified") is True for x in constraints)
    )
    return {
        "schema": SCHEMA,
        "pass": ok,
        "status": "VERIFIED" if ok else "UNRESOLVED",
        "reason": None if ok else "ONE_OR_MORE_GOAL_OR_CONSTRAINT_PREDICATES_UNVERIFIED",
        "intent_results": results,
        "constraint_results": constraints,
        "context_record_count": len(context_records),
        "verification_record_count": len(post_records),
    }
