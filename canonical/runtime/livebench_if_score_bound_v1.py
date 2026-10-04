#!/usr/bin/env python3
"""Exact score-bound arithmetic for the frozen LiveBench IF scorer.

This module does not read benchmark prompts, question ids, hidden kwargs, or
terminal answers.  It only implements the public score algebra used by the
pinned LiveBench IFBench evaluator so a precommitted successor can prove a
threshold from conservative per-question checker guarantees.

For a question with k instruction checkers and g checkers *guaranteed* true:
- if g == k, the exact score is guaranteed to be 1;
- otherwise the all-instructions term cannot be guaranteed, so the safe lower
  bound is (g/k)/2.

Unknown checkers are therefore safely treated as false rather than guessed.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import ceil
from typing import Iterable

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_IF_SCORE_BOUND_V1"


class ScoreBoundError(ValueError):
    pass


@dataclass(frozen=True)
class CaseGuarantee:
    instruction_count: int
    guaranteed_following: int

    def validate(self) -> None:
        if self.instruction_count <= 0:
            raise ScoreBoundError("INSTRUCTION_COUNT_MUST_BE_POSITIVE")
        if not 0 <= self.guaranteed_following <= self.instruction_count:
            raise ScoreBoundError("GUARANTEED_FOLLOWING_OUT_OF_RANGE")


def exact_score_from_checker_results(results: Iterable[bool]) -> Fraction:
    flags = tuple(bool(x) for x in results)
    if not flags:
        raise ScoreBoundError("CHECKER_RESULTS_REQUIRED")
    k = len(flags)
    g = sum(flags)
    all_term = 1 if g == k else 0
    return (Fraction(all_term, 1) + Fraction(g, k)) / 2


def conservative_case_lower_bound(case: CaseGuarantee) -> Fraction:
    case.validate()
    k = case.instruction_count
    g = case.guaranteed_following
    if g == k:
        return Fraction(1, 1)
    return Fraction(g, 2 * k)


def population_lower_bound(cases: Iterable[CaseGuarantee]) -> Fraction:
    rows = tuple(cases)
    if not rows:
        raise ScoreBoundError("CASES_REQUIRED")
    return sum((conservative_case_lower_bound(x) for x in rows), Fraction()) / len(rows)


def percent(value: Fraction) -> Fraction:
    return value * 100


def threshold_met(cases: Iterable[CaseGuarantee], threshold_percent: Fraction) -> bool:
    return percent(population_lower_bound(cases)) >= threshold_percent


def minimum_full_score_cases_if_all_others_zero(
    population_count: int,
    threshold_percent: Fraction,
) -> int:
    if population_count <= 0:
        raise ScoreBoundError("POPULATION_COUNT_MUST_BE_POSITIVE")
    if threshold_percent < 0 or threshold_percent > 100:
        raise ScoreBoundError("THRESHOLD_PERCENT_OUT_OF_RANGE")
    required = Fraction(population_count, 1) * threshold_percent / 100
    return ceil(required)


def maximum_zero_score_cases_if_all_others_full(
    population_count: int,
    threshold_percent: Fraction,
) -> int:
    return population_count - minimum_full_score_cases_if_all_others_zero(
        population_count, threshold_percent
    )


def livebench_2026_06_25_sufficient_full_score_cut() -> dict:
    """Public arithmetic consequence of N=200 and the frozen 65.7 bar."""
    threshold = Fraction(657, 10)
    population = 200
    required = minimum_full_score_cases_if_all_others_zero(population, threshold)
    return {
        "schema": SCHEMA,
        "population_count": population,
        "threshold_percent": "65.7",
        "minimum_full_score_cases_if_all_others_zero": required,
        "maximum_zero_score_cases_if_all_others_full": population - required,
        "lower_neighbor_percent": str(Fraction(required - 1, population) * 100),
        "cut_percent": str(Fraction(required, population) * 100),
        "interpretation": (
            "132 full-score cases with every other case scored zero is sufficient; "
            "131 is insufficient. Partial checker credit can reduce the number of "
            "full-score cases required, so 132 is a sufficient cut, not a necessary one."
        ),
        "terminal_data_read": False,
        "incremental_spend_usd": 0,
        "acceptance_credit": False,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(livebench_2026_06_25_sufficient_full_score_cut(), indent=2, sort_keys=True))
