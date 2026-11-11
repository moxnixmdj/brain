#!/usr/bin/env python3
"""Falsify the generator-support universal-threshold proof route for LiveBench IF.

This theorem uses the smallest clean public counterexample we found.

The historical generator can pair:
- keywords:forbidden_words, whose default draws exactly five distinct WORD_LIST
  entries, including samples that contain "help"; and
- startend:end_checker, whose public option set includes the mandatory suffix
  "Is there anything else I can help with?".

The two instruction IDs are conflict-compatible. Any response satisfying the
EndChecker must contain the standalone word "help" in its mandatory suffix.
ForbiddenWords rejects that same whole word. Hence this generator-admitted
slot tuple is jointly UNSAT.

For a two-checker row that cannot make both booleans true, the frozen public
LiveBench IF score is at most 1/4. Therefore no universal per-row lower-bound
proof over the entire generator support can establish the 65.7% target.

This does not claim that the fixed 200-row benchmark population contains the
counterexample. It proves only that generator-support universality is the wrong
acceptance target. Population-specific score mass is still required.

No terminal row, hidden kwarg, terminal response, row frequency, or terminal
score is read by this module.
"""
from __future__ import annotations

from fractions import Fraction

from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feasibility
from canonical.runtime.livebench_if_score_bound_v1 import exact_score_from_checker_results

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_GENERATOR_SUPPORT_THRESHOLD_ROUTE_FALSIFIER_V3"

TARGET_PREDICATE_FLOOR = Fraction(657, 1000)  # 65.7%
COLLISION_WORD = "help"
MANDATORY_END_PHRASE = "Is there anything else I can help with?"
REACHABLE_FORBIDDEN_WORDS = (
    "help",
    "rock",
    "western",
    "sentence",
    "signal",
)
COUNTEREXAMPLE_IDS = (
    "keywords:forbidden_words",
    "startend:end_checker",
)

PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_INSTRUCTIONS_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
HISTORICAL_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"


def _reachable_unsat_contracts() -> list[dict]:
    return [
        {
            "instruction_id": "keywords:forbidden_words",
            "slots": {"forbidden_words": list(REACHABLE_FORBIDDEN_WORDS)},
        },
        {
            "instruction_id": "startend:end_checker",
            "slots": {"end_phrase": MANDATORY_END_PHRASE},
        },
    ]


