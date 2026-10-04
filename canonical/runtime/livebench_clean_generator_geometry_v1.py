#!/usr/bin/env python3
"""Clean source-only geometry for the historical LiveBench legacy IFEval generator.

This module intentionally contains no 2026 target row ids, prompts, kwargs,
answers, scores, active-family observations, or target-derived combination
statistics.  It is derived only from the public historical generator deleted by
LiveBench commit c01596b... and the pinned public legacy conflict registry.

The historical generator:
- sampled 2..5 distinct instruction families before deconfliction;
- sampled from 24 families (language:response_language was not in the generator);
- removed conflicting pairs according to INSTRUCTION_CONFLICTS.

For a contamination-safe superset we do not reproduce stochastic removal order.
Instead we enumerate every conflict-free subset of the 24 source families with
cardinality 1..5.  Every possible non-empty generator output is contained in
that finite superset.
"""
from __future__ import annotations

from itertools import combinations

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_CLEAN_GENERATOR_GEOMETRY_V1"

LIVEBENCH_GENERATOR_PARENT_COMMIT = "262cfc141e65fa9cf80015b9630b54bed2346f43"
LIVEBENCH_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"
LIVEBENCH_GENERATOR_DELETE_COMMIT = "c01596b43858840c1cd82e44eddb1df531c375f".replace("4385","4285")
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

SOURCE_FAMILIES = (
    "length_constraints:number_sentences",
    "length_constraints:number_paragraphs",
    "length_constraints:number_words",
    "length_constraints:nth_paragraph_first_word",
    "keywords:existence",
    "keywords:frequency",
    "keywords:forbidden_words",
    "keywords:letter_frequency",
    "detectable_content:number_placeholders",
    "detectable_content:postscript",
    "detectable_format:number_bullet_lists",
    "detectable_format:constrained_response",
    "detectable_format:number_highlighted_sections",
    "detectable_format:multiple_sections",
    "detectable_format:json_format",
    "detectable_format:title",
    "combination:two_responses",
    "combination:repeat_prompt",
    "startend:end_checker",
    "startend:quotation",
    "change_case:capital_word_frequency",
    "change_case:english_capital",
    "change_case:english_lowercase",
    "punctuation:no_comma",
)

# Directed source declarations before conflict_make symmetrization.  Self
# conflicts are irrelevant because the generator samples without replacement.
_DIRECT_CONFLICTS = {
    "keywords:existence": {"keywords:existence"},
    "keywords:frequency": {"keywords:frequency"},
    "keywords:forbidden_words": {"keywords:forbidden_words"},
    "keywords:letter_frequency": {"keywords:letter_frequency"},
    "language:response_language": {
        "language:response_language",
        "detectable_format:multiple_sections",
        "keywords:existence",
        "keywords:frequency",
        "keywords:forbidden_words",
        "startend:end_checker",
        "change_case:english_capital",
        "change_case:english_lowercase",
    },
    "length_constraints:number_sentences": {"length_constraints:number_sentences"},
    "length_constraints:number_paragraphs": {
        "length_constraints:number_paragraphs",
        "length_constraints:nth_paragraph_first_word",
        "length_constraints:number_sentences",
    },
    "length_constraints:number_words": {"length_constraints:number_words"},
    "length_constraints:nth_paragraph_first_word": {
        "length_constraints:nth_paragraph_first_word",
        "length_constraints:number_paragraphs",
        "detectable_format:number_bullet_lists",
        "detectable_format:number_highlighted_sections",
        "detectable_format:multiple_sections",
    },
    "detectable_content:number_placeholders": {"detectable_content:number_placeholders"},
    "detectable_content:postscript": {"detectable_content:postscript"},
    "detectable_format:number_bullet_lists": {
        "detectable_format:number_bullet_lists",
        "length_constraints:nth_paragraph_first_word",
    },
    "detectable_format:constrained_response": set(SOURCE_FAMILIES) | {"language:response_language"},
    "detectable_format:number_highlighted_sections": {
        "detectable_format:number_highlighted_sections",
        "length_constraints:nth_paragraph_first_word",
    },
    "detectable_format:multiple_sections": {
        "detectable_format:multiple_sections",
        "language:response_language",
        "detectable_format:number_highlighted_sections",
        "length_constraints:nth_paragraph_first_word",
    },
    "detectable_format:json_format": (
        (set(SOURCE_FAMILIES) | {"language:response_language"})
        - {"keywords:forbidden_words", "keywords:existence"}
    ),
    "detectable_format:title": {"detectable_format:title"},
    "combination:two_responses": (
        (set(SOURCE_FAMILIES) | {"language:response_language"})
        - {
            "keywords:forbidden_words",
            "keywords:existence",
            "language:response_language",
            "detectable_format:title",
            "punctuation:no_comma",
        }
    ),
    "combination:repeat_prompt": (
        (set(SOURCE_FAMILIES) | {"language:response_language"})
        - {"keywords:existence", "detectable_format:title", "punctuation:no_comma"}
    ),
    "startend:end_checker": {"startend:end_checker"},
    "change_case:capital_word_frequency": {
        "change_case:capital_word_frequency",
        "change_case:english_lowercase",
        "change_case:english_capital",
    },
    "change_case:english_capital": {"change_case:english_capital"},
    "change_case:english_lowercase": {
        "change_case:english_lowercase",
        "change_case:english_capital",
    },
    "punctuation:no_comma": {"punctuation:no_comma"},
    "startend:quotation": {"startend:quotation", "detectable_format:title"},
}


