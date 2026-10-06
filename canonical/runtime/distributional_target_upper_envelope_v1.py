"""Finite falsifier kernel for deployed distributional dominance semantics.

This is not a proof of the general theorem. It makes several failure modes
executable on finite outcome spaces:
- probability mass matters, not just support;
- declared terminal evaluators must weakly improve;
- hard constraints must not regress;
- opaque external capability execution is not ownership;
- a library portfolio is not enough if the deployed context-conditioned router
  cannot reach the required behavior.
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
    """Return whether one finite law weakly dominates another."""
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


def portfolio_upper_envelope_covered(
    brain_candidates: Sequence[Mapping[str, Any]],
    target_laws: Sequence[Mapping[str, float]],
    *,
    evaluators: Sequence[Mapping[str, float]],
    hard_constraints: Sequence[Mapping[str, Any]] = (),
) -> bool:
    """Legacy existential-portfolio check.

    This is intentionally retained as a falsification control. A pass here is
    insufficient for terminal capability because it does not prove that the
    deployed router reaches the right policy from the actual external context.
    """
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


def deployed_kernel_dominates(
    brain_by_context: Mapping[str, Mapping[str, Any]],
    target_by_context: Mapping[str, Mapping[str, float]],
    *,
    evaluators_by_context: Mapping[str, Sequence[Mapping[str, float]]],
    hard_constraints_by_context: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> bool:
    """Compare actual deployed Brain and target laws under the same contexts.

    Each Brain row must be marked brain_owned=True and carry the law that the
    deployed router actually induces for that context. Merely having a better
    law somewhere else in the library is insufficient.
    """
    if not target_by_context:
        raise DistributionalEnvelopeError("TARGET_CONTEXTS_REQUIRED")
    constraints = hard_constraints_by_context or {}

    for context, target_law in target_by_context.items():
        brain_row = brain_by_context.get(context)
        if not isinstance(brain_row, Mapping):
            return False
        if brain_row.get("brain_owned") is not True:
            return False
        brain_law = brain_row.get("law")
        if not isinstance(brain_law, Mapping):
            return False
        evaluators = evaluators_by_context.get(context)
        if not evaluators:
            raise DistributionalEnvelopeError(
                f"MISSING_EVALUATORS_FOR_CONTEXT:{context}"
            )
        if not weakly_dominates(
            brain_law,
            target_law,
            evaluators=evaluators,
            hard_constraints=constraints.get(context, ()),
        ):
            return False

    return True


target_upper_envelope_covered = portfolio_upper_envelope_covered
