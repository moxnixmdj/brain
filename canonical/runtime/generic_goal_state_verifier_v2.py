"""Independent receipt-bound generic goal-state verifier V2.

V2 verifies goal predicates against fresh post-action observations while binding
each state claim to the exact generic execution receipt that caused it.

Supported generic action classes:
- observe: relevant state is freshly observable;
- update: exact intended field value exists on the exact acted-on record when a
  target identifier was grounded;
- create: the exact grounded object name appears post-action and was not already
  present in the observed pre-action state;
- associate: grounded relation references did not co-occur pre-action and do
  co-occur in one fresh post-action record subtree;
- delete: the exact acted-on target is independently re-read and returns a
  not-found/gone result;
- notify: a fresh artifact contains the grounded recipient plus any grounded
  subject/body facts and no equivalent artifact was observed pre-action.

Insufficient provenance or ambiguous evidence fails closed.
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
_RELATION_GROUPS = {"id","project","workspace","section","task","tag","person"}
_NOTIFY_GROUPS = {"email","person","name","text"}


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
    terms = {str(x).lower() for x in resource_terms or []}
    if not terms:
        return True
    return bool(terms & _words(_record_text(record)))


def _record_id(record: Mapping[str, Any]) -> str | None:
    for key, value in record.items():
        if canonical_field(key) == "id" and isinstance(value, (str, int)):
            text = str(value).strip()
            if text:
                return text
    return None


def _scalar_strings(value: Any) -> list[str]:
    out: list[str] = []

    def walk(x: Any) -> None:
        if isinstance(x, Mapping):
            for child in x.values():
                walk(child)
        elif isinstance(x, list):
            for child in x:
                walk(child)
        elif isinstance(x, (str, int, float, bool)):
            text = str(x).strip()
            if text:
                out.append(text)

    walk(value)
    return out


def _record_scalar_norms(record: Mapping[str, Any]) -> set[str]:
    return {_norm(x) for x in _scalar_strings(record) if _norm(x)}


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
    if group not in _CANONICAL_GROUPS:
        for piece in reversed(re.findall(r"[A-Za-z0-9_]+", field_phrase)):
            candidate = canonical_field(piece)
            if candidate in _CANONICAL_GROUPS:
                group = candidate
                break
    if group not in _CANONICAL_GROUPS:
        return None
    return group, expected


def _field_values(record: Mapping[str, Any], group: str) -> list[Any]:
    out: list[Any] = []
    for key, value in record.items():
        if canonical_field(key) != group:
            continue
        if isinstance(value, (str, int, float, bool)):
            out.append(value)
        elif isinstance(value, list):
            out.extend(x for x in value if isinstance(x, (str, int, float, bool)))
    return out


def _receipt_intent_id(receipt: Mapping[str, Any]) -> str | None:
    capability_id = str(receipt.get("capability_id") or "")
    parts = capability_id.split("::")
    for part in parts:
        if part.startswith("intent_"):
            return part
    return None


def _execution_receipt(
    receipts: Sequence[Any],
    intent_id: str,
    action_class: str,
) -> Mapping[str, Any] | None:
    exact = [
        r for r in receipts
        if isinstance(r, Mapping)
        and str(r.get("action_class") or "") == action_class
        and _receipt_intent_id(r) == intent_id
    ]
    if len(exact) == 1:
        return exact[0]
    same_action = [
        r for r in receipts
        if isinstance(r, Mapping)
        and str(r.get("action_class") or "") == action_class
    ]
    return same_action[0] if len(same_action) == 1 else None


def _grounded_binding_values(
    receipt: Mapping[str, Any] | None,
    allowed_groups: set[str] | None = None,
    *,
    parameters_only: bool = False,
) -> list[tuple[str, str]]:
    if not isinstance(receipt, Mapping):
        return []
    bindings = receipt.get("bindings")
    if not isinstance(bindings, Mapping):
        return []
    out: list[tuple[str, str]] = []
    for key, raw in bindings.items():
        if parameters_only and not str(key).startswith("parameter."):
            continue
        if not isinstance(raw, Mapping) or raw.get("source") != "grounded":
            continue
        field_name = str(key).split(".", 1)[-1]
        group = canonical_field(field_name)
        if allowed_groups is not None and group not in allowed_groups:
            continue
        value = raw.get("value")
        values = value if isinstance(value, list) else [value]
        for item in values:
            text = str(item or "").strip()
            if text:
                out.append((group, text))
    return out


def _verification_targets_value(
    receipts: Sequence[Any],
    value: str,
) -> bool:
    needle = str(value)
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            continue
        if str(receipt.get("method") or "").upper() != "GET":
            continue
        args = receipt.get("arguments")
        if not isinstance(args, Mapping):
            continue
        if needle in json.dumps(args, sort_keys=True, default=str):
            return True
    return False


def _has_not_found(value: Any) -> bool:
    if isinstance(value, Mapping):
        code = value.get("code", value.get("status"))
        if str(code) in {"404", "410"}:
            return True
        return any(_has_not_found(x) for x in value.values())
    if isinstance(value, list):
        return any(_has_not_found(x) for x in value)
    if isinstance(value, str):
        low = value.lower()
        return any(x in low for x in ("not found", "does not exist", "no such", "gone"))
    return False


def _verify_observe(intent: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    matches = [r for r in records if _record_relevant(r, intent.get("resource_terms") or [])]
    return {
        "verified": bool(matches),
        "reason": None if matches else "NO_RELEVANT_POST_ACTION_STATE_OBSERVED",
        "matching_record_count": len(matches),
    }


def _verify_update(
    intent: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    assignment = _assignment_from_clause(str(intent.get("clause") or ""))
    if assignment is None:
        return {"verified": False, "reason": "EXPLICIT_UPDATE_PREDICATE_NOT_DERIVABLE"}
    field_group, expected = assignment
    expected_norm = _norm(expected)
    target_ids = {
        _norm(value)
        for _, value in _grounded_binding_values(
            receipt, _RELATION_GROUPS, parameters_only=True
        )
    }
    candidates = [r for r in records if _record_relevant(r, intent.get("resource_terms") or [])]
    if target_ids:
        candidates = [
            r for r in candidates
            if _record_id(r) is not None and _norm(_record_id(r)) in target_ids
        ]
    for record in candidates:
        for value in _field_values(record, field_group):
            if _norm(value) == expected_norm:
                return {
                    "verified": True,
                    "reason": None,
                    "field_group": field_group,
                    "expected": expected,
                    "actual": value,
                    "target_ids": sorted(target_ids),
                }
    return {
        "verified": False,
        "reason": "POST_ACTION_FIELD_VALUE_NOT_OBSERVED_ON_ACTED_TARGET",
        "field_group": field_group,
        "expected": expected,
        "target_ids": sorted(target_ids),
        "candidate_count": len(candidates),
    }


def _verify_create(
    records: Sequence[Mapping[str, Any]],
    pre_records: Sequence[Mapping[str, Any]],
    grounding_facts: Mapping[str, list[str]],
) -> dict[str, Any]:
    names = [x for x in grounding_facts.get("name", []) if str(x).strip()]
    if not names:
        return {"verified": False, "reason": "CREATED_OBJECT_NAME_NOT_GROUNDED"}
    expected = _norm(names[0])
    existed = any(
        _norm(value) == expected
        for record in pre_records
        for value in _field_values(record, "name")
    )
    if existed:
        return {
            "verified": False,
            "reason": "CREATED_OBJECT_PREEXISTED_IN_OBSERVED_STATE",
            "expected_name": names[0],
        }
    matches = [
        record
        for record in records
        if any(_norm(value) == expected for value in _field_values(record, "name"))
    ]
    if matches:
        return {
            "verified": True,
            "reason": None,
            "expected_name": names[0],
            "observed_ids": sorted(
                {rid for rid in (_record_id(r) for r in matches) if rid}
            ),
        }
    return {
        "verified": False,
        "reason": "CREATED_OBJECT_NOT_OBSERVED",
        "expected_name": names[0],
    }


def _verify_associate(
    pre_records: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    refs = {
        _norm(value)
        for _, value in _grounded_binding_values(receipt, _RELATION_GROUPS)
    }
    if len(refs) < 2:
        return {"verified": False, "reason": "ASSOCIATION_REFERENCES_NOT_GROUNDED"}
    pre_present = any(refs <= _record_scalar_norms(record) for record in pre_records)
    if pre_present:
        return {
            "verified": False,
            "reason": "ASSOCIATION_PREEXISTED_IN_OBSERVED_STATE",
            "references": sorted(refs),
        }
    post_present = any(refs <= _record_scalar_norms(record) for record in records)
    return {
        "verified": post_present,
        "reason": None if post_present else "ASSOCIATION_NOT_OBSERVED_POST_ACTION",
        "references": sorted(refs),
    }


def _verify_delete(
    verification_observations: Sequence[Any],
    receipt: Mapping[str, Any] | None,
    verification_receipts: Sequence[Any],
) -> dict[str, Any]:
    targets = [
        value
        for _, value in _grounded_binding_values(
            receipt, _RELATION_GROUPS, parameters_only=True
        )
    ]
    if len(set(targets)) != 1:
        return {"verified": False, "reason": "DELETE_TARGET_NOT_UNIQUELY_GROUNDED"}
    target = targets[0]
    if not _verification_targets_value(verification_receipts, target):
        return {
            "verified": False,
            "reason": "DELETE_TARGET_NOT_INDEPENDENTLY_REREAD",
            "target": target,
        }
    absent = any(_has_not_found(x) for x in verification_observations)
    return {
        "verified": absent,
        "reason": None if absent else "DELETE_ABSENCE_NOT_PROVED_BY_FRESH_READ",
        "target": target,
    }


def _artifact_matches(
    record: Mapping[str, Any],
    expected: Sequence[tuple[str, str]],
) -> bool:
    scalars = _record_scalar_norms(record)
    for group, value in expected:
        needle = _norm(value)
        if group == "text":
            if not any(needle in scalar for scalar in scalars):
                return False
        else:
            if needle not in scalars:
                return False
    return True


def _verify_notify(
    pre_records: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    expected = _grounded_binding_values(receipt, _NOTIFY_GROUPS)
    if not expected:
        return {"verified": False, "reason": "NOTIFICATION_ARTIFACT_FACTS_NOT_GROUNDED"}
    if not any(group in {"email", "person"} for group, _ in expected):
        return {"verified": False, "reason": "NOTIFICATION_RECIPIENT_NOT_GROUNDED"}
    pre_matches = [r for r in pre_records if _artifact_matches(r, expected)]
    if pre_matches:
        return {"verified": False, "reason": "EQUIVALENT_NOTIFICATION_PREEXISTED"}
    post_matches = [r for r in records if _artifact_matches(r, expected)]
    return {
        "verified": bool(post_matches),
        "reason": None if post_matches else "NOTIFICATION_ARTIFACT_NOT_OBSERVED",
        "matching_record_ids": sorted(
            {rid for rid in (_record_id(r) for r in post_matches) if rid}
        ),
    }


def verify_goal_state(
    *,
    goal: str,
    context_observations: Sequence[Any],
    verification_observations: Sequence[Any],
    execution_receipts: Sequence[Any] = (),
    verification_receipts: Sequence[Any] = (),
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

    positive = [x for x in contract.get("intents") or [] if not x.get("forbidden")]
    if not positive:
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "VERIFIED_NO_POSITIVE_ACTION_REQUIRED",
            "intent_results": [],
        }

    pre_records = extract_records(context_observations)
    records = extract_records(verification_observations)
    facts = extract_grounding_facts(goal, context_observations)
    results: list[dict[str, Any]] = []

    for intent in positive:
        action = str(intent.get("action_class") or "")
        intent_id = str(intent.get("id") or "")
        receipt = _execution_receipt(execution_receipts, intent_id, action)
        if action == "observe":
            detail = _verify_observe(intent, records)
        elif action == "update":
            detail = _verify_update(intent, records, receipt)
        elif action == "create":
            detail = _verify_create(records, pre_records, facts)
        elif action == "associate":
            detail = _verify_associate(pre_records, records, receipt)
        elif action == "delete":
            detail = _verify_delete(
                verification_observations,
                receipt,
                verification_receipts,
            )
        elif action == "notify":
            detail = _verify_notify(pre_records, records, receipt)
        else:
            detail = {
                "verified": False,
                "reason": "GENERIC_VERIFIER_UNSUPPORTED_ACTION_CLASS:" + action,
            }
        results.append({
            "intent_id": intent_id,
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
        "execution_receipt_count": len(list(execution_receipts)),
        "verification_receipt_count": len(list(verification_receipts)),
    }
