"""Certified scope parser for a deliberately tiny English fragment.

This module proves only source structure for a few explicit constructions:
- MAIN unless EXCEPTION
- if ANTECEDENT, CONSEQUENT
- CONSEQUENT if ANTECEDENT
- LEFT before RIGHT
- LEFT after RIGHT

It does not prove what either clause means, resolve references, classify entities,
or infer domain rules. Nested operators of the same structural family are rejected
rather than guessed. The output is source-aligned and has no terminal authority.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Any

from canonical.runtime.semantic_operator_counterfactuals import extract_semantic_operators

SCHEMA = "BRAIN_CERTIFIED_SCOPE_FRAGMENT_V1"

_CONDITIONAL = {"CONDITIONAL_UNLESS", "CONDITIONAL_IF", "CONDITIONAL_WHEN"}
_TEMPORAL = {"TEMPORAL_BEFORE", "TEMPORAL_AFTER"}


@dataclass(frozen=True)
class ScopeParse:
    scope_id: str
    relation: str
    operator_id: str
    operator_span: tuple[int, int]
    left_role: str
    left_span: tuple[int, int]
    left_text_sha256: str
    right_role: str
    right_span: tuple[int, int]
    right_text_sha256: str

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["operator_span"] = list(self.operator_span)
        out["left_span"] = list(self.left_span)
        out["right_span"] = list(self.right_span)
        return out


def _hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and (text[end - 1].isspace() or text[end - 1] in ".,;:"):
        end -= 1
    return start, end


def _scope_id(source: str, relation: str, operator_id: str, spans: tuple[tuple[int, int], tuple[int, int]]) -> str:
    raw = f"{source}\0{relation}\0{operator_id}\0{spans!r}".encode("utf-8")
    return "SCOPE-" + sha256(raw).hexdigest()[:20]


def _reject_nested_family(text: str, source: str, family: set[str], chosen_id: str) -> str | None:
    other = [
        op for op in extract_semantic_operators(text, source=source)
        if op.semantic_class in family and op.operator_id != chosen_id
    ]
    if other:
        return "NESTED_OR_MULTIPLE_SAME_FAMILY_OPERATORS"
    return None


def _unresolved(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "UNRESOLVED",
        "reason": reason,
        "terminal_authority": False,
        **extra,
    }


def parse_scope(text: str, *, source: str = "source") -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "SOURCE_TEXT_MISSING", "terminal_authority": False}
    if not isinstance(source, str) or not source.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "SOURCE_ID_MISSING", "terminal_authority": False}

    ops = extract_semantic_operators(text, source=source)
    scope_ops = [op for op in ops if op.semantic_class in (_CONDITIONAL | _TEMPORAL)]
    if len(scope_ops) != 1:
        return _unresolved(
            "EXACTLY_ONE_SUPPORTED_SCOPE_OPERATOR_REQUIRED",
            candidate_scope_operator_count=len(scope_ops),
        )

    op = scope_ops[0]
    family = _CONDITIONAL if op.semantic_class in _CONDITIONAL else _TEMPORAL
    nested = _reject_nested_family(text, source, family, op.operator_id)
    if nested:
        return _unresolved(nested)

    relation = ""
    left_role = ""
    right_role = ""
    left: tuple[int, int]
    right: tuple[int, int]

    if op.semantic_class == "CONDITIONAL_IF" and not text[:op.start].strip():
        # Prefix IF is admitted only in the exact controlled shape: If A, B.
        commas = [i for i, ch in enumerate(text[op.end:], start=op.end) if ch == ","]
        if len(commas) != 1:
            return _unresolved("PREFIX_IF_REQUIRES_EXACTLY_ONE_COMMA_CONTROLLED_FORM")
        comma = commas[0]
        left = _trim_span(text, op.end, comma)
        right = _trim_span(text, comma + 1, len(text))
        relation = "IF_THEN"
        left_role, right_role = "ANTECEDENT", "CONSEQUENT"

    else:
        left = _trim_span(text, 0, op.start)
        right = _trim_span(text, op.end, len(text))

        if op.semantic_class == "CONDITIONAL_UNLESS":
            relation = "UNLESS"
            left_role, right_role = "ORDINARY_BRANCH", "EXCEPTION_BRANCH"
        elif op.semantic_class == "CONDITIONAL_IF":
            relation = "IF_THEN"
            left_role, right_role = "CONSEQUENT", "ANTECEDENT"
        elif op.semantic_class == "CONDITIONAL_WHEN":
            if not text[:op.start].strip():
                return _unresolved("PREFIX_WHEN_NOT_IN_V1_FRAGMENT")
            relation = "WHEN"
            left_role, right_role = "CONSEQUENT", "TRIGGER"
        elif op.semantic_class == "TEMPORAL_BEFORE":
            relation = "BEFORE"
            left_role, right_role = "EARLIER_EVENT", "LATER_EVENT"
        elif op.semantic_class == "TEMPORAL_AFTER":
            relation = "AFTER"
            left_role, right_role = "LATER_EVENT", "EARLIER_EVENT"
        else:
            return _unresolved("UNSUPPORTED_OPERATOR")

    if left[0] >= left[1] or right[0] >= right[1]:
        return _unresolved("EMPTY_SCOPE_OPERAND")

    left_text = text[left[0]:left[1]]
    right_text = text[right[0]:right[1]]
    parsed = ScopeParse(
        scope_id=_scope_id(source, relation, op.operator_id, (left, right)),
        relation=relation,
        operator_id=op.operator_id,
        operator_span=(op.start, op.end),
        left_role=left_role,
        left_span=left,
        left_text_sha256=_hash(left_text),
        right_role=right_role,
        right_span=right,
        right_text_sha256=_hash(right_text),
    )
    return {
        "schema": SCHEMA,
        "status": "PARSED",
        "parse": parsed.to_dict(),
        "terminal_authority": False,
        "scope": "STRUCTURAL_OPERATOR_SCOPE_ONLY__NO_DOMAIN_MEANING_OR_REFERENCE_RESOLUTION",
    }
