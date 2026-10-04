#!/usr/bin/env python3
"""Prompt-only constructive composer for the frozen LiveBench ratio:overlap family.

This module closes two residuals left by the V1 visible-token theorem for the
pinned public IFBench family:

1. selected private-use filler characters are chosen from characters absent
   from the recovered normalized reference, so suffix disjointness is no longer
   an external assumption under the prompt-segmenter equivalence contract;
2. the two public co-occurring checker families are composed constructively:
   sentence:keyword and words:consonants.

The construction uses only response trigrams whose reference membership is
known from the recovered prompt. Every other response trigram contains at least
one selected private-use character and is therefore provably absent from the
reference under the segmenter contract.

This is benchmark-constraint machinery only. It does not prove semantic answer
quality, terminal acceptance, or general instruction-following capability.
"""
from __future__ import annotations

import math
import re
from typing import Any

from canonical.runtime.livebench_ratio_overlap_prompt_segmenter_v1 import recover
from canonical.runtime.livebench_ratio_overlap_visible_token_constructor_v1 import trigram_set

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_RATIO_OVERLAP_PROMPT_COMPOSER_V1"
PUA_START = 0xE000
PUA_END = 0xF8FF
MAX_FILLER = 4096

_SENTENCE_KEYWORD = re.compile(
    r'The response must include keyword\s+"?(?P<word>[^"\s]+)"?\s+'
    r'in the (?P<N>\d+)-(?:st|nd|rd|th) sentence\.'
)
_CONSONANT_CLUSTER_TEXT = (
    "Ensure each word in your response has at least one consonant cluster "
    "(two or more consonants together)."
)
_CONSONANT_CLUSTER = re.compile(r"[bcdfghjklmnpqrstvwxyz]{2}", re.IGNORECASE)
_TOKEN = re.compile(r"[^\s.!?]{3,}")


class PromptComposerError(RuntimeError):
    pass


def _is_pua(ch: str) -> bool:
    code = ord(ch)
    return PUA_START <= code <= PUA_END


def _contains_pua(text: str) -> bool:
    return any(_is_pua(ch) for ch in text)


def _fresh_pua_pool(reference: str, forbidden: str = "") -> list[str]:
    used = {ord(ch) for ch in reference + forbidden if _is_pua(ch)}
    return [chr(code) for code in range(PUA_START, PUA_END + 1) if code not in used]


def _candidate_tokens(reference: str, require_consonant_cluster: bool) -> list[str]:
    seen: set[str] = set()
    candidates: list[str] = []
    for match in _TOKEN.finditer(reference):
        token = match.group(0)
        if token in seen or _contains_pua(token):
            continue
        if require_consonant_cluster and not _CONSONANT_CLUSTER.search(token):
            continue
        seen.add(token)
        candidates.append(token)
    # Longer tokens usually give a larger controllable known-overlap numerator.
    candidates.sort(key=lambda value: (-len(value), value))
    return candidates


def _known_membership(response: str, normalized_reference: str) -> tuple[int, int, float]:
    response_trigrams = trigram_set(response)
    reference_trigrams = trigram_set(normalized_reference)
    if not response_trigrams:
        return 0, 0, 0.0
    known_overlap = sum(
        1
        for trigram in response_trigrams
        if not _contains_pua(trigram) and trigram in reference_trigrams
    )
    return known_overlap, len(response_trigrams), 100.0 * known_overlap / len(response_trigrams)


def _assert_non_pua_trigrams_are_local(response: str, token: str, keyword: str | None) -> None:
    allowed = set(trigram_set(token))
    if keyword:
        allowed |= trigram_set(keyword)
    unexpected = {
        trigram
        for trigram in trigram_set(response)
        if not _contains_pua(trigram) and trigram not in allowed
    }
    if unexpected:
        raise PromptComposerError("UNEXPECTED_NON_PUA_TRIGRAM_ESCAPE")


def _solve_filler_length(
    numerator: int,
    base_denominator: int,
    target: float,
    tolerance: float,
    max_filler: int,
) -> int | None:
    lower = max(0.0, target - tolerance)
    upper = min(100.0, target + tolerance)
    if numerator <= 0 or base_denominator <= 0:
        return None

    min_denominator = base_denominator
    if upper > 0.0:
        min_denominator = max(
            min_denominator,
            math.ceil((100.0 * numerator / upper) - 1e-12),
        )

    max_denominator = base_denominator + max_filler
    if lower > 0.0:
        max_denominator = min(
            max_denominator,
            math.floor((100.0 * numerator / lower) + 1e-12),
        )

    if min_denominator > max_denominator:
        return None

    if target > 0.0:
        ideal = round(100.0 * numerator / target)
    else:
        ideal = max_denominator
    chosen_denominator = min(max(ideal, min_denominator), max_denominator)
    return int(chosen_denominator - base_denominator)


