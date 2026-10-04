#!/usr/bin/env python3
"""Distribution-free pointwise optimality certificate kernel for frozen LiveBench IF.

This module contains no terminal prompts, rows, kwargs, responses, or scores.
It formalizes a small theorem over the frozen public scorer:

For a case with k boolean checkers, score depends only on g, the number true,
plus the all-true bonus. If a candidate response makes g checkers true and
EVERY subset of size g+1 is independently proved jointly UNSAT, then no response
can make more than g checkers true. Therefore the candidate is pointwise
score-optimal for that case.

The semantic UNSAT proofs are external inputs to this structural kernel. This
module never invents or infers them.
"""
from __future__ import annotations

from fractions import Fraction
from itertools import combinations
from math import comb
from typing import Iterable, Sequence

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_POINTWISE_OPTIMALITY_CERTIFICATE_V1"
MAX_FROZEN_LEGACY_CHECKERS_PER_CASE = 5


class CertificateError(ValueError):
    pass


def exact_score(k: int, g: int) -> Fraction:
    if k <= 0:
        raise CertificateError("K_MUST_BE_POSITIVE")
    if not 0 <= g <= k:
        raise CertificateError("G_OUT_OF_RANGE")
    return Fraction(1, 1) if g == k else Fraction(g, 2 * k)


def required_next_cardinality_subsets(k: int, g: int) -> tuple[tuple[int, ...], ...]:
    """Return the minimal subset family whose UNSAT proves g is maximal.

    If g == k, the candidate already has full score and no UNSAT proof is needed.
    Otherwise, any hypothetical response satisfying >g checkers necessarily
    satisfies at least one subset of exactly g+1 checkers. Proving all such
    subsets UNSAT therefore proves no response can exceed g.
    """
    if k <= 0:
        raise CertificateError("K_MUST_BE_POSITIVE")
    if k > MAX_FROZEN_LEGACY_CHECKERS_PER_CASE:
        raise CertificateError("K_EXCEEDS_FROZEN_GENERATOR_BOUND")
    if not 0 <= g <= k:
        raise CertificateError("G_OUT_OF_RANGE")
    if g == k:
        return ()
    return tuple(combinations(range(k), g + 1))


def verify_pointwise_optimality_structure(
    checker_results: Sequence[bool],
    independently_verified_unsat_subsets: Iterable[Iterable[int]],
) -> dict:
    """Verify the finite structural certificate for pointwise score optimality.

    The caller is responsible for independently verifying that every supplied
    subset really is jointly UNSAT under exact pinned checker semantics.
    """
    flags = tuple(bool(x) for x in checker_results)
    if not flags:
        raise CertificateError("CHECKER_RESULTS_REQUIRED")
    k = len(flags)
    if k > MAX_FROZEN_LEGACY_CHECKERS_PER_CASE:
        raise CertificateError("K_EXCEEDS_FROZEN_GENERATOR_BOUND")
    g = sum(flags)

    required = set(required_next_cardinality_subsets(k, g))
    supplied: set[tuple[int, ...]] = set()
    for raw in independently_verified_unsat_subsets:
        subset = tuple(sorted(int(i) for i in raw))
        if len(subset) != len(set(subset)):
            raise CertificateError("DUPLICATE_INDEX_IN_UNSAT_SUBSET")
        if any(i < 0 or i >= k for i in subset):
            raise CertificateError("UNSAT_SUBSET_INDEX_OUT_OF_RANGE")
        supplied.add(subset)

    missing = sorted(required - supplied)
    complete = not missing
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__POINTWISE_OPTIMALITY_STRUCTURE_COMPLETE"
            if complete
            else "FAIL_CLOSED__MISSING_NEXT_CARDINALITY_UNSAT_CERTIFICATES"
        ),
        "checker_count": k,
        "candidate_true_checker_count": g,
        "candidate_exact_score_numerator": exact_score(k, g).numerator,
        "candidate_exact_score_denominator": exact_score(k, g).denominator,
        "required_unsat_subset_cardinality": None if g == k else g + 1,
        "required_unsat_subset_count": len(required),
        "supplied_unsat_subset_count": len(supplied),
        "missing_unsat_subsets": [list(x) for x in missing],
        "pointwise_optimality_follows_if_supplied_unsat_proofs_are_semantically_valid": complete,
        "terminal_data_used": False,
        "acceptance_credit": False,
    }


def frozen_bound() -> dict:
    """Maximum structural certificate fanout under k <= 5."""
    worst = max(
        (comb(k, g + 1), k, g)
        for k in range(1, MAX_FROZEN_LEGACY_CHECKERS_PER_CASE + 1)
        for g in range(k)
    )
    return {
        "schema": SCHEMA,
        "max_checkers_per_case": MAX_FROZEN_LEGACY_CHECKERS_PER_CASE,
        "max_required_unsat_subsets": worst[0],
        "attained_at_checker_count": worst[1],
        "attained_at_candidate_true_count": worst[2],
        "terminal_data_used": False,
    }


def run(args=None, root=None):
    return frozen_bound()


if __name__ == "__main__":
    import json
    print(json.dumps(frozen_bound(), indent=2, sort_keys=True))
