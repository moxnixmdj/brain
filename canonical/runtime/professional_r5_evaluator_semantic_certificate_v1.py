"""Bounded professional-quality R5 evaluator-reference semantics.

This certificate binds what the already-verified GDPVal hybrid evaluator
uncertainty machinery *means*. It deliberately does not prove that the real
owner evaluator lies in any proposed uncertainty set.

The load-bearing distinction is:
  authenticated evaluator-class semantics -> premise
  exact rational robust-margin calculation -> owned verifier
  public rubric or reconstructed grader -> never semantic authority

Positive output therefore means only conditional evaluator robustness over an
independently authenticated declared outer class.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_R5_EVALUATOR_SEMANTIC_CERTIFICATE_V1"
ROOT_ID = "R5_EVALUATOR_REFERENCE"
CLAIM_KIND = "CONDITIONAL_EVALUATOR_REFERENCE_ROBUSTNESS_SEMANTICS"
GOV_SCHEMA = "PROJECT_BRAIN_GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_SPRITE_VERIFICATION_V1"

SEMANTIC_ROLES = {
    "EVALUATOR_CLASS_MEMBERSHIP": "EXTERNAL_INDEPENDENT_SEMANTIC_PREMISE",
    "ROBUST_MARGIN_ARITHMETIC": "BRAIN_OWNED_EXACT_RATIONAL_VERIFIER",
    "PUBLIC_RUBRIC": "CANDIDATE_COORDINATES_ONLY__NO_OWNER_SEMANTIC_AUTHORITY",
    "POSITIVE_CERTIFICATE": "CONDITIONAL_NONINFERIORITY_OVER_AUTHENTICATED_OUTER_CLASS_ONLY",
}


def _canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(v: Any) -> str:
    return "sha256:" + sha256(_canon(v).encode("utf-8")).hexdigest()


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "detail": detail,
        "semantic_leaf_credit": False,
        "global_leaf_closure": False,
        "global_root_closure": False,
        "quality_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def certify(
    governance: Mapping[str, Any],
    verification: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    if not all(isinstance(x, Mapping) for x in (governance, verification, binding)):
        return _fail("MAPPING_INPUTS_REQUIRED")
    if governance.get("schema") != GOV_SCHEMA:
        return _fail("GOVERNANCE_SCHEMA_INVALID")
    if governance.get("status") != "CANDIDATE_CONDITIONAL_THEOREM__ARITHMETIC_ONLY__ZERO_GDPVAL_AND_TERMINAL_CREDIT":
        return _fail("GOVERNANCE_STATUS_INVALID")
    if verification.get("schema") != VERIFY_SCHEMA:
        return _fail("VERIFICATION_SCHEMA_INVALID")
    if verification.get("status") != "INDEPENDENT_SPRITE_EXACT_BLOB_REPLAY_PASS__11_OF_11__SEMANTIC_DECOMPOSITION_UNVERIFIED__ZERO_CREDIT":
        return _fail("VERIFICATION_STATUS_INVALID")

    if binding.get("root_id") != ROOT_ID or binding.get("claim_kind") != CLAIM_KIND:
        return _fail("BINDING_SUBJECT_INVALID")
    if binding.get("governance_digest") != digest(governance):
        return _fail("GOVERNANCE_BINDING_DRIFT")
    if binding.get("verification_digest") != digest(verification):
        return _fail("VERIFICATION_BINDING_DRIFT")
    if binding.get("semantic_roles") != SEMANTIC_ROLES:
        return _fail("SEMANTIC_ROLE_BINDING_INVALID")

    mechanics = set(verification.get("verified_mechanics") or [])
    required_mechanics = {
        "POSITIVE_ROBUST_MARGIN_CERTIFICATE_PASSES",
        "UNPROVED_DECOMPOSITION_FAILS_CLOSED",
        "PUBLIC_RUBRIC_ONLY_SEMANTIC_CLASS_IS_FIREWALLED",
        "NONINDEPENDENT_DECOMPOSITION_RECEIPT_FAILS_CLOSED",
        "NONORTHOGONAL_LINEALITY_FAILS_EVEN_WITH_LARGE_NOMINAL_MARGIN",
        "BOUNDED_UNCERTAINTY_CAN_BE_ABSORBED_BY_SUFFICIENT_CERTIFIED_MARGIN",
        "EXCESS_BOUNDED_UNCERTAINTY_FAILS",
        "DIMENSION_MISMATCH_FAILS_CLOSED",
    }
    if not required_mechanics <= mechanics:
        return _fail("VERIFIED_MECHANICS_INCOMPLETE")

    boundary = " ".join(verification.get("verification_boundary") or [])
    if "DOES_NOT_PROVE_THE_TRUE_CURRENT_GDPVAL_OWNER_EVALUATOR" not in boundary:
        return _fail("REAL_OWNER_NONCLAIM_MISSING")
    if "NO_GDPVAL_ACCEPTANCE_FAMILY_CAPABILITY_OWNERSHIP_OR_TERMINAL_CREDIT" not in boundary:
        return _fail("GLOBAL_NONCLAIM_MISSING")

    reality = governance.get("current_reality")
    if not isinstance(reality, Mapping):
        return _fail("CURRENT_REALITY_INVALID")
    required_false = (
        "sound_complete_gdpval_owner_decomposition_bound",
        "current_owner_pairwise_relation_bound",
        "complete_opus55_220_evaluator_facing_laws_bound",
        "gdpval_closed",
    )
    if any(reality.get(k) is not False for k in required_false):
        return _fail("BOUNDARY_STATE_NOT_EXACTLY_PRESERVED")

    firewall = governance.get("soundness_firewall")
    if not isinstance(firewall, Mapping):
        return _fail("SOUNDNESS_FIREWALL_INVALID")
    allowed = set(firewall.get("admissible_decomposition_proof_classes") or [])
    if not {
        "AUTHENTIC_CURRENT_OWNER_SEMANTICS",
        "EXTENSIONALLY_EQUIVALENT_CURRENT_PREFERENCE_RELATION",
        "INDEPENDENTLY_VERIFIED_RESTRICTED_OWNER_CLASS",
        "EVALUATOR_INDEPENDENT_SCOPE_COMPLETE_BOUND",
    } <= allowed:
        return _fail("ADMISSIBLE_SEMANTIC_PROOF_CLASSES_INCOMPLETE")
    forbidden = set(firewall.get("forbidden_as_semantic_containment_proof") or [])
    if not {"PUBLIC_RUBRIC_ONLY", "UNVERIFIED_RECONSTRUCTED_GRADER"} <= forbidden:
        return _fail("FORBIDDEN_SEMANTIC_PROOF_CLASSES_INCOMPLETE")

    claim_scope = {
        "kind": CLAIM_KIND,
        "guarantees": [
            "ROBUST_MARGIN_MEANING_IS_CONDITIONAL_ON_AN_INDEPENDENTLY_AUTHENTICATED_EVALUATOR_OUTER_CLASS",
            "ROBUST_MARGIN_IS_CHECKED_BY_EXACT_RATIONAL_ARITHMETIC",
            "UNPROVED_OR_NONINDEPENDENT_EVALUATOR_CLASS_MEMBERSHIP_FAILS_CLOSED",
            "PUBLIC_RUBRIC_ONLY_CANNOT_BIND_OWNER_PREFERENCE_SEMANTICS",
            "ARBITRARY_LINEALITY_REQUIRES_EXACT_ORTHOGONALITY",
            "BOUNDED_UNCERTAINTY_MUST_FIT_INSIDE_THE_CERTIFIED_MARGIN",
        ],
        "limitations": [
            "NO_PROOF_THE_TRUE_CURRENT_OWNER_EVALUATOR_IS_IN_ANY_PROPOSED_DECOMPOSITION",
            "NO_PROOF_PUBLIC_RUBRIC_DIRECTIONS_ARE_OWNER_MONOTONE",
            "NO_CURRENT_BRAIN_VS_OPUS55_DIFFERENCE_VECTOR_BINDING",
            "NO_GLOBAL_R5_SEMANTIC_LEAF_OR_ROOT_CLOSURE",
            "NO_GDPVAL_OR_AA_BRIEFCASE_QUALITY_ACCEPTANCE_CREDIT",
        ],
    }
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__BOUNDED_CONDITIONAL_EVALUATOR_REFERENCE_SEMANTICS",
        "root_id": ROOT_ID,
        "claim_kind": CLAIM_KIND,
        "claim_scope": claim_scope,
        "semantic_roles": dict(SEMANTIC_ROLES),
        "semantic_leaf_credit": False,
        "global_leaf_closure": False,
        "global_root_closure": False,
        "quality_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
