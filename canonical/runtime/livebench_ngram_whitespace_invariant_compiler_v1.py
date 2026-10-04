from __future__ import annotations

import re
from typing import Iterable

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_NGRAM_WHITESPACE_INVARIANT_COMPILER_V1"
TOLERANCE_PERCENT = 2.0

_RATIO_DESC_RE = re.compile(
    r"Maintain a trigram overlap of (?P<percentage>\d+(?:\.\d+)?)% \(±2%\) "
    r"with the provided reference text\."
)
_KEYWORD_DESC_RE = re.compile(
    r'The response must include keyword .*? in the \d+-(?:st|nd|rd|th) sentence\.'
)
_CONSONANT_DESC = (
    "Ensure each word in your response has at least one consonant cluster "
    "(two or more consonants together)."
)
_BOUNDARY_IGNORABLE_RE = re.compile(
    r"^[\s\u200B\u200C\u200D\u2060\uFEFF]+|"
    r"[\s\u200B\u200C\u200D\u2060\uFEFF]+$"
)


class NGramCompilerError(ValueError):
    pass


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _trim_boundary_ignorables(value: str) -> str:
    return _BOUNDARY_IGNORABLE_RE.sub("", str(value))


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


def recover_pinned_public_ratio_reference(prompt: str) -> dict:
    """Recover the normalized ratio:overlap reference from the pinned public family.

    Scope is deliberately narrow: the exact pinned public IFBench population
    used for proof development. The observed ratio:overlap companion grammar in
    that population is singleton, sentence:keyword, or words:consonants.

    This is not a frozen-terminal equivalence claim. Callers must keep it
    fail-closed unless a separate binding proves the target population obeys
    this grammar envelope.
    """
    s = normalize_ws(prompt)
    matches = list(_RATIO_DESC_RE.finditer(s))
    if len(matches) != 1:
        raise NGramCompilerError("RATIO_DESCRIPTION_COUNT_NOT_ONE")
    percentage = float(matches[0].group("percentage"))

    s = _RATIO_DESC_RE.sub(" ", s, count=1)
    s = s.replace(_CONSONANT_DESC, " ")
    s = _KEYWORD_DESC_RE.sub(" ", s)
    s = _trim_boundary_ignorables(normalize_ws(s))
    s = normalize_ws(s)

    if len(s) < 3:
        raise NGramCompilerError("RECOVERED_REFERENCE_TOO_SHORT")
    if _RATIO_DESC_RE.search(s):
        raise NGramCompilerError("RATIO_DESCRIPTION_REMAINS_AFTER_SEGMENTATION")

    return {
        "schema": SCHEMA,
        "normalized_reference": s,
        "percentage": percentage,
        "scope": "PINNED_PUBLIC_IFBENCH_RATIO_OVERLAP_GRAMMAR_V1",
        "exact_raw_reference_required": False,
    }


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


def construct_from_pinned_public_prompt(prompt: str) -> dict:
    recovered = recover_pinned_public_ratio_reference(prompt)
    witness = construct(recovered["normalized_reference"], recovered["percentage"])
    witness["reference_recovery_scope"] = recovered["scope"]
    witness["normalized_reference_recovered_from_visible_prompt"] = True
    return witness
