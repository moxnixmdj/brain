"""Deterministic decision primitives for Brain cognitive-basis subtraction.

These functions cover only cases where the decision variables are explicit:
hard constraints, explicit outcome probabilities/utilities, explicit Bayesian
likelihoods, explicit observation models, and explicit execution authority.

They deliberately fail closed instead of inventing missing beliefs, utilities,
likelihoods, or intervention permissions.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log2, isfinite
from typing import Iterable, Mapping, Sequence, Hashable, Any

_EPS = 1e-9

@dataclass(frozen=True)
class ConstraintDecision:
    admissible: bool
    reasons: tuple[str, ...]

def hard_constraint_admissibility(
    candidate: Mapping[str, Any],
    *,
    required_equal: Mapping[str, Any] | None = None,
    forbidden_equal: Mapping[str, Any] | None = None,
    required_present: Iterable[str] = (),
    allowed_values: Mapping[str, Iterable[Any]] | None = None,
) -> ConstraintDecision:
    reasons: list[str] = []
    required_equal = required_equal or {}
    forbidden_equal = forbidden_equal or {}
    allowed_values = allowed_values or {}
    for key in required_present:
        if key not in candidate:
            reasons.append(f"MISSING:{key}")
    for key, expected in required_equal.items():
        if key not in candidate:
            reasons.append(f"MISSING:{key}")
        elif candidate[key] != expected:
            reasons.append(f"REQUIRED_EQUAL:{key}")
    for key, forbidden in forbidden_equal.items():
        if key in candidate and candidate[key] == forbidden:
            reasons.append(f"FORBIDDEN_EQUAL:{key}")
    for key, allowed in allowed_values.items():
        allowed_set = set(allowed)
        if key not in candidate:
            reasons.append(f"MISSING:{key}")
        elif candidate[key] not in allowed_set:
            reasons.append(f"NOT_ALLOWED:{key}")
    return ConstraintDecision(not reasons, tuple(reasons))

def _validate_distribution(dist: Mapping[Hashable, float], name: str) -> None:
    if not dist:
        raise ValueError(f"{name} must be non-empty")
    total = 0.0
    for key, p in dist.items():
        p = float(p)
        if not isfinite(p) or p < 0.0 or p > 1.0:
            raise ValueError(f"{name}[{key!r}] is not a probability")
        total += p
    if abs(total - 1.0) > _EPS:
        raise ValueError(f"{name} probabilities must sum to 1, got {total!r}")

def expected_utility(outcomes: Sequence[tuple[float, float]], *, fixed_cost: float = 0.0) -> float:
    if not outcomes:
        raise ValueError("outcomes must be non-empty")
    total_p = 0.0
    eu = -float(fixed_cost)
    for p, utility in outcomes:
        p = float(p)
        utility = float(utility)
        if not isfinite(p) or p < 0.0 or p > 1.0:
            raise ValueError("invalid outcome probability")
        if not isfinite(utility):
            raise ValueError("utility must be finite")
        total_p += p
        eu += p * utility
    if abs(total_p - 1.0) > _EPS:
        raise ValueError(f"outcome probabilities must sum to 1, got {total_p!r}")
    return eu

def rank_actions_by_expected_utility(
    actions: Mapping[Hashable, Sequence[tuple[float, float]]],
    *,
    fixed_costs: Mapping[Hashable, float] | None = None,
) -> list[tuple[Hashable, float]]:
    fixed_costs = fixed_costs or {}
    scored = [
        (action, expected_utility(outcomes, fixed_cost=float(fixed_costs.get(action, 0.0))))
        for action, outcomes in actions.items()
    ]
    return sorted(scored, key=lambda item: (-item[1], repr(item[0])))

def bayes_posterior(
    prior: Mapping[Hashable, float],
    likelihood: Mapping[Hashable, float],
) -> dict[Hashable, float]:
    _validate_distribution(prior, "prior")
    if set(prior) != set(likelihood):
        raise ValueError("likelihood keys must exactly match prior hypotheses")
    weights: dict[Hashable, float] = {}
    evidence = 0.0
    for h, p in prior.items():
        l = float(likelihood[h])
        if not isfinite(l) or l < 0.0 or l > 1.0:
            raise ValueError(f"likelihood[{h!r}] is not in [0,1]")
        w = float(p) * l
        weights[h] = w
        evidence += w
    if evidence <= 0.0:
        raise ValueError("observation has zero probability under all hypotheses")
    return {h: w / evidence for h, w in weights.items()}

def entropy_bits(dist: Mapping[Hashable, float]) -> float:
    _validate_distribution(dist, "distribution")
    return -sum(float(p) * log2(float(p)) for p in dist.values() if float(p) > 0.0)

def expected_information_gain(
    prior: Mapping[Hashable, float],
    observation_model: Mapping[Hashable, Mapping[Hashable, float]],
) -> float:
    """Expected entropy reduction in bits.

    observation_model[h][o] = P(o | h). Every hypothesis must define the same
    observation support and a normalized conditional distribution.
    """
    _validate_distribution(prior, "prior")
    if set(prior) != set(observation_model):
        raise ValueError("observation model hypotheses must match prior")
    observation_keys: set[Hashable] | None = None
    for h, cond in observation_model.items():
        _validate_distribution(cond, f"observation_model[{h!r}]")
        keys = set(cond)
        if observation_keys is None:
            observation_keys = keys
        elif keys != observation_keys:
            raise ValueError("all hypotheses must use identical observation support")
    if not observation_keys:
        raise ValueError("observation support must be non-empty")

    h_prior = entropy_bits(prior)
    expected_h_post = 0.0
    for obs in observation_keys:
        p_obs = sum(float(prior[h]) * float(observation_model[h][obs]) for h in prior)
        if p_obs <= 0.0:
            continue
        posterior = {
            h: float(prior[h]) * float(observation_model[h][obs]) / p_obs
            for h in prior
        }
        expected_h_post += p_obs * entropy_bits(posterior)
    gain = h_prior - expected_h_post
    return 0.0 if abs(gain) < 1e-12 else gain

def intervenability_from_authority(
    variable: Hashable,
    action_catalog: Mapping[Hashable, Sequence[Mapping[str, Any]]],
) -> str:
    """Return INTERVENABLE, NOT_INTERVENABLE, or UNKNOWN from explicit authority.

    Passive telemetry is intentionally not an input. Intervenability is an
    execution-authority fact: an enabled actuator/API action must exist and be
    policy-authorized. Explicitly denied/disabled actions yield NOT_INTERVENABLE.
    Missing metadata yields UNKNOWN and must fail closed upstream.
    """
    if variable not in action_catalog:
        return "UNKNOWN"
    actions = list(action_catalog[variable])
    if not actions:
        return "NOT_INTERVENABLE"
    saw_explicit = False
    for action in actions:
        enabled = action.get("enabled")
        allowed = action.get("policy_allowed")
        if enabled is None or allowed is None:
            continue
        saw_explicit = True
        if enabled is True and allowed is True:
            return "INTERVENABLE"
    return "NOT_INTERVENABLE" if saw_explicit else "UNKNOWN"
