from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

TOL = 1e-12

class OutcomeOrderError(ValueError):
    pass

@dataclass(frozen=True)
class Comparison:
    weakly_dominates: bool
    utility_margins: tuple[tuple[str,float], ...]
    hard_risk_margins: tuple[tuple[str,float], ...]


def _validate_distribution(p: Mapping[str,float]) -> None:
    if not p:
        raise OutcomeOrderError("EMPTY_DISTRIBUTION")
    vals=list(p.values())
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or x < -TOL for x in vals):
        raise OutcomeOrderError("INVALID_PROBABILITY")
    if abs(sum(float(x) for x in vals)-1.0) > 1e-9:
        raise OutcomeOrderError("PROBABILITIES_MUST_SUM_TO_ONE")


def expectation(p: Mapping[str,float], functional: Mapping[str,float]) -> float:
    if set(p) != set(functional):
        raise OutcomeOrderError("OUTCOME_SPACE_MISMATCH")
    return sum(float(p[x])*float(functional[x]) for x in p)


def weakly_dominates(
    brain: Mapping[str,float],
    opus: Mapping[str,float],
    utilities: Mapping[str,Mapping[str,float]],
    hard_violation_risks: Mapping[str,Mapping[str,float]],
) -> Comparison:
    _validate_distribution(brain)
    _validate_distribution(opus)
    if set(brain) != set(opus):
        raise OutcomeOrderError("SEMANTIC_OUTCOME_SPACE_MISMATCH")
    if not utilities:
        raise OutcomeOrderError("NONEMPTY_UTILITY_FAMILY_REQUIRED")
    utility_margins=[]
    for name,u in sorted(utilities.items()):
        b=expectation(brain,u)
        o=expectation(opus,u)
        utility_margins.append((name,b-o))
    risk_margins=[]
    for name,h in sorted(hard_violation_risks.items()):
        b=expectation(brain,h)
        o=expectation(opus,h)
        # Positive means Brain is safer: Opus risk - Brain risk.
        risk_margins.append((name,o-b))
    ok=all(m >= -TOL for _,m in utility_margins) and all(m >= -TOL for _,m in risk_margins)
    return Comparison(ok,tuple(utility_margins),tuple(risk_margins))


def equivalent(
    a: Mapping[str,float],
    b: Mapping[str,float],
    utilities: Mapping[str,Mapping[str,float]],
    hard_violation_risks: Mapping[str,Mapping[str,float]],
)->bool:
    return (
        weakly_dominates(a,b,utilities,hard_violation_risks).weakly_dominates
        and weakly_dominates(b,a,utilities,hard_violation_risks).weakly_dominates
    )


def verify_finite_countermodels() -> dict:
    # Support-only false positive: both systems can succeed and fail, but reliability differs.
    outcomes={"success","failure"}
    success_u={"success":1.0,"failure":0.0}
    b={"success":0.51,"failure":0.49}
    o={"success":0.99,"failure":0.01}
    assert set(b)==set(o)==outcomes
    assert not weakly_dominates(b,o,{"success":success_u},{}).weakly_dominates

    # Same mean on one statistic is insufficient when a declared catastrophe functional distinguishes.
    outcomes2={"safe_low","safe_high","catastrophe"}
    mean_quality={"safe_low":0.0,"safe_high":2.0,"catastrophe":1.0}
    catastrophe={"safe_low":0.0,"safe_high":0.0,"catastrophe":1.0}
    b2={"safe_low":0.25,"safe_high":0.25,"catastrophe":0.50}
    o2={"safe_low":0.50,"safe_high":0.50,"catastrophe":0.0}
    assert abs(expectation(b2,mean_quality)-expectation(o2,mean_quality)) < TOL
    assert not weakly_dominates(
        b2,o2,{"mean_quality":mean_quality},{"catastrophe":catastrophe}
    ).weakly_dominates

    # Hard constraint cannot be compensated by more compensable utility.
    q={"good":10.0,"bad":0.0}
    violation={"good":1.0,"bad":0.0}
    b3={"good":0.9,"bad":0.1}
    o3={"good":0.8,"bad":0.2}
    assert expectation(b3,q)>expectation(o3,q)
    assert not weakly_dominates(b3,o3,{"quality":q},{"authority_violation":violation}).weakly_dominates

    # Incomparable trade-off fails closed in both directions.
    correctness={"fast_correct":1.0,"slow_correct":1.0,"fast_wrong":0.0}
    speed={"fast_correct":1.0,"slow_correct":0.0,"fast_wrong":1.0}
    a={"fast_correct":0.5,"slow_correct":0.5,"fast_wrong":0.0}
    c={"fast_correct":0.6,"slow_correct":0.0,"fast_wrong":0.4}
    u={"correctness":correctness,"speed":speed}
    assert not weakly_dominates(a,c,u,{}).weakly_dominates
    assert not weakly_dominates(c,a,u,{}).weakly_dominates

    return {
        "support_only_rejected":True,
        "mean_only_rejected_with_declared_tail_functional":True,
        "hard_constraint_compensation_rejected":True,
        "incomparable_tradeoff_fails_closed":True,
    }


def verify_order_laws(distributions: Sequence[Mapping[str,float]], utilities, hard_risks)->dict:
    if not distributions:
        raise OutcomeOrderError("DISTRIBUTIONS_REQUIRED")
    # Reflexivity.
    for p in distributions:
        if not weakly_dominates(p,p,utilities,hard_risks).weakly_dominates:
            raise OutcomeOrderError("REFLEXIVITY_FAILURE")
    # Transitivity over supplied arbitrary finite witnesses.
    for a in distributions:
        for b in distributions:
            for c in distributions:
                ab=weakly_dominates(a,b,utilities,hard_risks).weakly_dominates
                bc=weakly_dominates(b,c,utilities,hard_risks).weakly_dominates
                if ab and bc and not weakly_dominates(a,c,utilities,hard_risks).weakly_dominates:
                    raise OutcomeOrderError("TRANSITIVITY_FAILURE")
    # Mutual dominance defines equivalence; quotient antisymmetry is by equivalence-class identity.
    for a in distributions:
        for b in distributions:
            if weakly_dominates(a,b,utilities,hard_risks).weakly_dominates and weakly_dominates(b,a,utilities,hard_risks).weakly_dominates:
                if not equivalent(a,b,utilities,hard_risks):
                    raise OutcomeOrderError("EQUIVALENCE_FAILURE")
    return {
        "reflexive":True,
        "transitive":True,
        "mutual_dominance_defines_equivalence":True,
        "quotient_antisymmetry_by_equivalence_class":True,
    }
