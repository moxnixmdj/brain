#!/usr/bin/env python3
"""Reference-byte-free constructor for LiveBench/IFBench ratio:overlap.

This module is a candidate capability repair. It consumes only the visible prompt
and public instruction grammar. It never reads hidden benchmark kwargs, hidden
reference_text, case IDs, or comparator results.

The construction relies on a precise premise: after deleting public instruction
descriptions and normalizing whitespace, the remaining visible base equals the
whitespace-normalized scorer reference. Under that premise every whitespace-free
character trigram from the visible base is guaranteed to occur in the exact
reference, while any trigram containing a fresh private-use sentinel is
guaranteed not to occur. The scorer's set-overlap fraction can therefore be
dialed without the exact reference bytes.
"""
from __future__ import annotations

import re
from typing import Any

RATIO_RE = re.compile(
    r"Maintain a trigram overlap of (\d+)% \(±2%\) with the provided reference text\."
)
KEYWORD_RE = re.compile(
    r'The response must include keyword "?([A-Za-z0-9_-]+)"? in the '
    r"(\d+)-(?:st|nd|rd|th) sentence\."
)
CONSONANT_DESCRIPTION = (
    "Ensure each word in your response has at least one consonant cluster "
    "(two or more consonants together)."
)


def _ngrams(text: str, n: int = 3) -> set[str]:
    return {text[i : i + n] for i in range(max(0, len(text) - n + 1))}


