from decimal import Decimal, ROUND_HALF_UP

import pytest

from canonical.runtime.finance_modeling_workflows_v1 import (
    constant_ratio_dcf_model,
    simplified_lbo_model,
)
from canonical.runtime.finance_quantitative_algebra_v1 import FinanceAlgebraError


Q2 = Decimal("0.01")


def q2(value):
    return value.quantize(Q2, rounding=ROUND_HALF_UP)


def test_public_q26_like_epam_lbo_heavy_outputs_recompute_from_bound_inputs():
    out = simplified_lbo_model(
        share_price="141.00",
        offer_premium_percent="30.0",
        basic_shares_million="55.893",
        transaction_expenses_million="50",
        base_revenue_million="5457.056",
        base_ebitda_million="644.814",
        starting_cash_million="1296.077",
        existing_debt_million="25.034",
        minimum_cash_million="500",
        entry_leverage_x="5.0",
        debt_interest_rate_percent="8.0",
        cash_interest_rate_percent="2.0",
        tax_rate_percent="25.0",
        revenue_growth_percent="8.0",
        annual_ebitda_margin_expansion_pp="1.0",
        d_and_a_percent_revenue="2.5",
        capex_percent_revenue="1.0",
        hold_years=5,
        exit_multiple_x="10.0",
    )

    assert q2(out["initial_sponsor_equity_million"]) == Decimal("6300.07")
    assert q2(out["exit_enterprise_value_million"]) == Decimal("13483.54")
    assert q2(out["exit_equity_value_million"]) == Decimal("13976.13")
    assert q2(out["sponsor_moic_x"]) == Decimal("2.22")
    assert q2(out["sponsor_irr_percent"]) == Decimal("17.28")
    assert len(out["schedule"]) == 5
    assert out["schedule"][-1]["ending_debt_million"] > 0
    assert out["model_dependency_count"] == 0
    assert out["source_fact_binding_proved"] is False


def test_public_q27_like_lmt_dcf_recomputes_both_public_display_targets():
    revenue_2024 = Decimal("71043")
    revenue_2025 = Decimal("75048")
    revenue_growth = (revenue_2025 / revenue_2024 - Decimal(1)) * Decimal(100)
    ebitda_2025 = Decimal("7731") + Decimal("1687")
    ebitda_margin = ebitda_2025 / revenue_2025 * Decimal(100)
    da_percent = Decimal("1687") / revenue_2025 * Decimal(100)
    other_operating_average = (
        Decimal("-754") + Decimal("-509") + Decimal("-140")
    ) / Decimal(3)

    out = constant_ratio_dcf_model(
        base_revenue_million=revenue_2025,
        revenue_growth_percent=revenue_growth,
        ebitda_margin_percent=ebitda_margin,
        d_and_a_percent_revenue=da_percent,
        tax_rate_percent="15.3",
        deferred_taxes_million="372",
        other_operating_activity_million=other_operating_average,
        change_nwc_percent_revenue="0.25",
        capex_percent_revenue="2.0",
        wacc_percent="8.0",
        exit_multiple_x="10.0",
        terminal_growth_percent="2.5",
        net_debt_million="17579",
        shares_outstanding_million="231.4",
        projection_years=5,
    )

    assert q2(out["exit_multiple_method"]["per_share_equity_value"]) == Decimal("419.21")
    assert q2(out["perpetual_growth_method"]["per_share_equity_value"]) == Decimal("521.62")
    assert out["higher_per_share_method"] == "PERPETUAL_GROWTH"
    assert len(out["schedule"]) == 5
    assert out["model_dependency_count"] == 0
    assert out["source_fact_binding_proved"] is False


def test_lbo_fails_closed_when_debt_would_be_repaid_before_exit():
    with pytest.raises(
        FinanceAlgebraError,
        match="DEBT_REPAID_BEFORE_EXIT__POST_PAYDOWN_CASH_CONVENTION_REQUIRED",
    ):
        simplified_lbo_model(
            share_price="10",
            offer_premium_percent="0",
            basic_shares_million="10",
            transaction_expenses_million="0",
            base_revenue_million="1000",
            base_ebitda_million="500",
            starting_cash_million="0",
            existing_debt_million="0",
            minimum_cash_million="0",
            entry_leverage_x="0.1",
            debt_interest_rate_percent="1",
            cash_interest_rate_percent="0",
            tax_rate_percent="0",
            revenue_growth_percent="50",
            annual_ebitda_margin_expansion_pp="0",
            d_and_a_percent_revenue="0",
            capex_percent_revenue="0",
            hold_years=2,
            exit_multiple_x="10",
        )


def test_dcf_rejects_terminal_growth_at_or_above_wacc():
    with pytest.raises(FinanceAlgebraError, match="WACC_NOT_ABOVE_TERMINAL_GROWTH"):
        constant_ratio_dcf_model(
            base_revenue_million="100",
            revenue_growth_percent="5",
            ebitda_margin_percent="20",
            d_and_a_percent_revenue="2",
            tax_rate_percent="25",
            deferred_taxes_million="0",
            other_operating_activity_million="0",
            change_nwc_percent_revenue="0",
            capex_percent_revenue="1",
            wacc_percent="5",
            exit_multiple_x="10",
            terminal_growth_percent="5",
            net_debt_million="0",
            shares_outstanding_million="10",
            projection_years=5,
        )
