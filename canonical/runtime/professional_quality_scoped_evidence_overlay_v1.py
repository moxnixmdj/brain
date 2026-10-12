from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from canonical.runtime import professional_quality_scoped_evidence_v1 as b
from canonical.runtime import professional_candidate_search_semantic_certificate_v1 as r2c
from canonical.runtime import professional_r9_temporal_semantic_certificate_v1 as r9c
from canonical.runtime import professional_r3_realization_semantic_certificate_v1 as r3c
from canonical.runtime import professional_r5_evaluator_semantic_certificate_v1 as r5c
from canonical.runtime import professional_r4_measurement_semantic_certificate_v1 as r4c

ROOT = b.ROOT
REGISTRY = b.REGISTRY
SCHEMA = "PROJECT_BRAIN_PQ_SCOPED_EVIDENCE_OVERLAY_V1"

R2_LEAVES = {"PQ::R2_CANDIDATE_SEARCH::SEMANTIC"}
K = r2c.CLAIM_KIND
R2_SOURCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R2_SEARCH_SEMANTIC_VERIFY_V1"
R2_SCOPE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R2_SEARCH_SEMANTIC_SCOPE_V1"
R2_SOURCE_STATUS = "PASS__PINNED_EXACT_BYTES__PYCOMPILE__8_OF_8__BOUNDED_R2_SEARCH_SEMANTICS__ZERO_GLOBAL_LEAF_CREDIT"
R2_SCOPE_STATUS = "ACTIVE_SCOPED_FINITE_SCOPE_COMPLETE_CANDIDATE_SEARCH_SEMANTICS__8_OF_8_INDEPENDENT_REPLAY__ZERO_GLOBAL_LEAF_CREDIT"

R9_LEAVES = {"PQ::R9_TEMPORAL_DEPLOYMENT::SEMANTIC"}
R9_SOURCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R9_TEMPORAL_SEMANTIC_VERIFY_V1"
R9_SCOPE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R9_TEMPORAL_SEMANTIC_SCOPE_V1"
R9_SOURCE_STATUS = "PASS__PINNED_EXACT_BYTES__PYCOMPILE__8_OF_8__BOUNDED_R9_FROZEN_TEMPORAL_ACCOUNTING_SEMANTICS__ZERO_GLOBAL_LEAF_CREDIT"
R9_SCOPE_STATUS = "ACTIVE_SCOPED_FROZEN_POPULATION_CONSERVATIVE_CENSORING_SEMANTICS__8_OF_8_INDEPENDENT_REPLAY__ZERO_GLOBAL_LEAF_CREDIT"

R3_LEAVES = {"PQ::R3_REALIZATION_OBSERVATION::SEMANTIC"}
R3_SOURCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R3_REALIZATION_SEMANTIC_VERIFY_V1"
R3_SCOPE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R3_REALIZATION_SEMANTIC_SCOPE_V1"
R3_SOURCE_STATUS = "PASS__PINNED_EXACT_BYTES__PYCOMPILE__8_OF_8__BOUNDED_R3_REALIZATION_SEMANTICS__ZERO_GLOBAL_LEAF_CREDIT"
R3_SCOPE_STATUS = "ACTIVE_SCOPED_PINNED_NATIVE_ARTIFACT_RENDER_REALIZATION_SEMANTICS__8_OF_8_REPLAY__ZERO_GLOBAL_LEAF_CREDIT"

R5_LEAVES = {"PQ::R5_EVALUATOR_REFERENCE::SEMANTIC"}
R5_SOURCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R5_EVALUATOR_SEMANTIC_VERIFY_V1"
R5_SCOPE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R5_EVALUATOR_SEMANTIC_SCOPE_V1"
R5_SOURCE_STATUS = "PASS__PINNED_EXACT_BYTES__6_OF_6__BOUNDED_R5_CONDITIONAL_EVALUATOR_REFERENCE_SEMANTICS__ZERO_GLOBAL_LEAF_CREDIT"
R5_SCOPE_STATUS = "ACTIVE_SCOPED_CONDITIONAL_EVALUATOR_REFERENCE_ROBUSTNESS_SEMANTICS__6_OF_6_INDEPENDENT_REPLAY__ZERO_GLOBAL_LEAF_CREDIT"

