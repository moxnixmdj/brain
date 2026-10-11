#!/usr/bin/env python3
"""Pure ticker -> CIK resolution over authenticated SEC registry JSON.

Transport and source authentication are intentionally outside this module and
must be supplied by an existing verified observation route.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FINANCE_SEC_TICKER_CIK_FROM_REGISTRY_V1"
SEC_REGISTRY_URL = "https://www.sec.gov/files/company_tickers.json"
_TICKER_RE = re.compile(r"^[A-Z0-9.\-]{1,12}$")


class SecTickerIdentityError(ValueError):
    pass


def normalize_ticker(value: Any) -> str:
    ticker = str(value or "").strip().upper()
    if not _TICKER_RE.fullmatch(ticker):
        raise SecTickerIdentityError("TICKER_INVALID")
    return ticker


def resolve_registry(payload: Any, ticker: str) -> dict[str, Any]:
    ticker = normalize_ticker(ticker)
    if not isinstance(payload, Mapping):
        raise SecTickerIdentityError("SEC_TICKER_PAYLOAD_NOT_OBJECT")

    matches: list[dict[str, Any]] = []
    for row_key, raw in payload.items():
        if not isinstance(raw, Mapping):
            raise SecTickerIdentityError("SEC_TICKER_ROW_NOT_OBJECT:" + str(row_key))
        raw_ticker = normalize_ticker(raw.get("ticker"))
        if raw_ticker != ticker:
            continue
        cik = raw.get("cik_str")
        if isinstance(cik, bool):
            raise SecTickerIdentityError("CIK_INVALID")
        try:
            cik_int = int(cik)
        except Exception as exc:
            raise SecTickerIdentityError("CIK_INVALID") from exc
        if cik_int <= 0 or cik_int > 9_999_999_999:
            raise SecTickerIdentityError("CIK_INVALID")
        title = raw.get("title")
        if not isinstance(title, str) or not title.strip():
            raise SecTickerIdentityError("ISSUER_TITLE_REQUIRED")
        matches.append({
            "ticker": ticker,
            "cik": cik_int,
            "cik10": f"{cik_int:010d}",
            "title": " ".join(title.split()),
            "sec_registry_row_key": str(row_key),
        })

    if not matches:
        raise SecTickerIdentityError("TICKER_NOT_FOUND")
    unique = {(x["cik10"], x["title"]) for x in matches}
    if len(unique) != 1:
        raise SecTickerIdentityError("TICKER_IDENTITY_AMBIGUOUS")

    return {
        "schema": SCHEMA,
        "status": "PASS__UNIQUE_SEC_REGISTRY_TICKER_IDENTITY",
        "pass": True,
        **matches[0],
        "expected_source_url": SEC_REGISTRY_URL,
        "source_authentication_required": True,
        "model_dependency_count": 0,
        "external_cognition_dependency_count": 0,
        "fuzzy_entity_matching_used": False,
        "terminal_authority": False,
    }


__all__ = [
    "SCHEMA",
    "SEC_REGISTRY_URL",
    "SecTickerIdentityError",
    "normalize_ticker",
    "resolve_registry",
]
