"""Bounded R5 evaluator/reference semantic certificate.

Reuses the existing GDPval evaluator-uncertainty theorem and the constructive
public-information nonidentifiability cut to define what evaluator/reference
evidence means. It deliberately does not infer the hidden current owner
evaluator from public methodology, rubrics, historical prompts, or reconstructed
graders.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_R5_EVALUATOR_SEMANTIC_CERTIFICATE_V1"
ROOT_ID = "R5_EVALUATOR_REFERENCE"
CLAIM_KIND = "BOUNDED_EVALUATOR_REFERENCE_UNCERTAINTY_SEMANTICS"

UNCERTAINTY_SCHEMA = "PROJECT_BRAIN_GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_V1"
MECHANICS_SCHEMA = "PROJECT_BRAIN_GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_SPRITE_VERIFICATION_V1"
INFO_CUT_SCHEMA = "PROJECT_BRAIN_GDPVAL_EVALUATION_LAW_MINIMUM_INFORMATION_CUT_20261008_V1"

REQUIRED_ALLOWED_PROOF_CLASSES = frozenset({
    "AUTHENTIC_CURRENT_OWNER_SEMANTICS",
    "EXTENSIONALLY_EQUIVALENT_CURRENT_PREFERENCE_RELATION",
    "INDEPENDENTLY_VERIFIED_RESTRICTED_OWNER_CLASS",
    "EVALUATOR_INDEPENDENT_SCOPE_COMPLETE_BOUND",
})
REQUIRED_FORBIDDEN_PROOF_CLASSES = frozenset({
    "PUBLIC_METHODOLOGY_ONLY",
    "PUBLIC_RUBRIC_ONLY",
    "HISTORICAL_V1_PROMPT_CARRYFORWARD",
    "UNVERIFIED_RECONSTRUCTED_GRADER",
})
REQUIRED_MECHANICS = frozenset({
    "POSITIVE_ROBUST_MARGIN_CERTIFICATE_PASSES",
    "UNPROVED_DECOMPOSITION_FAILS_CLOSED",
    "PUBLIC_RUBRIC_ONLY_SEMANTIC_CLASS_IS_FIREWALLED",
    "NONINDEPENDENT_DECOMPOSITION_RECEIPT_FAILS_CLOSED",
})
REQUIRED_MECHANICS_BOUNDARY = frozenset({
    "THIS_REPLAY_PROVES_RUNTIME_AND_TEST_MECHANICS_ONLY.",
    "IT_DOES_NOT_PROVE_THE_TRUE_CURRENT_GDPVAL_OWNER_EVALUATOR_IS_CONTAINED_IN_ANY_PROPOSED_u0_PLUS_CONE_K_PLUS_CONV_B_PLUS_SPAN_L_DECOMPOSITION.",
})
REQUIRED_SEPARATOR_CLASSES = frozenset({
    "EXACT_CURRENT_OWNER_SEMANTICS",
    "EXTENSIONALLY_EQUIVALENT_CURRENT_PREFERENCE_RELATION",
    "AUTHENTIC_CURRENT_OWNER_PAIRWISE_OUTCOME",
    "INDEPENDENTLY_VERIFIED_RESTRICTED_OWNER_CLASS",
    "EVALUATOR_INDEPENDENT_SCOPE_COMPLETE_DOMINANCE",
    "TARGET_TRAJECTORY_LAW_EQUALITY",
})

SEMANTIC_ROLES = {
    "reference_identity": "CURRENT_OWNER_EVALUATOR_REFERENCE_IS_NOT_INFERRED_FROM_PUBLIC_METHODOLOGY_RUBRIC_HISTORY_OR_RECONSTRUCTED_GRADER",
    "uncertainty_model": "ROBUST_MARGIN_CERTIFICATE_IS_CONDITIONAL_ON_AN_INDEPENDENTLY_VERIFIED_SOUND_COMPLETE_OUTER_EVALUATOR_CLASS",
    "public_information_boundary": "PUBLICLY_BOUND_OBSERVATIONS_MAY_BE_COMPATIBLE_WITH_OWNER_RELATIONS_THAT_REVERSE_THE_TARGET_PAIRWISE_OUTCOME",
    "minimum_separator": "ONE_AUTHENTIC_FACT_OR_STRONGER_CERTIFICATE_MUST_EXCLUDE_AT_LEAST_ONE_REMAINING_DECISION_RELEVANT_OWNER_RELATION_WORLD",
    "stronger_route": "EVALUATOR_INDEPENDENT_SCOPE_COMPLETE_DOMINANCE_MAY_BYPASS_EXACT_OWNER_EVALUATOR_IDENTIFICATION",
    "acceptance_meaning": "R5_REFERENCE_SEMANTICS_DISTINGUISH_CONDITIONAL_ROBUSTNESS_FROM_AUTHENTIC_OWNER_RELATION_AUTHORITY",
}


def _canon(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
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
        "domain_semantic_closure": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def certify(
    uncertainty_governance: Mapping[str, Any],
    mechanics_verification: Mapping[str, Any],
    information_cut: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    for label, value in (
        ("UNCERTAINTY", uncertainty_governance),
        ("MECHANICS", mechanics_verification),
        ("INFO_CUT", information_cut),
        ("BINDING", binding),
    ):
        if not isinstance(value, Mapping):
            return _fail([label + "_NOT_OBJECT"])

    if uncertainty_governance.get("schema") != UNCERTAINTY_SCHEMA:
        errors.append("UNCERTAINTY_SCHEMA_INVALID")
    if not str(uncertainty_governance.get("status") or "").startswith(
        "CANDIDATE_CONDITIONAL_THEOREM"
    ):
        errors.append("UNCERTAINTY_STATUS_INVALID")
    reality = uncertainty_governance.get("current_reality")
    if not isinstance(reality, Mapping):
        errors.append("CURRENT_REALITY_INVALID")
    else:
        for field in (
            "sound_complete_gdpval_owner_decomposition_bound",
            "current_owner_pairwise_relation_bound",
            "gdpval_closed",
        ):
            if reality.get(field) is not False:
                errors.append("CURRENT_REALITY_OVERCLAIM:" + field)
    firewall = uncertainty_governance.get("soundness_firewall")
    if not isinstance(firewall, Mapping):
        errors.append("SOUNDNESS_FIREWALL_INVALID")
    else:
        if not REQUIRED_ALLOWED_PROOF_CLASSES <= set(
            firewall.get("admissible_decomposition_proof_classes") or []
        ):
            errors.append("ALLOWED_PROOF_CLASSES_MISSING")
        if not REQUIRED_FORBIDDEN_PROOF_CLASSES <= set(
            firewall.get("forbidden_as_semantic_containment_proof") or []
        ):
            errors.append("FORBIDDEN_PROOF_CLASSES_MISSING")

    if mechanics_verification.get("schema") != MECHANICS_SCHEMA:
        errors.append("MECHANICS_SCHEMA_INVALID")
    if not str(mechanics_verification.get("status") or "").startswith(
        "INDEPENDENT_SPRITE_EXACT_BLOB_REPLAY_PASS__11_OF_11"
    ):
        errors.append("MECHANICS_NOT_VERIFIED")
    if not REQUIRED_MECHANICS <= set(mechanics_verification.get("verified_mechanics") or []):
        errors.append("MECHANICS_REQUIRED_PROPERTIES_MISSING")
    if not REQUIRED_MECHANICS_BOUNDARY <= set(
        mechanics_verification.get("verification_boundary") or []
    ):
        errors.append("MECHANICS_BOUNDARY_MISSING")

    if information_cut.get("schema") != INFO_CUT_SCHEMA:
        errors.append("INFO_CUT_SCHEMA_INVALID")
    if not str(information_cut.get("status") or "").startswith(
        "CONSTRUCTIVE_TWO_WORLD_NONIDENTIFIABILITY_PROOF"
    ):
        errors.append("INFO_CUT_STATUS_INVALID")
    counter = information_cut.get("constructive_countermodel")
    if not isinstance(counter, Mapping):
        errors.append("COUNTERMODEL_INVALID")
    else:
        if "IDENTICAL" not in str(counter.get("observable_equivalence") or ""):
            errors.append("COUNTERMODEL_OBSERVABLE_EQUIVALENCE_MISSING")
        target_difference = str(counter.get("target_difference") or "")
        if "TRUE" not in target_difference or "FALSE" not in target_difference:
            errors.append("COUNTERMODEL_TARGET_DIFFERENCE_MISSING")
    separator = information_cut.get("minimum_separator_cut")
    if not isinstance(separator, Mapping):
        errors.append("MINIMUM_SEPARATOR_INVALID")
    else:
        if "EXCLUDES_AT_LEAST_ONE" not in str(separator.get("required_form") or ""):
            errors.append("MINIMUM_SEPARATOR_FORM_INVALID")
        if not REQUIRED_SEPARATOR_CLASSES <= set(separator.get("admissible_classes") or []):
            errors.append("MINIMUM_SEPARATOR_CLASSES_MISSING")
    if (
        "NO_CLAIM_A_STRONGER_BRAIN_SIDE_TOP_OR_DOMINANCE_THEOREM_CANNOT_BYPASS_TARGET_INFORMATION."
        not in set(information_cut.get("hard_nonclaims") or [])
    ):
        errors.append("STRONGER_ROUTE_NONCLAIM_MISSING")

    if binding.get("root_id") != ROOT_ID:
        errors.append("BINDING_ROOT_INVALID")
    if binding.get("claim_kind") != CLAIM_KIND:
        errors.append("BINDING_CLAIM_KIND_INVALID")
    if binding.get("uncertainty_sha256") != digest(dict(uncertainty_governance)):
        errors.append("UNCERTAINTY_DIGEST_MISMATCH")
    if binding.get("mechanics_sha256") != digest(dict(mechanics_verification)):
        errors.append("MECHANICS_DIGEST_MISMATCH")
    if binding.get("information_cut_sha256") != digest(dict(information_cut)):
        errors.append("INFO_CUT_DIGEST_MISMATCH")

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
        forbidden = {
            "true_owner_evaluator_identified": "OWNER_EVALUATOR_IDENTITY_OVERCLAIM",
            "public_rubric_owner_monotonicity_proved": "PUBLIC_RUBRIC_OVERCLAIM",
            "global_r5_semantic_leaf_closed": "GLOBAL_R5_SEMANTIC_OVERCLAIM",
            "gdpval_acceptance_closed": "GDPVAL_ACCEPTANCE_OVERCLAIM",
            "terminal_acceptance": "TERMINAL_ACCEPTANCE_OVERCLAIM",
        }
        for field, error in forbidden.items():
            if boundaries.get(field) is not False:
                errors.append(error)
        if boundaries.get("unresolved_owner_reference_stays_open") is not True:
            errors.append("UNRESOLVED_OWNER_REFERENCE_BOUNDARY_MISSING")
        if boundaries.get("stronger_brain_side_certificate_may_bypass") is not True:
            errors.append("STRONGER_ROUTE_BOUNDARY_MISSING")

    claim_scope = {
        "kind": CLAIM_KIND,
        "reference_scope": "GDPVAL_AA_V2_1_CURRENT_OWNER_PAIRWISE_RELATION_AND_CONDITIONAL_OUTER_EVALUATOR_CLASS",
        "guarantees": [
            "PUBLIC_METHODOLOGY_RUBRICS_HISTORICAL_PROMPTS_AND_UNVERIFIED_GRADERS_HAVE_ZERO_CURRENT_OWNER_REFERENCE_AUTHORITY",
            "THE_EXISTING_ROBUST_MARGIN_RUNTIME_HAS_SEMANTIC_FORCE_ONLY_AFTER_AN_INDEPENDENT_SOUND_COMPLETE_OUTER_EVALUATOR_CLASS_IS_BOUND",
            "CURRENTLY_BOUND_PUBLIC_OBSERVATIONS_DO_NOT_BY_THEMSELVES_ENTAIL_AN_ARBITRARY_CURRENT_OWNER_PAIRWISE_OUTCOME",
            "WHEN_DECISION_RELEVANT_OWNER_RELATION_WORLDS_REMAIN__ONE_AUTHENTIC_SEPARATOR_OR_STRONGER_CERTIFICATE_IS_REQUIRED",
            "AN_EVALUATOR_INDEPENDENT_SCOPE_COMPLETE_DOMINANCE_CERTIFICATE_MAY_BYPASS_EXACT_OWNER_EVALUATOR_IDENTIFICATION",
        ],
        "limitations": [
            "NO_TRUE_CURRENT_OWNER_EVALUATOR_IDENTIFICATION",
            "NO_PUBLIC_RUBRIC_OWNER_MONOTONICITY",
            "NO_COMPLETE_CURRENT_OWNER_PREFERENCE_RELATION",
            "NO_GLOBAL_R5_SEMANTIC_LEAF_CLOSURE",
            "NO_GLOBAL_R5_ROOT_CLOSURE",
            "NO_GDPVAL_ACCEPTANCE_OR_CAPABILITY_CREDIT",
            "NO_DOMAIN_SEMANTIC_CLOSURE",
            "NO_DOMAIN_EXECUTION_CLOSURE",
            "NO_TERMINAL_ACCEPTANCE_OR_CREDIT",
        ],
    }
    return {
        "schema": SCHEMA,
        "pass": not errors,
        "status": (
            "PASS__BOUNDED_EVALUATOR_REFERENCE_UNCERTAINTY_SEMANTICS"
            if not errors else "FAIL_CLOSED"
        ),
        "errors": sorted(set(errors)),
        "root_id": ROOT_ID,
        "claim_scope": claim_scope,
        "uncertainty_sha256": digest(dict(uncertainty_governance)),
        "mechanics_sha256": digest(dict(mechanics_verification)),
        "information_cut_sha256": digest(dict(information_cut)),
        "semantic_leaf_credit": False,
        "global_leaf_closure": False,
        "global_root_closure": False,
        "domain_semantic_closure": False,
        "domain_execution_closure": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
