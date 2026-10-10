#!/usr/bin/env python3
"""Adaptive minimum-action compiler for terminal closure.

Ranks current admissible actions by conservative useful-delta value density,
deletes provably zero-probability and strictly dominated actions, and preserves
unknown probabilities as unknown rather than inventing point estimates.

This module is scheduling-only. It grants no acceptance, capability, ownership,
execution, promotion, or fresh-reality authority.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import inf
from typing import Iterable, Sequence

@dataclass(frozen=True)
class Action:
    action_id: str
    targets: frozenset[str]
    critical_path_seconds: float
    p_lower: float | None
    predicate_weight: float = 1.0
    downstream_action_deletion: float = 1.0
    information_gain: float = 1.0
    correlation_penalty: float = 0.0
    admissible: bool = True
    zero_reality: bool = True

    def __post_init__(self):
        if self.critical_path_seconds <= 0:
            raise ValueError("critical_path_seconds must be > 0")
        if self.p_lower is not None and not (0.0 <= self.p_lower <= 1.0):
            raise ValueError("p_lower must be in [0,1] or None")
        if self.correlation_penalty < 0:
            raise ValueError("correlation_penalty must be >= 0")


def priority(a: Action) -> float | None:
    """Conservative value density. Unknown p_lower remains unknown."""
    if not a.admissible:
        return 0.0
    if a.p_lower is None:
        return None
    if a.p_lower == 0.0:
        return 0.0
    return (
        a.p_lower
        * a.predicate_weight
        * max(1, len(a.targets))
        * a.downstream_action_deletion
        * a.information_gain
        / (a.critical_path_seconds * (1.0 + a.correlation_penalty))
    )


def strictly_dominates(a: Action, b: Action) -> bool:
    """Truth-preserving structural dominance under conservative known bounds.

    a dominates b only when a covers a superset, is no slower, has no worse
    known lower success probability, no higher correlation penalty, and both
    share the same zero-reality class. Unknown probabilities never dominate.
    """
    if not (a.admissible and b.admissible):
        return False
    if a.zero_reality != b.zero_reality:
        return False
    if not a.targets.issuperset(b.targets):
        return False
    if a.critical_path_seconds > b.critical_path_seconds:
        return False
    if a.correlation_penalty > b.correlation_penalty:
        return False
    if a.p_lower is None or b.p_lower is None:
        return False
    if a.p_lower < b.p_lower:
        return False
    strict = (
        a.targets != b.targets
        or a.critical_path_seconds < b.critical_path_seconds
        or a.p_lower > b.p_lower
        or a.correlation_penalty < b.correlation_penalty
    )
    return strict


def compile_frontier(actions: Sequence[Action], *, allow_fresh_reality: bool = False) -> dict:
    deleted_zero = []
    inadmissible = []
    candidates = []

    for a in actions:
        if not a.admissible:
            inadmissible.append(a.action_id)
            continue
        if a.p_lower == 0.0:
            deleted_zero.append(a.action_id)
            continue
        if not allow_fresh_reality and not a.zero_reality:
            continue
        candidates.append(a)

    dominated = set()
    for i, b in enumerate(candidates):
        for j, a in enumerate(candidates):
            if i == j:
                continue
            if strictly_dominates(a, b):
                dominated.add(b.action_id)
                break

    frontier = [a for a in candidates if a.action_id not in dominated]

    known = [a for a in frontier if priority(a) is not None]
    unknown = [a for a in frontier if priority(a) is None]
    known.sort(key=lambda a: (-float(priority(a)), a.critical_path_seconds, a.action_id))
    unknown.sort(key=lambda a: (a.critical_path_seconds, -len(a.targets), a.action_id))

    return {
        "schema": "PROJECT_BRAIN_TERMINAL_ADAPTIVE_MINIMUM_ACTION_FRONTIER_V1",
        "status": "COMPILED_FAIL_CLOSED_ZERO_CREDIT",
        "allow_fresh_reality": allow_fresh_reality,
        "deleted_probability_zero": sorted(deleted_zero),
        "inadmissible": sorted(inadmissible),
        "dominated": sorted(dominated),
        "ranked_known_probability": [
            {**asdict(a), "targets": sorted(a.targets), "priority": priority(a)}
            for a in known
        ],
        "unknown_probability_preserved": [
            {**asdict(a), "targets": sorted(a.targets), "priority": None}
            for a in unknown
        ],
        "hard_rules": [
            "UNKNOWN_PROBABILITY_IS_NOT_ZERO",
            "UNKNOWN_PROBABILITY_IS_NOT_REPLACED_BY_AN_INVENTED_POINT_ESTIMATE",
            "ZERO_PROBABILITY_ROUTE_IS_DELETED_UNTIL_ITS_REOPEN_CONDITION_CHANGES",
            "FRESH_REALITY_IS_FILTERED_UNLESS_EXPLICITLY_AUTHORIZED",
            "DOMINANCE_REQUIRES_KNOWN_NONWORSE_CONSERVATIVE_BOUNDS",
            "OUTPUT_IS_SCHEDULING_ONLY_ZERO_CREDIT",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }


def next_actions(compiled: dict) -> list[str]:
    """Return all current top-tier parallel actions without fabricating order
    between known-probability and unknown-probability classes.
    """
    known = compiled.get("ranked_known_probability", [])
    if known:
        top = known[0]["priority"]
        return [x["action_id"] for x in known if x["priority"] == top]
    unknown = compiled.get("unknown_probability_preserved", [])
    if not unknown:
        return []
    min_t = min(x["critical_path_seconds"] for x in unknown)
    return [x["action_id"] for x in unknown if x["critical_path_seconds"] == min_t]
