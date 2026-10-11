#!/usr/bin/env python3
"""Static certificate for the contamination-safe active15 constructive frontier.

This module uses only public generator/checker constants already pinned by the
Brain.  It does not read benchmark rows, prompts, hidden kwargs, responses, or
scores.  The claim is deliberately narrower than acceptance: after the V1
constructive rewrites, all structural archetypes reduce to three irreducible
parameter-level contradiction classes.  The probability bound is under the
public generator random-draw model and is NOT a score on the frozen 200 rows.
"""
from __future__ import annotations

from math import comb
from typing import Any

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_SATISFIABLE_TOTALITY_CERTIFICATE_V1"

FROZEN_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
FROZEN_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
FROZEN_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
HISTORICAL_GENERATOR_COMMIT = "686be1e78a0ba8036d7e355bc406e1a265da5292"
HISTORICAL_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"

WORD_LIST_SIZE = 1525
FORBIDDEN_SAMPLE_SIZE = 5
MAX_SENTENCE_THRESHOLD = 20
MIN_WORD_THRESHOLD = 100
MAX_WORD_THRESHOLD = 500
MAX_SENTENCE_THRESHOLD_VALUE = 20
MAX_SECTIONS = 5
MAX_BULLETS = 5
MAX_PARAGRAPHS = 5
MAX_INSTRUCTIONS = 5

# Exact end-phrase words which are members of the frozen public WORD_LIST.
SHORT_END_WORDS_IN_POOL = 1       # "other"
LONG_END_WORDS_IN_POOL = 3        # "anything", "can", "help"


def _hit_probability(marked: int) -> float:
    """Probability a 5-word forbidden sample hits >=1 of marked pool words."""
    n = WORD_LIST_SIZE
    k = FORBIDDEN_SAMPLE_SIZE
    if marked <= 0:
        return 0.0
    return 1.0 - comb(n - marked, k) / comb(n, k)


def probability_bounds() -> dict[str, float]:
    # A random NumberOfSentences instance is "< 1" with probability
    # P(relation=less-than) * P(threshold=1) = 1/2 * 1/20.
    p_sentence_lt1 = 1.0 / (2 * MAX_SENTENCE_THRESHOLD)

    # ParagraphFirstWordCheck draws one word from the same 1525-word pool.
    # A simultaneously present five-word forbidden sample hits it with 5/N.
    p_nth_first_forbidden = FORBIDDEN_SAMPLE_SIZE / WORD_LIST_SIZE

    # EndChecker chooses one of two fixed phrases.  For a row-independent lower
    # bound we use the worse phrase, which contains three pool words.
    p_end_forbidden_worst = _hit_probability(LONG_END_WORDS_IN_POOL)

    # Conservative union bound.  It intentionally does not subtract overlaps.
    p_irreducible_contradiction_upper = (
        p_sentence_lt1
        + p_nth_first_forbidden
        + p_end_forbidden_worst
    )
    p_satisfiable_lower = 1.0 - p_irreducible_contradiction_upper

    return {
        "sentence_lt1_upper": p_sentence_lt1,
        "nth_first_forbidden_upper": p_nth_first_forbidden,
        "end_phrase_forbidden_worst_upper": p_end_forbidden_worst,
        "irreducible_contradiction_union_upper": p_irreducible_contradiction_upper,
        "satisfiable_parameter_draw_lower": p_satisfiable_lower,
    }


def verify() -> dict[str, Any]:
    shape = archetypes.verify()
    probs = probability_bounds()

    if shape["compatible_set_count"] != 928 or shape["archetype_count"] != 7:
        raise RuntimeError("ACTIVE15_SHAPE_DRIFT")
    if not (probs["satisfiable_parameter_draw_lower"] > 0.96):
        raise RuntimeError("SATISFIABLE_LOWER_BOUND_REGRESSION")
    if not (MAX_SENTENCE_THRESHOLD_VALUE + 2 * MAX_SECTIONS + 8 + 5 < MIN_WORD_THRESHOLD):
        # Conservative four-companion word budget with a NumberOfWords slot:
        # <=20 sentence carrier words + <=10 section words + <=8 end words
        # + <=5 existence carriers = 43 < minimum strict upper word bound 100.
        raise RuntimeError("WORD_UPPER_BOUND_CONSTRUCTION_NO_LONGER_TRIVIAL")

    return {
        "schema": SCHEMA,
        "status": "PASS_STATIC_REDUCTION__EXACT_CHECKER_REPLAY_STILL_REQUIRED",
        "bindings": {
            "frozen_livebench_commit": FROZEN_LIVEBENCH_COMMIT,
            "frozen_instructions_blob": FROZEN_INSTRUCTIONS_BLOB,
            "frozen_registry_blob": FROZEN_REGISTRY_BLOB,
            "historical_generator_commit": HISTORICAL_GENERATOR_COMMIT,
            "historical_generator_blob": HISTORICAL_GENERATOR_BLOB,
            "archetype_schema": archetypes.SCHEMA,
        },
        "structural_domain": shape,
        "constructive_lemmas": [
            "REQUIRED_KEYWORD_K_TO_K0_PRESERVES_REGEX_SUBSTRING_AND_BREAKS_WHOLE_WORD_FORBIDDEN_COLLISION",
            "JSON_STRING_WITNESS_REMOVES_FIXED_ALPHABETIC_OBJECT_KEY",
            "TWO_RESPONSE_NUMERIC_DIFFERENTIATORS_REMOVE_FIXED_WORD_COLLISIONS",
            "SECTION_X_TO_SECTIONX_DIGIT_PRESERVES_OPTIONAL_SPACE_SECTION_REGEX_AND_BREAKS_SECTION_WHOLE_WORD_BOUNDARY",
            "POSTSCRIPT_MARKER_EMBEDDING_WITHOUT_WHITESPACE_AFTER_PERIODS_PRESERVES_EXACT_POSTSCRIPT_REGEX_AND_AVOIDS_EXTRA_SENTENCE_BOUNDARY",
            "STRICT_WORD_UPPER_BOUND_HAS_CONSERVATIVE_BASE_BUDGET_LT_100_FOR_MAX_FIVE_INSTRUCTIONS",
            "WORD_LOWER_BOUND_IS_MONOTONE_AND_CAN_BE_PADDED_BEFORE_EXACT_END_SUFFIX",
        ],
        "irreducible_parameter_contradictions": [
            {
                "id": "SENTENCE_LT1_WITH_NONEMPTY_REQUIREMENT",
                "reason": "less-than one sentence requires a zero-sentence response while any positive-output companion requires nonempty output",
            },
            {
                "id": "NTH_FIRST_WORD_IS_FORBIDDEN",
                "reason": "the exact required first word creates the same whole-word match forbidden by ForbiddenWords",
            },
            {
                "id": "EXACT_END_PHRASE_CONTAINS_FORBIDDEN_WORD",
                "reason": "EndChecker requires the literal suffix while ForbiddenWords rejects the same whole word",
            },
        ],
        "generator_model_probability_bounds": probs,
        "terminal_case_content_read": 0,
        "terminal_case_metadata_read": 0,
        "terminal_cases_consumed": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit": False,
        "capability_credit": False,
        "promotion_authority": False,
        "hard_nonclaim": (
            "THE >96% VALUE IS A PUBLIC-GENERATOR PARAMETER-DRAW LOWER BOUND, "
            "NOT A MEASUREMENT OR DETERMINISTIC LOWER BOUND ON THE FROZEN 200 ROWS."
        ),
    }


def run(args=None, root=None):
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
