"""GDPval shared-style hidden-evaluator boundary.

The exact rubric text "Overall formatting and style of the deliverable" is repeated
across many public GDPval tasks, but the text does not itself define a complete
style utility or presentation-dimension contract.

This wrapper reuses Brain's finite hidden-evaluator theorem:
Brain is weakly noninferior for every bounded hidden utility iff the Brain and
target outcome distributions are identical.

Therefore a repeated vague style label cannot justify a universal top policy for
nonidentical artifacts until the admissible style-evaluator class is restricted by
source-bound semantics or a stronger target-relation certificate.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping

from canonical.runtime.hidden_evaluator_dominance_boundary_v1 import (
    distinguishing_hidden_utility,
    hidden_evaluator_universal_noninferiority,
)

SCHEMA="PROJECT_BRAIN_GDPVAL_SHARED_STYLE_HIDDEN_EVALUATOR_BOUNDARY_V1"
CRITERION="Overall formatting and style of the deliverable"


def deterministic_distribution(outcome_id:str)->dict[str,Fraction]:
    if not isinstance(outcome_id,str) or not outcome_id.strip():
        raise ValueError("OUTCOME_ID_REQUIRED")
    return {outcome_id:Fraction(1,1)}


def analyze(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        raise ValueError("PAYLOAD_MAPPING_REQUIRED")
    criterion=payload.get("criterion")
    if criterion!=CRITERION:
        raise ValueError("EXACT_SHARED_STYLE_CRITERION_REQUIRED")
    target=payload.get("target_distribution")
    brain=payload.get("brain_distribution")
    if not isinstance(target,Mapping) or not isinstance(brain,Mapping):
        raise ValueError("EXACT_DISTRIBUTIONS_REQUIRED")

    universal=hidden_evaluator_universal_noninferiority(target,brain)
    witness=None if universal else distinguishing_hidden_utility(target,brain)
    return {
        "schema":SCHEMA,
        "status":"PASS__UNRESTRICTED_STYLE_UTILITY_NONINFERIOR" if universal else "BOUNDARY__UNIVERSAL_STYLE_NONINFERIORITY_NOT_IDENTIFIED",
        "criterion":CRITERION,
        "unrestricted_hidden_utility_noninferiority":universal,
        "distinguishing_hidden_utility_indicator_outcome":witness,
        "theorem":"FOR_EVERY_BOUNDED_HIDDEN_STYLE_UTILITY__BRAIN_NONINFERIOR_IFF_EXACT_OUTCOME_LAWS_MATCH",
        "scheduler_effect":(
            "STYLE_SEMANTICS_MUST_BE_RESTRICTED_BY_SOURCE_BOUND_COMPLETE_DIMENSIONS_OR_A_STRONGER_TARGET_RELATION"
            if not universal else
            "NO_STYLE_UTILITY_CAN_DISTINGUISH_THE_BOUND_OUTCOME_LAWS"
        ),
        "semantic_restriction_proved_by_this_runtime":False,
        "owner_style_relation_reproduced":False,
        "terminal_authority":False,
        "promotion_authority":False,
        "terminal_credit_delta":0,
    }