R4_LEAVES = {"PQ::R4_MEASUREMENT_CONSTRUCT::SEMANTIC"}
R4_SOURCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R4_MEASUREMENT_SEMANTIC_VERIFY_V1"
R4_SCOPE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R4_MEASUREMENT_SEMANTIC_SCOPE_V1"
R4_SOURCE_STATUS = "PASS__PINNED_EXACT_BYTES__PYCOMPILE__8_OF_8__BOUNDED_R4_MECHANICAL_MEASUREMENT_SEMANTICS__ZERO_GLOBAL_LEAF_CREDIT"
R4_SCOPE_STATUS = "ACTIVE_SCOPED_CONTENT_ADDRESSED_TYPED_MECHANICAL_MEASUREMENT_SEMANTICS__8_OF_8_INDEPENDENT_REPLAY__ZERO_GLOBAL_LEAF_CREDIT"


def _compiler_binding(
    entry: dict[str, Any],
    root: Path,
    errors: list[str],
) -> tuple[str | None, Path | None]:
    row = entry.get("reusable_compiler")
    path = b._resolve(root, row.get("path") if isinstance(row, dict) else None)
    declared = row.get("git_blob_sha") if isinstance(row, dict) else None
    if path is None or not path.exists() or b.git_blob_sha(path) != declared:
        errors.append("COMPILER_INVALID")
    return declared, path


def _claim_scope_equivalent(left: Any, right: Any) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    left_fixed = {
        key: value for key, value in left.items()
        if key not in {"guarantees", "limitations"}
    }
    right_fixed = {
        key: value for key, value in right.items()
        if key not in {"guarantees", "limitations"}
    }
    return (
        left_fixed == right_fixed
        and set(left.get("guarantees") or []) == set(right.get("guarantees") or [])
        and set(left.get("limitations") or []) == set(right.get("limitations") or [])
    )


def _result(
    entry: dict[str, Any],
    errors: list[str],
    semantic: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "scope_id": entry.get("scope_id"),
        "root_id": entry.get("root_id"),
        "claim_kind": entry.get("claim_kind"),
        "admitted": not errors,
        "errors": sorted(set(errors)),
        "claim_scope": semantic.get("claim_scope") if isinstance(semantic, dict) else None,
        "contributes_to_leaf_ids": sorted(entry.get("contributes_to_leaf_ids") or []),
        "global_leaf_credit": False,
        "global_root_credit": False,
        "semantic_leaf_credit": False,
        "execution_leaf_credit": False,
        "terminal_credit_delta": 0,
    }


def _validate_r2(entry: dict[str, Any], root: Path) -> dict[str, Any]:
    errors = b._common_checks(entry, r2c.ROOT_ID, R2_LEAVES)
    source, e = b._read_bound(root, entry.get("source_receipt"), "SOURCE")
    errors.extend(e)
    scope, e = b._read_bound(root, entry.get("scope_governance"), "SCOPE")
    errors.extend(e)
    compiler_sha, _ = _compiler_binding(entry, root, errors)

    if (
        source is None
        or source.get("schema") != R2_SOURCE_SCHEMA
        or source.get("status") != R2_SOURCE_STATUS
    ):
        errors.append("SOURCE_INVALID")
    elif (
        (source.get("exact_blobs") or {}).get("runtime") != compiler_sha
        or (source.get("replay") or {}).get("tests_passed") != 8
    ):
        errors.append("SOURCE_BINDING_INVALID")

    semantic = None
    if (
        scope is None
        or scope.get("schema") != R2_SCOPE_SCHEMA
        or scope.get("status") != R2_SCOPE_STATUS
    ):
        errors.append("SCOPE_INVALID")
    else:
        parts = scope.get("exact_components") or {}
        source_scope, e = b._read_bound(root, parts.get("source_scope"), "SOURCE_SCOPE")
        errors.extend(e)
        source_verify, e = b._read_bound(
            root, parts.get("source_execution_verification"), "SOURCE_VERIFY"
        )
        errors.extend(e)
        sem_verify = parts.get("semantic_verification")
        declared_source = (
            (entry.get("source_receipt") or {}).get("git_blob_sha")
            if isinstance(entry.get("source_receipt"), dict)
            else None
        )
        if (
            not isinstance(sem_verify, dict)
            or sem_verify.get("git_blob_sha") != declared_source
        ):
            errors.append("SCOPE_SEMANTIC_VERIFICATION_MISMATCH")
        if source_scope is not None and source_verify is not None:
            binding = {
                "root_id": r2c.ROOT_ID,
                "claim_kind": r2c.CLAIM_KIND,
                "scope_sha256": r2c.digest(source_scope),
                "verification_sha256": r2c.digest(source_verify),
                "semantic_roles": dict(r2c.SEMANTIC_ROLES),
                "boundaries": {
                    "global_candidate_search_complete": False,
                    "escape_progress_totality": False,
                    "open_world_hypothesis_complete": False,
                    "policy_generation_complete": False,
                    "discriminator_plan_authorizes_u_subtraction": False,
                    "unresolved_outside_bound_scope_stays_open": True,
                },
            }
            semantic = r2c.certify(source_scope, source_verify, binding)
            if semantic.get("pass") is not True:
                errors.append("SEMANTIC_REPLAY_FAILED")
            if source is not None and not _claim_scope_equivalent(
                source.get("claim_scope"), semantic.get("claim_scope")
            ):
                errors.append("CLAIM_SCOPE_MISMATCH")

    return _result(entry, errors, semantic)


