#!/usr/bin/env python3
"""Falsify the generator-support universal-threshold proof route for LiveBench IF.

The proof uses a concrete slot tuple that is actually in the public historical
generator support, not merely an abstract checker-domain example:

- "rock" is present in the pinned LiveBench WORD_LIST;
- both ParagraphFirstWordCheck and ForbiddenWords draw their lexical slots from
  generate_keywords(), which samples that WORD_LIST;
- the two instruction IDs are conflict-compatible in the pinned registry;
- setting nth-paragraph first_word="rock" and forbidden_words containing
  "rock" is therefore a reachable generator-support tuple;
- the pinned checker semantics make that tuple jointly UNSAT.

For a two-checker row that cannot make both booleans true, the frozen public
LiveBench IF scorer is at most 1/4. Therefore a universal per-row lower-bound
proof over the entire generator support cannot establish the 65.7% target.

The 928-to-7 structural reduction remains useful for solver hardening and
falsification. It is not, by itself, a fixed-population acceptance proof.

No terminal row, hidden kwarg, terminal response, row frequency, or terminal
score is read by this module.
"""
from __future__ import annotations

from fractions import Fraction

from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feasibility
from canonical.runtime.livebench_if_score_bound_v1 import exact_score_from_checker_results

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_GENERATOR_SUPPORT_THRESHOLD_ROUTE_FALSIFIER_V2"

TARGET_PREDICATE_FLOOR = Fraction(657, 1000)  # 65.7%
REACHABLE_COLLISION_WORD = "rock"
COUNTEREXAMPLE_IDS = (
    "keywords:forbidden_words",
    "length_constraints:nth_paragraph_first_word",
)

# Exact public-source commitments independently checked before this candidate.
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_INSTRUCTIONS_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
HISTORICAL_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"


def _reachable_unsat_contracts() -> list[dict]:
    return [
        {
            "instruction_id": "length_constraints:nth_paragraph_first_word",
            "slots": {
                "num_paragraphs": 2,
                "nth_paragraph": 1,
                "first_word": REACHABLE_COLLISION_WORD,
            },
        },
        {
            "instruction_id": "keywords:forbidden_words",
            "slots": {"forbidden_words": [REACHABLE_COLLISION_WORD]},
        },
    ]


def verify() -> dict:
    slot = feasibility.classify_visible_contracts(_reachable_unsat_contracts())
    if slot.get("status") != "PROVED_UNSAT":
        raise RuntimeError("REACHABLE_COUNTEREXAMPLE_NOT_PROVED_UNSAT")

    ids = tuple(slot.get("instruction_ids") or ())
    if ids != COUNTEREXAMPLE_IDS:
        raise RuntimeError("COUNTEREXAMPLE_IDENTITY_DRIFT")

    reasons = set(slot.get("hard_unsat_reasons") or ())
    if "NTH_FIRST_WORD_IS_FORBIDDEN_WORD" not in reasons:
        raise RuntimeError("COUNTEREXAMPLE_UNSAT_CERTIFICATE_MISSING")

    # Joint UNSAT means at most one of the two checker booleans can be true.
    # The frozen public scorer is monotone in the checker-true count for a
    # non-all-true row, so [True, False] is the maximal possible score state.
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
        "counterexample_word": REACHABLE_COLLISION_WORD,
        "counterexample_archetype": slot.get("archetype"),
        "counterexample_hard_unsat_reason": "NTH_FIRST_WORD_IS_FORBIDDEN_WORD",
        "maximum_counterexample_score": "1/4",
        "target_predicate_floor": "657/1000",
        "public_support_reachability": {
            "word_is_in_pinned_word_list": True,
            "word": REACHABLE_COLLISION_WORD,
            "lexical_slots_share_generate_keywords_word_list": True,
            "instruction_pair_is_conflict_compatible": True,
            "pinned_livebench_commit": PINNED_LIVEBENCH_COMMIT,
            "pinned_instructions_blob": PINNED_INSTRUCTIONS_BLOB,
            "pinned_instructions_util_blob": PINNED_INSTRUCTIONS_UTIL_BLOB,
            "pinned_registry_blob": PINNED_REGISTRY_BLOB,
            "historical_generator_blob": HISTORICAL_GENERATOR_BLOB,
        },
        "truth_repair": {
            "prior_illustrative_word": "alpha",
            "prior_illustrative_word_is_in_pinned_word_list": False,
            "replacement_generator_reachable_word": REACHABLE_COLLISION_WORD,
            "effect": "PRESERVE_SLOT_UNSAT_THEOREM_AND_REPAIR_GENERATOR_SUPPORT_REACHABILITY",
        },
        "deduction": [
            "RAW_ID_COMPATIBILITY_IS_NOT_CONCRETE_SLOT_SATISFIABILITY",
            "THE_PUBLIC_GENERATOR_SUPPORT_CONTAINS_A_REACHABLE_JOINTLY_UNSAT_SLOT_TUPLE",
            "THAT_TWO_CHECKER_TUPLE_HAS_PER_ROW_SCORE_CEILING_1_OVER_4",
            "A_UNIVERSAL_PER_ROW_GENERATOR_SUPPORT_FLOOR_CANNOT_PROVE_LIVEBENCH_IF_GE_65_7",
            "THE_928_TO_7_REDUCTION_REMAINS_USEFUL_FOR_SOLVER_HARDENING_NOT_POPULATION_ACCEPTANCE_BY_ITSELF",
        ],
        "corrected_acceptance_routes": [
            "PRECOMMITTED_FIXED_POPULATION_EXECUTION_WITH_FROZEN_CANDIDATE_SCORER_AND_NONLEAKING_AGGREGATE_RECEIPT",
            "CONTENT_INDEPENDENT_FIXED_POPULATION_SCORE_MASS_PROOF_WITH_AN_ADMISSIBLE_SCOPE_BRIDGE",
        ],
        "next_minimum_cut": (
            "FINISH_EXACT_SYNTHETIC_SOLVER_FALSIFICATION_ONLY_TO_STABILIZE_THE_FROZEN_CANDIDATE__"
            "THEN_PRECOMMIT_AND_EXECUTE_ONE_CLEAN_FIXED_POPULATION_SCORE_RUN__"
            "DO_NOT_REQUIRE_UNIVERSAL_GENERATOR_SUPPORT_SATISFIABILITY"
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
