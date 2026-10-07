from __future__ import annotations

from hashlib import sha256
import re
from typing import Any

SCHEMA = "BRAIN_CERTIFIED_NORMATIVE_RULE_FRAGMENT_V1"

_RULE = re.compile(
    r"^(?P<subject>.+?)\s+(?P<modal>must|shall)\s+(?P<neg>not\s+)?"
    r"(?P<action>.+?)(?:\s+unless\s+(?P<exception>.+?))?[.!]?$",
    re.IGNORECASE,
)

_FORBIDDEN_NESTED = re.compile(
    r"\b(?:must|shall|unless|\bif\b|\bwhen\b|\bbefore\b|\bafter\b)\b",
    re.IGNORECASE,
)

def _h(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()

def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and (text[end - 1].isspace() or text[end - 1] in ".!"):
        end -= 1
    return start, end

def _span_for_group(match: re.Match[str], name: str, text: str) -> tuple[int, int] | None:
    try:
        a, b = match.span(name)
    except IndexError:
        return None
    if a < 0 or b < 0:
        return None
    a, b = _trim(text, a, b)
    return (a, b) if a < b else None

def parse_rule(text: str, *, source_id: str = "source") -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "SOURCE_TEXT_MISSING"}
    if not isinstance(source_id, str) or not source_id.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "SOURCE_ID_MISSING"}

    src = text.strip()
    m = _RULE.fullmatch(src)
    if m is None:
        return {"schema": SCHEMA, "status": "UNRESOLVED", "reason": "OUTSIDE_CONTROLLED_NORMATIVE_GRAMMAR"}

    subject_span = _span_for_group(m, "subject", src)
    action_span = _span_for_group(m, "action", src)
    exception_span = _span_for_group(m, "exception", src)
    if subject_span is None or action_span is None:
        return {"schema": SCHEMA, "status": "UNRESOLVED", "reason": "EMPTY_OPERAND"}

    subject = src[slice(*subject_span)]
    action = src[slice(*action_span)]
    exception = src[slice(*exception_span)] if exception_span is not None else None

    # The fragment intentionally refuses nested semantic structure inside the
    # payload clauses. Their domain meaning must come from typed facts or another
    # independently certified source relation.
    for label, value in (("SUBJECT", subject), ("ACTION", action), ("EXCEPTION", exception)):
        if value is None:
            continue
        if _FORBIDDEN_NESTED.search(value):
            return {
                "schema": SCHEMA,
                "status": "UNRESOLVED",
                "reason": "NESTED_OR_AMBIGUOUS_OPERATOR_IN_" + label,
            }

    modal = m.group("modal").lower()
    negated = bool(m.group("neg"))
    kind = "PROHIBITION" if negated else "OBLIGATION"

    return {
        "schema": SCHEMA,
        "status": "PARSED",
        "source_id": source_id,
        "source_sha256": _h(src),
        "normative_kind": kind,
        "modal": modal.upper(),
        "subject": {
            "span": list(subject_span),
            "text": subject,
            "sha256": _h(subject),
        },
        "action": {
            "span": list(action_span),
            "text": action,
            "sha256": _h(action),
        },
        "exception": None if exception is None else {
            "span": list(exception_span),
            "text": exception,
            "sha256": _h(exception),
        },
        "semantic_boundary": (
            "ONLY_MODAL_POLARITY_AND_OPTIONAL_UNLESS_BRANCH_ARE_CERTIFIED;"
            "SUBJECT_ACTION_AND_EXCEPTION_DOMAIN_MEANING_ARE_NOT_INFERRED"
        ),
    }

def decide(
    text: str,
    *,
    source_id: str = "source",
    subject_applies: bool,
    exception_holds: bool | None = None,
) -> dict[str, Any]:
    parsed = parse_rule(text, source_id=source_id)
    if parsed.get("status") != "PARSED":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": "RULE_NOT_CERTIFIABLY_PARSED",
            "parse": parsed,
        }
    if not isinstance(subject_applies, bool):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "SUBJECT_APPLIES_NOT_BOOLEAN"}

    has_exception = parsed["exception"] is not None
    if has_exception:
        if not isinstance(exception_holds, bool):
            return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "EXCEPTION_HOLDS_NOT_BOOLEAN"}
    elif exception_holds is not None:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "UNDECLARED_EXCEPTION_FACT"}

    if not subject_applies:
        disposition = "NOT_APPLICABLE"
    elif has_exception and exception_holds:
        disposition = "EXCEPTION_APPLIES"
    elif parsed["normative_kind"] == "OBLIGATION":
        disposition = "REQUIRED"
    else:
        disposition = "PROHIBITED"

    return {
        "schema": SCHEMA,
        "status": "DECIDED",
        "source_id": source_id,
        "source_sha256": parsed["source_sha256"],
        "normative_kind": parsed["normative_kind"],
        "disposition": disposition,
        "action": parsed["action"],
        "subject": parsed["subject"],
        "exception": parsed["exception"],
        "subject_applies": subject_applies,
        "exception_holds": exception_holds if has_exception else None,
        "model_dependency_count": 0,
        "external_capability_dependency": False,
        "terminal_authority": False,
    }
