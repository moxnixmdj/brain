"""Formal open-world proposal bounds for the H100 research path.

This module proves two facts.

1) A uniform positive proposal-mass lower bound over an unbounded countable set
   of distinct novel structural families is impossible for any normalized
   probability distribution.

2) A prefix-free universal program search can still give every finite
   description a strictly positive, complexity-conditioned mass and a
   deterministic dovetail bound.  The price is exponential dependence on
   description length, not persistent learned bytes.

No benchmark outcomes or learned models are used.
"""
from __future__ import annotations

import math
from typing import Iterable

SCHEMA="PROJECT_BRAIN_H100_UNIVERSAL_PROPOSAL_BOUND_V1"


class ProposalBoundError(ValueError):
    pass


def quantitative_uniform_bound_ceiling(distinct_hypotheses: int) -> float:
    """Any PMF over N distinct hypotheses has min mass <= 1/N."""
    if not isinstance(distinct_hypotheses,int) or isinstance(distinct_hypotheses,bool) or distinct_hypotheses < 1:
        raise ProposalBoundError("DISTINCT_HYPOTHESES_INVALID")
    return 1.0/distinct_hypotheses


def uniform_positive_lower_bound_contradiction(epsilon: float) -> dict:
    """Return a finite witness N where N*epsilon>1.

    Therefore a normalized distribution cannot assign >=epsilon to every
    member of an unbounded family.
    """
    try:
        e=float(epsilon)
    except Exception as exc:
        raise ProposalBoundError("EPSILON_INVALID") from exc
    if not math.isfinite(e) or e <= 0.0 or e > 1.0:
        raise ProposalBoundError("EPSILON_OUT_OF_RANGE")
    n=math.floor(1.0/e)+1
    return {
        "epsilon":e,
        "finite_witness_count":n,
        "required_mass_if_all_ge_epsilon":n*e,
        "contradiction":n*e>1.0,
    }


def kraft_mass(code_lengths: Iterable[int]) -> float:
    lengths=list(code_lengths)
    if any(not isinstance(x,int) or isinstance(x,bool) or x < 1 for x in lengths):
        raise ProposalBoundError("CODE_LENGTH_INVALID")
    return math.fsum(2.0**(-x) for x in lengths)


def validate_prefix_lengths(code_lengths: Iterable[int]) -> dict:
    lengths=list(code_lengths)
    mass=kraft_mass(lengths)
    # Kraft <= 1 is necessary and sufficient for existence of a binary
    # prefix code with these lengths.
    return {
        "code_count":len(lengths),
        "kraft_mass":mass,
        "prefix_code_exists":mass <= 1.0 + 1e-15,
    }


def proposal_mass_lower_bound(code_length: int) -> float:
    """Universal prefix prior mass assigned to one exact code."""
    if not isinstance(code_length,int) or isinstance(code_length,bool) or code_length < 1:
        raise ProposalBoundError("CODE_LENGTH_INVALID")
    return 2.0**(-code_length)


def stochastic_n95_for_code_length(code_length: int) -> int:
    """IID draws from exact prefix mass; finite for every finite code length."""
    p=proposal_mass_lower_bound(code_length)
    # For huge lengths 1-p rounds to 1. Use log1p for stable finite lengths,
    # and the asymptotic conservative 3/p bound beyond floating resolution.
    if p >= 2.0**-52:
        return int(math.ceil(math.log(0.05)/math.log1p(-p)))
    return int(math.ceil(-math.log(0.05)/p))


def prefix_candidate_count_bound(max_code_length: int) -> int:
    """At most 2^L valid prefix-free codes can have length <= L.

    By Kraft, each such code contributes >=2^-L and total mass <=1.
    """
    if not isinstance(max_code_length,int) or isinstance(max_code_length,bool) or max_code_length < 1:
        raise ProposalBoundError("MAX_CODE_LENGTH_INVALID")
    return 1 << max_code_length


def deterministic_dovetail_step_bound(max_code_length: int, verifier_steps: int) -> int:
    """Candidate-step upper bound for exhaustive prefix-code dovetailing.

    If a useful candidate has code length <=L and can be verified in <=T
    candidate-steps, exhaustive fair search over all valid candidates of
    length <=L can find it within at most 2^L*T candidate-steps.
    """
    if not isinstance(verifier_steps,int) or isinstance(verifier_steps,bool) or verifier_steps < 1:
        raise ProposalBoundError("VERIFIER_STEPS_INVALID")
    return prefix_candidate_count_bound(max_code_length)*verifier_steps


def certificate(code_length: int, verifier_steps: int) -> dict:
    p=proposal_mass_lower_bound(code_length)
    return {
        "schema":SCHEMA,
        "status":"FORMAL_COMPLEXITY_CONDITIONED_OPEN_WORLD_PROPOSAL_GUARANTEE",
        "code_length_bits":code_length,
        "proposal_mass_lower_bound":p,
        "stochastic_n95_proposals":stochastic_n95_for_code_length(code_length),
        "verifier_steps":verifier_steps,
        "deterministic_dovetail_candidate_step_bound":deterministic_dovetail_step_bound(code_length,verifier_steps),
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "deduction":[
            "UNIFORM_POSITIVE_P_LOWER_OVER_ARBITRARILY_MANY_DISTINCT_FAMILIES_IS_IMPOSSIBLE",
            "EVERY_FINITE_PREFIX_DESCRIPTION_CAN_STILL_RECEIVE_STRICTLY_POSITIVE_MASS",
            "OPEN_WORLD_COMPLETENESS_IS_COMPLEXITY_CONDITIONED_AND_PAYS_EXPONENTIAL_RUNTIME_IN_DESCRIPTION_LENGTH",
        ],
        "hard_nonclaims":[
            "DOES_NOT_PROVE_REAL_TARGETS_HAVE_SHORT_DESCRIPTIONS",
            "DOES_NOT_PROVE_PRACTICAL_WALL_CLOCK",
            "DOES_NOT_PROVE_VERIFICATION_IS_CHEAP_OR_DECIDABLE_FOR_ALL_TASKS",
            "DOES_NOT_PROVE_FULL_H100_TERMINAL_SUCCESS",
        ],
        "h100_terminal_credit_delta":0,
    }
