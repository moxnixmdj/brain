"""Certified explicit-definition to typed-field condition evaluator.

This module extends the controlled UNLESS fragment with one narrow denotation rule:

    DEFINED_TERM means TYPED_FIELD_NAME.
    ... unless DEFINED_TERM <controlled operator> LITERAL.

Only explicit named definitions accepted by explicit_definition_reference_graph are
used. The definition RHS must be exactly one typed-context field identifier. No
synonymy, paraphrase, ontology inference, abbreviation expansion, or world knowledge
is performed.

Supported condition forms after denotation binding:
- TERM is true|false
- TERM = true|false
- TERM is NUMBER
- TERM = NUMBER
- TERM is at least NUMBER
- TERM is at most NUMBER
- TERM is exactly NUMBER

The source scope, explicit definition graph, content-addressed typed context, and
exact boolean/decimal evaluation are all recomputed. This module has no terminal
authority.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from canonical.runtime.certified_scope_fragment_v1 import parse_scope
from canonical.runtime.explicit_definition_reference_graph import compile_reference_graph
from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256

SCHEMA = "BRAIN_CERTIFIED_DEFINED_TERM_TYPED_CONDITION_V1"

_FIELD_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_NUM = r"(?P<num>-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?)"
_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


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


def _condition_atom(payload: Mapping[str, Any]) -> str:
    return "CERTIFIED_DEFINED_CONDITION::" + sha256(
        _canon(payload).encode("utf-8")
    ).hexdigest()


def _parse_condition_for_term(condition_text: str, term: str) -> dict[str, Any] | None:
    t = re.escape(term)
    patterns = [
        (re.compile(rf"^\s*{t}\s*(?:is\s+|=\s*)(?P<bool>true|false)\s*$", re.I), "BOOL_EQ"),
        (re.compile(rf"^\s*{t}\s+is\s+at\s+least\s+{_NUM}\s*$", re.I), "DECIMAL_GE"),
        (re.compile(rf"^\s*{t}\s+is\s+at\s+most\s+{_NUM}\s*$", re.I), "DECIMAL_LE"),
        (re.compile(rf"^\s*{t}\s+is\s+exactly\s+{_NUM}\s*$", re.I), "DECIMAL_EQ"),
        (re.compile(rf"^\s*{t}\s*(?:is\s+|=\s*){_NUM}\s*$", re.I), "DECIMAL_EQ"),
    ]
    for regex, op in patterns:
        m = regex.fullmatch(condition_text)
        if not m:
            continue
        if op == "BOOL_EQ":
            literal = m.group("bool").lower()
            return {
                "operator": op,
                "literal": literal,
                "required_type": "BOOL",
                "expected_bool": literal == "true",
            }
        return {
            "operator": op,
            "literal": m.group("num"),
            "required_type": "DECIMAL_STRING",
        }
    return None


def evaluate_defined_unless_condition(
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

    graph = compile_reference_graph(source_text)
    if graph.get("status") == "FAIL_CLOSED":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["EXPLICIT_DEFINITION_GRAPH_FAIL_CLOSED", *(graph.get("errors") or [])],
            "definition_graph": graph,
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

    candidates: list[dict[str, Any]] = []
    for row in graph.get("definitions") or []:
        if not isinstance(row, Mapping):
            continue
        term = row.get("term")
        target = row.get("definition")
        if (
            isinstance(term, str) and term.strip()
            and isinstance(target, str)
            and _FIELD_ID.fullmatch(target.strip()) is not None
        ):
            parsed = _parse_condition_for_term(condition_text, term.strip())
            if parsed is not None:
                candidates.append({
                    "term": term.strip(),
                    "field_name": target.strip(),
                    "definition_sentence_index": row.get("sentence_index"),
                    **parsed,
                })

    if not candidates:
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "reason": "NO_EXPLICIT_DEFINED_TERM_BINDS_EXCEPTION_CONDITION_TO_TYPED_FIELD",
            "condition_span": [start, end],
            "condition_text_sha256": sha256(condition_text.encode("utf-8")).hexdigest(),
            "definition_graph": graph,
            "terminal_authority": False,
        }
    if len(candidates) != 1:
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "reason": "MULTIPLE_DEFINED_TERM_BINDINGS_MATCH_EXCEPTION_CONDITION",
            "candidate_count": len(candidates),
            "terminal_authority": False,
        }

    binding = candidates[0]
    schema_id = typed_context.get("schema_id")
    fields = typed_context.get("fields")
    if not isinstance(schema_id, str) or not schema_id.strip() or not isinstance(fields, Mapping):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["TYPED_CONTEXT_SCHEMA_INVALID"], "terminal_authority": False}

    field_name = binding["field_name"]
    row = fields.get(field_name)
    if not isinstance(row, Mapping):
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "reason": "DEFINED_FIELD_NOT_PRESENT_IN_TYPED_CONTEXT",
            "defined_term": binding["term"],
            "field_name": field_name,
            "terminal_authority": False,
        }

    required_type = binding["required_type"]
    if row.get("type") != required_type:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [f"TYPED_FIELD_TYPE_MISMATCH:{field_name}:{row.get('type')}!={required_type}"],
            "terminal_authority": False,
        }

    actual_value = row.get("value")
    operator = binding["operator"]
    literal = binding["literal"]
    try:
        if operator == "BOOL_EQ":
            if not isinstance(actual_value, bool):
                raise ValueError("BOOL_VALUE_INVALID")
            holds = actual_value is binding["expected_bool"]
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

    payload = {
        "source_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
        "source_id": source_id,
        "scope_id": p["scope_id"],
        "defined_term": binding["term"],
        "definition_sentence_index": binding["definition_sentence_index"],
        "field_name": field_name,
        "operator": operator,
        "literal": literal,
        "typed_context_sha256": actual_digest,
    }
    atom_id = _condition_atom(payload)
    atom = {"op": "ATOM", "id": atom_id}

    return {
        "schema": SCHEMA,
        "status": "PROVED_TRUE" if holds else "PROVED_FALSE",
        "condition_holds": holds,
        "scope_id": p["scope_id"],
        "condition_span": [start, end],
        "condition_text_sha256": sha256(condition_text.encode("utf-8")).hexdigest(),
        "defined_term": binding["term"],
        "definition_sentence_index": binding["definition_sentence_index"],
        "field_name": field_name,
        "field_type": required_type,
        "operator": operator,
        "literal": literal,
        "typed_context_sha256": actual_digest,
        "condition_atom_id": atom_id,
        "proved_constraint": atom if holds else {"op": "NOT", "arg": atom},
        "definition_graph": graph,
        "terminal_authority": False,
        "soundness_boundary": (
            "DENOTATION_IS_PROVED_ONLY_BY_AN_EXPLICIT_NAMED_DEFINITION_WHOSE_RHS_IS_EXACTLY_ONE_TYPED_FIELD_IDENTIFIER;"
            "NO_SYNONYM_PARAPHRASE_ONTOLOGY_ABBREVIATION_OR_WORLD_KNOWLEDGE_INFERENCE"
        ),
    }
