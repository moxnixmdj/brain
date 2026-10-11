"""Fail-closed deterministic lower-bound scorer for Chartography.

This is NOT a replacement claim for Surge's Gemini judge. It is a sound
under-approximation of the published grading rules: every awarded 1 must be
an unambiguous case that the published rules require to be correct. Ambiguous
or unsupported forms receive 0.

Never use golden answers to generate or tune candidate responses.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
from typing import Optional

_WS = re.compile(r"\s+")
_NUM = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")
_RANGE_MARKER = re.compile(r"(?i)\b(?:acceptable(?:\s+range)?|range)\b")
_RANGE_PAIR = re.compile(
    r"(?i)([-+]?\d[\d,]*(?:\.\d+)?)\s*(?:to|[-–—])\s*([-+]?\d[\d,]*(?:\.\d+)?)"
)
_UNIT = re.compile(
    r"(?i)(%|pp|mph|km/?h|m/s|kpa|mpa|pa|hz|khz|mhz|ghz|°c|°f|\bk\b|mm|cm|km|kg|lb|mw|kw|\bw\b)"
)
_CANNOT = re.compile(
    r"(?i)^(?:it\s+)?(?:cannot|can't)\s+be\s+determined(?:\s+from\s+the\s+chart)?[.!]?$"
)


@dataclass(frozen=True)
class ScoreResult:
    score: int
    reason: str


def _norm_text(s: str) -> str:
    s = str(s).strip().casefold()
    s = s.replace("–", "-").replace("—", "-")
    s = _WS.sub(" ", s)
    return s.strip(" \t\r\n.,;:")


def _dec(token: str) -> Optional[Decimal]:
    try:
        return Decimal(token.replace(",", ""))
    except InvalidOperation:
        return None


def _single_numeric_response(response: str) -> tuple[Optional[Decimal], Optional[str]]:
    """Return a scalar only when the response is substantively just one number + optional unit."""
    text = _norm_text(response)
    nums = list(_NUM.finditer(text))
    if len(nums) != 1:
        return None, None
    m = nums[0]
    value = _dec(m.group(0))
    if value is None:
        return None, None
    remainder = (text[:m.start()] + " " + text[m.end():]).strip()
    # Allow only currency punctuation and one recognized unit around the scalar.
    remainder = remainder.replace("$", " ").strip()
    units = _UNIT.findall(remainder)
    stripped = _UNIT.sub("", remainder)
    stripped = re.sub(r"[()\[\],]", " ", stripped)
    stripped = _WS.sub(" ", stripped).strip()
    if stripped:
        return None, None
    unit = units[0].casefold() if len(units) == 1 else ("" if not units else None)
    if unit is None:
        return None, None
    return value, unit


def _range_from_golden(golden: str) -> tuple[Optional[Decimal], Optional[Decimal], Optional[str]]:
    """Parse only explicitly marked acceptable/range intervals.

    Refuses generic hyphenated text so a date, axis label, or explanation
    cannot accidentally become a scoring interval.
    """
    text = _norm_text(golden)
    if not _RANGE_MARKER.search(text):
        return None, None, None
    m = _RANGE_PAIR.search(text)
    if not m:
        return None, None, None
    lo, hi = _dec(m.group(1)), _dec(m.group(2))
    if lo is None or hi is None:
        return None, None, None
    if lo > hi:
        lo, hi = hi, lo
    # Bind unit conservatively from the local tail after the interval.
    tail = text[m.end():m.end()+24]
    units = _UNIT.findall(tail)
    unit = units[0].casefold() if units else ""
    return lo, hi, unit


def score_lower_bound(golden_answer: str, response_text: str) -> ScoreResult:
    """Award 1 only when correctness follows directly from published rules."""
    g = _norm_text(golden_answer)
    r = _norm_text(response_text)
    if not g or not r:
        return ScoreResult(0, "EMPTY_OR_MISSING")

    # Exact substantive answer match is always accepted by the published rules.
    if r == g:
        return ScoreResult(1, "EXACT_NORMALIZED_GOLDEN_MATCH")

    # Exact 'cannot be determined' semantics. Do not infer synonyms.
    if _CANNOT.fullmatch(g) and _CANNOT.fullmatch(r):
        return ScoreResult(1, "EXACT_CANNOT_DETERMINE")

    # Explicit expert acceptable numerical range.
    lo, hi, g_unit = _range_from_golden(golden_answer)
    if lo is not None:
        val, r_unit = _single_numeric_response(response_text)
        if val is None:
            return ScoreResult(0, "RANGE_RESPONSE_NOT_SINGLE_SCALAR")
        # If golden binds a recognized unit, response must bind the same unit.
        if g_unit and r_unit != g_unit:
            return ScoreResult(0, "UNIT_MISMATCH_OR_MISSING")
        if lo <= val <= hi:
            return ScoreResult(1, "EXPLICIT_ACCEPTABLE_RANGE_CONTAINMENT")
        return ScoreResult(0, "OUTSIDE_EXPLICIT_RANGE")

    # Deliberately no fuzzy categorical matching, ranking inference, unit
    # conversion, or multipart decomposition: those remain 0 unless exact.
    return ScoreResult(0, "UNSUPPORTED_OR_AMBIGUOUS_FAIL_CLOSED")
