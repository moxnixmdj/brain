#!/usr/bin/env python3
"""Exact lower-bound certificate for LiveBench instruction-following scores.

The frozen LiveBench scorer assigns, per prompt:
    0.5 * all_instructions_followed + 0.5 * fraction_instructions_followed

This module computes a conservative score floor when a caller can prove that a
set of instruction constraints is supported. Every unsupported constraint is
assumed to fail. It deliberately carries no terminal-case data and grants no
acceptance or promotion authority.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Mapping

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_THRESHOLD_SUFFICIENCY_V1"


def _validate_counts(total_constraints: int, unsupported_constraints: int) -> None:
    if not isinstance(total_constraints, int) or not isinstance(unsupported_constraints, int):
        raise ValueError("COUNTS_MUST_BE_INTEGERS")
    if total_constraints < 1:
        raise ValueError("TOTAL_CONSTRAINTS_MUST_BE_POSITIVE")
    if unsupported_constraints < 0:
        raise ValueError("UNSUPPORTED_MUST_BE_NONNEGATIVE")
    if unsupported_constraints > total_constraints:
        raise ValueError("UNSUPPORTED_EXCEEDS_TOTAL")


def prompt_score_lower_bound(total_constraints: int, unsupported_constraints: int) -> Fraction:
    """Return the exact frozen-scorer floor if supported constraints all pass.

    Unsupported constraints are pessimistically counted as failures. This is a
    mathematical implication only; it does not prove that any constraint is in
    fact supported by the Brain.
    """
    _validate_counts(total_constraints, unsupported_constraints)
    followed = total_constraints - unsupported_constraints
    all_followed = Fraction(1 if unsupported_constraints == 0 else 0, 1)
    instruction_fraction = Fraction(followed, total_constraints)
    return (all_followed + instruction_fraction) / 2


def aggregate_score_lower_bound(histogram: Mapping[tuple[int, int], int]) -> Fraction:
    """Aggregate exact prompt floors from {(total, unsupported): prompt_count}."""
    if not histogram:
        raise ValueError("HISTOGRAM_REQUIRED")
    weighted = Fraction(0, 1)
    prompt_count = 0
    for key, count in histogram.items():
        if not isinstance(key, tuple) or len(key) != 2:
            raise ValueError("HISTOGRAM_KEY_MUST_BE_TOTAL_UNSUPPORTED_PAIR")
        total_constraints, unsupported_constraints = key
        _validate_counts(total_constraints, unsupported_constraints)
        if not isinstance(count, int) or count < 0:
            raise ValueError("PROMPT_COUNT_MUST_BE_NONNEGATIVE_INTEGER")
        weighted += prompt_score_lower_bound(total_constraints, unsupported_constraints) * count
        prompt_count += count
    if prompt_count < 1:
        raise ValueError("POSITIVE_PROMPT_COUNT_REQUIRED")
    return weighted / prompt_count


def certificate(
    histogram: Mapping[tuple[int, int], int],
    threshold: Fraction = Fraction(657, 1000),
) -> dict:
    """Return a fail-closed, exact-arithmetic threshold sufficiency certificate."""
    if not isinstance(threshold, Fraction):
        raise ValueError("THRESHOLD_MUST_BE_FRACTION")
    if threshold < 0 or threshold > 1:
        raise ValueError("THRESHOLD_OUT_OF_RANGE")
    floor = aggregate_score_lower_bound(histogram)
    margin = floor - threshold
    return {
        "schema": SCHEMA,
        "status": "PASS" if margin >= 0 else "INSUFFICIENT",
        "score_lower_bound_fraction": f"{floor.numerator}/{floor.denominator}",
        "score_lower_bound_decimal": float(floor),
        "threshold_fraction": f"{threshold.numerator}/{threshold.denominator}",
        "threshold_decimal": float(threshold),
        "margin_fraction": f"{margin.numerator}/{margin.denominator}",
        "margin_decimal": float(margin),
        "unsupported_constraints_assumed_fail": True,
        "supported_constraints_assumed_pass": True,
        "terminal_case_data_used": False,
        "terminal_authority": False,
        "acceptance_credit": False,
        "hard_nonclaim": (
            "PASS_PROVES_ONLY_THRESHOLD_SUFFICIENCY_CONDITIONAL_ON_THE_INPUT_"
            "HISTOGRAM_AND_SUPPORTED_CONSTRAINT_ASSUMPTION; IT_DOES_NOT_PROVE_"
            "POPULATION_IDENTITY_OR_CONSTRUCTOR_SOUNDNESS"
        ),
    }
