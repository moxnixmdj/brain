"""Adaptive exact terminal cut solver V2.

V2 corrects the V1 objective. V1 maximizes currently coverable predicates and
then minimizes fresh-reality cost and action count. That can prefer a smaller
but slower serial plan over a wider parallel plan.

V2 keeps fail-closed exact search, but among equally covering subsets it
minimizes causal critical-path wall time first, then fresh-reality units, then
action count. It also carries conservative probability intervals, deletes
actions whose useful-delta probability upper bound is exactly zero, and uses
correlation-aware robust utility only as a late tie-breaker.

This is scheduling evidence only. It grants no execution, acceptance,
capability, family, ownership, promotion, or fresh-reality authority.
"""
from __future__ import annotations

from itertools import combinations
from math import isfinite
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_MINIMUM_TERMINAL_CUT_SOLVER_V2"
MAX_EXACT_ACTIONS = 22


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "selected_actions": [],
        "covered_predicates": [],
        "uncovered_predicates": [],
        "blocked_preconditions": [],
        "zero_probability_deleted_actions": [],
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def _number(v: Any, *, minimum: float = 0.0) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    x = float(v)
    if not isfinite(x) or x < minimum:
        return None
    return x


def _prob(v: Any) -> float | None:
    x = _number(v)
    if x is None or x > 1:
        return None
    return x


def _critical_path(actions: list[dict[str, Any]]) -> float:
    """Sequential phases, perfect parallelism inside each phase."""
    by_phase: dict[str, float] = {}
    for row in actions:
        phase = row["causal_phase"]
        by_phase[phase] = max(by_phase.get(phase, 0.0), row["wall_clock_seconds"])
    return sum(by_phase.values())


def _robust_utility(actions: list[dict[str, Any]]) -> float:
    """Do not double count routes declared to share one correlation group."""
    by_group: dict[str, float] = {}
    for row in actions:
        u = (
            row["probability_lower"]
            * (len(row["targets"]) + row["downstream_action_deletion"])
            * row["information_gain"]
        )
        g = row["correlation_group"]
        by_group[g] = max(by_group.get(g, 0.0), u)
    return sum(by_group.values())


