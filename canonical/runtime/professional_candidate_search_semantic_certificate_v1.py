"""Bounded R2 candidate-search semantic certificate.

This certificate gives precise meaning to the already-verified finite
scope-complete candidate-search/refinement capability. It does not create a new
search algorithm and it never upgrades a declared finite scope into open-world
search completeness.

Authority is content-bound to the exact R2 scope-governance document and its
independent execution verification receipt.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_R2_SEARCH_SEMANTIC_CERTIFICATE_V1"
ROOT_ID = "R2_CANDIDATE_SEARCH"
SOURCE_SCOPE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R2_SCOPE_COMPLETE_SEARCH_SCOPE_V1"
SOURCE_VERIFY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R2_SCOPE_COMPLETE_SEARCH_VERIFY_V1"
CLAIM_KIND = "FINITE_SCOPE_COMPLETE_CANDIDATE_SEARCH_SEMANTICS"

REQUIRED_SCOPE_GUARANTEES = frozenset({
    "FOR_A_DECLARED_SCOPE_COMPLETE_FINITE_REGION_ONE_COMMON_INDEPENDENTLY_ADEQUATE_POLICY_CLOSES_WITHOUT_EXTRA_OBSERVATION",
    "WHEN_NO_COMMON_POLICY_EXISTS_EXACT_MINIMAX_SELECTS_THE_LOWEST_WORST_CASE_COST_DECLARED_TRUTHFUL_OBSERVATION_POLICY",
    "OVERLAPPING_POLICY_REGIONS_PERMIT_DECISION_RESOLUTION_BEFORE_WORLD_IDENTIFICATION",
    "SCOPE_INCOMPLETENESS_POLICY_ADEQUACY_GAPS_AND_INSUFFICIENT_OBSERVATION_SEPARATION_FAIL_CLOSED",
    "U_SUBTRACTION_IS_NOT_AUTHORIZED_BY_A_DISCRIMINATOR_PLAN_ALONE",
})

REQUIRED_SCOPE_LIMITS = frozenset({
    "NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS",
    "NO_ESCAPE_PROGRESS_TOTALITY",
    "NO_OPEN_WORLD_HYPOTHESIS_COMPLETENESS",
    "NO_POLICY_GENERATION_COMPLETENESS",
    "NO_GLOBAL_R2_SEMANTIC_OR_EXECUTION_LEAF_CLOSURE",
    "NO_GLOBAL_R2_ROOT_CLOSURE",
})

REQUIRED_VERIFY_PROVED = frozenset({
    "SCOPE_INCOMPLETE_REGIONS_NEVER_AUTHORIZE_U_SUBTRACTION",
    "INDEPENDENT_POLICY_ADEQUACY_IS_REQUIRED",
    "WHOLE_REGION_COMMON_POLICY_STOPS_WITHOUT_UNNECESSARY_OBSERVATION",
    "WHEN_NO_COMMON_POLICY_EXISTS_THE_EXACT_MINIMAX_SOLVER_SELECTS_THE_CHEAPEST_DECLARED_RESOLVING_OBSERVATION",
    "OVERLAPPING_POLICY_REGIONS_ALLOW_STOPPING_BEFORE_WORLD_IDENTIFICATION",
    "INCOMPLETE_POLICY_REGION_OR_OBSERVATION_OUTCOME_MAP_FAILS_CLOSED",
    "INDISTINGUISHABLE_INCOMPATIBLE_WORLDS_FAIL_CLOSED",
    "NO_COMMON_POLICY_RETURNS_A_TRUTHFUL_DISCRIMINATOR_PLAN_NOT_FAKE_CLOSURE",
})

REQUIRED_VERIFY_NONCLAIMS = frozenset({
    "GLOBAL_CANDIDATE_SEARCH_COMPLETENESS",
    "ESCAPE_PROGRESS_TOTALITY",
    "OPEN_WORLD_HYPOTHESIS_SET_COMPLETENESS",
    "POLICY_GENERATION_COMPLETENESS",
    "GLOBAL_R2_SEMANTIC_OR_EXECUTION_LEAF_CLOSURE",
})

SEMANTIC_ROLES = {
    "candidate_scope": "DECLARED_SCOPE_COMPLETE_FINITE_POLICY_RELEVANT_REGION",
    "policy_adequacy": "INDEPENDENT_OR_OBJECTIVE_POLICY_ADEQUACY_OVER_DECLARED_REGION_MEMBERS",
    "stop_rule": "STOP_WHEN_ONE_ADEQUATE_POLICY_COVERS_EVERY_SURVIVING_DECLARED_REGION_MEMBER",
    "discriminator_trigger": "QUERY_ONLY_WHEN_NO_COMMON_ADEQUATE_POLICY_EXISTS",
    "discriminator_semantics": "DECLARED_TRUTHFUL_OBSERVATION_WITH_COMPLETE_OUTCOME_MAP_INSIDE_BOUND_SCOPE",
    "optimization_rule": "MINIMIZE_DECLARED_WORST_CASE_OBSERVATION_COST_TO_REACH_A_COMMON_POLICY_REGION",
    "overlap_rule": "POLICY_REGIONS_MAY_OVERLAP_AND_DECISION_RESOLUTION_NEED_NOT_IDENTIFY_ONE_WORLD",
    "failure_rule": "SCOPE_INCOMPLETENESS_ADEQUACY_GAPS_OR_UNRESOLVABLE_INCOMPATIBILITY_REMAIN_OPEN_OR_FAIL_CLOSED",
    "credit_boundary": "A_DISCRIMINATOR_PLAN_ALONE_NEVER_AUTHORIZES_U_SUBTRACTION_OR_GLOBAL_SEARCH_CLOSURE",
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
    if scope.get("claim_kind") != "FINITE_SCOPE_COMPLETE_COMMON_POLICY_OR_MINIMUM_TRUTHFUL_DISCRIMINATOR_SEARCH":
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
        or replay.get("tests_run") != 9
        or replay.get("tests_passed") != 9
        or replay.get("tests_failed") != 0
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
        if boundaries.get("global_candidate_search_complete") is not False:
            errors.append("GLOBAL_SEARCH_COMPLETENESS_OVERCLAIM")
        if boundaries.get("escape_progress_totality") is not False:
            errors.append("ESCAPE_TOTALITY_OVERCLAIM")
        if boundaries.get("open_world_hypothesis_complete") is not False:
            errors.append("OPEN_WORLD_HYPOTHESIS_OVERCLAIM")
        if boundaries.get("policy_generation_complete") is not False:
            errors.append("POLICY_GENERATION_OVERCLAIM")
        if boundaries.get("discriminator_plan_authorizes_u_subtraction") is not False:
            errors.append("DISCRIMINATOR_U_SUBTRACTION_OVERCLAIM")
        if boundaries.get("unresolved_outside_bound_scope_stays_open") is not True:
            errors.append("OUTSIDE_SCOPE_FAIL_CLOSED_RULE_MISSING")

    return {
        "schema": SCHEMA,
        "pass": not errors,
        "status": (
            "PASS__FINITE_SCOPE_COMPLETE_CANDIDATE_SEARCH_SEMANTICS_BOUND"
            if not errors
            else "FAIL_CLOSED"
        ),
        "errors": sorted(set(errors)),
        "root_id": ROOT_ID,
        "claim_scope": {
            "kind": CLAIM_KIND,
            "guarantees": [
                "CANDIDATE_SCOPE_MEANS_THE_DECLARED_FINITE_POLICY_RELEVANT_REGION_AND_NOT_AN_OPEN_WORLD_UNIVERSE",
                "POLICY_ADEQUACY_IS_AN_INDEPENDENT_PREMISE_NOT_INFERRED_FROM_SEARCH_STRUCTURE",
                "A_COMMON_ADEQUATE_POLICY_STOPS_SEARCH_WITHOUT_WORLD_IDENTIFICATION",
                "A_DISCRIMINATOR_IS_NEEDED_ONLY_WHEN_NO_COMMON_ADEQUATE_POLICY_EXISTS",
                "MINIMAX_OPTIMALITY_IS_ONLY_OVER_DECLARED_COMPLETE_TRUTHFUL_OBSERVATIONS_IN_THE_BOUND_SCOPE",
                "OVERLAPPING_POLICY_REGIONS_PRESERVE_DECISION_LEVEL_NOT_WORLD_IDENTITY_SEMANTICS",
                "SCOPE_OR_EVIDENCE_INCOMPLETENESS_REMAINS_OPEN_OR_FAILS_CLOSED",
                "DISCRIMINATOR_PLANS_DO_NOT_BY_THEMSELVES_AUTHORIZE_U_SUBTRACTION",
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


def _fail(errors: list[str]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "errors": errors,
        "semantic_leaf_credit": False,
        "global_leaf_closure": False,
        "global_root_closure": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
