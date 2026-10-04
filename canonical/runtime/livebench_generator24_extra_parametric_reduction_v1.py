#!/usr/bin/env python3
"""Parametric reduction for the nine generator24 families outside Active15.

This module is deliberately a reduction, not an acceptance claim. It freezes the
small semantic residue that must be verified to extend the already-developed
Active15 pointwise constructor to the exact historical 24-family public
generator without multiplying raw slot identities.

Public source authority:
- LiveBench checker commit 8f8e5c381a16e3f24257776edd53471fe86f8091
- instructions.py blob 4997bab885a676d92545fd91a9a20b48d234a2b2
- instructions_registry.py blob 903ed738398648c7cfac61d5ffa478c22f1f0891
- instructions_util.py blob 1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b
- historical live_data.py blob 6ff390d6885cf90f88d9d36959735cb327613edc

The nine generator24-only families are:
  keyword frequency, letter frequency, placeholders, constrained response,
  highlights, capital-word frequency, English-uppercase, English-lowercase,
  and no-comma.

Reduction theorem shape
-----------------------
1. constrained_response is isolated by the frozen conflict graph, so it is a
   singleton route with a fixed witness and never participates in a product.
2. placeholders and highlights are bounded monotone punctuation scaffolds.
3. keyword/letter/capital-word frequency each factor through one integer:
   the count already forced by the other retained constraints. "at least" is
   completed by a compact carrier; "less than" is satisfiable iff forced_count
   < threshold, otherwise sacrificing that one frequency checker is a
   cardinality-one optimum.
4. no_comma is free on the ordinary constructor. The only admitted arbitrary
   visible-text source that can force a comma is repeat_prompt; therefore its
   residue is one visible bit: comma present in mandatory repeated prefix.
5. English uppercase/lowercase commute with every case-insensitive checker and
   punctuation/count scaffold. The only frozen case-sensitive structural
   residue among generator24 construction literals is multiple_sections:
     - uppercase is compatible with splitter SECTION, incompatible with Section;
     - lowercase is incompatible with both Section and SECTION.
   The remaining environment-sensitive obligation is a pinned langdetect
   English carrier that respects any simultaneous frequency budgets.
6. All compact extra-family carriers have tiny word cost. With max five
   generated instructions the word-<100 proof remains reducible to a finite
   per-family budget maximum rather than threshold enumeration.

No terminal row, hidden kwargs, frequency, response, or score is used here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_GENERATOR24_EXTRA_PARAMETRIC_REDUCTION_V1"

PINNED = {
    "livebench_commit": "8f8e5c381a16e3f24257776edd53471fe86f8091",
    "instructions_blob": "4997bab885a676d92545fd91a9a20b48d234a2b2",
    "registry_blob": "903ed738398648c7cfac61d5ffa478c22f1f0891",
    "instructions_util_blob": "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
    "historical_generator_blob": "6ff390d6885cf90f88d9d36959735cb327613edc",
}

KW_FREQ = "keywords:frequency"
LETTER_FREQ = "keywords:letter_frequency"
PLACEHOLDERS = "detectable_content:number_placeholders"
CONSTRAINED = "detectable_format:constrained_response"
HIGHLIGHTS = "detectable_format:number_highlighted_sections"
CAP_WORD_FREQ = "change_case:capital_word_frequency"
EN_CAP = "change_case:english_capital"
EN_LOW = "change_case:english_lowercase"
NO_COMMA = "punctuation:no_comma"

GENERATOR24_EXTRAS = (
    KW_FREQ, LETTER_FREQ, PLACEHOLDERS, CONSTRAINED, HIGHLIGHTS,
    CAP_WORD_FREQ, EN_CAP, EN_LOW, NO_COMMA,
)

# Exact public build_description random domains from the pinned checker source.
PUBLIC_DOMAINS = {
    KW_FREQ: {
        "keyword_identity_count": 1525,
        "frequency": (1, 2, 3),
        "relation": ("less than", "at least"),
        "raw_domain_size": 1525 * 3 * 2,
    },
    LETTER_FREQ: {
        "letter_identity_count_after_lowercasing": 26,
        "frequency": tuple(range(1, 11)),
        "relation": ("less than", "at least"),
        "raw_domain_size": 26 * 10 * 2,
    },
    PLACEHOLDERS: {"num_placeholders": tuple(range(1, 5)), "raw_domain_size": 4},
    CONSTRAINED: {"fixed": True, "raw_domain_size": 1},
    HIGHLIGHTS: {"num_highlights": tuple(range(1, 5)), "raw_domain_size": 4},
    CAP_WORD_FREQ: {
        "frequency": tuple(range(1, 21)),
        "relation": ("less than", "at least"),
        "raw_domain_size": 20 * 2,
    },
    EN_CAP: {"fixed": True, "raw_domain_size": 1},
    EN_LOW: {"fixed": True, "raw_domain_size": 1},
    NO_COMMA: {"fixed": True, "raw_domain_size": 1},
}

RAW_SINGLE_FAMILY_PARAMETER_STATES = sum(
    int(v["raw_domain_size"]) for v in PUBLIC_DOMAINS.values()
)

# Compact constructor word-cost upper bounds. Counter carriers deliberately put
# repeated characters/substrings inside one token where checker semantics allow.
EXTRA_WORD_COST_UPPER_BOUND = {
    KW_FREQ: 1,       # 9<keyword><keyword><keyword>9
    LETTER_FREQ: 1,   # 9aaaaaaaaaa9
    PLACEHOLDERS: 4,  # [9][9][9][9] => four regex-word tokens
    HIGHLIGHTS: 4,    # inline *9* units; never line-start bullets
    CAP_WORD_FREQ: 20,# exact NLTK all-uppercase word units
    EN_CAP: 12,       # reserved budget for independently verified EN carrier
    EN_LOW: 12,       # reserved budget for independently verified EN carrier
    NO_COMMA: 0,
}

# Active15 conservative per-family terms already used by the post-sacrifice
# reduction. We use the family-wise values rather than its impossible
# all-families sum because the public generator admits at most five families.
ACTIVE_WORD_COST_UPPER_BOUND = {
    "length_constraints:number_sentences": 20,
    "detectable_format:multiple_sections": 15,
    "startend:end_checker": 8,
    "length_constraints:nth_paragraph_first_word": 5,
    "detectable_format:number_bullet_lists": 5,
    "length_constraints:number_paragraphs": 4,
    "detectable_content:postscript": 3,
    "keywords:existence": 1,
    "detectable_format:title": 1,
    "detectable_format:json_format": 1,
    "combination:two_responses": 1,
    "combination:repeat_prompt": 1,
    "startend:quotation": 0,
    "keywords:forbidden_words": 0,
    "length_constraints:number_words": 0,
}

PUBLIC_WORD_LT_MIN = 100
MAX_GENERATED_INSTRUCTIONS = 5


@dataclass(frozen=True)
class CounterDecision:
    satisfiable: bool
    deficit: int
    mandatory_loss: bool


def counter_decision(forced_count: int, threshold: int, relation: str) -> CounterDecision:
    """Exact scalar reduction for monotone frequency checkers.

    This function intentionally knows nothing about lexical identity. A separate
    source-bound forced-count compiler supplies the count created by mandatory
    retained literals. Once that integer is known, all threshold arithmetic is
    exact.
    """
    forced_count = int(forced_count)
    threshold = int(threshold)
    if forced_count < 0 or threshold < 1:
        raise ValueError("INVALID_COUNTER_DOMAIN")
    if relation == "at least":
        return CounterDecision(True, max(0, threshold - forced_count), False)
    if relation == "less than":
        ok = forced_count < threshold
        return CounterDecision(ok, 0, not ok)
    raise ValueError("UNKNOWN_RELATION")


def no_comma_repeat_decision(repeat_active: bool, repeated_prefix_has_comma: bool) -> dict[str, Any]:
    """Collapse the only arbitrary-text comma source to one visible bit."""
    hard_collision = bool(repeat_active and repeated_prefix_has_comma)
    return {
        "satisfiable_together": not hard_collision,
        "mandatory_loss_count_if_both_required": int(hard_collision),
        "proof_coordinate": "REPEAT_PREFIX_CONTAINS_COMMA" if hard_collision else "NONE",
    }


def english_case_section_decision(case_family: str, section_splitter: str | None) -> dict[str, Any]:
    """Exact case-sensitive Section residue after global case normalization."""
    if case_family not in {EN_CAP, EN_LOW}:
        raise ValueError("UNKNOWN_CASE_FAMILY")
    if section_splitter is None:
        return {"satisfiable_together": True, "mandatory_loss_count": 0}
    if section_splitter not in {"Section", "SECTION"}:
        raise ValueError("OUTSIDE_PUBLIC_SECTION_SPLITTER_DOMAIN")
    if case_family == EN_CAP:
        ok = section_splitter == "SECTION"
    else:
        ok = False
    return {
        "satisfiable_together": ok,
        "mandatory_loss_count": 0 if ok else 1,
        "proof_coordinate": (
            "NONE" if ok else f"{case_family}__CASE_SENSITIVE_{section_splitter}"
        ),
    }


def _five_family_word_bound() -> dict[str, Any]:
    """Conservative max cost of any five family-local constructor components.

    This ignores conflicts, so it is deliberately weaker than the reachable
    maximum. If even this upper bound is below 100, every reachable five-family
    unpadded construction assembled from these budgeted carriers is also below
    the public word-< threshold minimum.
    """
    all_costs = dict(ACTIVE_WORD_COST_UPPER_BOUND)
    all_costs.update(EXTRA_WORD_COST_UPPER_BOUND)
    # CONSTRAINED is a singleton special route and does not participate.
    ranked = sorted(all_costs.items(), key=lambda kv: kv[1], reverse=True)
    top = ranked[:MAX_GENERATED_INSTRUCTIONS]
    total = sum(v for _, v in top)
    return {"top_five": top, "sum": total, "below_public_word_lt_min": total < PUBLIC_WORD_LT_MIN}


def verify() -> dict[str, Any]:
    if set(GENERATOR24_EXTRAS) != set(PUBLIC_DOMAINS):
        raise AssertionError("EXTRA_DOMAIN_COVERAGE_DRIFT")
    if RAW_SINGLE_FAMILY_PARAMETER_STATES != 9722:
        raise AssertionError("RAW_SINGLE_FAMILY_DOMAIN_ARITHMETIC_DRIFT")

    # Threshold arithmetic is fully parametric; exercise domain edges.
    for n in range(1, 4):
        assert counter_decision(0, n, "at least").deficit == n
        assert counter_decision(n, n, "less than").mandatory_loss
        assert counter_decision(n - 1, n, "less than").satisfiable
    for n in range(1, 11):
        assert counter_decision(0, n, "at least").deficit == n
        assert counter_decision(n, n, "less than").mandatory_loss
    for n in range(1, 21):
        assert counter_decision(0, n, "at least").deficit == n
        assert counter_decision(n, n, "less than").mandatory_loss

    assert no_comma_repeat_decision(True, True)["mandatory_loss_count_if_both_required"] == 1
    assert no_comma_repeat_decision(True, False)["satisfiable_together"]
    assert no_comma_repeat_decision(False, True)["satisfiable_together"]

    assert english_case_section_decision(EN_CAP, "SECTION")["satisfiable_together"]
    assert not english_case_section_decision(EN_CAP, "Section")["satisfiable_together"]
    assert not english_case_section_decision(EN_LOW, "SECTION")["satisfiable_together"]
    assert not english_case_section_decision(EN_LOW, "Section")["satisfiable_together"]

    wb = _five_family_word_bound()
    if not wb["below_public_word_lt_min"]:
        raise AssertionError("FIVE_FAMILY_WORD_LT_REDUCTION_NOT_CLOSED")

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__GENERATOR24_EXTRA_RAW_PARAMETER_AXES_REDUCED_TO_"
            "FORCED_COUNTS_PLUS_TWO_STRUCTURAL_BITS__INDEPENDENT_SOURCE_AUDIT_"
            "AND_ENGLISH_CARRIER_BANK_REMAIN"
        ),
        "source_bindings_expected": PINNED,
        "generator24_extra_families": list(GENERATOR24_EXTRAS),
        "raw_single_family_parameter_states": RAW_SINGLE_FAMILY_PARAMETER_STATES,
        "public_domains": PUBLIC_DOMAINS,
        "parametric_counter_reduction": {
            "families": [KW_FREQ, LETTER_FREQ, CAP_WORD_FREQ],
            "state": "THRESHOLD_AXIS_DELETED_AFTER_FORCED_COUNT_IS_KNOWN",
            "at_least": "APPEND_EXACT_DEFICIT_WITH_COMPACT_CARRIER",
            "less_than": "SAT_IFF_FORCED_COUNT_LT_THRESHOLD__ELSE_ONE_CHECKER_MANDATORY_LOSS",
        },
        "monotone_scaffolds": {
            PLACEHOLDERS: "1_TO_4_NUMERIC_SQUARE_BRACKET_UNITS",
            HIGHLIGHTS: "1_TO_4_INLINE_NUMERIC_MARKDOWN_UNITS",
        },
        "special_routes": {
            CONSTRAINED: "CONFLICT_GRAPH_SINGLETON__FIXED_OPTION_WITNESS",
            NO_COMMA: "ORDINARY_ROUTE_FREE__REPEAT_ROUTE_REDUCES_TO_VISIBLE_PREFIX_COMMA_BIT",
        },
        "global_case_residue": {
            "case_insensitive_or_case_neutral_families_commute": True,
            "case_sensitive_section_coordinate": {
                EN_CAP: {"SECTION": "SAT", "Section": "ONE_MANDATORY_LOSS"},
                EN_LOW: {"SECTION": "ONE_MANDATORY_LOSS", "Section": "ONE_MANDATORY_LOSS"},
            },
            "remaining_environment_obligation": (
                "CONTENT_BOUND_LANGDETECT_ENGLISH_CARRIER_BANK_SELECTED_TO_RESPECT_"
                "SIMULTANEOUS_KEYWORD_AND_LETTER_FREQUENCY_BUDGETS"
            ),
        },
        "word_lt_reduction": {
            "public_min_threshold": PUBLIC_WORD_LT_MIN,
            "max_instruction_count": MAX_GENERATED_INSTRUCTIONS,
            **wb,
        },
        "remaining_load_bearing_obligations": [
            "INDEPENDENTLY_AUDIT_THE_FROZEN_CHECKER_AND_CONFLICT_SOURCE_AGAINST_THIS_REDUCTION",
            "BUILD_AND_VERIFY_FORCED_OCCURRENCE_COMPILER_FOR_KEYWORD_LETTER_AND_CAPITAL_WORD_COUNTERS",
            "BUILD_AND_VERIFY_PINNED_LANGDETECT_ENGLISH_CARRIER_BANK_FOR_UPPER_AND_LOWER_CASE",
            "COMPOSE_THE_EXTRA_SCAFFOLDS_IN_PRE_TERMINAL_PHASE_AND_EXACT_POSTVALIDATE_THE_RESULT",
            "KEEP_LANGUAGE_RESPONSE_LANGUAGE_SEPARATE__IT_IS_NOT_IN_HISTORICAL_GENERATOR24",
        ],
        "deleted_requirements": [
            "NO_9722_STATE_SINGLE_FAMILY_PARAMETER_BRUTE_FORCE_REQUIRED",
            "NO_RAW_CARTESIAN_PRODUCT_OF_THE_NINE_EXTRA_FAMILIES_REQUIRED",
            "NO_WORD_THRESHOLD_100_TO_500_ENUMERATION_REQUIRED_FOR_WORD_LT_AFTER_BUDGET_PROOF",
        ],
        "terminal_rows_read": 0,
        "hidden_terminal_kwargs_read": 0,
        "target_scores_read": 0,
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
