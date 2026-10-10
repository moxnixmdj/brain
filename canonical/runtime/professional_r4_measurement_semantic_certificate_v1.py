"""Bounded R4 mechanical-measurement semantic certificate.

Binds the operational meaning of the existing content-addressed artifact
measurement + typed acceptance bridge. It certifies what the supported
mechanical fields mean and where their values come from; it does not claim that
those fields are automatically valid proxies for a professional-quality
construct or holistic visual quality.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_R4_MEASUREMENT_SEMANTIC_CERTIFICATE_V1"
ROOT_ID = "R4_MEASUREMENT_CONSTRUCT"
SOURCE_GOVERNANCE_SCHEMA = "PROJECT_BRAIN_ARTIFACT_MEASUREMENT_BINDING_V1"
SOURCE_VERIFY_SCHEMA = "PROJECT_BRAIN_ARTIFACT_MEASUREMENT_VERIFY_V1"
CLAIM_KIND = "CONTENT_ADDRESSED_TYPED_MECHANICAL_MEASUREMENT_SEMANTICS"

SUPPORTED_KINDS = frozenset({
    "FILE_BASENAME",
    "FILE_SUFFIX",
    "FILE_SIZE_BYTES",
    "OOXML_MEMBER_EXISTS",
    "XLSX_SHEET_EXISTS",
    "XLSX_SHEET_COUNT",
    "DOCX_TEXT_CONTAINS",
    "DOCX_PARAGRAPH_COUNT",
    "DOCX_TABLE_COUNT",
    "PPTX_SLIDE_COUNT",
    "PPTX_TEXT_CONTAINS",
})

REQUIRED_VERIFIED = frozenset({
    "ARTIFACT_SHA_AND_MEASUREMENTS_DERIVED_FROM_REAL_BYTES",
    "XLSX_DOCX_PPTX_MECHANICAL_FACTS_MEASURED",
    "FAILED_XLSX_PROPERTY_FALSIFIES_ACCEPTANCE",
    "PATH_ESCAPE_FAILS_CLOSED",
    "FIELD_TYPE_MISMATCH_FAILS_CLOSED",
})

REQUIRED_NONCLAIMS = frozenset({
    "NO_CLAIM_FIELD_TO_RUBRIC_SEMANTIC_ALIGNMENT_IS_AUTOMATIC",
    "NO_CLAIM_HOLISTIC_OR_VISUAL_QUALITY_IS_MEASURED",
    "NO_GDPVAL_U_DELETION",
    "NO_TERMINAL_CREDIT",
})

SEMANTIC_ROLES = {
    "artifact_fact_source": "MEASUREMENT_VALUES_ARE_DERIVED_FROM_CONTENT_ADDRESSED_ARTIFACT_BYTES",
    "field_identity": "MEASUREMENT_REQUEST_IDS_BIND_EXACT_SUPPORTED_MECHANICAL_OPERATIONS",
    "typed_binding": "PROGRAM_CANDIDATE_FIELD_SET_AND_TYPES_MUST_EQUAL_THE_MEASUREMENT_RECEIPT",
    "proposal_values": "PROPOSAL_SUPPLIED_CANDIDATE_VALUES_HAVE_ZERO_MEASUREMENT_AUTHORITY",
    "path_boundary": "ARTIFACT_PATH_MUST_REMAIN_INSIDE_THE_DECLARED_ROOT",
    "acceptance_meaning": "TYPED_ACCEPTANCE_OPERATES_ON_MEASURED_MECHANICAL_FIELDS_NOT_SELF_DECLARED_ARTIFACT_FACTS",
    "construct_boundary": "UPSTREAM_MUST_SEPARATELY_PROVE_EACH_MEASUREMENT_FIELD_MEANS_WHAT_THE_LOAD_BEARING_TASK_CONTRACT_REQUIRES",
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
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def certify(
    governance: Mapping[str, Any],
    verification: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(governance, Mapping):
        return _fail(["GOVERNANCE_NOT_OBJECT"])
    if not isinstance(verification, Mapping):
        return _fail(["VERIFICATION_NOT_OBJECT"])
    if not isinstance(binding, Mapping):
        return _fail(["BINDING_NOT_OBJECT"])

    if governance.get("schema") != SOURCE_GOVERNANCE_SCHEMA:
        errors.append("GOVERNANCE_SCHEMA_INVALID")
    if not str(governance.get("status") or "").startswith(
        "CANDIDATE_MEASUREMENT_BRIDGE__INDEPENDENT_REPLAY_PASS"
    ):
        errors.append("GOVERNANCE_STATUS_INVALID")
    repair = governance.get("repair")
    if not isinstance(repair, Mapping):
        errors.append("REPAIR_CONTRACT_INVALID")
        repair = {}
    if set(repair.get("supported_v1") or []) != SUPPORTED_KINDS:
        errors.append("SUPPORTED_MEASUREMENT_KINDS_INVALID")
    if repair.get("rule") != (
        "CANDIDATE_FIELDS_ARE_DERIVED_FROM_CONTENT_ADDRESSED_ARTIFACT_BYTES_AND_MATCH_THE_TYPED_PROGRAM_FIELD_SET_AND_TYPES_EXACTLY"
    ):
        errors.append("MEASUREMENT_BINDING_RULE_INVALID")
    if not REQUIRED_NONCLAIMS <= set(governance.get("hard_nonclaims") or []):
        errors.append("GOVERNANCE_REQUIRED_NONCLAIMS_MISSING")

    if verification.get("schema") != SOURCE_VERIFY_SCHEMA:
        errors.append("VERIFICATION_SCHEMA_INVALID")
    if verification.get("status") != "INDEPENDENT_SPRITE_PASS__8_OF_8__ZERO_CREDIT":
        errors.append("VERIFICATION_STATUS_INVALID")
    result = verification.get("result")
    if not isinstance(result, Mapping) or result.get("passed") != 8 or result.get("total") != 8:
        errors.append("VERIFICATION_REPLAY_INVALID")
    if not REQUIRED_VERIFIED <= set(verification.get("verified") or []):
        errors.append("VERIFICATION_REQUIRED_PROPERTIES_MISSING")

    blobs = verification.get("blobs")
    if not isinstance(blobs, Mapping):
        errors.append("VERIFICATION_BLOBS_INVALID")
        blobs = {}
    if blobs.get("measurement") != binding.get("measurement_runtime_git_blob_sha"):
        errors.append("MEASUREMENT_RUNTIME_HASH_MISMATCH")
    if blobs.get("measured_acceptance") != binding.get("acceptance_runtime_git_blob_sha"):
        errors.append("ACCEPTANCE_RUNTIME_HASH_MISMATCH")

    if binding.get("root_id") != ROOT_ID:
        errors.append("BINDING_ROOT_INVALID")
    if binding.get("claim_kind") != CLAIM_KIND:
        errors.append("BINDING_CLAIM_KIND_INVALID")
    if binding.get("governance_sha256") != digest(dict(governance)):
        errors.append("GOVERNANCE_DIGEST_MISMATCH")
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
        forbidden = {
            "automatic_rubric_construct_alignment": "RUBRIC_CONSTRUCT_OVERCLAIM",
            "holistic_visual_quality_measured": "HOLISTIC_QUALITY_OVERCLAIM",
            "proposal_supplied_values_authoritative": "PROPOSAL_VALUE_AUTHORITY_OVERCLAIM",
            "unsupported_measurement_kinds_allowed": "UNSUPPORTED_MEASUREMENT_OVERCLAIM",
            "global_r4_semantic_leaf_closed": "GLOBAL_R4_SEMANTIC_OVERCLAIM",
        }
        for field, error in forbidden.items():
            if boundaries.get(field) is not False:
                errors.append(error)
        if boundaries.get("outside_supported_mechanical_kinds_stays_open") is not True:
            errors.append("OUTSIDE_SUPPORTED_KINDS_BOUNDARY_MISSING")

    claim_scope = {
        "kind": CLAIM_KIND,
        "measurement_kinds": sorted(SUPPORTED_KINDS),
        "guarantees": [
            "MEASUREMENT_VALUES_ARE_DERIVED_FROM_CONTENT_ADDRESSED_ARTIFACT_BYTES",
            "EACH_MEASUREMENT_REQUEST_IS_CONTENT_ADDRESSED_AND_TYPED",
            "THE_MEASURED_FIELD_SET_AND_TYPES_MUST_MATCH_THE_TYPED_ACCEPTANCE_PROGRAM_EXACTLY",
            "ARTIFACT_PATH_ESCAPE_FAILS_CLOSED",
            "PROPOSAL_SUPPLIED_CANDIDATE_VALUES_DO_NOT_DEFINE_ARTIFACT_FACTS",
            "A_FAILED_MEASURED_PROPERTY_CAN_FALSIFY_TYPED_ACCEPTANCE",
        ],
        "limitations": [
            "NO_AUTOMATIC_FIELD_TO_RUBRIC_OR_CONSTRUCT_SEMANTIC_ALIGNMENT",
            "NO_HOLISTIC_OR_VISUAL_QUALITY_MEASUREMENT",
            "NO_UNSUPPORTED_MEASUREMENT_KIND_SEMANTICS",
            "NO_GLOBAL_R4_SEMANTIC_LEAF_CLOSURE",
            "NO_GLOBAL_R4_ROOT_CLOSURE",
        ],
    }

    return {
        "schema": SCHEMA,
        "pass": not errors,
        "status": (
            "PASS__CONTENT_ADDRESSED_TYPED_MECHANICAL_MEASUREMENT_SEMANTICS_BOUND"
            if not errors else "FAIL_CLOSED"
        ),
        "errors": sorted(set(errors)),
        "root_id": ROOT_ID,
        "claim_scope": claim_scope,
        "governance_sha256": digest(dict(governance)),
        "verification_sha256": digest(dict(verification)),
        "semantic_leaf_credit": False,
        "global_leaf_closure": False,
        "global_root_closure": False,
        "domain_semantic_closure": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
