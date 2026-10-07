from __future__ import annotations

from itertools import product

import pytest

from canonical.runtime.p2_professional_exact_dp_v1 import solve


def exhaustive(task):
    weights = task["rubric_weights"]
    edits = task["edit_candidates"]
    budget = task["edit_budget"]
    best = None
    n = len(edits)
    for mask in range(1 << n):
        chosen = [edits[i] for i in range(n) if mask & (1 << i)]
        if any(e.get("supported") is not True or e.get("hard_violation") is True for e in chosen):
            continue
        cost = sum(e["cost"] for e in chosen)
        if cost > budget:
            continue
        score = sum(
            sum(weights[d] * e["scores"][d] for d in weights)
            for e in chosen
        )
        ids = tuple(sorted(e["id"] for e in chosen))
        key = (-score, cost, ids)
        if best is None or key < best[0]:
            best = (key, ids, score, cost)
    assert best is not None
    return list(best[1]), best[2], best[3]


def test_zero_value_zero_cost_edit_lex_corner_matches_exhaustive():
    task = {
        "rubric_weights": {"d0": 0, "d1": 1},
        "edit_candidates": [
            {"id": "e04", "supported": True, "hard_violation": False, "cost": 5, "scores": {"d0": 4, "d1": 6}},
            {"id": "e05", "supported": True, "hard_violation": False, "cost": 0, "scores": {"d0": 1, "d1": 0}},
            {"id": "e06", "supported": True, "hard_violation": False, "cost": 5, "scores": {"d0": -3, "d1": 6}},
        ],
        "edit_budget": 10,
    }
    out = solve(task)
    assert out["selected_edits"] == ["e04", "e05", "e06"]
    assert (out["selected_edits"], out["objective_score"], out["total_cost"]) == exhaustive(task)


def test_small_complete_state_space_matches_exhaustive():
    # Deterministic adversarial sweep over sign, zero-cost, invalid-edit and tie cases.
    case_id = 0
    for values in product((-2, 0, 3), repeat=4):
        for costs in product((0, 1, 3), repeat=4):
            edits = []
            for i in range(4):
                edits.append({
                    "id": f"e{i}",
                    "supported": not (case_id % 5 == 0 and i == 3),
                    "hard_violation": bool(case_id % 7 == 0 and i == 2),
                    "cost": costs[i],
                    "scores": {"quality": values[i]},
                })
            task = {
                "rubric_weights": {"quality": 1},
                "edit_candidates": edits,
                "edit_budget": case_id % 6,
            }
            out = solve(task)
            expected = exhaustive(task)
            assert (out["selected_edits"], out["objective_score"], out["total_cost"]) == expected
            case_id += 1


def test_negative_cost_fails_closed_instead_of_widening_scope():
    task = {
        "rubric_weights": {"quality": 1},
        "edit_candidates": [
            {"id": "e0", "supported": True, "hard_violation": False, "cost": -1, "scores": {"quality": 1}},
        ],
        "edit_budget": 2,
    }
    with pytest.raises(ValueError, match="NONNEGATIVE_INTEGER_EDIT_COST_REQUIRED"):
        solve(task)


def test_unsupported_and_hard_violation_edits_are_never_selected():
    task = {
        "rubric_weights": {"quality": 1},
        "edit_candidates": [
            {"id": "bad_support", "supported": False, "hard_violation": False, "cost": 0, "scores": {"quality": 999}},
            {"id": "bad_hard", "supported": True, "hard_violation": True, "cost": 0, "scores": {"quality": 999}},
            {"id": "good", "supported": True, "hard_violation": False, "cost": 1, "scores": {"quality": 2}},
        ],
        "edit_budget": 1,
    }
    out = solve(task)
    assert out["selected_edits"] == ["good"]
