from __future__ import annotations

from functools import lru_cache
import math
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_INTERVAL_INFORMATION_FRONTIER_V1"
MAX_WORLDS = 128
MAX_QUERIES = 256
MAX_INTERVAL_CELLS_PER_QUERY = 512
MAX_DP_STATES = 65_536


class _WorkBudgetExceeded(RuntimeError):
    pass


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(label + "_INVALID")
    x = float(value)
    if not math.isfinite(x):
        raise ValueError(label + "_NONFINITE")
    return x


def _terminal_key(signature: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(k), repr(v)) for k, v in signature.items()))


def _possible_survivor_sets(
    state: frozenset[str],
    intervals: Mapping[str, tuple[float, float]],
) -> tuple[frozenset[str], ...]:
    """
    Exact survivor-set enumeration for one scalar noisy observation when every
    surviving world supplies a closed sound output interval.

    Membership can change only at interval endpoints. Checking every endpoint
    and one point from every open cell between adjacent endpoints therefore
    enumerates every distinct survivor set induced by any possible observation.
    """
    endpoints = sorted(
        {edge for world_id in state for edge in intervals[world_id]}
    )
    if not endpoints:
        return ()

    survivors: set[frozenset[str]] = set()

    for y in endpoints:
        bucket = frozenset(
            world_id
            for world_id in state
            if intervals[world_id][0] <= y <= intervals[world_id][1]
        )
        if bucket:
            survivors.add(bucket)

    for left, right in zip(endpoints, endpoints[1:]):
        if not left < right:
            continue
        y = left + (right - left) / 2.0
        if not math.isfinite(y):
            y = left / 2.0 + right / 2.0
        bucket = frozenset(
            world_id
            for world_id in state
            if intervals[world_id][0] <= y <= intervals[world_id][1]
        )
        if bucket:
            survivors.add(bucket)

    ordered = tuple(
        sorted(
            survivors,
            key=lambda bucket: (len(bucket), tuple(sorted(bucket))),
        )
    )
    if len(ordered) > MAX_INTERVAL_CELLS_PER_QUERY:
        raise ValueError("INTERVAL_CELL_BUDGET_EXCEEDED")
    return ordered


