"""Decision-relative semantic relation prover V1.

The prover never promotes lexical similarity, embeddings, model confidence, or
surface resemblance into semantic equality.

It derives the strongest relation justified by explicit verified evidence, then
checks whether that relation is sufficient for the caller's declared decision
need. Counterexamples dominate positive similarity evidence. Task-relative
equivalence may be sufficient even when universal linguistic synonymy is not
proved.

This runtime grants no authority to the evidence producer itself. Callers must
supply already-authenticated evidence receipts/claims.
"""
from __future__ import annotations

from typing import Any, Mapping
import re

from canonical.runtime.terminal_semantic_quotient_v1 import compile_minimal_quotient

SCHEMA = "PROJECT_BRAIN_DECISION_RELATIVE_SEMANTIC_RELATION_V1"

REL_UNKNOWN = "UNKNOWN"
REL_EQUIVALENT = "EXACT_EQUIVALENT"
REL_A_ENTAILS_B = "A_ENTAILS_B"
REL_B_ENTAILS_A = "B_ENTAILS_A"
REL_TASK_EQUIVALENT = "TASK_EQUIVALENT"
REL_DISTINCT = "DISTINCT_OR_NONINTERCHANGEABLE"

REQUIREMENTS = {
    "ANY_SOUND_RELATION",
    "BIDIRECTIONAL_EQUIVALENCE",
    "A_ENTAILS_B_REQUIRED",
    "B_ENTAILS_A_REQUIRED",
    "TASK_EQUIVALENCE",
}


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "strongest_proved_relation": REL_UNKNOWN,
        "requirement_satisfied": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _receipt(value: Any, *, relation: str) -> bool:
    if not isinstance(value, Mapping) or value.get("verified") is not True:
        return False
    if value.get("relation") != relation:
        return False
    if value.get("source_kind") not in {
        "EXPLICIT_SOURCE_DEFINITION",
        "AUTHENTICATED_ONTOLOGY",
        "CHECKED_PROOF_DAG",
        "CHECKED_COUNTEREXAMPLE",
    }:
        return False
    verifier = str(value.get("verifier_id") or "").strip()
    evidence_sha = str(value.get("evidence_sha256") or "")
    scope_sha = str(value.get("scope_sha256") or "")
    return bool(
        verifier
        and _SHA256.fullmatch(evidence_sha)
        and _SHA256.fullmatch(scope_sha)
    )


def _task_equivalence(problem: Mapping[str, Any]) -> dict[str, Any]:
    rows = problem.get("task_terminal_rows")
    if rows is None:
        return {"proved": False, "reason": "NO_TASK_TERMINAL_ROWS"}
    if not isinstance(rows, list) or len(rows) != 2:
        return {"proved": False, "reason": "TASK_TERMINAL_ROWS_MUST_HAVE_TWO_ROWS"}
    ids = [row.get("raw_id") if isinstance(row, Mapping) else None for row in rows]
    if ids != ["A", "B"]:
        return {"proved": False, "reason": "TASK_TERMINAL_ROWS_MUST_BE_A_AND_B"}
    compiled = compile_minimal_quotient(rows)
    if compiled.get("pass") is not True:
        return {"proved": False, "reason": compiled.get("reason") or compiled.get("status"), "receipt": compiled}
    same = compiled["raw_to_class"].get("A") == compiled["raw_to_class"].get("B")
    return {
        "proved": bool(same),
        "reason": "COMPLETE_TERMINAL_SIGNATURES_EQUAL" if same else "TERMINAL_SIGNATURES_DIFFER",
        "receipt": compiled,
    }


def _requirement_satisfied(requirement: str, relation: str, *, task_equivalent: bool) -> bool:
    if requirement == "ANY_SOUND_RELATION":
        return relation != REL_UNKNOWN
    if requirement == "BIDIRECTIONAL_EQUIVALENCE":
        return relation == REL_EQUIVALENT
    if requirement == "A_ENTAILS_B_REQUIRED":
        return relation in {REL_EQUIVALENT, REL_A_ENTAILS_B}
    if requirement == "B_ENTAILS_A_REQUIRED":
        return relation in {REL_EQUIVALENT, REL_B_ENTAILS_A}
    if requirement == "TASK_EQUIVALENCE":
        return relation == REL_EQUIVALENT or task_equivalent
    return False


