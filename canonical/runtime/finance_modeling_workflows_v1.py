#!/usr/bin/env python3
"""Deterministic full-workflow finance modeling for Project Brain.

This module executes two explicit modeling contracts from already-bound numeric
inputs:

1. a simplified sponsor LBO with average-debt interest and full FCF debt sweep;
2. a five-or-N-year constant-ratio unlevered DCF with both exit-multiple and
   perpetual-growth terminal methods.

It performs no source discovery, semantic extraction, benchmark lookup, model
inference, or hidden-convention guessing. Ambiguous conventions fail closed.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from canonical.runtime.finance_quantitative_algebra_v1 import (
    FinanceAlgebraError,
    decimal,
    simple_hold_period_irr_percent,
)

D = Decimal
HUNDRED = D("100")
TWO = D("2")


def _pct(value: object) -> Decimal:
    return decimal(value) / HUNDRED


def _positive_int(value: object, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise FinanceAlgebraError(code)
    return value


def simplified_lbo_model(
    *,
    share_price: object,
    offer_premium_percent: object,
    basic_shares_million: object,
    transaction_expenses_million: object,
    base_revenue_million: object,
    base_ebitda_million: object,
    starting_cash_million: object,
    existing_debt_million: object,
    minimum_cash_million: object,
    entry_leverage_x: object,
    debt_interest_rate_percent: object,
    cash_interest_rate_percent: object,
    tax_rate_percent: object,
    revenue_growth_percent: object,
    annual_ebitda_margin_expansion_pp: object,
    d_and_a_percent_revenue: object,
    capex_percent_revenue: object,
    hold_years: int,
    exit_multiple_x: object,
) -> dict[str, Any]:
    """Run an explicit simplified LBO with an average-debt interest convention.

    The debt sweep is solved analytically because current-period interest uses
    average beginning/end debt while end debt itself depends on post-interest
    FCF. The route intentionally fails closed if debt would be fully repaid
    before exit because the treatment of post-paydown excess cash is then a
    separate convention that must be supplied rather than guessed.
    """
    years = _positive_int(hold_years, "HOLD_YEARS_INVALID")
    sp = decimal(share_price)
    premium = _pct(offer_premium_percent)
    shares = decimal(basic_shares_million)
    tx = decimal(transaction_expenses_million)
    revenue = decimal(base_revenue_million)
    ebitda = decimal(base_ebitda_million)
    starting_cash = decimal(starting_cash_million)
    existing_debt = decimal(existing_debt_million)
    minimum_cash = decimal(minimum_cash_million)
    leverage = decimal(entry_leverage_x)
    debt_rate = _pct(debt_interest_rate_percent)
    cash_rate = _pct(cash_interest_rate_percent)
    tax_rate = _pct(tax_rate_percent)
    revenue_growth = _pct(revenue_growth_percent)
    margin_expansion = _pct(annual_ebitda_margin_expansion_pp)
    da_pct = _pct(d_and_a_percent_revenue)
    capex_pct = _pct(capex_percent_revenue)
    exit_multiple = decimal(exit_multiple_x)

    if shares <= 0:
        raise FinanceAlgebraError("SHARES_NONPOSITIVE")
    if revenue <= 0 or ebitda <= 0:
        raise FinanceAlgebraError("BASE_OPERATING_INPUT_NONPOSITIVE")
    if minimum_cash < 0 or starting_cash < 0 or existing_debt < 0:
        raise FinanceAlgebraError("BALANCE_SHEET_INPUT_NEGATIVE")
    if leverage < 0 or exit_multiple < 0:
        raise FinanceAlgebraError("MULTIPLE_NEGATIVE")
    if not (D("0") <= tax_rate < D("1")):
        raise FinanceAlgebraError("TAX_RATE_OUT_OF_RANGE")
    if debt_rate < 0 or cash_rate < 0:
        raise FinanceAlgebraError("INTEREST_RATE_NEGATIVE")

    offer_price = sp * (D("1") + premium)
    purchase_equity_value = offer_price * shares
    new_debt = leverage * ebitda

    excess_cash_source = max(starting_cash - minimum_cash, D("0"))
    minimum_cash_funding_gap = max(minimum_cash - starting_cash, D("0"))
    sponsor_equity = (
        purchase_equity_value
        + tx
        + existing_debt
        + minimum_cash_funding_gap
        - new_debt
        - excess_cash_source
    )
    if sponsor_equity <= 0:
        raise FinanceAlgebraError("SPONSOR_EQUITY_NONPOSITIVE")

    base_ebitda_margin = ebitda / revenue
    debt = new_debt
    schedule: list[dict[str, Any]] = []

    for year in range(1, years + 1):
        revenue *= D("1") + revenue_growth
        ebitda_margin = base_ebitda_margin + margin_expansion * D(year)
        ebitda = revenue * ebitda_margin
        da = revenue * da_pct
        capex = revenue * capex_pct
        ebit = ebitda - da
        cash_interest = minimum_cash * cash_rate

        after_tax_fraction = D("1") - tax_rate
        # FCF = A - interest, and interest = rate*(begin+end)/2 where
        # end = begin - FCF. Rearrangement gives the closed-form end balance.
        a = (ebit + cash_interest) * after_tax_fraction + da - capex
        b = debt_rate / TWO * after_tax_fraction
        if b >= D("1"):
            raise FinanceAlgebraError("AVERAGE_DEBT_CIRCULARITY_UNSTABLE")
        end_debt = (debt - a + b * debt) / (D("1") - b)
        if end_debt < 0:
            raise FinanceAlgebraError(
                "DEBT_REPAID_BEFORE_EXIT__POST_PAYDOWN_CASH_CONVENTION_REQUIRED"
            )

        interest_expense = debt_rate * (debt + end_debt) / TWO
        fcf_for_debt_sweep = (
            (ebit - interest_expense + cash_interest) * after_tax_fraction
            + da
            - capex
        )
        debt_paydown = debt - end_debt

        schedule.append(
            {
                "year": year,
                "revenue_million": revenue,
                "ebitda_margin_percent": ebitda_margin * HUNDRED,
                "ebitda_million": ebitda,
                "d_and_a_million": da,
                "capex_million": capex,
                "ebit_million": ebit,
                "beginning_debt_million": debt,
                "interest_expense_million": interest_expense,
                "cash_interest_income_million": cash_interest,
                "fcf_for_debt_sweep_million": fcf_for_debt_sweep,
                "debt_paydown_million": debt_paydown,
                "ending_debt_million": end_debt,
            }
        )
        debt = end_debt

    exit_enterprise_value = ebitda * exit_multiple
    exit_equity_value = exit_enterprise_value - debt + minimum_cash
    sponsor_moic = exit_equity_value / sponsor_equity
    sponsor_irr_percent = simple_hold_period_irr_percent(
        exit_equity_value, sponsor_equity, years
    )

    return {
        "status": "PASS__DETERMINISTIC_SIMPLIFIED_LBO",
        "offer_price": offer_price,
        "purchase_equity_value_million": purchase_equity_value,
        "new_debt_million": new_debt,
        "excess_cash_source_million": excess_cash_source,
        "minimum_cash_funding_gap_million": minimum_cash_funding_gap,
        "initial_sponsor_equity_million": sponsor_equity,
        "base_ebitda_margin_percent": base_ebitda_margin * HUNDRED,
        "schedule": schedule,
        "exit_enterprise_value_million": exit_enterprise_value,
        "exit_debt_million": debt,
        "exit_cash_million": minimum_cash,
        "exit_equity_value_million": exit_equity_value,
        "sponsor_moic_x": sponsor_moic,
        "sponsor_irr_percent": sponsor_irr_percent,
        "conventions": {
            "interest_expense": "AVERAGE_BEGINNING_ENDING_DEBT",
            "interest_income": "MINIMUM_CASH_BALANCE",
            "fcf_sweep": "ALL_POST_TAX_FCF_TO_NEW_DEBT",
            "minimum_cash": "PRESERVED_THROUGH_EXIT",
            "post_debt_paydown_cash": "FAIL_CLOSED_IF_REQUIRED",
        },
        "model_dependency_count": 0,
        "external_cognition_dependency_count": 0,
        "source_fact_binding_proved": False,
        "terminal_authority": False,
    }


def constant_ratio_dcf_model(
    *,
    base_revenue_million: object,
    revenue_growth_percent: object,
    ebitda_margin_percent: object,
    d_and_a_percent_revenue: object,
    tax_rate_percent: object,
    deferred_taxes_million: object,
    other_operating_activity_million: object,
    change_nwc_percent_revenue: object,
    capex_percent_revenue: object,
    wacc_percent: object,
    exit_multiple_x: object,
    terminal_growth_percent: object,
    net_debt_million: object,
    shares_outstanding_million: object,
    projection_years: int = 5,
) -> dict[str, Any]:
    """Project unlevered FCF under explicit constant-ratio assumptions.

    FCF convention:
      EBIT*(1-tax) + D&A + deferred taxes + other operating activities
      - change in NWC - CapEx

    Both terminal methods use the same projected operating path. Perpetual growth
    applies terminal growth to the final projected FCF exactly once.
    """
    years = _positive_int(projection_years, "PROJECTION_YEARS_INVALID")
    revenue = decimal(base_revenue_million)
    growth = _pct(revenue_growth_percent)
    ebitda_margin = _pct(ebitda_margin_percent)
    da_pct = _pct(d_and_a_percent_revenue)
    tax_rate = _pct(tax_rate_percent)
    deferred_taxes = decimal(deferred_taxes_million)
    other_operating = decimal(other_operating_activity_million)
    nwc_pct = _pct(change_nwc_percent_revenue)
    capex_pct = _pct(capex_percent_revenue)
    wacc = _pct(wacc_percent)
    exit_multiple = decimal(exit_multiple_x)
    terminal_growth = _pct(terminal_growth_percent)
    net_debt = decimal(net_debt_million)
    shares = decimal(shares_outstanding_million)

    if revenue <= 0 or shares <= 0:
        raise FinanceAlgebraError("DCF_SCALE_INPUT_NONPOSITIVE")
    if not (D("0") <= tax_rate < D("1")):
        raise FinanceAlgebraError("TAX_RATE_OUT_OF_RANGE")
    if wacc <= terminal_growth:
        raise FinanceAlgebraError("WACC_NOT_ABOVE_TERMINAL_GROWTH")
    if wacc <= D("-1") or growth <= D("-1"):
        raise FinanceAlgebraError("DCF_RATE_INVALID")
    if exit_multiple < 0:
        raise FinanceAlgebraError("EXIT_MULTIPLE_NEGATIVE")

    schedule: list[dict[str, Any]] = []
    pv_fcfs = D("0")
    for year in range(1, years + 1):
        revenue *= D("1") + growth
        ebitda = revenue * ebitda_margin
        da = revenue * da_pct
        ebit = ebitda - da
        nopat = ebit * (D("1") - tax_rate)
        change_nwc = revenue * nwc_pct
        capex = revenue * capex_pct
        fcf = (
            nopat
            + da
            + deferred_taxes
            + other_operating
            - change_nwc
            - capex
        )
        discount_factor = D("1") / ((D("1") + wacc) ** year)
        pv_fcf = fcf * discount_factor
        pv_fcfs += pv_fcf
        schedule.append(
            {
                "year": year,
                "revenue_million": revenue,
                "ebitda_million": ebitda,
                "d_and_a_million": da,
                "ebit_million": ebit,
                "nopat_million": nopat,
                "deferred_taxes_million": deferred_taxes,
                "other_operating_activity_million": other_operating,
                "change_nwc_million": change_nwc,
                "capex_million": capex,
                "fcf_million": fcf,
                "discount_factor": discount_factor,
                "pv_fcf_million": pv_fcf,
            }
        )

    final = schedule[-1]
    terminal_exit = final["ebitda_million"] * exit_multiple
    pv_terminal_exit = terminal_exit / ((D("1") + wacc) ** years)
    enterprise_value_exit = pv_fcfs + pv_terminal_exit

    next_period_fcf = final["fcf_million"] * (D("1") + terminal_growth)
    terminal_perpetual = next_period_fcf / (wacc - terminal_growth)
    pv_terminal_perpetual = terminal_perpetual / ((D("1") + wacc) ** years)
    enterprise_value_perpetual = pv_fcfs + pv_terminal_perpetual

    equity_value_exit = enterprise_value_exit - net_debt
    equity_value_perpetual = enterprise_value_perpetual - net_debt
    per_share_exit = equity_value_exit / shares
    per_share_perpetual = equity_value_perpetual / shares

    return {
        "status": "PASS__DETERMINISTIC_CONSTANT_RATIO_DCF",
        "schedule": schedule,
        "pv_projected_fcf_million": pv_fcfs,
        "exit_multiple_method": {
            "terminal_value_million": terminal_exit,
            "pv_terminal_value_million": pv_terminal_exit,
            "enterprise_value_million": enterprise_value_exit,
            "equity_value_million": equity_value_exit,
            "per_share_equity_value": per_share_exit,
        },
        "perpetual_growth_method": {
            "next_period_fcf_million": next_period_fcf,
            "terminal_value_million": terminal_perpetual,
            "pv_terminal_value_million": pv_terminal_perpetual,
            "enterprise_value_million": enterprise_value_perpetual,
            "equity_value_million": equity_value_perpetual,
            "per_share_equity_value": per_share_perpetual,
        },
        "higher_per_share_method": (
            "PERPETUAL_GROWTH"
            if per_share_perpetual > per_share_exit
            else "EXIT_MULTIPLE"
            if per_share_exit > per_share_perpetual
            else "EQUAL"
        ),
        "conventions": {
            "fcf": "NOPAT_PLUS_DA_PLUS_DEFERRED_TAXES_PLUS_OTHER_MINUS_CHANGE_NWC_MINUS_CAPEX",
            "terminal_perpetual_growth": "FINAL_PROJECTED_FCF_GROWN_ONE_PERIOD",
            "net_debt": "EXPLICIT_BOUND_INPUT",
        },
        "model_dependency_count": 0,
        "external_cognition_dependency_count": 0,
        "source_fact_binding_proved": False,
        "terminal_authority": False,
    }


__all__ = [
    "constant_ratio_dcf_model",
    "simplified_lbo_model",
]
