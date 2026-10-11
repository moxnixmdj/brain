#!/usr/bin/env python3
"""Deterministic finance formula compiler for Finance Agent v2.

This module chooses no accounting inputs and claims no benchmark score. It only
turns explicitly supplied numeric inputs into calculator expressions for common
finance transformations, so the official calculator performs the arithmetic
without intermediate rounding.

Source selection and convention choice remain separate obligations.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Sequence

SCHEMA = "PROJECT_BRAIN_FINANCE_METRIC_FORMULA_V1"


class FinanceFormulaError(ValueError):
    pass


def _num(value: Any, label: str) -> str:
    if isinstance(value, bool):
        raise FinanceFormulaError(label + "_INVALID")
    try:
        d = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError) as exc:
        raise FinanceFormulaError(label + "_INVALID") from exc
    if not d.is_finite():
        raise FinanceFormulaError(label + "_NONFINITE")
    return format(d, "f")


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise FinanceFormulaError(label + "_INVALID")
    try:
        n = int(value)
    except (TypeError, ValueError) as exc:
        raise FinanceFormulaError(label + "_INVALID") from exc
    if n <= 0 or str(n) != str(value).strip():
        raise FinanceFormulaError(label + "_INVALID")
    return n


def _nonzero(value: Any, label: str) -> str:
    text = _num(value, label)
    if Decimal(text) == 0:
        raise FinanceFormulaError(label + "_ZERO")
    return text


def average_expression(values: Sequence[Any]) -> str:
    vals = [_num(v, "VALUE") for v in values]
    if not vals:
        raise FinanceFormulaError("VALUES_REQUIRED")
    return "(" + "+".join(vals) + f")/{len(vals)}"


def midpoint_expression(low: Any, high: Any) -> str:
    return f"({_num(low,'LOW')}+{_num(high,'HIGH')})/2"


def percent_change_expression(start: Any, end: Any) -> str:
    s = _nonzero(start, "START")
    e = _num(end, "END")
    return f"(({e}/{s})-1)*100"


def cagr_expression(start: Any, end: Any, years: Any) -> str:
    s = _nonzero(start, "START")
    e = _num(end, "END")
    y = _positive_int(years, "YEARS")
    if Decimal(s) < 0 or Decimal(e) < 0:
        raise FinanceFormulaError("CAGR_NEGATIVE_INPUT_UNSUPPORTED")
    return f"(({e}/{s})**(1/{y})-1)*100"


def margin_expression(numerator: Any, denominator: Any) -> str:
    n = _num(numerator, "NUMERATOR")
    d = _nonzero(denominator, "DENOMINATOR")
    return f"({n}/{d})*100"


def difference_bps_expression(
    first_percent: Any,
    second_percent: Any,
) -> str:
    a = _num(first_percent, "FIRST_PERCENT")
    b = _num(second_percent, "SECOND_PERCENT")
    # Inputs are percentage-point values, e.g. 17.05 and 16.45.
    return f"({a}-{b})*100"


def dio_expression(
    beginning_inventory: Any,
    ending_inventory: Any,
    cogs: Any,
    actual_days: Any,
) -> str:
    b = _num(beginning_inventory, "BEGINNING_INVENTORY")
    e = _num(ending_inventory, "ENDING_INVENTORY")
    c = _nonzero(cogs, "COGS")
    days = _num(actual_days, "ACTUAL_DAYS")
    return f"((({b}+{e})/2)/{c})*{days}"


def debt_to_equity_expression(debt: Any, equity: Any) -> str:
    d = _num(debt, "DEBT")
    e = _nonzero(equity, "EQUITY")
    return f"{d}/{e}"


def debt_to_total_capital_expression(debt: Any, equity: Any) -> str:
    d = _num(debt, "DEBT")
    e = _num(equity, "EQUITY")
    if Decimal(d) + Decimal(e) == 0:
        raise FinanceFormulaError("TOTAL_CAPITAL_ZERO")
    return f"({d}/({d}+{e}))*100"


def fixed_charge_coverage_expression(ebitdar: Any, fixed_charges: Any) -> str:
    n = _num(ebitdar, "EBITDAR")
    d = _nonzero(fixed_charges, "FIXED_CHARGES")
    return f"{n}/{d}"


def beat_miss_expression(actual: Any, guidance_reference: Any) -> str:
    a = _num(actual, "ACTUAL")
    g = _nonzero(guidance_reference, "GUIDANCE_REFERENCE")
    return f"(({a}/{g})-1)*100"


def formula_record(metric: str, expression: str, *, convention: str) -> dict[str, Any]:
    metric = str(metric or "").strip()
    convention = str(convention or "").strip()
    expression = str(expression or "").strip()
    if not metric:
        raise FinanceFormulaError("METRIC_REQUIRED")
    if not expression:
        raise FinanceFormulaError("EXPRESSION_REQUIRED")
    if not convention:
        raise FinanceFormulaError("CONVENTION_REQUIRED")
    return {
        "schema": SCHEMA,
        "metric": metric,
        "calculator_expression": expression,
        "convention": convention,
        "intermediate_rounding_allowed": False,
        "calculator_execution_required": True,
        "source_selection_authority": False,
        "accounting_convention_selection_authority": False,
        "acceptance_credit_delta": 0,
    }
