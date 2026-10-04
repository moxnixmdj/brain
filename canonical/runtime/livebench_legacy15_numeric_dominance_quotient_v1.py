#!/usr/bin/env python3
"""Dominance quotient for frozen Active15 LiveBench numeric/structural slots.

This module does not claim checker equivalence. It identifies extremal public
parameter representatives whose successful exact-checker construction closes
weaker values in the same monotone class. If an extremal representative fails,
the class must be expanded rather than inferred UNSAT.

No terminal rows, terminal case frequencies, hidden kwargs, comparator
responses, or terminal scores are consumed.
"""
from __future__ import annotations

from math import prod
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_NUMERIC_DOMINANCE_QUOTIENT_V1"

WORD_MIN = 100
WORD_MAX = 500
SENTENCE_MIN = 1
SENTENCE_MAX = 20
PARAGRAPH_MAX = 5
BULLET_MAX = 5
SECTION_MAX = 5
SECTION_SPLITTERS = ("Section", "SECTION")
POSTSCRIPT_MARKERS = ("P.S.", "P.P.S")
END_PHRASES = (
    "Any other questions?",
    "Is there anything else I can help with?",
)
RELATIONS = ("less than", "at least")

RAW_FAMILY_STATE_COUNTS = {
    "number_words": (WORD_MAX - WORD_MIN + 1) * len(RELATIONS),
    "number_sentences": SENTENCE_MAX * len(RELATIONS),
    "number_paragraphs": PARAGRAPH_MAX,
    "nth_paragraph_numeric_pair": sum(range(1, PARAGRAPH_MAX + 1)),
    "number_bullet_lists": BULLET_MAX,
    "multiple_sections": SECTION_MAX * len(SECTION_SPLITTERS),
    "postscript": len(POSTSCRIPT_MARKERS),
    "end_checker": len(END_PHRASES),
}

# These are proof representatives, not claims that all raw values are identical.
REDUCED_PROOF_CLASS_COUNTS = {
    "number_words": 2,          # <100 ; >=500
    "number_sentences": 3,      # <1 ; <2 (covers all >=2) ; >=20
    "number_paragraphs": 5,     # exact count, retain all
    "nth_paragraph_numeric_pair": 15,  # exact pair, retain all
    "number_bullet_lists": 5,   # exact count, retain all
    "multiple_sections": 2,     # strongest count=5, preserve splitter case
    "postscript": 2,
    "end_checker": 2,
}

# Conservative over-composed upper bound on unavoidable \w+ tokens before any
# explicit NumberOfWords lower-bound padding. It intentionally combines more
# simultaneously active structures than the frozen <=5-checker generator can.
STRUCTURAL_WORD_UPPER_BOUND_COMPONENTS = {
    "title": 1,
    "five_existence_keywords_or_carriers": 5,
    "five_sections_sectionN_plus_payload": 10,
    "five_bullets": 5,
    "paragraph_or_nth_scaffold": 5,
    "longest_postscript_marker": 3,
    "longest_fixed_end_phrase": 8,
}
STRUCTURAL_WORD_UPPER_BOUND = sum(STRUCTURAL_WORD_UPPER_BOUND_COMPONENTS.values())


def _relation(value: str) -> str:
    value = str(value).strip().lower()
    if value not in RELATIONS:
        raise ValueError("RELATION_OUTSIDE_FROZEN_DOMAIN")
    return value


def number_words_class(num_words: int, relation: str) -> dict[str, Any]:
    n = int(num_words)
    rel = _relation(relation)
    if not WORD_MIN <= n <= WORD_MAX:
        raise ValueError("NUMBER_WORDS_OUTSIDE_FROZEN_DOMAIN")
    if rel == "less than":
        return {
            "class": "WORD_UPPER_BOUND",
            "representative": {"num_words": WORD_MIN, "relation": rel},
            "closure_rule": "PASS_AT_LT_100_IMPLIES_PASS_AT_EVERY_LT_N_FOR_100_LE_N_LE_500",
            "failure_rule": "REPRESENTATIVE_FAILURE_DOES_NOT_AUTHORIZE_GLOBAL_UNSAT",
        }
    return {
        "class": "WORD_LOWER_BOUND",
        "representative": {"num_words": WORD_MAX, "relation": rel},
        "closure_rule": "PASS_AT_GE_500_IMPLIES_PASS_AT_EVERY_GE_N_FOR_100_LE_N_LE_500",
        "failure_rule": "REPRESENTATIVE_FAILURE_DOES_NOT_AUTHORIZE_GLOBAL_UNSAT",
    }


