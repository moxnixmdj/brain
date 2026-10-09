"""Bounded producer for controlled typed finance UNLESS conditions.

This composes the already-existing certified source-scope parser and typed UNLESS
condition evaluator.  The input file is the task authority for the typed context;
this module makes no claim that the context mirrors the external world.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping

from canonical.runtime.certified_scope_fragment_v1 import parse_scope
from canonical.runtime.certified_typed_unless_condition_v1 import evaluate_unless_condition
from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256

SCHEMA = "PROJECT_BRAIN_FINANCE_CONTROLLED_TYPED_UNLESS_BRANCH_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_CONTROLLED_TYPED_UNLESS_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_CONTROLLED_TYPED_UNLESS_RESULT_V1"


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def compute(case: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(case, Mapping):
        raise ValueError("CASE_NOT_OBJECT")
    if case.get("schema") != INPUT_SCHEMA:
        raise ValueError("CASE_SCHEMA_INVALID")
    source_id = case.get("source_id")
    source_text = case.get("source_text")
    typed_context = case.get("typed_context")
    expected_digest = case.get("typed_context_sha256")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("SOURCE_ID_REQUIRED")
    if not isinstance(source_text, str) or not source_text.strip():
        raise ValueError("SOURCE_TEXT_REQUIRED")
    if not isinstance(typed_context, Mapping):
        raise ValueError("TYPED_CONTEXT_REQUIRED")
    if not isinstance(expected_digest, str) or len(expected_digest) != 64:
        raise ValueError("TYPED_CONTEXT_SHA256_REQUIRED")
    actual_digest = typed_context_sha256(typed_context)
    if actual_digest != expected_digest:
        raise ValueError("TYPED_CONTEXT_CONTENT_ADDRESS_MISMATCH")

    condition = evaluate_unless_condition(
        source_text,
        source_id=source_id.strip(),
        typed_context=typed_context,
        expected_typed_context_sha256=expected_digest,
    )
    if condition.get("status") not in {"PROVED_TRUE", "PROVED_FALSE"}:
        raise ValueError(
            "CONTROLLED_TYPED_UNLESS_CONDITION_NOT_PROVED:"
            + str(condition.get("reason") or condition.get("errors"))
        )

    scoped = parse_scope(source_text, source=source_id.strip())
    parsed = scoped.get("parse") if scoped.get("status") == "PARSED" else None
    if not isinstance(parsed, Mapping) or parsed.get("relation") != "UNLESS":
        raise ValueError("EXACT_SINGLE_UNLESS_SCOPE_REQUIRED")

    holds = condition.get("condition_holds") is True
    span = parsed.get("right_span") if holds else parsed.get("left_span")
    branch = "EXCEPTION_BRANCH" if holds else "ORDINARY_BRANCH"
    if not isinstance(span, list) or len(span) != 2:
        raise ValueError("CERTIFIED_BRANCH_SPAN_INVALID")
    start, end = span
    selected_text = source_text[start:end]
    if not selected_text:
        raise ValueError("SELECTED_BRANCH_EMPTY")

    return {
        "schema": RESULT_SCHEMA,
        "status": "PASS__CONTROLLED_TYPED_FINANCE_UNLESS_BRANCH_SELECTED",
        "pass": True,
        "source_id": source_id.strip(),
        "source_text_sha256": _sha(source_text),
        "typed_context_sha256": actual_digest,
        "scope_id": parsed.get("scope_id"),
        "relation": "UNLESS",
        "condition_holds": holds,
        "condition_atom_id": condition.get("condition_atom_id"),
        "proved_constraint": condition.get("proved_constraint"),
        "field_name": condition.get("field_name"),
        "field_type": condition.get("field_type"),
        "operator": condition.get("operator"),
        "literal": condition.get("literal"),
        "selected_branch": branch,
        "selected_span": [start, end],
        "selected_text": selected_text,
        "selected_text_sha256": _sha(selected_text),
        "model_dependency_count": 0,
        "external_world_truth_claimed": False,
        "terminal_authority": False,
    }
