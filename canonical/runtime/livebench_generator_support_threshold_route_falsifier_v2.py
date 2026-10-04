#!/usr/bin/env python3
"""Falsify the generator-support universal-threshold proof route for LiveBench IF.

This composes two already source-bound public facts:
1. the frozen active15 generator support contains an ID-compatible concrete
   slot tuple for which no response can satisfy both checkers; and
2. the frozen LiveBench IF score for a two-checker row with at most one true
   checker is at most 1/4.

Therefore no proof that assigns a per-row lower bound >= the target predicate
to every generator-admitted contract tuple can succeed. The 928-to-7 archetype
reduction remains useful for solver implementation and falsification, but it is
not by itself an acceptance proof for the fixed 200-row population.

No terminal row, hidden kwarg, terminal response, row frequency, or score is
read by this module.
"""
from __future__ import annotations

from fractions import Fraction

from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feasibility
from canonical.runtime.livebench_if_score_bound_v1 import exact_score_from_checker_results

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_GENERATOR_SUPPORT_THRESHOLD_ROUTE_FALSIFIER_V2"

TARGET_PREDICATE_FLOOR = Fraction(657, 1000)  # 65.7%
COUNTEREXAMPLE_IDS = (
    "keywords:forbidden_words",
    "length_constraints:nth_paragraph_first_word",
)


def verify() -> dict:
    slot = feasibility.prove_id_compatibility_is_not_satisfiability()
    if slot.get("status") != "PASS__ID_COMPATIBILITY_STRICTLY_WEAKER_THAN_SLOT_SATISFIABILITY":
        raise RuntimeError("UPSTREAM_SLOT_FEASIBILITY_THEOREM_NOT_PROVED")

    ids = tuple(slot.get("counterexample_instruction_ids") or ())
    if ids != COUNTEREXAMPLE_IDS:
        raise RuntimeError("COUNTEREXAMPLE_IDENTITY_DRIFT")

    reasons = set(slot.get("hard_unsat_reasons") or ())
    if "NTH_FIRST_WORD_IS_FORBIDDEN_WORD" not in reasons:
        raise RuntimeError("COUNTEREXAMPLE_UNSAT_CERTIFICATE_MISSING")

    # Joint UNSAT means at most one of the two checker booleans can be true.
    # The frozen public scorer is monotone in the checker-true count for a
    # non-all-true row, so [True, False] is the maximal possible score state.
    maximum_counterexample_score = exact_score_from_checker_results((True, False))
    if maximum_counterexample_score != Fraction(1, 4):
        raise RuntimeError("FROZEN_SCORE_ALGEBRA_DRIFT")
    if not maximum_counterexample_score < TARGET_PREDICATE_FLOOR:
        raise RuntimeError("COUNTEREXAMPLE_NO_LONGER_BELOW_TARGET_FLOOR")

    return {
        "schema": SCHEMA,
        "status": "PASS__UNIVERSAL_GENERATOR_SUPPORT_THRESHOLD_ROUTE_FALSIFIED",
        "target_predicate": "LIVEBENCH_IF_GE_65_7",
        "counterexample_instruction_ids": list(ids),
        "counterexample_hard_unsat_reason": "NTH_FIRST_WORD_IS_FORBIDDEN_WORD",
        "maximum_counterexample_score": "1/4",
        "target_predicate_floor": "657/1000",
        "deduction": [
            "RAW_ID_COMPATIBILITY_IS_NOT_CONCRETE_SLOT_SATISFIABILITY",
            "AT_LEAST_ONE_GENERATOR_ADMITTED_SLOT_CLASS_HAS_PER_ROW_SCORE_CEILING_1_OVER_4",
            "A_UNIVERSAL_PER_ROW_GENERATOR_SUPPORT_FLOOR_CANNOT_PROVE_LIVEBENCH_IF_GE_65_7",
            "THE_928_TO_7_REDUCTION_REMAINS_USEFUL_FOR_SOLVER_HARDENING_NOT_POPULATION_ACCEPTANCE_BY_ITSELF",
        ],
        "corrected_acceptance_routes": [
            "PRECOMMITTED_FIXED_POPULATION_EXECUTION_WITH_FROZEN_CANDIDATE_SCORER_AND_NONLEAKING_AGGREGATE_RECEIPT",
            "CONTENT_INDEPENDENT_FIXED_POPULATION_SCORE_MASS_PROOF_WITH_AN_ADMISSIBLE_SCOPE_BRIDGE",
        ],
        "next_minimum_cut": (
            "FINISH_EXACT_SYNTHETIC_SOLVER_FALSIFICATION_ONLY_TO_STABILIZE_THE_FROZEN_CANDIDATE__"
            "THEN_PRECOMMIT_AND_EXECUTE_ONE_CLEAN_FIXED_POPULATION_SCORE_RUN__"
            "DO_NOT_REQUIRE_UNIVERSAL_GENERATOR_SUPPORT_SATISFIABILITY"
        ),
        "terminal_row_content_read": False,
        "terminal_row_metadata_read": False,
        "terminal_case_frequency_inferred": False,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
    }


def run(args=None, root=None):
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
