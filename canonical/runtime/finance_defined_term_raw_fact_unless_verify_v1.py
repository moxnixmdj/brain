"""Producer-independent verifier for source-defined raw-fact finance UNLESS.

The verifier does not import the producer, the defined-term evaluator, the raw
typed-context compiler, the certified scope parser, or semantic proof v6.
It independently reparses:
- strict raw JSON with duplicate-key rejection,
- the explicit source definition,
- the single UNLESS condition,
- typed field/value semantics,
- scope/atom identities,
- branch selection and hashes.

It reuses only the previously verified structural finance source-coverage gate.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from canonical.runtime.finance_proof_carrying_source_gate_v1 import (
    verify_source_semantic_coverage,
)

SCHEMA = "PROJECT_BRAIN_FINANCE_DEFINED_TERM_RAW_FACT_UNLESS_VERIFY_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_DEFINED_TERM_RAW_FACT_UNLESS_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_DEFINED_TERM_RAW_FACT_UNLESS_RESULT_V1"

_FIELD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_UNLESS = re.compile(r"\bunless\b", re.I)
_DEF = re.compile(
    r"""^\s*(?:for purposes of this [^,]+,\s*)?["']?"""
    r"""(?P<term>[A-Za-z][A-Za-z0-9 _-]{0,80}?)["']?\s+"""
    r"""(?:means|refers to|is defined as)\s+(?P<target>.+?)\s*$""",
    re.I,
)
_NUM = r"(?P<num>-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?)"


class VerifyError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _pairs_no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise VerifyError("DUPLICATE_JSON_KEY:" + str(key))
        out[key] = value
    return out


def _strict_context(raw_source: Any) -> tuple[dict[str, Any], str, str]:
    if isinstance(raw_source, str):
        raw = raw_source.encode("utf-8")
    elif isinstance(raw_source, bytes):
        raw = raw_source
    else:
        raise VerifyError("RAW_SOURCE_MUST_BE_TEXT_OR_BYTES")
    if not raw:
        raise VerifyError("RAW_SOURCE_EMPTY")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerifyError("RAW_SOURCE_NOT_UTF8") from exc
    try:
        document = json.loads(text, object_pairs_hook=_pairs_no_duplicates)
    except VerifyError:
        raise
    except Exception as exc:
        raise VerifyError("RAW_SOURCE_JSON_INVALID") from exc

    if not isinstance(document, Mapping) or set(document) != {"schema_id", "fields"}:
        raise VerifyError("TYPED_CONTEXT_TOP_LEVEL_INVALID")
    schema_id = document.get("schema_id")
    fields = document.get("fields")
    if not isinstance(schema_id, str) or not schema_id.strip():
        raise VerifyError("SCHEMA_ID_INVALID")
    if not isinstance(fields, Mapping) or not fields:
        raise VerifyError("FIELDS_INVALID_OR_EMPTY")

    normalized = {}
    for name, row in fields.items():
        if not isinstance(name, str) or _FIELD.fullmatch(name) is None:
            raise VerifyError("FIELD_NAME_INVALID:" + str(name))
        if not isinstance(row, Mapping) or set(row) != {"type", "value"}:
            raise VerifyError("FIELD_ROW_INVALID:" + name)
        kind = row.get("type")
        value = row.get("value")
        if kind == "BOOL":
            ok = isinstance(value, bool)
        elif kind == "INT":
            ok = isinstance(value, int) and not isinstance(value, bool)
        elif kind == "STRING":
            ok = isinstance(value, str)
        elif kind == "DECIMAL_STRING":
            ok = isinstance(value, str) and _DECIMAL.fullmatch(value) is not None
        else:
            raise VerifyError("FIELD_TYPE_UNSUPPORTED:" + name)
        if not ok:
            raise VerifyError("FIELD_VALUE_TYPE_MISMATCH:" + name)
        normalized[name] = {"type": kind, "value": value}

    context = {"schema_id": schema_id.strip(), "fields": normalized}
    return (
        context,
        sha256(_canon(context).encode("utf-8")).hexdigest(),
        sha256(raw).hexdigest(),
    )


