from decimal import Decimal as D

import pytest

from canonical.runtime.finance_market_price_series_v1 import (
    MarketPriceError,
    calendar_offset_close,
    close_on_date,
    period_return,
)


ROWS = [
    {"date": "2025-07-28", "close": "100"},
    {"date": "2025-07-29", "close": "97.21"},
    {"date": "2025-07-30", "close": "98"},
    {"date": "2025-08-11", "close": "100.80"},
    {"date": "2025-08-27", "close": "102.20"},
]


def test_exact_trading_day_uses_raw_close():
    out = close_on_date(ROWS, "2025-07-29")
    assert out["close"] == D("97.21")
    assert out["used_next_trading_day"] is False
    assert out["raw_close_not_adjusted"] is True


def test_nontrading_calendar_offset_uses_next_available_trading_day():
    rows = [
        {"date": "2025-07-18", "close": "100"},
        {"date": "2025-07-21", "close": "98"},
    ]
    # Saturday +1 day would be Sunday; next trading day is Monday.
    out = calendar_offset_close(rows, "2025-07-19", 1)
    assert out["requested_date"] == "2025-07-20"
    assert out["used_date"] == "2025-07-21"
    assert out["used_next_trading_day"] is True


def test_period_return_is_raw_close_percent_change():
    out = period_return(ROWS, "2025-07-28", "2025-07-29")
    assert out["return_percent"] == D("-2.7900")


def test_missing_exact_date_fails_without_explicit_next_day_rule():
    with pytest.raises(MarketPriceError, match="TARGET_DATE_NOT_TRADING_DAY"):
        close_on_date(ROWS, "2025-07-31")


def test_duplicate_trading_dates_fail_closed():
    bad = [ROWS[0], {"date": "2025-07-28", "close": "101"}]
    with pytest.raises(MarketPriceError, match="DUPLICATE_TRADING_DATE"):
        close_on_date(bad, "2025-07-28")


def test_adjusted_close_is_ignored_even_if_present():
    rows = [{"date": "2025-01-02", "close": "10", "adjClose": "5"}]
    out = close_on_date(rows, "2025-01-02")
    assert out["close"] == D("10")
