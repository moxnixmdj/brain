"""Bounded producer for explicit-definition Finance UNLESS cases.

Owned scope:
- exactly two source sentences;
- first sentence is one explicit named definition: TERM means CONDITION;
- second sentence is one UNLESS rule whose exception branch is exactly TERM;
- CONDITION must be in the already-certified task-bound Boolean/decimal grammar.

The definition graph owns only explicit named-reference propagation. The typed
condition engine owns truth only relative to the content-addressed task context.
No external-world or general finance-language truth is inferred here.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any, Mapping

from canonical.runtime.explicit_definition_reference_graph import compile_reference_graph
from canonical.runtime.certified_scope_fragment_v1 import parse_scope
from canonical.runtime.certified_typed_unless_condition_v1 import evaluate_unless_condition
from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256

SCHEMA = "PROJECT_BRAIN_FINANCE_EXPLICIT_DEFINITION_UNLESS_BRANCH_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_EXPLICIT_DEFINITION_UNLESS_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_EXPLICIT_DEFINITION_UNLESS_RESULT_V1"

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _sentences(text: str) -> list[str]:
    return [x.strip() for x in _SENTENCE_SPLIT.split(text) if x.strip()]


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

    sentences = _sentences(source_text)
    if len(sentences) != 2:
        raise ValueError("EXACTLY_TWO_SOURCE_SENTENCES_REQUIRED")

    graph = compile_reference_graph(source_text)
    if graph.get("status") != "COMPILED":
        raise ValueError("EXPLICIT_DEFINITION_GRAPH_NOT_COMPILED")
    definitions = graph.get("definitions")
    references = graph.get("references")
    if not isinstance(definitions, list) or len(definitions) != 1:
        raise ValueError("EXACTLY_ONE_EXPLICIT_DEFINITION_REQUIRED")
    if not isinstance(references, list) or len(references) != 1:
        raise ValueError("EXACTLY_ONE_EXPLICIT_REFERENCE_SENTENCE_REQUIRED")

    definition = definitions[0]
    reference = references[0]
    resolved = reference.get("resolved_named_definitions")
    if (
        not isinstance(definition, Mapping)
        or not isinstance(reference, Mapping)
        or not isinstance(resolved, list)
        or len(resolved) != 1
        or not isinstance(resolved[0], Mapping)
    ):
        raise ValueError("REFERENCE_BINDING_SHAPE_INVALID")
    if definition.get("sentence_index") != 0 or reference.get("sentence_index") != 1:
        raise ValueError("DEFINITION_THEN_RULE_ORDER_REQUIRED")

    term = str(definition.get("term") or "").strip()
    definition_text = str(definition.get("definition") or "").strip()
    if (
        not term
        or not definition_text
        or str(resolved[0].get("term") or "").casefold() != term.casefold()
        or str(resolved[0].get("definition") or "").casefold()
        != definition_text.casefold()
    ):
        raise ValueError("REFERENCE_DEFINITION_BINDING_MISMATCH")

    # V1 deliberately admits only the simplest explicit-definition operator.
    first_bare = sentences[0].rstrip(".")
    expected_prefix = term + " means "
    if not first_bare.casefold().startswith(expected_prefix.casefold()):
        raise ValueError("V1_REQUIRES_EXPLICIT_MEANS_DEFINITION")

    rule_text = str(reference.get("sentence") or "").strip()
    if rule_text != sentences[1]:
        raise ValueError("REFERENCE_SENTENCE_MISMATCH")
    rule_source_id = source_id.strip() + "#rule"
    scoped = parse_scope(rule_text, source=rule_source_id)
    parsed = scoped.get("parse") if scoped.get("status") == "PARSED" else None
    if not isinstance(parsed, Mapping) or parsed.get("relation") != "UNLESS":
        raise ValueError("EXACT_SINGLE_UNLESS_RULE_REQUIRED")

    right_span = parsed.get("right_span")
    left_span = parsed.get("left_span")
    if (
        not isinstance(right_span, list)
        or len(right_span) != 2
        or not isinstance(left_span, list)
        or len(left_span) != 2
    ):
        raise ValueError("UNLESS_BRANCH_SPAN_INVALID")
    reference_text = rule_text[right_span[0]:right_span[1]]
    ordinary_text = rule_text[left_span[0]:left_span[1]]
    if reference_text.casefold() != term.casefold():
        raise ValueError("UNLESS_EXCEPTION_MUST_EQUAL_DEFINED_TERM")

    expanded_rule = ordinary_text + " unless " + definition_text + "."
    expanded_source_id = source_id.strip() + "#expanded"
    condition = evaluate_unless_condition(
        expanded_rule,
        source_id=expanded_source_id,
        typed_context=typed_context,
        expected_typed_context_sha256=expected_digest,
    )
    if condition.get("status") not in {"PROVED_TRUE", "PROVED_FALSE"}:
        raise ValueError(
            "DEFINED_CONDITION_NOT_PROVED:"
            + str(condition.get("reason") or condition.get("errors"))
        )

    holds = condition.get("condition_holds") is True
    selected_branch = "EXCEPTION_BRANCH" if holds else "ORDINARY_BRANCH"
    selected_local_span = right_span if holds else left_span
    selected_text = rule_text[selected_local_span[0]:selected_local_span[1]]

    rule_start = source_text.find(rule_text)
    if rule_start < 0 or source_text.find(rule_text, rule_start + 1) >= 0:
        raise ValueError("RULE_SENTENCE_NOT_UNIQUELY_LOCATED_IN_SOURCE")
    selected_span = [
        rule_start + selected_local_span[0],
        rule_start + selected_local_span[1],
    ]

    return {
        "schema": RESULT_SCHEMA,
        "status": "PASS__EXPLICIT_DEFINITION_TYPED_FINANCE_UNLESS_BRANCH_SELECTED",
        "pass": True,
        "source_id": source_id.strip(),
        "source_text_sha256": _sha(source_text),
        "typed_context_sha256": actual_digest,
        "definition_term": term,
        "definition_term_sha256": _sha(term),
        "definition_text_sha256": _sha(definition_text),
        "reference_sentence_index": 1,
        "reference_text_sha256": _sha(reference_text),
        "rule_text_sha256": _sha(rule_text),
        "expanded_rule_sha256": _sha(expanded_rule),
        "rule_scope_id": parsed.get("scope_id"),
        "condition_holds": holds,
        "condition_atom_id": condition.get("condition_atom_id"),
        "proved_constraint": condition.get("proved_constraint"),
        "field_name": condition.get("field_name"),
        "field_type": condition.get("field_type"),
        "operator": condition.get("operator"),
        "literal": condition.get("literal"),
        "selected_branch": selected_branch,
        "selected_span": selected_span,
        "selected_text": selected_text,
        "selected_text_sha256": _sha(selected_text),
        "model_dependency_count": 0,
        "reference_resolution_authority": (
            "EXPLICIT_NAMED_DEFINITION_TO_EXACT_LATER_NAMED_REFERENCE_ONLY"
        ),
        "external_world_truth_claimed": False,
        "general_ontology_mapping_claimed": False,
        "terminal_authority": False,
    }
