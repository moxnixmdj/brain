"""Visible-prompt-only robust compiler for frozen LiveBench IFBench ratio:overlap.

This module deliberately does not accept hidden instruction ids, kwargs, terminal case ids,
or raw reference_text. It compiles from the natural-language prompt only.

Bound scorer semantics:
  score = |T3(output) intersect T3(raw_reference)| / |T3(output)|
where T3 is the SET of character trigrams.

The construction is invariant to changes in raw whitespace whenever the visible prompt
recovers the whitespace-normalized reference. It is a component, not a LiveBench closure
certificate.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

RATIO_RE = re.compile(
    r"Maintain a trigram overlap of (\d+(?:\.\d+)?)% \(±2%\) with the provided reference text\."
)
SENTENCE_RE = re.compile(
    r'The response must include keyword\s+"?([^"\s]+)"?\s+in the (\d+)(?:-st|-nd|-rd|-th) sentence\.'
)
CONSONANT_TEXT = (
    "Ensure each word in your response has at least one consonant cluster "
    "(two or more consonants together)."
)
ASCII_CONSONANTS = set("bcdfghjklmnpqrstvwxyz")
ASCII_LETTERS = set("abcdefghijklmnopqrstuvwxyz")


@dataclass(frozen=True)
class RatioOverlapWitness:
    output: str
    target_percent: float
    robust_percent: float
    stable_hits: int
    output_trigram_count: int
    visible_reference: str
    base: str
    fresh_suffix_count: int


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def _trigrams(s: str) -> set[str]:
    return {s[i : i + 3] for i in range(max(0, len(s) - 2))}


def _stable_reference_trigrams(normalized_reference: str) -> set[str]:
    out: set[str] = set()
    for token in re.findall(r"\S+", normalized_reference):
        out |= _trigrams(token)
    return out


def recover_visible_reference(prompt: str) -> str:
    """Recover the public-family whitespace-normalized reference from visible text."""
    s = RATIO_RE.sub(" ", prompt)
    s = SENTENCE_RE.sub(" ", s)
    s = s.replace(CONSONANT_TEXT, " ")
    s = re.sub(r"^[\s\u200B\uFEFF]+|[\s\u200B\uFEFF]+$", "", s)
    return _norm_ws(s)


def _fresh_chars(reference: str, count: int = 1024) -> list[str]:
    """Return non-whitespace sentinels provably absent from the visible reference."""
    chars: list[str] = []
    cp = 0xE000
    while len(chars) < count:
        ch = chr(cp)
        cp += 1
        if ch not in reference:
            chars.append(ch)
    return chars


def _has_consonant_cluster(s: str) -> bool:
    t = s.lower()
    return any(
        t[i] in ASCII_CONSONANTS and t[i + 1] in ASCII_CONSONANTS
        for i in range(len(t) - 1)
    )


def _consonant_checker(value: str) -> bool:
    for word in value.lower().strip().split():
        if all(ch not in ASCII_LETTERS for ch in word):
            continue
        if not _has_consonant_cluster(word):
            return False
    return True


def _constructed_sentences(value: str) -> list[str]:
    # Construction uses only "." as sentence punctuation and introduces no protected
    # abbreviation/decimal forms, so this equals the frozen splitter on our witnesses.
    return [x.strip() for x in value.split(".") if x.strip()]


def _keyword_checker(value: str, keyword: str, n: int) -> bool:
    sentences = _constructed_sentences(value)
    return len(sentences) >= n and keyword.lower() in sentences[n - 1].lower()


def _score(value: str, reference_grams: set[str]) -> tuple[int, int, float]:
    gs = _trigrams(value)
    if not gs:
        raise ValueError("candidate has no trigrams")
    hits = len(gs & reference_grams)
    return hits, len(gs), 100.0 * hits / len(gs)


def compile_ratio_overlap_from_visible_prompt(
    prompt: str,
    *,
    max_fresh_suffix: int = 256,
) -> RatioOverlapWitness:
    """Construct a ratio:overlap witness using visible prompt text only.

    Fails closed if the public grammar is not recognized or no bounded witness is found.
    """
    ratio = RATIO_RE.search(prompt)
    if ratio is None:
        raise ValueError("unrecognized ratio:overlap description")
    target = float(ratio.group(1))
    if not 0 <= target <= 100:
        raise ValueError("invalid ratio target")

    visible_reference = recover_visible_reference(prompt)
    if not visible_reference:
        raise ValueError("empty visible reference")
    stable = _stable_reference_trigrams(visible_reference)

    sentence_match = SENTENCE_RE.search(prompt)
    sentence = None
    if sentence_match is not None:
        sentence = (sentence_match.group(1), int(sentence_match.group(2)))
        if sentence[1] < 1:
            raise ValueError("invalid sentence index")

    needs_consonant = CONSONANT_TEXT in prompt
    fresh = _fresh_chars(visible_reference, max_fresh_suffix + 2)

    def build(base: str, extra: int) -> str:
        out = base
        if sentence is not None:
            keyword, n = sentence
            q = fresh[0]
            if n == 1:
                out = q + keyword + q + base
            else:
                out = base + q
                # Repeated identical scaffold raises sentence count while adding only
                # O(1) distinct trigrams because the scorer deduplicates with a set.
                for _ in range(2, n):
                    out += "." + q
                out += "." + q + keyword + q
        for i in range(extra):
            out += fresh[i + 1]
        return out

    for token in re.findall(r"\S+", visible_reference):
        for start in range(len(token)):
            for end in range(start + 3, len(token) + 1):
                base = token[start:end]
                if needs_consonant and not _has_consonant_cluster(base):
                    continue
                for extra in range(max_fresh_suffix + 1):
                    output = build(base, extra)
                    hits, total, percent = _score(output, stable)
                    if not target - 2 <= percent <= target + 2:
                        continue
                    if sentence is not None and not _keyword_checker(
                        output, sentence[0], sentence[1]
                    ):
                        continue
                    if needs_consonant and not _consonant_checker(output):
                        continue
                    return RatioOverlapWitness(
                        output=output,
                        target_percent=target,
                        robust_percent=percent,
                        stable_hits=hits,
                        output_trigram_count=total,
                        visible_reference=visible_reference,
                        base=base,
                        fresh_suffix_count=extra,
                    )

    raise ValueError("no robust witness found within bounded search")