def _norm_ws(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def visible_base_from_prompt(prompt: str) -> str:
    """Recover the public base text without reading any hidden kwargs."""
    text = RATIO_RE.sub("", str(prompt))
    text = KEYWORD_RE.sub("", text)
    text = text.replace(CONSONANT_DESCRIPTION, "")
    text = text.replace("\u200b", "")
    return _norm_ws(text)


def _parse_visible_contract(prompt: str) -> dict[str, Any]:
    ratio = RATIO_RE.search(prompt)
    if ratio is None:
        raise ValueError("RATIO_OVERLAP_DESCRIPTION_NOT_FOUND")
    keyword = KEYWORD_RE.search(prompt)
    return {
        "target_percent": int(ratio.group(1)),
        "keyword": keyword.group(1) if keyword else None,
        "keyword_sentence": int(keyword.group(2)) if keyword else None,
        "consonant_cluster_required": CONSONANT_DESCRIPTION in prompt,
        "visible_base": visible_base_from_prompt(prompt),
    }


def _fresh_sentinels(base: str, count: int = 1400) -> list[str]:
    present = set(base)
    out: list[str] = []
    for cp in range(0xE000, 0xF900):
        ch = chr(cp)
        if ch not in present:
            out.append(ch)
            if len(out) >= count:
                return out
    raise ValueError("INSUFFICIENT_FRESH_PRIVATE_USE_SENTINELS")


def _classify_candidate(
    candidate: str, base: str, sentinel_set: set[str]
) -> dict[str, Any]:
    good_trigrams = {
        gram
        for gram in _ngrams(base)
        if not any(ch.isspace() for ch in gram)
    }
    good = 0
    bad = 0
    ambiguous: list[str] = []
    for gram in _ngrams(candidate):
        if any(ch in sentinel_set for ch in gram):
            bad += 1
        elif any(ch.isspace() for ch in gram):
            ambiguous.append(gram)
        elif gram in good_trigrams:
            good += 1
        else:
            bad += 1
    total = good + bad
    ratio = (100.0 * good / total) if total else 0.0
    return {
        "good": good,
        "bad": bad,
        "ambiguous": sorted(ambiguous),
        "predicted_overlap_percent": ratio,
    }


def _ranked_tokens(base: str, *, sentence_safe: bool) -> list[str]:
    tokens = [token for token in base.split() if len(token) >= 3]
    if sentence_safe:
        tokens = [token for token in tokens if not any(x in token for x in ".!?")]
    return sorted(tokens, key=lambda token: len(_ngrams(token)), reverse=True)


def _build_core(
    tokens: list[str], sentinels: list[str], *, wrapped: bool
) -> tuple[str, int]:
    if not tokens:
        return "", 0
    if not wrapped:
        return tokens[0], 0
    parts: list[str] = []
    used = 0
    for token in tokens:
        parts.extend((sentinels[used], token, sentinels[used + 1]))
        used += 2
    return "".join(parts), used


def _wrap_companions(
    core: str,
    *,
    keyword: str | None,
    keyword_sentence: int | None,
    consonant_cluster_required: bool,
    sentinels: list[str],
    used: int,
    bad_tail_len: int,
) -> tuple[str, int]:
    tail = "".join(sentinels[used : used + bad_tail_len])
    used += bad_tail_len
    payload = core + tail

    if consonant_cluster_required:
        return payload + sentinels[used] + "bb" + sentinels[used + 1], used + 2

    if keyword is not None:
        if keyword_sentence is None or keyword_sentence <= 0:
            raise ValueError("INVALID_KEYWORD_SENTENCE")
        sentences: list[str] = []
        for index in range(1, keyword_sentence + 1):
            left, right = sentinels[used], sentinels[used + 1]
            used += 2
            inner = payload if index == 1 else ""
            if index == keyword_sentence:
                if inner:
                    inner += sentinels[used]
                    used += 1
                inner += keyword
            if not inner:
                inner = sentinels[used]
                used += 1
            sentences.append(left + inner + right + ".")
        return " ".join(sentences), used

    return payload, used


def construct_ratio_overlap_candidate(prompt: str) -> dict[str, Any]:
    """Construct a ratio-overlap witness from the visible prompt only.

    The returned candidate is valid only under the explicitly returned
    required_reference_relation premise. Exact reference bytes are never consumed.
    """
    meta = _parse_visible_contract(prompt)
    target = meta["target_percent"]
    if not 0 <= target <= 100:
        raise ValueError("INVALID_TARGET_PERCENT")

    base = meta["visible_base"]
    sentinels = _fresh_sentinels(base)
    sentinel_set = set(sentinels)
    keyword = meta["keyword"]
    has_consonant = bool(meta["consonant_cluster_required"])
    ranked = _ranked_tokens(base, sentence_safe=keyword is not None)
    if not ranked:
        raise ValueError("NO_VISIBLE_GOOD_TRIGRAM_SOURCE")

    token_options: list[list[str]] = [[token] for token in ranked[:40]]
    if keyword is not None:
        token_options.extend(
            ranked[:k] for k in range(2, min(len(ranked), 20) + 1)
        )
    elif has_consonant:
        token_options.extend(
            ranked[:k] for k in range(2, min(len(ranked), 8) + 1)
        )

    best: dict[str, Any] | None = None
    for tokens in token_options:
        wrapped = keyword is not None or (has_consonant and len(tokens) > 1)
        core, used = _build_core(tokens, sentinels, wrapped=wrapped)
        for bad_tail_len in range(0, 301):
            candidate, _ = _wrap_companions(
                core,
                keyword=keyword,
                keyword_sentence=meta["keyword_sentence"],
                consonant_cluster_required=has_consonant,
                sentinels=sentinels,
                used=used,
                bad_tail_len=bad_tail_len,
            )
            classification = _classify_candidate(candidate, base, sentinel_set)
            if classification["ambiguous"]:
                continue
            error = abs(classification["predicted_overlap_percent"] - target)
            if best is None or error < best["absolute_error_percent"]:
                best = {
                    "candidate": candidate,
                    "absolute_error_percent": error,
                    "bad_tail_len": bad_tail_len,
                    "source_tokens": list(tokens),
                    **classification,
                }
            if error < 1e-12:
                break

    if best is None or best["absolute_error_percent"] > 2.0:
        raise ValueError("NO_PROVABLE_IN_BAND_CONSTRUCTION_FOUND")

    return {
        "schema": "PROJECT_BRAIN_LIVEBENCH_RATIO_REFERENCE_FREE_CONSTRUCTOR_V1",
        "status": "CANDIDATE_CONSTRUCTION_FOUND",
        "target_percent": target,
        "visible_base": base,
        "keyword": keyword,
        "keyword_sentence": meta["keyword_sentence"],
        "consonant_cluster_required": has_consonant,
        "required_reference_relation": (
            "NORMALIZE_WHITESPACE(EXACT_REFERENCE_TEXT)==VISIBLE_BASE"
        ),
        "uses_hidden_reference_text": False,
        "uses_hidden_kwargs": False,
        "uses_case_id": False,
        "uses_comparator_feedback": False,
        **best,
    }
