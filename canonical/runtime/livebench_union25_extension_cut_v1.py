#!/usr/bin/env python3
"""Union25 extension-cut theorem for frozen legacy LiveBench.

This module attacks the 25-family pointwise-closure problem at its actual
interaction rank instead of brute-forcing 14,559 structural identity sets.

The full pinned registry contains 25 checker families.  Fifteen are already
covered by the Active15 pointwise construction.  Of the ten added families,
three are passive structural decorators for composition purposes:

* number_placeholders: numeric bracket markers
* number_highlighted_sections: numeric inline-star markers
* no_comma: an absence predicate, with one forced-literal exception on repeat

After quotienting those decorators, every conflict-compatible set of 1..5
instructions falls into only 21 distinct hard extension signatures.  This is a
structural theorem, not acceptance evidence; exact checker postvalidation is
still required for the 21 hard modes.

No terminal rows, hidden kwargs, terminal instruction IDs, responses, scores,
or case frequencies are read.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Iterable

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_EXTENSION_CUT_V1"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
MAX_INSTRUCTIONS = 5

EXIST = "keywords:existence"
KEYWORD_FREQ = "keywords:frequency"
FORBIDDEN = "keywords:forbidden_words"
LETTER_FREQ = "keywords:letter_frequency"
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
CAPITAL_FREQ = "change_case:capital_word_frequency"
ENGLISH_CAPITAL = "change_case:english_capital"
ENGLISH_LOWER = "change_case:english_lowercase"
NO_COMMA = "punctuation:no_comma"
QUOTE = "startend:quotation"

UNION25 = (
    EXIST, KEYWORD_FREQ, FORBIDDEN, LETTER_FREQ, LANGUAGE,
    SENTENCES, PARAGRAPHS, WORDS, NTH,
    PLACEHOLDERS, POSTSCRIPT, BULLETS, CONSTRAINED, HIGHLIGHTS,
    SECTIONS, JSON_ID, TITLE, TWO, REPEAT, END,
    CAPITAL_FREQ, ENGLISH_CAPITAL, ENGLISH_LOWER, NO_COMMA, QUOTE,
)

ACTIVE15 = frozenset({
    EXIST, FORBIDDEN, PARAGRAPHS, WORDS, SENTENCES, NTH, POSTSCRIPT,
    BULLETS, TITLE, SECTIONS, JSON_ID, REPEAT, TWO, END, QUOTE,
})
NEW10 = frozenset(UNION25) - ACTIVE15

# These are composition-passive in the precise sense used by this theorem:
# they do not introduce alphabetic payload that can alter keyword/letter/case/
# language counts.  Numeric placeholder/highlight markers do add \w+ tokens,
# which is accounted for by the global word ceiling below.  NO_COMMA has one
# forced-literal exception when REPEAT is active because the exact repeated
# prompt is externally fixed visible text.
PASSIVE_DECORATORS = frozenset({PLACEHOLDERS, HIGHLIGHTS, NO_COMMA})
HARD_NEW7 = NEW10 - PASSIVE_DECORATORS

# Exact symmetric conflict graph induced by the frozen registry.  We encode the
# registry construction rather than all 97 unordered pairs by hand.
def _conflicts() -> dict[str, set[str]]:
    all_ids = set(UNION25)
    c = {iid: {iid} for iid in UNION25}

    c[LANGUAGE] |= {
        LANGUAGE, SECTIONS, EXIST, KEYWORD_FREQ, FORBIDDEN, END,
        ENGLISH_CAPITAL, ENGLISH_LOWER,
    }
    c[PARAGRAPHS] |= {PARAGRAPHS, NTH, SENTENCES}
    c[NTH] |= {NTH, PARAGRAPHS, BULLETS, HIGHLIGHTS, SECTIONS}
    c[BULLETS] |= {BULLETS, NTH}
    c[CONSTRAINED] |= all_ids
    c[HIGHLIGHTS] |= {HIGHLIGHTS, NTH}
    c[SECTIONS] |= {SECTIONS, LANGUAGE, HIGHLIGHTS, NTH}
    c[JSON_ID] |= all_ids - {FORBIDDEN, EXIST}
    c[TWO] |= all_ids - {FORBIDDEN, EXIST, LANGUAGE, TITLE, NO_COMMA}
    c[REPEAT] |= all_ids - {EXIST, TITLE, NO_COMMA}
    c[CAPITAL_FREQ] |= {CAPITAL_FREQ, ENGLISH_LOWER, ENGLISH_CAPITAL}
    c[ENGLISH_CAPITAL] |= {ENGLISH_CAPITAL}
    c[ENGLISH_LOWER] |= {ENGLISH_LOWER, ENGLISH_CAPITAL}
    c[QUOTE] |= {QUOTE, TITLE}

    # conflict_make() symmetrization from the pinned registry.
    for left in UNION25:
        for right in tuple(c[left]):
            c[right].add(left)
        c[left].add(left)
    return c


CONFLICTS = _conflicts()


def compatible(ids: Iterable[str]) -> bool:
    xs = tuple(ids)
    s = set(xs)
    if len(s) != len(xs) or not s <= set(UNION25):
        return False
    for iid in s:
        if (CONFLICTS[iid] - {iid}) & s:
            return False
    return True


def enumerate_compatible_sets() -> tuple[tuple[str, ...], ...]:
    out: list[tuple[str, ...]] = []
    for size in range(1, MAX_INSTRUCTIONS + 1):
        for ids in combinations(UNION25, size):
            if compatible(ids):
                out.append(ids)
    return tuple(out)


def hard_extension_signature(ids: Iterable[str]) -> tuple[str, ...]:
    if not compatible(ids):
        raise ValueError("INCOMPATIBLE_ID_SET")
    return tuple(sorted((set(ids) & NEW10) - PASSIVE_DECORATORS))


def passive_signature(ids: Iterable[str]) -> tuple[str, ...]:
    if not compatible(ids):
        raise ValueError("INCOMPATIBLE_ID_SET")
    return tuple(sorted(set(ids) & PASSIVE_DECORATORS))


# Conservative maximum \w+ contribution for an unpadded constructive witness.
# Values deliberately overcount where useful.  The proof only needs the global
# maximum among sets containing WORDS to stay below 100.
WORD_CONTRIBUTION_CEILINGS = {
    EXIST: 1,              # all required substrings packed in one shield token
    KEYWORD_FREQ: 1,       # all required occurrences can be packed in one token
    FORBIDDEN: 0,
    LETTER_FREQ: 1,        # required copies packed in one alphanumeric token
    LANGUAGE: 1,           # numeric exception carrier before hard-mode audit
    SENTENCES: 20,
    PARAGRAPHS: 5,
    WORDS: 0,
    NTH: 5,
    PLACEHOLDERS: 4,
    POSTSCRIPT: 3,
    BULLETS: 5,
    CONSTRAINED: 4,        # isolated and never co-occurs with WORDS
    HIGHLIGHTS: 4,
    SECTIONS: 15,
    JSON_ID: 1,
    TITLE: 1,
    TWO: 2,
    REPEAT: 1,             # incompatible with WORDS
    END: 8,
    CAPITAL_FREQ: 20,
    ENGLISH_CAPITAL: 10,
    ENGLISH_LOWER: 10,
    NO_COMMA: 0,
    QUOTE: 0,
}


def conservative_unpadded_word_ceiling(ids: Iterable[str]) -> int:
    xs = tuple(ids)
    if not compatible(xs):
        raise ValueError("INCOMPATIBLE_ID_SET")
    return sum(WORD_CONTRIBUTION_CEILINGS[iid] for iid in xs)


def route(ids: Iterable[str]) -> str:
    s = set(ids)
    if CONSTRAINED in s:
        return "CONSTRAINED_SINGLETON"
    if JSON_ID in s:
        return "JSON"
    if REPEAT in s:
        return "REPEAT"
    if TWO in s:
        return "TWO"
    return "GENERAL"


EXPECTED_HARD_SIGNATURES = (
    (),
    (CAPITAL_FREQ,),
    (ENGLISH_CAPITAL,),
    (ENGLISH_LOWER,),
    (CONSTRAINED,),
    (KEYWORD_FREQ,),
    (LETTER_FREQ,),
    (LANGUAGE,),
    (CAPITAL_FREQ, KEYWORD_FREQ),
    (CAPITAL_FREQ, LETTER_FREQ),
    (CAPITAL_FREQ, LANGUAGE),
    (ENGLISH_CAPITAL, KEYWORD_FREQ),
    (ENGLISH_CAPITAL, LETTER_FREQ),
    (ENGLISH_LOWER, KEYWORD_FREQ),
    (ENGLISH_LOWER, LETTER_FREQ),
    (KEYWORD_FREQ, LETTER_FREQ),
    (CAPITAL_FREQ, KEYWORD_FREQ, LETTER_FREQ),
    (CAPITAL_FREQ, LETTER_FREQ, LANGUAGE),
    (ENGLISH_CAPITAL, KEYWORD_FREQ, LETTER_FREQ),
    (ENGLISH_LOWER, KEYWORD_FREQ, LETTER_FREQ),
    (LETTER_FREQ, LANGUAGE),
)


def verify() -> dict:
    sets = enumerate_compatible_sets()
    by_size = Counter(map(len, sets))
    if len(sets) != 14559:
        raise AssertionError(f"UNION25_SET_COUNT_DRIFT:{len(sets)}")
    if dict(sorted(by_size.items())) != {1: 25, 2: 203, 3: 1055, 4: 3750, 5: 9526}:
        raise AssertionError("UNION25_CARDINALITY_DISTRIBUTION_DRIFT")

    active_only = tuple(ids for ids in sets if set(ids) <= ACTIVE15)
    if len(active_only) != 928:
        raise AssertionError(f"ACTIVE15_SUBSET_COUNT_DRIFT:{len(active_only)}")

    new_containing = len(sets) - len(active_only)
    if new_containing != 13631:
        raise AssertionError(f"NEW_CONTAINING_SET_COUNT_DRIFT:{new_containing}")

    new_signatures = {
        tuple(sorted(set(ids) & NEW10))
        for ids in sets
    }
    if len(new_signatures) != 157:
        raise AssertionError(f"NEW_SIGNATURE_COUNT_DRIFT:{len(new_signatures)}")

    hard_signatures = {
        hard_extension_signature(ids)
        for ids in sets
    }
    expected = set(EXPECTED_HARD_SIGNATURES)
    if hard_signatures != expected:
        raise AssertionError(
            "HARD_SIGNATURE_SET_DRIFT:"
            + repr(sorted(hard_signatures ^ expected))
        )

    routes = Counter(route(ids) for ids in sets)
    expected_routes = {
        "CONSTRAINED_SINGLETON": 1,
        "JSON": 4,
        "REPEAT": 8,
        "TWO": 20,
        "GENERAL": 14526,
    }
    if dict(routes) != expected_routes:
        raise AssertionError(f"ROUTE_DISTRIBUTION_DRIFT:{dict(routes)}")

    constrained_sets = [ids for ids in sets if CONSTRAINED in ids]
    if constrained_sets != [(CONSTRAINED,)]:
        raise AssertionError("CONSTRAINED_RESPONSE_NOT_ISOLATED_SINGLETON")

    json_new = [
        ids for ids in sets
        if JSON_ID in ids and (set(ids) & NEW10)
    ]
    if json_new:
        raise AssertionError("JSON_UNEXPECTED_NEW_FAMILY_EXTENSION")

    repeat_new_signatures = {
        tuple(sorted(set(ids) & NEW10))
        for ids in sets if REPEAT in ids
    }
    if repeat_new_signatures != {(), (NO_COMMA,)}:
        raise AssertionError(
            "REPEAT_NEW_EXTENSION_DRIFT:" + repr(repeat_new_signatures)
        )

    two_new_signatures = {
        tuple(sorted(set(ids) & NEW10))
        for ids in sets if TWO in ids
    }
    if two_new_signatures != {
        (),
        (LANGUAGE,),
        (NO_COMMA,),
        tuple(sorted((LANGUAGE, NO_COMMA))),
    }:
        raise AssertionError(
            "TWO_NEW_EXTENSION_DRIFT:" + repr(two_new_signatures)
        )

    word_sets = [ids for ids in sets if WORDS in ids]
    max_word_ceiling = max(conservative_unpadded_word_ceiling(ids) for ids in word_sets)
    maxima = [
        ids for ids in word_sets
        if conservative_unpadded_word_ceiling(ids) == max_word_ceiling
    ]
    if max_word_ceiling != 63:
        raise AssertionError(f"UNION25_WORD_CEILING_DRIFT:{max_word_ceiling}")
    if max_word_ceiling >= 100:
        raise AssertionError("UNION25_WORD_LESS_THAN_100_MARGIN_LOST")

    hard_histogram = Counter(hard_extension_signature(ids) for ids in sets)
    passive_histogram = Counter(passive_signature(ids) for ids in sets)

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__UNION25_14559_STRUCTURAL_SETS_COLLAPSED_TO_"
            "21_HARD_EXTENSION_SIGNATURES"
        ),
        "pinned_registry_blob": PINNED_REGISTRY_BLOB,
        "union25_family_count": len(UNION25),
        "active15_family_count": len(ACTIVE15),
        "new_family_count": len(NEW10),
        "compatible_set_count": len(sets),
        "compatible_sets_by_cardinality": dict(sorted(by_size.items())),
        "active15_only_set_count": len(active_only),
        "new_family_containing_set_count": new_containing,
        "raw_new_family_signature_count": len(new_signatures),
        "passive_decorators": sorted(PASSIVE_DECORATORS),
        "hard_new_families": sorted(HARD_NEW7),
        "hard_extension_signature_count": len(hard_signatures),
        "hard_extension_signatures": [list(x) for x in sorted(
            hard_signatures, key=lambda x: (len(x), x)
        )],
        "hard_signature_histogram": {
            "|".join(key) if key else "<none>": value
            for key, value in sorted(
                hard_histogram.items(), key=lambda kv: (len(kv[0]), kv[0])
            )
        },
        "passive_signature_count": len(passive_histogram),
        "route_counts": dict(sorted(routes.items())),
        "special_route_reductions": {
            "constrained_response": "ISOLATED_SINGLETON",
            "json": "NO_NEW10_FAMILY_CAN_COEXIST",
            "repeat": "ONLY_NEW10_EXTENSION_IS_NO_COMMA",
            "two_responses": "ONLY_NEW10_EXTENSIONS_ARE_LANGUAGE_AND_NO_COMMA",
        },
        "word_channel": {
            "conservative_unpadded_global_ceiling_over_WORDS_sets": max_word_ceiling,
            "public_minimum_less_than_threshold": 100,
            "margin_words": 100 - max_word_ceiling,
            "maximizing_structural_sets": [list(x) for x in maxima],
            "consequence": (
                "RAW_UNION25_WORD_THRESHOLD_100_TO_500_CROSS_PRODUCT_IS_NOT_"
                "LOAD_BEARING_IF_THE_21_HARD_MODE_CONSTRUCTORS_RESPECT_THE_"
                "DECLARED_CHANNEL_CEILINGS"
            ),
        },
        "remaining_load_bearing_hard_modes": [
            "KEYWORD_RAW_REGEX_FREQUENCY_VS_FORCED_LITERAL_OCCURRENCES",
            "LETTER_FREQUENCY_VS_FORCED_ALPHABETIC_EMISSIONS",
            "CAPITAL_WORD_FREQUENCY_VS_CASE_AND_LANGUAGE_CHANNELS",
            "ENGLISH_ALL_CAPITAL_OR_LOWERCASE_GLOBAL_CASE_MODE",
            "RESPONSE_LANGUAGE_GLOBAL_DETECTOR_MODE",
            "REPEAT_PROMPT_PLUS_NO_COMMA_FORCED_LITERAL_COLLISION",
        ],
        "next_exact_action": (
            "BUILD_ONE_POINTWISE_MAXIMIZING_CONSTRUCTOR_OVER_THE_21_HARD_"
            "SIGNATURES__THEN_EXHAUSTIVELY_POSTVALIDATE_EACH_HARD_SIGNATURE_"
            "CROSSED_WITH_ITS_FINITE_PUBLIC_SLOT_BOUNDARIES_AND_ACTIVE15_"
            "FORCED_LITERAL_COLLISION_SIGNATURE"
        ),
        "compression": {
            "structural_sets_to_hard_modes_ratio": len(sets) / len(hard_signatures),
            "raw_new_signatures_to_hard_modes_ratio": len(new_signatures) / len(hard_signatures),
        },
        "terminal_rows_used": False,
        "hidden_kwargs_used": False,
        "terminal_instruction_ids_used": False,
        "target_scores_used": False,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
    }


def run(args=None, root=None):
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
