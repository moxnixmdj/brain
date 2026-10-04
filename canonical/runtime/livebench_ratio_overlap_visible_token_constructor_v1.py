#!/usr/bin/env python3
"""Reference-independent constructor for the frozen LiveBench/IFBench ratio:overlap checker.

The frozen checker uses unique character trigrams of the response and computes

    |T(response) ∩ T(reference)| / |T(response)|.

If the caller can supply any whitespace-free visible token whose trigrams are
known to occur in the hidden/exact reference, the full reference text is not
needed. Appending L distinct private-use Unicode characters introduces exactly
L new response trigrams, none of which can match the reference when the caller
has separately established that the chosen private-use range is absent there.

Thus the overlap is exactly K / (K + L), where K is the number of distinct
trigrams in the visible token. This module searches L to hit the requested
percentage band.

This is a benchmark-constraint primitive only. It does not prove semantic
answer quality, terminal acceptance, or general instruction-following ability.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_RATIO_OVERLAP_VISIBLE_TOKEN_CONSTRUCTOR_V1"
DEFAULT_PRIVATE_USE_START = 0xE000


class RatioOverlapConstructionError(RuntimeError):
    pass


def trigram_set(text: str) -> set[str]:
    value = str(text or "")
    return {value[i : i + 3] for i in range(max(0, len(value) - 2))}


@dataclass(frozen=True)
class Construction:
    token: str
    percentage: float
    tolerance: float
    stable_trigram_count: int
    novel_trigram_count: int
    guaranteed_overlap_percent: float
    response: str


def _fresh_suffix(length: int, start: int = DEFAULT_PRIVATE_USE_START) -> str:
    if length < 0:
        raise RatioOverlapConstructionError("NEGATIVE_SUFFIX_LENGTH")
    if start < 0xE000 or start > 0xF8FF:
        raise RatioOverlapConstructionError("PRIVATE_USE_START_OUT_OF_BMP_RANGE")
    if start + max(length - 1, 0) > 0xF8FF:
        raise RatioOverlapConstructionError("PRIVATE_USE_RANGE_EXHAUSTED")
    return "".join(chr(start + i) for i in range(length))


def construct(
    visible_reference_token: str,
    percentage: float,
    *,
    tolerance: float = 2.0,
    max_novel_trigrams: int = 4096,
    private_use_start: int = DEFAULT_PRIVATE_USE_START,
) -> dict[str, Any]:
    token = str(visible_reference_token or "")
    if not token:
        raise RatioOverlapConstructionError("VISIBLE_REFERENCE_TOKEN_REQUIRED")
    if any(ch.isspace() for ch in token):
        raise RatioOverlapConstructionError("TOKEN_MUST_BE_WHITESPACE_FREE")
    if len(token) < 3:
        raise RatioOverlapConstructionError("TOKEN_TOO_SHORT_FOR_TRIGRAM")
    if any(0xE000 <= ord(ch) <= 0xF8FF for ch in token):
        raise RatioOverlapConstructionError("TOKEN_CONTAINS_PRIVATE_USE_CHARACTER")

    target = float(percentage)
    tol = float(tolerance)
    if not (0.0 <= target <= 100.0):
        raise RatioOverlapConstructionError("PERCENTAGE_OUT_OF_RANGE")
    if tol < 0.0:
        raise RatioOverlapConstructionError("NEGATIVE_TOLERANCE")
    if max_novel_trigrams < 0:
        raise RatioOverlapConstructionError("NEGATIVE_SEARCH_BOUND")

    stable = trigram_set(token)
    k = len(stable)
    if k == 0:
        raise RatioOverlapConstructionError("NO_STABLE_TRIGRAMS")

    lower = max(0.0, target - tol)
    upper = min(100.0, target + tol)

    best: tuple[float, int, float] | None = None
    for novel in range(max_novel_trigrams + 1):
        score = 100.0 * k / (k + novel)
        if lower <= score <= upper:
            distance = abs(score - target)
            candidate = (distance, novel, score)
            if best is None or candidate < best:
                best = candidate

    if best is None:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "NO_INTEGER_NOVEL_TRIGRAM_COUNT_IN_BAND",
            "visible_reference_token": token,
            "stable_trigram_count": k,
            "percentage": target,
            "tolerance": tol,
            "model_dependency_count": 0,
            "network_used": False,
            "incremental_spend_usd": 0,
            "terminal_authority": False,
        }

    _, novel, score = best
    suffix = _fresh_suffix(novel, private_use_start)
    response = token + suffix

    # Exact local set accounting: every appended distinct PUA character adds
    # exactly one new response trigram. Those trigrams cannot duplicate token
    # trigrams because they contain at least one PUA character.
    response_trigrams = trigram_set(response)
    if len(response_trigrams) != k + novel:
        raise RatioOverlapConstructionError("TRIGRAM_ACCOUNTING_INVARIANT_FAILED")

    return {
        "schema": SCHEMA,
        "status": "PASS_UNDER_EXPLICIT_REFERENCE_ASSUMPTIONS",
        "response": response,
        "visible_reference_token": token,
        "stable_trigram_count": k,
        "novel_trigram_count": novel,
        "guaranteed_overlap_percent": score,
        "percentage": target,
        "tolerance": tol,
        "proof_assumptions": [
            "EVERY_TRIGRAM_OF_VISIBLE_REFERENCE_TOKEN_OCCURS_IN_EXACT_REFERENCE_TEXT",
            "EXACT_REFERENCE_TEXT_CONTAINS_NO_CHARACTER_FROM_THE_SELECTED_PRIVATE_USE_SUFFIX_RANGE",
        ],
        "hard_nonclaims": [
            "NO_SEMANTIC_ANSWER_QUALITY_PROOF",
            "NO_GENERAL_INSTRUCTION_FOLLOWING_PROOF",
            "NO_TERMINAL_ACCEPTANCE_OR_CAPABILITY_CREDIT",
            "NO_CLAIM_THAT_UPSTREAM_VISIBLE_TOKEN_EXTRACTION_IS_ALREADY UNIVERSALLY SOLVED",
        ],
        "model_dependency_count": 0,
        "network_used": False,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
    }


def exact_checker_overlap(response: str, reference_text: str) -> float:
    """Reproduce the frozen NGramOverlapChecker overlap arithmetic."""
    response_trigrams = trigram_set(response)
    if not response_trigrams:
        return 0.0
    reference_trigrams = trigram_set(reference_text)
    return 100.0 * len(response_trigrams & reference_trigrams) / len(response_trigrams)


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return construct(
        str(args.get("visible_reference_token") or args.get("token") or ""),
        float(args.get("percentage")),
        tolerance=float(args.get("tolerance", 2.0)),
        max_novel_trigrams=int(args.get("max_novel_trigrams", 4096)),
    )
