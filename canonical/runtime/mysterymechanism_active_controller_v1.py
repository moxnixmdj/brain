"""Adaptive experiment controller for the public MysteryMechanism task contract.

The controller owns no hidden benchmark data and claims no benchmark score.  It
turns the public contract (two passive observations plus exactly 2d+1 active
experiments) into a deterministic active-discrimination loop:

1. acquire enough geometric coverage to make structure estimation identifiable;
2. synthesize multiple low-complexity mechanism candidates with V2;
3. spend each remaining experiment where surviving candidates disagree most;
4. submit only a stable executable candidate, otherwise fail closed.

This replaces the old "pre-plan the entire budget" behavior without changing
the zero-learned-byte boundary.
"""
from __future__ import annotations

import itertools
import math
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_zero_learned_mechanism_synthesizer_v1 as v1
from canonical.runtime import h100_zero_learned_mechanism_synthesizer_v2 as v2

SCHEMA = "PROJECT_BRAIN_MYSTERYMECHANISM_ACTIVE_CONTROLLER_V1"
_EPS = 1e-12


def _normalize_bounds(bounds: Mapping[str, Sequence[Any]]) -> dict[str, tuple[float, float]]:
    if not isinstance(bounds, Mapping) or not bounds:
        raise v1.MechanismSynthesisError("BOUNDS_REQUIRED")
    out: dict[str, tuple[float, float]] = {}
    for raw_name, raw_pair in bounds.items():
        name = str(raw_name).strip()
        if (
            not name
            or not isinstance(raw_pair, Sequence)
            or isinstance(raw_pair, (str, bytes))
            or len(raw_pair) != 2
        ):
            raise v1.MechanismSynthesisError("BOUND_INVALID")
        lo = v1._finite_number(raw_pair[0], name + "_lo")
        hi = v1._finite_number(raw_pair[1], name + "_hi")
        if not lo < hi:
            raise v1.MechanismSynthesisError("BOUND_ORDER_INVALID:" + name)
        out[name] = (lo, hi)
    return dict(sorted(out.items()))


def _point_key(point: Mapping[str, Any], names: Sequence[str]) -> tuple[float, ...]:
    return tuple(round(float(point[name]), 12) for name in names)


def _normalized_distance(
    a: Mapping[str, float],
    b: Mapping[str, float],
    bounds: Mapping[str, tuple[float, float]],
) -> float:
    return math.sqrt(sum(
        ((float(a[name]) - float(b[name])) / max(bounds[name][1] - bounds[name][0], _EPS)) ** 2
        for name in bounds
    ))


def _coverage_pool(bounds: Mapping[str, tuple[float, float]]) -> list[dict[str, float]]:
    names = list(bounds)
    axes: list[list[float]] = []
    for name in names:
        lo, hi = bounds[name]
        mid = math.sqrt(lo * hi) if lo > 0 and hi > 0 else (lo + hi) / 2.0
        axes.append([lo, mid, hi])
    pool: list[dict[str, float]] = []
    # Corners and center/grid points expose scale, interaction, and curvature.
    for values in itertools.product(*axes):
        pool.append(dict(zip(names, values)))
    return pool


def _observed_points(
    observations: Sequence[Mapping[str, Any]],
    names: Sequence[str],
) -> list[dict[str, float]]:
    out = []
    for i, row in enumerate(observations):
        if not isinstance(row, Mapping) or any(name not in row for name in names):
            raise v1.MechanismSynthesisError(f"OBSERVATION_SCHEMA_MISMATCH:{i}")
        out.append({name: v1._finite_number(row[name], name) for name in names})
    return out


def _available_pool(
    bounds: Mapping[str, tuple[float, float]],
    observations: Sequence[Mapping[str, Any]],
) -> list[dict[str, float]]:
    names = list(bounds)
    observed = {_point_key(p, names) for p in _observed_points(observations, names)}
    out = []
    for point in _coverage_pool(bounds):
        if _point_key(point, names) not in observed:
            out.append(point)
    return out


