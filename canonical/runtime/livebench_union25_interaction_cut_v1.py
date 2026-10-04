#!/usr/bin/env python3
"""Exact interaction cut for the frozen LiveBench union25 extension.

The union25 structural quotient leaves 156 signatures containing at least one
family outside the already-proved Active15 core.  Those ten extra families do
not form a ten-way interaction problem.

They factor exactly into:
  * six load-bearing semantic/count interaction families;
  * three passive syntax modifiers;
  * one conflict-isolated constrained-response singleton.

After quotienting away passive modifiers, only 20 distinct hard interaction
cores remain, and no hard core contains more than three families.

This is a scheduling/proof decomposition only.  It grants zero benchmark,
acceptance, family, capability, or ownership credit.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_union25_archetypes_v1 as u

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_INTERACTION_CUT_V1"

HARD = frozenset({
    u.KEYWORD_FREQUENCY,
    u.LETTER_FREQUENCY,
    u.LANGUAGE,
    u.CAPITAL_FREQUENCY,
    u.ENGLISH_CAPITAL,
    u.ENGLISH_LOWERCASE,
})

PASSIVE = frozenset({
    u.PLACEHOLDERS,
    u.HIGHLIGHTS,
    u.NO_COMMA,
})

ISOLATED = frozenset({u.CONSTRAINED})

EXPECTED_EXTRA_SIGNATURES = 156
EXPECTED_HARD_CORE_SIGNATURES = 20
EXPECTED_HARD_ARITY_HISTOGRAM = {0: 1, 1: 6, 2: 9, 3: 4}
EXPECTED_MAX_HARD_ARITY = 3

EXPECTED_HARD_CORES = {
    (),
    (u.CAPITAL_FREQUENCY,),
    (u.ENGLISH_CAPITAL,),
    (u.ENGLISH_LOWERCASE,),
    (u.KEYWORD_FREQUENCY,),
    (u.LETTER_FREQUENCY,),
    (u.LANGUAGE,),
    (u.KEYWORD_FREQUENCY, u.CAPITAL_FREQUENCY),
    (u.KEYWORD_FREQUENCY, u.ENGLISH_CAPITAL),
    (u.KEYWORD_FREQUENCY, u.ENGLISH_LOWERCASE),
    (u.KEYWORD_FREQUENCY, u.LETTER_FREQUENCY),
    (u.LETTER_FREQUENCY, u.CAPITAL_FREQUENCY),
    (u.LETTER_FREQUENCY, u.ENGLISH_CAPITAL),
    (u.LETTER_FREQUENCY, u.ENGLISH_LOWERCASE),
    (u.LETTER_FREQUENCY, u.LANGUAGE),
    (u.LANGUAGE, u.CAPITAL_FREQUENCY),
    (u.KEYWORD_FREQUENCY, u.LETTER_FREQUENCY, u.CAPITAL_FREQUENCY),
    (u.KEYWORD_FREQUENCY, u.LETTER_FREQUENCY, u.ENGLISH_CAPITAL),
    (u.KEYWORD_FREQUENCY, u.LETTER_FREQUENCY, u.ENGLISH_LOWERCASE),
    (u.LETTER_FREQUENCY, u.LANGUAGE, u.CAPITAL_FREQUENCY),
}


def _ordered(values: Sequence[str] | set[str] | frozenset[str]) -> tuple[str, ...]:
    s = set(values)
    return tuple(iid for iid in u.ALL_IDS if iid in s)


def hard_core(signature: Sequence[str]) -> tuple[str, ...]:
    return _ordered(set(signature) & HARD)


def passive_modifiers(signature: Sequence[str]) -> tuple[str, ...]:
    return _ordered(set(signature) & PASSIVE)


def classify_signature(signature: Sequence[str]) -> dict[str, Any]:
    sig = tuple(signature)
    s = set(sig)
    unknown = s - set(u.EXTRA10)
    if unknown:
        raise ValueError("NON_EXTRA10_ID:" + ",".join(sorted(unknown)))
    isolated = _ordered(s & ISOLATED)
    if isolated and len(s) != 1:
        raise ValueError("CONSTRAINED_RESPONSE_MUST_BE_SINGLETON")
    return {
        "signature": list(_ordered(s)),
        "hard_core": list(hard_core(sig)),
        "passive_modifiers": list(passive_modifiers(sig)),
        "isolated": list(isolated),
    }


def _reachable_extra_signatures() -> tuple[tuple[str, ...], ...]:
    signatures = {
        u.extra_signature(ids)
        for ids in u.enumerate_compatible_sets()
        if set(ids) & set(u.EXTRA10)
    }
    return tuple(sorted(signatures, key=lambda x: (len(x), x)))


def verify() -> dict[str, Any]:
    if HARD | PASSIVE | ISOLATED != set(u.EXTRA10):
        raise AssertionError("EXTRA10_PARTITION_NOT_EXHAUSTIVE")
    if (HARD & PASSIVE) or (HARD & ISOLATED) or (PASSIVE & ISOLATED):
        raise AssertionError("EXTRA10_PARTITION_NOT_DISJOINT")

    signatures = _reachable_extra_signatures()
    if len(signatures) != EXPECTED_EXTRA_SIGNATURES:
        raise AssertionError("EXTRA_SIGNATURE_COUNT_DRIFT")

    # The constrained checker conflicts with every other registry family, so it
    # is exactly one already-trivial route, not a composition dimension.
    constrained = [s for s in signatures if u.CONSTRAINED in s]
    if constrained != [(u.CONSTRAINED,)]:
        raise AssertionError("CONSTRAINED_SINGLETON_DRIFT")

    nonisolated = [s for s in signatures if u.CONSTRAINED not in s]
    cores = {hard_core(s) for s in nonisolated}
    if cores != EXPECTED_HARD_CORES:
        raise AssertionError("HARD_CORE_SET_DRIFT")

    arities = Counter(map(len, cores))
    if dict(sorted(arities.items())) != EXPECTED_HARD_ARITY_HISTOGRAM:
        raise AssertionError("HARD_ARITY_HISTOGRAM_DRIFT")
    if max(map(len, cores)) != EXPECTED_MAX_HARD_ARITY:
        raise AssertionError("MAX_HARD_ARITY_DRIFT")

    # Every passive modifier is pairwise compatible with every hard family.
    # Therefore passive families can be handled as orthogonal response
    # decorators after the hard core construction, subject only to interaction
    # with the already-known Active15 context.
    for p in PASSIVE:
        for h in HARD:
            if not u.compatible((p, h)):
                raise AssertionError(f"PASSIVE_HARD_CONFLICT_DRIFT:{p}:{h}")

    passive_subset_hist = Counter(len(passive_modifiers(s)) for s in nonisolated)
    hard_core_occurrence_hist = Counter(len(hard_core(s)) for s in nonisolated)

    hard_triples = sorted(
        (list(x) for x in cores if len(x) == 3),
        key=lambda x: tuple(x),
    )

    return {
        "schema": SCHEMA,
        "status": "PASS__UNION25_156_SIGNATURES_FACTOR_TO_20_HARD_CORES_MAX_ARITY_3",
        "union25_compatible_structural_sets": 14559,
        "extra_bearing_structural_sets": 13631,
        "raw_extra10_signatures": len(signatures),
        "isolated_signature_count": 1,
        "isolated_signature": [u.CONSTRAINED],
        "nonisolated_extra_signatures": len(nonisolated),
        "hard_family_count": len(HARD),
        "passive_family_count": len(PASSIVE),
        "hard_core_signature_count": len(cores),
        "hard_core_reduction_factor": len(signatures) / len(cores),
        "hard_core_arity_histogram": dict(sorted(arities.items())),
        "max_hard_core_arity": max(map(len, cores)),
        "hard_triples": hard_triples,
        "hard_families": list(_ordered(HARD)),
        "passive_families": list(_ordered(PASSIVE)),
        "passive_subset_size_histogram_over_nonisolated_signatures": dict(
            sorted(passive_subset_hist.items())
        ),
        "hard_arity_histogram_over_nonisolated_signatures": dict(
            sorted(hard_core_occurrence_hist.items())
        ),
        "proof_obligations": {
            "hard_core": (
                "SOLVE_AND_POINTWISE_POSTVALIDATE_ONLY_THE_20_HARD_INTERACTION_"
                "CORES_AGAINST_COMPATIBLE_ACTIVE15_CONTEXTS"
            ),
            "passive_lift": (
                "PROVE_PLACEHOLDER_HIGHLIGHT_NOCOMMA_DECORATORS_PRESERVE_THE_"
                "HARD_CORE_AND_ACTIVE15_CHECKER_VECTOR_EXCEPT_ALREADY_EXPLICIT_"
                "MANDATORY_COLLISIONS"
            ),
            "isolated": (
                "CONSTRAINED_RESPONSE_IS_SINGLETON_AND_ALREADY_HAS_AN_"
                "INDEPENDENTLY_VERIFIED_SINGLE_CONTRACT_WITNESS"
            ),
        },
        "terminal_rows_used": False,
        "hidden_kwargs_used": False,
        "instruction_id_list_used": False,
        "target_scores_used": False,
        "model_dependency_count": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
