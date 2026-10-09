"""Producer-independent verifier for normalized-finance UNLESS branching.

This verifier deliberately does not import the certified scope parser or producer.
It recomputes the admitted source shape with a separate stdlib regular-expression
implementation and checks every load-bearing output field.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FINANCE_NORMALIZED_UNLESS_VERIFY_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_NORMALIZED_UNLESS_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_NORMALIZED_UNLESS_RESULT_V1"
_UNLESS = re.compile(r"\bunless\b", re.IGNORECASE)


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and (text[end - 1].isspace() or text[end - 1] in ".,;:"):
        end -= 1
    return start, end


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
    exception_applies = case.get("exception_applies")
    if not isinstance(source_id, str) or not source_id.strip():
        errors.append("SOURCE_ID_INVALID")
    if not isinstance(text, str) or not text.strip():
        errors.append("SOURCE_TEXT_INVALID")
        text = ""
    if not isinstance(exception_applies, bool):
        errors.append("EXCEPTION_APPLIES_INVALID")

    matches = list(_UNLESS.finditer(text))
    if len(matches) != 1:
        errors.append("EXACTLY_ONE_UNLESS_REQUIRED")
    else:
        match = matches[0]
        left = _trim(text, 0, match.start())
        right = _trim(text, match.end(), len(text))
        if left[0] >= left[1] or right[0] >= right[1]:
            errors.append("UNLESS_BRANCH_EMPTY")
        elif isinstance(exception_applies, bool):
            expected_branch = (
                "EXCEPTION_BRANCH" if exception_applies else "ORDINARY_BRANCH"
            )
            expected_span = right if exception_applies else left
            selected_text = text[expected_span[0]:expected_span[1]]

            if result.get("status") != "PASS__NORMALIZED_FINANCE_UNLESS_BRANCH_SELECTED":
                errors.append("RESULT_STATUS_INVALID")
            if result.get("pass") is not True:
                errors.append("RESULT_PASS_FALSE")
            if result.get("source_id") != source_id.strip():
                errors.append("SOURCE_ID_MISMATCH")
            if result.get("source_text_sha256") != _sha(text):
                errors.append("SOURCE_TEXT_HASH_MISMATCH")
            if result.get("relation") != "UNLESS":
                errors.append("RELATION_MISMATCH")
            if result.get("exception_applies") is not exception_applies:
                errors.append("EXCEPTION_FACT_MISMATCH")
            if result.get("selected_branch") != expected_branch:
                errors.append("SELECTED_BRANCH_MISMATCH")
            if result.get("selected_span") != [expected_span[0], expected_span[1]]:
                errors.append("SELECTED_SPAN_MISMATCH")
            if result.get("selected_text") != selected_text:
                errors.append("SELECTED_TEXT_MISMATCH")
            if result.get("selected_text_sha256") != _sha(selected_text):
                errors.append("SELECTED_TEXT_HASH_MISMATCH")
            if result.get("semantic_truth_inferred") is not False:
                errors.append("SEMANTIC_TRUTH_BOUNDARY_VIOLATION")
            if result.get("model_dependency_count") != 0:
                errors.append("MODEL_DEPENDENCY_NONZERO")

    return {
        "schema": SCHEMA,
        "verified": not errors,
        "status": (
            "PASS__INDEPENDENT_NORMALIZED_FINANCE_UNLESS_RECOMPUTATION"
            if not errors
            else "FAIL_CLOSED"
        ),
        "producer_independent": True,
        "model_dependency_count": 0,
        "errors": sorted(set(errors)),
        "terminal_authority": False,
        "boundary": (
            "VERIFIES_BRANCH_SELECTION_RELATIVE_TO_EXPLICIT_TYPED_EXCEPTION_FACT;"
            "DOES_NOT_VERIFY_THE_REAL_WORLD_TRUTH_OF_EXCEPTION_APPLIES_OR_GENERAL_FINANCE_SEMANTICS"
        ),
    }