def prove(problem: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        return _fail("PROBLEM_NOT_OBJECT")

    a = str(problem.get("expression_a") or "").strip()
    b = str(problem.get("expression_b") or "").strip()
    if not a or not b:
        return _fail("TWO_EXPRESSIONS_REQUIRED")

    requirement = str(problem.get("required_relation") or "").strip().upper()
    if requirement not in REQUIREMENTS:
        return _fail("REQUIRED_RELATION_INVALID")

    evidence = problem.get("evidence") or {}
    if not isinstance(evidence, Mapping):
        return _fail("EVIDENCE_NOT_OBJECT")

    forbidden = []
    for key in ("embedding_similarity", "model_confidence", "surface_similarity", "llm_vote"):
        if key in evidence:
            forbidden.append(key)
    if forbidden:
        return _fail(
            "UNSAFE_SIMILARITY_EVIDENCE_CANNOT_GRANT_SEMANTIC_RELATION",
            forbidden_evidence=sorted(forbidden),
        )

    # Negative evidence is checked first. A verified substitutability
    # counterexample defeats that direction regardless of weaker positive cues.
    counter_a_to_b = _receipt(
        evidence.get("counterexample_a_substituted_for_b"),
        relation="COUNTEREXAMPLE_A_FOR_B",
    )
    counter_b_to_a = _receipt(
        evidence.get("counterexample_b_substituted_for_a"),
        relation="COUNTEREXAMPLE_B_FOR_A",
    )

    explicit_eq = _receipt(
        evidence.get("explicit_source_equivalence"),
        relation=REL_EQUIVALENT,
    )
    concept = evidence.get("authenticated_concept_binding")
    same_concept = (
        isinstance(concept, Mapping)
        and _receipt(concept, relation=REL_EQUIVALENT)
        and isinstance(concept.get("a_concept_id"), str)
        and concept.get("a_concept_id")
        and concept.get("a_concept_id") == concept.get("b_concept_id")
    )
    a_to_b = _receipt(evidence.get("entailment_a_to_b"), relation=REL_A_ENTAILS_B)
    b_to_a = _receipt(evidence.get("entailment_b_to_a"), relation=REL_B_ENTAILS_A)

    positive_exact = explicit_eq or same_concept or (a_to_b and b_to_a)

    if positive_exact and (counter_a_to_b or counter_b_to_a):
        return _fail(
            "CONTRADICTORY_EQUIVALENCE_EVIDENCE",
            counterexample_a_to_b=counter_a_to_b,
            counterexample_b_to_a=counter_b_to_a,
        )

    relation = REL_UNKNOWN
    basis: list[str] = []

    if positive_exact:
        relation = REL_EQUIVALENT
        if explicit_eq:
            basis.append("EXPLICIT_SOURCE_EQUIVALENCE")
        if same_concept:
            basis.append("AUTHENTICATED_SHARED_CONCEPT_ID")
        if a_to_b and b_to_a:
            basis.append("MUTUAL_VERIFIED_ENTAILMENT")
    elif a_to_b and not counter_a_to_b:
        relation = REL_A_ENTAILS_B
        basis.append("VERIFIED_A_TO_B_ENTAILMENT")
    elif b_to_a and not counter_b_to_a:
        relation = REL_B_ENTAILS_A
        basis.append("VERIFIED_B_TO_A_ENTAILMENT")
    elif counter_a_to_b or counter_b_to_a:
        relation = REL_DISTINCT
        if counter_a_to_b:
            basis.append("COUNTEREXAMPLE_A_FOR_B")
        if counter_b_to_a:
            basis.append("COUNTEREXAMPLE_B_FOR_A")

    task = _task_equivalence(problem)
    task_eq = task.get("proved") is True
    if relation == REL_UNKNOWN and task_eq:
        relation = REL_TASK_EQUIVALENT
        basis.append("COMPLETE_TASK_TERMINAL_SIGNATURE_EQUIVALENCE")
    elif relation in {REL_A_ENTAILS_B, REL_B_ENTAILS_A, REL_DISTINCT} and task_eq:
        # Universal relation remains directional/distinct, but the current task
        # may still safely quotient the two expressions.
        basis.append("ALSO_TASK_EQUIVALENT")

    satisfied = _requirement_satisfied(
        requirement,
        relation,
        task_equivalent=task_eq,
    )

    status = (
        "PASS__REQUIRED_SEMANTIC_RELATION_PROVED"
        if satisfied
        else "OPEN__STRONGER_SEMANTIC_RELATION_OR_DISCRIMINATOR_REQUIRED"
    )

    return {
        "schema": SCHEMA,
        "status": status,
        "pass": satisfied,
        "expression_a": a,
        "expression_b": b,
        "required_relation": requirement,
        "strongest_proved_relation": relation,
        "proof_basis": basis,
        "task_equivalent": task_eq,
        "task_equivalence_receipt": task.get("receipt"),
        "requirement_satisfied": satisfied,
        "counterexample_a_to_b": counter_a_to_b,
        "counterexample_b_to_a": counter_b_to_a,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "hard_nonclaims": [
            "THIS_PROVES_ONLY_THE_RELATION_SUPPORTED_BY_TYPED_CONTENT_ADDRESSED_RECEIPTS_AND_COMPLETE_TASK_SIGNATURES",
            "RECEIPT_STRUCTURE_DOES_NOT_BY_ITSELF_AUTHENTICATE_THE_UPSTREAM_VERIFIER_OR_SOURCE",
            "DIRECTIONAL_ENTAILMENT_IS_NOT_UNRESTRICTED_SUBSTITUTABILITY__POLARITY_AND_COMPOSITION_RULES_REMAIN_LOAD_BEARING",
            "NO_OPEN_WORLD_LINGUISTIC_SYNONYMY_CLAIM",
        ],
    }
