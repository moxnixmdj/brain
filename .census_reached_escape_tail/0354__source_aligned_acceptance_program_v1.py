"""Source-aligned compiler from controlled structured requirements to typed acceptance programs.

Supported full-sentence requirement forms:
- FIELD must be at least NUMBER
- FIELD must be at most NUMBER
- FIELD must be exactly NUMBER
- FIELD must equal NUMBER
- FIELD must be true|false
- FIELD must equal "ENUM_LITERAL"

FIELD must be an exact declared candidate-field identifier. Every normative sentence
in the source must be either compiled by this grammar or explicitly left unresolved;
no normative sentence is silently ignored. Non-normative narrative may be ignored.

This is a bounded source-to-verifier compiler, not general natural-language semantics.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any, Mapping

from canonical.runtime.source_contract_compiler import NORMATIVE_RE
from canonical.runtime.typed_acceptance_program_v1 import PROGRAM_SCHEMA

SCHEMA = "PROJECT_BRAIN_SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_COMPILER_V1"
_FIELD = r"(?P<field>[A-Za-z_][A-Za-z0-9_]*)"
_NUM = r"(?P<num>-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?)"

_PATTERNS = (
    (re.compile(rf"^\s*{_FIELD}\s+must\s+be\s+at\s+least\s+{_NUM}\s*[.!]?\s*$", re.I), "GE"),
    (re.compile(rf"^\s*{_FIELD}\s+must\s+be\s+at\s+most\s+{_NUM}\s*[.!]?\s*$", re.I), "LE"),
    (re.compile(rf"^\s*{_FIELD}\s+must\s+be\s+exactly\s+{_NUM}\s*[.!]?\s*$", re.I), "EQ_NUM"),
    (re.compile(rf"^\s*{_FIELD}\s+must\s+equal\s+{_NUM}\s*[.!]?\s*$", re.I), "EQ_NUM"),
    (re.compile(rf"^\s*{_FIELD}\s+must\s+be\s+(?P<bool>true|false)\s*[.!]?\s*$", re.I), "EQ_BOOL"),
    (re.compile(rf'^\s*{_FIELD}\s+must\s+equal\s+"(?P<enum>[^"\n]+)"\s*[.!]?\s*$', re.I), "EQ_ENUM"),
)


def _segments(text: str) -> list[tuple[int, int, str]]:
    out = []
    for m in re.finditer(r"[^.!?\n]+(?:[.!?]+|\n|$)", text):
        s, e = m.span()
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if s < e:
            out.append((s, e, text[s:e]))
    return out


def _const_number(value: str, dimension: str) -> dict[str, Any]:
    return {"op": "const", "type": "number", "dimension": dimension, "value": float(value)}


def compile_program(
    source_text: str,
    *,
    source_id: str,
    field_schema: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    if not isinstance(source_text, str) or not source_text.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["SOURCE_TEXT_MISSING"], "terminal_authority": False}
    if not isinstance(source_id, str) or not source_id.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["SOURCE_ID_MISSING"], "terminal_authority": False}
    if not isinstance(field_schema, Mapping) or not field_schema:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["FIELD_SCHEMA_INVALID"], "terminal_authority": False}

    declarations = []
    normalized_schema: dict[str, dict[str, str]] = {}
    errors = []
    for fid, row in field_schema.items():
        if not isinstance(fid, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", fid):
            errors.append("FIELD_ID_INVALID:" + str(fid))
            continue
        if not isinstance(row, Mapping):
            errors.append("FIELD_SCHEMA_ROW_INVALID:" + fid)
            continue
        typ = str(row.get("type") or "")
        dim = str(row.get("dimension") or "")
        if typ not in {"number", "integer", "boolean", "enum"} or not dim:
            errors.append("FIELD_SCHEMA_TYPE_OR_DIMENSION_INVALID:" + fid)
            continue
        normalized_schema[fid] = {"type": typ, "dimension": dim}
        declarations.append({"id": fid, "type": typ, "dimension": dim, "source": "candidate"})
    if errors:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": sorted(set(errors)), "terminal_authority": False}

    expressions = []
    compiled = []
    unresolved = []
    ignored = []

    for idx, (start, end, segment) in enumerate(_segments(source_text)):
        matched = None
        mode = None
        for regex, candidate_mode in _PATTERNS:
            m = regex.fullmatch(segment)
            if m:
                matched = m
                mode = candidate_mode
                break

        if matched is None:
            row = {
                "segment_index": idx,
                "span": [start, end],
                "segment_sha256": sha256(segment.encode("utf-8")).hexdigest(),
            }
            if NORMATIVE_RE.search(segment):
                row["reason"] = "NORMATIVE_SENTENCE_OUTSIDE_CONTROLLED_ACCEPTANCE_GRAMMAR"
                unresolved.append(row)
            else:
                ignored.append(row)
            continue

        field = matched.group("field")
        meta = normalized_schema.get(field)
        if meta is None:
            unresolved.append({
                "segment_index": idx,
                "span": [start, end],
                "segment_sha256": sha256(segment.encode("utf-8")).hexdigest(),
                "reason": "SOURCE_FIELD_NOT_IN_DECLARED_SCHEMA:" + field,
            })
            continue

        left = {"op": "ref", "id": field}
        typ = meta["type"]
        dim = meta["dimension"]
        if mode in {"GE", "LE", "EQ_NUM"}:
            if typ not in {"number", "integer"}:
                unresolved.append({
                    "segment_index": idx,
                    "span": [start, end],
                    "segment_sha256": sha256(segment.encode("utf-8")).hexdigest(),
                    "reason": "NUMERIC_REQUIREMENT_ON_NONNUMERIC_FIELD:" + field,
                })
                continue
            right = _const_number(matched.group("num"), dim)
            op = {"GE": "ge", "LE": "le", "EQ_NUM": "eq"}[mode]
            expr = {"op": op, "left": left, "right": right}
            literal = matched.group("num")
        elif mode == "EQ_BOOL":
            if typ != "boolean" or dim != "dimensionless":
                unresolved.append({
                    "segment_index": idx,
                    "span": [start, end],
                    "segment_sha256": sha256(segment.encode("utf-8")).hexdigest(),
                    "reason": "BOOLEAN_REQUIREMENT_ON_NONBOOLEAN_FIELD:" + field,
                })
                continue
            value = matched.group("bool").lower() == "true"
            right = {"op": "const", "type": "boolean", "dimension": "dimensionless", "value": value}
            expr = {"op": "eq", "left": left, "right": right}
            literal = str(value).lower()
        else:
            if typ != "enum" or dim != "dimensionless":
                unresolved.append({
                    "segment_index": idx,
                    "span": [start, end],
                    "segment_sha256": sha256(segment.encode("utf-8")).hexdigest(),
                    "reason": "ENUM_REQUIREMENT_ON_NONENUM_FIELD:" + field,
                })
                continue
            value = matched.group("enum")
            right = {"op": "const", "type": "enum", "dimension": "dimensionless", "value": value}
            expr = {"op": "eq", "left": left, "right": right}
            literal = value

        expressions.append(expr)
        compiled.append({
            "segment_index": idx,
            "span": [start, end],
            "segment_sha256": sha256(segment.encode("utf-8")).hexdigest(),
            "field": field,
            "mode": mode,
            "literal": literal,
        })

    if unresolved:
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "source_id": source_id,
            "source_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
            "compiled_requirements": compiled,
            "unresolved_normative_requirements": unresolved,
            "ignored_non_normative_segments": ignored,
            "terminal_authority": False,
        }
    if not expressions:
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "source_id": source_id,
            "source_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
            "compiled_requirements": [],
            "unresolved_normative_requirements": [],
            "reason": "NO_CONTROLLED_ACCEPTANCE_REQUIREMENTS",
            "terminal_authority": False,
        }

    accept_when = expressions[0] if len(expressions) == 1 else {"op": "and", "args": expressions}
    program = {
        "schema": PROGRAM_SCHEMA,
        "fields": sorted(declarations, key=lambda x: x["id"]),
        "accept_when": accept_when,
    }
    return {
        "schema": SCHEMA,
        "status": "COMPILED",
        "source_id": source_id,
        "source_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
        "compiled_requirements": compiled,
        "unresolved_normative_requirements": [],
        "ignored_non_normative_segments": ignored,
        "acceptance_program": program,
        "terminal_authority": False,
        "soundness_boundary": (
            "ONLY_EXACT_FIELD_IDS_AND_THE_CONTROLLED_MUST_CONSTRAINT_GRAMMAR_ARE_COMPILED;"
            "ANY_OTHER_NORMATIVE_SENTENCE_BLOCKS_INSTEAD_OF_BEING_IGNORED"
        ),
    }
