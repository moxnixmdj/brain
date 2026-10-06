"""Finite falsifier kernel for distributional target upper-envelope semantics.

This is not a proof of the general theorem. It only makes the repaired
semantic distinction executable on finite outcome spaces:
- probability mass matters, not just support;
- all declared terminal evaluators must weakly improve;
- hard constraints must not regress;
- only Brain-owned candidate laws are admissible.
"""
from __future__ import annotations

from typing import Mapping, Sequence, Any

EPS = 1e-12


class DistributionalEnvelopeError(ValueError):
    pass


def normalize_distribution(dist: Mapping[str, float]) -> dict[str, float]:
    if not isinstance(dist, Mapping) or not dist:
        raise DistributionalEnvelopeError("DISTRIBUTION_REQUIRED")
    out: dict[str, float] = {}
    total = 0.0
    for key, value in dist.items():
        p = float(value)
        if p < -EPS:
            raise DistributionalEnvelopeError("NEGATIVE_PROBABILITY")
        if p > EPS:
            out[str(key)] = p
        total += p
    if abs(total - 1.0) > 1e-9:
        raise DistributionalEnvelopeError("PROBABILITIES_MUST_SUM_TO_ONE")
    return out


def support(dist: Mapping[str, float]) -> frozenset[str]:
    return frozenset(normalize_distribution(dist))


def expected_value(dist: Mapping[str, float], evaluator: Mapping[str, float]) -> float:
    d = normalize_distribution(dist)
    return sum(p * float(evaluator.get(outcome, 0.0)) for outcome, p in d.items())


def weakly_dominates(
    brain: Mapping[str, float],
    target: Mapping[str, float],
    *,
    evaluators: Sequence[Mapping[str, float]],
    hard_constraints: Sequence[Mapping[str, Any]] = (),
) -> bool:
    """Return whether one finite law weakly dominates another.

    Evaluators are terminal-relevant score maps, all interpreted as higher
    is better. Each hard constraint contains:
      evaluator: score map
      threshold: lower bound
    A constraint is load-bearing only when the target law satisfies it. If so,
    the Brain law must also satisfy it.
    """
    b = normalize_distribution(brain)
    o = normalize_distribution(target)
    if not evaluators:
        raise DistributionalEnvelopeError("AT_LEAST_ONE_EVALUATOR_REQUIRED")

    for evaluator in evaluators:
        if expected_value(b, evaluator) + EPS < expected_value(o, evaluator):
            return False

    for rule in hard_constraints:
        evaluator = rule.get("evaluator")
        threshold = rule.get("threshold")
        if not isinstance(evaluator, Mapping) or threshold is None:
            raise DistributionalEnvelopeError("HARD_CONSTRAINT_INVALID")
        t = float(threshold)
        target_ok = expected_value(o, evaluator) + EPS >= t
        brain_ok = expected_value(b, evaluator) + EPS >= t
        if target_ok and not brain_ok:
            return False

    return True


def target_upper_envelope_covered(
    brain_candidates: Sequence[Mapping[str, Any]],
    target_laws: Sequence[Mapping[str, float]],
    *,
    evaluators: Sequence[Mapping[str, float]],
    hard_constraints: Sequence[Mapping[str, Any]] = (),
) -> bool:
    """Every target law must have at least one Brain-owned dominating law."""
    if not target_laws:
        raise DistributionalEnvelopeError("TARGET_LAWS_REQUIRED")

    owned = []
    for row in brain_candidates:
        if row.get("brain_owned") is True and isinstance(row.get("law"), Mapping):
            owned.append(row["law"])

    if not owned:
        return False

    for target in target_laws:
        if not any(
            weakly_dominates(
                candidate,
                target,
                evaluators=evaluators,
                hard_constraints=hard_constraints,
            )
            for candidate in owned
        ):
            return False
    return True
