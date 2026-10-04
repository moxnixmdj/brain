#!/usr/bin/env python3
"""Exact zero-terminal composition-shape reduction for frozen legacy LiveBench IF.

This module reasons only about:
- the existing exact 15-ID commitment opening,
- the pinned legacy INSTRUCTION_CONFLICTS semantics, and
- the recovered historical generator rule: sample 2..5 distinct IDs, then
  delete members of conflicting pairs.

It never reads active terminal prompts, kwargs, question IDs, responses, scores,
or case frequencies.  It reduces the *identity-set search space* only.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from collections import Counter

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_COMPOSITION_SHAPE_REDUCTION_V1"
EXPECTED_ACTIVE_ID_COMMITMENT = "af4eeddebf27394eb689d2049f2f8104ae081ebafe237258bdc1a992e96f598d"

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

# Exact active-active edges induced by the pinned legacy registry after the
# registry's conflict_make symmetry closure.  Self-conflicts are irrelevant
# because the historical generator samples IDs without replacement.
CONFLICT_PAIRS = frozenset({
    frozenset(("length_constraints:number_paragraphs", "length_constraints:number_sentences")),
    frozenset(("length_constraints:number_paragraphs", "length_constraints:nth_paragraph_first_word")),
    frozenset(("length_constraints:nth_paragraph_first_word", "detectable_format:number_bullet_lists")),
    frozenset(("length_constraints:nth_paragraph_first_word", "detectable_format:multiple_sections")),
    frozenset(("detectable_format:title", "startend:quotation")),
    # json_format conflicts with every registered type except keyword existence
    # and forbidden_words.
    *(
        frozenset(("detectable_format:json_format", other))
        for other in ACTIVE_IDS
        if other not in {
            "detectable_format:json_format",
            "keywords:existence",
            "keywords:forbidden_words",
        }
    ),
    # two_responses is compatible, among the active 15, only with existence,
    # forbidden_words, and title.
    *(
        frozenset(("combination:two_responses", other))
        for other in ACTIVE_IDS
        if other not in {
            "combination:two_responses",
            "keywords:existence",
            "keywords:forbidden_words",
            "detectable_format:title",
        }
    ),
    # repeat_prompt is compatible, among the active 15, only with existence and
    # title (the registry also allows no_comma, but that ID is not active).
    *(
        frozenset(("combination:repeat_prompt", other))
        for other in ACTIVE_IDS
        if other not in {
            "combination:repeat_prompt",
            "keywords:existence",
            "detectable_format:title",
        }
    ),
})

EXPECTED_COUNTS_BY_SIZE = {1: 15, 2: 68, 3: 179, 4: 310, 5: 356}
EXPECTED_BRANCH_COUNTS = {"GENERAL": 912, "JSON": 4, "TWO": 8, "REPEAT": 4}
EXPECTED_TOTAL = 928


def active_commitment(ids=ACTIVE_IDS) -> str:
    return hashlib.sha256(json.dumps(sorted(ids)).encode()).hexdigest()


def conflict_compatible(ids) -> bool:
    values = tuple(ids)
    if len(values) != len(set(values)):
        return False
    s = set(values)
    return not any(pair.issubset(s) for pair in CONFLICT_PAIRS)


def branch(ids) -> str:
    s = set(ids)
    if "detectable_format:json_format" in s:
        return "JSON"
    if "combination:two_responses" in s:
        return "TWO"
    if "combination:repeat_prompt" in s:
        return "REPEAT"
    return "GENERAL"


def enumerate_shapes(max_size: int = 5):
    if max_size < 1 or max_size > 5:
        raise ValueError("MAX_SIZE_MUST_BE_1_TO_5")
    out = []
    for size in range(1, max_size + 1):
        for combo in itertools.combinations(ACTIVE_IDS, size):
            if conflict_compatible(combo):
                out.append(combo)
    return tuple(out)


def verify_reduction() -> dict:
    if active_commitment() != EXPECTED_ACTIVE_ID_COMMITMENT:
        raise RuntimeError("ACTIVE_ID_COMMITMENT_DRIFT")
    shapes = enumerate_shapes(5)
    counts_by_size = Counter(map(len, shapes))
    branch_counts = Counter(branch(x) for x in shapes)
    if dict(sorted(counts_by_size.items())) != EXPECTED_COUNTS_BY_SIZE:
        raise RuntimeError("SHAPE_COUNT_DRIFT")
    if dict(sorted(branch_counts.items())) != dict(sorted(EXPECTED_BRANCH_COUNTS.items())):
        raise RuntimeError("BRANCH_COUNT_DRIFT")
    if len(shapes) != EXPECTED_TOTAL:
        raise RuntimeError("TOTAL_SHAPE_COUNT_DRIFT")
    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_CONFLICT_COMPATIBLE_IDENTITY_SHAPE_REDUCTION",
        "active_id_count": len(ACTIVE_IDS),
        "active_id_commitment_sha256": active_commitment(),
        "max_historical_draw_size": 5,
        "conflict_compatible_shape_count": len(shapes),
        "counts_by_size": dict(sorted(counts_by_size.items())),
        "branch_counts": dict(sorted(branch_counts.items())),
        "special_branch_shape_count": sum(branch_counts[k] for k in ("JSON", "TWO", "REPEAT")),
        "general_branch_shape_count": branch_counts["GENERAL"],
        "new_terminal_cases_exposed": 0,
        "terminal_case_content_used": False,
        "terminal_case_metadata_used": False,
        "case_frequency_claimed": False,
        "acceptance_credit": False,
    }


def run(args=None, root=None):
    return verify_reduction()


if __name__ == "__main__":
    print(json.dumps(verify_reduction(), indent=2, sort_keys=True))
