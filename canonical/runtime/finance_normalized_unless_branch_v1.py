"""Pure producer for a deliberately bounded normalized-finance UNLESS branch.

The input supplies the policy-changing fact exception_applies explicitly.
This module does not infer that fact, finance domain truth, or arbitrary language
semantics. It only binds an exact single-UNLESS source structure to the correct
branch under the supplied typed Boolean.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping

from canonical.runtime.certified_scope_fragment_v1 import parse_scope

SCHEMA = "PROJECT_BRAIN_FINANCE_NORMALIZED_UNLESS_BRANCH_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_NORMALIZED_UNLESS_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_NORMALIZED_UNLESS_RESULT_V1"


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def compute(case: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(case, Mapping):
        raise ValueError("CASE_NOT_OBJECT")
    if case.get("schema") != INPUT_SCHEMA:
        raise ValueError("CASE_SCHEMA_INVALID")

    source_id = case.get("source_id")
    source_text = case.get("source_text")
    exception_applies = case.get("exception_applies")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("SOURCE_ID_REQUIRED")
    if not isinstance(source_text, str) or not source_text.strip():
        raise ValueError("SOURCE_TEXT_REQUIRED")
    if not isinstance(exception_applies, bool):
        raise ValueError("EXCEPTION_APPLIES_BOOLEAN_REQUIRED")

    scoped = parse_scope(source_text, source=source_id.strip())
    if scoped.get("status") != "PARSED":
        raise ValueError("SOURCE_SCOPE_NOT_CERTIFIED:" + str(scoped.get("reason")))
    parsed = scoped.get("parse")
    if not isinstance(parsed, Mapping) or parsed.get("relation") != "UNLESS":
        raise ValueError("EXACT_SINGLE_UNLESS_SCOPE_REQUIRED")

    if exception_applies:
        selected_branch = "EXCEPTION_BRANCH"
        span = parsed.get("right_span")
        expected_role = "EXCEPTION_BRANCH"
    else:
        selected_branch = "ORDINARY_BRANCH"
        span = parsed.get("left_span")
        expected_role = "ORDINARY_BRANCH"

    if (
        not isinstance(span, list)
        or len(span) != 2
        or any(not isinstance(x, int) or isinstance(x, bool) for x in span)
    ):
        raise ValueError("CERTIFIED_BRANCH_SPAN_INVALID")
    if exception_applies and parsed.get("right_role") != expected_role:
        raise ValueError("CERTIFIED_EXCEPTION_ROLE_MISMATCH")
    if not exception_applies and parsed.get("left_role") != expected_role:
        raise ValueError("CERTIFIED_ORDINARY_ROLE_MISMATCH")

    start, end = span
    selected_text = source_text[start:end]
    if not selected_text:
        raise ValueError("SELECTED_BRANCH_EMPTY")

    return {
        "schema": RESULT_SCHEMA,
        "status": "PASS__NORMALIZED_FINANCE_UNLESS_BRANCH_SELECTED",
        "pass": True,
        "source_id": source_id.strip(),
        "source_text_sha256": _sha(source_text),
        "scope_id": parsed.get("scope_id"),
        "relation": "UNLESS",
        "exception_applies": exception_applies,
        "selected_branch": selected_branch,
        "selected_span": [start, end],
        "selected_text": selected_text,
        "selected_text_sha256": _sha(selected_text),
        "producer": SCHEMA,
        "model_dependency_count": 0,
        "semantic_truth_inferred": False,
        "terminal_authority": False,
    }
