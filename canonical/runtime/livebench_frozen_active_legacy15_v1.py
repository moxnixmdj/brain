#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_FROZEN_ACTIVE_LEGACY15_V1"
EXPECTED_COMMITMENT = "af4eeddebf27394eb689d2049f2f8104ae081ebafe237258bdc1a992e96f598d"

ACTIVE_IDS = (
    "keywords:existence",
    "keywords:forbidden_words",
    "length_constraints:number_paragraphs",
    "length_constraints:number_words",
    "length_constraints:number_sentences",
    "length_constraints:nth_paragraph_first_word",
    "detectable_content:postscript",
    "detectable_format:number_bullet_lists",
    "detectable_format:title",
    "detectable_format:multiple_sections",
    "detectable_format:json_format",
    "combination:repeat_prompt",
    "combination:two_responses",
    "startend:end_checker",
    "startend:quotation",
)

EXCLUDED_IDS = (
    "keywords:frequency",
    "keywords:letter_frequency",
    "language:response_language",
    "detectable_content:number_placeholders",
    "detectable_format:constrained_response",
    "detectable_format:number_highlighted_sections",
    "change_case:english_capital",
    "change_case:english_lowercase",
    "change_case:capital_word_frequency",
    "punctuation:no_comma",
)


def commitment(ids=ACTIVE_IDS) -> str:
    return hashlib.sha256(json.dumps(sorted(ids)).encode()).hexdigest()


def verify() -> dict:
    got = commitment()
    if len(ACTIVE_IDS) != 15:
        raise RuntimeError("ACTIVE_ID_COUNT_DRIFT")
    if len(set(ACTIVE_IDS)) != 15:
        raise RuntimeError("ACTIVE_ID_DUPLICATE")
    if set(ACTIVE_IDS) & set(EXCLUDED_IDS):
        raise RuntimeError("ACTIVE_EXCLUDED_INTERSECTION")
    if got != EXPECTED_COMMITMENT:
        raise RuntimeError("TERMINAL_COMMITMENT_MISMATCH")
    return {
        "schema": SCHEMA,
        "status": "PASS__EXISTING_TERMINAL_SET_COMMITMENT_OPENED",
        "active_id_count": 15,
        "commitment_sha256": got,
        "new_terminal_cases_exposed": 0,
        "acceptance_credit": False,
    }
