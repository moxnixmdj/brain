#!/usr/bin/env python3
"""Deterministic Decimal finance algebra for Project Brain.

This module is deliberately narrow: it computes finance quantities from already
bound numeric inputs. It performs no semantic extraction, source selection,
network access, model inference, or benchmark-specific answer lookup.

All public entry points return Decimal values unless otherwise documented.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, getcontext
from typing import Iterable, Mapping, Sequence

getcontext().prec = 50

D = Decimal
HUNDRED = D("100")
TEN_THOUSAND = D("10000")


class FinanceAlgebraError(ValueError):
    pass


def decimal(value: object) -> Decimal:
    if isinstance(value, bool):
        raise FinanceAlgebraError("BOOLEAN_NOT_NUMERIC")
    if isinstance(value, Decimal):
        out = value
    elif isinstance(value, int):
        out = D(value)
    elif isinstance(value, str):
        raw = value.strip().replace(",", "")
        if raw.startswith("(") and raw.endswith(")"):
            raw = "-" + raw[1:-1].strip()
        raw = raw.removeprefix("$").strip()
        if raw.endswith("%"):
            raw = raw[:-1].strip()
        try:
            out = D(raw)
        except InvalidOperation as exc:
            raise FinanceAlgebraError("DECIMAL_INVALID") from exc
    else:
        raise FinanceAlgebraError("DECIMAL_TYPE_INVALID")
    if not out.is_finite():
        raise FinanceAlgebraError("DECIMAL_NONFINITE")
    return out


def _nonzero(value: object, code: str = "DIVISOR_ZERO") -> Decimal:
    out = decimal(value)
    if out == 0:
        raise FinanceAlgebraError(code)
    return out


def ratio(numerator: object, denominator: object) -> Decimal:
    return decimal(numerator) / _nonzero(denominator)


def percent_of(numerator: object, denominator: object) -> Decimal:
    return ratio(numerator, denominator) * HUNDRED


def percent_change(new_value: object, old_value: object) -> Decimal:
    old = _nonzero(old_value, "OLD_VALUE_ZERO")
    return (decimal(new_value) / old - D(1)) * HUNDRED


def basis_points_from_percent_delta(percent_delta: object) -> Decimal:
    return decimal(percent_delta) * D(100)


def basis_points_between(new_percent: object, old_percent: object) -> Decimal:
    return (decimal(new_percent) - decimal(old_percent)) * D(100)


def average(values: Iterable[object]) -> Decimal:
    xs = [decimal(x) for x in values]
    if not xs:
        raise FinanceAlgebraError("AVERAGE_EMPTY")
    return sum(xs, D(0)) / D(len(xs))


def midpoint(low: object, high: object) -> Decimal:
    return (decimal(low) + decimal(high)) / D(2)


def cagr(end_value: object, start_value: object, periods: int) -> Decimal:
    if not isinstance(periods, int) or isinstance(periods, bool) or periods <= 0:
        raise FinanceAlgebraError("PERIODS_INVALID")
    start = _nonzero(start_value, "START_VALUE_ZERO")
    end = decimal(end_value)
    if start < 0 or end < 0:
        raise FinanceAlgebraError("CAGR_NEGATIVE_VALUE")
    if end == 0:
        return D("-100")
    exponent = D(1) / D(periods)
    growth_factor = getcontext().power(end / start, exponent)
    return (growth_factor - D(1)) * HUNDRED



def actual_fiscal_days(start_date: str, end_date: str) -> int:
    """Inclusive calendar-day count for a fiscal reporting period."""
    try:
        start = date.fromisoformat(str(start_date))
        end = date.fromisoformat(str(end_date))
    except Exception as exc:
        raise FinanceAlgebraError("FISCAL_DATE_INVALID") from exc
    if end < start:
        raise FinanceAlgebraError("FISCAL_DATE_ORDER_INVALID")
    return (end - start).days + 1


def days_inventory_outstanding(
    beginning_inventory: object,
    ending_inventory: object,
    cost_of_sales: object,
    actual_fiscal_days: object,
) -> Decimal:
    avg_inventory = average((beginning_inventory, ending_inventory))
    return ratio(avg_inventory, cost_of_sales) * decimal(actual_fiscal_days)


def debt_to_equity(debt: object, equity: object) -> Decimal:
    return ratio(debt, equity)


def debt_to_total_capital(debt: object, equity: object) -> Decimal:
    d = decimal(debt)
    e = decimal(equity)
    return ratio(d, d + e) * HUNDRED


def price_to_book(market_cap: object, book_equity: object) -> Decimal:
    return ratio(market_cap, book_equity)


def enterprise_value(
    equity_value: object,
    debt: object = 0,
    preferred_stock: object = 0,
    noncontrolling_interest: object = 0,
    cash_and_equivalents: object = 0,
) -> Decimal:
    return (
        decimal(equity_value)
        + decimal(debt)
        + decimal(preferred_stock)
        + decimal(noncontrolling_interest)
        - decimal(cash_and_equivalents)
    )


def ev_to_ebitda(ev: object, ebitda: object) -> Decimal:
    return ratio(ev, ebitda)


def ebitda_margin(ebitda: object, revenue: object) -> Decimal:
    return percent_of(ebitda, revenue)


def adjusted_ebitda(
    operating_income: object,
    depreciation_and_amortization: object,
    adjustments: Iterable[object] = (),
) -> Decimal:
    return (
        decimal(operating_income)
        + decimal(depreciation_and_amortization)
        + sum((decimal(x) for x in adjustments), D(0))
    )


def adjusted_ebitdar(ebitda: object, rent_obligations: object) -> Decimal:
    return decimal(ebitda) + decimal(rent_obligations)


def fixed_charge_coverage_ratio(
    ebitdar: object,
    interest_expense: object,
    fixed_operating_lease_cost: object,
) -> Decimal:
    fixed_charges = decimal(interest_expense) + decimal(fixed_operating_lease_cost)
    return ratio(ebitdar, fixed_charges)


def transaction_premium(offer_price: object, unaffected_price: object) -> Decimal:
    return percent_change(offer_price, unaffected_price)


def beat_miss_percent(actual: object, guidance_reference: object) -> Decimal:
    return percent_change(actual, guidance_reference)


def intensity(value: object, revenue: object) -> Decimal:
    return percent_of(value, revenue)


def discount_factor(rate_percent: object, years: int) -> Decimal:
    if not isinstance(years, int) or isinstance(years, bool) or years < 0:
        raise FinanceAlgebraError("YEARS_INVALID")
    rate = decimal(rate_percent) / HUNDRED
    base = D(1) + rate
    if base <= 0:
        raise FinanceAlgebraError("DISCOUNT_BASE_NONPOSITIVE")
    return D(1) / (base ** years)


def present_value(value: object, rate_percent: object, years: int) -> Decimal:
    return decimal(value) * discount_factor(rate_percent, years)


def terminal_value_exit_multiple(terminal_ebitda: object, exit_multiple: object) -> Decimal:
    return decimal(terminal_ebitda) * decimal(exit_multiple)


def terminal_value_perpetual_growth(
    next_period_fcf: object,
    discount_rate_percent: object,
    terminal_growth_percent: object,
) -> Decimal:
    r = decimal(discount_rate_percent) / HUNDRED
    g = decimal(terminal_growth_percent) / HUNDRED
    if r <= g:
        raise FinanceAlgebraError("DISCOUNT_RATE_NOT_ABOVE_GROWTH")
    return decimal(next_period_fcf) / (r - g)


def dcf_enterprise_value(
    projected_fcfs: Sequence[object],
    discount_rate_percent: object,
    terminal_value: object,
) -> Decimal:
    if not projected_fcfs:
        raise FinanceAlgebraError("PROJECTED_FCFS_EMPTY")
    pv_fcfs = sum(
        (present_value(value, discount_rate_percent, year) for year, value in enumerate(projected_fcfs, start=1)),
        D(0),
    )
    pv_terminal = present_value(terminal_value, discount_rate_percent, len(projected_fcfs))
    return pv_fcfs + pv_terminal


def moic(exit_equity_value: object, initial_sponsor_equity: object) -> Decimal:
    return ratio(exit_equity_value, initial_sponsor_equity)


def simple_hold_period_irr_percent(
    exit_equity_value: object,
    initial_sponsor_equity: object,
    years: int,
) -> Decimal:
    if not isinstance(years, int) or isinstance(years, bool) or years <= 0:
        raise FinanceAlgebraError("YEARS_INVALID")
    multiple = moic(exit_equity_value, initial_sponsor_equity)
    if multiple < 0:
        raise FinanceAlgebraError("NEGATIVE_MOIC")
    if multiple == 0:
        return D("-100")
    return (getcontext().power(multiple, D(1) / D(years)) - D(1)) * HUNDRED


def rank_desc(values: Mapping[str, object]) -> list[str]:
    if not values:
        raise FinanceAlgebraError("RANK_EMPTY")
    normalized = [(name, decimal(value)) for name, value in values.items()]
    return [name for name, _ in sorted(normalized, key=lambda x: (-x[1], x[0]))]


def same_rank_order(a: Mapping[str, object], b: Mapping[str, object]) -> bool:
    return rank_desc(a) == rank_desc(b)



def signed_direction(value: object) -> str:
    x = decimal(value)
    if x > 0:
        return "POSITIVE"
    if x < 0:
        return "NEGATIVE"
    return "FLAT"


def market_sentiment_from_return(return_percent: object) -> str:
    """Deterministic benchmark-compatible sign interpretation only."""
    direction = signed_direction(return_percent)
    if direction == "POSITIVE":
        return "POSITIVE"
    if direction == "NEGATIVE":
        return "NEGATIVE"
    return "NEUTRAL"


def conservative_guidance_dominance(
    a_beat_miss_percents: Sequence[object],
    b_beat_miss_percents: Sequence[object],
) -> str:
    """Return the unambiguous more-conservative guidance series, else AMBIGUOUS.

    Higher actual-vs-guidance beat/miss percentages mean actual results exceeded
    guidance by more. We claim dominance only when every observation in one
    series is strictly above every observation in the other series.
    """
    if not a_beat_miss_percents or not b_beat_miss_percents:
        raise FinanceAlgebraError("GUIDANCE_SERIES_EMPTY")
    a = [decimal(x) for x in a_beat_miss_percents]
    b = [decimal(x) for x in b_beat_miss_percents]
    if min(a) > max(b):
        return "A"
    if min(b) > max(a):
        return "B"
    return "AMBIGUOUS"


__all__ = [
    "FinanceAlgebraError",
    "actual_fiscal_days",
    "adjusted_ebitda",
    "adjusted_ebitdar",
    "average",
    "basis_points_between",
    "basis_points_from_percent_delta",
    "beat_miss_percent",
    "cagr",
    "conservative_guidance_dominance",
    "days_inventory_outstanding",
    "dcf_enterprise_value",
    "debt_to_equity",
    "debt_to_total_capital",
    "decimal",
    "discount_factor",
    "ebitda_margin",
    "enterprise_value",
    "ev_to_ebitda",
    "fixed_charge_coverage_ratio",
    "intensity",
    "market_sentiment_from_return",
    "midpoint",
    "moic",
    "percent_change",
    "percent_of",
    "present_value",
    "price_to_book",
    "rank_desc",
    "ratio",
    "same_rank_order",
    "signed_direction",
    "simple_hold_period_irr_percent",
    "terminal_value_exit_multiple",
    "terminal_value_perpetual_growth",
    "transaction_premium",
]