def _maximin_point(
    pool: Sequence[Mapping[str, float]],
    observations: Sequence[Mapping[str, Any]],
    bounds: Mapping[str, tuple[float, float]],
) -> dict[str, float] | None:
    if not pool:
        return None
    names = list(bounds)
    observed = _observed_points(observations, names)
    if not observed:
        return dict(pool[0])
    ranked = []
    for point in pool:
        nearest = min(_normalized_distance(point, prior, bounds) for prior in observed)
        ranked.append((nearest, _point_key(point, names), dict(point)))
    ranked.sort(key=lambda x: (-x[0], x[1]))
    return ranked[0][2]


def _candidate_disagreement(
    candidates: Sequence[Mapping[str, Any]],
    point: Mapping[str, float],
) -> float | None:
    predictions = []
    for candidate in candidates:
        try:
            y = v2.predict(candidate, point)
        except (v1.MechanismSynthesisError, KeyError, TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(y):
            predictions.append(float(y))
    if len(predictions) < 2:
        return None
    mean = sum(predictions) / len(predictions)
    spread = math.sqrt(sum((x - mean) ** 2 for x in predictions) / len(predictions))
    scale = max(abs(mean), max(abs(x) for x in predictions), 1.0)
    return spread / scale


def _disagreement_point(
    pool: Sequence[Mapping[str, float]],
    candidates: Sequence[Mapping[str, Any]],
    names: Sequence[str],
) -> tuple[dict[str, float] | None, float]:
    ranked = []
    for point in pool:
        disagreement = _candidate_disagreement(candidates, point)
        if disagreement is None:
            continue
        ranked.append((disagreement, _point_key(point, names), dict(point)))
    if not ranked:
        return None, 0.0
    ranked.sort(key=lambda x: (-x[0], x[1]))
    return ranked[0][2], float(ranked[0][0])


def next_experiment(
    *,
    bounds: Mapping[str, Sequence[Any]],
    observations: Sequence[Mapping[str, Any]],
    target: str,
    active_experiments_used: int,
    budget: int | None = None,
) -> dict[str, Any]:
    normalized = _normalize_bounds(bounds)
    names = list(normalized)
    d = len(names)
    default_budget = 2 * d + 1
    if budget is None:
        budget = default_budget
    if (
        not isinstance(budget, int)
        or isinstance(budget, bool)
        or budget < 1
        or budget > default_budget
    ):
        raise v1.MechanismSynthesisError("ACTIVE_BUDGET_INVALID")
    if (
        not isinstance(active_experiments_used, int)
        or isinstance(active_experiments_used, bool)
        or active_experiments_used < 0
        or active_experiments_used > budget
    ):
        raise v1.MechanismSynthesisError("ACTIVE_EXPERIMENT_COUNT_INVALID")

    target = str(target or "").strip()
    if not target:
        raise v1.MechanismSynthesisError("TARGET_REQUIRED")
    for i, row in enumerate(observations):
        if target not in row:
            raise v1.MechanismSynthesisError(f"TARGET_MISSING:{i}")
        v1._finite_number(row[target], target)

    if active_experiments_used >= budget:
        return {
            "schema": SCHEMA,
            "status": "ACTIVE_BUDGET_EXHAUSTED",
            "point": None,
            "active_experiments_used": active_experiments_used,
            "active_budget": budget,
            "remaining_active_experiments": 0,
            "acceptance_credit_delta": 0,
            "fresh_reality_authority": False,
        }

    pool = _available_pool(normalized, observations)
    if not pool:
        return {
            "schema": SCHEMA,
            "status": "NO_UNUSED_COVERAGE_POINT",
            "point": None,
            "active_experiments_used": active_experiments_used,
            "active_budget": budget,
            "remaining_active_experiments": budget - active_experiments_used,
            "acceptance_credit_delta": 0,
            "fresh_reality_authority": False,
        }

    # V1/V2 need at least five total observations.  Until then, maximize geometric
    # coverage instead of hallucinating a functional family from two points.
    if len(observations) < 5:
        point = _maximin_point(pool, observations, normalized)
        return {
            "schema": SCHEMA,
            "status": "EXPERIMENT_REQUIRED",
            "strategy": "MAXIMIN_IDENTIFIABILITY_COVERAGE",
            "point": point,
            "active_experiments_used": active_experiments_used,
            "active_budget": budget,
            "remaining_active_experiments_after_this": budget - active_experiments_used - 1,
            "candidate_count": 0,
            "disagreement": None,
            "learned_parameter_bytes": 0,
            "external_learned_capability_calls": 0,
            "acceptance_credit_delta": 0,
            "fresh_reality_authority": False,
        }

    discovery = v2.discover(
        observations,
        target=target,
        inputs=names,
        bounds={name: list(normalized[name]) for name in names},
        top_k=16,
    )
    candidates = list(discovery.get("candidates") or [])
    point, disagreement = _disagreement_point(pool, candidates[:12], names)
    if point is None:
        point = _maximin_point(pool, observations, normalized)
        strategy = "MAXIMIN_FALLBACK_AFTER_CANDIDATE_COLLAPSE"
    else:
        strategy = "MAXIMIZE_SURVIVING_CANDIDATE_DISAGREEMENT"

    return {
        "schema": SCHEMA,
        "status": "EXPERIMENT_REQUIRED",
        "strategy": strategy,
        "point": point,
        "active_experiments_used": active_experiments_used,
        "active_budget": budget,
        "remaining_active_experiments_after_this": budget - active_experiments_used - 1,
        "candidate_count": len(candidates),
        "disagreement": disagreement,
        "current_best_visible_nrmse": (
            float(candidates[0].get("nrmse", math.inf)) if candidates else None
        ),
        "learned_parameter_bytes": 0,
        "external_learned_capability_calls": 0,
        "acceptance_credit_delta": 0,
        "fresh_reality_authority": False,
    }


def finalize(
    *,
    bounds: Mapping[str, Sequence[Any]],
    observations: Sequence[Mapping[str, Any]],
    target: str,
    active_experiments_used: int,
    budget: int | None = None,
    fit_threshold: float = 0.03,
    loo_threshold: float = 0.08,
) -> dict[str, Any]:
    normalized = _normalize_bounds(bounds)
    names = list(normalized)
    default_budget = 2 * len(names) + 1
    if budget is None:
        budget = default_budget
    if active_experiments_used > budget:
        raise v1.MechanismSynthesisError("ACTIVE_EXPERIMENT_COUNT_INVALID")
    if len(observations) < 5:
        return {
            "schema": SCHEMA,
            "status": "INSUFFICIENT_VISIBLE_EVIDENCE__FAIL_CLOSED",
            "expression": None,
            "acceptance_credit_delta": 0,
            "fresh_reality_authority": False,
        }

    discovery = v2.discover(
        observations,
        target=target,
        inputs=names,
        bounds={name: list(normalized[name]) for name in names},
        top_k=16,
    )
    verdict = v2.judge(
        discovery,
        fit_threshold=fit_threshold,
        loo_threshold=loo_threshold,
    )
    candidate = verdict.get("candidate")
    if candidate is None:
        return {
            "schema": SCHEMA,
            "status": "NO_STABLE_DECLARED_MECHANISM__FAIL_CLOSED",
            "expression": None,
            "verdict": verdict,
            "acceptance_credit_delta": 0,
            "fresh_reality_authority": False,
        }
    expression = candidate.get("expression")
    if not expression:
        # V1 candidates are useful challengers but this controller refuses to
        # invent an executable serialization for families that do not provide it.
        return {
            "schema": SCHEMA,
            "status": "CANDIDATE_HAS_NO_EXECUTABLE_SERIALIZATION__FAIL_CLOSED",
            "expression": None,
            "verdict": verdict,
            "acceptance_credit_delta": 0,
            "fresh_reality_authority": False,
        }
    return {
        "schema": SCHEMA,
        "status": "EXECUTABLE_CANDIDATE_READY__UNVERIFIED",
        "expression": str(expression),
        "candidate": candidate,
        "active_experiments_used": active_experiments_used,
        "active_budget": budget,
        "learned_parameter_bytes": 0,
        "external_learned_capability_calls": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "fresh_reality_authority": False,
        "hard_nonclaim": "NO_MYSTERYMECHANISM_HIDDEN_SCORE_OR_ACCEPTANCE_CREDIT",
    }