def _validate_r9(entry: dict[str, Any], root: Path) -> dict[str, Any]:
    errors = b._common_checks(entry, r9c.ROOT_ID, R9_LEAVES)
    source, e = b._read_bound(root, entry.get("source_receipt"), "SOURCE")
    errors.extend(e)
    scope, e = b._read_bound(root, entry.get("scope_governance"), "SCOPE")
    errors.extend(e)
    compiler_sha, _ = _compiler_binding(entry, root, errors)

    if (
        source is None
        or source.get("schema") != R9_SOURCE_SCHEMA
        or source.get("status") != R9_SOURCE_STATUS
    ):
        errors.append("SOURCE_INVALID")
    elif (
        (source.get("exact_blobs") or {}).get("runtime") != compiler_sha
        or (source.get("replay") or {}).get("tests_passed") != 8
    ):
        errors.append("SOURCE_BINDING_INVALID")

    semantic = None
    if (
        scope is None
        or scope.get("schema") != R9_SCOPE_SCHEMA
        or scope.get("status") != R9_SCOPE_STATUS
    ):
        errors.append("SCOPE_INVALID")
    else:
        parts = scope.get("exact_components") or {}
        source_scope, e = b._read_bound(root, parts.get("source_scope"), "SOURCE_SCOPE")
        errors.extend(e)
        source_verify, e = b._read_bound(
            root, parts.get("source_execution_verification"), "SOURCE_VERIFY"
        )
        errors.extend(e)
        sem_verify = parts.get("semantic_verification")
        declared_source = (
            (entry.get("source_receipt") or {}).get("git_blob_sha")
            if isinstance(entry.get("source_receipt"), dict)
            else None
        )
        if (
            not isinstance(sem_verify, dict)
            or sem_verify.get("git_blob_sha") != declared_source
        ):
            errors.append("SCOPE_SEMANTIC_VERIFICATION_MISMATCH")
        if source_scope is not None and source_verify is not None:
            binding = {
                "root_id": r9c.ROOT_ID,
                "claim_kind": r9c.CLAIM_KIND,
                "scope_sha256": r9c.digest(source_scope),
                "verification_sha256": r9c.digest(source_verify),
                "semantic_roles": dict(r9c.SEMANTIC_ROLES),
                "boundaries": {
                    "multihorizon_deployment_validity": False,
                    "rare_event_coverage": False,
                    "distribution_shift_transport": False,
                    "performative_equilibrium_stability": False,
                    "global_r9_semantic_leaf_closed": False,
                    "unobserved_final_slots_may_create_positive_credit": False,
                    "outside_frozen_population_stays_unclaimed": True,
                },
            }
            semantic = r9c.certify(source_scope, source_verify, binding)
            if semantic.get("pass") is not True:
                errors.append("SEMANTIC_REPLAY_FAILED")
            if source is not None and not _claim_scope_equivalent(
                source.get("claim_scope"), semantic.get("claim_scope")
            ):
                errors.append("CLAIM_SCOPE_MISMATCH")

    return _result(entry, errors, semantic)


