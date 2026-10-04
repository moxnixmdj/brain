#!/usr/bin/env python3
"""Conditional arity and score-marginal theorem for historical LiveBench legacy generation.

This module is deliberately conditional. It proves consequences of the recovered
historical generator contract:
  - sample 2..5 distinct instruction ids (replace=False);
  - conflict repair only deletes instruction ids;
and of the pinned legacy IFEval scoring algebra.

It does NOT assert byte-level lineage from that historical generator to the
current frozen terminal rows. Therefore it grants no acceptance or capability
credit by itself.
"""
from __future__ import annotations

from fractions import Fraction
from itertools import combinations

from canonical.runtime import livebench_legacy15_composition_partition_v1 as partition

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_GENERATOR_MAX5_COMPLETION_BOUND_V1"
HISTORICAL_GENERATOR_COMMIT = "686be1e78a0ba8036d7e355bc406e1a265da5292"
HISTORICAL_GENERATOR_MAX_DRAW = 5
HISTORICAL_GENERATOR_MIN_DRAW = 2
TARGET_POPULATION = 200
TARGET_PERCENT = Fraction(263, 4) + Fraction(151, 4000)  # 65.73775 exactly


def case_score(instruction_count: int, guaranteed_following: int) -> Fraction:
    if instruction_count < 1:
        raise ValueError("INSTRUCTION_COUNT_MUST_BE_POSITIVE")
    if not 0 <= guaranteed_following <= instruction_count:
        raise ValueError("GUARANTEED_FOLLOWING_OUT_OF_RANGE")
    if guaranteed_following == instruction_count:
        return Fraction(1, 1)
    return Fraction(guaranteed_following, 2 * instruction_count)


def final_completion_marginal(instruction_count: int) -> Fraction:
    if instruction_count < 1:
        raise ValueError("INSTRUCTION_COUNT_MUST_BE_POSITIVE")
    return case_score(instruction_count, instruction_count) - case_score(
        instruction_count, instruction_count - 1
    )


def nonfinal_instruction_marginal(instruction_count: int) -> Fraction:
    if instruction_count < 2:
        raise ValueError("NEEDS_NONFINAL_INSTRUCTION")
    return Fraction(1, 2 * instruction_count)


def valid_active_subsets_up_to_max_draw() -> int:
    ids = sorted(partition.ACTIVE_IDS)
    total = 0
    for r in range(1, HISTORICAL_GENERATOR_MAX_DRAW + 1):
        for subset in combinations(ids, r):
            if partition.is_valid(subset):
                total += 1
    return total


def prove() -> dict:
    # Historical source draws without replacement from 2..5 ids, then its
    # conflict-repair pass only removes ids. Therefore output arity cannot grow.
    max_output_arity = HISTORICAL_GENERATOR_MAX_DRAW

    completion_marginals = {
        n: final_completion_marginal(n)
        for n in range(1, max_output_arity + 1)
    }
    min_completion = min(completion_marginals.values())

    nonfinal_marginals = {
        n: nonfinal_instruction_marginal(n)
        for n in range(2, max_output_arity + 1)
    }
    min_nonfinal = min(nonfinal_marginals.values())

    target_mass = Fraction(TARGET_POPULATION, 1) * TARGET_PERCENT / 100
    fully_completed_rows_sufficient = (
        target_mass.numerator + target_mass.denominator - 1
    ) // target_mass.denominator

    result = {
        "schema": SCHEMA,
        "status": "PASS__CONDITIONAL_ON_HISTORICAL_GENERATOR_LINEAGE",
        "historical_generator_commit": HISTORICAL_GENERATOR_COMMIT,
        "historical_generator_contract": {
            "initial_draw_min": HISTORICAL_GENERATOR_MIN_DRAW,
            "initial_draw_max": HISTORICAL_GENERATOR_MAX_DRAW,
            "draw_without_replacement": True,
            "conflict_repair_operation": "DELETE_ONLY",
        },
        "derived": {
            "maximum_output_instruction_count": max_output_arity,
            "duplicate_instruction_ids_possible_under_contract": False,
            "valid_active15_identity_subsets_size_1_to_5_upper_bound":
                valid_active_subsets_up_to_max_draw(),
            "minimum_nonfinal_instruction_score_marginal":
                f"{min_nonfinal.numerator}/{min_nonfinal.denominator}",
            "minimum_final_completion_score_marginal":
                f"{min_completion.numerator}/{min_completion.denominator}",
            "completion_marginal_formula": "1/2 + 1/(2n)",
            "target_population": TARGET_POPULATION,
            "target_percent": "65.73775",
            "target_score_mass":
                f"{target_mass.numerator}/{target_mass.denominator}",
            "fully_completed_rows_sufficient": fully_completed_rows_sufficient,
        },
        "lineage_requirement": (
            "NO_TERMINAL_CREDIT_UNLESS_THE_RECOVERED_HISTORICAL_GENERATOR_"
            "CONTRACT_IS_ADMISSIBLY_BOUND_TO_THE_CURRENT_FROZEN_POPULATION"
        ),
        "terminal_data_used": False,
        "acceptance_credit": False,
        "capability_credit": False,
    }

    assert result["derived"]["maximum_output_instruction_count"] == 5
    assert result["derived"]["valid_active15_identity_subsets_size_1_to_5_upper_bound"] == 928
    assert min_nonfinal == Fraction(1, 10)
    assert min_completion == Fraction(3, 5)
    assert target_mass == Fraction(5259, 40)  # 131.475
    assert fully_completed_rows_sufficient == 132
    return result


if __name__ == "__main__":
    import json
    print(json.dumps(prove(), indent=2, sort_keys=True))
