"""Exact-byte adapter from one independently verified P3 top-law region to a residual atom.

This is deliberately P3-specific. It does not accept caller-selected verification
receipts or self-asserted "verified" flags. The canonical region and independent
verification receipt are pinned by Git blob SHA, then their theorem/ownership
flags are checked before a symbolic admission atom is emitted.

A pass means only that the atom has a real, exact-byte semantic binding to the
verified parameterized P3 region. It does not make the union of regions complete.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes

SCHEMA = "PROJECT_BRAIN_P3_VERIFIED_REGION_RESIDUAL_ADAPTER_V1"
SCOPE_ID = "scope://project-brain/universal-escape-v1"
ATOM_ID = "P3_STRICT_TOPLAW_REGION"
REGION_PATH = "canonical/governance/P3_BOUND_BINARY_REAL_CONTEXT_TOP_LAW_REGION_20261008_V1.json"
REGION_BLOB = "e367ff0a5734e2430b0b5476bf073b4688c410e1"
VERIFY_PATH = "canonical/verification/P3_BINARY_EXPLICIT_TOP_LAW_REGION_TWO_SPRITE_VERIFICATION_20261008_V1.json"
VERIFY_BLOB = "05dd31a787eccec0311c8abd26f21c624d4deb66"
REGION_ID = "P3_BOUND_BINARY_REAL_CONTEXT_GROUNDED_DECISION_TOP_LAW_V1"
RECOGNIZER_BLOB = "ca24d891210fb6d885a959c26a9da3451a8b67c7"
POLICY_BLOB = "590cdc4e7f5a513d0e40bb31afed20df61826bad"
VERIFIER_BLOB = "da871727e5939b5c190e9c383d6c361642168b80"


def _fail(reason: str, **more: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "real_region_atom_bound": False,
        "global_scope_complete": False,
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **more,
    }


def build_bound_residual_spec(*, repo_root: str | Path) -> dict[str, Any]:
    try:
        region_bound = resolve_receipt_bytes(
            {"path": REGION_PATH, "git_blob_sha": REGION_BLOB},
            repo_root=repo_root,
        )
        verify_bound = resolve_receipt_bytes(
            {"path": VERIFY_PATH, "git_blob_sha": VERIFY_BLOB},
            repo_root=repo_root,
        )
    except Exception as exc:
        return _fail(
            "PINNED_REGION_OR_VERIFICATION_BYTES_INVALID",
            exception_type=type(exc).__name__,
            detail=str(exc)[:200],
        )

    region = region_bound["document"]
    receipt = verify_bound["document"]
    errors: list[str] = []

    if region.get("schema") != "PROJECT_BRAIN_P3_BOUND_BINARY_REAL_CONTEXT_TOP_LAW_REGION_V1":
        errors.append("REGION_SCHEMA")
    if region.get("status") != (
        "CANDIDATE_PARAMETERIZED_SOUND_TOP_LAW_REGION__"
        "STRICT_EXPLICIT_ROOT_SOURCE_MEMBERSHIP__ZERO_GLOBAL_TERMINAL_CREDIT"
    ):
        errors.append("REGION_STATUS")

    rr = region.get("region") or {}
    if rr.get("id") != REGION_ID:
        errors.append("REGION_ID")
    recognizer = rr.get("recognizer") or {}
    policy = rr.get("policy") or {}
    if recognizer.get("git_blob_sha") != RECOGNIZER_BLOB:
        errors.append("RECOGNIZER_BINDING")
    if policy.get("git_blob_sha") != POLICY_BLOB:
        errors.append("POLICY_BINDING")

    theorem = region.get("theorem") or {}
    if theorem.get("common_policy_region") is not True:
        errors.append("COMMON_POLICY_REGION")
    if theorem.get("target_comparator_required") is not False:
        errors.append("TARGET_COMPARATOR")
    if theorem.get("exact_target_identity_required") is not False:
        errors.append("TARGET_IDENTITY")

    resource = region.get("resource_and_ownership") or {}
    if resource.get("brain_owned") is not True:
        errors.append("BRAIN_OWNERSHIP")
    if resource.get("exact_runtime_bytes_bound") is not True:
        errors.append("RUNTIME_BYTES")
    if resource.get("no_external_target_model_runtime_dependency") is not True:
        errors.append("EXTERNAL_TARGET_DEPENDENCY")

    if receipt.get("schema") != "PROJECT_BRAIN_P3_BINARY_EXPLICIT_TOP_LAW_REGION_TWO_SPRITE_VERIFICATION_V1":
        errors.append("VERIFY_SCHEMA")
    if receipt.get("status") != (
        "PASS_ON_TWO_SPRITES__STRICT_EXPLICIT_P3_BINARY_PARAMETERIZED_TOP_LAW_REGION_VERIFIED__"
        "ZERO_GLOBAL_CREDIT"
    ):
        errors.append("VERIFY_STATUS")
    subject = receipt.get("subject") or {}
    subject_region = subject.get("region") or {}
    subject_verifier = subject.get("verifier") or {}
    if subject_region.get("path") != REGION_PATH or subject_region.get("git_blob_sha") != REGION_BLOB:
        errors.append("VERIFY_REGION_BINDING")
    if subject_verifier.get("git_blob_sha") != VERIFIER_BLOB:
        errors.append("VERIFY_VERIFIER_BINDING")
    verification_runs = receipt.get("verification") or []
    if (
        not isinstance(verification_runs, list)
        or len(verification_runs) != 2
        or any(row.get("result") != "PASS" for row in verification_runs if isinstance(row, dict))
        or any(not isinstance(row, dict) for row in verification_runs)
    ):
        errors.append("VERIFY_TWO_SPRITE_RUNS")

    verified = receipt.get("verified") or {}
    required_true = (
        "exact_region_bytes",
        "explicit_membership_20_of_20_two_sprite_receipt",
        "binary_expression_11_of_11_two_sprite_receipt",
        "no_caller_membership_flag_or_semantic_extractor",
        "old_self_certifying_membership_route_promotion_invalidated",
        "explicit_selection_order_top_law_common_policy",
        "p3_required_checks_imply_synthesis_contract_success",
        "parameterized_D_B_region_candidate",
    )
    for key in required_true:
        if verified.get(key) is not True:
            errors.append("VERIFY_FLAG:" + key)
    if verified.get("target_comparator_required") is not False:
        errors.append("VERIFY_TARGET_COMPARATOR")
    for key in ("free_form_p3_closed", "whole_p3_closed", "u_empty", "terminal"):
        if verified.get(key) is not False:
            errors.append("VERIFY_FORBIDDEN_GLOBAL_FLAG:" + key)

    if errors:
        return _fail("PINNED_REGION_THEOREM_INVALID", errors=sorted(errors))

    spec = {
        "schema": "PROJECT_BRAIN_UNIVERSAL_RESIDUAL_SPEC_V1",
        "scope_id": SCOPE_ID,
        "variables": [ATOM_ID],
        "overapprox_cnf": [],
        "routes": [
            {
                "route_id": REGION_ID,
                "admission_cnf": [[ATOM_ID]],
            }
        ],
    }
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__EXACT_P3_VERIFIED_REGION_BOUND_TO_ONE_RESIDUAL_ATOM",
        "atom_id": ATOM_ID,
        "atom_semantics": (
            "TRUE_IFF_UPSTREAM_ROOT_TASK_BYTES_PASS_THE_EXACT_PINNED_"
            "P3_BINARY_EXPLICIT_CONTRACT_MEMBERSHIP_V1_RECOGNIZER"
        ),
        "region_id": REGION_ID,
        "region_git_blob_sha": REGION_BLOB,
        "verification_git_blob_sha": VERIFY_BLOB,
        "real_region_atom_bound": True,
        "spec": spec,
        "expected_residual_semantics": (
            "THE_SINGLE_REGION_SEED_RESIDUAL_IS_EXACTLY_THE_COMPLEMENT_OF_THE_"
            "VERIFIED_STRICT_EXPLICIT_P3_BINARY_TOP_LAW_REGION_WITHIN_TOP"
        ),
        "global_scope_complete": False,
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