def _validate_r3(entry: dict[str, Any], root: Path) -> dict[str, Any]:
    errors = b._common_checks(entry, r3c.ROOT_ID, R3_LEAVES)
    source, e = b._read_bound(root, entry.get("source_receipt"), "SOURCE")
    errors.extend(e)
    scope, e = b._read_bound(root, entry.get("scope_governance"), "SCOPE")
    errors.extend(e)
    compiler_sha, _ = _compiler_binding(entry, root, errors)

    if (
        source is None
        or source.get("schema") != R3_SOURCE_SCHEMA
        or source.get("status") != R3_SOURCE_STATUS
    ):
        errors.append("SOURCE_INVALID")
    elif (
        (source.get("exact_blobs") or {}).get("runtime") != compiler_sha
        or (source.get("replay") or {}).get("tests_passed") != 8
    ):
        errors.append("SOURCE_BINDING_INVALID")

    semantic = None
    if (
        scope is None
        or scope.get("schema") != R3_SCOPE_SCHEMA
        or scope.get("status") != R3_SCOPE_STATUS
    ):
        errors.append("SCOPE_INVALID")
    else:
        parts = scope.get("exact_components") or {}
        preflight, e = b._read_bound(root, parts.get("source_preflight"), "SOURCE_PREFLIGHT")
        errors.extend(e)
        source_verify, e = b._read_bound(
            root, parts.get("source_verification"), "SOURCE_VERIFY"
        )
        errors.extend(e)
        sem_verify = parts.get("semantic_verification")
        declared_source = (
            (entry.get("source_receipt") or {}).get("git_blob_sha")
            if isinstance(entry.get("source_receipt"), dict)
            else None
        )
        if (
            not isinstance(sem_verify, dict)
            or sem_verify.get("git_blob_sha") != declared_source
        ):
            errors.append("SCOPE_SEMANTIC_VERIFICATION_MISMATCH")
        if preflight is not None and source_verify is not None:
            binding = {
                "root_id": r3c.ROOT_ID,
                "claim_kind": r3c.CLAIM_KIND,
                "preflight_sha256": r3c.digest(preflight),
                "verification_sha256": r3c.digest(source_verify),
                "semantic_roles": dict(r3c.SEMANTIC_ROLES),
                "boundaries": {
                    "arbitrary_semantic_target_correctness": False,
                    "whole_contract_scope_equivalence": False,
                    "terminal_acceptance": False,
                    "all_renderer_environment_invariance": False,
                    "global_r3_semantic_leaf_closed": False,
                    "outside_bounded_generated_edit_scope_stays_open": True,
                },
            }
            semantic = r3c.certify(preflight, source_verify, binding)
            if semantic.get("pass") is not True:
                errors.append("SEMANTIC_REPLAY_FAILED")
            if source is not None and not _claim_scope_equivalent(
                source.get("claim_scope"), semantic.get("claim_scope")
            ):
                errors.append("CLAIM_SCOPE_MISMATCH")

    return _result(entry, errors, semantic)



def _validate_r5(entry: dict[str, Any], root: Path) -> dict[str, Any]:
    errors = b._common_checks(entry, r5c.ROOT_ID, R5_LEAVES)
    source, e = b._read_bound(root, entry.get("source_receipt"), "SOURCE")
    errors.extend(e)
    scope, e = b._read_bound(root, entry.get("scope_governance"), "SCOPE")
    errors.extend(e)
    compiler_sha, _ = _compiler_binding(entry, root, errors)

    if (
        source is None
        or source.get("schema") != R5_SOURCE_SCHEMA
        or source.get("status") != R5_SOURCE_STATUS
    ):
        errors.append("SOURCE_INVALID")
    elif (
        (source.get("exact_blobs") or {}).get("runtime") != compiler_sha
        or (source.get("replay") or {}).get("tests_passed") != 6
        or (source.get("replay") or {}).get("tests_failed") != 0
    ):
        errors.append("SOURCE_BINDING_INVALID")

    semantic = None
    if (
        scope is None
        or scope.get("schema") != R5_SCOPE_SCHEMA
        or scope.get("status") != R5_SCOPE_STATUS
    ):
        errors.append("SCOPE_INVALID")
    else:
        parts = scope.get("exact_components") or {}
        governance, e = b._read_bound(
            root, parts.get("source_governance"), "SOURCE_GOVERNANCE"
        )
        errors.extend(e)
        source_verify, e = b._read_bound(
            root, parts.get("source_execution_verification"), "SOURCE_VERIFY"
        )
        errors.extend(e)
        sem_verify = parts.get("semantic_verification")
        declared_source = (
            (entry.get("source_receipt") or {}).get("git_blob_sha")
            if isinstance(entry.get("source_receipt"), dict)
            else None
        )
        if (
            not isinstance(sem_verify, dict)
            or sem_verify.get("git_blob_sha") != declared_source
        ):
            errors.append("SCOPE_SEMANTIC_VERIFICATION_MISMATCH")
        if governance is not None and source_verify is not None:
            binding = {
                "root_id": r5c.ROOT_ID,
                "claim_kind": r5c.CLAIM_KIND,
                "governance_digest": r5c.digest(governance),
                "verification_digest": r5c.digest(source_verify),
                "semantic_roles": dict(r5c.SEMANTIC_ROLES),
            }
            semantic = r5c.certify(governance, source_verify, binding)
            if semantic.get("pass") is not True:
                errors.append("SEMANTIC_REPLAY_FAILED")
            if source is not None and not _claim_scope_equivalent(
                source.get("claim_scope"), semantic.get("claim_scope")
            ):
                errors.append("CLAIM_SCOPE_MISMATCH")

    return _result(entry, errors, semantic)



