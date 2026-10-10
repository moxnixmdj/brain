"""Executable V7 layered equal-or-better semantics.

Layer 1: Opus-relative capability noninferiority.
Layer 2: absolute Brain project promotion constraints.
Layer 3: lexicographic optimization among already qualifying Brain routes.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.distributional_target_upper_envelope_v1 import weakly_dominates


class V7LayeredOrderError(ValueError):
    pass


def capability_noninferior(
    brain_law: Mapping[str, float],
    target_law: Mapping[str, float],
    *,
    evaluators: Sequence[Mapping[str, float]],
    capability_hard_constraints: Sequence[Mapping[str, Any]] = (),
) -> bool:
    return weakly_dominates(
        brain_law,
        target_law,
        evaluators=evaluators,
        hard_constraints=capability_hard_constraints,
    )


def absolute_promotion_feasible(route: Mapping[str, Any]) -> bool:
    try:
        spend = float(route.get("incremental_spend_usd"))
    except (TypeError, ValueError):
        return False
    return (
        route.get("brain_owned") is True
        and route.get("donor_independent") is True
        and route.get("absolute_project_constraints_ok") is True
        and abs(spend) <= 1e-12
    )


def qualifies(
    route: Mapping[str, Any],
    target_law: Mapping[str, float],
    *,
    evaluators: Sequence[Mapping[str, float]],
    capability_hard_constraints: Sequence[Mapping[str, Any]] = (),
) -> bool:
    law = route.get("law")
    if not isinstance(law, Mapping):
        return False
    if not capability_noninferior(
        law,
        target_law,
        evaluators=evaluators,
        capability_hard_constraints=capability_hard_constraints,
    ):
        return False
    return absolute_promotion_feasible(route)


def optimization_key(route: Mapping[str, Any]) -> tuple[float, float, float]:
    try:
        wall = float(route["wall_clock_to_verified_ownership"])
        durable = float(route["durable_resource_compute_footprint"])
        complexity = float(route["complexity"])
    except (KeyError, TypeError, ValueError) as exc:
        raise V7LayeredOrderError("OPTIMIZATION_METRICS_REQUIRED") from exc
    if wall < 0 or durable < 0 or complexity < 0:
        raise V7LayeredOrderError("OPTIMIZATION_METRICS_MUST_BE_NONNEGATIVE")
    return wall, durable, complexity


def select_best_qualifying_route(
    routes: Sequence[Mapping[str, Any]],
    target_law: Mapping[str, float],
    *,
    evaluators: Sequence[Mapping[str, float]],
    capability_hard_constraints: Sequence[Mapping[str, Any]] = (),
) -> Mapping[str, Any] | None:
    good = [
        route
        for route in routes
        if qualifies(
            route,
            target_law,
            evaluators=evaluators,
            capability_hard_constraints=capability_hard_constraints,
        )
    ]
    if not good:
        return None
    return min(good, key=optimization_key)
