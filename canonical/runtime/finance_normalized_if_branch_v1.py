"""Pure producer for bounded normalized-finance IF_THEN cases.

The policy-changing fact antecedent_holds is supplied explicitly. This module
certifies only structural scope plus branch selection relative to that fact.
It does not infer finance truth from raw language.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping

from canonical.runtime.certified_scope_fragment_v1 import parse_scope

SCHEMA = "PROJECT_BRAIN_FINANCE_NORMALIZED_IF_BRANCH_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_NORMALIZED_IF_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_NORMALIZED_IF_RESULT_V1"


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def compute(case: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(case, Mapping):
        raise ValueError("CASE_NOT_OBJECT")
    if case.get("schema") != INPUT_SCHEMA:
        raise ValueError("CASE_SCHEMA_INVALID")
    source_id = case.get("source_id")
    source_text = case.get("source_text")
    antecedent_holds = case.get("antecedent_holds")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("SOURCE_ID_REQUIRED")
    if not isinstance(source_text, str) or not source_text.strip():
        raise ValueError("SOURCE_TEXT_REQUIRED")
    if not isinstance(antecedent_holds, bool):
        raise ValueError("ANTECEDENT_HOLDS_BOOLEAN_REQUIRED")

    scoped = parse_scope(source_text, source=source_id.strip())
    if scoped.get("status") != "PARSED":
        raise ValueError("SOURCE_SCOPE_NOT_CERTIFIED:" + str(scoped.get("reason")))
    parsed = scoped.get("parse")
    if not isinstance(parsed, Mapping) or parsed.get("relation") != "IF_THEN":
        raise ValueError("EXACT_SINGLE_IF_THEN_SCOPE_REQUIRED")

    if parsed.get("left_role") == "ANTECEDENT":
        antecedent_span = parsed.get("left_span")
        consequent_span = parsed.get("right_span")
        if parsed.get("right_role") != "CONSEQUENT":
            raise ValueError("CERTIFIED_CONSEQUENT_ROLE_MISMATCH")
    elif parsed.get("right_role") == "ANTECEDENT":
        antecedent_span = parsed.get("right_span")
        consequent_span = parsed.get("left_span")
        if parsed.get("left_role") != "CONSEQUENT":
            raise ValueError("CERTIFIED_CONSEQUENT_ROLE_MISMATCH")
    else:
        raise ValueError("CERTIFIED_ANTECEDENT_ROLE_MISSING")

    for name, span in (("ANTECEDENT", antecedent_span), ("CONSEQUENT", consequent_span)):
        if (
            not isinstance(span, list)
            or len(span) != 2
            or any(not isinstance(x, int) or isinstance(x, bool) for x in span)
        ):
            raise ValueError(name + "_SPAN_INVALID")

    a0, a1 = antecedent_span
    c0, c1 = consequent_span
    antecedent_text = source_text[a0:a1]
    consequent_text = source_text[c0:c1]
    if not antecedent_text or not consequent_text:
        raise ValueError("CERTIFIED_OPERAND_EMPTY")

    selected_branch = "CONSEQUENT_BRANCH" if antecedent_holds else "CONDITION_NOT_MET"
    selected_text = consequent_text if antecedent_holds else ""
    selected_span = [c0, c1] if antecedent_holds else None

    return {
        "schema": RESULT_SCHEMA,
        "status": "PASS__NORMALIZED_FINANCE_IF_BRANCH_SELECTED",
        "pass": True,
        "source_id": source_id.strip(),
        "source_text_sha256": _sha(source_text),
        "scope_id": parsed.get("scope_id"),
        "relation": "IF_THEN",
        "antecedent_holds": antecedent_holds,
        "antecedent_span": [a0, a1],
        "antecedent_text_sha256": _sha(antecedent_text),
        "consequent_span": [c0, c1],
        "consequent_text_sha256": _sha(consequent_text),
        "selected_branch": selected_branch,
        "selected_span": selected_span,
        "selected_text": selected_text,
        "selected_text_sha256": _sha(selected_text),
        "producer": SCHEMA,
        "model_dependency_count": 0,
        "semantic_truth_inferred": False,
        "terminal_authority": False,
    }