def solve(problem: Mapping[str, Any]) -> dict[str, Any]:
    """
    Exact minimax information policy for a finite COMPLETE hypothesis cover
    with nondeterministic scalar observations represented by sound intervals.

    This is a conservative noisy-observation analogue of
    semantic_information_frontier_v1. A query is creditable only when every
    possible observation consistent with every surviving world is represented.

    The kernel never claims the supplied finite cover is complete. The caller
    must bind that fact. It grants no benchmark, acceptance, or terminal credit.
    """
    if not isinstance(problem, Mapping):
        return _fail("PROBLEM_REQUIRED")
    if problem.get("hypothesis_cover_complete") is not True:
        return _fail("HYPOTHESIS_COVER_COMPLETENESS_UNPROVED")
    if problem.get("interval_soundness_bound") is not True:
        return _fail("INTERVAL_SOUNDNESS_UNPROVED")

    worlds_raw = problem.get("worlds")
    queries_raw = problem.get("queries")
    if (
        not isinstance(worlds_raw, Sequence)
        or isinstance(worlds_raw, (str, bytes))
        or not worlds_raw
        or len(worlds_raw) > MAX_WORLDS
    ):
        return _fail("WORLDS_INVALID_OR_TOO_MANY")
    if (
        not isinstance(queries_raw, Sequence)
        or isinstance(queries_raw, (str, bytes))
        or len(queries_raw) > MAX_QUERIES
    ):
        return _fail("QUERIES_INVALID_OR_TOO_MANY")

    ids: list[str] = []
    signatures: dict[str, tuple[tuple[str, str], ...]] = {}
    seen_worlds: set[str] = set()
    for index, raw in enumerate(worlds_raw):
        if not isinstance(raw, Mapping):
            return _fail(f"WORLD_INVALID:{index}")
        world_id = raw.get("world_id")
        if (
            not isinstance(world_id, str)
            or not world_id
            or world_id in seen_worlds
        ):
            return _fail(f"WORLD_ID_INVALID_OR_DUPLICATE:{index}")
        if raw.get("terminal_signature_complete") is not True:
            return _fail(f"TERMINAL_SIGNATURE_COMPLETENESS_UNPROVED:{world_id}")
        signature = raw.get("terminal_signature")
        if not isinstance(signature, Mapping):
            return _fail(f"TERMINAL_SIGNATURE_INVALID:{world_id}")
        seen_worlds.add(world_id)
        ids.append(world_id)
        signatures[world_id] = _terminal_key(signature)

    query_cost: dict[str, float] = {}
    query_intervals: dict[str, dict[str, tuple[float, float]]] = {}
    seen_queries: set[str] = set()
    id_set = set(ids)

    try:
        for index, raw in enumerate(queries_raw):
            if not isinstance(raw, Mapping):
                return _fail(f"QUERY_INVALID:{index}")
            query_id = raw.get("query_id")
            if (
                not isinstance(query_id, str)
                or not query_id
                or query_id in seen_queries
            ):
                return _fail(f"QUERY_ID_INVALID_OR_DUPLICATE:{index}")
            seen_queries.add(query_id)
            cost = _finite_number(raw.get("cost_units"), f"QUERY_COST:{query_id}")
            if cost < 0:
                return _fail(f"QUERY_COST_NEGATIVE:{query_id}")
            if raw.get("prediction_intervals_complete") is not True:
                return _fail(f"PREDICTION_INTERVALS_COMPLETENESS_UNPROVED:{query_id}")
            intervals_raw = raw.get("prediction_intervals")
            if not isinstance(intervals_raw, Mapping) or set(intervals_raw) != id_set:
                return _fail(f"PREDICTION_INTERVAL_DOMAIN_MISMATCH:{query_id}")

            normalized: dict[str, tuple[float, float]] = {}
            for world_id in ids:
                pair = intervals_raw[world_id]
                if (
                    not isinstance(pair, Sequence)
                    or isinstance(pair, (str, bytes))
                    or len(pair) != 2
                ):
                    return _fail(f"PREDICTION_INTERVAL_INVALID:{query_id}:{world_id}")
                lo = _finite_number(pair[0], f"INTERVAL_LO:{query_id}:{world_id}")
                hi = _finite_number(pair[1], f"INTERVAL_HI:{query_id}:{world_id}")
                if lo > hi:
                    return _fail(f"PREDICTION_INTERVAL_ORDER_INVALID:{query_id}:{world_id}")
                normalized[world_id] = (lo, hi)

            query_cost[query_id] = cost
            query_intervals[query_id] = normalized
    except ValueError as exc:
        return _fail("QUERY_BINDING_INVALID", detail=str(exc))

    budget = problem.get("max_worst_case_cost_units")
    if budget is not None:
        try:
            budget_value = _finite_number(budget, "MAX_WORST_CASE_COST_UNITS")
        except ValueError as exc:
            return _fail("BUDGET_INVALID", detail=str(exc))
        if budget_value < 0:
            return _fail("BUDGET_NEGATIVE")
    else:
        budget_value = None

    def resolved(state: frozenset[str]) -> bool:
        return len({signatures[world_id] for world_id in state}) <= 1

    dp_states_seen: set[frozenset[str]] = set()

    @lru_cache(maxsize=None)
    def dp(state: frozenset[str]) -> tuple[
        float,
        str | None,
        tuple[tuple[tuple[str, ...], float], ...],
    ]:
        if state not in dp_states_seen:
            dp_states_seen.add(state)
            if len(dp_states_seen) > MAX_DP_STATES:
                raise _WorkBudgetExceeded("DP_STATE_BUDGET_EXCEEDED")
        if resolved(state):
            return 0.0, None, ()

        best: tuple[
            float,
            str,
            tuple[tuple[tuple[str, ...], float], ...],
        ] | None = None

        for query_id in sorted(query_intervals):
            try:
                outcomes = _possible_survivor_sets(
                    state, query_intervals[query_id]
                )
            except ValueError:
                continue

            # If some possible noisy outcome preserves the entire current state,
            # this query cannot guarantee worst-case progress.
            if not outcomes or any(outcome == state for outcome in outcomes):
                continue

            worst = 0.0
            children: list[tuple[tuple[str, ...], float]] = []
            impossible = False
            for outcome in outcomes:
                child_cost, _, _ = dp(outcome)
                if child_cost == float("inf"):
                    impossible = True
                    break
                worst = max(worst, child_cost)
                children.append((tuple(sorted(outcome)), child_cost))
            if impossible:
                continue

            total = query_cost[query_id] + worst
            candidate = (total, query_id, tuple(children))
            if best is None or (candidate[0], candidate[1]) < (best[0], best[1]):
                best = candidate

        if best is None:
            return float("inf"), None, ()
        return best

    initial = frozenset(ids)
    try:
        total, first_query, children = dp(initial)
    except _WorkBudgetExceeded:
        return {
            **_fail("DP_STATE_BUDGET_EXCEEDED"),
            "status": "FAIL_CLOSED__EXACT_MINIMAX_WORK_BUDGET_EXCEEDED",
            "dp_states_checked": len(dp_states_seen),
            "max_dp_states": MAX_DP_STATES,
        }

    if total == float("inf"):
        unresolved_pairs = sorted(
            (left, right)
            for i, left in enumerate(ids)
            for right in ids[i + 1 :]
            if signatures[left] != signatures[right]
            and all(
                not (
                    query_intervals[q][left][1] < query_intervals[q][right][0]
                    or query_intervals[q][right][1] < query_intervals[q][left][0]
                )
                for q in query_intervals
            )
        )
        return {
            **_fail("NO_WORST_CASE_RESOLVING_QUERY_POLICY"),
            "status": "FAIL_CLOSED__TERMINALLY_DISTINCT_WORLDS_NOT_WORST_CASE_SEPARABLE",
            "unresolved_pairs": unresolved_pairs,
            "world_count": len(ids),
            "query_count": len(query_intervals),
        }

    within_budget = budget_value is None or total <= budget_value
    return {
        "schema": SCHEMA,
        "pass": within_budget,
        "status": (
            "PASS__EXACT_MINIMAX_INTERVAL_INFORMATION_POLICY"
            if within_budget
            else "FAIL_CLOSED__MINIMUM_WORST_CASE_COST_EXCEEDS_BUDGET"
        ),
        "world_count": len(ids),
        "terminal_equivalence_class_count": len(set(signatures.values())),
        "query_count": len(query_intervals),
        "dp_states_checked": len(dp_states_seen),
        "max_dp_states": MAX_DP_STATES,
        "minimum_worst_case_cost_units": total,
        "max_worst_case_cost_units": budget_value,
        "within_declared_budget": within_budget,
        "first_query_id": first_query,
        "first_query_possible_survivor_sets": [
            {
                "world_ids": list(world_ids),
                "remaining_optimal_cost": remaining,
            }
            for world_ids, remaining in children
        ],
        "stops_when_terminally_equivalent": True,
        "does_not_require_exact_world_identification": True,
        "noise_handling": "ADVERSARIAL_WITHIN_DECLARED_SOUND_CLOSED_INTERVALS",
        "theorem_boundary": (
            "EXACT_ONLY_FOR_THE_DECLARED_FINITE_COMPLETE_HYPOTHESIS_COVER__"
            "COMPLETE_TERMINAL_SIGNATURES__AND_SOUND_COMPLETE_PREDICTION_INTERVALS;"
            "NO_CLAIM_THE_PRIVATE_MYSTERYMECHANISM_POPULATION_OR_MECHANISM_CLASS_IS_COVERED"
        ),
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
