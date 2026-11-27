#!/usr/bin/env python3
"""Exact conflict-compatible structural superset for historical LiveBench 24.

The historical generator samples 2..5 IDs without replacement and then removes
conflicting IDs. Therefore every emitted ID set is a conflict-compatible subset
of the exact 24-ID generator pool with cardinality 1..5. Enumerating that whole
superset removes any dependence on empirical case frequencies.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations

from canonical.runtime import livebench_historical24_scope_superset_v1 as scope

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_HISTORICAL24_COMPOSITION_SPACE_V1"
MAX_GENERATED_INSTRUCTIONS = 5
IDS = tuple(scope.HISTORICAL24)
ID_SET = frozenset(IDS)

CONSTRAINED = "detectable_format:constrained_response"
JSON_ID = "detectable_format:json_format"
REPEAT = "combination:repeat_prompt"
TWO = "combination:two_responses"

# Exact symmetric conflict relation induced by the pinned registry.  Self
# conflicts are omitted because the generator samples without replacement.
_pairs: set[frozenset[str]] = set()


def _conflict(a: str, b: str) -> None:
    if a != b and a in ID_SET and b in ID_SET:
        _pairs.add(frozenset((a, b)))


def _conflict_many(a: str, others) -> None:
    for b in others:
        _conflict(a, b)


_conflict_many(
    "length_constraints:number_paragraphs",
    {
        "length_constraints:nth_paragraph_first_word",
        "length_constraints:number_sentences",
    },
)
_conflict_many(
    "length_constraints:nth_paragraph_first_word",
    {
        "detectable_format:number_bullet_lists",
        "detectable_format:number_highlighted_sections",
        "detectable_format:multiple_sections",
    },
)
_conflict_many(CONSTRAINED, ID_SET - {CONSTRAINED})
_conflict("detectable_format:multiple_sections", "detectable_format:number_highlighted_sections")
_conflict_many(
    JSON_ID,
    ID_SET
    - {
        JSON_ID,
        "keywords:forbidden_words",
        "keywords:existence",
    },
)
_conflict_many(
    TWO,
    ID_SET
    - {
        TWO,
        "keywords:forbidden_words",
        "keywords:existence",
        "detectable_format:title",
        "punctuation:no_comma",
    },
)
_conflict_many(
    REPEAT,
    ID_SET
    - {
        REPEAT,
        "keywords:existence",
        "detectable_format:title",
        "punctuation:no_comma",
    },
)
_conflict_many(
    "change_case:capital_word_frequency",
    {
        "change_case:english_lowercase",
        "change_case:english_capital",
    },
)
_conflict("change_case:english_lowercase", "change_case:english_capital")
_conflict("startend:quotation", "detectable_format:title")

CONFLICT_PAIRS = frozenset(_pairs)


def compatible(ids) -> bool:
    seq = tuple(ids)
    s = set(seq)
    if len(seq) != len(s):
        return False
    if not s <= ID_SET:
        return False
    return not any(pair <= s for pair in CONFLICT_PAIRS)


def route(ids) -> str:
    if not compatible(ids):
        raise ValueError("INCOMPATIBLE_OR_UNKNOWN_ID_SET")
    s = set(ids)
    if CONSTRAINED in s:
        return "CONSTRAINED_RESPONSE"
    if JSON_ID in s:
        return "JSON"
    if REPEAT in s:
        return "REPEAT_PROMPT"
    if TWO in s:
        return "TWO_RESPONSES"
    return "GENERAL"


def enumerate_compatible_sets() -> tuple[tuple[str, ...], ...]:
    out = []
    for k in range(1, MAX_GENERATED_INSTRUCTIONS + 1):
        for ids in combinations(IDS, k):
            if compatible(ids):
                out.append(ids)
    return tuple(out)


def verify() -> dict:
    sets = enumerate_compatible_sets()
    by_size = Counter(map(len, sets))
    by_route = Counter(route(x) for x in sets)

    expected_size = {1: 24, 2: 189, 3: 980, 4: 3514, 5: 9043}
    expected_route = {
        "CONSTRAINED_RESPONSE": 1,
        "JSON": 4,
        "REPEAT_PROMPT": 8,
        "TWO_RESPONSES": 16,
        "GENERAL": 13721,
    }

    if len(sets) != 13750:
        raise RuntimeError("HISTORICAL24_COMPATIBLE_SET_COUNT_DRIFT")
    if dict(sorted(by_size.items())) != expected_size:
        raise RuntimeError("HISTORICAL24_CARDINALITY_DISTRIBUTION_DRIFT")
    if dict(by_route) != expected_route:
        raise RuntimeError("HISTORICAL24_ROUTE_DISTRIBUTION_DRIFT")

    active15_sets = {
        frozenset(x)
        for x in __import__(
            "canonical.runtime.livebench_legacy15_composition_archetypes_v1",
            fromlist=["enumerate_compatible_sets"],
        ).enumerate_compatible_sets()
    }
    historical_sets = {frozenset(x) for x in sets}
    if not active15_sets < historical_sets:
        raise RuntimeError("ACTIVE15_STRUCTURAL_SPACE_NOT_STRICT_SUBSET")

    with_extra = sum(
        1
        for ids in sets
        if any(i in set(scope.UNCOVERED_GENERATOR9) for i in ids)
    )
    if with_extra != 12822:
        raise RuntimeError("EXTRA9_STRUCTURAL_SET_COUNT_DRIFT")

    return {
        "schema": SCHEMA,
        "status": "PASS__13750_CONSERVATIVE_HISTORICAL24_STRUCTURAL_SETS",
        "generator_id_count": len(IDS),
        "max_generated_instructions": MAX_GENERATED_INSTRUCTIONS,
        "compatible_structural_set_count": len(sets),
        "counts_by_size": dict(sorted(by_size.items())),
        "counts_by_route": dict(sorted(by_route.items())),
        "active15_structural_set_count": len(active15_sets),
        "active15_is_strict_structural_subset": True,
        "sets_containing_at_least_one_extra9_family": with_extra,
        "structural_expansion_factor_vs_active15": len(sets) / len(active15_sets),
        "terminal_rows_read": 0,
        "case_frequencies_read": 0,
        "acceptance_credit": False,
        "next_load_bearing_target": (
            "CONSTRUCT_AND_EXACT_POSTVALIDATE_POINTWISE_OPTIMAL_RESPONSES_FOR_"
            "THE_13750_STRUCTURAL_SUPERSET_USING_SLOT_SEMANTIC_QUOTIENTS"
        ),
    }


def run(args=None, root=None):
    return verify()


if __name__ == "__main__":
    import json

    print(json.dumps(verify(), indent=2, sort_keys=True))
