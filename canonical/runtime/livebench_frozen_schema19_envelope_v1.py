#!/usr/bin/env python3
"""Assumption-free frozen-schema envelope for the LiveBench terminal predicate.

The exact frozen parquet kwargs struct cannot represent six registry families
whose required argument fields are absent.  Therefore, without relying on the
paper's inconsistent 15-vs-16 scope description, every serialized checker
family is contained in a 19-family envelope: Active15 plus four no-argument
extras.  This shrinks the full registry25 structural proof target from 14,559
compatible sets / 156 extra signatures to 3,108 sets / 6 extra signatures.

No target row values, instruction IDs, hidden kwargs values, responses, or
scores are read.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from canonical.runtime import livebench_release_schema_scope_bridge_v1 as schema
from canonical.runtime import livebench_union25_archetypes_v1 as u

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_FROZEN_SCHEMA19_ENVELOPE_V1"
EXPECTED_ENVELOPE_FAMILIES = 19
EXPECTED_COMPATIBLE_BY_CARDINALITY = {1: 19, 2: 108, 3: 391, 4: 958, 5: 1632}
EXPECTED_COMPATIBLE_TOTAL = 3108
EXPECTED_ACTIVE15_TOTAL = 928
EXPECTED_EXTRA_BEARING_TOTAL = 2180
EXPECTED_EXTRA_SIGNATURES = 6

EXCLUDED_BY_FROZEN_SCHEMA = frozenset(schema.ARG_BEARING_EXTRAS)
SCHEMA19 = frozenset(u.ALL_IDS) - EXCLUDED_BY_FROZEN_SCHEMA
REMAINING_EXTRAS = SCHEMA19 - u.ACTIVE15


def verify() -> dict[str, Any]:
    upstream = schema.verify()
    excluded = frozenset(upstream["schema_excluded_extra_families"])
    if excluded != EXCLUDED_BY_FROZEN_SCHEMA:
        raise AssertionError("FROZEN_SCHEMA_EXCLUSION_DRIFT")
    if len(SCHEMA19) != EXPECTED_ENVELOPE_FAMILIES:
        raise AssertionError("SCHEMA19_FAMILY_COUNT_DRIFT")

    expected_remaining = frozenset({
        u.CONSTRAINED,
        u.ENGLISH_CAPITAL,
        u.ENGLISH_LOWERCASE,
        u.NO_COMMA,
    })
    if REMAINING_EXTRAS != expected_remaining:
        raise AssertionError("SCHEMA19_REMAINING_EXTRA_DRIFT")

    all_sets = u.enumerate_compatible_sets()
    envelope_sets = tuple(ids for ids in all_sets if set(ids) <= SCHEMA19)
    by_cardinality = dict(sorted(Counter(map(len, envelope_sets)).items()))
    if by_cardinality != EXPECTED_COMPATIBLE_BY_CARDINALITY:
        raise AssertionError("SCHEMA19_CARDINALITY_DRIFT")
    if len(envelope_sets) != EXPECTED_COMPATIBLE_TOTAL:
        raise AssertionError("SCHEMA19_TOTAL_DRIFT")

    active = tuple(ids for ids in envelope_sets if set(ids) <= u.ACTIVE15)
    if len(active) != EXPECTED_ACTIVE15_TOTAL:
        raise AssertionError("ACTIVE15_EMBEDDED_COUNT_DRIFT")

    extra_sets = tuple(ids for ids in envelope_sets if set(ids) & REMAINING_EXTRAS)
    if len(extra_sets) != EXPECTED_EXTRA_BEARING_TOTAL:
        raise AssertionError("SCHEMA19_EXTRA_BEARING_DRIFT")

    signatures = {
        tuple(iid for iid in u.ALL_IDS if iid in set(ids) and iid in REMAINING_EXTRAS)
        for ids in extra_sets
    }
    if len(signatures) != EXPECTED_EXTRA_SIGNATURES:
        raise AssertionError("SCHEMA19_EXTRA_SIGNATURE_COUNT_DRIFT")

    expected_signatures = {
        (u.CONSTRAINED,),
        (u.ENGLISH_CAPITAL,),
        (u.ENGLISH_LOWERCASE,),
        (u.NO_COMMA,),
        (u.ENGLISH_CAPITAL, u.NO_COMMA),
        (u.ENGLISH_LOWERCASE, u.NO_COMMA),
    }
    if signatures != expected_signatures:
        raise AssertionError("SCHEMA19_EXTRA_SIGNATURE_IDENTITY_DRIFT")

    return {
        "schema": SCHEMA,
        "status": "PASS__ASSUMPTION_FREE_FROZEN_SCHEMA19_ENVELOPE__REGISTRY25_14559_TO_SCHEMA19_3108__EXTRA156_TO6",
        "frozen_hf_revision": schema.FROZEN_HF_REVISION,
        "frozen_parquet_sha256": schema.FROZEN_PARQUET_SHA256,
        "frozen_kwargs_fields": sorted(schema.EXPECTED_KWARGS_FIELDS),
        "excluded_argument_bearing_families": sorted(EXCLUDED_BY_FROZEN_SCHEMA),
        "envelope_family_count": len(SCHEMA19),
        "envelope_families": [iid for iid in u.ALL_IDS if iid in SCHEMA19],
        "remaining_extra_families": [iid for iid in u.ALL_IDS if iid in REMAINING_EXTRAS],
        "compatible_by_cardinality": by_cardinality,
        "compatible_total": len(envelope_sets),
        "embedded_active15_total": len(active),
        "extra_bearing_total": len(extra_sets),
        "distinct_remaining_extra_signatures": len(signatures),
        "remaining_extra_signatures": [list(x) for x in sorted(signatures)],
        "reduction": {
            "union25_family_count": len(u.ALL_IDS),
            "schema19_family_count": len(SCHEMA19),
            "union25_compatible_total": u.EXPECTED_COMPATIBLE_TOTAL,
            "schema19_compatible_total": len(envelope_sets),
            "compatible_sets_deleted": u.EXPECTED_COMPATIBLE_TOTAL - len(envelope_sets),
            "union25_extra_signatures": u.EXPECTED_DISTINCT_EXTRA_SIGNATURES,
            "schema19_extra_signatures": len(signatures),
            "extra_signatures_deleted": u.EXPECTED_DISTINCT_EXTRA_SIGNATURES - len(signatures),
        },
        "assumption_boundary": "NONE_BEYOND_EXACT_FROZEN_PARQUET_SCHEMA_AND_PINNED_25_FAMILY_REGISTRY",
        "new_critical_path": "PROVE_POINTWISE_COMPOSITION_ONLY_FOR_SIX_SCHEMA19_EXTRA_SIGNATURES_ON_TOP_OF_ALREADY_VERIFIED_ACTIVE15",
        "terminal_rows_read": 0,
        "terminal_instruction_id_lists_read": 0,
        "hidden_kwargs_values_read": 0,
        "target_responses_read": 0,
        "target_scores_read": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "independent_verification_required": True,
    }


def run(args=None, root=None):
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
