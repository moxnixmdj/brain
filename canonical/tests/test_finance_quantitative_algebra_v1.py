from decimal import Decimal as D

import pytest

from canonical.runtime.finance_quantitative_algebra_v1 import (
    FinanceAlgebraError,
    actual_fiscal_days,
    adjusted_ebitda,
    adjusted_ebitdar,
    basis_points_between,
    beat_miss_percent,
    cagr,
    conservative_guidance_dominance,
    days_inventory_outstanding,
    dcf_enterprise_value,
    debt_to_total_capital,
    enterprise_value,
    ebitda_from_operating_income,
    fixed_charge_coverage_ratio,
    fixed_operating_lease_cost,
    market_sentiment_from_return,
    midpoint,
    moic,
    percent_change,
    rank_desc,
    same_rank_order,
    simple_hold_period_irr_percent,
    terminal_value_exit_multiple,
    terminal_value_perpetual_growth,
    transaction_premium,
)


def close(a: D, b: D, tol: str = "0.0000001") -> bool:
    return abs(a - b) <= D(tol)


def test_cagr_and_basis_points_exact_examples():
    assert cagr("121", "100", 2) == D("10.0")
    assert basis_points_between("32.82", "15.67") == D("1715.00")


def test_percent_change_and_guidance_beat_miss():
    assert percent_change("110", "100") == D("10.0")
    assert transaction_premium("130", "100") == D("30.0")
    assert beat_miss_percent("90", "100") == D("-10.0")
    assert midpoint("80", "120") == D("100")



def test_inclusive_fiscal_days_handles_52_and_53_week_years():
    assert actual_fiscal_days("2024-01-29", "2025-02-02") == 371
    assert actual_fiscal_days("2024-02-03", "2025-01-31") == 364


def test_inventory_and_fixed_charge_formulas():
    assert days_inventory_outstanding("100", "120", "550", "365") == D("73.0")
    assert fixed_charge_coverage_ratio("900", "100", "50") == D("6")


def test_leverage_and_enterprise_value():
    assert debt_to_total_capital("300", "200") == D("60")
    assert enterprise_value("1000", debt="300", cash_and_equivalents="100") == D("1200")


def test_adjusted_earnings_builds_from_explicit_addbacks():
    assert adjusted_ebitda("500", "100", ["20", "30"]) == D("650")
    assert adjusted_ebitdar("650", "50") == D("700")


def test_dcf_exit_multiple_path():
    tv = terminal_value_exit_multiple("100", "10")
    assert tv == D("1000")
    ev = dcf_enterprise_value(["100", "100"], "10", tv)
    assert close(ev, D("1000"))


def test_perpetual_growth_requires_wacc_above_growth():
    tv = terminal_value_perpetual_growth("105", "10", "5")
    assert tv == D("2100")
    with pytest.raises(FinanceAlgebraError, match="DISCOUNT_RATE_NOT_ABOVE_GROWTH"):
        terminal_value_perpetual_growth("100", "5", "5")



def test_comparables_fccr_convention_matches_operating_income_bridge():
    tgt_ebitda = ebitda_from_operating_income("5566", "2981")
    tgt_rent = fixed_operating_lease_cost("641", "132")
    assert tgt_ebitda == D("8547")
    assert tgt_rent == D("509")
    assert adjusted_ebitdar(tgt_ebitda, tgt_rent) == D("9056")
    assert close(fixed_charge_coverage_ratio("9056", "411", "509"), D("9.843478260869565"))

    wmt_ebitda = ebitda_from_operating_income("29348", "12973")
    assert wmt_ebitda == D("42321")
    assert adjusted_ebitdar(wmt_ebitda, "2347") == D("44668")
    assert close(fixed_charge_coverage_ratio("44668", "2245", "2347"), D("9.727351916376306"))


def test_lbo_moic_and_hold_period_irr():
    assert moic("200", "100") == D("2")
    irr = simple_hold_period_irr_percent("200", "100", 5)
    assert close(irr, D("14.8698354997035"), "0.000000001")


def test_rank_comparison_is_deterministic():
    a = {"A": "30", "B": "20", "C": "10"}
    b = {"A": "3", "B": "2", "C": "1"}
    c = {"B": "3", "A": "2", "C": "1"}
    assert rank_desc(a) == ["A", "B", "C"]
    assert same_rank_order(a, b) is True
    assert same_rank_order(a, c) is False



def test_market_sentiment_is_only_return_sign():
    assert market_sentiment_from_return("2.5") == "POSITIVE"
    assert market_sentiment_from_return("-0.1") == "NEGATIVE"
    assert market_sentiment_from_return("0") == "NEUTRAL"


def test_guidance_conservatism_requires_strict_series_dominance():
    assert conservative_guidance_dominance(["4", "8"], ["-4", "-2"]) == "A"
    assert conservative_guidance_dominance(["-4"], ["4", "8"]) == "B"
    assert conservative_guidance_dominance(["1", "5"], ["3", "4"]) == "AMBIGUOUS"


def test_fail_closed_numeric_boundaries():
    with pytest.raises(FinanceAlgebraError):
        cagr("10", "0", 2)
    with pytest.raises(FinanceAlgebraError):
        cagr("-1", "10", 2)
    with pytest.raises(FinanceAlgebraError):
        percent_change("1", "0")
