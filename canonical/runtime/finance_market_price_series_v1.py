#!/usr/bin/env python3
"""Deterministic daily-market-price semantics for Finance Agent v2.

Consumes already-authenticated daily price rows. This module does not fetch
prices or certify a market-data provider. It implements the benchmark-relevant
selection semantics: raw closing price, exact date when present, or next
trading day for calendar-offset event windows when explicitly requested.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_FINANCE_MARKET_PRICE_SERIES_V1"


class MarketPriceError(ValueError):
    pass


def _date(value: Any) -> date:
    try:
        return date.fromisoformat(str(value))
    except Exception as exc:
        raise MarketPriceError("DATE_INVALID") from exc


def _decimal(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise MarketPriceError("PRICE_INVALID")
    try:
        out = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise MarketPriceError("PRICE_INVALID") from exc
    if not out.is_finite() or out <= 0:
        raise MarketPriceError("PRICE_INVALID")
    return out


def normalize_daily_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes))
        or not rows
    ):
        raise MarketPriceError("PRICE_ROWS_REQUIRED")
    out: list[dict[str, Any]] = []
    seen: set[date] = set()
    for index, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise MarketPriceError("PRICE_ROW_NOT_OBJECT:" + str(index))
        d = _date(raw.get("date"))
        if d in seen:
            raise MarketPriceError("DUPLICATE_TRADING_DATE:" + d.isoformat())
        seen.add(d)
        close = _decimal(raw.get("close"))
        out.append({
            "date": d.isoformat(),
            "close": close,
        })
    out.sort(key=lambda x: x["date"])
    return out


def close_on_date(
    rows: Sequence[Mapping[str, Any]],
    target_date: str,
    *,
    next_trading_day_if_missing: bool = False,
) -> dict[str, Any]:
    normalized = normalize_daily_rows(rows)
    target = _date(target_date)
    mapping = {_date(x["date"]): x["close"] for x in normalized}
    if target in mapping:
        used = target
    elif next_trading_day_if_missing:
        later = sorted(d for d in mapping if d > target)
        if not later:
            raise MarketPriceError("NO_NEXT_TRADING_DAY")
        used = later[0]
    else:
        raise MarketPriceError("TARGET_DATE_NOT_TRADING_DAY")
    return {
        "schema": SCHEMA,
        "status": "PASS__RAW_CLOSE_SELECTED",
        "requested_date": target.isoformat(),
        "used_date": used.isoformat(),
        "used_next_trading_day": used != target,
        "close": mapping[used],
        "raw_close_not_adjusted": True,
        "source_authentication_required": True,
        "model_dependency_count": 0,
        "external_cognition_dependency_count": 0,
        "terminal_authority": False,
    }


def calendar_offset_close(
    rows: Sequence[Mapping[str, Any]],
    announcement_date: str,
    calendar_days: int,
) -> dict[str, Any]:
    if (
        not isinstance(calendar_days, int)
        or isinstance(calendar_days, bool)
        or calendar_days < 0
    ):
        raise MarketPriceError("CALENDAR_DAYS_INVALID")
    target = _date(announcement_date) + timedelta(days=calendar_days)
    return close_on_date(
        rows,
        target.isoformat(),
        next_trading_day_if_missing=True,
    )


def return_percent(start_close: Any, end_close: Any) -> Decimal:
    start = _decimal(start_close)
    end = _decimal(end_close)
    return (end / start - Decimal(1)) * Decimal(100)


def period_return(
    rows: Sequence[Mapping[str, Any]],
    start_date: str,
    end_date: str,
    *,
    next_trading_day_if_missing: bool = False,
) -> dict[str, Any]:
    start = close_on_date(
        rows,
        start_date,
        next_trading_day_if_missing=next_trading_day_if_missing,
    )
    end = close_on_date(
        rows,
        end_date,
        next_trading_day_if_missing=next_trading_day_if_missing,
    )
    return {
        "schema": SCHEMA,
        "status": "PASS__RAW_CLOSE_PERIOD_RETURN",
        "start": start,
        "end": end,
        "return_percent": return_percent(start["close"], end["close"]),
        "raw_close_not_adjusted": True,
        "source_authentication_required": True,
        "model_dependency_count": 0,
        "external_cognition_dependency_count": 0,
        "terminal_authority": False,
    }


__all__ = [
    "MarketPriceError",
    "SCHEMA",
    "calendar_offset_close",
    "close_on_date",
    "normalize_daily_rows",
    "period_return",
    "return_percent",
]
