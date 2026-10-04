#!/usr/bin/env python3
"""Exact public-grammar reduction for the frozen active legacy LiveBench surface.

The historical generator samples 2..5 legacy instruction IDs and removes
conflicting pairs. The exact frozen population is already committed to 15 active
legacy IDs. This module enumerates the *entire conflict-compatible superset* of
active ID sets of cardinality 1..5 and partitions it into seven structural
archetypes. It reads no terminal row content, case frequencies, kwargs, prompts,
responses, or scores.
"""
from __future__ import annotations

from itertools import combinations
from collections import Counter

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_COMPOSITION_ARCHETYPES_V1"
HISTORICAL_GENERATOR_COMMIT = "686be1e78a0ba8036d7e355bc406e1a265da5292"
HISTORICAL_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"
FROZEN_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
MAX_GENERATED_INSTRUCTIONS = 5

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

# Pairwise active conflicts induced by the frozen legacy registry after
# conflict_make() symmetrization. Self-conflicts are irrelevant because the
# historical sampler uses replace=False.
ACTIVE_CONFLICT_PAIRS = frozenset({
    frozenset(("length_constraints:number_paragraphs", "length_constraints:nth_paragraph_first_word")),
    frozenset(("length_constraints:number_paragraphs", "length_constraints:number_sentences")),
    frozenset(("length_constraints:nth_paragraph_first_word", "detectable_format:number_bullet_lists")),
    frozenset(("length_constraints:nth_paragraph_first_word", "detectable_format:multiple_sections")),
    frozenset(("detectable_format:title", "startend:quotation")),

    # JSON conflicts with every active family except existence/forbidden.
    *(
        frozenset(("detectable_format:json_format", other))
        for other in ACTIVE_IDS
        if other not in {
            "detectable_format:json_format",
            "keywords:existence",
            "keywords:forbidden_words",
        }
    ),

    # two_responses conflicts with every active family except
    # existence/forbidden/title.
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

    # repeat_prompt conflicts with every active family except existence/title.
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

ARCHETYPE_ORDER = (
    "JSON",
    "REPEAT_PROMPT",
    "TWO_RESPONSES",
    "NTH_PARAGRAPH",
    "STAR_PARAGRAPH",
    "SENTENCE",
    "PLAIN",
)


def compatible(ids: tuple[str, ...] | list[str] | set[str]) -> bool:
    s = set(ids)
    if len(s) != len(tuple(ids)):
        return False
    if not s <= set(ACTIVE_IDS):
        return False
    return not any(pair <= s for pair in ACTIVE_CONFLICT_PAIRS)


def archetype(ids: tuple[str, ...] | list[str] | set[str]) -> str:
    if not compatible(ids):
        raise ValueError("INCOMPATIBLE_OR_UNKNOWN_ID_SET")
    s = set(ids)
    if "detectable_format:json_format" in s:
        return "JSON"
    if "combination:repeat_prompt" in s:
        return "REPEAT_PROMPT"
    if "combination:two_responses" in s:
        return "TWO_RESPONSES"
    if "length_constraints:nth_paragraph_first_word" in s:
        return "NTH_PARAGRAPH"
    if "length_constraints:number_paragraphs" in s:
        return "STAR_PARAGRAPH"
    if "length_constraints:number_sentences" in s:
        return "SENTENCE"
    return "PLAIN"


def enumerate_compatible_sets() -> tuple[tuple[str, ...], ...]:
    out = []
    for k in range(1, MAX_GENERATED_INSTRUCTIONS + 1):
        for ids in combinations(ACTIVE_IDS, k):
            if compatible(ids):
                out.append(ids)
    return tuple(out)


def verify() -> dict:
    sets = enumerate_compatible_sets()
    counts_by_size = Counter(map(len, sets))
    counts_by_archetype = Counter(archetype(ids) for ids in sets)

    expected_size = {1: 15, 2: 68, 3: 179, 4: 310, 5: 356}
    expected_arch = {
        "JSON": 4,
        "REPEAT_PROMPT": 4,
        "TWO_RESPONSES": 8,
        "NTH_PARAGRAPH": 141,
        "STAR_PARAGRAPH": 227,
        "SENTENCE": 227,
        "PLAIN": 317,
    }

    if len(sets) != 928:
        raise RuntimeError("COMPATIBLE_SET_COUNT_DRIFT")
    if dict(sorted(counts_by_size.items())) != expected_size:
        raise RuntimeError("CARDINALITY_DISTRIBUTION_DRIFT")
    if dict(counts_by_archetype) != expected_arch:
        raise RuntimeError("ARCHETYPE_DISTRIBUTION_DRIFT")
    if sum(counts_by_archetype.values()) != len(sets):
        raise RuntimeError("ARCHETYPE_PARTITION_NOT_TOTAL")
    if set(counts_by_archetype) != set(ARCHETYPE_ORDER):
        raise RuntimeError("ARCHETYPE_SET_DRIFT")

    return {
        "schema": SCHEMA,
        "status": "PASS__928_COMPATIBLE_ACTIVE15_SETS_PARTITION_TO_7_ARCHETYPES",
        "active_id_count": len(ACTIVE_IDS),
        "max_generated_instructions": MAX_GENERATED_INSTRUCTIONS,
        "compatible_set_count": len(sets),
        "counts_by_size": dict(sorted(counts_by_size.items())),
        "archetype_count": len(counts_by_archetype),
        "counts_by_archetype": dict(sorted(counts_by_archetype.items())),
        "terminal_case_content_read": 0,
        "terminal_case_metadata_read": 0,
        "acceptance_credit": False,
    }


def run(args=None, root=None):
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
