"""Independent verifier for explicit-definition controlled Finance UNLESS."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FINANCE_EXPLICIT_DEFINITION_UNLESS_VERIFY_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_EXPLICIT_DEFINITION_UNLESS_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_EXPLICIT_DEFINITION_UNLESS_RESULT_V1"

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_DEF = re.compile(
    r"^\s*(?P<term>[A-Za-z][A-Za-z0-9 _-]{0,80}?)\s+means\s+(?P<value>.+?)\s*\.?\s*$",
    re.I,
)
_UNLESS = re.compile(r"\bunless\b", re.I)
_FIELD = r"(?P<field>[A-Za-z_][A-Za-z0-9_]*)"
_NUM = r"(?P<num>-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?)"
_BOOL = re.compile(rf"^\s*{_FIELD}\s*(?:is\s+|=\s*)(?P<bool>true|false)\s*$", re.I)
_NUM_EQ = re.compile(rf"^\s*{_FIELD}\s*(?:is\s+|=\s*){_NUM}\s*$", re.I)
_MIN = re.compile(rf"^\s*{_FIELD}\s+is\s+at\s+least\s+{_NUM}\s*$", re.I)
_MAX = re.compile(rf"^\s*{_FIELD}\s+is\s+at\s+most\s+{_NUM}\s*$", re.I)
_EXACT = re.compile(rf"^\s*{_FIELD}\s+is\s+exactly\s+{_NUM}\s*$", re.I)
_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def _canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and (text[end - 1].isspace() or text[end - 1] in ".,;:"):
        end -= 1
    return start, end


def _decimal(v: Any) -> Decimal:
    if not isinstance(v, str) or _DECIMAL.fullmatch(v) is None:
        raise ValueError("DECIMAL_STRING_INVALID")
    try:
        out = Decimal(v)
    except InvalidOperation as exc:
        raise ValueError("DECIMAL_STRING_INVALID") from exc
    if not out.is_finite():
        raise ValueError("DECIMAL_STRING_NONFINITE")
    return out


def _scope_id(source_id: str, text: str, match: re.Match[str]) -> tuple[str, tuple[int, int], tuple[int, int]]:
    left = _trim(text, 0, match.start())
    right = _trim(text, match.end(), len(text))
    material = (
        f"{source_id}\0{match.start()}\0{match.end()}\0"
        f"CONDITIONAL_UNLESS\0{text[match.start():match.end()].lower()}"
    )
    operator_id = "OP-" + sha256(material.encode("utf-8")).hexdigest()[:20]
    scope_raw = f"{source_id}\0UNLESS\0{operator_id}\0{(left, right)!r}".encode("utf-8")
    return "SCOPE-" + sha256(scope_raw).hexdigest()[:20], left, right


def _atom(
    source_id: str,
    scope_id: str,
    field: str,
    operator: str,
    literal: str,
    digest: str,
) -> str:
    payload = {
        "source_id": source_id,
        "scope_id": scope_id,
        "field_name": field,
        "operator": operator,
        "literal": literal,
        "typed_context_sha256": digest,
    }
    return "CERTIFIED_CONDITION::" + sha256(_canon(payload).encode("utf-8")).hexdigest()


def verify(case: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(case, Mapping) or case.get("schema") != INPUT_SCHEMA:
        return {
            "schema": SCHEMA, "verified": False, "errors": ["CASE_SCHEMA_INVALID"],
            "producer_independent": True, "model_dependency_count": 0,
            "terminal_authority": False,
        }
    if not isinstance(result, Mapping) or result.get("schema") != RESULT_SCHEMA:
        return {
            "schema": SCHEMA, "verified": False, "errors": ["RESULT_SCHEMA_INVALID"],
            "producer_independent": True, "model_dependency_count": 0,
            "terminal_authority": False,
        }

    source_id = case.get("source_id")
    source_text = case.get("source_text")
    ctx = case.get("typed_context")
    expected_digest = case.get("typed_context_sha256")
    if not isinstance(source_id, str) or not source_id.strip():
        errors.append("SOURCE_ID_INVALID")
        source_id = ""
    if not isinstance(source_text, str) or not source_text.strip():
        errors.append("SOURCE_TEXT_INVALID")
        source_text = ""
    if not isinstance(ctx, Mapping):
        errors.append("TYPED_CONTEXT_INVALID")
        ctx = {}
    digest = sha256(_canon(ctx).encode("utf-8")).hexdigest()
    if not isinstance(expected_digest, str) or expected_digest != digest:
        errors.append("TYPED_CONTEXT_DIGEST_MISMATCH")

    sentences = [x.strip() for x in _SENTENCE_SPLIT.split(source_text) if x.strip()]
    if len(sentences) != 2:
        errors.append("EXACTLY_TWO_SOURCE_SENTENCES_REQUIRED")
    else:
        definition_sentence, rule_text = sentences
        dm = _DEF.fullmatch(definition_sentence)
        if dm is None:
            errors.append("EXPLICIT_MEANS_DEFINITION_REQUIRED")
        else:
            term = " ".join(dm.group("term").split()).strip()
            definition = " ".join(dm.group("value").rstrip(".").split()).strip()
            matches = list(_UNLESS.finditer(rule_text))
            if len(matches) != 1:
                errors.append("EXACT_SINGLE_UNLESS_RULE_REQUIRED")
            else:
                um = matches[0]
                rule_source_id = source_id.strip() + "#rule"
                rule_scope, left, right = _scope_id(rule_source_id, rule_text, um)
                ordinary = rule_text[left[0]:left[1]]
                reference = rule_text[right[0]:right[1]]
                if reference.casefold() != term.casefold():
                    errors.append("UNLESS_EXCEPTION_NOT_EXACT_DEFINED_TERM")
                else:
                    expanded = ordinary + " unless " + definition + "."
                    ems = list(_UNLESS.finditer(expanded))
                    if len(ems) != 1:
                        errors.append("EXPANDED_UNLESS_INVALID")
                    else:
                        expanded_source_id = source_id.strip() + "#expanded"
                        expanded_scope, _, eright = _scope_id(
                            expanded_source_id, expanded, ems[0]
                        )
                        condition_text = expanded[eright[0]:eright[1]]
                        match = _BOOL.fullmatch(condition_text)
                        field = operator = literal = required = ""
                        holds = None
                        if match:
                            field = match.group("field")
                            literal = match.group("bool").lower()
                            operator = "BOOL_EQ"
                            required = "BOOL"
                        else:
                            for rx, op in (
                                (_MIN, "DECIMAL_GE"),
                                (_MAX, "DECIMAL_LE"),
                                (_EXACT, "DECIMAL_EQ"),
                                (_NUM_EQ, "DECIMAL_EQ"),
                            ):
                                match = rx.fullmatch(condition_text)
                                if match:
                                    field = match.group("field")
                                    literal = match.group("num")
                                    operator = op
                                    required = "DECIMAL_STRING"
                                    break
                        if not field:
                            errors.append("DEFINED_CONDITION_OUTSIDE_TYPED_GRAMMAR")
                        else:
                            fields = ctx.get("fields") if isinstance(ctx, Mapping) else None
                            row = fields.get(field) if isinstance(fields, Mapping) else None
                            if not isinstance(row, Mapping):
                                errors.append("DEFINED_FIELD_NOT_PRESENT")
                            elif row.get("type") != required:
                                errors.append("DEFINED_FIELD_TYPE_MISMATCH")
                            else:
                                try:
                                    value = row.get("value")
                                    if operator == "BOOL_EQ":
                                        if not isinstance(value, bool):
                                            raise ValueError("BOOL_VALUE_INVALID")
                                        holds = value is (literal == "true")
                                    else:
                                        av = _decimal(value)
                                        lv = _decimal(literal)
                                        if operator == "DECIMAL_GE":
                                            holds = av >= lv
                                        elif operator == "DECIMAL_LE":
                                            holds = av <= lv
                                        else:
                                            holds = av == lv
                                except ValueError as exc:
                                    errors.append(str(exc))

                        if holds is not None:
                            atom = _atom(
                                expanded_source_id,
                                expanded_scope,
                                field,
                                operator,
                                literal,
                                digest,
                            )
                            constraint = (
                                {"op": "ATOM", "id": atom}
                                if holds
                                else {"op": "NOT", "arg": {"op": "ATOM", "id": atom}}
                            )
                            selected_branch = (
                                "EXCEPTION_BRANCH" if holds else "ORDINARY_BRANCH"
                            )
                            local_span = right if holds else left
                            selected_text = rule_text[local_span[0]:local_span[1]]
                            rule_start = source_text.find(rule_text)
                            if (
                                rule_start < 0
                                or source_text.find(rule_text, rule_start + 1) >= 0
                            ):
                                errors.append("RULE_SENTENCE_NOT_UNIQUE")
                            else:
                                expected = {
                                    "source_id": source_id.strip(),
                                    "source_text_sha256": _sha(source_text),
                                    "typed_context_sha256": digest,
                                    "definition_term": term,
                                    "definition_term_sha256": _sha(term),
                                    "definition_text_sha256": _sha(definition),
                                    "reference_sentence_index": 1,
                                    "reference_text_sha256": _sha(reference),
                                    "rule_text_sha256": _sha(rule_text),
                                    "expanded_rule_sha256": _sha(expanded),
                                    "rule_scope_id": rule_scope,
                                    "condition_holds": holds,
                                    "condition_atom_id": atom,
                                    "proved_constraint": constraint,
                                    "field_name": field,
                                    "field_type": required,
                                    "operator": operator,
                                    "literal": literal,
                                    "selected_branch": selected_branch,
                                    "selected_span": [
                                        rule_start + local_span[0],
                                        rule_start + local_span[1],
                                    ],
                                    "selected_text": selected_text,
                                    "selected_text_sha256": _sha(selected_text),
                                }
                                for key, value in expected.items():
                                    if result.get(key) != value:
                                        errors.append("MISMATCH:" + key)

    if result.get("model_dependency_count") != 0:
        errors.append("MODEL_DEPENDENCY_NONZERO")
    if result.get("external_world_truth_claimed") is not False:
        errors.append("EXTERNAL_WORLD_TRUTH_BOUNDARY_VIOLATION")
    if result.get("general_ontology_mapping_claimed") is not False:
        errors.append("GENERAL_ONTOLOGY_BOUNDARY_VIOLATION")
    if result.get("reference_resolution_authority") != (
        "EXPLICIT_NAMED_DEFINITION_TO_EXACT_LATER_NAMED_REFERENCE_ONLY"
    ):
        errors.append("REFERENCE_AUTHORITY_BOUNDARY_MISMATCH")

    return {
        "schema": SCHEMA,
        "verified": not errors,
        "status": (
            "PASS__INDEPENDENT_EXPLICIT_DEFINITION_TYPED_UNLESS_RECOMPUTATION"
            if not errors else "FAIL_CLOSED"
        ),
        "errors": sorted(set(errors)),
        "producer_independent": True,
        "model_dependency_count": 0,
        "terminal_authority": False,
        "boundary": (
            "EXACT_TWO_SENTENCE_MEANS_DEFINITION_PLUS_EXACT_NAMED_UNLESS_REFERENCE;"
            "DEFINITION_MUST_BE_LITERAL_TYPED_BOOLEAN_OR_DECIMAL_CONDITION;"
            "NO_GENERAL_COREFERENCE_ONTOLOGY_OR_EXTERNAL_WORLD_TRUTH"
        ),
    }