def _sentences(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n+", text) if x.strip()]


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and (text[end - 1].isspace() or text[end - 1] in ".,;:"):
        end -= 1
    return start, end


def _condition_for_term(condition: str, term: str) -> dict[str, Any] | None:
    t = re.escape(term)
    patterns = [
        (re.compile(rf"^\s*{t}\s*(?:is\s+|=\s*)(?P<bool>true|false)\s*$", re.I), "BOOL_EQ"),
        (re.compile(rf"^\s*{t}\s+is\s+at\s+least\s+{_NUM}\s*$", re.I), "DECIMAL_GE"),
        (re.compile(rf"^\s*{t}\s+is\s+at\s+most\s+{_NUM}\s*$", re.I), "DECIMAL_LE"),
        (re.compile(rf"^\s*{t}\s+is\s+exactly\s+{_NUM}\s*$", re.I), "DECIMAL_EQ"),
        (re.compile(rf"^\s*{t}\s*(?:is\s+|=\s*){_NUM}\s*$", re.I), "DECIMAL_EQ"),
    ]
    for rx, op in patterns:
        m = rx.fullmatch(condition)
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


def _decimal(value: Any) -> Decimal:
    if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
        raise VerifyError("DECIMAL_STRING_INVALID")
    try:
        out = Decimal(value)
    except InvalidOperation as exc:
        raise VerifyError("DECIMAL_STRING_INVALID") from exc
    if not out.is_finite():
        raise VerifyError("DECIMAL_STRING_NONFINITE")
    return out


def _scope_and_condition(
    text: str,
    source_id: str,
) -> tuple[dict[str, Any], str]:
    matches = list(_UNLESS.finditer(text))
    if len(matches) != 1:
        raise VerifyError("EXACTLY_ONE_UNLESS_REQUIRED")
    m = matches[0]
    left = _trim(text, 0, m.start())
    right = _trim(text, m.end(), len(text))
    if left[0] >= left[1] or right[0] >= right[1]:
        raise VerifyError("UNLESS_BRANCH_EMPTY")

    operator_material = (
        f"{source_id}\0{m.start()}\0{m.end()}\0"
        f"CONDITIONAL_UNLESS\0{text[m.start():m.end()].lower()}"
    )
    operator_id = "OP-" + sha256(operator_material.encode("utf-8")).hexdigest()[:20]
    scope_raw = f"{source_id}\0UNLESS\0{operator_id}\0{(left, right)!r}".encode("utf-8")
    scope_id = "SCOPE-" + sha256(scope_raw).hexdigest()[:20]
    return {
        "scope_id": scope_id,
        "left_span": left,
        "right_span": right,
    }, text[right[0]:right[1]]


def _binding(
    source_text: str,
    condition: str,
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    definitions = []
    seen = {}
    for i, sentence in enumerate(_sentences(source_text)):
        m = _DEF.fullmatch(sentence.rstrip("."))
        if not m:
            continue
        term = " ".join(m.group("term").split()).strip()
        target = " ".join(m.group("target").split()).strip()
        key = term.casefold()
        prior = seen.get(key)
        if prior is not None and prior.casefold() != target.casefold():
            raise VerifyError("CONFLICTING_DEFINITION:" + term)
        seen[key] = target
        if _FIELD.fullmatch(target) is not None:
            parsed = _condition_for_term(condition, term)
            if parsed is not None:
                definitions.append({
                    "defined_term": term,
                    "field_name": target,
                    "definition_sentence_index": i,
                    **parsed,
                })
    if len(definitions) != 1:
        raise VerifyError(
            "DEFINED_TERM_BINDING_COUNT:" + str(len(definitions))
        )
    binding = definitions[0]
    row = fields.get(binding["field_name"])
    if not isinstance(row, Mapping):
        raise VerifyError("DEFINED_FIELD_NOT_PRESENT_IN_TYPED_CONTEXT")
    if row.get("type") != binding["required_type"]:
        raise VerifyError("FIELD_TYPE_MISMATCH")
    return binding


def _holds(binding: Mapping[str, Any], fields: Mapping[str, Any]) -> bool:
    value = fields[binding["field_name"]]["value"]
    op = binding["operator"]
    if op == "BOOL_EQ":
        if not isinstance(value, bool):
            raise VerifyError("BOOL_VALUE_INVALID")
        return value is binding["expected_bool"]
    actual = _decimal(value)
    literal = _decimal(binding["literal"])
    if op == "DECIMAL_GE":
        return actual >= literal
    if op == "DECIMAL_LE":
        return actual <= literal
    return actual == literal


def verify(case: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    base = {
        "schema": SCHEMA,
        "verified": False,
        "producer_independent": True,
        "producer_module_imported": False,
        "defined_term_evaluator_imported": False,
        "raw_context_compiler_imported": False,
        "scope_parser_imported": False,
        "model_dependency_count": 0,
        "terminal_authority": False,
    }
    try:
        if not isinstance(case, Mapping) or case.get("schema") != INPUT_SCHEMA:
            raise VerifyError("CASE_SCHEMA_INVALID")
        if not isinstance(result, Mapping) or result.get("schema") != RESULT_SCHEMA:
            raise VerifyError("RESULT_SCHEMA_INVALID")

        source_id = case.get("policy_source_id")
        text = case.get("policy_source_text")
        fact_source_id = case.get("fact_source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            raise VerifyError("POLICY_SOURCE_ID_INVALID")
        if not isinstance(text, str) or not text.strip():
            raise VerifyError("POLICY_SOURCE_TEXT_INVALID")
        if not isinstance(fact_source_id, str) or not fact_source_id.strip():
            raise VerifyError("FACT_SOURCE_ID_INVALID")
        source_id = source_id.strip()
        fact_source_id = fact_source_id.strip()

        coverage = verify_source_semantic_coverage({
            "source_id": source_id,
            "source_text": text,
            "source_coverage_manifest": case.get("source_coverage_manifest"),
            "source_semantic_coverage": case.get("source_semantic_coverage"),
        })
        if coverage.get("pass") is not True:
            raise VerifyError(
                "FINANCE_SOURCE_SEMANTIC_COVERAGE_NOT_PROVED:"
                + ",".join(coverage.get("errors") or [])
            )

        context, context_sha, fact_sha = _strict_context(case.get("fact_source"))
        scope, condition = _scope_and_condition(text, source_id)
        binding = _binding(text, condition, context["fields"])
        holds = _holds(binding, context["fields"])

        atom_payload = {
            "source_sha256": _sha(text),
            "source_id": source_id,
            "scope_id": scope["scope_id"],
            "defined_term": binding["defined_term"],
            "definition_sentence_index": binding["definition_sentence_index"],
            "field_name": binding["field_name"],
            "operator": binding["operator"],
            "literal": binding["literal"],
            "typed_context_sha256": context_sha,
        }
        atom_id = "CERTIFIED_DEFINED_CONDITION::" + sha256(
            _canon(atom_payload).encode("utf-8")
        ).hexdigest()
        constraint = (
            {"op": "ATOM", "id": atom_id}
            if holds
            else {"op": "NOT", "arg": {"op": "ATOM", "id": atom_id}}
        )
        span = scope["right_span"] if holds else scope["left_span"]
        selected = text[span[0]:span[1]]

        expected = {
            "policy_source_id": source_id,
            "policy_source_text_sha256": _sha(text),
            "fact_source_id": fact_source_id,
            "fact_source_sha256": fact_sha,
            "typed_context_sha256": context_sha,
            "scope_id": scope["scope_id"],
            "relation": "UNLESS",
            "condition_holds": holds,
            "condition_atom_id": atom_id,
            "proved_constraint": constraint,
            "defined_term": binding["defined_term"],
            "definition_sentence_index": binding["definition_sentence_index"],
            "field_name": binding["field_name"],
            "field_type": binding["required_type"],
            "operator": binding["operator"],
            "literal": binding["literal"],
            "selected_branch": "EXCEPTION_BRANCH" if holds else "ORDINARY_BRANCH",
            "selected_span": [span[0], span[1]],
            "selected_text": selected,
            "selected_text_sha256": _sha(selected),
        }
        for key, value in expected.items():
            if result.get(key) != value:
                errors.append("MISMATCH:" + key)

        if result.get("status") != "PASS__SOURCE_DEFINED_RAW_FACT_FINANCE_UNLESS_BRANCH_SELECTED":
            errors.append("RESULT_STATUS_INVALID")
        if result.get("pass") is not True:
            errors.append("RESULT_PASS_FALSE")
        if result.get("source_semantic_coverage_verified") is not True:
            errors.append("SOURCE_SEMANTIC_COVERAGE_FLAG_FALSE")
        if result.get("source_semantic_coverage_receipt") != coverage:
            errors.append("SOURCE_SEMANTIC_COVERAGE_RECEIPT_MISMATCH")
        if result.get("model_dependency_count") != 0:
            errors.append("MODEL_DEPENDENCY_NONZERO")
        if result.get("external_world_truth_claimed") is not False:
            errors.append("EXTERNAL_WORLD_TRUTH_BOUNDARY_VIOLATION")
        if result.get("implicit_semantic_inference_claimed") is not False:
            errors.append("IMPLICIT_SEMANTIC_INFERENCE_BOUNDARY_VIOLATION")

        return {
            **base,
            "verified": not errors,
            "status": (
                "PASS__INDEPENDENT_SOURCE_DEFINED_RAW_FACT_UNLESS_RECOMPUTATION"
                if not errors else "FAIL_CLOSED"
            ),
            "errors": sorted(set(errors)),
            "condition_holds": holds,
            "condition_atom_id": atom_id,
            "defined_term": binding["defined_term"],
            "field_name": binding["field_name"],
            "typed_context_sha256": context_sha,
            "fact_source_sha256": fact_sha,
            "selected_branch": expected["selected_branch"],
            "source_semantic_coverage_verified": True,
            "boundary": (
                "EXPLICIT_SOURCE_DECLARATION_TO_ONE_TYPED_FIELD_PLUS_STRICT_TASK_BOUND_RAW_FACT_BYTES_ONLY;"
                "NO_SYNONYMY_ONTOLOGY_IMPLICIT_CONVENTION_CROSS_DOCUMENT_ENTITY_LINKING_OR_EXTERNAL_WORLD_TRUTH"
            ),
        }
    except Exception as exc:
        return {
            **base,
            "status": "FAIL_CLOSED",
            "errors": [type(exc).__name__ + ":" + str(exc)],
        }
