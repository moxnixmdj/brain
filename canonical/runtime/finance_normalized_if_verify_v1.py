"""Producer-independent verifier for normalized-finance IF_THEN branching."""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FINANCE_NORMALIZED_IF_VERIFY_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_NORMALIZED_IF_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_NORMALIZED_IF_RESULT_V1"
_IF = re.compile(r"\bif\b", re.IGNORECASE)


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and (text[end - 1].isspace() or text[end - 1] in ".,;:"):
        end -= 1
    return start, end


def _parse_if(text: str) -> tuple[tuple[int, int], tuple[int, int]] | None:
    matches = list(_IF.finditer(text))
    if len(matches) != 1:
        return None
    match = matches[0]
    if not text[:match.start()].strip():
        commas = [
            i for i, ch in enumerate(text[match.end():], start=match.end())
            if ch == ","
        ]
        if len(commas) != 1:
            return None
        comma = commas[0]
        antecedent = _trim(text, match.end(), comma)
        consequent = _trim(text, comma + 1, len(text))
    else:
        consequent = _trim(text, 0, match.start())
        antecedent = _trim(text, match.end(), len(text))
    if antecedent[0] >= antecedent[1] or consequent[0] >= consequent[1]:
        return None
    return antecedent, consequent


def verify(case: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(case, Mapping) or case.get("schema") != INPUT_SCHEMA:
        return {
            "schema": SCHEMA,
            "verified": False,
            "producer_independent": True,
            "model_dependency_count": 0,
            "errors": ["CASE_SCHEMA_INVALID"],
            "terminal_authority": False,
        }
    if not isinstance(result, Mapping) or result.get("schema") != RESULT_SCHEMA:
        return {
            "schema": SCHEMA,
            "verified": False,
            "producer_independent": True,
            "model_dependency_count": 0,
            "errors": ["RESULT_SCHEMA_INVALID"],
            "terminal_authority": False,
        }

    source_id = case.get("source_id")
    text = case.get("source_text")
    antecedent_holds = case.get("antecedent_holds")
    if not isinstance(source_id, str) or not source_id.strip():
        errors.append("SOURCE_ID_INVALID")
    if not isinstance(text, str) or not text.strip():
        errors.append("SOURCE_TEXT_INVALID")
        text = ""
    if not isinstance(antecedent_holds, bool):
        errors.append("ANTECEDENT_HOLDS_INVALID")

    parsed = _parse_if(text)
    if parsed is None:
        errors.append("EXACT_SINGLE_IF_THEN_REQUIRED")
    elif isinstance(antecedent_holds, bool):
        antecedent, consequent = parsed
        atext = text[antecedent[0]:antecedent[1]]
        ctext = text[consequent[0]:consequent[1]]
        expected_branch = (
            "CONSEQUENT_BRANCH" if antecedent_holds else "CONDITION_NOT_MET"
        )
        expected_span = [consequent[0], consequent[1]] if antecedent_holds else None
        expected_text = ctext if antecedent_holds else ""

        checks = [
            (result.get("status") == "PASS__NORMALIZED_FINANCE_IF_BRANCH_SELECTED", "RESULT_STATUS_INVALID"),
            (result.get("pass") is True, "RESULT_PASS_FALSE"),
            (result.get("source_id") == source_id.strip(), "SOURCE_ID_MISMATCH"),
            (result.get("source_text_sha256") == _sha(text), "SOURCE_TEXT_HASH_MISMATCH"),
            (result.get("relation") == "IF_THEN", "RELATION_MISMATCH"),
            (result.get("antecedent_holds") is antecedent_holds, "ANTECEDENT_FACT_MISMATCH"),
            (result.get("antecedent_span") == [antecedent[0], antecedent[1]], "ANTECEDENT_SPAN_MISMATCH"),
            (result.get("antecedent_text_sha256") == _sha(atext), "ANTECEDENT_HASH_MISMATCH"),
            (result.get("consequent_span") == [consequent[0], consequent[1]], "CONSEQUENT_SPAN_MISMATCH"),
            (result.get("consequent_text_sha256") == _sha(ctext), "CONSEQUENT_HASH_MISMATCH"),
            (result.get("selected_branch") == expected_branch, "SELECTED_BRANCH_MISMATCH"),
            (result.get("selected_span") == expected_span, "SELECTED_SPAN_MISMATCH"),
            (result.get("selected_text") == expected_text, "SELECTED_TEXT_MISMATCH"),
            (result.get("selected_text_sha256") == _sha(expected_text), "SELECTED_TEXT_HASH_MISMATCH"),
            (result.get("semantic_truth_inferred") is False, "SEMANTIC_TRUTH_BOUNDARY_VIOLATION"),
            (result.get("model_dependency_count") == 0, "MODEL_DEPENDENCY_NONZERO"),
        ]
        errors.extend(reason for ok, reason in checks if not ok)

    return {
        "schema": SCHEMA,
        "verified": not errors,
        "status": (
            "PASS__INDEPENDENT_NORMALIZED_FINANCE_IF_RECOMPUTATION"
            if not errors else "FAIL_CLOSED"
        ),
        "producer_independent": True,
        "model_dependency_count": 0,
        "errors": sorted(set(errors)),
        "terminal_authority": False,
        "boundary": (
            "VERIFIES_IF_THEN_BRANCH_SELECTION_RELATIVE_TO_EXPLICIT_TYPED_"
            "ANTECEDENT_TRUTH__DOES_NOT_INFER_THE_TRUTH"
        ),
    }
