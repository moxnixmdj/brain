"""Decision-relative semantic relation control V1.

This runtime deliberately does NOT solve global synonymy.

It answers a smaller, sounder question:
"What is the weakest semantic relation that must be proved for the current task,
and do the currently authenticated/recomputable facts prove it?"

Authoritative relation admission in V1 is recomputed only from:
1. exact source-declared definitions in raw source bytes, and
2. equality of COMPLETE terminal-relevant signatures via the existing semantic
   quotient compiler.

Embeddings, LLM judgments, lexical databases, string similarity, and model
consensus may appear only as candidate relations/search hints. They cannot
certify equivalence.

Unsupported inferred entailment/ontology relations remain explicit proof targets
instead of being guessed. This module grants no execution, acceptance, promotion,
or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from canonical.runtime.explicit_definition_reference_graph import (
    compile_reference_graph,
)
from canonical.runtime.terminal_semantic_quotient_v1 import (
    compile_minimal_quotient,
)
from canonical.runtime.source_aligned_semantic_entailment_v1 import prove as prove_source_entailment

SCHEMA = "PROJECT_BRAIN_DECISION_RELATIVE_SEMANTIC_RELATION_CONTROL_V1"

REQUIRED_RELATIONS = {
    "SEMANTIC_IDENTITY",
    "LOGICAL_EQUIVALENCE_IN_SCOPE",
    "LEFT_ENTAILS_RIGHT",
    "RIGHT_ENTAILS_LEFT",
    "CURRENT_DECISION_SUBSTITUTION",
}


class SemanticRelationError(ValueError):
    pass


def _norm(value: Any) -> str:
    return " ".join(str(value if value is not None else "").strip().split()).casefold()


def _explicit_equivalence(
    left_surface: str,
    right_surface: str,
    scope_id: str,
    rows: Any,
) -> dict[str, Any]:
    if rows is None:
        return {
            "available": False,
            "proved": False,
            "sources_checked": [],
            "reason": "NO_EXPLICIT_DEFINITION_SOURCES",
        }
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return {
            "available": True,
            "proved": False,
            "sources_checked": [],
            "reason": "EXPLICIT_DEFINITION_SOURCES_INVALID",
        }

    left = _norm(left_surface)
    right = _norm(right_surface)
    checked = []
    matches = []
    failures = []

    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            failures.append(f"ROW_NOT_OBJECT:{i}")
            continue
        source_id = str(row.get("source_id") or "").strip()
        source_scope = str(row.get("scope_id") or "").strip()
        source_text = row.get("source_text")
        if not source_id:
            failures.append(f"SOURCE_ID_REQUIRED:{i}")
            continue
        if source_scope != scope_id:
            failures.append(f"SOURCE_SCOPE_MISMATCH:{source_id}")
            continue
        if not isinstance(source_text, str) or not source_text.strip():
            failures.append(f"SOURCE_TEXT_REQUIRED:{source_id}")
            continue

        graph = compile_reference_graph(source_text)
        checked.append({
            "source_id": source_id,
            "definition_graph_status": graph.get("status"),
        })
        if graph.get("status") == "FAIL_CLOSED":
            failures.append(
                f"DEFINITION_GRAPH_FAIL_CLOSED:{source_id}:"
                + ",".join(str(x) for x in graph.get("errors", []))
            )
            continue
        if graph.get("status") != "COMPILED":
            continue

        for definition in graph.get("definitions", []):
            if not isinstance(definition, Mapping):
                continue
            term = _norm(definition.get("term"))
            target = _norm(definition.get("definition"))
            if (term == left and target == right) or (term == right and target == left):
                matches.append({
                    "source_id": source_id,
                    "term": definition.get("term"),
                    "definition": definition.get("definition"),
                    "sentence_index": definition.get("sentence_index"),
                })

    if failures:
        return {
            "available": True,
            "proved": False,
            "sources_checked": checked,
            "matches": matches,
            "reason": "EXPLICIT_SOURCE_EVIDENCE_FAIL_CLOSED",
            "errors": sorted(set(failures)),
        }

    return {
        "available": True,
        "proved": bool(matches),
        "sources_checked": checked,
        "matches": matches,
        "reason": (
            "EXACT_SOURCE_DECLARED_EQUIVALENCE"
            if matches
            else "NO_EXACT_SOURCE_DECLARED_EQUIVALENCE"
        ),
    }


def _terminal_equivalence(
    left_id: str,
    right_id: str,
    terminal_rows: Any,
) -> dict[str, Any]:
    if terminal_rows is None:
        return {
            "available": False,
            "proved": False,
            "reason": "NO_TERMINAL_SIGNATURE_ROWS",
        }
    if not isinstance(terminal_rows, Sequence) or isinstance(
        terminal_rows, (str, bytes)
    ):
        return {
            "available": True,
            "proved": False,
            "reason": "TERMINAL_SIGNATURE_ROWS_INVALID",
        }

    rows = []
    for row in terminal_rows:
        if not isinstance(row, Mapping):
            return {
                "available": True,
                "proved": False,
                "reason": "TERMINAL_SIGNATURE_ROW_INVALID",
            }
        rows.append(deepcopy(dict(row)))

    ids = [str(x.get("raw_id") or "") for x in rows]
    if len(ids) != 2 or set(ids) != {left_id, right_id}:
        return {
            "available": True,
            "proved": False,
            "reason": "TERMINAL_SIGNATURE_DOMAIN_MUST_BE_EXACT_PAIR",
        }

    quotient = compile_minimal_quotient(rows)
    if quotient.get("pass") is not True:
        return {
            "available": True,
            "proved": False,
            "reason": str(
                quotient.get("reason")
                or quotient.get("status")
                or "TERMINAL_QUOTIENT_FAILED"
            ),
            "quotient": quotient,
        }

    same = quotient["raw_to_class"][left_id] == quotient["raw_to_class"][right_id]
    return {
        "available": True,
        "proved": same,
        "reason": (
            "COMPLETE_TERMINAL_SIGNATURES_EQUAL"
            if same
            else "COMPLETE_TERMINAL_SIGNATURES_DIFFER"
        ),
        "quotient": quotient,
    }


def _next_targets(required: str) -> list[str]:
    if required == "SEMANTIC_IDENTITY":
        return [
            "EXACT_SOURCE_DECLARED_EQUIVALENCE",
            "AUTHENTICATED_SHARED_CONCEPT_IDENTITY",
            "VERIFIED_COUNTEREXAMPLE_SEARCH_BEFORE_ANY_WIDER_MERGE",
        ]
    if required == "LOGICAL_EQUIVALENCE_IN_SCOPE":
        return [
            "SOURCE_ALIGNED_LEFT_TO_RIGHT_ENTAILMENT_PROOF",
            "SOURCE_ALIGNED_RIGHT_TO_LEFT_ENTAILMENT_PROOF",
            "VERIFIED_COUNTEREXAMPLE_SEARCH",
        ]
    if required == "LEFT_ENTAILS_RIGHT":
        return [
            "SOURCE_ALIGNED_LEFT_TO_RIGHT_ENTAILMENT_PROOF",
            "VERIFIED_LEFT_TO_RIGHT_COUNTEREXAMPLE_SEARCH",
        ]
    if required == "RIGHT_ENTAILS_LEFT":
        return [
            "SOURCE_ALIGNED_RIGHT_TO_LEFT_ENTAILMENT_PROOF",
            "VERIFIED_RIGHT_TO_LEFT_COUNTEREXAMPLE_SEARCH",
        ]
    return [
        "COMPLETE_TERMINAL_RELEVANT_SIGNATURE_FOR_LEFT",
        "COMPLETE_TERMINAL_RELEVANT_SIGNATURE_FOR_RIGHT",
        "VERIFIED_TERMINAL_DIVERGENCE_COUNTEREXAMPLE_SEARCH",
    ]


def resolve(problem: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "PROBLEM_NOT_OBJECT",
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    allowed = {
        "left_id",
        "right_id",
        "left_surface",
        "right_surface",
        "scope_id",
        "required_relation",
        "explicit_definition_sources",
        "terminal_signature_rows",
        "candidate_relations",
        "source_entailment_spans",
    }
    extra = set(problem) - allowed
    if extra:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "UNMODELED_FIELDS:" + ",".join(sorted(str(x) for x in extra)),
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    left_id = str(problem.get("left_id") or "").strip()
    right_id = str(problem.get("right_id") or "").strip()
    left_surface = str(problem.get("left_surface") or left_id).strip()
    right_surface = str(problem.get("right_surface") or right_id).strip()
    scope_id = str(problem.get("scope_id") or "").strip()
    required = str(problem.get("required_relation") or "").strip().upper()

    if not left_id or not right_id or left_id == right_id:
        raise SemanticRelationError("DISTINCT_LEFT_RIGHT_IDS_REQUIRED")
    if not left_surface or not right_surface:
        raise SemanticRelationError("LEFT_RIGHT_SURFACES_REQUIRED")
    if not scope_id:
        raise SemanticRelationError("SCOPE_ID_REQUIRED")
    if required not in REQUIRED_RELATIONS:
        raise SemanticRelationError("REQUIRED_RELATION_INVALID")

    candidates = problem.get("candidate_relations", [])
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        raise SemanticRelationError("CANDIDATE_RELATIONS_NOT_SEQUENCE")
    candidate_snapshot = []
    for row in candidates:
        if not isinstance(row, Mapping):
            raise SemanticRelationError("CANDIDATE_RELATION_NOT_OBJECT")
        candidate_snapshot.append(deepcopy(dict(row)))

    explicit = _explicit_equivalence(
        left_surface,
        right_surface,
        scope_id,
        problem.get("explicit_definition_sources"),
    )
    terminal = _terminal_equivalence(
        left_id,
        right_id,
        problem.get("terminal_signature_rows"),
    )

    source_entailment = {
        "available": False,
        "pass": False,
        "status": "NOT_REQUESTED",
        "proved_facts": {
            "left_entails_right": False,
            "right_entails_left": False,
            "logical_equivalence_in_scope": False,
            "left_entails_right_disproved": False,
            "right_entails_left_disproved": False,
        },
    }
    if problem.get("source_entailment_spans") is not None:
        source_entailment = prove_source_entailment({
            "left_surface": left_surface,
            "right_surface": right_surface,
            "scope_id": scope_id,
            "required_relation": "ANY_DIRECTIONAL_RELATION",
            "source_spans": problem.get("source_entailment_spans"),
        })
        source_entailment = {"available": True, **source_entailment}
        if str(source_entailment.get("status") or "").startswith("FAIL_CLOSED"):
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "FAIL_CLOSED__SOURCE_ALIGNED_ENTAILMENT_INVALID",
                "reason": source_entailment.get("reason")
                or source_entailment.get("conflicts")
                or source_entailment.get("status"),
                "scope_id": scope_id,
                "required_relation": required,
                "source_entailment": source_entailment,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }

    if explicit.get("reason") == "EXPLICIT_SOURCE_EVIDENCE_FAIL_CLOSED":
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__EXPLICIT_SOURCE_EVIDENCE_INVALID",
            "reason": explicit.get("errors"),
            "scope_id": scope_id,
            "required_relation": required,
            "explicit_equivalence": explicit,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    semantic_identity = explicit.get("proved") is True
    task_equivalent = terminal.get("proved") is True

    source_facts = (
        source_entailment.get("proved_facts")
        if isinstance(source_entailment.get("proved_facts"), Mapping)
        else {}
    )
    left_entails_right = bool(
        semantic_identity or source_facts.get("left_entails_right") is True
    )
    right_entails_left = bool(
        semantic_identity or source_facts.get("right_entails_left") is True
    )
    logical_equivalence = bool(
        semantic_identity or (left_entails_right and right_entails_left)
    )

    if semantic_identity:
        strongest = "SEMANTIC_IDENTITY"
    elif logical_equivalence:
        strongest = "LOGICAL_EQUIVALENCE_IN_SCOPE"
    elif left_entails_right:
        strongest = "LEFT_ENTAILS_RIGHT"
    elif right_entails_left:
        strongest = "RIGHT_ENTAILS_LEFT"
    elif task_equivalent:
        strongest = "CURRENT_DECISION_SUBSTITUTION"
    elif source_facts.get("left_entails_right_disproved") is True:
        strongest = "LEFT_ENTAILS_RIGHT_DISPROVED"
    elif source_facts.get("right_entails_left_disproved") is True:
        strongest = "RIGHT_ENTAILS_LEFT_DISPROVED"
    else:
        strongest = "UNKNOWN"

    if required == "SEMANTIC_IDENTITY":
        satisfied = semantic_identity
    elif required == "LOGICAL_EQUIVALENCE_IN_SCOPE":
        satisfied = logical_equivalence
    elif required == "LEFT_ENTAILS_RIGHT":
        satisfied = left_entails_right
    elif required == "RIGHT_ENTAILS_LEFT":
        satisfied = right_entails_left
    else:
        satisfied = semantic_identity or logical_equivalence or task_equivalent

    next_targets = [] if satisfied else _next_targets(required)

    return {
        "schema": SCHEMA,
        "pass": satisfied,
        "status": (
            "PASS__REQUIRED_SEMANTIC_RELATION_RECOMPUTED"
            if satisfied
            else "OPEN__REQUIRED_SEMANTIC_RELATION_NOT_PROVED"
        ),
        "action": (
            "USE_PROVED_RELATION_WITHIN_BOUND_SCOPE"
            if satisfied
            else "PRESERVE_DISTINCT_MEANINGS_AND_ACQUIRE_ONLY_DECISION_RELEVANT_EVIDENCE"
        ),
        "left_id": left_id,
        "right_id": right_id,
        "left_surface": left_surface,
        "right_surface": right_surface,
        "scope_id": scope_id,
        "required_relation": required,
        "strongest_proved_relation": strongest,
        "proved_facts": {
            "semantic_identity": semantic_identity,
            "logical_equivalence_in_scope": logical_equivalence,
            "left_entails_right": left_entails_right,
            "right_entails_left": right_entails_left,
            "current_decision_substitution": task_equivalent,
        },
        "explicit_equivalence": explicit,
        "terminal_equivalence": terminal,
        "source_entailment": source_entailment,
        "next_proof_targets": next_targets,
        "counterexample_first": not satisfied,
        "candidate_relation_count": len(candidate_snapshot),
        "candidate_relations": candidate_snapshot,
        "candidate_relations_are_authority": False,
        "similarity_or_model_consensus_can_certify_equivalence": False,
        "source_authority_is_separate_from_source_text_parsing": True,
        "scope_leakage_authorized": False,
        "transitive_promotion_outside_scope_authorized": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
