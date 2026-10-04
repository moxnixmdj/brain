#!/usr/bin/env python3
"""Whitespace-invariant constructor for LiveBench/IFBench NGramOverlapChecker.

The pinned checker computes character-trigram set overlap:
    |T3(candidate) ∩ T3(reference)| / |T3(candidate)|

For a candidate containing no whitespace, membership of every candidate trigram
is invariant under the specific normalization N(s)=collapse each whitespace run
to one ASCII space and strip outer whitespace. N does not create adjacency
between non-whitespace characters that were separated by whitespace.

Therefore a normalized visible reference is an exact membership oracle for
all trigrams of a whitespace-free candidate, even when the raw reference has
unknown tabs/newlines/repeated spaces.

This module is intentionally narrow. It does not recover the reference from a
full benchmark prompt and it does not solve conjunctions with other checkers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_NGRAM_WHITESPACE_INVARIANT_CONSTRUCTOR_V1"


class NGramConstructionError(RuntimeError):
    pass


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def trigram_set(text: str) -> set[str]:
    value = str(text or "")
    return {value[i : i + 3] for i in range(max(0, len(value) - 2))}


def overlap_percent(candidate: str, reference: str) -> float:
    cand = trigram_set(candidate)
    if not cand:
        raise NGramConstructionError("CANDIDATE_HAS_NO_TRIGRAMS")
    ref = trigram_set(reference)
    return 100.0 * len(cand & ref) / len(cand)


def invariant_membership_percent(candidate: str, normalized_reference: str) -> float:
    if any(ch.isspace() for ch in candidate):
        raise NGramConstructionError("CANDIDATE_MUST_BE_WHITESPACE_FREE")
    return overlap_percent(candidate, normalize_ws(normalized_reference))


def _novel_chars(base: str, limit: int) -> str:
    out: list[str] = []
    # Unicode Private Use Area. We only select characters absent from the
    # normalized reference, so every trigram containing one is a certified
    # non-overlap trigram under the normalization theorem.
    for cp in range(0xE000, 0xF8FF + 1):
        ch = chr(cp)
        if ch not in base:
            out.append(ch)
            if len(out) >= limit:
                break
    if len(out) < limit:
        raise NGramConstructionError("INSUFFICIENT_NOVEL_CHARACTER_POOL")
    return "".join(out)


@dataclass(frozen=True)
class Witness:
    candidate: str
    predicted_percent: float
    target_percent: float
    absolute_error: float
    seed_start: int
    seed_length: int
    novel_length: int

    def as_dict(self) -> dict:
        return {
            "schema": SCHEMA,
            "status": "PASS",
            "candidate": self.candidate,
            "predicted_percent": self.predicted_percent,
            "target_percent": self.target_percent,
            "absolute_error": self.absolute_error,
            "seed_start": self.seed_start,
            "seed_length": self.seed_length,
            "novel_length": self.novel_length,
            "candidate_whitespace_free": not any(ch.isspace() for ch in self.candidate),
            "raw_reference_required": False,
            "normalized_reference_required": True,
        }


def construct_overlap_witness(
    normalized_reference: str,
    target_percent: float,
    *,
    tolerance: float = 2.0,
    max_seed_span: int = 240,
    max_starts: int = 80,
    max_novel: int = 160,
) -> dict:
    """Construct a whitespace-free witness or fail closed.

    Search is deterministic and uses only the normalized reference plus target.
    The output is not claimed universal: if no witness is found inside the
    bounded search envelope, status is BLOCKED rather than fabricated success.
    """
    ref = normalize_ws(normalized_reference)
    target = float(target_percent)
    tol = float(tolerance)
    if not 0.0 <= target <= 100.0:
        raise NGramConstructionError("TARGET_PERCENT_OUT_OF_RANGE")
    if tol < 0.0:
        raise NGramConstructionError("NEGATIVE_TOLERANCE")

    compact = "".join(ch for ch in ref if not ch.isspace())
    if len(compact) < 3:
        return {
            "schema": SCHEMA,
            "status": "BLOCKED",
            "reason": "NORMALIZED_REFERENCE_HAS_FEWER_THAN_THREE_NONWHITESPACE_CHARACTERS",
            "raw_reference_required": False,
        }

    novel = _novel_chars(ref, max_novel)
    best: Witness | None = None
    start_count = min(max(0, len(compact) - 2), max_starts)

    for start in range(start_count):
        max_len = min(max_seed_span, len(compact) - start)
        for seed_len in range(3, max_len + 1):
            seed = compact[start : start + seed_len]
            for novel_len in range(0, max_novel + 1):
                candidate = seed + novel[:novel_len]
                predicted = invariant_membership_percent(candidate, ref)
                error = abs(predicted - target)
                witness = Witness(
                    candidate=candidate,
                    predicted_percent=predicted,
                    target_percent=target,
                    absolute_error=error,
                    seed_start=start,
                    seed_length=seed_len,
                    novel_length=novel_len,
                )
                if best is None or (
                    witness.absolute_error,
                    len(witness.candidate),
                    witness.seed_start,
                    witness.seed_length,
                    witness.novel_length,
                ) < (
                    best.absolute_error,
                    len(best.candidate),
                    best.seed_start,
                    best.seed_length,
                    best.novel_length,
                ):
                    best = witness
                if error <= tol:
                    return witness.as_dict()

    assert best is not None
    out = best.as_dict()
    out["status"] = "BLOCKED"
    out["reason"] = "NO_WITNESS_WITHIN_SEARCH_ENVELOPE"
    return out


def verify_against_raw_reference(
    candidate: str,
    raw_reference: str,
    normalized_reference: str,
) -> dict:
    """Diagnostic theorem check. Raw reference is verifier-only, never required
    by the constructor itself.
    """
    if any(ch.isspace() for ch in candidate):
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "reason": "CANDIDATE_NOT_WHITESPACE_FREE",
        }
    expected_norm = normalize_ws(raw_reference)
    supplied_norm = normalize_ws(normalized_reference)
    if expected_norm != supplied_norm:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "reason": "NORMALIZED_REFERENCE_MISMATCH",
        }
    raw = overlap_percent(candidate, raw_reference)
    normalized = overlap_percent(candidate, supplied_norm)
    return {
        "schema": SCHEMA,
        "status": "PASS" if raw == normalized else "FAIL",
        "raw_percent": raw,
        "normalized_percent": normalized,
        "exact_equal": raw == normalized,
    }
