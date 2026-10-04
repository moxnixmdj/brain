#!/usr/bin/env python3
"""Metadata-only LiveBench release scope bridge from the frozen HF schema.

Purpose
-------
Reduce the public 15-vs-16-vs-24-vs-25 scope ambiguity without reading a
single terminal row, instruction_id_list, prompt, hidden kwarg value, response,
frequency, or target score.

The exact frozen Hugging Face parquet bound elsewhere in Brain has a fixed
Arrow kwargs struct. A checker family whose public build_description requires a
named kwarg field that is absent from that struct cannot occur in any serialized
row of those exact parquet bytes.

This theorem intentionally does NOT infer more than the metadata proves.
The frozen schema deletes six argument-bearing extra families. Four no-argument
families remain schema-indistinguishable. Combining that fact with the two
first-party paper surfaces (15 visible Table-4 checkmarks vs prose "subset of
16") gives an ambiguity-robust envelope of Active15 plus at most one of those
four no-argument families, conditional on at least one paper representation
being faithful to the release scope.

No acceptance credit is granted here. The next proof target is pointwise
optimality on the four Active15+1 supersets, which subsumes both public paper
interpretations without guessing which one is the typo.
"""
from __future__ import annotations

from typing import Any, Iterable

from canonical.runtime import livebench_union25_archetypes_v1 as u

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_RELEASE_SCHEMA_SCOPE_BRIDGE_V1"

FROZEN_HF_REVISION = "0868379c4b5cf62aeacaf8be4f08fced815c81bb"
FROZEN_PARQUET_SHA256 = "a9bb97bbaf8788142c310bcb33d50e2f6f5df8cbd8b8c3db677816b06f0f4f25"
FROZEN_PARQUET_BYTES = 537024
FROZEN_RELEASE = "2026-06-25"

# Exact kwargs struct fields published for the frozen 400-row parquet schema.
# This is a schema-level union, not values from any target row.
EXPECTED_KWARGS_FIELDS = frozenset({
    "num_bullets",
    "num_paragraphs",
    "num_words",
    "relation",
    "forbidden_words",
    "section_spliter",
    "num_sections",
    "keywords",
    "end_phrase",
    "postscript_marker",
    "num_sentences",
    "nth_paragraph",
    "first_word",
    "prompt_to_repeat",
})

# Every one of these frozen checker families requires at least one unique kwarg
# absent from EXPECTED_KWARGS_FIELDS. A row using that checker could not be
# represented by the exact frozen Arrow struct.
ARG_BEARING_EXTRAS = {
    u.KEYWORD_FREQUENCY: frozenset({"keyword", "frequency"}),
    u.LETTER_FREQUENCY: frozenset({"letter", "let_frequency", "let_relation"}),
    u.LANGUAGE: frozenset({"language"}),
    u.PLACEHOLDERS: frozenset({"num_placeholders"}),
    u.HIGHLIGHTS: frozenset({"num_highlights"}),
    u.CAPITAL_FREQUENCY: frozenset({"capital_frequency", "capital_relation"}),
}

NOARG_EXTRAS = frozenset({
    u.CONSTRAINED,
    u.ENGLISH_CAPITAL,
    u.ENGLISH_LOWERCASE,
    u.NO_COMMA,
})

TABLE4_VISIBLE_CHECKMARK_COUNT = 15
PAPER_PROSE_SUBSET_COUNT = 16


def schema_excluded_families(kwargs_fields: Iterable[str]) -> frozenset[str]:
    fields = frozenset(map(str, kwargs_fields))
    return frozenset(
        family
        for family, required in ARG_BEARING_EXTRAS.items()
        if not required <= fields
    )


