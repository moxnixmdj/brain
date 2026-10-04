#!/usr/bin/env python3
"""Prompt-only normalized reference recovery for the pinned public IFBench ratio-overlap grammar.

Scope is intentionally narrow. This module proves a zero-terminal-data fact over the
public IFBench ratio:overlap construction family; it is not terminal LiveBench
dataset-equivalence authority.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_PUBLIC_NORMALIZED_REFERENCE_SEGMENTER_V1"

_FORMAT_CHARS = re.compile(r"[\u200B-\u200D\uFEFF]")
_WS = re.compile(r"\s+")

_OVERLAP = re.compile(
    r"Maintain a trigram overlap of\s+"
    r"(?P<percentage>\d+(?:\.\d+)?)%\s+"
    r"\(±2%\)\s+with the provided reference text\.",
    re.IGNORECASE,
)
_KEYWORD_SENTENCE = re.compile(
    r"The response must include keyword\s+\S+\s+in the\s+"
    r"\d+-(?:st|nd|rd|th)\s+sentence\.",
    re.IGNORECASE,
)
_CONSONANT_CLUSTER = re.compile(
    r"Ensure each word in your response has at least one consonant cluster\s+"
    r"\(two or more consonants together\)\.",
    re.IGNORECASE,
)

_UNRESOLVED_MARKERS = re.compile(
    r"trigram overlap|provided reference text|"
    r"The response must include keyword|consonant cluster",
    re.IGNORECASE,
)


def normalize_ws(value: str) -> str:
    text = _FORMAT_CHARS.sub("", str(value or ""))
    return _WS.sub(" ", text).strip()


def recover_normalized_reference(prompt: str) -> dict[str, Any]:
    """Recover the normalized base/reference text for the supported public grammar.

    The algorithm observes only the visible prompt. It removes the public
    ratio-overlap instruction and the two co-constraint templates present in the
    complete pinned public ratio-overlap population. Any ambiguity or unresolved
    known marker fails closed.
    """
    visible = normalize_ws(prompt)
    matches = list(_OVERLAP.finditer(visible))
    if len(matches) != 1:
        return {
            "schema": SCHEMA,
            "status": "BLOCKED",
            "normalized_reference": None,
            "percentage": None,
            "reason": "OVERLAP_CLAUSE_COUNT_NOT_EXACTLY_ONE",
            "model_dependency_count": 0,
        }

    percentage = float(matches[0].group("percentage"))
    candidate, overlap_count = _OVERLAP.subn(" ", visible)
    candidate, keyword_count = _KEYWORD_SENTENCE.subn(" ", candidate)
    candidate, cluster_count = _CONSONANT_CLUSTER.subn(" ", candidate)
    candidate = normalize_ws(candidate)

    if not candidate:
        reason = "EMPTY_REFERENCE_AFTER_ERASURE"
    elif _UNRESOLVED_MARKERS.search(candidate):
        reason = "UNRESOLVED_SUPPORTED_GRAMMAR_MARKER"
    else:
        reason = None

    if reason is not None:
        return {
            "schema": SCHEMA,
            "status": "BLOCKED",
            "normalized_reference": None,
            "percentage": percentage,
            "reason": reason,
            "model_dependency_count": 0,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS__PUBLIC_GRAMMAR_NORMALIZED_REFERENCE_RECOVERED",
        "normalized_reference": candidate,
        "percentage": percentage,
        "removed_overlap_clauses": overlap_count,
        "removed_keyword_sentence_constraints": keyword_count,
        "removed_consonant_cluster_constraints": cluster_count,
        "model_dependency_count": 0,
        "terminal_case_dependency_count": 0,
        "authority": "PUBLIC_GRAMMAR_PROOF_INPUT_ONLY",
    }
