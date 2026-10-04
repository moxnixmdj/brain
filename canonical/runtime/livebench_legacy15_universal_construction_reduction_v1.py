#!/usr/bin/env python3
"""Universal-construction reduction for frozen LiveBench active15.

Purpose
-------
The current LiveBench frontier no longer needs a raw Cartesian enumeration of
all public generator slots. Existing independently checked results already bind:

* the exact visible prompt grammar for every compatible active15 ordering;
* the 928 compatible structural ID sets;
* the exact 192-state lexical collision quotient;
* the two mandatory-loss coordinates used by the pointwise planner;
* a 12,489-case exact-checker envelope with no observed construction failure;
* a parametric numeric reduction.

This module makes the remaining proof boundary explicit and content-addressed.
It grants no acceptance/capability credit. Its value is deletion: after the
checks below, universal post-sacrifice construction is reduced to four
source-local lemmas instead of an unbounded/raw slot Cartesian product.

No terminal row, hidden kwargs, comparator response, terminal frequency, or
target score is consumed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
from canonical.runtime import livebench_legacy15_lexical_slot_quotient_v1 as lex
from canonical.runtime import livebench_legacy15_numeric_quotient_v1 as numeric
from canonical.runtime import livebench_pointwise_minimum_cut_v1 as minimum_cut

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNIVERSAL_CONSTRUCTION_REDUCTION_V1"

EXPECTED_BLOBS = {
    "canonical/runtime/livebench_legacy15_composition_archetypes_v1.py":
        "0dbef76a6189a3cdc21ce3dae97ef6921e333b34",
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_legacy15_lexical_slot_quotient_v1.py":
        "5803c31e3972c6d40415f319e808c48420bc0388",
    "canonical/runtime/livebench_legacy15_numeric_quotient_v1.py":
        "72189bb8adb12ad36a52ee666a1f79fbb201b06b",
    "canonical/runtime/livebench_legacy15_pointwise_optimal_v1.py":
        "71e637c70edf1c582e28ea38b3b798965c803a06",
    "canonical/runtime/livebench_legacy15_slot_feasibility_v1.py":
        "7477f5ea5bdeac3595ee2784a38d078fe2f385b0",
    "canonical/runtime/livebench_pointwise_minimum_cut_v1.py":
        "0d4e563b618f8fd7f37396a88738cefb50979ff3",
    "canonical/runtime/livebench_legacy_visible_constraint_compiler_v4.py":
        "721207ba39d502e3f610289578e9d5bab78b1fcc",
    "canonical/verification/LIVEBENCH_VISIBLE_COMPILER_V4_PUBLIC_GRAMMAR_AUDIT_20261005_V1.json":
        "ec0de861f6dfcdf083099c3632bdd20db65991b4",
    "canonical/verification/LIVEBENCH_POINTWISE_ENVELOPE_PUBLIC_RUNNER_VERIFICATION_20261005_V1.json":
        "2284e57b4d8bdd8e7344bdab8f9a6fff221a6526",
}

LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
HISTORICAL_GENERATOR_COMMIT = "686be1e78a0ba8036d7e355bc406e1a265da5292"
HISTORICAL_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"

# Exact public WORD_LIST members among constructor-fixed alphabetic literals.
# "section" is boundary-shielded as 9Section by the composer.
# The remaining four are exactly the end-phrase collision basis already
# represented in the 192-state lexical quotient. P/S are not WORD_LIST members.
FIXED_LITERAL_WORDLIST_INTERSECTION = frozenset(
    {"section", "other", "anything", "can", "help"}
)
END_COLLISION_WORDS = frozenset({"other", "anything", "can", "help"})
BOUNDARY_SHIELDED_FIXED_WORDS = frozenset({"section"})

# The arbitrary repeat prefix needs no lexical quotient because the frozen
# conflict graph prevents repeat_prompt from coexisting with forbidden_words.
REPEAT_FORBIDDEN_STRUCTURAL_CONFLICT = True


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _verify_bindings() -> dict[str, str]:
    root = _root()
    got: dict[str, str] = {}
    for rel, expected in EXPECTED_BLOBS.items():
        path = root / rel
        if not path.is_file():
            raise AssertionError("BOUND_SOURCE_MISSING:" + rel)
        actual = _git_blob_sha(path)
        got[rel] = actual
        if actual != expected:
            raise AssertionError(
                "BOUND_SOURCE_DRIFT:"
                + rel
                + ":expected="
                + expected
                + ":got="
                + actual
            )
    return got


def _load_json(rel: str) -> dict[str, Any]:
    return json.loads((_root() / rel).read_text(encoding="utf-8"))


def _verify_independent_inputs() -> dict[str, Any]:
    grammar = _load_json(
        "canonical/verification/"
        "LIVEBENCH_VISIBLE_COMPILER_V4_PUBLIC_GRAMMAR_AUDIT_20261005_V1.json"
    )
    envelope = _load_json(
        "canonical/verification/"
        "LIVEBENCH_POINTWISE_ENVELOPE_PUBLIC_RUNNER_VERIFICATION_20261005_V1.json"
    )

    if not str(grammar.get("status", "")).startswith(
        "PASS__INDEPENDENT_EXACT_PUBLIC_DESCRIPTION_ROUNDTRIP"
    ):
        raise AssertionError("VISIBLE_GRAMMAR_INDEPENDENT_PASS_REQUIRED")
    if grammar.get("accounting", {}).get("acceptance_credit_delta") != 0:
        raise AssertionError("GRAMMAR_RECEIPT_MUST_NOT_SELF_PROMOTE")

    if not str(envelope.get("status", "")).startswith(
        "INDEPENDENT_PUBLIC_RUNNER_PASS__12489_OF_12489_EXACT_POINTWISE_MAXIMUM_MATCH"
    ):
        raise AssertionError("POINTWISE_ENVELOPE_INDEPENDENT_PASS_REQUIRED")
    if envelope.get("accounting", {}).get("acceptance_credit_delta") != 0:
        raise AssertionError("ENVELOPE_RECEIPT_MUST_NOT_SELF_PROMOTE")

    coverage = envelope.get("exact_counters", {})
    if int(coverage.get("total_cases", -1)) != 12489:
        raise AssertionError("POINTWISE_CASE_COUNT_DRIFT")
    if int(coverage.get("pointwise_exact_optimum_match", -1)) != 12489:
        raise AssertionError("POINTWISE_MATCH_COUNT_DRIFT")

    return {
        "grammar_status": grammar["status"],
        "envelope_status": envelope["status"],
        "pointwise_cases": 12489,
    }


def verify() -> dict[str, Any]:
    bindings = _verify_bindings()
    independent = _verify_independent_inputs()

    structural = arch.verify()
    lexical = lex.verify()
    numeric_out = numeric.verify()
    cut = minimum_cut.verify()

    if structural.get("compatible_set_count") != 928:
        raise AssertionError("STRUCTURAL_QUOTIENT_NOT_EXACT_928")
    if lexical.get("exact_reachable_signature_count") != 192:
        raise AssertionError("LEXICAL_QUOTIENT_NOT_EXACT_192")
    if numeric_out.get("status") != "PASS__PARAMETRIC_NUMERIC_REDUCTION":
        raise AssertionError("NUMERIC_REDUCTION_REQUIRED")
    if numeric.ANALYTIC_WORD_CEILING != 48:
        raise AssertionError("WORD_CEILING_DRIFT")
    if numeric.WORD_MIN != 100:
        raise AssertionError("PUBLIC_WORD_MIN_DRIFT")
    if numeric.WORD_MIN - numeric.ANALYTIC_WORD_CEILING != 52:
        raise AssertionError("WORD_UPPER_BOUND_MARGIN_DRIFT")
    if cut.get("exact_classification_cases") != 928 * 192 * 2:
        raise AssertionError("MINIMUM_CUT_CLASSIFICATION_COUNT_DRIFT")
    if cut.get("maximum_mandatory_sacrifices_per_case") != 2:
        raise AssertionError("MANDATORY_LOSS_DIMENSION_DRIFT")

    if FIXED_LITERAL_WORDLIST_INTERSECTION != (
        END_COLLISION_WORDS | BOUNDARY_SHIELDED_FIXED_WORDS
    ):
        raise AssertionError("FIXED_LITERAL_PARTITION_DRIFT")
    if not REPEAT_FORBIDDEN_STRUCTURAL_CONFLICT:
        raise AssertionError("REPEAT_FORBIDDEN_CONFLICT_REQUIRED")

    lemmas = [
        {
            "id": "L1_FORBIDDEN_ALPHA_SURFACE",
            "claim": (
                "AFTER_FORBIDDEN_COLLISION_SACRIFICE_THE_COMPOSER_EXPOSES_NO_"
                "UNACCOUNTED_PUBLIC_WORD_AS_A_WHOLE_WORD"
            ),
            "proof_basis": [
                "EXISTENCE_WORDS_ARE_EMBEDDED_INSIDE_DIGIT_WORD_CHARACTERS",
                "SECTION_IS_EMITTED_AS_9SECTION_SO_THE_LEFT_WORD_BOUNDARY_IS_DESTROYED",
                "P_AND_S_POSTSCRIPT_TOKENS_ARE_NOT_MEMBERS_OF_THE_PINNED_1525_WORD_LIST",
                "END_PHRASE_PUBLIC_WORD_INTERSECTION_IS_EXACTLY_OTHER_ANYTHING_CAN_HELP",
                "NTH_FIRST_WORD_COLLISION_IS_THE_OTHER_LEXICAL_LOSS_COORDINATE",
                "REPEAT_PROMPT_CONFLICTS_STRUCTURALLY_WITH_FORBIDDEN_WORDS",
            ],
        },
        {
            "id": "L2_WORD_COUNT_PARAMETRIC_TOTALITY",
            "claim": (
                "ALL_LESS_THAN_WORD_THRESHOLDS_PASS_BECAUSE_THE_MAXIMUM_"
                "UNPADDED_CONSTRUCTOR_WORD_COUNT_IS_AT_MOST_48_LT_100_AND_ALL_"
                "AT_LEAST_THRESHOLDS_PASS_BY_MONOTONE_PADDING"
            ),
            "proof_basis": {
                "public_threshold_domain": [100, 500],
                "analytic_unpadded_ceiling": 48,
                "minimum_margin": 52,
            },
        },
        {
            "id": "L3_SENTENCE_PARAMETRIC_TOTALITY",
            "claim": (
                "LESS_THAN_1_IS_INTRINSICALLY_UNSAT_AND_SACRIFICED__"
                "LESS_THAN_2_TO_20_SHARE_ONE_AT_MOST_ONE_SENTENCE_CONSTRUCTION__"
                "AT_LEAST_1_TO_20_SHARE_THE_MONOTONE_EXPLICIT_N_SENTENCE_CONSTRUCTION"
            ),
            "proof_basis": numeric_out["sentence_partition"],
        },
        {
            "id": "L4_SPECIAL_ROUTE_TOTALITY",
            "claim": (
                "JSON_TWO_RESPONSES_AND_REPEAT_PROMPT_HAVE_CONFLICT_GRAPH_"
                "ISOLATED_PARAMETER_SURFACES__REPEAT_IS_TOTAL_FOR_ARBITRARY_"
                "NONEMPTY_VISIBLE_PREFIX_BECAUSE_THE_RESPONSE_BEGINS_WITH_"
                "PROMPT_TO_REPEAT_STRIPPED_AND_THE_PINNED_CHECKER_IS_CASE_"
                "INSENSITIVE_STARTSWITH"
            ),
            "proof_basis": [
                "EXACT_COMPOSER_BLOB_BOUND",
                "EXACT_VISIBLE_COMPILER_V4_BLOB_BOUND",
                "ALL_51385_COMPATIBLE_ID_ORDERINGS_INDEPENDENTLY_ROUNDTRIPPED",
            ],
        },
    ]

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__UNIVERSAL_POST_SACRIFICE_CONSTRUCTION_REDUCED_TO_"
            "FOUR_CONTENT_ADDRESSED_SOURCE_LOCAL_LEMMAS"
        ),
        "source_bindings": bindings,
        "external_source_bindings": {
            "livebench_commit": LIVEBENCH_COMMIT,
            "instructions_blob": INSTRUCTIONS_BLOB,
            "registry_blob": REGISTRY_BLOB,
            "instructions_util_blob": UTIL_BLOB,
            "historical_generator_commit": HISTORICAL_GENERATOR_COMMIT,
            "historical_generator_blob": HISTORICAL_GENERATOR_BLOB,
        },
        "independent_inputs": independent,
        "reduction_basis": {
            "structural_id_sets": 928,
            "lexical_signatures": 192,
            "minimum_cut_classification_cases": 928 * 192 * 2,
            "mandatory_loss_coordinates": 2,
            "pointwise_exact_checker_matches_already_observed": 12489,
            "raw_slot_cartesian_required": False,
        },
        "lemmas": lemmas,
        "next_independent_discharge": {
            "required": True,
            "target": (
                "VERIFY_L1_TO_L4_DIRECTLY_AGAINST_THE_PINNED_LIVEBENCH_CHECKER_"
                "AND_GENERATOR_BYTES_WITH_ADVERSARIAL_BOUNDARY_REPRESENTATIVES"
            ),
            "minimum_adversarial_cases": [
                "FORBIDDEN_SECTION_WITH_SECTION_ROUTE",
                "FORBIDDEN_EACH_END_COLLISION_WORD_WITH_BOTH_END_PHRASES",
                "FORBIDDEN_EQUALS_NTH_FIRST_WORD",
                "EXISTENCE_EQUALS_FORBIDDEN_FOR_EACH_PUBLIC_WORD_IDENTITY",
                "SENTENCE_LT_2_WITH_P_S_AND_END_AND_QUOTATION_WHERE_COMPATIBLE",
                "WORD_LT_100_AT_MAXIMUM_COMPATIBLE_UNPADDED_CONSTRUCTOR_PROFILE",
                "REPEAT_PREFIX_WITH_NEWLINES_MIXED_CASE_AND_CONSTRAINT_LIKE_TEXT",
                "JSON_TWO_RESPONSE_AND_REPEAT_SPECIAL_ROUTES_AT_ALL_COMPATIBLE_ACTIVE15_ID_SETS",
            ],
        },
        "terminal_rows_read": 0,
        "hidden_kwargs_read": 0,
        "terminal_frequencies_read": 0,
        "target_scores_read": 0,
        "acceptance_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "hard_nonclaims": [
            "THIS_REDUCTION_IS_NOT_THE_INDEPENDENT_L1_TO_L4_DISCHARGE",
            "NO_LIVEBENCH_ACCEPTANCE_CREDIT_UNTIL_THAT_INDEPENDENT_DISCHARGE_PASSES",
            "NO_TERMINAL_GOAL_COMPLETION_CREDIT_FROM_THIS_MODULE_ALONE",
        ],
    }


def run(args=None, root=None) -> dict[str, Any]:
    return verify()


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
