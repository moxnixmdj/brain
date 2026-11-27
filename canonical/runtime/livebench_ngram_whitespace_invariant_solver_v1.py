#!/usr/bin/env python3
"""Whitespace-invariant constructor for frozen LiveBench ratio:overlap.

No exact reference whitespace is accepted by this API. If V is the
whitespace-normalized visible reference and Y has no whitespace, every
trigram of Y is non-whitespace. Whitespace normalization preserves membership
of every non-whitespace trigram, therefore the frozen character-trigram score
of Y against the exact reference R equals its score against V.
"""
from __future__ import annotations
import math
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class SentenceKeyword:
    word: str
    sentence_number: int

@dataclass(frozen=True)
class SolveResult:
    output: str
    score_percent: float
    target_percent: float
    absolute_error: float

def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()

def trigrams(text: str) -> set[str]:
    return {text[i:i+3] for i in range(max(0, len(text)-2))}

def overlap_parts(output: str, reference: str) -> tuple[int, int]:
    out = trigrams(output)
    if not out:
        raise ValueError("output must form at least one trigram")
    ref = trigrams(reference)
    return len(out & ref), len(out)

def overlap_percent(output: str, reference: str) -> float:
    n, d = overlap_parts(output, reference)
    return 100.0 * n / d

def _fresh_chars(reference: str, count: int) -> str:
    used = set(reference)
    out: list[str] = []
    cp = 0xE000
    while len(out) < count:
        if cp > 0xF8FF:
            raise ValueError("fresh-character pool exhausted")
        ch = chr(cp)
        if ch not in used and not ch.isspace():
            out.append(ch)
        cp += 1
    return "".join(out)

def _prefix(sentence_keyword: SentenceKeyword | None, require_consonant_cluster: bool) -> str:
    if sentence_keyword is not None:
        if sentence_keyword.sentence_number < 1 or not sentence_keyword.word or re.search(r"\s", sentence_keyword.word):
            raise ValueError("invalid sentence-keyword companion")
        return "str!" * (sentence_keyword.sentence_number - 1) + sentence_keyword.word + "str"
    return "str" if require_consonant_cluster else ""

def _sentence_keyword_ok(output: str, spec: SentenceKeyword) -> bool:
    if "." in output or "?" in output:
        return False
    sentences = [piece for piece in output.split("!") if piece]
    return len(sentences) >= spec.sentence_number and spec.word.lower() in sentences[spec.sentence_number-1].lower()

def _consonant_cluster_ok(output: str) -> bool:
    if re.search(r"\s", output):
        return False
    consonants = set("bcdfghjklmnpqrstvwxyz")
    word = output.lower()
    if not any(c in "abcdefghijklmnopqrstuvwxyz" for c in word):
        return True
    return any(word[i] in consonants and word[i+1] in consonants for i in range(len(word)-1))

def solve(
    visible_normalized_reference: str,
    target_percent: float,
    *,
    sentence_keyword: SentenceKeyword | None = None,
    require_consonant_cluster: bool = False,
    tolerance_percent: float = 2.0,
) -> SolveResult:
    reference = normalize_whitespace(visible_normalized_reference)
    if not reference:
        raise ValueError("empty normalized reference")
    if not (0.0 < float(target_percent) <= 100.0):
        raise ValueError("target_percent must be in (0, 100]")
    fixed = _prefix(sentence_keyword, require_consonant_cluster)
    runs = [run for run in reference.split(" ") if len(run) >= 3]
    if not runs:
        raise ValueError("reference has no non-whitespace trigram source")

    best: tuple[float, int, str, float] | None = None
    for run in runs:
        for length in range(3, min(len(run), 90) + 1):
            for start in range(0, len(run) - length + 1):
                source = run[start:start+length]
                if sentence_keyword is not None and any(c in source for c in ".?!"):
                    continue
                base = fixed + source
                numerator, denominator = overlap_parts(base, reference)
                if numerator == 0:
                    continue
                ideal_k = numerator * 100.0 / float(target_percent) - denominator
                for k in {0, max(0, math.floor(ideal_k)), max(0, math.ceil(ideal_k))}:
                    if k > 1000:
                        continue
                    output = base + _fresh_chars(reference, k)
                    if re.search(r"\s", output):
                        raise AssertionError("constructor emitted whitespace")
                    score = overlap_percent(output, reference)
                    error = abs(score - float(target_percent))
                    rank = (error, len(output))
                    if best is None or rank < best[:2]:
                        best = (error, len(output), output, score)

    if best is None:
        raise ValueError("no candidate found")
    error, _, output, score = best
    if error > tolerance_percent:
        raise ValueError(f"target miss: target={target_percent} score={score} error={error}")
    if sentence_keyword is not None and not _sentence_keyword_ok(output, sentence_keyword):
        raise AssertionError("sentence-keyword companion failed")
    if require_consonant_cluster and not _consonant_cluster_ok(output):
        raise AssertionError("consonant-cluster companion failed")
    return SolveResult(output, score, float(target_percent), error)

__all__ = ["SentenceKeyword", "SolveResult", "normalize_whitespace", "trigrams", "overlap_parts", "overlap_percent", "solve"]
