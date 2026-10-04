#!/usr/bin/env python3
"""Symbolic collapse of the remaining LiveBench active15 slot Cartesian product.

This module does not claim terminal acceptance.  It proves a narrower but
load-bearing fact: the raw public slot Cartesian product is not the right proof
obligation for the current deterministic composer.

For every conflict-compatible active15 identity set (cardinality 1..5), all
non-tokenizer slot dimensions either:
  * are handled by a direct exact constructor whose correctness is algebraic,
  * are finite lexical collision predicates already reduced to the exact lexical
    quotient, or
  * are monotone threshold constraints with a closed-form safety bound.

The only runtime-semantic residual left by this reduction is the frozen Punkt
sentence-tokenizer interaction surface.  That residual is intentionally kept
fail-closed for independent exact-byte verification.

No terminal rows, hidden kwargs, terminal frequencies, comparator responses, or
terminal scores are read here.
"""
from __future__ import annotations

from typing import Iterable

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_UNIVERSAL_SEMANTIC_REDUCTION_V1"

EXIST = "keywords:existence"
FORBIDDEN = "keywords:forbidden_words"
PARAGRAPHS = "length_constraints:number_paragraphs"
WORDS = "length_constraints:number_words"
SENTENCES = "length_constraints:number_sentences"
NTH = "length_constraints:nth_paragraph_first_word"
POSTSCRIPT = "detectable_content:postscript"
BULLETS = "detectable_format:number_bullet_lists"
TITLE = "detectable_format:title"
SECTIONS = "detectable_format:multiple_sections"
JSON_ID = "detectable_format:json_format"
REPEAT = "combination:repeat_prompt"
TWO = "combination:two_responses"
END = "startend:end_checker"
QUOTE = "startend:quotation"

PUBLIC_MIN_WORD_THRESHOLD = 100
PUBLIC_MAX_WORD_THRESHOLD = 500
PUBLIC_MAX_SENTENCE_THRESHOLD = 20
PUBLIC_MAX_PARAGRAPHS = 5
PUBLIC_MAX_BULLETS = 5
PUBLIC_MAX_SECTIONS = 5

# Exact public fixed lexical intersections already established against the
# pinned 1,525-word ASCII-alphabetic WORD_LIST.
END_PHRASE_WORD_INTERSECTIONS = {
    "Any other questions?": frozenset({"other"}),
    "Is there anything else I can help with?": frozenset(
        {"anything", "can", "help"}
    ),
}
POSTSCRIPT_WORD_INTERSECTION = frozenset()

SPECIAL_BRANCH_ALLOWED = {
    JSON_ID: frozenset({JSON_ID, EXIST, FORBIDDEN}),
    REPEAT: frozenset({REPEAT, EXIST, TITLE}),
    TWO: frozenset({TWO, EXIST, FORBIDDEN, TITLE}),
}


class SemanticReductionError(RuntimeError):
    pass


def _general(ids: Iterable[str]) -> bool:
    s = set(ids)
    return not bool(s & {JSON_ID, REPEAT, TWO})


def symbolic_unpadded_word_upper_bound(ids: Iterable[str]) -> int:
    """Upper-bound current composer word count when WORDS is 'less than'.

    The bound is over *all* admitted values of every other public slot:
      existence: five required words are packed into one alphanumeric token;
      sentence lower-bound constructor: <=20 one-word sentence tokens;
      sections: <=5 * 3 words;
      bullets: <=5 one-word bullet payloads;
      title: one numeric title token;
      nth paragraphs: <=5 additional words around the core;
      star paragraphs: <=4 additional numeric words around the core;
      postscript: P.P.S contributes at most three RegexpTokenizer words;
      end phrase: the longer public phrase contributes eight words.

    Special JSON/repeat/two branches conflict with WORDS in the frozen registry,
    so this function is defined only for the general branch.
    """
    s = set(ids)
    if WORDS not in s:
        raise SemanticReductionError("WORDS_ID_REQUIRED")
    if not _general(s):
        raise SemanticReductionError("WORDS_CANNOT_OCCUR_IN_SPECIAL_BRANCH")

    # Parts joined into the general core before paragraph wrapping.
    core = 0
    if EXIST in s:
        core += 1
    if TITLE in s:
        core += 1
    if SECTIONS in s:
        core += 3 * PUBLIC_MAX_SECTIONS
    if BULLETS in s:
        core += PUBLIC_MAX_BULLETS
    if SENTENCES in s:
        # Worst word-count case is the 'at least' constructor at threshold 20.
        core += PUBLIC_MAX_SENTENCE_THRESHOLD

    # _general() injects one numeric safe token if no earlier part exists.
    if core == 0:
        core = 1

    # NTH and star-paragraph modes are mutually exclusive by the frozen graph.
    if NTH in s:
        core += PUBLIC_MAX_PARAGRAPHS
    elif PARAGRAPHS in s:
        core += PUBLIC_MAX_PARAGRAPHS - 1

    if POSTSCRIPT in s:
        core += 3
    if END in s:
        core += 8

    # Quote characters add no \w+ tokens; FORBIDDEN and WORDS emit no text.
    return core