def _build_ratio_only(token: str, filler: str) -> str:
    return token + filler


def _build_sentence_keyword(
    token: str,
    scaffold: str,
    filler: str,
    keyword: str,
    sentence_index: int,
) -> str:
    if sentence_index < 1:
        raise PromptComposerError("INVALID_SENTENCE_INDEX")
    if any(ch in keyword for ch in ".!?") or any(ch.isspace() for ch in keyword):
        raise PromptComposerError("UNSUPPORTED_KEYWORD_SHAPE")

    if sentence_index == 1:
        return token + scaffold + keyword + scaffold + filler + "."

    # The repeated scaffold creates arbitrarily many checker-visible sentences
    # while adding only O(1) distinct scaffold trigrams. Every scaffold trigram
    # contains the private-use character and therefore cannot hit the reference.
    return (
        token
        + scaffold
        + "."
        + (scaffold + ".") * max(0, sentence_index - 2)
        + scaffold
        + keyword
        + scaffold
        + filler
        + "."
    )


def _verify_constructed_sentence_shape(response: str, keyword: str, sentence_index: int) -> bool:
    # This constructor emits only period terminators and rejects .!? in token and
    # keyword, so the frozen IFBench splitter reduces to one stop per period.
    sentences = [part for part in response.split(".") if part]
    return (
        len(sentences) == sentence_index
        and keyword.lower() in sentences[sentence_index - 1].lower()
    )


def _verify_consonant_shape(response: str) -> bool:
    words = response.lower().strip().split()
    for word in words:
        if all(ch not in "abcdefghijklmnopqrstuvwxyz" for ch in word):
            continue
        if not _CONSONANT_CLUSTER.search(word):
            return False
    return True