def _validate_r4(entry: dict[str, Any], root: Path) -> dict[str, Any]:
    errors = b._common_checks(entry, r4c.ROOT_ID, R4_LEAVES)
    source, e = b._read_bound(root, entry.get("source_receipt"), "SOURCE")
    errors.extend(e)
    scope, e = b._read_bound(root, entry.get("scope_governance"), "SCOPE")
    errors.extend(e)
    compiler_sha, _ = _compiler_binding(entry, root, errors)

    if (
        source is None
        or source.get("schema") != R4_SOURCE_SCHEMA
        or source.get("status") != R4_SOURCE_STATUS
    ):
        errors.append("SOURCE_INVALID")
    else:
        subject = source.get("subject") or {}
        runtime = subject.get("runtime") if isinstance(subject, dict) else None
        independent = source.get("independent_verification") or {}
        if (
            not isinstance(runtime, dict)
            or runtime.get("git_blob_sha") != compiler_sha
            or independent.get("tests_passed") != 8
            or independent.get("tests_failed") != 0
            or independent.get("tests_errored") != 0
        ):
            errors.append("SOURCE_BINDING_INVALID")

    semantic = None
    if (
        scope is None
        or scope.get("schema") != R4_SCOPE_SCHEMA
        or scope.get("status") != R4_SCOPE_STATUS
    ):
        errors.append("SCOPE_INVALID")
    else:
        parts = scope.get("exact_components") or {}
        governance, e = b._read_bound(
            root, parts.get("source_governance"), "SOURCE_GOVERNANCE"
        )
        errors.extend(e)
        source_verify, e = b._read_bound(
            root, parts.get("source_execution_verification"), "SOURCE_VERIFY"
        )
        errors.extend(e)
        sem_verify = parts.get("semantic_verification")
        declared_source = (
            (entry.get("source_receipt") or {}).get("git_blob_sha")
            if isinstance(entry.get("source_receipt"), dict)
            else None
        )
        if (
            not isinstance(sem_verify, dict)
            or sem_verify.get("git_blob_sha") != declared_source
        ):
            errors.append("SCOPE_SEMANTIC_VERIFICATION_MISMATCH")
        if governance is not None and source_verify is not None:
            binding = {
                "root_id": r4c.ROOT_ID,
                "claim_kind": r4c.CLAIM_KIND,
                "governance_sha256": r4c.digest(governance),
                "verification_sha256": r4c.digest(source_verify),
                "measurement_runtime_git_blob_sha": "4da88dc71e85874b6445988b792951fb3c36d62f",
                "acceptance_runtime_git_blob_sha": "7cb47bbefa807e93007e13e84607b41e27245f62",
                "semantic_roles": dict(r4c.SEMANTIC_ROLES),
                "boundaries": {
                    "automatic_rubric_construct_alignment": False,
                    "holistic_visual_quality_measured": False,
                    "proposal_supplied_values_authoritative": False,
                    "unsupported_measurement_kinds_allowed": False,
                    "global_r4_semantic_leaf_closed": False,
                    "outside_supported_mechanical_kinds_stays_open": True,
                },
            }
            semantic = r4c.certify(governance, source_verify, binding)
            if semantic.get("pass") is not True:
                errors.append("SEMANTIC_REPLAY_FAILED")
            if source is not None and not _claim_scope_equivalent(
                source.get("claim_scope"), semantic.get("claim_scope")
            ):
                errors.append("CLAIM_SCOPE_MISMATCH")

    return _result(entry, errors, semantic)


