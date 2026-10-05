"""Exact finite-outcome witness for the hidden-evaluator duality theorem.

For target distribution P and Brain distribution Q over the same finite
observable outcome space, universal expected-utility noninferiority over a class
containing every indicator utility holds iff P == Q.

This runtime proves/constructs only that mathematical fact. It does not prove
that any real Opus task has the unrestricted separating evaluator class.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Iterable, Sequence

SCHEMA = "PROJECT_BRAIN_OPUS55_HIDDEN_EVALUATOR_DUALITY_RUNTIME_V1"

class DualityError(ValueError):
    pass

def _fraction(x: Any) -> Fraction:
    if isinstance(x, Fraction):
        return x
    if isinstance(x, int):
        return Fraction(x, 1)
    if isinstance(x, str):
        return Fraction(x)
    raise DualityError("PROBABILITY_MUST_BE_INT_STRING_OR_FRACTION")

def _distribution(values: Sequence[Any], label: str) -> tuple[Fraction, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)) or not values:
        raise DualityError(label + "_INVALID")
    out=tuple(_fraction(x) for x in values)
    if any(x < 0 for x in out):
        raise DualityError(label + "_NEGATIVE")
    if sum(out, Fraction(0,1)) != 1:
        raise DualityError(label + "_NOT_NORMALIZED")
    return out

def indicator_separator(target: Sequence[Any], brain: Sequence[Any]) -> dict[str, Any]:
    """Return a target-favoring indicator event iff the distributions differ."""
    p=_distribution(target,"TARGET")
    q=_distribution(brain,"BRAIN")
    if len(p) != len(q):
        raise DualityError("OUTCOME_SPACE_SIZE_MISMATCH")
    if p == q:
        return {
            "schema":SCHEMA,
            "status":"EQUIVALENT",
            "separator_event":[],
            "target_probability":"0",
            "brain_probability":"0",
            "strict_gap":"0",
        }

    event=tuple(i for i,(pi,qi) in enumerate(zip(p,q)) if pi > qi)
    if not event:
        raise DualityError("INTERNAL_NO_POSITIVE_TARGET_GAP_DESPITE_UNEQUAL_NORMALIZED_DISTRIBUTIONS")
    pp=sum((p[i] for i in event),Fraction(0,1))
    qq=sum((q[i] for i in event),Fraction(0,1))
    if not pp > qq:
        raise DualityError("INTERNAL_SEPARATOR_NOT_STRICT")
    return {
        "schema":SCHEMA,
        "status":"SEPARATED",
        "separator_event":list(event),
        "target_probability":str(pp),
        "brain_probability":str(qq),
        "strict_gap":str(pp-qq),
        "witness_utility":"INDICATOR_OF_SEPARATOR_EVENT",
    }

def universal_indicator_noninferiority(target: Sequence[Any], brain: Sequence[Any]) -> dict[str, Any]:
    """Decide universal noninferiority for the all-indicators evaluator class."""
    witness=indicator_separator(target,brain)
    equal=witness["status"] == "EQUIVALENT"
    return {
        "schema":SCHEMA,
        "status":"PASS" if equal else "FAIL",
        "universal_noninferiority_over_all_indicator_utilities":equal,
        "distribution_equivalence":equal,
        "counterexample":None if equal else witness,
        "capability_credit_delta":0,
    }

def proof_route(*, exact: bool, restricted: bool, other_sound_noninferiority: bool) -> str:
    """Priority proof-carrying reduction; unknown/unproved cells stay residual."""
    for value in (exact,restricted,other_sound_noninferiority):
        if type(value) is not bool:
            raise DualityError("ROUTE_PREDICATES_MUST_BE_BOOL")
    if exact:
        return "E_EXACT_SOLVED"
    if restricted:
        return "M_RESTRICTED_SOLVED"
    if other_sound_noninferiority:
        return "OTHER_PROOF_CARRYING_SOLVED"
    return "EQUIVALENCE_RESIDUAL"
