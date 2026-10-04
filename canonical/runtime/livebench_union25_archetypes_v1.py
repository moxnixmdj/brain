#!/usr/bin/env python3
"""Exact structural quotient for the frozen public LiveBench registry25.

This reifies the pinned registry conflict graph without importing LiveBench.
It exists to turn the apparent 25-family combinatorial explosion into exact
structural classes that can be attacked compositionally.

No target rows, hidden kwargs, frequencies, responses or scores are used.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_ARCHETYPES_V1"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"

EXIST = "keywords:existence"
KEYWORD_FREQUENCY = "keywords:frequency"
FORBIDDEN = "keywords:forbidden_words"
LETTER_FREQUENCY = "keywords:letter_frequency"
LANGUAGE = "language:response_language"
SENTENCES = "length_constraints:number_sentences"
PARAGRAPHS = "length_constraints:number_paragraphs"
WORDS = "length_constraints:number_words"
NTH = "length_constraints:nth_paragraph_first_word"
PLACEHOLDERS = "detectable_content:number_placeholders"
POSTSCRIPT = "detectable_content:postscript"
BULLETS = "detectable_format:number_bullet_lists"
CONSTRAINED = "detectable_format:constrained_response"
HIGHLIGHTS = "detectable_format:number_highlighted_sections"
SECTIONS = "detectable_format:multiple_sections"
JSON_ID = "detectable_format:json_format"
TITLE = "detectable_format:title"
TWO = "combination:two_responses"
REPEAT = "combination:repeat_prompt"
END = "startend:end_checker"
CAPITAL_FREQUENCY = "change_case:capital_word_frequency"
ENGLISH_CAPITAL = "change_case:english_capital"
ENGLISH_LOWERCASE = "change_case:english_lowercase"
NO_COMMA = "punctuation:no_comma"
QUOTE = "startend:quotation"

ALL_IDS = (
    EXIST,
    KEYWORD_FREQUENCY,
    FORBIDDEN,
    LETTER_FREQUENCY,
    LANGUAGE,
    SENTENCES,
    PARAGRAPHS,
    WORDS,
    NTH,
    PLACEHOLDERS,
    POSTSCRIPT,
    BULLETS,
    CONSTRAINED,
    HIGHLIGHTS,
    SECTIONS,
    JSON_ID,
    TITLE,
    TWO,
    REPEAT,
    END,
    CAPITAL_FREQUENCY,
    ENGLISH_CAPITAL,
    ENGLISH_LOWERCASE,
    NO_COMMA,
    QUOTE,
)

ACTIVE15 = frozenset({
    EXIST,
    FORBIDDEN,
    SENTENCES,
    PARAGRAPHS,
    WORDS,
    NTH,
    POSTSCRIPT,
    BULLETS,
    SECTIONS,
    JSON_ID,
    TITLE,
    TWO,
    REPEAT,
    END,
    QUOTE,
})

EXTRA10 = frozenset(ALL_IDS) - ACTIVE15
MAX_GENERATED_INSTRUCTIONS = 5

EXPECTED_NONSELF_CONFLICT_PAIR_COUNT = 97
EXPECTED_COMPATIBLE_BY_CARDINALITY = {1: 25, 2: 203, 3: 1055, 4: 3750, 5: 9526}
EXPECTED_COMPATIBLE_TOTAL = 14559
EXPECTED_ACTIVE15_TOTAL = 928
EXPECTED_EXTRA_BEARING_TOTAL = 13631
EXPECTED_DISTINCT_EXTRA_SIGNATURES = 156


def _conflicts() -> dict[str, set[str]]:
    c = {iid: {iid} for iid in ALL_IDS}

    c[LANGUAGE] |= {
        SECTIONS,
        EXIST,
        KEYWORD_FREQUENCY,
        FORBIDDEN,
        END,
        ENGLISH_CAPITAL,
        ENGLISH_LOWERCASE,
    }
    c[PARAGRAPHS] |= {NTH, SENTENCES}
    c[NTH] |= {PARAGRAPHS, BULLETS, HIGHLIGHTS, SECTIONS}
    c[CONSTRAINED] = set(ALL_IDS)
    c[SECTIONS] |= {LANGUAGE, HIGHLIGHTS, NTH}
    c[JSON_ID] = set(ALL_IDS) - {FORBIDDEN, EXIST}
    c[TWO] = set(ALL_IDS) - {
        FORBIDDEN,
        EXIST,
        LANGUAGE,
        TITLE,
        NO_COMMA,
    }
    c[REPEAT] = set(ALL_IDS) - {EXIST, TITLE, NO_COMMA}
    c[CAPITAL_FREQUENCY] |= {
        ENGLISH_LOWERCASE,
        ENGLISH_CAPITAL,
    }
    c[ENGLISH_LOWERCASE] |= {ENGLISH_CAPITAL}
    c[QUOTE] |= {TITLE}

    # Frozen conflict_make() makes the relation symmetric and adds self edges.
    for a in tuple(ALL_IDS):
        for b in tuple(c[a]):
            c[b].add(a)
            c[a].add(a)
    return c


CONFLICTS = _conflicts()


def compatible(ids: Sequence[str]) -> bool:
    values = tuple(ids)
    if len(values) != len(set(values)):
        return False
    if any(iid not in CONFLICTS for iid in values):
        return False
    return all(b not in CONFLICTS[a] for a, b in combinations(values, 2))


def enumerate_compatible_sets() -> tuple[tuple[str, ...], ...]:
    out: list[tuple[str, ...]] = []
    for n in range(1, MAX_GENERATED_INSTRUCTIONS + 1):
        for ids in combinations(ALL_IDS, n):
            if compatible(ids):
                out.append(ids)
    return tuple(out)


def route(ids: Sequence[str]) -> str:
    s = set(ids)
    if CONSTRAINED in s:
        return "CONSTRAINED_SINGLETON"
    if JSON_ID in s:
        return "JSON"
    if REPEAT in s:
        return "REPEAT_PROMPT"
    if TWO in s:
        return "TWO_RESPONSES"
    return "GENERAL"


def extra_signature(ids: Sequence[str]) -> tuple[str, ...]:
    s = set(ids)
    return tuple(iid for iid in ALL_IDS if iid in s and iid in EXTRA10)


def verify() -> dict[str, Any]:
    nonself_pairs = {
        tuple(sorted((a, b)))
        for a in ALL_IDS
        for b in CONFLICTS[a]
        if a != b
    }
    if len(nonself_pairs) != EXPECTED_NONSELF_CONFLICT_PAIR_COUNT:
        raise AssertionError("REGISTRY_CONFLICT_PAIR_COUNT_DRIFT")

    sets = enumerate_compatible_sets()
    by_cardinality = dict(sorted(Counter(map(len, sets)).items()))
    if by_cardinality != EXPECTED_COMPATIBLE_BY_CARDINALITY:
        raise AssertionError("REGISTRY_COMPATIBLE_CARDINALITY_DRIFT")
    if len(sets) != EXPECTED_COMPATIBLE_TOTAL:
        raise AssertionError("REGISTRY_COMPATIBLE_TOTAL_DRIFT")

    active = [ids for ids in sets if set(ids) <= ACTIVE15]
    if len(active) != EXPECTED_ACTIVE15_TOTAL:
        raise AssertionError("ACTIVE15_EMBEDDED_COUNT_DRIFT")

    extra = [ids for ids in sets if set(ids) & EXTRA10]
    if len(extra) != EXPECTED_EXTRA_BEARING_TOTAL:
        raise AssertionError("EXTRA_BEARING_COUNT_DRIFT")

    signatures = Counter(extra_signature(ids) for ids in extra)
    if len(signatures) != EXPECTED_DISTINCT_EXTRA_SIGNATURES:
        raise AssertionError("EXTRA_SIGNATURE_COUNT_DRIFT")

    route_counts_all = Counter(route(ids) for ids in sets)
    route_counts_extra = Counter(route(ids) for ids in extra)

    # Special-route extra-bearing structures are tiny; almost the entire union25
    # delta belongs to a single GENERAL constructor regime.
    if route_counts_extra != Counter({
        "GENERAL": 13614,
        "TWO_RESPONSES": 12,
        "REPEAT_PROMPT": 4,
        "CONSTRAINED_SINGLETON": 1,
    }):
        raise AssertionError("EXTRA_ROUTE_PARTITION_DRIFT")

    extra_cardinality = Counter(len(extra_signature(ids)) for ids in extra)

    return {
        "schema": SCHEMA,
        "status": "PASS__UNION25_STRUCTURAL_EXPLOSION_REDUCED_EXACTLY",
        "pinned_registry_blob": PINNED_REGISTRY_BLOB,
        "registry_instruction_count": len(ALL_IDS),
        "nonself_conflict_pair_count": len(nonself_pairs),
        "compatible_by_cardinality": by_cardinality,
        "compatible_total": len(sets),
        "embedded_active15_total": len(active),
        "extra_bearing_total": len(extra),
        "distinct_extra10_signatures": len(signatures),
        "extra_instruction_count_histogram": dict(sorted(extra_cardinality.items())),
        "route_counts_all": dict(route_counts_all),
        "route_counts_extra_bearing": dict(route_counts_extra),
        "reduction": {
            "raw_extra_bearing_structures": len(extra),
            "extra_family_signatures": len(signatures),
            "special_route_extra_structures": (
                route_counts_extra["TWO_RESPONSES"]
                + route_counts_extra["REPEAT_PROMPT"]
                + route_counts_extra["CONSTRAINED_SINGLETON"]
            ),
            "general_route_extra_structures": route_counts_extra["GENERAL"],
        },
        "next_load_bearing_problem": (
            "PROVE_POINTWISE_COMPLETE_COMPOSITION_FOR_THE_156_EXTRA10_SIGNATURES_"
            "WITH_ACTIVE15_NEUTRAL_CONTEXT_FACTORED_OUT"
        ),
        "terminal_rows_used": False,
        "hidden_kwargs_used": False,
        "target_scores_used": False,
        "acceptance_credit": False,
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
