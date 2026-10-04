#!/usr/bin/env python3
from __future__ import annotations

import re

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_RATIO_OVERLAP_PROMPT_SEGMENTER_V1"

class SegmenterError(ValueError):
    pass

_RATIO = re.compile(
    r"Maintain a trigram overlap of (?P<percentage>\d+(?:\.\d+)?)% "
    r"\(±2%\) with the provided reference text\."
)
_SENTENCE_KEYWORD = re.compile(
    r"The response must include keyword \S+ in the \d+-(?:st|nd|rd|th) sentence\."
)
_CONSONANT_CLUSTER = re.compile(
    r"Ensure each word in your response has at least one consonant cluster "
    r"\(two or more consonants together\)\."
)

def normalize_ws(value: str) -> str:
    return " ".join(str(value or "").strip().split())

def recover(prompt: str) -> dict:
    """Recover the normalized ratio-overlap reference from visible prompt text.

    This V1 is deliberately narrow and fail-closed. It recognizes the exact
    public ratio-overlap instruction plus the only two co-occurring instruction
    forms observed in the pinned 300-row public IFBench population.

    It does not claim arbitrary future/terminal instruction-combination coverage.
    """
    text = normalize_ws(prompt)
    m = _RATIO.search(text)
    if not m:
        raise SegmenterError("RATIO_OVERLAP_INSTRUCTION_NOT_FOUND")
    percentage = float(m.group("percentage"))

    # Remove all recognized generated constraint descriptions. Their placement
    # may be prefix, suffix, or middle; the base/reference request remains.
    reduced = _RATIO.sub(" ", text)
    reduced = _SENTENCE_KEYWORD.sub(" ", reduced)
    reduced = _CONSONANT_CLUSTER.sub(" ", reduced)

    # One pinned public row contains U+200B directly between base request and
    # generated ratio constraint. The stored reference_text excludes it. Treat
    # it only as an outer delimiter after recognized constraint removal; never
    # delete U+200B from the interior of recovered base content.
    reduced = re.sub(r"^[\s\u200B]+|[\s\u200B]+$", "", reduced)
    recovered = normalize_ws(reduced)
    if not recovered:
        raise SegmenterError("EMPTY_RECOVERED_REFERENCE")

    # Fail closed if any known generated constraint survives, which would mean
    # the reconstruction is not proven clean for this V1 grammar.
    if _RATIO.search(recovered) or _SENTENCE_KEYWORD.search(recovered) or _CONSONANT_CLUSTER.search(recovered):
        raise SegmenterError("UNREMOVED_RECOGNIZED_CONSTRAINT")

    return {
        "schema": SCHEMA,
        "normalized_reference": recovered,
        "percentage": percentage,
        "source": "VISIBLE_PROMPT_ONLY",
        "exact_raw_whitespace_required": False,
    }
