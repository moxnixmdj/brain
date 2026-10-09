"""Bounded finance producer for source-defined raw-fact UNLESS cases.

This composes already-owned verified pieces:
- finance proof-carrying structural source coverage,
- explicit source-declared term -> typed-field binding,
- strict raw JSON -> typed context compilation,
- controlled single-UNLESS scope selection.

It closes only the case where the policy source itself explicitly defines the
human term used by the condition and the task-bound raw fact source contains the
referenced typed field. It does not infer synonyms, ontology, unstated sector
conventions, cross-document entity identity, source factual truth, or authority
beyond the task-bound input.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping

from canonical.runtime.finance_proof_carrying_source_gate_v1 import (
    verify_source_semantic_coverage,
)
from canonical.runtime.certified_defined_term_raw_typed_condition_v2 import (
    evaluate_defined_unless_condition_from_raw_facts,
)
from canonical.runtime.certified_scope_fragment_v1 import parse_scope

SCHEMA = "PROJECT_BRAIN_FINANCE_DEFINED_TERM_RAW_FACT_UNLESS_BRANCH_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_DEFINED_TERM_RAW_FACT_UNLESS_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_DEFINED_TERM_RAW_FACT_UNLESS_RESULT_V1"


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _coverage_bundle(case: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_id": case.get("policy_source_id"),
        "source_text": case.get("policy_source_text"),
        "source_coverage_manifest": deepcopy(case.get("source_coverage_manifest")),
        "source_semantic_coverage": deepcopy(case.get("source_semantic_coverage")),
    }


def compute(case: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(case, Mapping):
        raise ValueError("CASE_NOT_OBJECT")
    if case.get("schema") != INPUT_SCHEMA:
        raise ValueError("CASE_SCHEMA_INVALID")

    policy_source_id = case.get("policy_source_id")
    policy_source_text = case.get("policy_source_text")
    fact_source_id = case.get("fact_source_id")
    fact_source = case.get("fact_source")

    if not isinstance(policy_source_id, str) or not policy_source_id.strip():
        raise ValueError("POLICY_SOURCE_ID_REQUIRED")
    if not isinstance(policy_source_text, str) or not policy_source_text.strip():
        raise ValueError("POLICY_SOURCE_TEXT_REQUIRED")
    if not isinstance(fact_source_id, str) or not fact_source_id.strip():
        raise ValueError("FACT_SOURCE_ID_REQUIRED")
    if not isinstance(fact_source, (str, bytes)) or not fact_source:
        raise ValueError("FACT_SOURCE_BYTES_REQUIRED")

    coverage = verify_source_semantic_coverage(_coverage_bundle(case))
    if coverage.get("pass") is not True:
        raise ValueError(
            "FINANCE_SOURCE_SEMANTIC_COVERAGE_NOT_PROVED:"
            + ",".join(coverage.get("errors") or [])
        )

    evaluated = evaluate_defined_unless_condition_from_raw_facts(
        policy_source_text,
        policy_source_id=policy_source_id.strip(),
        fact_source=fact_source,
        fact_source_id=fact_source_id.strip(),
    )
    if evaluated.get("status") not in {"PROVED_TRUE", "PROVED_FALSE"}:
        raise ValueError(
            "DEFINED_TERM_RAW_FACT_CONDITION_NOT_PROVED:"
            + str(evaluated.get("reason") or evaluated.get("errors"))
        )

    scoped = parse_scope(policy_source_text, source=policy_source_id.strip())
    parsed = scoped.get("parse") if scoped.get("status") == "PARSED" else None
    if not isinstance(parsed, Mapping) or parsed.get("relation") != "UNLESS":
        raise ValueError("EXACT_SINGLE_UNLESS_SCOPE_REQUIRED")

    holds = evaluated.get("condition_holds") is True
    span = parsed.get("right_span") if holds else parsed.get("left_span")
    if not isinstance(span, list) or len(span) != 2:
        raise ValueError("CERTIFIED_BRANCH_SPAN_INVALID")
    start, end = span
    selected_text = policy_source_text[start:end]
    if not selected_text:
        raise ValueError("SELECTED_BRANCH_EMPTY")

    raw_fact = fact_source.encode("utf-8") if isinstance(fact_source, str) else fact_source
    return {
        "schema": RESULT_SCHEMA,
        "status": "PASS__SOURCE_DEFINED_RAW_FACT_FINANCE_UNLESS_BRANCH_SELECTED",
        "pass": True,
        "policy_source_id": policy_source_id.strip(),
        "policy_source_text_sha256": _sha(policy_source_text),
        "fact_source_id": fact_source_id.strip(),
        "fact_source_sha256": sha256(raw_fact).hexdigest(),
        "typed_context_sha256": evaluated.get("typed_context_sha256"),
        "scope_id": parsed.get("scope_id"),
        "relation": "UNLESS",
        "condition_holds": holds,
        "condition_atom_id": evaluated.get("condition_atom_id"),
        "proved_constraint": deepcopy(evaluated.get("proved_constraint")),
        "defined_term": evaluated.get("defined_term"),
        "definition_sentence_index": evaluated.get("definition_sentence_index"),
        "field_name": evaluated.get("field_name"),
        "field_type": evaluated.get("field_type"),
        "operator": evaluated.get("operator"),
        "literal": evaluated.get("literal"),
        "selected_branch": "EXCEPTION_BRANCH" if holds else "ORDINARY_BRANCH",
        "selected_span": [start, end],
        "selected_text": selected_text,
        "selected_text_sha256": _sha(selected_text),
        "source_semantic_coverage_verified": True,
        "source_semantic_coverage_receipt": deepcopy(coverage),
        "model_dependency_count": 0,
        "external_world_truth_claimed": False,
        "implicit_semantic_inference_claimed": False,
        "terminal_authority": False,
        "authority_boundary": (
            "TASK_BOUND_POLICY_AND_FACT_SOURCES_ONLY;"
            "POLICY_SOURCE_MUST_EXPLICITLY_DEFINE_THE_CONDITION_TERM_AS_ONE_TYPED_FIELD;"
            "RAW_FACT_BYTES_ARE_STRICTLY_COMPILED_AND_CONTENT_ADDRESSED;"
            "NO_SYNONYMY_ONTOLOGY_IMPLICIT_SECTOR_CONVENTIONS_CROSS_DOCUMENT_ENTITY_LINKING_"
            "OR_EXTERNAL_WORLD_FACTUAL_TRUTH"
        ),
    }
