#!/usr/bin/env python3
"""A residual of *names* is not a residual of *meaning*.

A compiled class of statements is not evidence that the user has a choice to
make. Before asking, this gate evaluates the statements on real runs from a
machine that was not used to fit them. If every candidate gives the same
verdict, there is no question to ask and the gate refuses to spend an answer.

It parses no English, ranks no statements, stores no world fact, and never uses
a model to choose. Authority: NONE.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "BRAIN_RESIDUAL_QUESTION_GATE_V1"
Trace = tuple[tuple[tuple[str, str], ...], ...]
Predicate = Callable[[Trace], bool]

NO_QUESTION = "NO_QUESTION"
ASK_USER = "ASK_USER"


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    text: str
    holds: Predicate


def candidate_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def from_predicates(pairs: Sequence[tuple[str, Predicate]]) -> list[Candidate]:
    out = [Candidate(candidate_id(text), text, predicate) for text, predicate in pairs]
    if len({candidate.candidate_id for candidate in out}) != len(out):
        raise ValueError("two statements have the same text; refusing to ask")
    return out


def from_combos(terms: Sequence[Any], combos: Sequence[Sequence[int]],
                text_of: Callable[[Sequence[int]], str]) -> list[Candidate]:
    pairs: list[tuple[str, Predicate]] = []
    for combo in combos:
        indexes = tuple(combo)
        if not indexes:
            raise ValueError("empty conjunction is not a statement")
        pairs.append((text_of(indexes),
                      lambda trace, indexes=indexes: all(terms[i].holds(trace) for i in indexes)))
    return from_predicates(pairs)


def decide(candidates: Sequence[Candidate], traces: Sequence[Trace],
           *, goal_judge: Predicate | None = None) -> dict[str, Any]:
    """Ask only when some real trace separates the candidates."""
    if len(candidates) < 2 or not traces:
        return {
            "schema": SCHEMA,
            "action": NO_QUESTION,
            "reason": "NO_ALTERNATIVES" if len(candidates) < 2 else "NO_TRACES",
            "candidates": len(candidates), "traces": len(traces),
            "distinct_verdict_vectors": len({tuple(c.holds(t) for t in traces)
                                             for c in candidates}),
            "distinguishing_runs": 0, "questions": 0,
            "mismatches_with_goal_judge": {},
        }
    vectors = {c.candidate_id: tuple(bool(c.holds(t)) for t in traces) for c in candidates}
    behaviours = set(vectors.values())
    distinguishing = [i for i in range(len(traces))
                      if len({vector[i] for vector in vectors.values()}) > 1]
    mismatches: dict[str, int] = {}
    if goal_judge is not None:
        expected = [bool(goal_judge(trace)) for trace in traces]
        mismatches = {
            c.candidate_id: sum(vectors[c.candidate_id][i] != expected[i]
                                for i in range(len(expected))) for c in candidates
        }
    if len(behaviours) == 1:
        return {
            "schema": SCHEMA, "action": NO_QUESTION,
            "reason": "IDENTICAL_VERDICTS_ON_REAL_RUNS",
            "candidates": len(candidates), "traces": len(traces),
            "distinct_verdict_vectors": 1, "distinguishing_runs": 0, "questions": 0,
            "mismatches_with_goal_judge": mismatches,
            "candidate_texts": [c.text for c in candidates],
        }
    return {
        "schema": SCHEMA, "action": ASK_USER,
        "reason": "REAL_RUN_SEPARATES_CANDIDATES",
        "candidates": len(candidates), "traces": len(traces),
        "distinct_verdict_vectors": len(behaviours),
        "distinguishing_runs": len(distinguishing),
        "first_distinguishing_run": distinguishing[0],
        "questions": max(1, math.ceil(math.log2(len(behaviours)))),
        "mismatches_with_goal_judge": mismatches,
        "candidate_texts": [c.text for c in candidates],
    }


def ask_payload(decision: Mapping[str, Any]) -> dict[str, Any] | None:
    if decision.get("action") != ASK_USER:
        return None
    return {
        "kind": "RESIDUAL_STATEMENT_CHOICE",
        "question_id": "distinguishing-run-" + str(decision["first_distinguishing_run"]),
        "options": [{"candidate_id": candidate_id(text), "text": text}
                    for text in decision["candidate_texts"]],
        "questions": decision["questions"],
        "evidence": "real held-out runs, not model preference",
    }
