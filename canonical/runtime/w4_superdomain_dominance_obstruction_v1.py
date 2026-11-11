"""Executable counterexample kernel for the unrestricted W4 transducer-superdomain dominance route.

This proves only a no-go theorem: if the candidate domain contains every transducer
and the evaluator class is unrestricted, no fixed Brain policy can dominate every
candidate transducer. It grants no acceptance or execution authority.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any

SCHEMA = "PROJECT_BRAIN_W4_SUPERDOMAIN_DOMINANCE_OBSTRUCTION_KERNEL_V1"


class ObstructionError(ValueError):
    pass


def binary_counterwitness(probability_y1: Fraction) -> dict[str, Any]:
    """Construct a deterministic transducer/evaluator pair beating Brain.

    probability_y1 is Brain's probability of output y1 at one admissible history.
    The other output y0 has probability 1-probability_y1.
    """
    p1 = Fraction(probability_y1)
    if p1 < 0 or p1 > 1:
        raise ObstructionError("PROBABILITY_OUT_OF_RANGE")
    p0 = 1 - p1

    # Choose an output Brain does not emit with probability one.
    if p1 < 1:
        y_star = "y1"
        brain_score = p1
    else:
        y_star = "y0"
        brain_score = p0

    competitor_score = Fraction(1, 1)
    if not competitor_score > brain_score:
        raise ObstructionError("COUNTERWITNESS_NOT_STRICT")

    return {
        "schema": SCHEMA,
        "status": "COUNTERWITNESS",
        "y_star": y_star,
        "brain_expected_score": str(brain_score),
        "competitor_expected_score": "1",
        "strictly_better": True,
        "theorem": "UNRESTRICTED_ALL_TRANSDUCER_DOMINANCE_NO_GO",
        "acceptance_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def verify_binary_universal_obstruction() -> dict[str, Any]:
    # Boundary and representative interior points exercise both deterministic and
    # stochastic cases. The universal step is algebraic in binary_counterwitness:
    # for p<1 choose y1 (1>p), while for p=1 choose y0 (1>0).
    probes = [
        Fraction(0, 1),
        Fraction(1, 1000),
        Fraction(1, 4),
        Fraction(1, 2),
        Fraction(3, 4),
        Fraction(999, 1000),
        Fraction(1, 1),
    ]
    receipts = [binary_counterwitness(p) for p in probes]
    if not all(r["strictly_better"] for r in receipts):
        raise ObstructionError("PROBE_FAILURE")
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "proof_shape": "FOR_ALL_p_IN_[0,1]__IF_p_LT_1_THEN_1_GT_p__ELSE_p_EQ_1_AND_1_GT_0",
        "probe_count": len(receipts),
        "unrestricted_superdomain_dominance_possible": False,
        "requires_target_evaluator_restriction_to_reopen": True,
        "acceptance_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
