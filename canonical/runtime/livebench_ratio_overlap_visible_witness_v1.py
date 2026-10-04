#!/usr/bin/env python3
from __future__ import annotations

"""Visible-only constructive witness for the frozen LiveBench character-trigram overlap checker."""

from dataclasses import dataclass


class VisibleOverlapWitnessError(RuntimeError):
    pass


@dataclass(frozen=True)
class VisibleOverlapWitness:
    token: str
    target_percent: float
    novel_char_count: int
    overlap_trigram_count: int
    predicted_percent: float
    response: str


def character_trigrams(value: str) -> set[str]:
    text = str(value or "")
    return {text[i:i + 3] for i in range(max(0, len(text) - 2))}


def _novel_suffix(visible_reference: str, count: int) -> str:
    out: list[str] = []
    cp = 0xE000
    while len(out) < count:
        ch = chr(cp)
        cp += 1
        if ch not in visible_reference:
            out.append(ch)
    return "".join(out)


def synthesize_from_visible_reference(
    visible_reference: str,
    target_percent: float,
    *,
    tolerance_pp: float = 2.0,
    max_novel_chars: int = 10000,
) -> VisibleOverlapWitness:
    """Build a witness without accepting hidden reference_text or hidden kwargs."""

    visible = str(visible_reference or "")
    target = float(target_percent)
    tolerance = float(tolerance_pp)
    if not visible.strip():
        raise VisibleOverlapWitnessError("VISIBLE_REFERENCE_REQUIRED")
    if not (0.0 <= target <= 100.0):
        raise VisibleOverlapWitnessError("TARGET_PERCENT_OUT_OF_RANGE")
    if tolerance < 0:
        raise VisibleOverlapWitnessError("NEGATIVE_TOLERANCE")

    best: tuple[int, int, str, float] | None = None
    for token in visible.split():
        k = len(character_trigrams(token))
        if k == 0:
            continue
        for m in range(max_novel_chars + 1):
            predicted = 100.0 * k / (k + m)
            if abs(predicted - target) <= tolerance + 1e-12:
                item = (m, -k, token, predicted)
                if best is None or item < best:
                    best = item
                break

    if best is None:
        raise VisibleOverlapWitnessError("NO_VISIBLE_TOKEN_WITNESS_WITHIN_TOLERANCE")

    m, neg_k, token, predicted = best
    k = -neg_k
    response = token + _novel_suffix(visible, m)
    if len(character_trigrams(response)) != k + m:
        raise VisibleOverlapWitnessError("CONSTRUCTION_CARDINALITY_INVARIANT_FAILED")

    return VisibleOverlapWitness(
        token=token,
        target_percent=target,
        novel_char_count=m,
        overlap_trigram_count=k,
        predicted_percent=predicted,
        response=response,
    )


def exact_frozen_overlap_percent(candidate: str, exact_reference: str) -> float:
    """Mathematical equivalent of the frozen checker core, for verification only."""

    candidate_grams = character_trigrams(candidate)
    if not candidate_grams:
        raise VisibleOverlapWitnessError("EMPTY_CANDIDATE_TRIGRAM_SET")
    reference_grams = character_trigrams(exact_reference)
    return 100.0 * len(candidate_grams & reference_grams) / len(candidate_grams)
