#!/usr/bin/env python3
"""Deterministic Finance evidence synthesis V1.

Converts Brain-native extracted source rows into a small set of mechanically
provable finance outputs.  V1 intentionally starts with revenue growth/CAGR,
basis-point comparison, and revenue-growth ranking because these require no
industry convention once entity, fiscal years, and revenue values are uniquely
bound.

Ambiguity fails closed.  No model inference, fuzzy semantic completion, hidden
benchmark answer lookup, or source discovery occurs here.
"""
from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping

from canonical.runtime.finance_quantitative_algebra_v1 import (
    FinanceAlgebraError,
    basis_points_between,
    cagr,
    percent_change,
    rank_desc,
)

SCHEMA = "PROJECT_BRAIN_FINANCE_NATIVE_EVIDENCE_SYNTHESIS_V1"
Q2 = Decimal("0.01")
_YEAR = re.compile(r"\b(?:FY\s*)?(20\d{2})\b", re.I)
_FY_YEAR = re.compile(r"\bFY\s*(20\d{2})\b", re.I)
_NUMBER = re.compile(
    r"(?<![A-Za-z0-9])"
    r"(\(\s*\$?\s*\d[\d,]*(?:\.\d+)?\s*\)|[-+]?\$?\s*\d[\d,]*(?:\.\d+)?)"
    r"(?![A-Za-z0-9])"
)
_METRIC_PATTERNS = {
    "REVENUE": re.compile(r"\b(?:revenue|revenues|net sales|total revenues?)\b", re.I),
}


class FinanceEvidenceSynthesisError(ValueError):
    pass


def _decimal(token: str) -> Decimal:
    raw = token.strip().replace("$", "").replace(",", "").replace(" ", "")
    if raw.startswith("(") and raw.endswith(")"):
        raw = "-" + raw[1:-1]
    try:
        value = Decimal(raw)
    except Exception as exc:
        raise FinanceEvidenceSynthesisError("NUMERIC_TOKEN_INVALID") from exc
    if not value.is_finite():
        raise FinanceEvidenceSynthesisError("NUMERIC_TOKEN_NONFINITE")
    return value


def _numbers_without_years(line: str) -> list[Decimal]:
    scrubbed = _YEAR.sub(" ", line)
    out: list[Decimal] = []
    for match in _NUMBER.finditer(scrubbed):
        token = match.group(1)
        # Percentages/multiples are not monetary metric candidates.
        tail = scrubbed[match.end(): match.end() + 2]
        if "%" in tail or re.match(r"\s*[xX]", tail):
            continue
        value = _decimal(token)
        out.append(value)
    return out


def _bind(
    bound: dict[int, Decimal],
    year: int,
    value: Decimal,
) -> None:
    prior = bound.get(year)
    if prior is None:
        bound[year] = value
        return
    if prior != value:
        raise FinanceEvidenceSynthesisError(
            f"CONFLICTING_METRIC_VALUE:{year}:{prior}:{value}"
        )


def extract_metric_series(evidence: str, metric_id: str) -> dict[str, Any]:
    if not isinstance(evidence, str) or not evidence.strip():
        raise FinanceEvidenceSynthesisError("EVIDENCE_REQUIRED")
    pattern = _METRIC_PATTERNS.get(metric_id)
    if pattern is None:
        raise FinanceEvidenceSynthesisError("METRIC_NOT_SUPPORTED:" + metric_id)

    lines = [" ".join(x.split()) for x in evidence.splitlines() if x.strip()]
    bound: dict[int, Decimal] = {}
    receipts: list[dict[str, Any]] = []

    # Explicit same-line binding: one fiscal/calendar year and exactly one
    # non-year monetary number on a metric-bearing row.
    for index, line in enumerate(lines):
        if not pattern.search(line):
            continue
        years = [int(x) for x in _YEAR.findall(line)]
        values = _numbers_without_years(line)
        if len(set(years)) == 1 and len(values) == 1:
            year = years[0]
            _bind(bound, year, values[0])
            receipts.append(
                {
                    "mode": "EXPLICIT_SAME_LINE",
                    "line_index": index,
                    "year": year,
                    "value": str(values[0]),
                }
            )

    # Table binding: a nearby year header followed by one metric row with the
    # exact same number of values.  No partial alignment or guessing.
    for header_index, header in enumerate(lines):
        years = [int(x) for x in _YEAR.findall(header)]
        if len(years) < 2 or len(years) != len(set(years)):
            continue
        for row_index in range(header_index + 1, min(len(lines), header_index + 5)):
            row = lines[row_index]
            if not pattern.search(row):
                continue
            values = _numbers_without_years(row)
            if len(values) != len(years):
                continue
            for year, value in zip(years, values):
                _bind(bound, year, value)
            receipts.append(
                {
                    "mode": "TABLE_HEADER_ROW_EXACT_ARITY",
                    "header_line_index": header_index,
                    "metric_line_index": row_index,
                    "years": years,
                    "values": [str(x) for x in values],
                }
            )
            break

    return {
        "schema": SCHEMA,
        "status": "BOUND" if bound else "NO_UNAMBIGUOUS_BINDING",
        "metric_id": metric_id,
        "series": {str(k): str(v) for k, v in sorted(bound.items())},
        "receipts": receipts,
        "ambiguity_failed_closed": True,
        "model_dependency_count": 0,
        "external_cognition_dependency_count": 0,
        "terminal_authority": False,
    }


