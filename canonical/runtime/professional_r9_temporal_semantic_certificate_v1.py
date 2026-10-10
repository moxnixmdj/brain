"""Bounded R9 temporal/deployment semantic certificate.

Binds the exact meaning of the already-verified frozen Terminal-Bench-Science
conservative-censoring reducer. This is deliberately narrower than general
deployment validity: it certifies finite frozen-population outcome accounting,
not multihorizon transport, rare-event coverage, distribution shift, or
performative/equilibrium stability.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_R9_TEMPORAL_SEMANTIC_CERTIFICATE_V1"
ROOT_ID = "R9_TEMPORAL_DEPLOYMENT"
SOURCE_SCOPE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R9_CONSERVATIVE_CENSORING_SCOPE_V1"
SOURCE_VERIFY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R9_CONSERVATIVE_CENSORING_VERIFY_V1"
SOURCE_CLAIM_KIND = "FROZEN_POPULATION_CONSERVATIVE_CENSORING_AND_EARLY_FAILURE_ACCOUNTING"
CLAIM_KIND = "FROZEN_POPULATION_CONSERVATIVE_CENSORING_SEMANTICS"

REQUIRED_SCOPE_GUARANTEES = frozenset({
    "FROZEN_DENOMINATOR_NEVER_SHRINKS",
    "ONLY_EXACT_SUCCESS_COUNTS_POSITIVE",
    "FINAL_MISSING_AND_NON_SUCCESS_OUTCOMES_COUNT_ZERO",
    "DUPLICATES_AND_OUT_OF_UNIVERSE_RECORDS_FAIL_CLOSED",
    "PASS_AND_FAIL_LOCKS_ARE_MONOTONE_WITH_RESPECT_TO_REMAINING_POSSIBLE_SUCCESSES",
})

REQUIRED_SCOPE_LIMITS = frozenset({
    "NO_MULTIHORIZON_DEPLOYMENT_VALIDITY",
    "NO_RARE_EVENT_COVERAGE_CLAIM",
    "NO_DISTRIBUTION_SHIFT_TRANSPORT_CLAIM",
    "NO_PERFORMATIVE_OR_EQUILIBRIUM_STABILITY",
    "NO_GLOBAL_R9_SEMANTIC_OR_EXECUTION_LEAF_CLOSURE",
    "NO_GLOBAL_R9_ROOT_CLOSURE",
})

REQUIRED_VERIFY_PROVED = frozenset({
    "FIXED_210_SLOT_DENOMINATOR_CANNOT_SHRINK",
    "ONLY_EXACT_SUCCESS_COUNTS_POSITIVE",
    "MISSING_OR_FINAL_NON_SUCCESS_COUNTS_ZERO_AT_FINALIZATION",
    "RESOURCE_TIMEOUT_INFRA_AND_OTHER_FINAL_FAILURES_CREATE_ZERO_POSITIVE_CREDIT",
    "FAILURE_LOCK_OCCURS_WHEN_MAXIMUM_POSSIBLE_SUCCESS_COUNT_DROPS_BELOW_TARGET",
    "DUPLICATE_OR_OUT_OF_UNIVERSE_RECORDS_FAIL_CLOSED",
    "PASS_BOUNDARY_IS_EXHAUSTIVELY_CORRECT_FOR_ALL_211_FINAL_SUCCESS_COUNTS",
})

REQUIRED_VERIFY_NONCLAIMS = frozenset({
    "MULTIHORIZON_DEPLOYMENT_VALIDITY",
    "RARE_EVENT_COVERAGE",
    "DISTRIBUTION_SHIFT_TRANSPORT",
    "PERFORMATIVE_OR_EQUILIBRIUM_STABILITY",
    "GLOBAL_R9_SEMANTIC_OR_EXECUTION_LEAF_CLOSURE",
})

SEMANTIC_ROLES = {
    "evaluation_population": "ONE_FROZEN_EXACT_210_UNIQUE_SLOT_UNIVERSE",
    "positive_outcome": "ONLY_EXACT_SUCCESS_STATE_CREATES_POSITIVE_CREDIT",
    "final_missing_outcome": "UNOBSERVED_SLOT_COUNTS_AS_ZERO_POSITIVE_CREDIT_ON_FINALIZATION",
    "declared_final_failure": "FINAL_FAILURE_TIMEOUT_INFRA_RESOURCE_INVALID_AND_CANCELLED_CREATE_ZERO_POSITIVE_CREDIT",
    "pass_lock": "SUCCESS_COUNT_AT_OR_ABOVE_THE_DECLARED_REQUIRED_SUCCESS_THRESHOLD",
    "fail_lock": "MAXIMUM_POSSIBLE_SUCCESS_COUNT_BELOW_THE_DECLARED_REQUIRED_SUCCESS_THRESHOLD",
    "open_state": "NEITHER_PASS_NOR_FAIL_IS_YET_MATHEMATICALLY_LOCKED",
    "scope_boundary": "THE_CERTIFICATE_DESCRIBES_ONLY_THIS_FROZEN_FINITE_ACCOUNTING_SYSTEM_NOT_GENERAL_DEPLOYMENT_VALIDITY",
}


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def digest(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _fail(errors: list[str]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "semantic_leaf_credit": False,
        "global_leaf_closure": False,
        "global_root_closure": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def certify(
    scope: Mapping[str, Any],
    verification: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(scope, Mapping):
        return _fail(["SCOPE_NOT_OBJECT"])
    if not isinstance(verification, Mapping):
        return _fail(["VERIFICATION_NOT_OBJECT"])
    if not isinstance(binding, Mapping):
        return _fail(["BINDING_NOT_OBJECT"])

    if scope.get("schema") != SOURCE_SCOPE_SCHEMA:
        errors.append("SCOPE_SCHEMA_INVALID")
    if scope.get("root_id") != ROOT_ID:
        errors.append("SCOPE_ROOT_INVALID")
    if scope.get("claim_kind") != SOURCE_CLAIM_KIND:
        errors.append("SOURCE_CLAIM_KIND_INVALID")
    if not REQUIRED_SCOPE_GUARANTEES <= set(scope.get("guarantees") or []):
        errors.append("SCOPE_REQUIRED_GUARANTEES_MISSING")
    if not REQUIRED_SCOPE_LIMITS <= set(scope.get("limitations") or []):
        errors.append("SCOPE_REQUIRED_LIMITATIONS_MISSING")
    if scope.get("terminal_authority") is not False:
        errors.append("SCOPE_TERMINAL_AUTHORITY_INVALID")

    if verification.get("schema") != SOURCE_VERIFY_SCHEMA:
        errors.append("VERIFICATION_SCHEMA_INVALID")
    if not str(verification.get("status") or "").startswith("PASS__"):
        errors.append("VERIFICATION_NOT_PASS")
    replay = verification.get("replay")
    if (
        not isinstance(replay, Mapping)
        or replay.get("unit_tests_run") != 5
        or replay.get("unit_tests_passed") != 5
        or replay.get("exhaustive_final_success_counts_checked") != 211
    ):
        errors.append("VERIFICATION_REPLAY_INVALID")
    if not REQUIRED_VERIFY_PROVED <= set(verification.get("proved") or []):
        errors.append("VERIFICATION_REQUIRED_PROPERTIES_MISSING")
    if not REQUIRED_VERIFY_NONCLAIMS <= set(verification.get("not_proved") or []):
        errors.append("VERIFICATION_REQUIRED_NONCLAIMS_MISSING")
    if verification.get("terminal_authority") is not False:
        errors.append("VERIFICATION_TERMINAL_AUTHORITY_INVALID")

    if binding.get("root_id") != ROOT_ID:
        errors.append("BINDING_ROOT_INVALID")
    if binding.get("claim_kind") != CLAIM_KIND:
        errors.append("BINDING_CLAIM_KIND_INVALID")
    if binding.get("scope_sha256") != digest(dict(scope)):
        errors.append("SCOPE_DIGEST_MISMATCH")
    if binding.get("verification_sha256") != digest(dict(verification)):
        errors.append("VERIFICATION_DIGEST_MISMATCH")

    roles = binding.get("semantic_roles")
    if not isinstance(roles, Mapping):
        errors.append("SEMANTIC_ROLES_INVALID")
        roles = {}
    for role, expected in SEMANTIC_ROLES.items():
        if roles.get(role) != expected:
            errors.append("SEMANTIC_ROLE_INVALID:" + role)

    boundaries = binding.get("boundaries")
    if not isinstance(boundaries, Mapping):
        errors.append("BOUNDARIES_INVALID")
    else:
        forbidden_true = {
            "multihorizon_deployment_validity": "MULTIHORIZON_OVERCLAIM",
            "rare_event_coverage": "RARE_EVENT_OVERCLAIM",
            "distribution_shift_transport": "DISTRIBUTION_SHIFT_OVERCLAIM",
            "performative_equilibrium_stability": "PERFORMATIVE_STABILITY_OVERCLAIM",
            "global_r9_semantic_leaf_closed": "GLOBAL_R9_SEMANTIC_OVERCLAIM",
            "unobserved_final_slots_may_create_positive_credit": "MISSING_SLOT_POSITIVE_CREDIT_OVERCLAIM",
        }
        for field, error in forbidden_true.items():
            if boundaries.get(field) is not False:
                errors.append(error)
        if boundaries.get("outside_frozen_population_stays_unclaimed") is not True:
            errors.append("OUTSIDE_FROZEN_POPULATION_BOUNDARY_MISSING")

    return {
        "schema": SCHEMA,
        "pass": not errors,
        "status": (
            "PASS__FROZEN_POPULATION_CONSERVATIVE_CENSORING_SEMANTICS_BOUND"
            if not errors
            else "FAIL_CLOSED"
        ),
        "errors": sorted(set(errors)),
        "root_id": ROOT_ID,
        "claim_scope": {
            "kind": CLAIM_KIND,
            "guarantees": [
                "THE_EVALUATION_UNIVERSE_IS_ONE_FROZEN_SET_OF_EXACTLY_210_UNIQUE_SLOTS",
                "ONLY_EXACT_SUCCESS_STATE_CREATES_POSITIVE_CREDIT",
                "FINAL_UNOBSERVED_OR_NON_SUCCESS_OUTCOMES_CREATE_ZERO_POSITIVE_CREDIT",
                "DECLARED_FINAL_FAILURE_TIMEOUT_INFRA_RESOURCE_INVALID_AND_CANCELLED_STATES_CREATE_ZERO_POSITIVE_CREDIT",
                "PASS_LOCK_MEANS_SUCCESS_COUNT_ALREADY_MEETS_THE_DECLARED_THRESHOLD",
                "FAIL_LOCK_MEANS_EVEN_ALL_REMAINING_POSSIBLE_SUCCESSES_CANNOT_MEET_THE_DECLARED_THRESHOLD",
                "DUPLICATE_AND_OUT_OF_UNIVERSE_RECORDS_FAIL_CLOSED",
                "THE_FINITE_ACCOUNTING_BOUNDARY_IS_EXHAUSTIVELY_CHECKED_OVER_ALL_211_FINAL_SUCCESS_COUNTS",
            ],
            "limitations": sorted(REQUIRED_SCOPE_LIMITS),
        },
        "scope_sha256": digest(dict(scope)),
        "verification_sha256": digest(dict(verification)),
        "semantic_leaf_credit": False,
        "global_leaf_closure": False,
        "global_root_closure": False,
        "domain_semantic_closure": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
