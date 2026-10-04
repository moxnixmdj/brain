from fractions import Fraction

import pytest

from canonical.runtime.livebench_exact_completion_cut_v1 import (
    CaseWork,
    ExactCutError,
    case_score_mass,
    completion_marginal_mass,
    exact_minimum_work_cut,
    threshold_score_mass,
)


def test_frozen_threshold_mass_is_exact_rational():
    assert threshold_score_mass(200, "65.7") == Fraction(657, 5)
    assert Fraction(131, 1) < Fraction(657, 5)
    assert Fraction(132, 1) >= Fraction(657, 5)


def test_completion_bonus_is_large_and_exact():
    assert case_score_mass(4, 3) == Fraction(3, 8)
    assert case_score_mass(4, 4) == 1
    assert completion_marginal_mass(4) == Fraction(5, 8)


def test_optimizer_prefers_finishing_nearly_complete_case():
    result = exact_minimum_work_cut(
        [
            CaseWork(
                instruction_count=4,
                guaranteed_following=3,
                additional_checker_costs=(Fraction(1),),
            ),
            CaseWork(
                instruction_count=4,
                guaranteed_following=0,
                additional_checker_costs=(
                    Fraction(1),
                    Fraction(1),
                    Fraction(1),
                    Fraction(100),
                ),
            ),
        ],
        population_count=2,
        threshold_percent="50",
    )
    assert result["feasible"] is True
    assert result["minimum_work_cost"] == "1"
    assert result["selected_additional_checkers_by_case"] == [1, 0]
    assert result["proved_score_mass"] == "1"


def test_unrepresented_rows_are_zero_not_optimistically_filled():
    result = exact_minimum_work_cut(
        [CaseWork(instruction_count=1, guaranteed_following=1)],
        population_count=2,
        threshold_percent="60",
    )
    assert result["feasible"] is False
    assert result["maximum_reachable_score_mass"] == "1"
    assert result["threshold_score_mass"] == "6/5"


def test_unlisted_unresolved_checkers_are_unprovable():
    result = exact_minimum_work_cut(
        [
            CaseWork(
                instruction_count=3,
                guaranteed_following=1,
                additional_checker_costs=(Fraction(1),),
            )
        ],
        population_count=1,
        threshold_percent="100",
    )
    assert result["feasible"] is False
    assert result["maximum_reachable_score_mass"] == "1/3"


def test_exact_cut_is_global_not_greedy_by_raw_checker_count():
    result = exact_minimum_work_cut(
        [
            CaseWork(
                instruction_count=2,
                guaranteed_following=1,
                additional_checker_costs=(Fraction(3),),
            ),
            CaseWork(
                instruction_count=5,
                guaranteed_following=0,
                additional_checker_costs=(
                    Fraction(1),
                    Fraction(1),
                    Fraction(1),
                    Fraction(1),
                    Fraction(100),
                ),
            ),
        ],
        population_count=2,
        threshold_percent="50",
    )
    assert result["feasible"] is True
    assert result["minimum_work_cost"] == "3"
    assert result["selected_additional_checkers_by_case"] == [1, 0]


def test_float_inputs_fail_closed():
    with pytest.raises(ExactCutError, match="FLOAT_INPUT_FORBIDDEN"):
        exact_minimum_work_cut(
            [CaseWork(instruction_count=1, guaranteed_following=1)],
            population_count=1,
            threshold_percent=65.7,
        )


def test_negative_cost_fails_closed():
    with pytest.raises(ExactCutError, match="NEGATIVE_PROOF_COST"):
        exact_minimum_work_cut(
            [
                CaseWork(
                    instruction_count=2,
                    guaranteed_following=0,
                    additional_checker_costs=(Fraction(-1),),
                )
            ],
            population_count=1,
            threshold_percent="1",
        )
