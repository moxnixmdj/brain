"""Bounded R3 realization/observation semantic certificate.

Defines what the existing native-artifact render-preservation preflight means.
It certifies one pinned realization/observation contract for generated bounded
low-level text edits; it does not promote render preservation into arbitrary
semantic correctness or whole-contract equivalence.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_R3_REALIZATION_SEMANTIC_CERTIFICATE_V1"
ROOT_ID = "R3_REALIZATION_OBSERVATION"
SOURCE_PREFLIGHT_SCHEMA = "PROJECT_BRAIN_NATIVE_ARTIFACT_RENDER_PRESERVATION_PREFLIGHT_V1"
SOURCE_VERIFY_SCHEMA = "PROJECT_BRAIN_NATIVE_ARTIFACT_RENDER_PRESERVATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1"
CLAIM_KIND = "PINNED_NATIVE_ARTIFACT_RENDER_REALIZATION_SEMANTICS"

FORMATS = ("docx", "xlsx", "pptx", "pdf")
REQUIRED_VERIFIED = frozenset({
    "DOCX_XLSX_PPTX_RENDER_THROUGH_LIBREOFFICE_AND_ALL_FORMATS_RASTERIZE_THROUGH_POPPLER",
    "SOURCE_AND_OUTPUT_PAGE_COUNTS_EQUAL",
    "SOURCE_AND_OUTPUT_PAGE_PIXEL_DIMENSIONS_EQUAL",
    "UNCHANGED_PAGES_ARE_ACCEPTED_AS_PRESERVED",
    "AT_LEAST_ONE_PAGE_MUST_VISIBLY_CHANGE",
    "CHANGED_PIXELS_AND_BOUNDING_BOX_MUST_REMAIN_WITHIN_FROZEN_LOCALIZATION_BOUNDS",
    "UNCHANGED_WHOLE_OUTPUT_IS_REJECTED",
    "LARGE_DOCX_PAGE_GEOMETRY_MUTATION_IS_REJECTED",
    "STRUCTURAL_HIDDEN_ORACLE_MUST_PASS_BEFORE_RENDER_ACCEPTANCE",
    "EXACT_BRAIN_BLOBS_VERIFIED_BY_PUBLIC_CAPSULE",
})
REQUIRED_LIMITATIONS = frozenset({
    "BOUNDED_GENERATED_EXPLICIT_LOW_LEVEL_TEXT_EDITS_ONLY",
    "NO_ARBITRARY_SEMANTIC_TARGET_SELECTION",
    "NO_WHOLE_OPEN_ENDED_NATIVE_ARTIFACT_CONTRACT_SCOPE_EQUIVALENCE",
    "NO_TERMINAL_ACCEPTANCE_OR_CAPABILITY_CREDIT",
})

SEMANTIC_ROLES = {
    "subject_pair": "SOURCE_AND_OUTPUT_BYTES_FOR_ONE_GENERATED_BOUNDED_EDIT_CASE",
    "realization_stack": "PINNED_LIBREOFFICE_TO_PDF_PLUS_POPPLER_96_DPI_RASTERIZATION",
    "structural_gate": "HIDDEN_STRUCTURAL_ORACLE_MUST_PASS_BEFORE_RENDER_ACCEPTANCE",
    "page_identity": "SOURCE_AND_OUTPUT_PAGE_COUNTS_AND_PIXEL_DIMENSIONS_MUST_MATCH",
    "unchanged_page": "ZERO_PIXEL_DELTA_PAGE_IS_PRESERVED_NOT_A_FAILURE",
    "visible_edit": "AT_LEAST_ONE_PAGE_MUST_CHANGE_VISIBLY",
    "localization": "EVERY_CHANGED_PAGE_MUST_STAY_WITHIN_FROZEN_PIXEL_AND_BOUNDING_BOX_LIMITS",
    "acceptance_meaning": "BOUNDED_RENDER_AND_STRUCTURE_PRESERVATION_ONLY",
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
    preflight: Mapping[str, Any],
    verification: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(preflight, Mapping):
        return _fail(["PREFLIGHT_NOT_OBJECT"])
    if not isinstance(verification, Mapping):
        return _fail(["VERIFICATION_NOT_OBJECT"])
    if not isinstance(binding, Mapping):
        return _fail(["BINDING_NOT_OBJECT"])

    if preflight.get("schema") != SOURCE_PREFLIGHT_SCHEMA:
        errors.append("PREFLIGHT_SCHEMA_INVALID")
    if preflight.get("behavior_id") != "NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001":
        errors.append("BEHAVIOR_ID_INVALID")
    if not str(preflight.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("PREFLIGHT_NOT_VERIFIED")
    acceptance = preflight.get("acceptance")
    if not isinstance(acceptance, Mapping):
        errors.append("ACCEPTANCE_CONTRACT_INVALID")
    else:
        expected = {
            "page_count_equal": True,
            "page_pixel_dimensions_equal": True,
            "minimum_visible_change_required": True,
            "max_changed_pixel_fraction": 0.025,
            "max_changed_bounding_box_fraction": 0.1,
            "pixel_delta_threshold": 8,
        }
        for key, value in expected.items():
            if acceptance.get(key) != value:
                errors.append("ACCEPTANCE_FIELD_INVALID:" + key)
    if set(preflight.get("anti_shortcut_checks") or []) != {
        "UNCHANGED_OUTPUT_REJECTED",
        "LARGE_DOCX_PAGE_GEOMETRY_MUTATION_REJECTED",
        "STRUCTURAL_HIDDEN_ORACLE_MUST_PASS_BEFORE_RENDER_ACCEPTANCE",
    }:
        errors.append("ANTI_SHORTCUT_CONTRACT_INVALID")
    scope_text = str(preflight.get("scope_limitation") or "")
    for token in (
        "BOUNDED_EXPLICIT_LOW_LEVEL_TEXT_EDITS_ON_GENERATED_DOCX_XLSX_PPTX_PDF",
        "NO_ARBITRARY_SEMANTIC_TARGET_SELECTION",
        "NO_WHOLE_CONTRACT_SCOPE_EQUIVALENCE",
    ):
        if token not in scope_text:
            errors.append("PREFLIGHT_SCOPE_LIMIT_MISSING:" + token)

    if verification.get("schema") != SOURCE_VERIFY_SCHEMA:
        errors.append("VERIFICATION_SCHEMA_INVALID")
    if not str(verification.get("status") or "").startswith(
        "INDEPENDENT_BOUNDED_RENDER_PRESERVATION_PREFLIGHT_PASS"
    ):
        errors.append("VERIFICATION_NOT_PASS")
    if verification.get("behavior_id") != preflight.get("behavior_id"):
        errors.append("VERIFICATION_BEHAVIOR_MISMATCH")
    if not REQUIRED_VERIFIED <= set(verification.get("verified") or []):
        errors.append("VERIFICATION_REQUIRED_PROPERTIES_MISSING")
    if not REQUIRED_LIMITATIONS <= set(verification.get("limitations") or []):
        errors.append("VERIFICATION_REQUIRED_LIMITATIONS_MISSING")

    if binding.get("root_id") != ROOT_ID:
        errors.append("BINDING_ROOT_INVALID")
    if binding.get("claim_kind") != CLAIM_KIND:
        errors.append("BINDING_CLAIM_KIND_INVALID")
    if binding.get("preflight_sha256") != digest(dict(preflight)):
        errors.append("PREFLIGHT_DIGEST_MISMATCH")
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
            "arbitrary_semantic_target_correctness": "ARBITRARY_SEMANTIC_TARGET_OVERCLAIM",
            "whole_contract_scope_equivalence": "WHOLE_CONTRACT_OVERCLAIM",
            "terminal_acceptance": "TERMINAL_ACCEPTANCE_OVERCLAIM",
            "all_renderer_environment_invariance": "RENDERER_INVARIANCE_OVERCLAIM",
            "global_r3_semantic_leaf_closed": "GLOBAL_R3_SEMANTIC_OVERCLAIM",
        }
        for field, error in forbidden.items():
            if boundaries.get(field) is not False:
                errors.append(error)
        if boundaries.get("outside_bounded_generated_edit_scope_stays_open") is not True:
            errors.append("OUTSIDE_SCOPE_OPEN_BOUNDARY_MISSING")

    claim_scope = {
        "kind": CLAIM_KIND,
        "formats": list(FORMATS),
        "behavior_id": "NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001",
        "guarantees": [
            "THE_REALIZATION_STACK_IS_THE_PINNED_LIBREOFFICE_AND_POPPLER_PIPELINE",
            "SOURCE_AND_OUTPUT_PAGE_COUNTS_AND_PIXEL_DIMENSIONS_MATCH",
            "UNCHANGED_PAGES_ARE_VALID_PRESERVATION",
            "AT_LEAST_ONE_PAGE_MUST_CHANGE_VISIBLY",
            "EVERY_CHANGED_PAGE_STAYS_WITHIN_THE_FROZEN_PIXEL_AND_BOUNDING_BOX_LIMITS",
            "THE_HIDDEN_STRUCTURAL_ORACLE_PASSES_BEFORE_RENDER_ACCEPTANCE",
            "UNCHANGED_WHOLE_OUTPUT_AND_LARGE_PAGE_GEOMETRY_MUTATION_ARE_REJECTED",
        ],
        "limitations": sorted(REQUIRED_LIMITATIONS | {
            "NO_ALL_RENDERER_OR_ENVIRONMENT_INVARIANCE",
            "NO_GLOBAL_R3_SEMANTIC_LEAF_CLOSURE",
            "NO_GLOBAL_R3_ROOT_CLOSURE",
        }),
    }
    return {
        "schema": SCHEMA,
        "pass": not errors,
        "status": (
            "PASS__PINNED_NATIVE_ARTIFACT_RENDER_REALIZATION_SEMANTICS_BOUND"
            if not errors else "FAIL_CLOSED"
        ),
        "errors": sorted(set(errors)),
        "root_id": ROOT_ID,
        "claim_scope": claim_scope,
        "preflight_sha256": digest(dict(preflight)),
        "verification_sha256": digest(dict(verification)),
        "semantic_leaf_credit": False,
        "global_leaf_closure": False,
        "global_root_closure": False,
        "domain_semantic_closure": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
