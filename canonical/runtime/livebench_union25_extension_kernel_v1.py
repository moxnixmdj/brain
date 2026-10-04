#!/usr/bin/env python3
"""Second-stage structural reduction for the LiveBench union25 delta10.

The exact registry25 quotient has 156 distinct subsets of the ten families not
present in the closed active15 core. Four of those families are not genuinely
new semantic interactions:

* constrained_response is structurally isolated by the frozen conflict graph;
* number_placeholders admits punctuation/case/language-neutral numeric tokens;
* number_highlighted_sections admits inline numeric *...* tokens and conflicts
  with NTH/sections at the registry layer;
* no_comma is a deletion constraint and all generated fragments can be chosen
  comma-free. The only forced-text exception is repeat_prompt, where the visible
  repeated prefix itself may contain a comma and must be handled pointwise.

Projecting those overlays leaves six semantically load-bearing delta families.
Across the exact 14,559 compatible registry structures they form only 20 hard
extra-family signatures, of width at most three.

This is a reduction theorem/candidate construction law, not acceptance credit.
The overlay lemmas still require exact-checker independent verification in
composition with the active15 constructor.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_union25_archetypes_v1 as u

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_EXTENSION_KERNEL_V1"

HARD_EXTRA = frozenset({
    u.KEYWORD_FREQUENCY,
    u.LETTER_FREQUENCY,
    u.LANGUAGE,
    u.CAPITAL_FREQUENCY,
    u.ENGLISH_CAPITAL,
    u.ENGLISH_LOWERCASE,
})
SYNTAX_OVERLAYS = frozenset({
    u.PLACEHOLDERS,
    u.HIGHLIGHTS,
    u.NO_COMMA,
})
ISOLATED = frozenset({u.CONSTRAINED})

EXPECTED_HARD_SIGNATURE_COUNT = 20
EXPECTED_MAX_HARD_SIGNATURE_WIDTH = 3


def hard_signature(ids: Sequence[str]) -> tuple[str, ...]:
    s = set(ids)
    return tuple(iid for iid in u.ALL_IDS if iid in s and iid in HARD_EXTRA)


def verify() -> dict[str, Any]:
    base = u.verify()
    sets = u.enumerate_compatible_sets()
    extra_sets = [ids for ids in sets if set(ids) & u.EXTRA10]

    hard = Counter(hard_signature(ids) for ids in extra_sets)
    if len(hard) != EXPECTED_HARD_SIGNATURE_COUNT:
        raise AssertionError("HARD_EXTENSION_SIGNATURE_COUNT_DRIFT")
    max_width = max(map(len, hard))
    if max_width != EXPECTED_MAX_HARD_SIGNATURE_WIDTH:
        raise AssertionError("HARD_EXTENSION_SIGNATURE_WIDTH_DRIFT")

    constrained_sets = [ids for ids in extra_sets if u.CONSTRAINED in ids]
    if constrained_sets != [(u.CONSTRAINED,)]:
        raise AssertionError("CONSTRAINED_NOT_ISOLATED")

    repeat_extra = [ids for ids in extra_sets if u.REPEAT in ids]
    if len(repeat_extra) != 4:
        raise AssertionError("REPEAT_EXTRA_ROUTE_COUNT_DRIFT")
    if any(set(ids) & u.EXTRA10 != {u.NO_COMMA} for ids in repeat_extra):
        raise AssertionError("REPEAT_EXTRA_ROUTE_NOT_ONLY_NO_COMMA")

    two_extra = [ids for ids in extra_sets if u.TWO in ids]
    if len(two_extra) != 12:
        raise AssertionError("TWO_EXTRA_ROUTE_COUNT_DRIFT")
    if any(
        not (set(ids) & u.EXTRA10) <= {u.LANGUAGE, u.NO_COMMA}
        for ids in two_extra
    ):
        raise AssertionError("TWO_EXTRA_ROUTE_DELTA_DRIFT")

    hard_signatures = [
        {"ids": list(sig), "structural_set_count": count}
        for sig, count in sorted(
            hard.items(),
            key=lambda kv: (len(kv[0]), kv[0]),
        )
    ]

    return {
        "schema": SCHEMA,
        "status": "PASS__UNION25_DELTA156_PROJECTS_TO_20_HARD_EXTENSION_SIGNATURES_WIDTH_LE_3",
        "upstream_schema": base["schema"],
        "raw_extra10_signature_count": base["distinct_extra10_signatures"],
        "hard_extra_families": [
            iid for iid in u.ALL_IDS if iid in HARD_EXTRA
        ],
        "hard_signature_count": len(hard),
        "max_hard_signature_width": max_width,
        "hard_signatures": hard_signatures,
        "factored_families": {
            "isolated": [u.CONSTRAINED],
            "syntax_overlays": [
                u.PLACEHOLDERS,
                u.HIGHLIGHTS,
                u.NO_COMMA,
            ],
        },
        "special_route_facts": {
            "constrained_response_sets": 1,
            "repeat_extra_sets": len(repeat_extra),
            "repeat_only_delta_family": u.NO_COMMA,
            "two_response_extra_sets": len(two_extra),
            "two_response_possible_delta_families": [
                u.LANGUAGE,
                u.NO_COMMA,
            ],
        },
        "candidate_overlay_lemmas": [
            {
                "family": u.PLACEHOLDERS,
                "construction": (
                    "append required count of numeric square-bracket tokens "
                    "such as [9000001]; exact checker counts bracket pairs and "
                    "the fragment introduces no cased alphabetic characters, "
                    "comma, or sentence terminator"
                ),
            },
            {
                "family": u.HIGHLIGHTS,
                "construction": (
                    "append required count of inline numeric highlight tokens "
                    "such as *9000001* away from line starts; frozen conflicts "
                    "already exclude NTH and multiple_sections"
                ),
            },
            {
                "family": u.NO_COMMA,
                "construction": (
                    "choose all generated fragments comma-free; only "
                    "repeat_prompt can force an arbitrary visible prefix, so "
                    "repeat+no_comma must inspect the visible repeated prefix "
                    "and sacrifice exactly one checker iff that prefix contains ','"
                ),
            },
            {
                "family": u.CONSTRAINED,
                "construction": (
                    "singleton structural route; choose one frozen constrained "
                    "option and no composition proof is needed"
                ),
            },
        ],
        "next_load_bearing_problem": (
            "PROVE_POINTWISE_COMPLETE_COMPOSITION_FOR_20_HARD_SIGNATURES_"
            "AND_INDEPENDENTLY_VERIFY_THE_THREE_OVERLAY_LEMMAS"
        ),
        "terminal_rows_used": False,
        "hidden_kwargs_used": False,
        "target_scores_used": False,
        "acceptance_credit": False,
        "hard_nonclaims": [
            "OVERLAY_COMPOSITION_LEMMAS_ARE_NOT_YET_INDEPENDENTLY_VERIFIED",
            "20_HARD_SIGNATURES_ARE_NOT_YET_POINTWISE_CLOSED",
            "NO_LIVEBENCH_ACCEPTANCE_CREDIT",
        ],
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