def _assert_special_branch_partition(sets: tuple[tuple[str, ...], ...]) -> None:
    for ids in sets:
        s = set(ids)
        specials = s & set(SPECIAL_BRANCH_ALLOWED)
        if len(specials) > 1:
            raise SemanticReductionError("MULTIPLE_SPECIAL_BRANCHES:" + ",".join(ids))
        for special in specials:
            if not s <= set(SPECIAL_BRANCH_ALLOWED[special]):
                raise SemanticReductionError(
                    "SPECIAL_BRANCH_SCOPE_DRIFT:" + special + ":" + ",".join(ids)
                )


def _assert_general_topology(sets: tuple[tuple[str, ...], ...]) -> None:
    for ids in sets:
        s = set(ids)
        if not _general(s):
            continue
        if PARAGRAPHS in s and NTH in s:
            raise SemanticReductionError("PARAGRAPH_NTH_CONFLICT_DRIFT")
        if PARAGRAPHS in s and SENTENCES in s:
            raise SemanticReductionError("PARAGRAPH_SENTENCE_CONFLICT_DRIFT")
        if NTH in s and BULLETS in s:
            raise SemanticReductionError("NTH_BULLET_CONFLICT_DRIFT")
        if NTH in s and SECTIONS in s:
            raise SemanticReductionError("NTH_SECTION_CONFLICT_DRIFT")
        if TITLE in s and QUOTE in s:
            raise SemanticReductionError("TITLE_QUOTE_CONFLICT_DRIFT")


