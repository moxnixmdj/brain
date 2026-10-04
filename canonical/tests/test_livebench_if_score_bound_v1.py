from fractions import Fraction

import pytest

from canonical.runtime.livebench_if_score_bound_v1 import (
    CaseGuarantee,
    ScoreBoundError,
    conservative_case_lower_bound,
    exact_score_from_checker_results,
    livebench_2026_06_25_sufficient_full_score_cut,
    maximum_zero_score_cases_if_all_others_full,
    minimum_full_score_cases_if_all_others_zero,
    population_lower_bound,
    threshold_met,
)


def test_exact_public_score_formula():
    assert exact_score_from_checker_results([True, True]) == Fraction(1, 1)
    assert exact_score_from_checker_results([True, False]) == Fraction(1, 4)
    assert exact_score_from_checker_results([True, True, False]) == Fraction(1, 3)
    assert exact_score_from_checker_results([False, False]) == Fraction(0, 1)


def test_conservative_case_bound():
    assert conservative_case_lower_bound(CaseGuarantee(4, 4)) == Fraction(1, 1)
    assert conservative_case_lower_bound(CaseGuarantee(4, 3)) == Fraction(3, 8)
    assert conservative_case_lower_bound(CaseGuarantee(4, 0)) == Fraction(0, 1)


def test_population_bound_and_threshold():
    rows = [CaseGuarantee(1, 1)] * 132 + [CaseGuarantee(1, 0)] * 68
    assert population_lower_bound(rows) == Fraction(33, 50)
    assert threshold_met(rows, Fraction(657, 10))


def test_131_full_scores_are_not_enough_at_zero_elsewhere():
    rows = [CaseGuarantee(1, 1)] * 131 + [CaseGuarantee(1, 0)] * 69
    assert population_lower_bound(rows) == Fraction(131, 200)
    assert not threshold_met(rows, Fraction(657, 10))


def test_sufficient_cut_is_exact():
    t = Fraction(657, 10)
    assert minimum_full_score_cases_if_all_others_zero(200, t) == 132
    assert maximum_zero_score_cases_if_all_others_full(200, t) == 68
    cut = livebench_2026_06_25_sufficient_full_score_cut()
    assert cut["minimum_full_score_cases_if_all_others_zero"] == 132
    assert cut["maximum_zero_score_cases_if_all_others_full"] == 68
    assert cut["lower_neighbor_percent"] == "131/2"
    assert cut["cut_percent"] == "66"


def test_invalid_bounds_fail_closed():
    with pytest.raises(ScoreBoundError):
        conservative_case_lower_bound(CaseGuarantee(0, 0))
    with pytest.raises(ScoreBoundError):
        conservative_case_lower_bound(CaseGuarantee(2, 3))
    with pytest.raises(ScoreBoundError):
        exact_score_from_checker_results([])
