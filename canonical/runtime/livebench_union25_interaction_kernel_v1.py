#!/usr/bin/env python3
"""Exact interaction kernel for the frozen LiveBench public union25.

This module is deliberately conservative. It does not claim that the new
checker families are solved. It proves which combinations can create genuinely
different composition obligations after the independently verified Active15
subsystem is factored out.

The 156 extra-family signatures are partitioned into five proof regimes:
  K0 constrained-response singleton;
  K1 decorator-only general contexts;
  K2 repeat-prompt + no-comma exceptions;
  K3 hard scalar/case/language cores;
  K4 two-response + language wrapper exceptions.

No target rows, hidden kwargs, target responses, target scores or terminal
frequencies are consumed.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_union25_archetypes_v1 as u

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_INTERACTION_KERNEL_V1"
BOUND_ARCHETYPES_BLOB = "8c68e63bbc1e1b843f076dbcd8c4bfae11d4cc2a"

HARD_IDS = frozenset({
    u.KEYWORD_FREQUENCY,
    u.LETTER_FREQUENCY,
    u.LANGUAGE,
    u.CAPITAL_FREQUENCY,
    u.ENGLISH_CAPITAL,
    u.ENGLISH_LOWERCASE,
})

DECORATOR_IDS = frozenset({
    u.PLACEHOLDERS,
    u.HIGHLIGHTS,
    u.NO_COMMA,
})

assert HARD_IDS | DECORATOR_IDS | {u.CONSTRAINED} == u.EXTRA10
assert not (HARD_IDS & DECORATOR_IDS)

EXPECTED_HARD_CORES = {
    (u.KEYWORD_FREQUENCY,),
    (u.LETTER_FREQUENCY,),
    (u.LANGUAGE,),
    (u.CAPITAL_FREQUENCY,),
    (u.ENGLISH_CAPITAL,),
    (u.ENGLISH_LOWERCASE,),
    tuple(sorted((u.KEYWORD_FREQUENCY, u.LETTER_FREQUENCY))),
    tuple(sorted((u.KEYWORD_FREQUENCY, u.CAPITAL_FREQUENCY))),
    tuple(sorted((u.KEYWORD_FREQUENCY, u.ENGLISH_CAPITAL))),
    tuple(sorted((u.KEYWORD_FREQUENCY, u.ENGLISH_LOWERCASE))),
    tuple(sorted((u.LETTER_FREQUENCY, u.LANGUAGE))),
    tuple(sorted((u.LETTER_FREQUENCY, u.CAPITAL_FREQUENCY))),
    tuple(sorted((u.LETTER_FREQUENCY, u.ENGLISH_CAPITAL))),
    tuple(sorted((u.LETTER_FREQUENCY, u.ENGLISH_LOWERCASE))),
    tuple(sorted((u.LANGUAGE, u.CAPITAL_FREQUENCY))),
    tuple(sorted((u.KEYWORD_FREQUENCY, u.LETTER_FREQUENCY, u.CAPITAL_FREQUENCY))),
    tuple(sorted((u.KEYWORD_FREQUENCY, u.LETTER_FREQUENCY, u.ENGLISH_CAPITAL))),
    tuple(sorted((u.KEYWORD_FREQUENCY, u.LETTER_FREQUENCY, u.ENGLISH_LOWERCASE))),
    tuple(sorted((u.LETTER_FREQUENCY, u.LANGUAGE, u.CAPITAL_FREQUENCY))),
}

EXPECTED_DECORATOR_SIGNATURES = {
    (u.PLACEHOLDERS,),
    (u.HIGHLIGHTS,),
    (u.NO_COMMA,),
    tuple(sorted((u.PLACEHOLDERS, u.HIGHLIGHTS))),
    tuple(sorted((u.PLACEHOLDERS, u.NO_COMMA))),
    tuple(sorted((u.HIGHLIGHTS, u.NO_COMMA))),
    tuple(sorted((u.PLACEHOLDERS, u.HIGHLIGHTS, u.NO_COMMA))),
}

EXPECTED_REGIME_COUNTS = {
    "K0_CONSTRAINED_SINGLETON": 1,
    "K1_DECORATOR_GENERAL": 2053,
    "K2_REPEAT_NO_COMMA": 4,
    "K3_HARD_GENERAL": 11569,
    "K4_TWO_LANGUAGE": 4,
}


def _hard_core(ids: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(ids) & HARD_IDS))


def _decorator_signature(ids: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(ids) & DECORATOR_IDS))


def classify(ids: Sequence[str]) -> str:
    s = set(ids)
    extras = s & u.EXTRA10
    if not extras:
        return "ACTIVE15_ONLY"
    if u.CONSTRAINED in extras:
        if s != {u.CONSTRAINED}:
            raise AssertionError("CONSTRAINED_MUST_BE_SINGLETON")
        return "K0_CONSTRAINED_SINGLETON"

    hard = extras & HARD_IDS
    if hard:
        # The only compatible special wrapper for a hard family is
        # TWO_RESPONSES with LANGUAGE. REPEAT and JSON cannot carry hard extras.
        if u.TWO in s:
            if u.LANGUAGE not in hard:
                raise AssertionError("TWO_HARD_WITHOUT_LANGUAGE")
            return "K4_TWO_LANGUAGE"
        if u.REPEAT in s or u.JSON_ID in s:
            raise AssertionError("HARD_EXTRA_ON_FORBIDDEN_SPECIAL_ROUTE")
        return "K3_HARD_GENERAL"

    # No hard family remains: only three source-local decorator families.
    if not extras <= DECORATOR_IDS:
        raise AssertionError("UNCLASSIFIED_EXTRA_FAMILY")

    # NO_COMMA is normally a response-local deletion constraint. Repeat-prompt
    # is the sole public route that must reproduce arbitrary visible source text,
    # so commas in that prefix can create a real mandatory-loss interaction.
    if u.REPEAT in s:
        if u.NO_COMMA not in extras:
            raise AssertionError("REPEAT_DECORATOR_WITHOUT_NO_COMMA")
        return "K2_REPEAT_NO_COMMA"
    return "K1_DECORATOR_GENERAL"


def verify() -> dict[str, Any]:
    base = u.verify()
    if base["status"] != "PASS__UNION25_STRUCTURAL_EXPLOSION_REDUCED_EXACTLY":
        raise AssertionError("UNION25_ARCHETYPE_BASE_NOT_VERIFIED")
    if base["distinct_extra10_signatures"] != 156:
        raise AssertionError("UNION25_SIGNATURE_COUNT_DRIFT")

    sets = u.enumerate_compatible_sets()
    counts = Counter(classify(ids) for ids in sets)
    if counts["ACTIVE15_ONLY"] != 928:
        raise AssertionError("ACTIVE15_COUNT_DRIFT")

    regimes = {k: counts[k] for k in EXPECTED_REGIME_COUNTS}
    if regimes != EXPECTED_REGIME_COUNTS:
        raise AssertionError(f"REGIME_COUNT_DRIFT:{regimes!r}")

    extra_sets = [ids for ids in sets if set(ids) & u.EXTRA10]
    if sum(regimes.values()) != len(extra_sets) or len(extra_sets) != 13631:
        raise AssertionError("EXTRA_PARTITION_TOTAL_DRIFT")

    extra_signatures = {
        u.extra_signature(ids)
        for ids in extra_sets
    }
    if len(extra_signatures) != 156:
        raise AssertionError("EXTRA_SIGNATURE_RECOMPUTE_DRIFT")

    hard_cores = {
        _hard_core(ids)
        for ids in extra_sets
        if set(ids) & HARD_IDS
    }
    if hard_cores != EXPECTED_HARD_CORES:
        raise AssertionError("HARD_CORE_SET_DRIFT")

    decorator_signatures = {
        _decorator_signature(ids)
        for ids in extra_sets
        if (set(ids) & u.EXTRA10) <= DECORATOR_IDS
    }
    if decorator_signatures != EXPECTED_DECORATOR_SIGNATURES:
        raise AssertionError("DECORATOR_SIGNATURE_SET_DRIFT")

    hard_core_structure_counts: dict[str, int] = defaultdict(int)
    for ids in extra_sets:
        core = _hard_core(ids)
        if core:
            hard_core_structure_counts[" + ".join(core)] += 1

    # Exact special-route identities. These are tiny enough to preserve
    # literally rather than approximate away.
    repeat_no_comma = [
        tuple(ids) for ids in extra_sets
        if classify(ids) == "K2_REPEAT_NO_COMMA"
    ]
    two_language = [
        tuple(ids) for ids in extra_sets
        if classify(ids) == "K4_TWO_LANGUAGE"
    ]
    if len(repeat_no_comma) != 4 or len(two_language) != 4:
        raise AssertionError("SPECIAL_ROUTE_COUNT_DRIFT")

    return {
        "schema": SCHEMA,
        "status": "PASS__UNION25_156_SIGNATURES_REDUCED_TO_19_HARD_CORES_PLUS_FOUR_PROOF_REGIMES",
        "bound_archetypes_blob": BOUND_ARCHETYPES_BLOB,
        "input": {
            "compatible_union25_structures": 14559,
            "active15_structures": 928,
            "extra_bearing_structures": 13631,
            "extra_family_signatures": 156,
        },
        "interaction_partition": regimes,
        "hard_kernel": {
            "family_ids": sorted(HARD_IDS),
            "distinct_compatible_hard_cores": len(hard_cores),
            "hard_cores": [list(x) for x in sorted(hard_cores)],
            "structure_counts_by_hard_core": dict(sorted(hard_core_structure_counts.items())),
            "general_structures": counts["K3_HARD_GENERAL"],
            "two_response_language_structures": counts["K4_TWO_LANGUAGE"],
        },
        "decorator_kernel": {
            "family_ids": sorted(DECORATOR_IDS),
            "distinct_nonempty_signatures": len(decorator_signatures),
            "signatures": [list(x) for x in sorted(decorator_signatures)],
            "general_structures": counts["K1_DECORATOR_GENERAL"],
            "repeat_no_comma_exceptions": [list(x) for x in repeat_no_comma],
        },
        "direct_singleton_kernel": {
            "instruction_id": u.CONSTRAINED,
            "structure_count": counts["K0_CONSTRAINED_SINGLETON"],
        },
        "critical_path": {
            "previous_obligations": 156,
            "new_primary_hard_cores": 19,
            "special_route_exception_structures": 8,
            "decorator_general_proof_regimes": 1,
            "direct_singleton_proof_regimes": 1,
            "next": (
                "BUILD_ONE_PARAMETRIC_CONSTRUCTOR_POSTVALIDATOR_FOR_THE_19_HARD_"
                "CORES__ONE_DECORATOR_NEUTRALITY_THEOREM__AND_EXHAUST_THE_8_"
                "SPECIAL_ROUTE_STRUCTURES"
            ),
        },
        "terminal_rows_used": 0,
        "hidden_kwargs_used": 0,
        "target_scores_used": 0,
        "acceptance_credit": False,
        "capability_credit": False,
        "hard_nonclaims": [
            "THIS_IS_AN_EXACT_OBLIGATION_REDUCTION_NOT_A_COMPOSITION_PASS",
            "DECORATOR_NEUTRALITY_IS_NOT_CLAIMED_BY_STRUCTURE_ALONE",
            "NO_LIVEBENCH_PREDICATE_PROMOTION_UNTIL_CONSTRUCTION_AND_INDEPENDENT_POSTVALIDATION_CLOSE_THE_REDUCED_KERNEL",
        ],
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