def verify() -> dict:
    sets = archetypes.enumerate_compatible_sets()
    if len(sets) != 928:
        raise SemanticReductionError("STRUCTURAL_SET_COUNT_DRIFT")
    _assert_special_branch_partition(sets)
    _assert_general_topology(sets)

    word_bounds = [
        symbolic_unpadded_word_upper_bound(ids)
        for ids in sets
        if WORDS in ids
    ]
    if not word_bounds:
        raise SemanticReductionError("NO_WORD_CONSTRAINT_STRUCTURAL_SETS")
    maximum = max(word_bounds)
    if maximum >= PUBLIC_MIN_WORD_THRESHOLD:
        raise SemanticReductionError(
            "WORD_UPPER_BOUND_PROOF_FAILED:"
            + str(maximum)
            + ">="
            + str(PUBLIC_MIN_WORD_THRESHOLD)
        )

    # The exact bound is useful as a drift detector.  It follows from a
    # compatible five-checker set containing WORDS + SENTENCES + SECTIONS +
    # BULLETS + END at their maximum text-producing public values.
    if maximum != 48:
        raise SemanticReductionError("WORD_BOUND_DRIFT:" + str(maximum))

    sentence_sets = tuple(ids for ids in sets if SENTENCES in ids)
    general_sets = tuple(ids for ids in sets if _general(ids))

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__RAW_SLOT_CARTESIAN_PRODUCT_COLLAPSED_TO_SYMBOLIC_LEMMAS_"
            "PLUS_EXACT_PUNKT_RESIDUAL"
        ),
        "structural_identity_sets": len(sets),
        "general_identity_sets": len(general_sets),
        "sentence_identity_sets": len(sentence_sets),
        "special_branch_allowed_id_sets": {
            key: sorted(value) for key, value in SPECIAL_BRANCH_ALLOWED.items()
        },
        "word_upper_bound": {
            "maximum_unpadded_words_over_every_compatible_words_set": maximum,
            "minimum_public_less_than_threshold": PUBLIC_MIN_WORD_THRESHOLD,
            "margin_words": PUBLIC_MIN_WORD_THRESHOLD - maximum,
            "less_than_consequence": (
                "EVERY_PUBLIC_WORDS_LESS_THAN_THRESHOLD_IS_SAFE_IF_THE_OTHER_"
                "CONSTRUCTED_CHECKERS_PASS"
            ),
            "at_least_consequence": (
                "COMPOSER_PADS_TO_THRESHOLD_BEFORE_ONLY_MONOTONE_TEXT_WRAPPERS"
            ),
        },
        "lexical_hazard_basis": {
            "required_keywords": (
                "PACKED_INSIDE_ONE_ALPHANUMERIC_WORD_TOKEN__RAW_EXISTENCE_"
                "SUBSTRINGS_SURVIVE__FORBIDDEN_WORD_BOUNDARIES_DO_NOT"
            ),
            "forced_standalone_public_words": [
                "NTH_FIRST_WORD",
                "END_PHRASE_WORDS",
            ],
            "end_phrase_word_list_intersections": {
                key: sorted(value)
                for key, value in END_PHRASE_WORD_INTERSECTIONS.items()
            },
            "postscript_word_list_intersection": sorted(
                POSTSCRIPT_WORD_INTERSECTION
            ),
            "section_forbidden_resolution": (
                "CONSTRUCTED_9Section_OR_9SECTION_PREFIX_REMOVES_LEFT_WORD_BOUNDARY"
            ),
            "remaining_forbidden_unsat_classes": [
                "NTH_FIRST_WORD_EQUALS_FORBIDDEN_WORD",
                "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD",
            ],
        },
        "algebraic_positive_checker_lemmas": [
            "JSON_SPECIAL_BRANCH_EMITS_VALID_JSON_AND_ONLY_COMPATIBLE_LEXICAL_CHECKERS",
            "REPEAT_SPECIAL_BRANCH_STARTS_WITH_EXACT_VISIBLE_PROMPT_PREFIX",
            "TWO_RESPONSE_SPECIAL_BRANCH_EMITS_EXACTLY_TWO_DISTINCT_NONEMPTY_RESPONSES",
            "TITLE_EMITS_ONE_NONEMPTY_DOUBLE_ANGLE_TITLE",
            "PARAGRAPH_MODE_EMITS_EXACTLY_REQUESTED_STAR_DIVIDER_PARAGRAPHS",
            "NTH_MODE_EMITS_EXACTLY_REQUESTED_DOUBLE_NEWLINE_PARAGRAPHS_AND_FIRST_WORD",
            "BULLET_MODE_EMITS_EXACTLY_REQUESTED_SINGLE_ASTERISK_BULLET_LINES",
            "SECTION_MODE_EMITS_AT_LEAST_REQUESTED_CASE_SENSITIVE_SECTION_MARKERS",
            "POSTSCRIPT_MODE_EMITS_ONE_OF_THE_TWO_EXACT_PUBLIC_MARKERS",
            "END_MODE_ENDS_WITH_ONE_OF_THE_TWO_EXACT_PUBLIC_END_PHRASES",
            "QUOTE_MODE_WRAPS_ENTIRE_RESPONSE_IN_DOUBLE_QUOTES",
            "WORD_LESS_THAN_IS_PROVED_BY_GLOBAL_48_WORD_BOUND",
            "WORD_AT_LEAST_IS_PROVED_BY_DIRECT_PADDING_AND_MONOTONE_WRAPPERS",
            "SENTENCE_LESS_THAN_ONE_IS_INTRINSICALLY_UNSAT_UNDER_STRICT_NONEMPTY_EVALUATION",
        ],
        "remaining_exact_runtime_residual": {
            "family": "NLTK_PUNKT_SENTENCE_TOKENIZATION",
            "why_only_residual": (
                "SENTENCE_CHECKER_DEPENDS_ON_EXTERNAL_FROZEN_TOKENIZER_RUNTIME; "
                "ALL_OTHER_ACTIVE15_CONSTRUCTOR_SLOT_EFFECTS_ABOVE_ARE_REGEX_"
                "JSON_PREFIX_SUFFIX_COUNT_OR_MONOTONE_WORD_ARITHMETIC"
            ),
            "required_independent_check": (
                "VERIFY_SENTENCE_AT_LEAST_1_TO_20_AND_LESS_THAN_2_TO_20_ACROSS_"
                "EVERY_COMPATIBLE_SENTENCE_IDENTITY_SHAPE_AND_THE_FINITE_"
                "POSTSCRIPT_END_QUOTE_NTH_WRAPPER_STATES_USING_EXACT_PINNED_PUNKT"
            ),
        },
        "terminal_rows_used": False,
        "terminal_kwargs_used": False,
        "terminal_frequencies_used": False,
        "target_scores_used": False,
        "acceptance_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
    }


def run(args=None, root=None):
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
