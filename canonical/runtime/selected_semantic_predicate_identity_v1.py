"""Stable precommitment identity for the checked raw defined-term condition fragment.

This module derives only the identity of the semantic predicate from policy-source
syntax. It does not inspect case facts and therefore does not learn TRUE/FALSE.

The identity exactly matches selected_semantic_truth_certificate_v1's checker-
minted source-condition-sha256 identity for the same checked fragment.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.certified_scope_fragment_v1 import parse_scope
from canonical.runtime.explicit_definition_reference_graph import compile_reference_graph
from canonical.runtime.certified_defined_term_typed_condition_v1 import _parse_condition_for_term

SCHEMA = "PROJECT_BRAIN_SELECTED_SEMANTIC_PREDICATE_IDENTITY_V1"


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "predicate_id": None,
        "truth_observed": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def compile_identity(source_text: str, *, source_id: str) -> dict[str, Any]:
    if not isinstance(source_text, str) or not source_text.strip():
        return _fail("SOURCE_TEXT_REQUIRED")
    if not isinstance(source_id, str) or not source_id.strip():
        return _fail("SOURCE_ID_REQUIRED")

    graph = compile_reference_graph(source_text)
    if graph.get("status") == "FAIL_CLOSED":
        return _fail("EXPLICIT_DEFINITION_GRAPH_FAIL_CLOSED")

    scoped = parse_scope(source_text, source=source_id)
    parsed = scoped.get("parse") if scoped.get("status") == "PARSED" else None
    if not isinstance(parsed, Mapping) or parsed.get("relation") != "UNLESS":
        return _fail("SOURCE_NOT_IN_CERTIFIED_SINGLE_UNLESS_FRAGMENT")

    start, end = parsed["right_span"]
    condition_text = source_text[start:end]

    candidates: list[dict[str, Any]] = []
    for row in graph.get("definitions") or []:
        if not isinstance(row, Mapping):
            continue
        term = row.get("term")
        target = row.get("definition")
        if not isinstance(term, str) or not term.strip():
            continue
        if not isinstance(target, str) or not target.strip():
            continue
        parsed_condition = _parse_condition_for_term(condition_text, term.strip())
        if parsed_condition is None:
            continue
        candidates.append({
            "defined_term": term.strip(),
            "field_name": target.strip(),
            "field_type": parsed_condition["required_type"],
            "operator": parsed_condition["operator"],
            "literal": parsed_condition["literal"],
        })

    if len(candidates) != 1:
        return _fail(
            "UNIQUE_DEFINED_TERM_CONDITION_REQUIRED",
            candidate_count=len(candidates),
        )

    row = candidates[0]
    source_sha256 = sha256(source_text.encode("utf-8")).hexdigest()
    descriptor = {
        "source_id": source_id,
        "source_sha256": source_sha256,
        "kind": "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION",
        "defined_term": row["defined_term"],
        "field_name": row["field_name"],
        "field_type": row["field_type"],
        "operator": row["operator"],
        "literal": row["literal"],
    }
    material = json.dumps(
        descriptor,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    predicate_id = "source-condition-sha256:" + sha256(material).hexdigest()
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__STABLE_SELECTED_SEMANTIC_PREDICATE_IDENTITY",
        "predicate_id": predicate_id,
        "source_id": source_id,
        "source_sha256": source_sha256,
        "descriptor": descriptor,
        "truth_observed": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "PREDICATE_IDENTITY_ONLY__NO_CASE_FACTS_CONSUMED__NO_TRUTH_VALUE__"
            "NO_SOURCE_AUTHORIZATION_POLICY_ADEQUACY_OR_TERMINAL_CREDIT"
        ),
    }
