"""Claim-scoped professional-quality evidence registry validator.

Admits reusable bounded domain capability evidence without allowing it to close
the global semantic/execution leaves. Supported handlers are intentionally
explicit; unknown claim kinds fail closed instead of inheriting authority by
similarity.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json"

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_VALIDATOR_V1"
REGISTRY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_V1"

R7_KIND = "EXACT_SINGLE_EDIT_PROFESSIONAL_CODE_INTERVENTION_INSTANCE"
R7_ROOT = "R7_CAUSAL_PRESCRIPTIVE"
R7_LEAVES = {
    "PQ::R7_CAUSAL_PRESCRIPTIVE::SEMANTIC",
    "PQ::R7_CAUSAL_PRESCRIPTIVE::EXECUTION",
}
R7_SOURCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R7_SINGLE_EDIT_CAUSAL_INSTANCE_VERIFY_V1"
R7_COMPILER_VERIFY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_EDIT_CAUSAL_CERTIFICATE_VERIFY_V1"

R3_KIND = "BOUNDED_GENERATED_EXPLICIT_LOW_LEVEL_TEXT_EDIT_RENDER_PRESERVATION"
R3_ROOT = "R3_REALIZATION_OBSERVATION"
R3_LEAVES = {"PQ::R3_REALIZATION_OBSERVATION::EXECUTION"}
R3_SOURCE_SCHEMA = "PROJECT_BRAIN_NATIVE_ARTIFACT_RENDER_PRESERVATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1"
R3_PREFLIGHT_SCHEMA = "PROJECT_BRAIN_NATIVE_ARTIFACT_RENDER_PRESERVATION_PREFLIGHT_V1"

R11_KIND = "CLEAN_EVALUATION_LANE_POST_IDENTITY_DISCOVERY_REVOCATION"
R11_ROOT = "R11_ADAPTIVE_INTEGRITY_SECURITY"
R11_LEAVES = {"PQ::R11_ADAPTIVE_INTEGRITY_SECURITY::EXECUTION"}
R11_SOURCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R11_EVALUATION_FIREWALL_SCOPED_VERIFY_V1"
R11_GOVERNANCE_SCHEMA = "PROJECT_BRAIN_EVALUATION_INFORMATION_FIREWALL_GOVERNANCE_V1"

R10_KIND = "LOSSLESS_DECISION_SUFFICIENT_GAP_REPRESENTATION_AND_MINIMUM_POLICY_CHANGING_INFORMATION_ROUTING"
R10_ROOT = "R10_ANALYSIS_DECISION"
R10_LEAVES = {"PQ::R10_ANALYSIS_DECISION::EXECUTION"}
R10_SOURCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_DECISION_SUFFICIENCY_SCOPED_VERIFY_V1"
R10_HISTORY_SCHEMA = "PROJECT_BRAIN_ONE_SHOT_DECISION_SUFFICIENT_GATE_VERIFY_20261009_V2"

R6_KIND = "CONTENT_ADDRESSED_SCOPE_MATCHED_LEAF_EVIDENCE_ADMISSION_WITH_STATUS_NONAUTHORITY"
R6_ROOT = "R6_EVIDENCE_GROUNDING_DEPENDENCE"
R6_LEAVES = {"PQ::R6_EVIDENCE_GROUNDING_DEPENDENCE::EXECUTION"}
R6_SOURCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_BINDER_V2_VERIFY_V1"
R6_REGISTRY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_V1"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("utf-8") + data).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _resolve(repo_root: Path, path_text: Any) -> Path | None:
    if not isinstance(path_text, str) or not path_text.startswith("canonical/"):
        return None
    return repo_root / path_text


def _read_bound(
    repo_root: Path,
    binding: Any,
    label: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    if not isinstance(binding, dict):
        return None, [f"{label}_BINDING_INVALID"]
    path = _resolve(repo_root, binding.get("path"))
    declared = binding.get("git_blob_sha")
    if path is None:
        return None, [f"{label}_PATH_INVALID"]
    if not path.exists():
        return None, [f"{label}_MISSING"]
    actual = git_blob_sha(path)
    if actual != declared:
        return None, [f"{label}_STALE"]
    try:
        return _load(path), []
    except Exception:
        return None, [f"{label}_JSON_INVALID"]


def _common_checks(entry: dict[str, Any], expected_root: str, expected_leaves: set[str]) -> list[str]:
    errors: list[str] = []
    if entry.get("root_id") != expected_root:
        errors.append("ROOT_ID_INVALID")
    leaf_ids = entry.get("contributes_to_leaf_ids")
    if not isinstance(leaf_ids, list) or set(leaf_ids) != expected_leaves:
        errors.append("LEAF_BINDING_INVALID")
    if entry.get("global_leaf_closure") is not False:
        errors.append("GLOBAL_LEAF_CLOSURE_FORBIDDEN")
    if entry.get("global_root_closure") is not False:
        errors.append("GLOBAL_ROOT_CLOSURE_FORBIDDEN")
    if entry.get("semantic_leaf_credit") is True:
        errors.append("SEMANTIC_LEAF_CREDIT_FORBIDDEN")
    if entry.get("execution_leaf_credit") is True:
        errors.append("EXECUTION_LEAF_CREDIT_FORBIDDEN")
    if entry.get("terminal_credit_delta") != 0:
        errors.append("TERMINAL_CREDIT_FORBIDDEN")
    return errors


def _validate_r7(
    entry: dict[str, Any],
    source: dict[str, Any] | None,
    compiler_verify: dict[str, Any] | None,
    compiler_declared: Any,
) -> tuple[list[str], Any]:
    errors = _common_checks(entry, R7_ROOT, R7_LEAVES)
    claim_scope = None
    if source is not None:
        if source.get("schema") != R7_SOURCE_SCHEMA:
            errors.append("SOURCE_SCHEMA_INVALID")
        if source.get("root_id") != R7_ROOT:
            errors.append("SOURCE_ROOT_INVALID")
        scope = source.get("claim_scope")
        conclusions = source.get("conclusions")
        dispositions = source.get("r7_defeater_disposition")
        claim_scope = scope
        if not isinstance(scope, dict) or scope.get("kind") != R7_KIND:
            errors.append("SOURCE_CLAIM_SCOPE_INVALID")
        if not isinstance(conclusions, dict):
            errors.append("SOURCE_CONCLUSIONS_INVALID")
        else:
            if conclusions.get("exact_claim_scoped_professional_edit_causality_proved") is not True:
                errors.append("SOURCE_SCOPED_CAUSALITY_NOT_PROVED")
            for forbidden in (
                "r7_global_root_closed",
                "domain_semantic_closure",
                "domain_execution_closure",
                "multi_edit_attribution_proved",
                "sequence_invariance_proved",
                "treatment_generalization_proved",
            ):
                if conclusions.get(forbidden) is True:
                    errors.append("SOURCE_GLOBAL_OVERCLAIM:" + forbidden)
        expected = {
            "C28_PREDICTIVE_PRESCRIPTIVE_GAP": "DISCHARGED_FOR_THIS_EXACT_INSTANCE",
            "C30_TREATMENT_VERSION_NONINVARIANCE": "DISCHARGED_FOR_THIS_EXACT_INSTANCE",
            "C29_COMPOUND_EDIT_ATTRIBUTION": "PROVEN_IRRELEVANT_TO_THIS_CLAIM_SCOPE",
            "C31_EDIT_SEQUENCE_INTERACTION": "PROVEN_IRRELEVANT_TO_THIS_CLAIM_SCOPE",
        }
        if not isinstance(dispositions, dict):
            errors.append("SOURCE_DEFEATER_DISPOSITIONS_INVALID")
        else:
            for defeater_id, state in expected.items():
                row = dispositions.get(defeater_id)
                if not isinstance(row, dict) or row.get("claim_scoped_state") != state:
                    errors.append("SOURCE_DEFEATER_STATE_INVALID:" + defeater_id)

    if compiler_verify is not None:
        if compiler_verify.get("schema") != R7_COMPILER_VERIFY_SCHEMA:
            errors.append("COMPILER_VERIFY_SCHEMA_INVALID")
        if not str(compiler_verify.get("status") or "").startswith("PASS__"):
            errors.append("COMPILER_VERIFY_NOT_PASS")
        exact_blobs = compiler_verify.get("exact_blobs")
        if not isinstance(exact_blobs, dict):
            errors.append("COMPILER_VERIFY_EXACT_BLOBS_INVALID")
        else:
            if exact_blobs.get("runtime") != compiler_declared:
                errors.append("COMPILER_VERIFY_RUNTIME_MISMATCH")
            source_declared = (
                (entry.get("source_receipt") or {}).get("git_blob_sha")
                if isinstance(entry.get("source_receipt"), dict)
                else None
            )
            if exact_blobs.get("source_receipt") != source_declared:
                errors.append("COMPILER_VERIFY_SOURCE_MISMATCH")
        if "GLOBAL_R7_ROOT_CLOSURE" not in (compiler_verify.get("not_proved") or []):
            errors.append("COMPILER_VERIFY_GLOBAL_NONCLAIM_MISSING")
    return errors, claim_scope


def _validate_r3(
    entry: dict[str, Any],
    source: dict[str, Any] | None,
    preflight: dict[str, Any] | None,
    compiler_declared: Any,
) -> tuple[list[str], Any]:
    errors = _common_checks(entry, R3_ROOT, R3_LEAVES)
    claim_scope: dict[str, Any] | None = None
    if source is not None:
        if source.get("schema") != R3_SOURCE_SCHEMA:
            errors.append("SOURCE_SCHEMA_INVALID")
        if source.get("status") != "INDEPENDENT_BOUNDED_RENDER_PRESERVATION_PREFLIGHT_PASS__ZERO_TERMINAL_CREDIT":
            errors.append("SOURCE_STATUS_NOT_ADMITTED")
        blobs = source.get("exact_brain_blobs")
        if not isinstance(blobs, dict):
            errors.append("SOURCE_EXACT_BLOBS_INVALID")
        elif blobs.get("canonical/runtime/native_artifact_render_preservation_proof_v1.py") != compiler_declared:
            errors.append("SOURCE_RUNTIME_MISMATCH")
        required_verified = {
            "SOURCE_AND_OUTPUT_PAGE_COUNTS_EQUAL",
            "SOURCE_AND_OUTPUT_PAGE_PIXEL_DIMENSIONS_EQUAL",
            "AT_LEAST_ONE_PAGE_MUST_VISIBLY_CHANGE",
            "CHANGED_PIXELS_AND_BOUNDING_BOX_MUST_REMAIN_WITHIN_FROZEN_LOCALIZATION_BOUNDS",
            "UNCHANGED_WHOLE_OUTPUT_IS_REJECTED",
            "STRUCTURAL_HIDDEN_ORACLE_MUST_PASS_BEFORE_RENDER_ACCEPTANCE",
            "EXACT_BRAIN_BLOBS_VERIFIED_BY_PUBLIC_CAPSULE",
        }
        verified = set(source.get("verified") or [])
        if not required_verified <= verified:
            errors.append("SOURCE_REQUIRED_RENDER_ASSERTIONS_MISSING")
        limitations = set(source.get("limitations") or [])
        required_limits = {
            "BOUNDED_GENERATED_EXPLICIT_LOW_LEVEL_TEXT_EDITS_ONLY",
            "NO_ARBITRARY_SEMANTIC_TARGET_SELECTION",
            "NO_WHOLE_OPEN_ENDED_NATIVE_ARTIFACT_CONTRACT_SCOPE_EQUIVALENCE",
            "NO_TERMINAL_ACCEPTANCE_OR_CAPABILITY_CREDIT",
        }
        if not required_limits <= limitations:
            errors.append("SOURCE_SCOPE_LIMITATIONS_MISSING")
        claim_scope = {
            "kind": R3_KIND,
            "formats": ["docx", "xlsx", "pptx", "pdf"],
            "behavior_id": source.get("behavior_id"),
            "limitations": sorted(limitations),
        }

    if preflight is not None:
        if preflight.get("schema") != R3_PREFLIGHT_SCHEMA:
            errors.append("PREFLIGHT_SCHEMA_INVALID")
        if preflight.get("status") != "INDEPENDENT_PUBLIC_RUNNER_PASS__BOUNDED_RENDER_PRESERVATION_ONLY__ZERO_TERMINAL_AUTHORITY":
            errors.append("PREFLIGHT_STATUS_NOT_ADMITTED")
        if preflight.get("render_oracle") != "canonical/runtime/native_artifact_render_preservation_proof_v1.py":
            errors.append("PREFLIGHT_RENDER_ORACLE_MISMATCH")
        limitation = str(preflight.get("scope_limitation") or "")
        if "NO_ARBITRARY_SEMANTIC_TARGET_SELECTION" not in limitation:
            errors.append("PREFLIGHT_SEMANTIC_SCOPE_LIMIT_MISSING")
        if "NO_WHOLE_CONTRACT_SCOPE_EQUIVALENCE" not in limitation:
            errors.append("PREFLIGHT_WHOLE_CONTRACT_SCOPE_LIMIT_MISSING")
        if preflight.get("execution_authority") is not False:
            errors.append("PREFLIGHT_EXECUTION_AUTHORITY_INVALID")
    return errors, claim_scope


def _validate_r11(
    entry: dict[str, Any],
    source: dict[str, Any] | None,
    governance: dict[str, Any] | None,
    compiler_declared: Any,
) -> tuple[list[str], Any]:
    errors = _common_checks(entry, R11_ROOT, R11_LEAVES)
    claim_scope = None
    if source is not None:
        if source.get("schema") != R11_SOURCE_SCHEMA:
            errors.append("SOURCE_SCHEMA_INVALID")
        if source.get("status") != "PASS__PINNED_EXACT_BYTES__PYCOMPILE__4_OF_4__BOUNDED_POST_IDENTITY_DISCOVERY_REVOCATION__ZERO_GLOBAL_LEAF_CREDIT":
            errors.append("SOURCE_STATUS_NOT_ADMITTED")
        blobs = source.get("exact_blobs")
        if not isinstance(blobs, dict):
            errors.append("SOURCE_EXACT_BLOBS_INVALID")
        elif blobs.get("runtime") != compiler_declared:
            errors.append("SOURCE_RUNTIME_MISMATCH")
        scope = source.get("claim_scope")
        claim_scope = scope
        if not isinstance(scope, dict) or scope.get("kind") != R11_KIND:
            errors.append("SOURCE_CLAIM_SCOPE_INVALID")
        else:
            guarantees = set(scope.get("guarantees") or [])
            required = {
                "POST_EXPOSURE_REPO_SEARCH_DENIED",
                "POST_EXPOSURE_EXACT_FROZEN_BLOB_READ_ALLOWED",
                "TASK_IDENTITY_EXPOSURE_CANNOT_REVERSE",
                "REVOKED_DISCOVERY_CAPABILITY_CANNOT_BE_RESTORED_IN_SAME_LANE",
            }
            if not required <= guarantees:
                errors.append("SOURCE_REQUIRED_FIREWALL_GUARANTEES_MISSING")
            limitations = set(scope.get("limitations") or [])
            if "NO_GLOBAL_R11_LEAF_OR_ROOT_CLOSURE" not in limitations:
                errors.append("SOURCE_GLOBAL_SCOPE_LIMIT_MISSING")
        state = source.get("current_state")
        if not isinstance(state, dict):
            errors.append("SOURCE_CURRENT_STATE_INVALID")
        else:
            for field in ("global_leaf_credit", "global_r11_root_closed", "domain_semantic_closure", "domain_execution_closure"):
                if state.get(field) is not False:
                    errors.append("SOURCE_GLOBAL_OVERCLAIM:" + field)

    if governance is not None:
        if governance.get("schema") != R11_GOVERNANCE_SCHEMA:
            errors.append("FIREWALL_GOVERNANCE_SCHEMA_INVALID")
        if governance.get("status") != "ACTIVE_FAIL_CLOSED__POST_IDENTITY_DISCOVERY_REVOCATION__ZERO_CREDIT":
            errors.append("FIREWALL_GOVERNANCE_STATUS_INVALID")
        if governance.get("runtime") != "canonical/runtime/evaluation_information_firewall_v1.py":
            errors.append("FIREWALL_RUNTIME_PATH_MISMATCH")
        hard_rules = set(governance.get("hard_rules") or [])
        required_rules = {
            "TASK_IDENTITY_EXPOSURE_IS_MONOTONIC_WITHIN_A_LANE",
            "REVOKED_CAPABILITIES_CANNOT_BE_RESTORED_WITHIN_THE_SAME_LANE",
            "UNKNOWN_CAPABILITY_FAILS_CLOSED",
            "NO_CAPABILITY_OR_FAMILY_CREDIT_FROM_FIREWALL_STATE",
        }
        if not required_rules <= hard_rules:
            errors.append("FIREWALL_REQUIRED_RULES_MISSING")
    return errors, claim_scope


def _validate_r10(
    entry: dict[str, Any],
    source: dict[str, Any] | None,
    history: dict[str, Any] | None,
    compiler_declared: Any,
) -> tuple[list[str], Any]:
    errors = _common_checks(entry, R10_ROOT, R10_LEAVES)
    claim_scope = None
    if source is not None:
        if source.get("schema") != R10_SOURCE_SCHEMA:
            errors.append("SOURCE_SCHEMA_INVALID")
        if source.get("status") != "PASS__PINNED_CURRENT_BYTES__PYCOMPILE__23_OF_23__BOUNDED_DECISION_SUFFICIENCY_AND_MINIMUM_INFORMATION_ROUTING__ZERO_GLOBAL_LEAF_CREDIT":
            errors.append("SOURCE_STATUS_NOT_ADMITTED")
        blobs = source.get("exact_blobs")
        if not isinstance(blobs, dict):
            errors.append("SOURCE_EXACT_BLOBS_INVALID")
        elif blobs.get("runtime") != compiler_declared:
            errors.append("SOURCE_RUNTIME_MISMATCH")
        replay = source.get("replay")
        if not isinstance(replay, dict) or replay.get("tests_passed") != 23 or replay.get("tests_failed") != 0:
            errors.append("SOURCE_REPLAY_INVALID")
        scope = source.get("claim_scope")
        claim_scope = scope
        if not isinstance(scope, dict) or scope.get("kind") != R10_KIND:
            errors.append("SOURCE_CLAIM_SCOPE_INVALID")
        else:
            guarantees = set(scope.get("guarantees") or [])
            required = {
                "DECISION_SUFFICIENT_BASELINE_IS_LOSSLESS_IDENTITY_AND_CONTENT_ADDRESSED",
                "NO_EVIDENCE_IS_OMITTED_WITHOUT_A_FUTURE_OMISSION_CERTIFICATE",
                "MINIMUM_INFORMATION_REQUESTS_DEDUPLICATE_EVIDENCE_BLOCKERS",
                "BROAD_ACQUISITION_IS_FORBIDDEN_WITHOUT_MINIMALITY_PROOF",
                "FULL_EMPIRICAL_EVALUATION_REMAINS_LAST",
                "PROVIDERS_CANNOT_MUTATE_VERIFICATION_AUTHORITY",
                "FALSE_PROGRESS_WITH_UNCHANGED_FRONTIER_FAILS_CLOSED",
            }
            if not required <= guarantees:
                errors.append("SOURCE_REQUIRED_DECISION_GUARANTEES_MISSING")
            limitations = set(scope.get("limitations") or [])
            required_limits = {
                "NO_GENERAL_PROFESSIONAL_RISK_POLICY_CLOSURE",
                "NO_NORMATIVE_AGGREGATION_CLOSURE",
                "NO_MODEL_MULTIPLICITY_DECISION_CLOSURE",
                "NO_GLOBAL_R10_LEAF_OR_ROOT_CLOSURE",
            }
            if not required_limits <= limitations:
                errors.append("SOURCE_SCOPE_LIMITATIONS_MISSING")
        state = source.get("current_state")
        if not isinstance(state, dict):
            errors.append("SOURCE_CURRENT_STATE_INVALID")
        else:
            for field in ("global_leaf_credit", "global_r10_root_closed", "domain_semantic_closure", "domain_execution_closure"):
                if state.get(field) is not False:
                    errors.append("SOURCE_GLOBAL_OVERCLAIM:" + field)

    if history is not None:
        if history.get("schema") != R10_HISTORY_SCHEMA:
            errors.append("HISTORY_SCHEMA_INVALID")
        if history.get("status") != "PASS__FOCUSED_18_OF_18__CURRENT_V1_ADJACENT_7_OF_7__PY_COMPILE_PASS":
            errors.append("HISTORY_STATUS_NOT_ADMITTED")
        guarantees = set(history.get("guarantees") or [])
        historical_required = {
            "BUILTIN_DECISION_REDUCTION_IS_LOSSLESS_IDENTITY__NO_UNVERIFIED_OMISSION",
            "FUTURE_COMPRESSION_REQUIRES_OMISSION_CERTIFICATE",
            "EVIDENCE_ACQUISITION_RECEIVES_DEDUPLICATED_MINIMUM_POLICY_CHANGING_INFORMATION_CONTRACT",
            "FULL_EMPIRICAL_EVALUATION_REMAINS_LAST",
            "SYNTHESIS_AND_ACQUISITION_CANNOT_MUTATE_VERIFICATION_AUTHORITY",
        }
        if not historical_required <= guarantees:
            errors.append("HISTORY_REQUIRED_FEATURES_MISSING")
        if "NO_OPEN_WORLD_TERMINAL_CLOSURE_CLAIM" not in set(history.get("nonclaims") or []):
            errors.append("HISTORY_GLOBAL_NONCLAIM_MISSING")
    return errors, claim_scope


def _validate_r6(
    entry: dict[str, Any],
    source: dict[str, Any] | None,
    governance: dict[str, Any] | None,
    compiler_declared: Any,
) -> tuple[list[str], Any]:
    errors = _common_checks(entry, R6_ROOT, R6_LEAVES)
    claim_scope = None
    if source is not None:
        if source.get("schema") != R6_SOURCE_SCHEMA:
            errors.append("SOURCE_SCHEMA_INVALID")
        if source.get("status") != "PASS__PINNED_EXACT_BYTES__PYCOMPILE__5_OF_5__MANIFEST_STATUS_SELF_CERTIFICATION_KILLED__ZERO_TERMINAL_CREDIT":
            errors.append("SOURCE_STATUS_NOT_ADMITTED")
        blobs = source.get("exact_blobs")
        if not isinstance(blobs, dict):
            errors.append("SOURCE_EXACT_BLOBS_INVALID")
        elif blobs.get("runtime") != compiler_declared:
            errors.append("SOURCE_RUNTIME_MISMATCH")
        proved = set(source.get("proved") or [])
        required = {
            "MANIFEST_VERIFIED_STATUS_HAS_ZERO_PROMOTION_AUTHORITY",
            "LEAF_CLOSURE_REQUIRES_SCOPE_MATCHED_CONTENT_ADDRESSED_RECEIPT",
            "RECEIPT_MUST_BIND_EXACT_ROOT_CONTRACT_AND_EXACT_LEAF_ACCEPTANCE",
            "RECEIPT_VERIFICATION_BASIS_MUST_BE_CONTENT_ADDRESSED_AND_CURRENT",
            "UNKNOWN_REGISTRY_LEAF_IDS_FAIL_STRUCTURE",
        }
        if not required <= proved:
            errors.append("SOURCE_REQUIRED_EVIDENCE_ADMISSION_PROPERTIES_MISSING")
        state = source.get("current_state")
        if not isinstance(state, dict):
            errors.append("SOURCE_CURRENT_STATE_INVALID")
        else:
            if state.get("verified_leaf_count") != 0:
                errors.append("SOURCE_UNEXPECTED_GLOBAL_LEAF_CREDIT")
            if state.get("domain_semantic_closure") is not False:
                errors.append("SOURCE_DOMAIN_SEMANTIC_OVERCLAIM")
            if state.get("domain_execution_closure") is not False:
                errors.append("SOURCE_DOMAIN_EXECUTION_OVERCLAIM")
        claim_scope = {
            "kind": R6_KIND,
            "guarantees": sorted(required),
            "limitations": [
                "NO_GENERAL_EVIDENCE_TRUTH_CLOSURE",
                "NO_GENERAL_EVIDENCE_INDEPENDENCE_CLOSURE",
                "NO_GENERAL_UNCERTAINTY_SEMANTICS_CLOSURE",
                "NO_GLOBAL_R6_LEAF_OR_ROOT_CLOSURE",
            ],
        }

    if governance is not None:
        if governance.get("schema") != R6_REGISTRY_SCHEMA:
            errors.append("EVIDENCE_REGISTRY_SCHEMA_INVALID")
        if governance.get("receipt_schema") != "PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_VERIFICATION_RECEIPT_V1":
            errors.append("EVIDENCE_REGISTRY_RECEIPT_SCHEMA_INVALID")
        law = str(governance.get("admission_law") or "")
        if "MANIFEST_STATUS_STRINGS_HAVE_ZERO_PROMOTION_AUTHORITY" not in law:
            errors.append("EVIDENCE_REGISTRY_STATUS_NONAUTHORITY_LAW_MISSING")
        if governance.get("terminal_authority") is not False:
            errors.append("EVIDENCE_REGISTRY_TERMINAL_AUTHORITY_INVALID")
    return errors, claim_scope


def validate_entry(entry: dict[str, Any], *, repo_root: Path = ROOT) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(entry, dict):
        return {"admitted": False, "errors": ["ENTRY_INVALID"]}
    scope_id = entry.get("scope_id")
    if not isinstance(scope_id, str) or not scope_id:
        errors.append("SCOPE_ID_INVALID")

    source, e = _read_bound(repo_root, entry.get("source_receipt"), "SOURCE_RECEIPT")
    errors.extend(e)
    verifier, e = _read_bound(repo_root, entry.get("compiler_verification"), "COMPILER_VERIFICATION")
    errors.extend(e)

    compiler_binding = entry.get("reusable_compiler")
    compiler_path = _resolve(
        repo_root,
        compiler_binding.get("path") if isinstance(compiler_binding, dict) else None,
    )
    compiler_declared = (
        compiler_binding.get("git_blob_sha") if isinstance(compiler_binding, dict) else None
    )
    if compiler_path is None:
        errors.append("COMPILER_PATH_INVALID")
    elif not compiler_path.exists():
        errors.append("COMPILER_MISSING")
    elif git_blob_sha(compiler_path) != compiler_declared:
        errors.append("COMPILER_STALE")

    kind = entry.get("claim_kind")
    if kind == R7_KIND:
        handler_errors, claim_scope = _validate_r7(entry, source, verifier, compiler_declared)
    elif kind == R3_KIND:
        handler_errors, claim_scope = _validate_r3(entry, source, verifier, compiler_declared)
    elif kind == R11_KIND:
        handler_errors, claim_scope = _validate_r11(entry, source, verifier, compiler_declared)
    elif kind == R10_KIND:
        handler_errors, claim_scope = _validate_r10(entry, source, verifier, compiler_declared)
    elif kind == R6_KIND:
        handler_errors, claim_scope = _validate_r6(entry, source, verifier, compiler_declared)
    else:
        handler_errors, claim_scope = ["CLAIM_KIND_UNSUPPORTED"], None
    errors.extend(handler_errors)

    leaf_ids = entry.get("contributes_to_leaf_ids")
    return {
        "scope_id": scope_id,
        "root_id": entry.get("root_id"),
        "claim_kind": kind,
        "admitted": not errors,
        "errors": sorted(set(errors)),
        "claim_scope": claim_scope,
        "contributes_to_leaf_ids": sorted(leaf_ids) if isinstance(leaf_ids, list) else [],
        "global_leaf_credit": False,
        "global_root_credit": False,
        "semantic_leaf_credit": False,
        "execution_leaf_credit": False,
        "terminal_credit_delta": 0,
    }


def evaluate(*, registry_path: Path = REGISTRY, repo_root: Path = ROOT) -> dict[str, Any]:
    registry = _load(registry_path)
    structural_errors: list[str] = []
    if registry.get("schema") != REGISTRY_SCHEMA:
        structural_errors.append("REGISTRY_SCHEMA_INVALID")
    entries = registry.get("entries")
    if not isinstance(entries, list):
        entries = []
        structural_errors.append("REGISTRY_ENTRIES_INVALID")

    results = [
        validate_entry(entry, repo_root=repo_root)
        for entry in entries
        if isinstance(entry, dict)
    ]
    scope_ids = [x.get("scope_id") for x in results]
    if len(scope_ids) != len(set(scope_ids)):
        structural_errors.append("DUPLICATE_SCOPE_ID")

    admitted = [x for x in results if x.get("admitted") is True]
    rejected = [x for x in results if x.get("admitted") is not True]
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__SCOPED_CAPABILITIES_ADMITTED_WITH_ZERO_GLOBAL_LEAF_CREDIT"
            if not structural_errors and not rejected
            else "OPEN__SCOPED_EVIDENCE_REGISTRY_ERRORS"
        ),
        "pass": not structural_errors and not rejected,
        "structural_errors": sorted(set(structural_errors)),
        "admitted_scope_count": len(admitted),
        "rejected_scope_count": len(rejected),
        "admitted_scopes": admitted,
        "rejected_scopes": rejected,
        "global_leaf_closure": False,
        "global_root_closure": False,
        "domain_semantic_closure": False,
        "domain_execution_closure": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
