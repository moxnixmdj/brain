#!/usr/bin/env python3
"""Project Brain C3 tool-route adapter V1.

Architecture:
1. Deterministic eligibility / authority filtering.
2. Semantic scorer only among routes that are actually admissible.
3. Fail closed when no route is admissible.

The scorer is injected. This file owns the control contract, not any donor model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence


@dataclass(frozen=True)
class ToolRoute:
    route_id: str
    description: str
    provider: str | None = None
    available: bool = True
    authorized: bool = True


@dataclass(frozen=True)
class RouteDecision:
    status: str
    route_id: str | None
    score: float | None
    eligible_route_ids: tuple[str, ...]
    reason: str


def eligible_routes(
    routes: Iterable[ToolRoute],
    *,
    required_provider: str | None = None,
    allowed_route_ids: set[str] | None = None,
) -> list[ToolRoute]:
    """Return only routes permitted by deterministic host constraints."""
    out: list[ToolRoute] = []
    for route in routes:
        if not route.available or not route.authorized:
            continue
        if required_provider is not None and route.provider != required_provider:
            continue
        if allowed_route_ids is not None and route.route_id not in allowed_route_ids:
            continue
        out.append(route)
    return out


def select_route(
    query: str,
    routes: Sequence[ToolRoute],
    scorer: Callable[[str, list[str]], Sequence[float]],
    *,
    required_provider: str | None = None,
    allowed_route_ids: set[str] | None = None,
) -> RouteDecision:
    if not query.strip():
        raise ValueError("query must be non-empty")
    eligible = eligible_routes(
        routes,
        required_provider=required_provider,
        allowed_route_ids=allowed_route_ids,
    )
    ids = tuple(r.route_id for r in eligible)
    if not eligible:
        return RouteDecision(
            status="ESCALATE",
            route_id=None,
            score=None,
            eligible_route_ids=ids,
            reason="NO_DETERMINISTICALLY_ADMISSIBLE_ROUTE",
        )
    if len(eligible) == 1:
        only = eligible[0]
        return RouteDecision(
            status="SELECT",
            route_id=only.route_id,
            score=None,
            eligible_route_ids=ids,
            reason="SINGLE_DETERMINISTICALLY_ADMISSIBLE_ROUTE",
        )

    scores = [float(x) for x in scorer(query, [r.description for r in eligible])]
    if len(scores) != len(eligible):
        raise ValueError("scorer returned wrong number of scores")
    best_i = max(range(len(scores)), key=scores.__getitem__)
    return RouteDecision(
        status="SELECT",
        route_id=eligible[best_i].route_id,
        score=scores[best_i],
        eligible_route_ids=ids,
        reason="SEMANTIC_RERANK_AMONG_DETERMINISTICALLY_ADMISSIBLE_ROUTES",
    )
