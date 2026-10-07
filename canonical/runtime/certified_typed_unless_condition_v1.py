"""Certified typed condition evaluator for a narrow UNLESS fragment.

Supported exception-branch forms:
- FIELD is true|false
- FIELD = true|false
- FIELD is NUMBER
- FIELD = NUMBER
- FIELD is at least NUMBER
- FIELD is at most NUMBER
- FIELD is exactly NUMBER

FIELD must literally name a field in a content-addressed typed context. Boolean
conditions require BOOL fields. Numeric conditions require DECIMAL_STRING fields
with exact decimal syntax. The module recomputes the certified UNLESS scope and
typed-context digest; unsupported language remains unresolved.

This proves only the truth value of the controlled source condition relative to
the supplied authoritative typed context. It has no terminal authority.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from canonical.runtime.certified_scope_fragment_v1 import parse_scope
from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256

SCHEMA = "BRAIN_CERTIFIED_TYPED_UNLESS_CONDITION_V1"

_FIELD = r"(?P<field>[A-Za-z_][A-Za-z0-9_]*)"
_NUM = r"(?P<num>-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?)"
_BOOL = re.compile(rf"^\s*{_FIELD}\s*(?:is\s+|=\s*)(?P<bool>true|false)\s*$", re.I)
_NUM_EQ = re.compile(rf"^\s*{_FIELD}\s*(?:is\s+|=\s*){_NUM}\s*$", re.I)
_MIN = re.compile(rf"^\s*{_FIELD}\s+is\s+at\s+least\s+{_NUM}\s*$", re.I)
_MAX = re.compile(rf"^\s*{_FIELD}\s+is\s+at\s+most\s+{_NUM}\s*$", re.I)
_EXACT = re.compile(rf"^\s*{_FIELD}\s+is\s+exactly\s+{_NUM}\s*$", re.I)
_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _condition_atom(
    *,
    source_id: str,
    scope_id: str,
    field_name: str,
    operator: str,
    literal: str,
    typed_context_sha256_value: str,
) -> str:
    payload = {
        "source_id": source_id,
        "scope_id": scope_id,
        "field_name": field_name,
        "operator": operator,
        "literal": literal,
        "typed_context_sha256": typed_context_sha256_value,
    }
    return "CERTIFIED_CONDITION::" + sha256(_canon(payload).encode("utf-8")).hexdigest()


def _decimal(value: Any) -> Decimal:
    if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
        raise ValueError("DECIMAL_STRING_INVALID")
    try:
        out = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("DECIMAL_STRING_INVALID") from exc
    if not out.is_finite():
        raise ValueError("DECIMAL_STRING_NONFINITE")
    return out


def evaluate_unless_condition(
    source_text: str,
    *,
    source_id: str,
    typed_context: Mapping[str, Any],
    expected_typed_context_sha256: str,
) -> dict[str, Any]:
    if not isinstance(source_text, str) or not source_text.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["SOURCE_TEXT_MISSING"], "terminal_authority": False}
    if not isinstance(source_id, str) or not source_id.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["SOURCE_ID_MISSING"], "terminal_authority": False}
    if not isinstance(typed_context, Mapping):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["TYPED_CONTEXT_REQUIRED"], "terminal_authority": False}
    if not isinstance(expected_typed_context_sha256, str) or len(expected_typed_context_sha256) != 64:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["EXPECTED_TYPED_CONTEXT_SHA256_REQUIRED"], "terminal_authority": False}

    actual_digest = typed_context_sha256(typed_context)
    if actual_digest != expected_typed_context_sha256:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["TYPED_CONTEXT_CONTENT_ADDRESS_MISMATCH"],
            "typed_context_sha256": actual_digest,
            "terminal_authority": False,
        }

    scoped = parse_scope(source_text, source=source_id)
    p = scoped.get("parse") if scoped.get("status") == "PARSED" else None
    if not isinstance(p, Mapping) or p.get("relation") != "UNLESS":
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "reason": "SOURCE_NOT_IN_CERTIFIED_SINGLE_UNLESS_FRAGMENT",
            "scope_parse": scoped,
            "terminal_authority": False,
        }

    start, end = p["right_span"]
    condition_text = source_text[start:end]

    match = _BOOL.fullmatch(condition_text)
    operator = ""
    literal = ""
    field_name = ""
    required_type = ""
    expected_value: Any = None

    if match:
        field_name = match.group("field")
        literal = match.group("bool").lower()
        operator = "BOOL_EQ"
        required_type = "BOOL"
        expected_value = literal == "true"
    else:
        for regex, op in ((_MIN, "DECIMAL_GE"), (_MAX, "DECIMAL_LE"), (_EXACT, "DECIMAL_EQ"), (_NUM_EQ, "DECIMAL_EQ")):
            match = regex.fullmatch(condition_text)
            if match:
                field_name = match.group("field")
                literal = match.group("num")
                operator = op
                required_type = "DECIMAL_STRING"
                break

    if not field_name:
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "reason": "EXCEPTION_BRANCH_OUTSIDE_CERTIFIED_TYPED_CONDITION_GRAMMAR",
            "condition_span": [start, end],
            "condition_sha256": sha256(condition_text.encode("utf-8")).hexdigest(),
            "terminal_authority": False,
        }

    schema_id = typed_context.get("schema_id")
    fields = typed_context.get("fields")
    if not isinstance(schema_id, str) or not schema_id.strip() or not isinstance(fields, Mapping):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["TYPED_CONTEXT_SCHEMA_INVALID"], "terminal_authority": False}

    row = fields.get(field_name)
    if not isinstance(row, Mapping):
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "reason": "SOURCE_FIELD_NOT_PRESENT_IN_TYPED_CONTEXT",
            "field_name": field_name,
            "terminal_authority": False,
        }
    if row.get("type") != required_type:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [f"TYPED_FIELD_TYPE_MISMATCH:{field_name}:{row.get('type')}!={required_type}"],
            "terminal_authority": False,
        }

    actual_value = row.get("value")
    try:
        if operator == "BOOL_EQ":
            if not isinstance(actual_value, bool):
                raise ValueError("BOOL_VALUE_INVALID")
            holds = actual_value is expected_value
        else:
            actual_num = _decimal(actual_value)
            literal_num = _decimal(literal)
            if operator == "DECIMAL_GE":
                holds = actual_num >= literal_num
            elif operator == "DECIMAL_LE":
                holds = actual_num <= literal_num
            else:
                holds = actual_num == literal_num
    except ValueError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
            "terminal_authority": False,
        }

    atom_id = _condition_atom(
        source_id=source_id,
        scope_id=str(p["scope_id"]),
        field_name=field_name,
        operator=operator,
        literal=literal,
        typed_context_sha256_value=actual_digest,
    )
    atom = {"op": "ATOM", "id": atom_id}
    proved_constraint = atom if holds else {"op": "NOT", "arg": atom}

    return {
        "schema": SCHEMA,
        "status": "PROVED_TRUE" if holds else "PROVED_FALSE",
        "condition_holds": holds,
        "scope_id": p["scope_id"],
        "condition_span": [start, end],
        "condition_text_sha256": sha256(condition_text.encode("utf-8")).hexdigest(),
        "schema_id": schema_id,
        "field_name": field_name,
        "field_type": required_type,
        "operator": operator,
        "literal": literal,
        "typed_context_sha256": actual_digest,
        "condition_atom_id": atom_id,
        "proved_constraint": proved_constraint,
        "terminal_authority": False,
        "soundness_boundary": (
            "ONLY_LITERAL_FIELD_NAMES_AND_THE_DECLARED_CONTROLLED_BOOLEAN_OR_DECIMAL_GRAMMAR_ARE_BOUND;"
            "AUTHORITY_OF_THE_EXPECTED_TYPED_CONTEXT_DIGEST_REMAINS_EXTERNAL_TO_THIS_MODULE"
        ),
    }
