#!/usr/bin/env python3
"""Collapse the LiveBench union25 residual to four maximal hard kernels.

This is a structural and syntactic reduction only. It proves:

1. The 20 hard extra-family signatures from the frozen union25 conflict graph
   are exactly the down-set of four maximal compatible three-family kernels.
2. Placeholder/highlight overlays consume at most eight extra RegexpTokenizer
   words, preserving the independently derived active15 less-than word margin:
   48 + 8 = 56 < the minimum public threshold 100.
3. Numeric placeholder/highlight carriers are comma-free, case-neutral,
   alphabetic-letter-neutral and sentence-terminal-neutral.
4. no_comma is algebraic outside repeat_prompt; repeat_prompt+no_comma has one
   exact visible contradiction condition: a comma in the verbatim prefix.
5. The only overlay behavior intentionally left uncollapsed is exact
   langdetect stability under numeric placeholder/highlight insertion.

No terminal rows, hidden kwargs, target scores or comparator responses are used.
No acceptance, family, capability or ownership credit is granted.
"""
from __future__ import annotations

from itertools import combinations
import re
from typing import Iterable

from canonical.runtime import livebench_legacy15_universal_semantic_reduction_v1 as active15
from canonical.runtime import livebench_union25_archetypes_v1 as u
from canonical.runtime import livebench_union25_extension_kernel_v1 as ext

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_FOUR_MAXIMAL_KERNEL_REDUCTION_V1"

MAXIMAL_HARD_KERNELS = (
    frozenset({u.KEYWORD_FREQUENCY, u.LETTER_FREQUENCY, u.CAPITAL_FREQUENCY}),
    frozenset({u.KEYWORD_FREQUENCY, u.LETTER_FREQUENCY, u.ENGLISH_CAPITAL}),
    frozenset({u.KEYWORD_FREQUENCY, u.LETTER_FREQUENCY, u.ENGLISH_LOWERCASE}),
    frozenset({u.LETTER_FREQUENCY, u.LANGUAGE, u.CAPITAL_FREQUENCY}),
)

PUBLIC_MAX_PLACEHOLDERS = 4
PUBLIC_MAX_HIGHLIGHTS = 4
PUBLIC_MIN_WORD_LESS_THAN_THRESHOLD = 100
PLACEHOLDER_CARRIER = "[9000001]"
HIGHLIGHT_CARRIER = "*9000001*"


class Union25KernelReductionError(RuntimeError):
    pass


def _canon(items: Iterable[str]) -> tuple[str, ...]:
    s = set(items)
    return tuple(iid for iid in u.ALL_IDS if iid in s)


def _powerset(kernel: frozenset[str]) -> set[tuple[str, ...]]:
    ordered = _canon(kernel)
    out: set[tuple[str, ...]] = set()
    for size in range(len(ordered) + 1):
        for subset in combinations(ordered, size):
            out.add(_canon(subset))
    return out


def expected_hard_signature_downset() -> set[tuple[str, ...]]:
    out: set[tuple[str, ...]] = set()
    for kernel in MAXIMAL_HARD_KERNELS:
        out |= _powerset(kernel)
    return out


def actual_hard_signatures() -> set[tuple[str, ...]]:
    state = ext.verify()
    return {
        _canon(row["ids"])
        for row in state["hard_signatures"]
    }


def maximal_signatures(
    signatures: set[tuple[str, ...]],
) -> set[frozenset[str]]:
    sets = {frozenset(sig) for sig in signatures}
    return {
        s for s in sets
        if not any(s < other for other in sets)
    }


def _word_tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text)


