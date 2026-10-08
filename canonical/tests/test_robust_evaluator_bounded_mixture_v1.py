from fractions import Fraction
import pytest

from canonical.runtime.robust_evaluator_bounded_mixture_v1 import solve, RobustMixtureError


def test_pass_even_with_one_negative_component():
    out = solve({"components": [
        {"id": "J1", "delta_lower": "-1/20", "delta_upper": "1/10", "weight_lower": "1/5", "weight_upper": "4/5"},
        {"id": "J2", "delta_lower": "3/10", "delta_upper": "2/5", "weight_lower": "1/5", "weight_upper": "4/5"},
    ]})
    assert out["status"] == "PASS__ROBUST_NONINFERIOR"
    assert Fraction(out["identified_delta_interval"]["lower"]) == Fraction(1, 50)


def test_unknown_when_bounds_straddle_zero():
    out = solve({"components": [
        {"id": "A", "delta_lower": "-1/5", "delta_upper": "1/5", "weight_lower": "0", "weight_upper": "1"},
        {"id": "B", "delta_lower": "1/10", "delta_upper": "1/4", "weight_lower": "0", "weight_upper": "1"},
    ]})
    assert out["status"] == "UNKNOWN__IDENTIFIED_INTERVAL_STRADDLES_ZERO"
    assert Fraction(out["identified_delta_interval"]["lower"]) < 0
    assert Fraction(out["identified_delta_interval"]["upper"]) > 0


def test_fail_when_even_best_case_is_negative():
    out = solve({"components": [
        {"id": "A", "delta_lower": "-1/2", "delta_upper": "-1/10", "weight_lower": "1/2", "weight_upper": "1"},
        {"id": "B", "delta_lower": "-1/3", "delta_upper": "-1/20", "weight_lower": "0", "weight_upper": "1/2"},
    ]})
    assert out["status"] == "FAIL__ROBUSTLY_INFERIOR"
    assert Fraction(out["identified_delta_interval"]["upper"]) < 0


def test_exact_adversarial_weight_allocation():
    out = solve({"components": [
        {"id": "low", "delta_lower": "-2", "delta_upper": "-2", "weight_lower": "1/10", "weight_upper": "3/5"},
        {"id": "mid", "delta_lower": "1", "delta_upper": "1", "weight_lower": "1/10", "weight_upper": "4/5"},
        {"id": "high", "delta_lower": "3", "delta_upper": "3", "weight_lower": "0", "weight_upper": "4/5"},
    ]})
    w = {x["id"]: Fraction(x["weight"]) for x in out["lower_bound_witness"]}
    assert w == {"high": Fraction(0), "low": Fraction(3, 5), "mid": Fraction(2, 5)}
    assert Fraction(out["identified_delta_interval"]["lower"]) == Fraction(-4, 5)


def test_reject_infeasible_weight_bounds():
    with pytest.raises(RobustMixtureError):
        solve({"components": [
            {"id": "A", "delta_lower": "0", "delta_upper": "1", "weight_lower": "0", "weight_upper": "2/5"},
            {"id": "B", "delta_lower": "0", "delta_upper": "1", "weight_lower": "0", "weight_upper": "2/5"},
        ]})


def test_no_terminal_authority():
    out = solve({"components": [
        {"id": "A", "delta_lower": "0", "delta_upper": "0", "weight_lower": "1", "weight_upper": "1"},
    ]})
    assert out["status"] == "PASS__ROBUST_NONINFERIOR"
    assert out["semantic_premise_verified_by_this_runtime"] is False
    assert out["terminal_authority"] is False
    assert out["promotion_authority"] is False
    assert out["terminal_credit_delta"] == 0