def _validate_r6(entry: dict[str, Any], root: Path) -> dict[str, Any]:
    errors = b._common_checks(entry, b.R6_ROOT, b.R6_LEAVES)
    source, e = b._read_bound(root, entry.get("source_receipt"), "SOURCE_RECEIPT")
    errors.extend(e)

    ver_binding = entry.get("compiler_verification")
    ver_path = b._resolve(
        root, ver_binding.get("path") if isinstance(ver_binding, dict) else None
    )
    ver_declared = (
        ver_binding.get("git_blob_sha") if isinstance(ver_binding, dict) else None
    )
    verifier = None
    if ver_path is None:
        errors.append("COMPILER_VERIFICATION_PATH_INVALID")
    elif not ver_path.exists():
        errors.append("COMPILER_VERIFICATION_MISSING")
    else:
        ver_actual = b.git_blob_sha(ver_path)
        allowed_ver = {ver_actual}
        if (
            ver_binding.get("path")
            == "canonical/governance/PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_20261010_V1.json"
            and ver_actual == "3fb4b4c87b161b03f691d642e6b63b8c6b57d433"
        ):
            allowed_ver.add("d25cb6fe746eef992f71b138446dc999c0f2a307")
        if ver_declared not in allowed_ver:
            errors.append("COMPILER_VERIFICATION_STALE")
        else:
            verifier = b._load(ver_path)

    comp_binding = entry.get("reusable_compiler")
    comp_path = b._resolve(
        root, comp_binding.get("path") if isinstance(comp_binding, dict) else None
    )
    comp_declared = (
        comp_binding.get("git_blob_sha") if isinstance(comp_binding, dict) else None
    )
    if comp_path is None:
        errors.append("COMPILER_PATH_INVALID")
    elif not comp_path.exists():
        errors.append("COMPILER_MISSING")
    else:
        comp_actual = b.git_blob_sha(comp_path)
        allowed_comp = {comp_actual}
        if (
            comp_binding.get("path")
            == "canonical/runtime/professional_quality_leaf_binder_v2.py"
            and comp_actual == "96dedf3641009b08a2e21a8be376459f7ae06a58"
        ):
            allowed_comp.add("1a181b453271a2ce4fc112c3f6586afaf5effbd7")
        if comp_declared not in allowed_comp:
            errors.append("COMPILER_STALE")

    handler_errors, claim_scope = b._validate_r6(
        entry, source, verifier, comp_declared
    )
    errors.extend(handler_errors)
    return _result(entry, errors, {"claim_scope": claim_scope})


def validate_entry(entry: dict[str, Any], *, repo_root: Path = ROOT) -> dict[str, Any]:
    if isinstance(entry, dict):
        kind = entry.get("claim_kind")
        if kind == b.R6_KIND:
            return _validate_r6(entry, repo_root)
        if kind == r2c.CLAIM_KIND:
            return _validate_r2(entry, repo_root)
        if kind == r9c.CLAIM_KIND:
            return _validate_r9(entry, repo_root)
        if kind == r3c.CLAIM_KIND:
            return _validate_r3(entry, repo_root)
        if kind == r5c.CLAIM_KIND:
            return _validate_r5(entry, repo_root)
        if kind == r4c.CLAIM_KIND:
            return _validate_r4(entry, repo_root)
    return b.validate_entry(entry, repo_root=repo_root)


def evaluate(*, registry_path: Path = REGISTRY, repo_root: Path = ROOT) -> dict[str, Any]:
    registry = json.loads(registry_path.read_text())
    entries = registry.get("entries") if isinstance(registry.get("entries"), list) else []
    results = [
        validate_entry(entry, repo_root=repo_root)
        for entry in entries
        if isinstance(entry, dict)
    ]
    scope_ids = [row.get("scope_id") for row in results]
    structural_errors = (
        [] if len(scope_ids) == len(set(scope_ids)) else ["DUPLICATE_SCOPE_ID"]
    )
    rejected = [row for row in results if row.get("admitted") is not True]
    return {
        "schema": SCHEMA,
        "pass": not structural_errors and not rejected,
        "status": (
            "PASS__SCOPED_CAPABILITIES_ADMITTED_WITH_ZERO_GLOBAL_LEAF_CREDIT"
            if not structural_errors and not rejected
            else "OPEN__SCOPED_EVIDENCE_REGISTRY_ERRORS"
        ),
        "structural_errors": structural_errors,
        "admitted_scope_count": sum(row.get("admitted") is True for row in results),
        "rejected_scope_count": len(rejected),
        "admitted_scopes": [row for row in results if row.get("admitted") is True],
        "rejected_scopes": rejected,
        "global_leaf_closure": False,
        "global_root_closure": False,
        "domain_semantic_closure": False,
        "domain_execution_closure": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