def verify() -> dict:
    extension = ext.verify()
    active = active15.verify()

    actual = actual_hard_signatures()
    expected = expected_hard_signature_downset()

    if len(actual) != 20:
        raise Union25KernelReductionError(
            "HARD_SIGNATURE_COUNT_DRIFT:" + str(len(actual))
        )
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise Union25KernelReductionError(
            "FOUR_KERNEL_DOWNSET_MISMATCH:"
            + "MISSING="
            + repr(missing)
            + ":EXTRA="
            + repr(extra)
        )

    expected_maxima = set(MAXIMAL_HARD_KERNELS)
    actual_maxima = maximal_signatures(actual)
    if actual_maxima != expected_maxima:
        raise Union25KernelReductionError(
            "MAXIMAL_KERNEL_SET_DRIFT:"
            + repr(sorted(map(sorted, actual_maxima)))
        )

    for kernel in MAXIMAL_HARD_KERNELS:
        ordered = _canon(kernel)
        if len(ordered) != 3:
            raise Union25KernelReductionError("MAXIMAL_KERNEL_WIDTH_DRIFT")
        if not u.compatible(ordered):
            raise Union25KernelReductionError(
                "MAXIMAL_KERNEL_NOT_COMPATIBLE:" + ",".join(ordered)
            )

    placeholder_words = len(_word_tokens(PLACEHOLDER_CARRIER))
    highlight_words = len(_word_tokens(HIGHLIGHT_CARRIER))
    if placeholder_words != 1 or highlight_words != 1:
        raise Union25KernelReductionError("NUMERIC_OVERLAY_WORD_COST_DRIFT")

    for token in (PLACEHOLDER_CARRIER, HIGHLIGHT_CARRIER):
        if "," in token:
            raise Union25KernelReductionError("OVERLAY_CARRIER_COMMA_DRIFT")
        if re.search(r"[A-Za-z]", token):
            raise Union25KernelReductionError("OVERLAY_CARRIER_ALPHA_DRIFT")
        if re.search(r"[.!?]", token):
            raise Union25KernelReductionError(
                "OVERLAY_CARRIER_SENTENCE_TERMINAL_DRIFT"
            )

    active_bound = active["word_upper_bound"][
        "maximum_unpadded_words_over_every_compatible_words_set"
    ]
    if active_bound != 48:
        raise Union25KernelReductionError(
            "ACTIVE15_WORD_BOUND_DRIFT:" + str(active_bound)
        )

    overlay_word_cost = (
        PUBLIC_MAX_PLACEHOLDERS * placeholder_words
        + PUBLIC_MAX_HIGHLIGHTS * highlight_words
    )
    combined_word_bound = active_bound + overlay_word_cost
    if combined_word_bound >= PUBLIC_MIN_WORD_LESS_THAN_THRESHOLD:
        raise Union25KernelReductionError(
            "OVERLAY_WORD_MARGIN_COLLAPSED:"
            + str(combined_word_bound)
        )

    sets = u.enumerate_compatible_sets()

    if any(
        u.JSON_ID in ids
        and (u.PLACEHOLDERS in ids or u.HIGHLIGHTS in ids or u.NO_COMMA in ids)
        for ids in sets
    ):
        raise Union25KernelReductionError("JSON_OVERLAY_CONFLICT_GRAPH_DRIFT")

    if any(
        u.HIGHLIGHTS in ids and (u.NTH in ids or u.SECTIONS in ids)
        for ids in sets
    ):
        raise Union25KernelReductionError(
            "HIGHLIGHT_STRUCTURE_CONFLICT_GRAPH_DRIFT"
        )

    repeat_extra = [
        ids for ids in sets
        if u.REPEAT in ids and set(ids) & u.EXTRA10
    ]
    if not repeat_extra:
        raise Union25KernelReductionError("REPEAT_OVERLAY_ROUTE_MISSING")
    if any(set(ids) & u.EXTRA10 != {u.NO_COMMA} for ids in repeat_extra):
        raise Union25KernelReductionError("REPEAT_OVERLAY_ROUTE_DRIFT")

    constrained = [
        ids for ids in sets
        if u.CONSTRAINED in ids
    ]
    if constrained != [(u.CONSTRAINED,)]:
        raise Union25KernelReductionError("CONSTRAINED_SINGLETON_DRIFT")

    coverage = {
        "|".join(sig) if sig else "<EMPTY>": [
            index
            for index, kernel in enumerate(MAXIMAL_HARD_KERNELS, start=1)
            if set(sig) <= set(kernel)
        ]
        for sig in sorted(actual, key=lambda x: (len(x), x))
    }
    if any(not owners for owners in coverage.values()):
        raise Union25KernelReductionError("UNCOVERED_HARD_SIGNATURE")

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__20_HARD_SIGNATURES_EQUAL_DOWNSET_OF_4_MAXIMAL_KERNELS__"
            "SYNTAX_OVERLAYS_COLLAPSED_TO_WORD_SAFE_NUMERIC_CARRIERS__"
            "LANGDETECT_NUMERIC_INVARIANCE_REMAINS_EXACT_RUNTIME_RESIDUAL"
        ),
        "upstream_extension_schema": extension["schema"],
        "hard_signature_count": len(actual),
        "maximal_hard_kernel_count": len(MAXIMAL_HARD_KERNELS),
        "maximal_hard_kernels": [
            list(_canon(kernel))
            for kernel in MAXIMAL_HARD_KERNELS
        ],
        "hard_signature_coverage": coverage,
        "overlay_reduction": {
            "placeholder_max_count": PUBLIC_MAX_PLACEHOLDERS,
            "highlight_max_count": PUBLIC_MAX_HIGHLIGHTS,
            "placeholder_carrier": PLACEHOLDER_CARRIER,
            "highlight_carrier": HIGHLIGHT_CARRIER,
            "overlay_max_added_words": overlay_word_cost,
            "active15_max_unpadded_words": active_bound,
            "combined_max_unpadded_words": combined_word_bound,
            "minimum_public_less_than_word_threshold":
                PUBLIC_MIN_WORD_LESS_THAN_THRESHOLD,
            "remaining_word_margin":
                PUBLIC_MIN_WORD_LESS_THAN_THRESHOLD - combined_word_bound,
            "carrier_properties": [
                "ZERO_COMMAS",
                "ZERO_ASCII_ALPHABETIC_LETTERS",
                "ZERO_SENTENCE_TERMINAL_PUNCTUATION",
                "ONE_REGEXP_WORD_TOKEN_EACH",
                "CASE_NEUTRAL",
            ],
            "placement_rule": (
                "INSERT_NUMERIC_OVERLAYS_IN_GENERAL_CORE_BEFORE_SUFFIX_WRAPPERS;"
                "HIGHLIGHTS_NEVER_AT_LINE_START;KEEP_END_POSTSCRIPT_QUOTE_WRAPPERS"
                "_OUTSIDE_THE_OVERLAY"
            ),
            "exact_unresolved_runtime_interaction": (
                "LANGDETECT_OUTPUT_STABILITY_UNDER_NUMERIC_PLACEHOLDER_OR_"
                "HIGHLIGHT_INSERTION_WHEN_LANGUAGE_RESPONSE_CHECKER_COEXISTS"
            ),
        },
        "no_comma_reduction": {
            "general_rule": (
                "ALL_BRAIN_GENERATED_FRAGMENTS_CAN_BE_SELECTED_COMMA_FREE"
            ),
            "repeat_prompt_exception": (
                "REPEAT_PROMPT_REQUIRES_VISIBLE_PREFIX_VERBATIM;IF_PREFIX_"
                "CONTAINS_COMMA_THEN_REPEAT_AND_NO_COMMA_ARE JOINTLY_UNSAT"
            ),
            "pointwise_rule": (
                "VISIBLE_PREFIX_COMMA_PRESENT=>MAXIMUM_JOINT_TRUE_COUNT_AT_MOST_1;"
                "VISIBLE_PREFIX_COMMA_ABSENT=>BOTH_CAN_BE_CONSTRUCTED_TRUE"
            ),
        },
        "isolated_family": {
            "instruction_id": u.CONSTRAINED,
            "route": "SINGLETON_DIRECT_WITNESS",
        },
        "next_load_bearing_problem": (
            "PROVE_FOUR_PARAMETRIC_MAXIMAL_HARD_KERNEL_CONSTRUCTORS_OVER_"
            "COMPATIBLE_ACTIVE15_CONTEXTS_AND_VERIFY_LANGDETECT_NUMERIC_"
            "OVERLAY_INVARIANCE_OR_CLASSIFY_ITS_EXACT_COUNTEREXAMPLES"
        ),
        "terminal_rows_used": False,
        "hidden_kwargs_used": False,
        "target_scores_used": False,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "hard_nonclaims": [
            "FOUR_MAXIMAL_KERNELS_ARE_NOT_YET_SEMANTICALLY_CLOSED",
            "LANGDETECT_NUMERIC_OVERLAY_INVARIANCE_IS_NOT_YET_PROVED",
            "NO_UNION25_POINTWISE_OPTIMALITY_CREDIT",
            "NO_LIVEBENCH_PREDICATE_PROMOTION",
        ],
    }


def run(args=None, root=None):
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