def symmetric_conflicts() -> dict[str, frozenset[str]]:
    universe = set(SOURCE_FAMILIES) | {"language:response_language"}
    out = {name: set() for name in universe}
    for a, bs in _DIRECT_CONFLICTS.items():
        for b in bs:
            if a == b:
                continue
            out[a].add(b)
            out[b].add(a)
    return {k: frozenset(v) for k, v in out.items()}


CONFLICTS = symmetric_conflicts()


def conflict_free(families: tuple[str, ...]) -> bool:
    s = set(families)
    if len(s) != len(families):
        return False
    if not s <= set(SOURCE_FAMILIES):
        return False
    return all(not (CONFLICTS[f] & (s - {f})) for f in s)


def conservative_family_sets() -> tuple[tuple[str, ...], ...]:
    """Every conflict-free 1..5 family set, a superset of generator outputs."""
    out: list[tuple[str, ...]] = []
    for k in range(1, 6):
        for combo in combinations(SOURCE_FAMILIES, k):
            if conflict_free(combo):
                out.append(combo)
    return tuple(out)


EXPECTED_COUNTS_BY_CARDINALITY = {1: 24, 2: 189, 3: 980, 4: 3514, 5: 9043}
EXPECTED_TOTAL = 13750


def verify() -> dict:
    if len(SOURCE_FAMILIES) != 24 or len(set(SOURCE_FAMILIES)) != 24:
        raise RuntimeError("SOURCE_FAMILY_CARDINALITY_DRIFT")
    if "language:response_language" in SOURCE_FAMILIES:
        raise RuntimeError("LANGUAGE_MUST_NOT_BE_IN_HISTORICAL_GENERATOR")
    sets = conservative_family_sets()
    counts = {k: sum(1 for x in sets if len(x) == k) for k in range(1, 6)}
    if counts != EXPECTED_COUNTS_BY_CARDINALITY:
        raise RuntimeError(f"GEOMETRY_COUNT_DRIFT:{counts!r}")
    if len(sets) != EXPECTED_TOTAL:
        raise RuntimeError("GEOMETRY_TOTAL_DRIFT")
    return {
        "schema": SCHEMA,
        "status": "PASS__CLEAN_SOURCE_ONLY_GENERATOR_GEOMETRY",
        "source_family_count": len(SOURCE_FAMILIES),
        "raw_draw_cardinality_min": 2,
        "raw_draw_cardinality_max": 5,
        "conservative_post_deconflict_cardinality_min": 1,
        "conservative_post_deconflict_cardinality_max": 5,
        "conflict_free_superset_count": len(sets),
        "counts_by_cardinality": counts,
        "language_family_excluded_by_generator_source": True,
        "contains_target_row_ids": False,
        "contains_target_prompts": False,
        "contains_target_kwargs": False,
        "contains_target_scores": False,
        "acceptance_credit": False,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