def ambiguity_robust_scope_envelope(kwargs_fields: Iterable[str]) -> dict[str, Any]:
    fields = frozenset(map(str, kwargs_fields))
    if fields != EXPECTED_KWARGS_FIELDS:
        raise ValueError("FROZEN_HF_KWARGS_SCHEMA_DRIFT")

    excluded = schema_excluded_families(fields)
    if excluded != frozenset(ARG_BEARING_EXTRAS):
        raise AssertionError("ARG_BEARING_EXTRA_EXCLUSION_DRIFT")

    active = frozenset(u.ACTIVE15)
    extra10 = frozenset(u.EXTRA10)
    if extra10 != frozenset(ARG_BEARING_EXTRAS) | NOARG_EXTRAS:
        raise AssertionError("EXTRA10_PARTITION_DRIFT")

    # The two first-party paper surfaces disagree by exactly one family:
    # visible Table-4 checkmarks=15, prose count=16. Metadata proves any possible
    # 16th serialized family must be one of NOARG_EXTRAS.
    candidate_scopes = [active]
    candidate_scopes.extend(active | {x} for x in sorted(NOARG_EXTRAS))

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__FROZEN_PARQUET_SCHEMA_EXCLUDES_SIX_ARGUMENT_BEARING_EXTRAS__"
            "PUBLIC_15_VS_16_DISAGREEMENT_REDUCED_TO_FOUR_ACTIVE15_PLUS_ONE_SUPERSETS"
        ),
        "frozen_hf_revision": FROZEN_HF_REVISION,
        "frozen_parquet_sha256": FROZEN_PARQUET_SHA256,
        "frozen_parquet_bytes": FROZEN_PARQUET_BYTES,
        "release": FROZEN_RELEASE,
        "kwargs_schema_fields": sorted(fields),
        "schema_excluded_extra_families": sorted(excluded),
        "schema_indistinguishable_noarg_extras": sorted(NOARG_EXTRAS),
        "paper_surfaces": {
            "visible_table4_checkmarks": TABLE4_VISIBLE_CHECKMARK_COUNT,
            "prose_subset_count": PAPER_PROSE_SUBSET_COUNT,
            "disagreement_width": PAPER_PROSE_SUBSET_COUNT - TABLE4_VISIBLE_CHECKMARK_COUNT,
        },
        "candidate_scope_count_under_paper_faithfulness_assumption": len(candidate_scopes),
        "candidate_scopes": [sorted(x) for x in candidate_scopes],
        "proof_obligation_reduction": {
            "old_ambiguity_free_superset": "FULL_REGISTRY25__14559_STRUCTURAL_SETS",
            "new_conditional_envelope": (
                "ACTIVE15_OR_ACTIVE15_PLUS_EXACTLY_ONE_OF_FOUR_NOARG_EXTRAS"
            ),
            "sufficient_next_theorem": (
                "POINTWISE_OPTIMALITY_OVER_EACH_OF_FOUR_ACTIVE15_PLUS_ONE_SUPERSETS"
            ),
        },
        "assumption_boundary": (
            "AT_LEAST_ONE_OF_THE_TWO_FIRST_PARTY_PAPER_SCOPE_REPRESENTATIONS_"
            "IS_FAITHFUL_TO_THE_RELEASE_SCOPE__TABLE_VISIBLE_15_OR_PROSE_COUNT_16"
        ),
        "hard_nonclaims": [
            "SCHEMA_METADATA_ALONE_DOES_NOT_EXCLUDE_THE_FOUR_NOARG_FAMILIES",
            "THIS_MODULE_DOES_NOT_ASSERT_WHETHER_THE_TABLE_15_OR_PROSE_16_IS_CORRECT",
            "IF_BOTH_PAPER_SCOPE_REPRESENTATIONS_ARE_WRONG_THE_AT_MOST_ONE_EXTRA_BOUND_DOES_NOT_FOLLOW",
            "NO_TERMINAL_ROW_CONTENT_OR_INSTRUCTION_ID_LIST_IS_READ",
            "NO_LIVEBENCH_ACCEPTANCE_CREDIT",
        ],
        "terminal_rows_read": 0,
        "terminal_instruction_id_lists_read": 0,
        "hidden_kwargs_values_read": 0,
        "target_scores_read": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
    }


def verify() -> dict[str, Any]:
    out = ambiguity_robust_scope_envelope(EXPECTED_KWARGS_FIELDS)
    if len(out["schema_excluded_extra_families"]) != 6:
        raise AssertionError("SCHEMA_EXCLUDED_COUNT_DRIFT")
    if len(out["schema_indistinguishable_noarg_extras"]) != 4:
        raise AssertionError("NOARG_EXTRA_COUNT_DRIFT")
    if out["candidate_scope_count_under_paper_faithfulness_assumption"] != 5:
        raise AssertionError("CANDIDATE_SCOPE_COUNT_DRIFT")
    return out


def run(args=None, root=None):
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
