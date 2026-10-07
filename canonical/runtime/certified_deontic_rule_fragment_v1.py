"""Certified deontic rule fragment v1.

One-sided source proof for a deliberately tiny controlled-English fragment.
It proves only explicit obligation/prohibition structure while preserving the
subject, action, and optional condition/exception as exact source spans.

Supported shapes:
- SUBJECT must ACTION
- SUBJECT shall ACTION
- SUBJECT must not ACTION
- SUBJECT shall not ACTION
- SUBJECT is required to ACTION
- SUBJECT is prohibited from ACTION
- If CONDITION, <simple deontic clause>
- <simple deontic clause> if CONDITION
- <simple deontic clause> unless EXCEPTION
- <simple deontic clause> when TRIGGER

Everything else returns UNRESOLVED. In particular this module does not resolve
references, infer domain entities, normalize action meaning, or decide whether
a source is authoritative.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any, Mapping

from canonical.runtime.certified_scope_fragment_v1 import parse_scope

SCHEMA = "BRAIN_CERTIFIED_DEONTIC_RULE_FRAGMENT_V1"

_REQUIRED_PATTERNS = (
    re.compile(r"^(?P<subject>[A-Za-z0-9][A-Za-z0-9 _./:'()\-]{0,180}?)\s+(?P<modal>must|shall)\s+(?P<action>[A-Za-z0-9][A-Za-z0-9 _./:'()\-]{0,240})$", re.I),
    re.compile(r"^(?P<subject>[A-Za-z0-9][A-Za-z0-9 _./:'()\-]{0,180}?)\s+(?P<modal>is\s+required\s+to)\s+(?P<action>[A-Za-z0-9][A-Za-z0-9 _./:'()\-]{0,240})$", re.I),
)
_PROHIBITED_PATTERNS = (
    re.compile(r"^(?P<subject>[A-Za-z0-9][A-Za-z0-9 _./:'()\-]{0,180}?)\s+(?P<modal>must\s+not|shall\s+not)\s+(?P<action>[A-Za-z0-9][A-Za-z0-9 _./:'()\-]{0,240})$", re.I),
    re.compile(r"^(?P<subject>[A-Za-z0-9][A-Za-z0-9 _./:'()\-]{0,180}?)\s+(?P<modal>is\s+prohibited\s+from)\s+(?P<action>[A-Za-z0-9][A-Za-z0-9 _./:'()\-]{0,240})$", re.I),
)
_UNSAFE_JOIN = re.compile(r"\b(?:and|or|except|excepting)\b", re.I)
_SCOPE_WORD = re.compile(r"\b(?:if|unless|when|before|after)\b", re.I)


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and (text[end - 1].isspace() or text[end - 1] in ".,;:"):
        end -= 1
    return start, end


def _unresolved(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "UNRESOLVED",
        "reason": reason,
        "terminal_authority": False,
        **extra,
    }


def _simple_clause(text: str, *, offset: int = 0) -> dict[str, Any]:
    start, end = _trim(text, 0, len(text))
    clause = text[start:end]
    if not clause:
        return _unresolved("EMPTY_CLAUSE")
    if any(ch in clause for ch in ",;"):
        return _unresolved("COMPOUND_PUNCTUATION_OUTSIDE_FRAGMENT")
    if _SCOPE_WORD.search(clause):
        return _unresolved("SCOPE_OPERATOR_REQUIRES_CERTIFIED_SCOPE_PATH")

    match = None
    relation = None
    for pat in _PROHIBITED_PATTERNS:
        match = pat.fullmatch(clause)
        if match:
            relation = "PROHIBITED"
            break
    if match is None:
        for pat in _REQUIRED_PATTERNS:
            match = pat.fullmatch(clause)
            if match:
                relation = "REQUIRED"
                break
    if match is None or relation is None:
        return _unresolved("NO_CONTROLLED_DEONTIC_FORM")

    subject = match.group("subject").strip()
    action = match.group("action").strip()
    if _UNSAFE_JOIN.search(subject) or _UNSAFE_JOIN.search(action):
        return _unresolved("COORDINATED_OR_EXCEPTION_CONTENT_OUTSIDE_FRAGMENT")
    if not subject or not action:
        return _unresolved("SUBJECT_OR_ACTION_EMPTY")

    local_subject = match.span("subject")
    local_action = match.span("action")
    local_modal = match.span("modal")
    base = offset + start
    return {
        "schema": SCHEMA,
        "status": "PARSED_SIMPLE",
        "relation": relation,
        "subject_span": [base + local_subject[0], base + local_subject[1]],
        "subject_text_sha256": _sha(subject),
        "modal_span": [base + local_modal[0], base + local_modal[1]],
        "modal_text": match.group("modal"),
        "action_span": [base + local_action[0], base + local_action[1]],
        "action_text_sha256": _sha(action),
        "terminal_authority": False,
    }


def parse_deontic_rule(text: str, *, source: str = "source") -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "SOURCE_TEXT_MISSING", "terminal_authority": False}
    if not isinstance(source, str) or not source.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "SOURCE_ID_MISSING", "terminal_authority": False}

    simple = _simple_clause(text)
    if simple.get("status") == "PARSED_SIMPLE":
        payload = dict(simple)
        payload["status"] = "PARSED"
        payload["source_id"] = source
        payload["scope"] = None
        payload["rule_id"] = "DR-" + _sha(
            f"{source}\0{payload['relation']}\0{payload['subject_span']}\0{payload['action_span']}"
        )[:20]
        return payload

    scoped = parse_scope(text, source=source)
    if scoped.get("status") != "PARSED":
        return _unresolved(
            "SOURCE_NOT_IN_SIMPLE_OR_SUPPORTED_SCOPED_DEONTIC_FRAGMENT",
            simple_reason=simple.get("reason"),
            scope_status=scoped.get("status"),
            scope_reason=scoped.get("reason"),
        )
    p = scoped["parse"]
    relation = p["relation"]
    if relation not in {"IF_THEN", "UNLESS", "WHEN"}:
        return _unresolved("SCOPE_RELATION_NOT_DEONTICALLY_SUPPORTED", scope_relation=relation)

    deontic_role = "CONSEQUENT" if relation in {"IF_THEN", "WHEN"} else "ORDINARY_BRANCH"
    if p["left_role"] == deontic_role:
        span = p["left_span"]
        condition_role = p["right_role"]
        condition_span = p["right_span"]
    elif p["right_role"] == deontic_role:
        span = p["right_span"]
        condition_role = p["left_role"]
        condition_span = p["left_span"]
    else:
        return _unresolved("CERTIFIED_SCOPE_HAS_NO_DEONTIC_BRANCH_ROLE", scope_relation=relation)

    branch_text = text[span[0]:span[1]]
    branch = _simple_clause(branch_text, offset=span[0])
    if branch.get("status") != "PARSED_SIMPLE":
        return _unresolved(
            "DEONTIC_BRANCH_OUTSIDE_CONTROLLED_FRAGMENT",
            branch_reason=branch.get("reason"),
            scope_parse=p,
        )

    cond_text = text[condition_span[0]:condition_span[1]]
    payload = dict(branch)
    payload["status"] = "PARSED"
    payload["source_id"] = source
    payload["scope"] = {
        "scope_id": p["scope_id"],
        "relation": relation,
        "operator_id": p["operator_id"],
        "deontic_role": deontic_role,
        "deontic_span": list(span),
        "condition_role": condition_role,
        "condition_span": list(condition_span),
        "condition_text_sha256": _sha(cond_text),
    }
    payload["rule_id"] = "DR-" + _sha(
        f"{source}\0{payload['relation']}\0{payload['subject_span']}\0{payload['action_span']}\0{p['scope_id']}"
    )[:20]
    return payload