def _requested_fiscal_years(question: str) -> list[int]:
    years = [int(x) for x in _FY_YEAR.findall(question)]
    out: list[int] = []
    for year in years:
        if year not in out:
            out.append(year)
    return out


def _display_percent(value: Decimal) -> str:
    q = value.quantize(Q2, rounding=ROUND_HALF_UP)
    if q < 0:
        return f"({abs(q)}%)"
    return f"{q}%"


def synthesize_revenue_growth(
    question: str,
    evidence_by_ticker: Mapping[str, str],
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise FinanceEvidenceSynthesisError("QUESTION_REQUIRED")
    if not isinstance(evidence_by_ticker, Mapping) or not evidence_by_ticker:
        return {
            "schema": SCHEMA,
            "status": "NO_EVIDENCE",
            "results": {},
            "model_dependency_count": 0,
            "external_cognition_dependency_count": 0,
        }

    years = _requested_fiscal_years(question)
    if len(years) < 2:
        return {
            "schema": SCHEMA,
            "status": "FISCAL_YEAR_PAIR_NOT_EXPLICIT",
            "results": {},
            "model_dependency_count": 0,
            "external_cognition_dependency_count": 0,
        }
    start_year, end_year = years[0], years[-1]
    if end_year <= start_year:
        raise FinanceEvidenceSynthesisError("FISCAL_YEAR_ORDER_INVALID")

    wants_cagr = bool(
        re.search(r"(?i)\bCAGR\b|compound annual growth rate", question)
    )
    wants_growth = bool(
        re.search(r"(?i)\brevenue growth\b|growth in revenue|revenue.*growth", question)
    )
    if not wants_cagr and not wants_growth:
        return {
            "schema": SCHEMA,
            "status": "REVENUE_GROWTH_NOT_REQUESTED",
            "results": {},
            "model_dependency_count": 0,
            "external_cognition_dependency_count": 0,
        }

    results: dict[str, dict[str, Any]] = {}
    for ticker, evidence in evidence_by_ticker.items():
        bound = extract_metric_series(str(evidence), "REVENUE")
        series = {
            int(year): Decimal(value)
            for year, value in bound.get("series", {}).items()
        }
        if start_year not in series or end_year not in series:
            continue
        start = series[start_year]
        end = series[end_year]
        try:
            value = (
                cagr(end, start, end_year - start_year)
                if wants_cagr
                else percent_change(end, start)
            )
        except FinanceAlgebraError:
            continue
        results[str(ticker).upper()] = {
            "metric": "REVENUE",
            "method": "CAGR" if wants_cagr else "PERCENT_CHANGE",
            "start_year": start_year,
            "end_year": end_year,
            "start_value": str(start),
            "end_value": str(end),
            "value_percent": str(value),
            "display_percent": _display_percent(value),
            "binding_receipt": bound,
        }

    ranking = (
        rank_desc({ticker: row["value_percent"] for ticker, row in results.items()})
        if results
        else []
    )
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PASS__BOUND_REVENUE_GROWTH" if results else "INSUFFICIENT_BOUND_FACTS",
        "method": "CAGR" if wants_cagr else "PERCENT_CHANGE",
        "results": results,
        "ranking_high_to_low": ranking,
        "all_entities_bound": len(results) == len(evidence_by_ticker),
        "model_dependency_count": 0,
        "external_cognition_dependency_count": 0,
        "benchmark_score_credit": 0,
        "terminal_authority": False,
    }

    if wants_cagr and len(results) == 2 and re.search(r"(?i)basis points?|\bbps\b", question):
        ordered = list(results)
        a, b = ordered[0], ordered[1]
        av = Decimal(results[a]["value_percent"])
        bv = Decimal(results[b]["value_percent"])
        delta = basis_points_between(max(av, bv), min(av, bv))
        higher = a if av > bv else b if bv > av else "EQUAL"
        out["basis_point_comparison"] = {
            "higher": higher,
            "difference_bps": str(delta),
            "display_bps": str(delta.quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
        }
    return out


def format_revenue_growth(result: Mapping[str, Any]) -> str:
    if not str(result.get("status", "")).startswith("PASS__"):
        return ""
    lines: list[str] = []
    method = str(result.get("method") or "growth")
    for ticker, row in result.get("results", {}).items():
        lines.append(
            f"{ticker} revenue {method.lower()} from FY{row['start_year']} to "
            f"FY{row['end_year']}: {row['display_percent']}."
        )
    ranking = result.get("ranking_high_to_low", [])
    if len(ranking) > 1:
        lines.append(
            "Revenue-growth ranking, highest to lowest: "
            + " > ".join(str(x) for x in ranking)
            + "."
        )
    bps = result.get("basis_point_comparison")
    if isinstance(bps, Mapping):
        lines.append(
            f"{bps['higher']} has the higher revenue CAGR by "
            f"{bps['display_bps']} basis points."
        )
    return "\n".join(lines)


__all__ = [
    "FinanceEvidenceSynthesisError",
    "SCHEMA",
    "extract_metric_series",
    "format_revenue_growth",
    "synthesize_revenue_growth",
]
