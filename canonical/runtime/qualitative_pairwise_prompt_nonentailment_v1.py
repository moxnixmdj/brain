"""Pairwise prompt non-entailment kernel.

This kernel checks the constructive two-world countermodel used by
QUALITATIVE_PAIRWISE_PROMPT_NONENTAILMENT_CUT_V1. It proves only the logical
information boundary: fixed prompt/input/judge metadata does not determine a
unique preference when judge response semantics remain unbound.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_QUALITATIVE_PAIRWISE_PROMPT_NONENTAILMENT_KERNEL_V1"
PREFERENCES = {"A", "B"}

class PairwiseNonentailmentError(ValueError):
    pass

def evaluate(spec: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, Mapping):
        raise PairwiseNonentailmentError("SPEC_MAPPING_REQUIRED")
    shared = spec.get("shared_contract")
    worlds = spec.get("worlds")
    if not isinstance(shared, Mapping):
        raise PairwiseNonentailmentError("SHARED_CONTRACT_REQUIRED")
    if not isinstance(worlds, list) or len(worlds) != 2:
        raise PairwiseNonentailmentError("EXACTLY_TWO_WORLDS_REQUIRED")
    required = ("prompt_blob_sha", "input_digest", "judge_identities", "aggregation_digest", "output_schema")
    for key in required:
        if key not in shared:
            raise PairwiseNonentailmentError("SHARED_CONTRACT_FIELD_MISSING:" + key)
    if not isinstance(shared["judge_identities"], list) or not shared["judge_identities"]:
        raise PairwiseNonentailmentError("JUDGE_IDENTITIES_REQUIRED")

    prefs = []
    for i, world in enumerate(worlds):
        if not isinstance(world, Mapping):
            raise PairwiseNonentailmentError(f"WORLD_NOT_MAPPING:{i}")
        if world.get("same_public_contract") is not True:
            raise PairwiseNonentailmentError(f"WORLD_PUBLIC_CONTRACT_MISMATCH:{i}")
        if world.get("judge_semantics_bound") is not False:
            raise PairwiseNonentailmentError(f"WORLD_MUST_LEAVE_JUDGE_SEMANTICS_UNBOUND:{i}")
        pref = world.get("preference")
        if pref not in PREFERENCES:
            raise PairwiseNonentailmentError(f"INVALID_PREFERENCE:{i}")
        prefs.append(pref)

    if prefs[0] == prefs[1]:
        raise PairwiseNonentailmentError("COUNTERMODEL_DOES_NOT_FLIP_PREFERENCE")

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__PROMPT_AND_PUBLIC_METADATA_DO_NOT_ENTAIL_UNIQUE_PREFERENCE_WITH_UNBOUND_JUDGE_SEMANTICS",
        "same_public_contract": True,
        "opposite_pairwise_preferences_exist": True,
        "unique_preference_entailed": False,
        "exact_prompt_bytes_alone_sufficient": False,
        "minimum_sound_closure_disjunction": [
            "AUTHENTIC_TARGET_OUTCOME_OR_EQUIVALENT_RELATION_BIT",
            "BOUND_JUDGE_SEMANTICS_SUFFICIENT_TO_DERIVE_OUTCOME",
            "EVALUATOR_ROBUST_SCOPE_COMPLETE_DOMINANCE"
        ],
        "terminal_credit_delta": 0,
    }