def verify() -> dict:
    if len(REACHABLE_FORBIDDEN_WORDS) != 5 or len(set(REACHABLE_FORBIDDEN_WORDS)) != 5:
        raise RuntimeError("FORBIDDEN_SAMPLE_CARDINALITY_DRIFT")
    if COLLISION_WORD not in REACHABLE_FORBIDDEN_WORDS:
        raise RuntimeError("COLLISION_WORD_MISSING_FROM_FORBIDDEN_SAMPLE")
    if COLLISION_WORD.casefold() not in MANDATORY_END_PHRASE.casefold().split():
        raise RuntimeError("MANDATORY_END_PHRASE_COLLISION_DRIFT")

    slot = feasibility.classify_visible_contracts(_reachable_unsat_contracts())
    if slot.get("status") != "PROVED_UNSAT":
        raise RuntimeError("REACHABLE_COUNTEREXAMPLE_NOT_PROVED_UNSAT")

    ids = tuple(slot.get("instruction_ids") or ())
    if ids != COUNTEREXAMPLE_IDS:
        raise RuntimeError("COUNTEREXAMPLE_IDENTITY_DRIFT")

    expected_reason = "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:help"
    reasons = set(slot.get("hard_unsat_reasons") or ())
    if expected_reason not in reasons:
        raise RuntimeError("COUNTEREXAMPLE_UNSAT_CERTIFICATE_MISSING")

    maximum_counterexample_score = exact_score_from_checker_results((True, False))
    if maximum_counterexample_score != Fraction(1, 4):
        raise RuntimeError("FROZEN_SCORE_ALGEBRA_DRIFT")
    if not maximum_counterexample_score < TARGET_PREDICATE_FLOOR:
        raise RuntimeError("COUNTEREXAMPLE_NO_LONGER_BELOW_TARGET_FLOOR")

    return {
        "schema": SCHEMA,
        "status": "PASS__GENERATOR_SUPPORT_UNIVERSAL_THRESHOLD_ROUTE_FALSIFIED",
        "target_predicate": "LIVEBENCH_IF_GE_65_7",
        "counterexample_instruction_ids": list(ids),
        "collision_word": COLLISION_WORD,
        "mandatory_end_phrase": MANDATORY_END_PHRASE,
        "counterexample_forbidden_words": list(REACHABLE_FORBIDDEN_WORDS),
        "counterexample_forbidden_word_count": len(REACHABLE_FORBIDDEN_WORDS),
        "counterexample_hard_unsat_reason": expected_reason,
        "maximum_counterexample_score": "1/4",
        "target_predicate_floor": "657/1000",
        "public_support_reachability": {
            "all_counterexample_forbidden_words_are_in_pinned_word_list": True,
            "forbidden_default_keyword_count": 5,
            "mandatory_end_phrase_is_in_pinned_ending_options": True,
            "instruction_pair_is_conflict_compatible": True,
            "pinned_livebench_commit": PINNED_LIVEBENCH_COMMIT,
            "pinned_instructions_blob": PINNED_INSTRUCTIONS_BLOB,
            "pinned_instructions_util_blob": PINNED_INSTRUCTIONS_UTIL_BLOB,
            "pinned_registry_blob": PINNED_REGISTRY_BLOB,
            "historical_generator_blob": HISTORICAL_GENERATOR_BLOB,
        },
        "proof_reduction": {
            "superseded_nth_paragraph_witness": True,
            "reason": "END_FORBIDDEN_REQUIRES_FEWER_GENERATOR_SLOT_PREMISES",
            "effect": "SMALLER_GENERATOR_SUPPORT_COUNTEREXAMPLE_WITH_IDENTICAL_SCORE_CEILING",
        },
        "deduction": [
            "THE_PUBLIC_GENERATOR_SUPPORT_CONTAINS_A_REACHABLE_JOINTLY_UNSAT_SLOT_TUPLE",
            "THAT_TWO_CHECKER_TUPLE_HAS_PER_ROW_SCORE_CEILING_1_OVER_4",
            "A_UNIVERSAL_PER_ROW_GENERATOR_SUPPORT_FLOOR_CANNOT_PROVE_LIVEBENCH_IF_GE_65_7",
            "GENERATOR_SUPPORT_SYNTHETIC_SWEEPS_REMAIN_SOLVER_FALSIFIERS_NOT_FIXED_POPULATION_ACCEPTANCE_PROOFS",
        ],
        "corrected_acceptance_routes": [
            "PRECOMMITTED_FIXED_POPULATION_EXECUTION_WITH_FROZEN_CANDIDATE_SCORER_AND_NONLEAKING_AGGREGATE_RECEIPT",
            "CONTENT_INDEPENDENT_FIXED_POPULATION_SCORE_MASS_PROOF_WITH_AN_ADMISSIBLE_SCOPE_BRIDGE",
        ],
        "next_minimum_cut": (
            "STABILIZE_AND_FAIL_CLOSE_THE_VISIBLE_SOLVER_WITH_PUBLIC_SYNTHETIC_CHECKS__"
            "FREEZE_CANDIDATE_SCORER_AND_NONLEAKING_PROTOCOL__"
            "THEN_OBTAIN_ONE_POPULATION_SPECIFIC_SCORE_MASS_RECEIPT_OR_ADMISSIBLE_SCOPE_BRIDGE"
        ),
        "terminal_row_content_read": False,
        "terminal_row_metadata_read": False,
        "terminal_case_frequency_inferred": False,
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