def number_sentences_class(num_sentences: int, relation: str) -> dict[str, Any]:
    n = int(num_sentences)
    rel = _relation(relation)
    if not SENTENCE_MIN <= n <= SENTENCE_MAX:
        raise ValueError("NUMBER_SENTENCES_OUTSIDE_FROZEN_DOMAIN")
    if rel == "at least":
        return {
            "class": "SENTENCE_LOWER_BOUND",
            "representative": {"num_sentences": SENTENCE_MAX, "relation": rel},
            "closure_rule": "PASS_AT_GE_20_IMPLIES_PASS_AT_EVERY_GE_N_FOR_1_LE_N_LE_20",
            "failure_rule": "EXPAND_ONLY_THIS_CLASS_IF_GE_20_FAILS",
        }
    if n == 1:
        return {
            "class": "SENTENCE_ZERO_ONLY_UPPER_BOUND",
            "representative": {"num_sentences": 1, "relation": rel},
            "closure_rule": "LT_1_IS_THE_UNIQUE_ZERO_SENTENCE_CORNER",
            "failure_rule": "USE_SOUND_ZERO_SENTENCE_UNSAT_KERNEL_OR_EXACT_POSTVALIDATION",
        }
    return {
        "class": "SENTENCE_POSITIVE_UPPER_BOUND",
        "representative": {"num_sentences": 2, "relation": rel},
        "closure_rule": "PASS_WITH_ONE_SENTENCE_AT_LT_2_IMPLIES_PASS_AT_EVERY_LT_N_FOR_2_LE_N_LE_20",
        "failure_rule": "EXPAND_ONLY_THIS_CLASS_IF_LT_2_FAILS",
    }


def section_class(num_sections: int, section_spliter: str) -> dict[str, Any]:
    n = int(num_sections)
    splitter = str(section_spliter)
    if not 1 <= n <= SECTION_MAX:
        raise ValueError("NUMBER_SECTIONS_OUTSIDE_FROZEN_DOMAIN")
    if splitter not in SECTION_SPLITTERS:
        raise ValueError("SECTION_SPLITTER_OUTSIDE_FROZEN_DOMAIN")
    return {
        "class": "SECTION_MINIMUM_COUNT",
        "representative": {"num_sections": SECTION_MAX, "section_spliter": splitter},
        "closure_rule": "PASS_WITH_5_SECTIONS_IMPLIES_PASS_FOR_EVERY_MINIMUM_1_THROUGH_5_WITH_THE_SAME_SPLITTER",
        "boundary_safe_form": splitter + "1",
    }


def summary() -> dict[str, Any]:
    raw_cartesian = prod(RAW_FAMILY_STATE_COUNTS.values())
    reduced_cartesian = prod(REDUCED_PROOF_CLASS_COUNTS.values())
    return {
        "schema": SCHEMA,
        "status": "PASS__FINITE_DOMINANCE_QUOTIENT_DECLARED",
        "raw_family_state_counts": dict(RAW_FAMILY_STATE_COUNTS),
        "reduced_proof_class_counts": dict(REDUCED_PROOF_CLASS_COUNTS),
        "raw_family_state_sum": sum(RAW_FAMILY_STATE_COUNTS.values()),
        "reduced_proof_class_sum": sum(REDUCED_PROOF_CLASS_COUNTS.values()),
        "nonreachable_cartesian_envelope_raw": raw_cartesian,
        "nonreachable_cartesian_envelope_reduced": reduced_cartesian,
        "cartesian_envelope_reduction_numerator": raw_cartesian,
        "cartesian_envelope_reduction_denominator": reduced_cartesian,
        "structural_word_upper_bound": STRUCTURAL_WORD_UPPER_BOUND,
        "structural_word_upper_bound_components": dict(STRUCTURAL_WORD_UPPER_BOUND_COMPONENTS),
        "word_upper_bound_margin_below_hardest_historical_threshold": WORD_MIN - STRUCTURAL_WORD_UPPER_BOUND,
        "important_nonclaim": "CARTESIAN_ENVELOPES_ARE_NOT_REACHABLE_CASE_COUNTS_AND_REPRESENTATIVE_FAILURE_NEVER_IMPLES_CLASS_WIDE_UNSAT",
        "terminal_data_used": False,
        "acceptance_credit": False,
    }


def run(args=None, root=None):
    return summary()


if __name__ == "__main__":
    import json
    print(json.dumps(summary(), indent=2, sort_keys=True))
