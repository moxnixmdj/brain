from __future__ import annotations

import re
from typing import Iterable

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_NGRAM_WHITESPACE_INVARIANT_COMPILER_V1"
TOLERANCE_PERCENT = 2.0


class NGramCompilerError(ValueError):
    pass


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def char_trigrams(value: str) -> set[str]:
    value = str(value)
    return {value[i:i+3] for i in range(max(0, len(value) - 2))}


def overlap_percent(response: str, reference: str) -> float:
    grams = char_trigrams(response)
    if not grams:
        raise NGramCompilerError("RESPONSE_TOO_SHORT_FOR_TRIGRAMS")
    ref = char_trigrams(reference)
    return 100.0 * len(grams & ref) / len(grams)


def whitespace_invariant_for_reference(response: str, raw_reference: str) -> bool:
    """Executable theorem check for a concrete witness.

    If response contains no whitespace, normalization of whitespace in the
    reference cannot change membership of any response trigram.
    """
    if any(ch.isspace() for ch in response):
        return False
    return char_trigrams(response).intersection(char_trigrams(raw_reference)) == (
        char_trigrams(response).intersection(char_trigrams(normalize_ws(raw_reference)))
    )


def _novel_chars(reference: str, count: int) -> str:
    if count < 0:
        raise NGramCompilerError("NEGATIVE_FILLER_COUNT")
    out: list[str] = []
    for cp in range(0xE000, 0xF8FF + 1):
        ch = chr(cp)
        if ch not in reference:
            out.append(ch)
            if len(out) == count:
                return "".join(out)
    raise NGramCompilerError("INSUFFICIENT_NOVEL_PRIVATE_USE_CHARACTERS")


def _candidate_token_substrings(normalized_reference: str) -> Iterable[str]:
    for token in normalized_reference.split(" "):
        if len(token) < 3:
            continue
        for start in range(0, len(token) - 2):
            for end in range(start + 3, len(token) + 1):
                yield token[start:end]


def construct(
    normalized_reference: str,
    percentage: float,
    *,
    tolerance_percent: float = TOLERANCE_PERCENT,
    max_filler_chars: int = 256,
) -> dict:
    """Construct a whitespace-free response that meets NGramOverlapChecker.

    The caller supplies only the whitespace-normalized reference and the
    visible requested percentage. Exact raw whitespace is deliberately not
    required.

    Fail-closed: if the finite deterministic search cannot find a witness,
    no score claim is made.
    """
    normalized_reference = normalize_ws(normalized_reference)
    if len(normalized_reference) < 3:
        raise NGramCompilerError("NORMALIZED_REFERENCE_TOO_SHORT")
    try:
        percentage = float(percentage)
        tolerance_percent = float(tolerance_percent)
    except Exception as exc:
        raise NGramCompilerError("PERCENTAGE_NOT_NUMERIC") from exc
    if not 0 <= percentage <= 100:
        raise NGramCompilerError("PERCENTAGE_OUT_OF_RANGE")
    if not 0 <= tolerance_percent <= 100:
        raise NGramCompilerError("TOLERANCE_OUT_OF_RANGE")
    if max_filler_chars < 0 or max_filler_chars > 4096:
        raise NGramCompilerError("MAX_FILLER_OUT_OF_RANGE")

    best: dict | None = None
    filler_cache = {0: ""}
    for base in _candidate_token_substrings(normalized_reference):
        for filler_len in range(max_filler_chars + 1):
            if filler_len not in filler_cache:
                filler_cache[filler_len] = _novel_chars(normalized_reference, filler_len)
            response = base + filler_cache[filler_len]
            if any(ch.isspace() for ch in response):
                raise AssertionError("INTERNAL_WHITESPACE_CONSTRUCTION_BUG")
            score = overlap_percent(response, normalized_reference)
            error = abs(score - percentage)
            record = {
                "schema": SCHEMA,
                "response": response,
                "score_against_normalized_reference_percent": score,
                "requested_percent": percentage,
                "absolute_error_percent": error,
                "within_tolerance": error <= tolerance_percent,
                "base": base,
                "filler_len": filler_len,
                "response_len": len(response),
                "whitespace_free": True,
                "exact_raw_reference_required": False,
            }
            key = (0 if record["within_tolerance"] else 1, len(response), error, response)
            if best is None or key < best["_key"]:
                best = dict(record)
                best["_key"] = key

    if best is None or not best["within_tolerance"]:
        raise NGramCompilerError("NO_WHITESPACE_INVARIANT_WITNESS_FOUND")
    best.pop("_key", None)
    return best
