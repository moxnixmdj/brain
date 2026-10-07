from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_P2_PROFESSIONAL_EXACT_DP_V1"


def solve(task: Mapping[str, Any]) -> dict[str, Any]:
    """Exact P2 optimizer for the explicit-rubric, nonnegative-integer-cost subregion.

    Objective/tie-break matches the frozen contract-native professional policy:
    maximize additive weighted score, then minimize total cost, then choose the
    lexicographically smallest sorted edit-id tuple.

    Dynamic programming is pseudo-polynomial in edit_budget rather than 2**n.
    """
    weights = task.get("rubric_weights")
    edits = task.get("edit_candidates")
    budget = task.get("edit_budget")
    if not isinstance(weights, Mapping) or not weights:
        raise ValueError("RUBRIC_WEIGHTS_REQUIRED")
    if not isinstance(edits, list):
        raise ValueError("EDIT_CANDIDATES_REQUIRED")
    if not isinstance(budget, int) or isinstance(budget, bool) or budget < 0:
        raise ValueError("NONNEGATIVE_INTEGER_BUDGET_REQUIRED")

    dims = tuple(sorted(weights))
    if any(
        not isinstance(d, str)
        or not d
        or not isinstance(weights[d], int)
        or isinstance(weights[d], bool)
        for d in dims
    ):
        raise ValueError("RUBRIC_WEIGHTS_INVALID")

    normalized: list[tuple[str, int, int]] = []
    seen: set[str] = set()
    for raw in edits:
        if not isinstance(raw, Mapping):
            raise ValueError("EDIT_INVALID")
        eid = raw.get("id")
        if not isinstance(eid, str) or not eid or eid in seen:
            raise ValueError("EDIT_ID_INVALID_OR_DUPLICATE")
        seen.add(eid)

        # Invalid edits are never admissible, matching the frozen exhaustive policy.
        if raw.get("supported") is not True or raw.get("hard_violation") is True:
            continue

        cost = raw.get("cost")
        scores = raw.get("scores")
        if not isinstance(cost, int) or isinstance(cost, bool) or cost < 0:
            raise ValueError("NONNEGATIVE_INTEGER_EDIT_COST_REQUIRED")
        if not isinstance(scores, Mapping):
            raise ValueError("EDIT_SCORES_INVALID")
        if any(
            d not in scores
            or not isinstance(scores[d], int)
            or isinstance(scores[d], bool)
            for d in dims
        ):
            raise ValueError("EDIT_SCORE_DIMENSION_INVALID")
        value = sum(int(weights[d]) * int(scores[d]) for d in dims)
        normalized.append((eid, cost, value))

    # Descending edit-id order is deliberate. Future additions then prepend
    # lexicographically smaller ids, preserving dominance of the lexicographically
    # smallest state for an exact (cost, score) state.
    normalized.sort(key=lambda x: x[0], reverse=True)

    # exact_cost -> (best_score, lexicographically-smallest sorted id tuple)
    dp: dict[int, tuple[int, tuple[str, ...]]] = {0: (0, ())}
    for eid, cost, value in normalized:
        nxt = dict(dp)
        for old_cost, (old_score, old_ids) in dp.items():
            new_cost = old_cost + cost
            if new_cost > budget:
                continue
            new_ids = tuple(sorted(old_ids + (eid,)))
            candidate = (old_score + value, new_ids)
            previous = nxt.get(new_cost)
            if (
                previous is None
                or candidate[0] > previous[0]
                or (candidate[0] == previous[0] and candidate[1] < previous[1])
            ):
                nxt[new_cost] = candidate
        dp = nxt

    best_cost, (best_score, best_ids) = min(
        dp.items(),
        key=lambda kv: (-kv[1][0], kv[0], kv[1][1]),
    )
    return {
        "schema": SCHEMA,
        "selected_edits": list(best_ids),
        "objective_score": best_score,
        "total_cost": best_cost,
        "exact": True,
        "algorithm": "PSEUDO_POLYNOMIAL_BUDGET_DP",
        "state_count": len(dp),
        "scope": "EXPLICIT_RUBRIC__NONNEGATIVE_INTEGER_EDIT_COST_AND_BUDGET",
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