def evaluate(ir: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(ir, Mapping):
        return _fail("IR_NOT_OBJECT")
    predicates = ir.get("predicates")
    actions = ir.get("actions")
    if ir.get("status") not in {"PASS", "PASS_WITH_UNCOVERED_ACTION_TARGETS"}:
        return _fail("IR_NOT_PASS")
    if not isinstance(predicates, list) or not isinstance(actions, list):
        return _fail("IR_SHAPE_INVALID")

    unresolved = {
        row["id"]
        for row in predicates
        if isinstance(row, Mapping)
        and isinstance(row.get("id"), str)
        and row.get("state") != "PROVED"
    }

    available: list[dict[str, Any]] = []
    blocked_preconditions: dict[str, set[str]] = {}
    zero_probability_deleted: list[str] = []

    for row in actions:
        if not isinstance(row, Mapping) or not isinstance(row.get("id"), str):
            return _fail("ACTION_INVALID")
        aid = row["id"]
        targets = row.get("unresolved_target_predicates")
        if not isinstance(targets, list) or any(not isinstance(x, str) for x in targets):
            return _fail(f"ACTION_TARGETS_INVALID:{aid}")
        targets_set = set(targets) & unresolved

        reality = _number(row.get("new_reality_units", 0))
        wall = _number(row.get("wall_clock_seconds"))
        p_lo = _prob(row.get("probability_lower", 0.0))
        p_hi = _prob(row.get("probability_upper", 1.0))
        info = _number(row.get("information_gain", 1.0))
        deletion = _number(row.get("downstream_action_deletion", 0.0))
        phase = row.get("causal_phase", "CURRENT")
        corr = row.get("correlation_group", aid)

        if reality is None:
            return _fail(f"ACTION_REALITY_COST_INVALID:{aid}")
        if row.get("available_now") is True and wall is None:
            return _fail(f"ACTION_WALL_CLOCK_INVALID:{aid}")
        if p_lo is None or p_hi is None or p_lo > p_hi:
            return _fail(f"ACTION_PROBABILITY_INTERVAL_INVALID:{aid}")
        if info is None:
            return _fail(f"ACTION_INFORMATION_GAIN_INVALID:{aid}")
        if deletion is None:
            return _fail(f"ACTION_DOWNSTREAM_DELETION_INVALID:{aid}")
        if not isinstance(phase, str) or not phase:
            return _fail(f"ACTION_CAUSAL_PHASE_INVALID:{aid}")
        if not isinstance(corr, str) or not corr:
            return _fail(f"ACTION_CORRELATION_GROUP_INVALID:{aid}")

        if p_hi == 0:
            zero_probability_deleted.append(aid)
            continue

        if row.get("available_now") is True:
            available.append(
                {
                    "id": aid,
                    "targets": targets_set,
                    "new_reality_units": reality,
                    "wall_clock_seconds": wall,
                    "probability_lower": p_lo,
                    "probability_upper": p_hi,
                    "information_gain": info,
                    "downstream_action_deletion": deletion,
                    "causal_phase": phase,
                    "correlation_group": corr,
                }
            )
        else:
            gaps = row.get("unsatisfied_preconditions", [])
            if not isinstance(gaps, list):
                return _fail(f"ACTION_GAPS_INVALID:{aid}")
            for gap in gaps:
                if not isinstance(gap, str) or not gap:
                    return _fail(f"ACTION_GAP_INVALID:{aid}")
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
            chosen = [available[idx] for idx in combo]
            covered: set[str] = set()
            reality = 0.0
            ids: list[str] = []
            for action in chosen:
                covered.update(action["targets"])
                reality += action["new_reality_units"]
                ids.append(action["id"])
            cp = _critical_path(chosen)
            utility = _robust_utility(chosen)
            ids_t = tuple(sorted(ids))

            # Exact lexicographic objective:
            # 1) maximize unresolved predicate coverage,
            # 2) minimize causal critical-path wall time,
            # 3) minimize fresh-reality consumption,
            # 4) minimize action count,
            # 5) maximize conservative correlation-aware utility,
            # 6) deterministic lexicographic tie-break.
            key = (
                -len(covered),
                cp,
                reality,
                len(ids_t),
                -utility,
                ids_t,
            )
            if best is None or key < best[0]:
                best = (key, ids_t, covered, reality, cp, utility)

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
        "status": "EXACT_ADAPTIVE_TERMINAL_ACTION_CUT_COMPUTED",
        "pass": True,
        "errors": [],
        "unresolved_predicate_count": len(unresolved),
        "available_action_count": len(available),
        "selected_actions": selected,
        "selected_action_count": len(selected),
        "selected_new_reality_units": best[3],
        "selected_critical_path_seconds": best[4],
        "selected_robust_utility": best[5],
        "covered_predicates": sorted(covered),
        "covered_predicate_count": len(covered),
        "uncovered_predicates": sorted(uncovered),
        "blocked_preconditions": gap_rows,
        "zero_probability_deleted_actions": sorted(zero_probability_deleted),
        "probability_policy": (
            "POINT_PROBABILITIES_ARE_NOT_INFERRED__CALLER_SUPPLIES_ONLY_EVIDENCE_JUSTIFIED_"
            "INTERVALS__P_UPPER_EQ_0_DELETES_ROUTE__ROBUST_UTILITY_USES_P_LOWER_AND_"
            "CORRELATION_GROUP_MAX_TO_AVOID_DOUBLE_COUNT"
        ),
        "parallelism_model": (
            "ACTIONS_IN_ONE_CAUSAL_PHASE_RUN_IN_PARALLEL__PHASES_RUN_SEQUENTIALLY__"
            "CRITICAL_PATH_IS_SUM_OF_PER_PHASE_MAX_WALL_CLOCK"
        ),
        "objective": (
            "MAXIMIZE_CURRENT_UNRESOLVED_COVERAGE__MINIMIZE_CRITICAL_PATH_WALL_CLOCK__"
            "MINIMIZE_FRESH_REALITY__MINIMIZE_ACTION_COUNT__MAXIMIZE_CONSERVATIVE_"
            "CORRELATION_AWARE_INFORMATION_VALUE"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
