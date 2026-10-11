#!/usr/bin/env python3
"""Deterministic pre-submit guard for the current Finance Agent v2 contract.

The guard is intentionally narrow. It does not infer hidden rubrics or award
benchmark credit. It only enforces evidence classes and final-answer structure
that are explicitly required by the public question and the pinned first-party
Vals prompt.

Inputs are the public question, the candidate final_result string, and tool
receipts from the official harness. A failed guard blocks submission so the
agent can continue gathering evidence instead of voluntarily taking a zero.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_FINANCE_AGENT_V2_PRESUBMIT_GUARD_V1"

_CALC_PATTERNS = (
    r"\bcalculate\b",
    r"\bcompute\b",
    r"\bcagr\b",
    r"\bbasis points?\b",
    r"\bbps\b",
    r"\bmargin\b",
    r"\bratio\b",
    r"\bgrowth rate\b",
    r"\breturn\b",
    r"\bdcf\b",
    r"\bnpv\b",
    r"\blbo\b",
    r"\baccretion\b",
    r"\bdilution\b",
    r"\bmultiple\b",
    r"\bpercent(?:age)? change\b",
)

_PRICE_PATTERNS = (
    r"\bshare price\b",
    r"\bstock price\b",
    r"\bprice performance\b",
    r"\btotal shareholder return\b",
    r"\bshare price return\b",
    r"\bclosing share price\b",
    r"\bclosing price\b",
)

_SEC_PATTERNS = (
    r"\b10-k\b",
    r"\b10-q\b",
    r"\b8-k\b",
    r"\bs-4\b",
    r"\bsec filing\b",
    r"\bfiling\b",
    r"\bannual filing\b",
    r"\bquarterly filing\b",
    r"\bform 10-k\b",
    r"\bform 10-q\b",
    r"\bform 8-k\b",
)

_TICKER_RE = re.compile(r"\b(?:NASDAQ|NYSE|AMEX):\s*([A-Z][A-Z0-9.-]{0,9})\b", re.I)


def compile_requirements(question: str) -> dict[str, Any]:
    text = str(question or "").strip()
    if not text:
        raise ValueError("QUESTION_REQUIRED")
    low = text.lower()
    return {
        "requires_calculator": any(re.search(p, low) for p in _CALC_PATTERNS),
        "requires_price_history": any(re.search(p, low) for p in _PRICE_PATTERNS),
        "requires_sec_evidence": any(re.search(p, low) for p in _SEC_PATTERNS),
        "tickers": sorted({m.group(1).upper() for m in _TICKER_RE.finditer(text)}),
    }


def _receipt_ok(row: Mapping[str, Any]) -> bool:
    status = str(row.get("status") or "").strip().lower()
    if status in {"ok", "success", "succeeded", "complete", "completed"}:
        return True
    if row.get("ok") is True or row.get("success") is True:
        return True
    if row.get("error") not in (None, "", False):
        return False
    # Official tool traces may not normalize a status field. A non-empty result
    # with no error is enough to count as an observed successful tool result.
    return row.get("result") not in (None, "")


def _tool_rows(receipts: Sequence[Mapping[str, Any]], name: str) -> list[Mapping[str, Any]]:
    return [
        row for row in receipts
        if isinstance(row, Mapping)
        and str(row.get("tool_name") or row.get("name") or "") == name
    ]


def _has_success(receipts: Sequence[Mapping[str, Any]], name: str) -> bool:
    return any(_receipt_ok(row) for row in _tool_rows(receipts, name))


def _has_failure(receipts: Sequence[Mapping[str, Any]], name: str) -> bool:
    rows = _tool_rows(receipts, name)
    return bool(rows) and any(not _receipt_ok(row) for row in rows)


def _extract_sources(final_result: str) -> list[dict[str, str]]:
    text = str(final_result or "").strip()
    marker = text.rfind('"sources"')
    if marker < 0:
        return []

    start = text.rfind("{", 0, marker + 1)
    if start < 0:
        return []

    # The prompt requires the sources dictionary at the end of the answer.
    # Accept prose before it, but nothing except whitespace after it.
    suffix = text[start:].strip()
    try:
        obj = json.loads(suffix)
    except Exception:
        return []
    if not isinstance(obj, Mapping):
        return []
    raw = obj.get("sources")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            return []
        url = str(item.get("url") or "").strip()
        name = str(item.get("name") or "").strip()
        if not url.startswith(("https://", "http://")) or not name:
            return []
        out.append({"url": url, "name": name})
    return out


def evaluate(
    *,
    question: str,
    final_result: str,
    tool_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(tool_receipts, Sequence) or isinstance(tool_receipts, (str, bytes)):
        raise ValueError("TOOL_RECEIPTS_MUST_BE_SEQUENCE")

    req = compile_requirements(question)
    errors: list[str] = []

    if not str(final_result or "").strip():
        errors.append("FINAL_RESULT_EMPTY")

    sources = _extract_sources(final_result)
    if not sources:
        errors.append("FINAL_SOURCES_DICTIONARY_MISSING_OR_INVALID")

    if req["requires_calculator"] and not _has_success(tool_receipts, "calculator"):
        errors.append("CALCULATION_REQUEST_WITHOUT_SUCCESSFUL_CALCULATOR_RECEIPT")

    if req["requires_price_history"]:
        direct = _has_success(tool_receipts, "price_history")
        fallback = (
            _has_failure(tool_receipts, "price_history")
            and _has_success(tool_receipts, "web_search")
        )
        if not (direct or fallback):
            errors.append("HISTORICAL_PRICE_REQUEST_WITHOUT_PRICE_HISTORY_OR_RECORDED_FALLBACK")

    if req["requires_sec_evidence"]:
        sec_search = _has_success(tool_receipts, "edgar_search")
        sec_page = any(
            _receipt_ok(row)
            and "sec.gov" in json.dumps(row, sort_keys=True, default=str).lower()
            for row in _tool_rows(tool_receipts, "parse_html_page")
        )
        if not (sec_search or sec_page):
            errors.append("FILING_REQUEST_WITHOUT_SEC_EVIDENCE_RECEIPT")

    passed = not errors
    return {
        "schema": SCHEMA,
        "status": "PASS__SUBMIT_ALLOWED" if passed else "BLOCK__CONTINUE_WORK",
        "pass": passed,
        "errors": errors,
        "requirements": req,
        "source_count": len(sources),
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
