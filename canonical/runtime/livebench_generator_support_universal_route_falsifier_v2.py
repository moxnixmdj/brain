#!/usr/bin/env python3
"""Falsify the full-generator-support universal LiveBench threshold route.

This theorem is deliberately population-agnostic and terminal-row-free. It
uses one reachable, conflict-compatible historical-generator parameterization:

  keywords:forbidden_words = ["other"]
  startend:end_checker     = "Any other questions?"

The exact frozen checker semantics make these obligations mutually exclusive:
EndChecker requires the normalized response to end with the exact phrase, while
ForbiddenWords rejects a whole-word match for "other". The phrase itself
contains "other" as a whole word. Therefore at most one of the two checkers can
be true for any response.

Under the frozen LiveBench score rule
  (all_true_binary + true_fraction) / 2
the maximum score of that two-checker case is 1/4, below 0.6573775.

This does NOT say the frozen terminal 200-row population contains that case.
It proves only that arbitrary generator-support-wide worst-case threshold
proofs are impossible and must not be used as the acceptance route.
"""
from __future__ import annotations

import re
from fractions import Fraction

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_GENERATOR_SUPPORT_UNIVERSAL_ROUTE_FALSIFIER_V2"
FORBIDDEN_WORD = "other"
END_PHRASE = "Any other questions?"
IDS = (
    "keywords:forbidden_words",
    "startend:end_checker",
)
OPUS55_FLOOR = Fraction(262951, 400000)  # 0.6573775


def end_phrase_forces_forbidden_word() -> bool:
    """Pure string theorem mirroring the frozen checker predicates."""
    return re.search(
        r"\b" + re.escape(FORBIDDEN_WORD) + r"\b",
        END_PHRASE,
        flags=re.IGNORECASE,
    ) is not None


def strict_score(all_true: bool, true_count: int, instruction_count: int) -> Fraction:
    if instruction_count <= 0:
        raise ValueError("instruction_count must be positive")
    if not 0 <= true_count <= instruction_count:
        raise ValueError("true_count outside instruction_count")
    return (Fraction(1 if all_true else 0, 1) + Fraction(true_count, instruction_count)) / 2


def prove() -> dict:
    compatible = archetypes.compatible(IDS)
    phrase_collision = end_phrase_forces_forbidden_word()
    if not compatible:
        raise RuntimeError("COUNTEREXAMPLE_IDS_NOT_CONFLICT_COMPATIBLE")
    if not phrase_collision:
        raise RuntimeError("END_PHRASE_NO_LONGER_CONTAINS_FORBIDDEN_WHOLE_WORD")

    # Mutual exclusion:
    #   EndChecker(response) == True
    #     => normalized response endswith END_PHRASE
    #     => response contains whole-word FORBIDDEN_WORD
    #     => ForbiddenWords(response) == False.
    # Hence both cannot be true, so true_count <= 1 and all_true is false.
    upper = strict_score(False, 1, 2)
    if upper != Fraction(1, 4):
        raise RuntimeError("SCORE_UPPER_BOUND_DRIFT")
    if not upper < OPUS55_FLOOR:
        raise RuntimeError("COUNTEREXAMPLE_NO_LONGER_BELOW_COMPARATOR")

    return {
        "schema": SCHEMA,
        "status": "PASS__GENERATOR_SUPPORT_UNIVERSAL_THRESHOLD_ROUTE_FALSIFIED",
        "counterexample": {
            "instruction_ids": list(IDS),
            "forbidden_words": [FORBIDDEN_WORD],
            "end_phrase": END_PHRASE,
            "conflict_compatible": compatible,
            "joint_satisfiable": False,
            "maximum_simultaneously_true": 1,
        },
        "score": {
            "maximum_case_score_fraction": "1/4",
            "maximum_case_score": float(upper),
            "opus55_floor_fraction": "262951/400000",
            "opus55_floor": float(OPUS55_FLOOR),
            "below_comparator": upper < OPUS55_FLOOR,
        },
        "deduction": {
            "full_generator_support_per_case_floor_ge_comparator": False,
            "actual_frozen_population_contains_counterexample": "NOT_CLAIMED",
            "actual_frozen_population_score": "NOT_CLAIMED",
            "acceptance_credit": False,
        },
        "terminal_rows_read": 0,
        "terminal_case_metadata_read": 0,
        "model_dependency_count": 0,
        "network_dependency_count": 0,
    }


def run(args=None, root=None):
    return prove()


if __name__ == "__main__":
    import json
    print(json.dumps(prove(), indent=2, sort_keys=True))
