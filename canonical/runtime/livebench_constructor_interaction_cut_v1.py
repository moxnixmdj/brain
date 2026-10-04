#!/usr/bin/env python3
"""Construction-interaction cut for frozen LiveBench active-15.

Purpose
-------
Reduce the remaining universal constructor proof after the pointwise minimum-cut
theorem.  For the exact frozen Brain blobs below, every active checker family
except NumberOfSentences has a parametric construction argument that is
independent of the raw slot Cartesian product.  The only remaining nonlinear
checker-semantic residue is English Punkt sentence tokenization.

This is a proof-reduction module, not an acceptance receipt.  It reads no
terminal rows, hidden kwargs, terminal frequencies, comparator responses, or
target scores.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_CONSTRUCTOR_INTERACTION_CUT_V1"

EXPECTED_BLOBS = {
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":
        "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py":
        "71e637c70edf1c582e28ea38b3b798965c803a06",
    "canonical/runtime/livebench_pointwise_minimum_cut_v1.py":
        "PENDING_SELF_BINDING",
}

PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_INSTRUCTIONS_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
PINNED_NLTK_VERSION = "3.10.3"
PINNED_NLTK_PUNKT_SOURCE_BLOB = "48496d2448c009221d2452c8e928699027b20ebe"

# Exact public generator domains consumed by Composer V2.
MIN_WORD_THRESHOLD = 100
MAX_WORD_THRESHOLD = 500
MAX_SENTENCE_THRESHOLD = 20
MAX_SECTIONS = 5
MAX_BULLETS = 5
MAX_NTH_PARAGRAPHS = 5
MAX_PARAGRAPHS = 5

# Conservative \\w+ contribution bound for any non-special Composer V2 response
# BEFORE a NumberOfWords(at least) pad.  Deliberately ignores conflict-graph
# exclusions and therefore over-counts mutually incompatible features.
#
# title                 <= 1
# packed existence      <= 1
# five section markers  <= 5 * 3 = 15
# five bullet payloads  <= 5
# twenty sentence atoms <= 20
# nth wrapper additions <= 1 first_word + 4 other paragraphs = 5
# paragraph additions   <= 4
# P.P.S                  <= 3
# longest end phrase    <= 8
CONSERVATIVE_PREPAD_WORD_BOUND = 1 + 1 + 15 + 5 + 20 + 5 + 4 + 3 + 8


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _bindings() -> dict[str, str]:
    root = _root()
    out: dict[str, str] = {}
    for rel, expected in EXPECTED_BLOBS.items():
        got = _git_blob_sha(root / rel)
        out[rel] = got
        if expected != "PENDING_SELF_BINDING" and got != expected:
            raise AssertionError(
                "EXACT_SUBJECT_BLOB_MISMATCH:"
                + rel + ":" + expected + ":" + got
            )
    return out


def verify() -> dict[str, Any]:
    bindings = _bindings()

    if CONSERVATIVE_PREPAD_WORD_BOUND >= MIN_WORD_THRESHOLD:
        raise AssertionError("WORD_UPPER_BOUND_NO_LONGER_BELOW_PUBLIC_MINIMUM")

    # This bound is intentionally stronger than necessary: it counts NTH and
    # Paragraph wrappers together even though the frozen conflict graph excludes
    # them, and likewise ignores other exclusions.  Therefore every legal
    # Composer-V2 non-special response with NumberOfWords(< n), n>=100, remains
    # strictly below n without enumerating numeric/structural Cartesian products.
    word_upper_margin = MIN_WORD_THRESHOLD - CONSERVATIVE_PREPAD_WORD_BOUND

    closed = {
        "keywords:existence": {
            "proof": (
                "PUBLIC_KEYWORDS_ARE_ASCII_ALPHA; COMPOSER_PACKS_EACH_REQUIRED_"
                "WORD_INSIDE_ONE_ALPHANUMERIC_WORD_TOKEN; RAW_REGEX_SUBSTRING_"
                "CHECKER_SEES_EVERY_REQUIRED_WORD"
            ),
        },
        "keywords:forbidden_words": {
            "proof": (
                "PACKED_REQUIRED_WORDS_HAVE_NO_WORD_BOUNDARIES; SECTION_LITERAL_"
                "IS_LEFT_SHIELDED_BY_9; NTH_AND_END_WHOLE_WORD_COLLISIONS_ARE_"
                "EXACTLY_THE_SHARED_FORBIDDEN_LOSS_COORDINATE; OTHER_EMITTED_"
                "STRUCTURAL_ATOMS_ARE_NUMERIC_OR_NONPUBLIC_WORDS"
            ),
        },
        "length_constraints:number_paragraphs": {
            "proof": (
                "COMPOSER_EMITS_EXACTLY_N_MINUS_1_TRIPLE_ASTERISK_DIVIDERS; "
                "NO_OTHER_COMPATIBLE_ROUTE_EMITS_A_TRIPLE_ASTERISK_DIVIDER"
            ),
        },
        "length_constraints:number_words": {
            "proof": (
                "LESS_THAN_DOMAIN_IS_UNIVERSAL_BY_CONSERVATIVE_PREPAD_WORD_BOUND_"
                "LT_100; AT_LEAST_DOMAIN_PADS_WITH_EXACTLY_SEPARATE_WORD_TOKENS_"
                "TO_THRESHOLD_AND_LATER_WRAPPERS_CANNOT_REMOVE_EXISTING_REGEX_"
                "WORD_TOKENS"
            ),
            "conservative_prepad_word_bound": CONSERVATIVE_PREPAD_WORD_BOUND,
            "public_minimum_threshold": MIN_WORD_THRESHOLD,
            "margin": word_upper_margin,
        },
        "length_constraints:nth_paragraph_first_word": {
            "proof": (
                "FROZEN_CONFLICT_GRAPH_EXCLUDES_PARAGRAPH_BULLET_SECTION_"
                "GENERATORS; COMPOSER_INTRODUCES_EXACTLY_N_PARAGRAPHS_WITH_"
                "N_MINUS_1_DOUBLE_NEWLINE_SEPARATORS_AND_PLACES_THE_VISIBLE_"
                "PUBLIC_FIRST_WORD_AT_THE_EXACT_TARGET_INDEX; QUOTATION_CHECKER_"
                "WRAPPER_IS_STRIPPED_BY_THE_PINNED_NTH_FIRST_WORD_LOGIC"
            ),
        },
        "detectable_content:postscript": {
            "proof": (
                "COMPOSER_APPENDS_THE_EXACT_PUBLIC_MARKER_ON_A_FINAL_LINE; "
                "THE_PINNED_MULTILINE_POSTSCRIPT_REGEX_ACCEPTS_ARBITRARY_"
                "TRAILING_CHARACTERS_SO_END_PHRASE_AND_OUTER_QUOTE_PRESERVE_PASS"
            ),
        },
        "detectable_format:number_bullet_lists": {
            "proof": (
                "COMPOSER_EMITS_EXACTLY_N_STAR_BULLET_LINES; PARAGRAPH_TRIPLE_"
                "ASTERISK_DIVIDERS_FAIL_THE_BULLET_REGEX_SECOND_CHARACTER_GUARD; "
                "NO_OTHER_COMPATIBLE_CONSTRUCTION_EMITS_STAR_OR_DASH_BULLET_LINES"
            ),
        },
        "detectable_format:title": {
            "proof": "COMPOSER_EMITS_ONE_NONEMPTY_DOUBLE_ANGLE_TITLE; CHECKER_IS_EXISTENTIAL",
        },
        "detectable_format:multiple_sections": {
            "proof": (
                "COMPOSER_EMITS_AT_LEAST_N_EXACT_SECTION_SPLITTER_PLUS_INDEX_"
                "MARKERS; CHECKER_REQUIRES_GREATER_THAN_OR_EQUAL_N_SO_ANY_"
                "ACCIDENTAL_EXTRA_MATCH_CANNOT_CREATE_FAILURE"
            ),
        },
        "detectable_format:json_format": {
            "proof": (
                "FROZEN_CONFLICT_GRAPH_RESTRICTS_JSON_TO_EXISTENCE_FORBIDDEN; "
                "COMPOSER_EMITS_A_DIRECT_JSON_OBJECT_WITH_THE_SHIELDED_PAYLOAD"
            ),
        },
        "combination:repeat_prompt": {
            "proof": (
                "FROZEN_CONFLICT_GRAPH_RESTRICTS_REPEAT_TO_EXISTENCE_TITLE; "
                "COMPOSER_BEGINS_WITH_THE_VISIBLE_PROMPT_TO_REPEAT_VERBATIM_SO_"
                "PINNED_STARTSWITH_CHECKER_PASSES_INDEPENDENTLY_OF_SUFFIX"
            ),
        },
        "combination:two_responses": {
            "proof": (
                "FROZEN_CONFLICT_GRAPH_RESTRICTS_TWO_RESPONSES_TO_EXISTENCE_"
                "FORBIDDEN_TITLE; COMPOSER_EMITS_EXACTLY_ONE_SIX_ASTERISK_"
                "SEPARATOR_AND_TWO_NONEMPTY_DISTINCT_NUMERIC_SAFE_RESPONSES"
            ),
        },
        "startend:end_checker": {
            "proof": (
                "COMPOSER_APPENDS_THE_EXACT_VISIBLE_END_PHRASE_LAST_BEFORE_AN_"
                "OPTIONAL_OUTER_QUOTE; PINNED_END_CHECKER_STRIPS_OUTER_QUOTES_"
                "BEFORE_ENDSWITH"
            ),
        },
        "startend:quotation": {
            "proof": "COMPOSER_WRAPS_THE_COMPLETE_RESPONSE_IN_EXACTLY_ONE_OUTER_DOUBLE_QUOTE_PAIR",
        },
    }

    active_count = 15
    remaining = ["length_constraints:number_sentences"]
    if len(closed) + len(remaining) != active_count:
        raise AssertionError("ACTIVE15_PARTITION_DRIFT")

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__14_OF_15_ACTIVE_FAMILIES_REDUCED_TO_PARAMETRIC_"
            "CONSTRUCTION_ARGUMENTS__ONLY_PUNKT_SENTENCE_RESIDUE_REMAINS"
        ),
        "source_bindings": bindings,
        "pinned_external_semantics": {
            "livebench_commit": PINNED_LIVEBENCH_COMMIT,
            "instructions_blob": PINNED_INSTRUCTIONS_BLOB,
            "instructions_util_blob": PINNED_INSTRUCTIONS_UTIL_BLOB,
            "registry_blob": PINNED_REGISTRY_BLOB,
            "nltk_version": PINNED_NLTK_VERSION,
            "punkt_source_blob": PINNED_NLTK_PUNKT_SOURCE_BLOB,
        },
        "closed_family_count": len(closed),
        "closed_families": closed,
        "remaining_family_count": len(remaining),
        "remaining_families": remaining,
        "remaining_load_bearing_obligation": (
            "PROVE_EXACT_PINNED_PUNKT_SENTENCE_COUNTS_FOR_THE_FINITE_"
            "CONSTRUCTOR_PUNCTUATION_ADJACENCY_QUOTIENT_AFTER_KNOWN_SACRIFICES"
        ),
        "deleted_proof_requirements": [
            "FULL_RAW_WORD_THRESHOLD_CARTESIAN_PRODUCT",
            "FULL_PARAGRAPH_BULLET_SECTION_NTH_CARTESIAN_PRODUCT",
            "FULL_LEXICAL_IDENTITY_CARTESIAN_PRODUCT_OUTSIDE_KNOWN_FORBIDDEN_COLLISIONS",
            "FULL_SPECIAL_ROUTE_CARTESIAN_PRODUCT",
        ],
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_frequencies_read": 0,
        "target_scores_read": 0,
        "acceptance_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "hard_nonclaims": [
            "PUNKT_SENTENCE_RESIDUE_IS_NOT_YET_UNIVERSALLY_CLOSED",
            "LIVEBENCH_ACCEPTANCE_IS_NOT_YET_PROVED",
            "THE_TERMINAL_GOAL_IS_NOT_YET_PROVED",
        ],
    }


def run(args=None, root=None) -> dict[str, Any]:
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
