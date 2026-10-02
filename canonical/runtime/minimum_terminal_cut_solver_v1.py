"""Exact zero-credit solver for the currently executable terminal action cut.

Given a compiled acceptance IR, find the available action subset that covers the
maximum number of unresolved predicates. Among equally covering subsets, minimize
new reality units, then action count, then lexicographic action IDs.

Actions with explicitly false preconditions are never selected. Their false
preconditions are surfaced as representation/dependency gaps instead of being
silently ignored.
"""
from __future__ import annotations

from itertools import combinations
from math import isfinite
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_MINIMUM_TERMINAL_CUT_SOLVER_V1"
MAX_EXACT_ACTIONS = 22


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "selected_actions": [],
        "covered_predicates": [],
        "uncovered_predicates": [],
        "blocked_preconditions": [],
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def evaluate(ir: Mapping[str, Any]) -> dict[str, Any]:
    predicates = ir.get("predicates")
    actions = ir.get("actions")
    if ir.get("status") not in {"PASS", "PASS_WITH_UNCOVERED_ACTION_TARGETS"}:
        return _fail("IR_NOT_PASS")
    if not isinstance(predicates, list) or not isinstance(actions, list):
        return _fail("IR_SHAPE_INVALID")

    unresolved = {
        row["id"] for row in predicates
        if isinstance(row, Mapping)
        and isinstance(row.get("id"), str)
        and row.get("state") != "PROVED"
    }

    available = []
    blocked_preconditions: dict[str, set[str]] = {}
    for row in actions:
        if not isinstance(row, Mapping) or not isinstance(row.get("id"), str):
            return _fail("ACTION_INVALID")
        targets = row.get("unresolved_target_predicates")
        if not isinstance(targets, list):
            return _fail(f"ACTION_TARGETS_INVALID:{row.get('id')}")
        targets_set = set(targets) & unresolved
        raw_cost = row.get("new_reality_units", 0)
        if isinstance(raw_cost, bool) or not isinstance(raw_cost, (int, float)):
            return _fail(f"ACTION_COST_INVALID:{row['id']}")
        cost = float(raw_cost)
        if not isfinite(cost) or cost < 0:
            return _fail(f"ACTION_COST_INVALID:{row['id']}")
        if row.get("available_now") is True:
            available.append({
                "id": row["id"],
                "targets": targets_set,
                "cost": cost,
                "critical_path": row.get("critical_path") is True,
            })
        else:
            gaps = row.get("unsatisfied_preconditions", [])
            if not isinstance(gaps, list):
                return _fail(f"ACTION_GAPS_INVALID:{row['id']}")
            for gap in gaps:
                if not isinstance(gap, str) or not gap:
                    return _fail(f"ACTION_GAP_INVALID:{row['id']}")
                blocked_preconditions.setdefault(gap, set()).update(targets_set)

    if len(available) > MAX_EXACT_ACTIONS:
        return {
            **_fail(f"AVAILABLE_ACTION_COUNT_EXCEEDS_{MAX_EXACT_ACTIONS}"),
            "status": "EXACT_SEARCH_LIMIT",
            "available_action_count": len(available),
        }

    best = None
    n = len(available)
    for size in range(n + 1):
        for combo in combinations(range(n), size):
            covered: set[str] = set()
            cost = 0.0
            ids = []
            for idx in combo:
                action = available[idx]
                covered.update(action["targets"])
                cost += action["cost"]
                ids.append(action["id"])
            ids_t = tuple(sorted(ids))
            key = (-len(covered), cost, len(ids_t), ids_t)
            if best is None or key < best[0]:
                best = (key, ids_t, covered, cost)

    assert best is not None
    selected = list(best[1])
    covered = set(best[2])
    uncovered = unresolved - covered

    gap_rows = [
        {
            "precondition_id": gap,
            "blocked_target_predicates": sorted(targets),
        }
        for gap, targets in sorted(blocked_preconditions.items())
    ]

    return {
        "schema": SCHEMA,
        "status": "EXACT_TERMINAL_ACTION_CUT_COMPUTED",
        "errors": [],
        "unresolved_predicate_count": len(unresolved),
        "available_action_count": len(available),
        "selected_actions": selected,
        "selected_action_count": len(selected),
        "selected_new_reality_units": best[3],
        "covered_predicates": sorted(covered),
        "covered_predicate_count": len(covered),
        "uncovered_predicates": sorted(uncovered),
        "blocked_preconditions": gap_rows,
        "rule": (
            "MAXIMIZE_CURRENT_UNRESOLVED_PREDICATE_COVERAGE_THEN_MINIMIZE_REALITY_"
            "THEN_ACTION_COUNT__FALSE_PRECONDITIONS_SURFACE_AS_FIRST_CLASS_GAPS"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
