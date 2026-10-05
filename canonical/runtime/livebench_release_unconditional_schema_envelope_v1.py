#!/usr/bin/env python3
"""Unconditional LiveBench 2026-06-25 IF scope envelope from frozen parquet schema.

This strengthens livebench_release_schema_scope_bridge_v1 by removing its paper
faithfulness assumption entirely.

The exact frozen parquet kwargs struct cannot encode six argument-bearing
registry25 families. Therefore every frozen release row, regardless of whether
the paper's public "15" or "16" description is correct, lies inside:
    ACTIVE15 union any compatible subset of the four no-argument extras.

Enumerating only that exact conflict-graph envelope yields 3,108 compatible
structures, down from 14,559 registry25 structures, and only seven extra-family
signatures. No terminal row values or instruction-id lists are inspected.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from canonical.runtime import livebench_release_schema_scope_bridge_v1 as scope
from canonical.runtime import livebench_union25_archetypes_v1 as u

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_RELEASE_UNCONDITIONAL_SCHEMA_ENVELOPE_V1"

ALLOWED = frozenset(u.ACTIVE15) | scope.NOARG_EXTRAS
EXPECTED_ALLOWED_FAMILY_COUNT = 19
EXPECTED_COMPATIBLE_BY_CARDINALITY = {1: 19, 2: 108, 3: 391, 4: 958, 5: 1632}
EXPECTED_COMPATIBLE_TOTAL = 3108
EXPECTED_EXTRA_SIGNATURES = (
    (),
    (u.CONSTRAINED,),
    (u.ENGLISH_CAPITAL,),
    (u.ENGLISH_LOWERCASE,),
    (u.NO_COMMA,),
    (u.ENGLISH_CAPITAL, u.NO_COMMA),
    (u.ENGLISH_LOWERCASE, u.NO_COMMA),
)


def enumerate_envelope() -> tuple[tuple[str, ...], ...]:
    return tuple(
        ids
        for ids in u.enumerate_compatible_sets()
        if set(ids) <= ALLOWED
    )


def verify() -> dict[str, Any]:
    upstream = scope.verify()
    if set(upstream["schema_excluded_extra_families"]) != set(scope.ARG_BEARING_EXTRAS):
        raise AssertionError("UPSTREAM_SCHEMA_EXCLUSION_DRIFT")
    if len(ALLOWED) != EXPECTED_ALLOWED_FAMILY_COUNT:
        raise AssertionError("ALLOWED_FAMILY_COUNT_DRIFT")

    sets = enumerate_envelope()
    by_cardinality = Counter(map(len, sets))
    if dict(sorted(by_cardinality.items())) != EXPECTED_COMPATIBLE_BY_CARDINALITY:
        raise AssertionError(
            "UNCONDITIONAL_ENVELOPE_CARDINALITY_DRIFT:"
            + repr(dict(sorted(by_cardinality.items())))
        )
    if len(sets) != EXPECTED_COMPATIBLE_TOTAL:
        raise AssertionError("UNCONDITIONAL_ENVELOPE_TOTAL_DRIFT")

    signatures = tuple(sorted(
        {tuple(iid for iid in u.ALL_IDS if iid in ids and iid in scope.NOARG_EXTRAS)
         for ids in sets},
        key=lambda x: (len(x), x),
    ))
    expected = tuple(sorted(EXPECTED_EXTRA_SIGNATURES, key=lambda x: (len(x), x)))
    if signatures != expected:
        raise AssertionError("NOARG_EXTRA_SIGNATURE_DRIFT:" + repr(signatures))

    counts = Counter(
        tuple(iid for iid in u.ALL_IDS if iid in ids and iid in scope.NOARG_EXTRAS)
        for ids in sets
    )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__FROZEN_SCHEMA_UNCONDITIONALLY_REDUCES_RELEASE_SCOPE_TO_"
            "ACTIVE15_PLUS_COMPATIBLE_SUBSETS_OF_FOUR_NOARG_EXTRAS__"
            "3108_STRUCTURES__7_EXTRA_SIGNATURES"
        ),
        "frozen_hf_revision": scope.FROZEN_HF_REVISION,
        "frozen_parquet_sha256": scope.FROZEN_PARQUET_SHA256,
        "frozen_parquet_bytes": scope.FROZEN_PARQUET_BYTES,
        "allowed_family_count": len(ALLOWED),
        "allowed_families": [iid for iid in u.ALL_IDS if iid in ALLOWED],
        "schema_excluded_argument_bearing_extras": sorted(scope.ARG_BEARING_EXTRAS),
        "remaining_noarg_extras": [iid for iid in u.ALL_IDS if iid in scope.NOARG_EXTRAS],
        "compatible_by_cardinality": dict(sorted(by_cardinality.items())),
        "compatible_total": len(sets),
        "extra_signatures": [list(x) for x in signatures],
        "extra_signature_structure_counts": {
            "|".join(sig) if sig else "ACTIVE15_ONLY": count
            for sig, count in sorted(counts.items(), key=lambda kv: (len(kv[0]), kv[0]))
        },
        "proof_obligation_reduction": {
            "old_full_registry25_structures": u.EXPECTED_COMPATIBLE_TOTAL,
            "old_full_registry25_extra_signatures": u.EXPECTED_DISTINCT_EXTRA_SIGNATURES,
            "new_unconditional_release_envelope_structures": len(sets),
            "new_noarg_extra_signatures": len(signatures),
            "paper_15_vs_16_faithfulness_assumption_required": False,
            "response_language_required": False,
            "keyword_frequency_required": False,
            "letter_frequency_required": False,
            "placeholders_required": False,
            "highlights_required": False,
            "capital_word_frequency_required": False,
        },
        "remaining_pointwise_extension_classes": [
            "CONSTRAINED_SINGLETON",
            "ENGLISH_CAPITAL",
            "ENGLISH_LOWERCASE",
            "NO_COMMA",
            "ENGLISH_CAPITAL_PLUS_NO_COMMA",
            "ENGLISH_LOWERCASE_PLUS_NO_COMMA",
        ],
        "terminal_rows_read": 0,
        "terminal_instruction_id_lists_read": 0,
        "hidden_kwargs_values_read": 0,
        "target_responses_read": 0,
        "target_scores_read": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "next_load_bearing_problem": (
            "PROVE_POINTWISE_OPTIMALITY_FOR_SIX_NOARG_EXTENSION_CLASSES_OVER_"
            "THE_ALREADY_CLOSED_ACTIVE15_CORE"
        ),
    }


def run(args=None, root=None):
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
