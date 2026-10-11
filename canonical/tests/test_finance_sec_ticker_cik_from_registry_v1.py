import pytest

from canonical.runtime.finance_sec_ticker_cik_from_registry_v1 import (
    SEC_REGISTRY_URL,
    SecTickerIdentityError,
    resolve_registry,
)


def registry():
    return {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
    }


def test_unique_ticker_resolves_exact_cik10():
    out = resolve_registry(registry(), "aapl")
    assert out["ticker"] == "AAPL"
    assert out["cik"] == 320193
    assert out["cik10"] == "0000320193"
    assert out["expected_source_url"] == SEC_REGISTRY_URL
    assert out["fuzzy_entity_matching_used"] is False


def test_missing_ticker_fails_closed():
    with pytest.raises(SecTickerIdentityError, match="TICKER_NOT_FOUND"):
        resolve_registry(registry(), "ZZZZ")


def test_duplicate_conflicting_identity_fails_closed():
    data = registry()
    data["2"] = {"cik_str": 123456, "ticker": "AAPL", "title": "Different Issuer"}
    with pytest.raises(SecTickerIdentityError, match="TICKER_IDENTITY_AMBIGUOUS"):
        resolve_registry(data, "AAPL")


def test_malformed_rows_fail_closed():
    data = registry()
    data["2"] = {"ticker": "BAD"}
    with pytest.raises(SecTickerIdentityError):
        resolve_registry(data, "BAD")


def test_transport_authentication_is_not_self_certified():
    out = resolve_registry(registry(), "MSFT")
    assert out["source_authentication_required"] is True
    assert out["external_cognition_dependency_count"] == 0
    assert out["terminal_authority"] is False
