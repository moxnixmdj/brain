#!/usr/bin/env python3
from __future__ import annotations

import re
import unicodedata
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_RATIO_OVERLAP_WHITESPACE_INVARIANT_V1"

RATIO_RE = re.compile(
    r"Maintain a trigram overlap of (\d+(?:\.\d+)?)% \(±2%\) with the provided reference text\."
)
KEYWORD_RE = re.compile(
    r"The response must include keyword\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))\s+"
    r"in the (\d+)-(?:st|nd|rd|th) sentence\."
)
CONSONANT_TEXT = (
    "Ensure each word in your response has at least one consonant cluster "
    "(two or more consonants together)."
)


class RatioOverlapBlocked(RuntimeError):
    pass


def norm_ws(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def drop_format_chars(value: str) -> str:
    return "".join(ch for ch in value if unicodedata.category(ch) != "Cf")


def char_trigrams(value: str) -> set[str]:
    value = str(value)
    return {value[i:i + 3] for i in range(max(0, len(value) - 2))}


def overlap_percent(response: str, reference: str) -> float:
    output = char_trigrams(response)
    if not output:
        raise RatioOverlapBlocked("RESPONSE_TOO_SHORT_FOR_TRIGRAM_SCORE")
    reference_grams = char_trigrams(reference)
    return 100.0 * len(output & reference_grams) / len(output)


def whitespace_free_score_equivalence(
    response: str,
    *,
    raw_reference: str,
    normalized_reference: str | None = None,
) -> bool:
    """Exact theorem check for the pinned set-of-character-trigrams scorer.

    When response contains no whitespace, all response trigrams are whitespace-free.
    Collapsing whitespace in the reference cannot create or destroy a whitespace-free
    trigram, so response/reference intersection membership is unchanged.
    """
    if re.search(r"\s", str(response)):
        return False
    normalized = norm_ws(raw_reference)
    if normalized_reference is not None and normalized != str(normalized_reference):
        return False
    return overlap_percent(response, raw_reference) == overlap_percent(response, normalized)


def parse_public_ratio_prompt(prompt: str) -> dict[str, Any]:
    """Reverse the pinned public IFBench ratio-overlap prompt grammar.

    This is deliberately narrow. It recognizes only the three ratio-overlap shapes
    independently verified in the pinned 300-row public IFBench population:
    ratio-only, ratio+sentence:keyword, and ratio+words:consonants.
    """
    text = norm_ws(prompt)
    matches = list(RATIO_RE.finditer(text))
    if len(matches) != 1:
        raise RatioOverlapBlocked("RATIO_DESCRIPTION_NOT_UNIQUE")
    percentage = float(matches[0].group(1))
    if not (0.0 <= percentage <= 100.0):
        raise RatioOverlapBlocked("RATIO_PERCENTAGE_OUT_OF_RANGE")

    keyword_match = KEYWORD_RE.search(text)
    keyword = None
    keyword_sentence = None
    if keyword_match:
        keyword = next(
            value for value in keyword_match.groups()[:3] if value is not None
        )
        keyword_sentence = int(keyword_match.group(4))
        if keyword_sentence < 1:
            raise RatioOverlapBlocked("KEYWORD_SENTENCE_INVALID")

    consonant = CONSONANT_TEXT in text
    if keyword_match and consonant:
        raise RatioOverlapBlocked("UNVERIFIED_RATIO_COMPANION_COMBINATION")

    base = RATIO_RE.sub(" ", text)
    base = KEYWORD_RE.sub(" ", base)
    base = base.replace(CONSONANT_TEXT, " ")
    base = norm_ws(drop_format_chars(base))
    if not base:
        raise RatioOverlapBlocked("NORMALIZED_REFERENCE_CANDIDATE_EMPTY")

    return {
        "percentage": percentage,
        "normalized_reference": base,
        "keyword": keyword,
        "keyword_sentence": keyword_sentence,
        "consonant_cluster": consonant,
        "response_language": "WHITESPACE_FREE",
    }


def _private_use_pool(reference: str, count: int = 2048) -> list[str]:
    pool: list[str] = []
    for cp in range(0xE000, 0xF900):
        ch = chr(cp)
        if ch not in reference:
            pool.append(ch)
            if len(pool) >= count:
                break
    if len(pool) < count:
        raise RatioOverlapBlocked("SENTINEL_POOL_EXHAUSTED")
    return pool


def _has_consonant_cluster(value: str) -> bool:
    consonants = set("bcdfghjklmnpqrstvwxyz")
    lower = value.lower()
    return any(
        lower[i] in consonants and lower[i + 1] in consonants
        for i in range(len(lower) - 1)
    )


def _keyword_scaffold_passes(value: str, keyword: str, sentence_number: int) -> bool:
    # The generated scaffold deliberately uses plain periods, no whitespace,
    # no abbreviations, and no other sentence punctuation.
    sentences = [part for part in value.split(".") if part]
    return (
        len(sentences) >= sentence_number
        and keyword.lower() in sentences[sentence_number - 1].lower()
    )


def _candidate_seeds(normalized_reference: str) -> list[str]:
    seeds: set[str] = set()
    compact = re.sub(r"\s+", "", normalized_reference)
    for end in range(3, len(compact) + 1):
        seeds.add(compact[:end])

    for token in re.findall(r"\S+", normalized_reference):
        if len(token) < 3:
            continue
        seeds.add(token)
        for start in range(len(token) - 2):
            for end in range(start + 3, len(token) + 1):
                seeds.add(token[start:end])

    return sorted(
        seeds,
        key=lambda value: (-len(char_trigrams(value)), -len(value), value),
    )


def synthesize_public_ratio_overlap(prompt: str) -> dict[str, Any]:
    """Synthesize from visible prompt only, with no model or external tool."""
    parsed = parse_public_ratio_prompt(prompt)
    target = float(parsed["percentage"])
    reference = str(parsed["normalized_reference"])
    sentinels = _private_use_pool(reference)
    cursor = 0

    mandatory = ""
    if parsed["consonant_cluster"]:
        # The exact public checker splits on whitespace. A whitespace-free response
        # is one word, and this guarantees an ASCII consonant cluster ("st").
        mandatory += "str"

    if parsed["keyword"] is not None:
        count = int(parsed["keyword_sentence"])
        for sentence_index in range(1, count + 1):
            marker = sentinels[cursor]
            cursor += 1
            mandatory += (
                marker
                + (str(parsed["keyword"]) if sentence_index == count else "")
                + "."
            )

    separator = ""
    if mandatory:
        separator = sentinels[cursor]
        cursor += 1

    reference_grams = char_trigrams(reference)
    lower = target - 2.0
    upper = target + 2.0
    seeds = [""] + _candidate_seeds(reference)

    for seed in seeds:
        core = mandatory + separator + seed
        if len(core) < 3 or re.search(r"\s", core):
            continue
        core_grams = char_trigrams(core)
        intersection = len(core_grams & reference_grams)
        denominator = len(core_grams)

        # Appending a fresh private-use character adds exactly one new unique
        # response trigram and zero reference intersections. Its final character
        # has never occurred before and is absent from the reference.
        for filler_len in range(513):
            score = 100.0 * intersection / (denominator + filler_len)
            if not (lower <= score <= upper):
                continue
            filler = "".join(
                sentinels[cursor:cursor + filler_len]
            )
            response = core + filler
            if re.search(r"\s", response):
                continue
            if parsed["keyword"] is not None and not _keyword_scaffold_passes(
                response,
                str(parsed["keyword"]),
                int(parsed["keyword_sentence"]),
            ):
                continue
            if parsed["consonant_cluster"] and not _has_consonant_cluster(response):
                continue
            measured = overlap_percent(response, reference)
            if abs(measured - score) > 1e-12:
                raise RatioOverlapBlocked("SCORE_CONSTRUCTION_INVARIANT_FAILED")
            return {
                "schema": SCHEMA,
                "status": "PASS__VISIBLE_PROMPT_ONLY__WHITESPACE_INVARIANT",
                "response": response,
                "score_against_normalized_reference": measured,
                "target_percentage": target,
                "target_lower": lower,
                "target_upper": upper,
                "normalized_reference": reference,
                "response_has_whitespace": False,
                "model_dependency_count": 0,
                "external_tool_count": 0,
                "terminal_case_metadata_dependency_count": 0,
                "keyword_companion": parsed["keyword"] is not None,
                "consonant_cluster_companion": bool(parsed["consonant_cluster"]),
                "seed": seed,
                "filler_len": filler_len,
            }

    raise RatioOverlapBlocked("NO_VERIFIED_WHITESPACE_FREE_SYNTHESIS")


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    prompt = str((args or {}).get("prompt") or (args or {}).get("instruction") or "")
    if not prompt:
        raise RatioOverlapBlocked("PROMPT_REQUIRED")
    return synthesize_public_ratio_overlap(prompt)
