from fractions import Fraction

import pytest

from canonical.runtime.livebench_public_checker_exact_mincut_v1 import (
    ExactCutError,
    build_integer_objective,
    exact_frontier,
    minimum_cut,
)


def test_integer_objective_matches_frozen_one_and_two_checker_scores():
    rows = [
        {"instruction_id_list": ["a"]},
        {"instruction_id_list": ["a", "b"]},
        {"instruction_id_list": ["b"]},
    ]
    _, families, node, edge = build_integer_objective(rows)
    ia, ib = families.index("a"), families.index("b")

    assert node[ia] == 5
    assert node[ib] == 5
    assert edge[ia][ib] == 2

    frontier = exact_frontier(rows)
    assert frontier["frontier"][1].score4 == 5   # 1.25 score mass
    assert frontier["frontier"][2].score4 == 12  # 3.0 score mass


def test_exact_minimum_cut_proves_lower_cardinality_fails():
    rows = [
        {"instruction_id_list": ["a"]},
        {"instruction_id_list": ["a"]},
        {"instruction_id_list": ["b"]},
        {"instruction_id_list": ["b"]},
        {"instruction_id_list": ["a", "b"]},
    ]
    # k=1 best = 2 + 0.25 = 2.25 / 5 = 45%
    # k=2 = 5 / 5 = 100%
    out = minimum_cut(rows, Fraction(50, 1))
    assert out["minimum_family_count"] == 2
    assert out["lower_neighbor_percent"] == "45"
    assert out["crossing_percent"] == "100"


def test_disconnected_components_are_combined_exactly():
    rows = [
        {"instruction_id_list": ["a"]},
        {"instruction_id_list": ["a", "b"]},
        {"instruction_id_list": ["b"]},
        {"instruction_id_list": ["c"]},
        {"instruction_id_list": ["d"]},
    ]
    out = exact_frontier(rows)
    assert out["component_sizes"] == (2, 1, 1)
    assert len(out["frontier"]) == 5


def test_fail_closed_on_three_checker_rows():
    with pytest.raises(ExactCutError, match="ONLY_ONE_OR_TWO_CHECKER_ROWS_SUPPORTED"):
        exact_frontier([{"instruction_id_list": ["a", "b", "c"]}])


def test_component_size_guard_is_fail_closed():
    rows = [
        {"instruction_id_list": ["a", "b"]},
        {"instruction_id_list": ["b", "c"]},
    ]
    with pytest.raises(ExactCutError, match="COMPONENT_TOO_LARGE"):
        exact_frontier(rows, max_component_size=2)