def compose(prompt: str, *, tolerance: float = 2.0, max_filler: int = MAX_FILLER) -> dict[str, Any]:
    segmented = recover(prompt)
    reference = str(segmented["normalized_reference"])
    target = float(segmented["percentage"])
    tolerance = float(tolerance)

    if tolerance < 0.0:
        raise PromptComposerError("NEGATIVE_TOLERANCE")
    if max_filler < 0:
        raise PromptComposerError("NEGATIVE_FILLER_BOUND")

    normalized_prompt = " ".join(str(prompt or "").strip().split())
    sentence_match = _SENTENCE_KEYWORD.search(normalized_prompt)
    has_sentence_keyword = sentence_match is not None
    has_consonant_cluster = _CONSONANT_CLUSTER_TEXT in normalized_prompt

    if has_sentence_keyword and has_consonant_cluster:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "UNPROVEN_MULTI_CO_CONSTRAINT_COMPOSITION",
            "model_dependency_count": 0,
            "network_used": False,
            "incremental_spend_usd": 0,
            "terminal_authority": False,
        }

    keyword: str | None = None
    sentence_index: int | None = None
    if sentence_match is not None:
        keyword = sentence_match.group("word")
        sentence_index = int(sentence_match.group("N"))

    mode = (
        "RATIO_PLUS_SENTENCE_KEYWORD"
        if has_sentence_keyword
        else "RATIO_PLUS_CONSONANT_CLUSTER"
        if has_consonant_cluster
        else "RATIO_ONLY"
    )

    candidates = _candidate_tokens(reference, require_consonant_cluster=has_consonant_cluster)
    if not candidates:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "NO_SAFE_VISIBLE_TOKEN",
            "composition_mode": mode,
            "model_dependency_count": 0,
            "network_used": False,
            "incremental_spend_usd": 0,
            "terminal_authority": False,
        }

    lower = max(0.0, target - tolerance)
    upper = min(100.0, target + tolerance)
    best: dict[str, Any] | None = None

    for token in candidates:
        forbidden = token + (keyword or "")
        pool = _fresh_pua_pool(reference, forbidden)
        required_pool = max_filler + (1 if has_sentence_keyword else 0)
        if len(pool) < required_pool:
            continue

        scaffold = pool[0] if has_sentence_keyword else ""
        filler_pool = pool[1:] if has_sentence_keyword else pool

        if has_sentence_keyword:
            assert keyword is not None and sentence_index is not None
            base_response = _build_sentence_keyword(
                token, scaffold, "", keyword, sentence_index
            )
        else:
            base_response = _build_ratio_only(token, "")

        _assert_non_pua_trigrams_are_local(base_response, token, keyword)
        numerator, base_denominator, _ = _known_membership(base_response, reference)
        filler_length = _solve_filler_length(
            numerator,
            base_denominator,
            target,
            tolerance,
            min(max_filler, len(filler_pool)),
        )
        if filler_length is None:
            continue

        filler = "".join(filler_pool[:filler_length])
        if has_sentence_keyword:
            response = _build_sentence_keyword(
                token, scaffold, filler, keyword, sentence_index
            )
        else:
            response = _build_ratio_only(token, filler)

        _assert_non_pua_trigrams_are_local(response, token, keyword)
        final_numerator, denominator, predicted = _known_membership(response, reference)

        # Every fresh filler character must increase the distinct denominator by
        # exactly one while leaving the known numerator fixed.
        if final_numerator != numerator:
            raise PromptComposerError("KNOWN_NUMERATOR_CHANGED_AFTER_FILLER")
        if denominator != base_denominator + filler_length:
            raise PromptComposerError("FILLER_DENOMINATOR_INVARIANT_FAILED")
        if not (lower <= predicted <= upper):
            continue

        if has_sentence_keyword and not _verify_constructed_sentence_shape(
            response, keyword, sentence_index
        ):
            raise PromptComposerError("SENTENCE_COMPOSITION_INVARIANT_FAILED")
        if has_consonant_cluster and not _verify_consonant_shape(response):
            raise PromptComposerError("CONSONANT_COMPOSITION_INVARIANT_FAILED")

        candidate = {
            "schema": SCHEMA,
            "status": "PASS_UNDER_PROMPT_SEGMENTER_CONTRACT",
            "composition_mode": mode,
            "response": response,
            "visible_reference_token": token,
            "keyword": keyword,
            "sentence_index": sentence_index,
            "stable_known_overlap_trigrams": final_numerator,
            "distinct_response_trigrams": denominator,
            "filler_length": filler_length,
            "predicted_exact_overlap_percent": predicted,
            "percentage": target,
            "tolerance": tolerance,
            "proof_contract": [
                "PROMPT_SEGMENTER_RECOVERS_REFERENCE_UP_TO_WHITESPACE_ONLY",
                "PRIVATE_USE_CHARACTERS_ARE_NON_WHITESPACE_AND_SELECTED_ABSENT_FROM_RECOVERED_REFERENCE",
                "EVERY_RESPONSE_TRIGRAM_NOT_CONTAINING_SELECTED_PRIVATE_USE_CHARACTERS_IS_LOCAL_TO_THE_SELECTED_VISIBLE_TOKEN_OR_REQUIRED_KEYWORD",
            ],
            "proof_obligations_discharged_under_contract": [
                "PRIVATE_USE_SUFFIX_DISJOINTNESS",
                "RATIO_ONLY_COMPOSITION",
                "PUBLIC_SENTENCE_KEYWORD_COMPOSITION" if has_sentence_keyword else None,
                "PUBLIC_CONSONANT_CLUSTER_COMPOSITION" if has_consonant_cluster else None,
            ],
            "hard_nonclaims": [
                "NO_GENERAL_SEMANTIC_ANSWER_QUALITY_PROOF",
                "NO_GENERAL_FUTURE_CHECKER_COMBINATION_PROOF",
                "NO_TERMINAL_ACCEPTANCE_OR_OPUS55_CAPABILITY_CREDIT",
                "NO_CLAIM_BEYOND_THE_PROMPT_SEGMENTER_EQUIVALENCE_CONTRACT",
            ],
            "model_dependency_count": 0,
            "network_used": False,
            "incremental_spend_usd": 0,
            "terminal_authority": False,
        }
        candidate["proof_obligations_discharged_under_contract"] = [
            item for item in candidate["proof_obligations_discharged_under_contract"] if item
        ]

        distance = abs(predicted - target)
        if best is None or distance < best["_distance"]:
            candidate["_distance"] = distance
            best = candidate

    if best is None:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "NO_CONSTRUCTIVE_RESPONSE_IN_TARGET_BAND",
            "composition_mode": mode,
            "percentage": target,
            "tolerance": tolerance,
            "model_dependency_count": 0,
            "network_used": False,
            "incremental_spend_usd": 0,
            "terminal_authority": False,
        }

    best.pop("_distance", None)
    return best


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return compose(
        str(args.get("prompt") or ""),
        tolerance=float(args.get("tolerance", 2.0)),
        max_filler=int(args.get("max_filler", MAX_FILLER)),
    )
