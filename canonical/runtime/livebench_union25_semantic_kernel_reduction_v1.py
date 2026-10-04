#!/usr/bin/env python3
"""Exact semantic-kernel reduction for the LiveBench public union25 delta.

The structural union25 proof reduces 13,631 extra-bearing structures to 156
extra10 signatures. This module removes another layer of fake combinatorics.

Two extra families admit zero-lexeme carriers:
  * number_placeholders -> "[]"
  * number_highlighted_sections -> "+*-*"

At any general-route augmentation site, these carriers:
  * add zero RegexpTokenizer(r"\w+") words;
  * add zero ASCII letters, so they cannot change keyword or letter counts;
  * add zero commas and zero .?! sentence terminators;
  * contain no cased character, so they cannot change isupper()/islower()
    truth or capital-word counts;
  * create no paragraph, bullet, section, title, quote, JSON, repeat, or
    two-response delimiter.

The registry already excludes these decorator families from JSON, repeat,
two-response, constrained-response, and their known structural conflicts.

One external/runtime-sensitive caveat remains deliberately load-bearing:
langdetect must be shown invariant to appending/inserting these punctuation-only
decorators for the 30 pinned language carriers. Until that independent fact is
bound, decorator bits are retained only in language-bearing kernels.

Result:
  156 exact extra10 structural signatures
    -> 64 exact semantic kernels with no language assumption
    -> 41 kernels if the 30-language punctuation-neutrality gate passes.

No terminal row, hidden kwarg, target response, target frequency, or target
score is used. This file grants zero acceptance credit.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Sequence

from canonical.runtime import livebench_union25_archetypes_v1 as u

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_SEMANTIC_KERNEL_REDUCTION_V1"

TRANSPARENT_DECORATORS = (
    u.PLACEHOLDERS,
    u.HIGHLIGHTS,
)

HARD_EXTRAS = (
    u.KEYWORD_FREQUENCY,
    u.LETTER_FREQUENCY,
    u.LANGUAGE,
    u.CAPITAL_FREQUENCY,
    u.ENGLISH_CAPITAL,
    u.ENGLISH_LOWERCASE,
    u.NO_COMMA,
)

PLACEHOLDER_CARRIER = "[]"
HIGHLIGHT_CARRIER = "+*-*"

EXPECTED_STRUCTURAL_SIGNATURES = 156
EXPECTED_CONSERVATIVE_KERNELS = 64
EXPECTED_CONSERVATIVE_LANGUAGE_KERNELS = 31
EXPECTED_CONSERVATIVE_NONLANGUAGE_HARD_KERNELS = 31
EXPECTED_LANGUAGE_NEUTRAL_KERNELS = 41
EXPECTED_LANGUAGE_NEUTRAL_HARD_KERNELS = 39


def _decorator_invariants() -> dict[str, Any]:
    p = PLACEHOLDER_CARRIER
    h = HIGHLIGHT_CARRIER

    if re.findall(r"\[.*?\]", p) != [p]:
        raise AssertionError("PLACEHOLDER_CARRIER_CHECKER_DRIFT")

    highlights = re.findall(r"\*[^\n\*]*\*", h)
    if highlights != [h] or not highlights[0].strip("*").strip():
        raise AssertionError("HIGHLIGHT_CARRIER_CHECKER_DRIFT")

    for name, token in (("placeholder", p), ("highlight", h)):
        if re.findall(r"\w+", token):
            raise AssertionError(f"{name.upper()}_ADDS_WORDS")
        if re.findall(r"[A-Za-z]", token):
            raise AssertionError(f"{name.upper()}_ADDS_ASCII_LETTERS")
        if "," in token:
            raise AssertionError(f"{name.upper()}_ADDS_COMMA")
        if any(ch in token for ch in ".?!"):
            raise AssertionError(f"{name.upper()}_ADDS_SENTENCE_TERMINATOR")
        if "\n" in token:
            raise AssertionError(f"{name.upper()}_ADDS_NEWLINE")
        if "******" in token or "***" in token or "<<" in token or ">>" in token:
            raise AssertionError(f"{name.upper()}_ADDS_SPECIAL_DELIMITER")
        if '"' in token:
            raise AssertionError(f"{name.upper()}_ADDS_QUOTE")
        if any(ch.isalpha() or ch.isupper() or ch.islower() for ch in token):
            raise AssertionError(f"{name.upper()}_ADDS_CASED_CHARACTER")
        if re.search(r"(?m)^\s*[-\*]\s+", token):
            raise AssertionError(f"{name.upper()}_ADDS_BULLET")

    # HIGHLIGHTS and PLACEHOLDERS must never enter special routes in the pinned
    # conflict graph; otherwise interior augmentation would need a new proof.
    for ids in u.enumerate_compatible_sets():
        s = set(ids)
        if s & set(TRANSPARENT_DECORATORS):
            if u.route(ids) != "GENERAL":
                raise AssertionError(
                    "DECORATOR_SPECIAL_ROUTE_CONFLICT_DRIFT:" + repr(ids)
                )

    return {
        "placeholder_carrier": p,
        "highlight_carrier": h,
        "regexp_word_delta_each": 0,
        "ascii_letter_delta_each": 0,
        "comma_delta_each": 0,
        "sentence_terminator_delta_each": 0,
        "cased_character_delta_each": 0,
        "special_route_compatible": False,
        "general_route_interior_insertion_required": False,
        "language_detector_neutrality_proved_here": False,
    }


def semantic_kernel(
    ids: Sequence[str],
    *,
    assume_language_decorator_neutrality: bool = False,
) -> tuple[str, ...]:
    sig = set(u.extra_signature(ids))
    if not sig:
        return ("ACTIVE15_ONLY",)

    if u.CONSTRAINED in sig:
        # Registry conflict set makes this an exact singleton.
        if sig != {u.CONSTRAINED}:
            raise AssertionError("CONSTRAINED_NOT_SINGLETON:" + repr(sorted(sig)))
        return ("ISOLATED_CONSTRAINED_SINGLETON",)

    hard = tuple(iid for iid in HARD_EXTRAS if iid in sig)
    decorators = tuple(iid for iid in TRANSPARENT_DECORATORS if iid in sig)

    if u.LANGUAGE in hard and not assume_language_decorator_neutrality:
        return (
            "LANGUAGE_SENSITIVE_KERNEL",
            *hard,
            "DECORATOR_BITS",
            *decorators,
        )

    if hard:
        return ("HARD_KERNEL", *hard)

    # One constructor handles placeholder-only, highlight-only, and both.
    if not decorators:
        raise AssertionError("EXTRA_SIGNATURE_WITHOUT_CLASSIFICATION")
    return ("DECORATOR_ONLY_GENERAL_KERNEL",)


def verify() -> dict[str, Any]:
    structural = u.verify()
    if structural["distinct_extra10_signatures"] != EXPECTED_STRUCTURAL_SIGNATURES:
        raise AssertionError("UPSTREAM_STRUCTURAL_SIGNATURE_DRIFT")

    extra_sets = [
        ids
        for ids in u.enumerate_compatible_sets()
        if set(ids) & set(u.EXTRA10)
    ]

    raw_signatures = {u.extra_signature(ids) for ids in extra_sets}
    if len(raw_signatures) != EXPECTED_STRUCTURAL_SIGNATURES:
        raise AssertionError("RAW_SIGNATURE_COUNT_DRIFT")

    conservative = {semantic_kernel(ids) for ids in extra_sets}
    if len(conservative) != EXPECTED_CONSERVATIVE_KERNELS:
        raise AssertionError(
            f"CONSERVATIVE_KERNEL_COUNT_DRIFT:{len(conservative)}"
        )

    language_sensitive = {
        key for key in conservative if key[0] == "LANGUAGE_SENSITIVE_KERNEL"
    }
    nonlanguage_hard = {
        key for key in conservative if key[0] == "HARD_KERNEL"
    }
    if len(language_sensitive) != EXPECTED_CONSERVATIVE_LANGUAGE_KERNELS:
        raise AssertionError("LANGUAGE_KERNEL_COUNT_DRIFT")
    if (
        len(nonlanguage_hard)
        != EXPECTED_CONSERVATIVE_NONLANGUAGE_HARD_KERNELS
    ):
        raise AssertionError("NONLANGUAGE_HARD_KERNEL_COUNT_DRIFT")

    conditional = {
        semantic_kernel(ids, assume_language_decorator_neutrality=True)
        for ids in extra_sets
    }
    if len(conditional) != EXPECTED_LANGUAGE_NEUTRAL_KERNELS:
        raise AssertionError(
            f"LANGUAGE_NEUTRAL_KERNEL_COUNT_DRIFT:{len(conditional)}"
        )
    conditional_hard = {
        key for key in conditional if key[0] == "HARD_KERNEL"
    }
    if len(conditional_hard) != EXPECTED_LANGUAGE_NEUTRAL_HARD_KERNELS:
        raise AssertionError("LANGUAGE_NEUTRAL_HARD_KERNEL_COUNT_DRIFT")

    decorator_facts = _decorator_invariants()

    hard_family_occurrence = Counter()
    for key in conditional_hard:
        for iid in key[1:]:
            hard_family_occurrence[iid] += 1

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__UNION25_156_STRUCTURAL_SIGNATURES_REDUCED_TO_"
            "64_EXACT_CONSERVATIVE_SEMANTIC_KERNELS"
        ),
        "upstream": {
            "structural_schema": structural["schema"],
            "structural_status": structural["status"],
            "extra_bearing_structures": structural["extra_bearing_total"],
            "raw_extra10_signatures": len(raw_signatures),
        },
        "proven_reduction_without_language_assumption": {
            "semantic_kernel_count": len(conservative),
            "nonlanguage_hard_kernel_count": len(nonlanguage_hard),
            "language_sensitive_kernel_count": len(language_sensitive),
            "decorator_only_kernel_count": 1,
            "isolated_constrained_kernel_count": 1,
        },
        "conditional_reduction_after_language_neutrality_gate": {
            "semantic_kernel_count": len(conditional),
            "hard_kernel_count": len(conditional_hard),
            "decorator_only_kernel_count": 1,
            "isolated_constrained_kernel_count": 1,
            "required_gate": (
                "INDEPENDENTLY_VERIFY_LANGDETECT_INVARIANCE_FOR_[]_AND_+*-*_"
                "INSERTIONS_OVER_ALL_30_PINNED_LANGUAGE_CARRIERS"
            ),
        },
        "decorator_invariants": decorator_facts,
        "hard_extra_families": list(HARD_EXTRAS),
        "hard_family_kernel_occurrence": dict(sorted(hard_family_occurrence.items())),
        "new_critical_path": (
            "VERIFY_30_LANGUAGE_DECORATOR_NEUTRALITY_THEN_PROVE_ONLY_39_"
            "HARD_EXTRA_KERNELS_OVER_THE_ALREADY_CLOSED_ACTIVE15_CORE"
        ),
        "terminal_rows_read": 0,
        "hidden_terminal_kwargs_read": 0,
        "terminal_instruction_id_lists_read": 0,
        "target_responses_read": 0,
        "target_scores_read": 0,
        "incremental_spend_usd": 0,
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
