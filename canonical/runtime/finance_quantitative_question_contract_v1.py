#!/usr/bin/env python3
"""Compile explicit finance-question structure into model-free typed contracts.

This compiler recognizes only operations literally requested or unambiguously
named in the question. It does not infer hidden benchmark categories, source
facts, industry conventions, or qualitative conclusions.

A matched operation means only that the arithmetic/workflow family is known.
semantic_tail_required=True preserves any remaining interpretation obligation.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_FINANCE_QUANTITATIVE_QUESTION_CONTRACT_V1"

_TICKER = re.compile(r"\b(NASDAQ|NYSE)\s*:\s*([A-Z]{1,6})\b", re.I)
_DATE = re.compile(
    r"\b(?:"
    r"(?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12][0-9]|3[01])/(?:[0-9]{2}|[0-9]{4})"
    r"|(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(?:0?[1-9]|[12][0-9]|3[01]),?\s+[0-9]{4}"
    r"|(?:FY\s*)?[12][0-9]{3}"
    r")\b",
    re.I,
)

_OPERATION_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("CAGR", (r"\bCAGR\b", r"compound annual growth rate")),
    ("BASIS_POINT_DELTA", (r"basis points?", r"\bbps\b")),
    ("PERCENT_CHANGE", (r"percent(?:age)? change", r"\bchange in .*?%")),
    ("SHARE_PRICE_RETURN", (r"share price return", r"price performance", r"closing share price")),
    ("RANK_COMPARISON", (r"\brank(?:ing|ings|ed)?\b", r"rank-order")),
    ("AVERAGE", (r"\baverage\b",)),
    ("DAYS_INVENTORY_OUTSTANDING", (r"days inventory outstanding", r"\bDIO\b")),
    ("ADJUSTED_EBITDAR", (r"adjusted EBITDAR",)),
    ("ADJUSTED_EBITDA", (r"adjusted EBITDA",)),
    ("EBITDA_MARGIN", (r"EBITDA margin",)),
    ("PRICE_TO_BOOK", (r"price to book",)),
    ("DEBT_TO_EQUITY", (r"debt to equity",)),
    ("DEBT_TO_TOTAL_CAPITAL", (r"debt to (?:total )?capital",)),
    ("FIXED_CHARGE_COVERAGE", (r"fixed charge coverage ratio", r"\bFCCR\b")),
    ("ENTERPRISE_VALUE", (r"enterprise value", r"\bEV\b")),
    ("EV_TO_EBITDA", (r"EV\s*/\s*(?:Adjusted\s+)?EBITDA", r"transaction value\s*/\s*FY adjusted EBITDA")),
    ("EV_TO_REVENUE", (r"EV\s*/\s*FY[0-9]*\s*Revenue", r"transaction value\s*/\s*FY revenue")),
    ("TRANSACTION_PREMIUM", (r"premium paid", r"offer premium", r"unaffected share price")),
    ("GUIDANCE_MIDPOINT", (r"midpoint of .*guidance", r"guid(?:ed|ance).*midpoint", r"guidance ranges?")),
    ("BEAT_MISS_PERCENT", (r"beat\s*/\s*\(miss\)\s*%", r"beat.*miss")),
    ("INTENSITY", (r"\bintensity\b",)),
    ("RECONCILIATION", (r"\breconcil(?:e|iation|ing)\b", r"GAAP-to-", r"roll-forward")),
    ("ADDBACKS", (r"add[- ]?backs?", r"adding rent obligations")),
    ("NORMALIZATION", (r"\bnormaliz(?:e|ed|ation)\b",)),
    ("MARGIN_CHANGE", (r"change in gross margin", r"gross margin")),
    ("DISCLOSURE_DELTA", (r"how did .* change", r"year-over-year.*(?:decline|change|reduction)", r"\bdifference between\b")),
    ("DCF", (r"discounted cash flow", r"\bDCF\b")),
    ("EXIT_MULTIPLE_TERMINAL_VALUE", (r"exit multiple", r"terminal EBITDA multiple")),
    ("PERPETUAL_GROWTH_TERMINAL_VALUE", (r"perpetual growth", r"terminal growth rate")),
    ("LBO", (r"\bLBO\b", r"take-private", r"sponsor equity")),
    ("MOIC", (r"\bMOIC\b",)),
    ("IRR", (r"\bIRR\b",)),
)

_SOURCE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("SEC_8K", (r"\b8-K\b", r"\b8Ks\b")),
    ("SEC_10Q", (r"\b10-Q\b",)),
    ("ANNUAL_FILING", (r"annual filing", r"annual report", r"FY20[0-9]{2} filing")),
    ("EARNINGS_RELEASE", (r"earnings (?:press )?release",)),
    ("MERGER_ANNOUNCEMENT", (r"merger announcement", r"acquisition announcement", r"transaction terms")),
    ("MARKET_PRICE_HISTORY", (r"share price", r"market prices?", r"closing share prices?", r"price performance")),
    ("SEC_FILINGS_GENERAL", (r"\bfiling\b", r"\bfilings\b", r"disclos(?:ure|ures|ed)")),
)

_SEMANTIC_PATTERNS: tuple[str, ...] = (
    r"\bwhy\b",
    r"\bexplain\b",
    r"\bsuggest\b",
    r"\bimply\b",
    r"\bappears?\b",
    r"\bstrategic\b",
    r"\brisks?\b",
    r"\bcompetitors?\b",
    r"better positioned",
    r"more detailed disclosure",
    r"underlying cause",
    r"market sentiment",
    r"more conservative",
    r"more likely to",
)


def _matches(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.I | re.S) is not None for pattern in patterns)


def compile_question(question: str) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("QUESTION_REQUIRED")
    q = " ".join(question.split())

    tickers: list[str] = []
    for exchange, ticker in _TICKER.findall(q):
        item = f"{exchange.upper()}:{ticker.upper()}"
        if item not in tickers:
            tickers.append(item)

    dates: list[str] = []
    for m in _DATE.finditer(q):
        item = m.group(0)
        if item not in dates:
            dates.append(item)

    operations = [
        op for op, patterns in _OPERATION_PATTERNS
        if _matches(q, patterns)
    ]
    sources = [
        source for source, patterns in _SOURCE_PATTERNS
        if _matches(q, patterns)
    ]
    semantic_tail = any(re.search(p, q, flags=re.I | re.S) for p in _SEMANTIC_PATTERNS)

    # A fully structured candidate means the compiler sees at least one owned
    # quantitative family and no explicit qualitative/consequential language.
    # It is NOT a correctness or source-completeness certificate.
    quantitative_candidate = bool(operations)
    fully_structured_candidate = quantitative_candidate and not semantic_tail

    material = {
        "question_sha256": sha256(question.encode("utf-8")).hexdigest(),
        "tickers": tickers,
        "dates": dates,
        "operations": operations,
        "source_hints": sources,
        "semantic_tail_required": semantic_tail,
        "quantitative_candidate": quantitative_candidate,
        "fully_structured_candidate": fully_structured_candidate,
    }
    contract_sha = sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema": SCHEMA,
        "status": "COMPILED_EXPLICIT_FINANCE_STRUCTURE",
        **material,
        "contract_sha256": contract_sha,
        "model_dependency_count": 0,
        "external_cognition_dependency_count": 0,
        "source_fact_binding_proved": False,
        "semantic_adequacy_proved": False,
        "benchmark_score_credit": 0,
        "terminal_authority": False,
    }


__all__ = ["SCHEMA", "compile_question"]
