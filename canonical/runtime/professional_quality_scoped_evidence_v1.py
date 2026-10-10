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

R11_SEMANTIC_KIND = "CLEAN_EVALUATION_LANE_POST_IDENTITY_REVOCATION_SEMANTICS"
R11_SEMANTIC_LEAVES = {"PQ::R11_ADAPTIVE_INTEGRITY_SECURITY::SEMANTIC"}
R11_SEMANTIC_SOURCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R11_FIREWALL_SEMANTIC_VERIFY_V1"
R11_SEMANTIC_SCOPE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R11_FIREWALL_SEMANTIC_SCOPE_V1"

R10_KIND = "LOSSLESS_DECISION_SUFFICIENT_GAP_REPRESENTATION_AND_MINIMUM_POLICY_CHANGING_INFORMATION_ROUTING"
R10_ROOT = "R10_ANALYSIS_DECISION"
R10_LEAVES = {"PQ::R10_ANALYSIS_DECISION::EXECUTION"}
R10_SOURCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_DECISION_SUFFICIENCY_SCOPED_VERIFY_V1"
R10_HISTORY_SCHEMA = "PROJECT_BRAIN_ONE_SHOT_DECISION_SUFFICIENT_GATE_VERIFY_20261009_V2"

R6_KIND = "CONTENT_ADDRESSED_SCOPE_MATCHED_LEAF_EVIDENCE_ADMISSION_WITH_STATUS_NONAUTHORITY"
R6_ROOT = "R6_EVIDENCE_GROUNDING_DEPENDENCE"
R6_LEAVES = {
    "PQ::R6_EVIDENCE_GROUNDING_DEPENDENCE::SEMANTIC",
    "PQ::R6_EVIDENCE_GROUNDING_DEPENDENCE::EXECUTION",
}
R6_SOURCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_BINDER_V2_VERIFY_V1"
R6_REGISTRY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_V1"

R4_KIND = "CONTENT_ADDRESSED_TYPED_MECHANICAL_ARTIFACT_MEASUREMENT_AND_ACCEPTANCE"
R4_ROOT = "R4_MEASUREMENT_CONSTRUCT"
R4_LEAVES = {"PQ::R4_MEASUREMENT_CONSTRUCT::EXECUTION"}
R4_SOURCE_SCHEMA = "PROJECT_BRAIN_ARTIFACT_MEASUREMENT_VERIFY_V1"
R4_GOVERNANCE_SCHEMA = "PROJECT_BRAIN_ARTIFACT_MEASUREMENT_BINDING_V1"
R4_MEASUREMENT_RUNTIME = "canonical/runtime/content_addressed_artifact_measurement_v1.py"

R5_KIND = "CONDITIONAL_EVALUATOR_UNCERTAINTY_ROBUST_MARGIN_CERTIFICATE"
R5_ROOT = "R5_EVALUATOR_REFERENCE"
R5_LEAVES = {"PQ::R5_EVALUATOR_REFERENCE::EXECUTION"}
R5_SOURCE_SCHEMA = "PROJECT_BRAIN_GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_SPRITE_VERIFICATION_V1"
R5_GOVERNANCE_SCHEMA = "PROJECT_BRAIN_GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_V1"

R1_KIND = "CONTENT_ADDRESSED_BEHAVIORAL_CONTRACT_STRUCTURAL_COMPLETENESS_GATE"
R1_ROOT = "R1_TARGET_SPECIFICATION"
R1_LEAVES = {"PQ::R1_TARGET_SPECIFICATION::EXECUTION"}
R1_SOURCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R1_STRUCTURAL_TARGET_VERIFY_V1"
R1_GOVERNANCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R1_STRUCTURAL_TARGET_SCOPE_V1"

R1_SEMANTIC_KIND = "EXACT_PARAMETERIZED_PROFESSIONAL_ARTIFACT_TARGET_SEMANTICS"
R1_SEMANTIC_LEAVES = {"PQ::R1_TARGET_SPECIFICATION::SEMANTIC"}
R1_SEMANTIC_SOURCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R1_TARGET_SEMANTIC_VERIFY_V1"
R1_SEMANTIC_SCOPE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R1_TARGET_SEMANTIC_SCOPE_V1"

R2_KIND = "FINITE_SCOPE_COMPLETE_COMMON_POLICY_OR_MINIMUM_TRUTHFUL_DISCRIMINATOR_SEARCH"
R2_ROOT = "R2_CANDIDATE_SEARCH"
R2_LEAVES = {"PQ::R2_CANDIDATE_SEARCH::EXECUTION"}
R2_SOURCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R2_SCOPE_COMPLETE_SEARCH_VERIFY_V1"
R2_GOVERNANCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R2_SCOPE_COMPLETE_SEARCH_SCOPE_V1"

R9_KIND = "FROZEN_POPULATION_CONSERVATIVE_CENSORING_AND_EARLY_FAILURE_ACCOUNTING"
R9_ROOT = "R9_TEMPORAL_DEPLOYMENT"
R9_LEAVES = {"PQ::R9_TEMPORAL_DEPLOYMENT::EXECUTION"}
R9_SOURCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R9_CONSERVATIVE_CENSORING_VERIFY_V1"
R9_GOVERNANCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R9_CONSERVATIVE_CENSORING_SCOPE_V1"

R8_KIND = "FROZEN_512_CASE_PRE_BEACON_DELEGATION_POPULATION_BINDING"
R8_ROOT = "R8_POPULATION_CONTEXT_OPERATOR"
R8_LEAVES = {"PQ::R8_POPULATION_CONTEXT_OPERATOR::EXECUTION"}
R8_SOURCE_SCHEMA = "PROJECT_BRAIN_DELEGATION_TERMINAL_POPULATION_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1"
R8_SCOPE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R8_POPULATION_CONTEXT_SCOPE_V1"

R12_KIND = "FAIL_CLOSED_ASSURANCE_GRAPH_META_COMPOSITION_AND_ORDER_INDEPENDENT_DEFEATER_ROUTING"
R12_ROOT = "R12_META_COMPOSITION_CLOSURE"
R12_LEAVES = {
    "PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC",
    "PQ::R12_META_COMPOSITION_CLOSURE::EXECUTION",
}
R12_SOURCE_SCHEMA = "PROJECT_BRAIN_UVCK_V2_CURRENT_GENERATION_INDEPENDENT_REPLAY_VERIFY_V1"
R12_VERIFY_SCHEMA = "PROJECT_BRAIN_UVCK_V2_DEFEATER_ORDER_VERIFY_V1"
R12_SCOPE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R12_META_COMPOSITION_SCOPE_V1"


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


def _validate_r11_semantic(
    entry: dict[str, Any],
    source: dict[str, Any] | None,
    verifier: dict[str, Any] | None,
    compiler_declared: Any,
    repo_root: Path,
) -> tuple[list[str], Any]:
    errors = _common_checks(entry, R11_ROOT, R11_SEMANTIC_LEAVES)
    claim_scope = None
    scope, e = _read_bound(repo_root, entry.get("scope_governance"), "SCOPE_GOVERNANCE")
    errors.extend(e)

    expected_guarantees = {
        "TASK_IDENTITY_EXPOSURE_IS_MONOTONIC_WITHIN_A_LANE",
        "POST_EXPOSURE_BROAD_DISCOVERY_CAPABILITIES_ARE_REVOKED",
        "REVOKED_CAPABILITIES_CANNOT_BE_RESTORED_WITHIN_THE_SAME_LANE",
        "DEACTIVATING_CLEAN_MODE_DOES_NOT_REENABLE_DISCOVERY_IN_THE_SAME_LANE",
        "UNKNOWN_CAPABILITY_DENIES_FAIL_CLOSED",
        "ALLOW_AND_REVOKE_CAPABILITY_CLASSES_ARE_DISJOINT",
    }
    expected_limits = {
        "NO_GENERAL_PROMPT_INJECTION_CLOSURE",
        "NO_GENERAL_GOODHART_CLOSURE",
        "NO_HOLDOUT_LIFECYCLE_CLOSURE",
        "NO_GLOBAL_R11_SEMANTIC_LEAF_CLOSURE",
        "NO_GLOBAL_R11_ROOT_CLOSURE",
    }

    if source is not None:
        if source.get("schema") != R11_SEMANTIC_SOURCE_SCHEMA:
            errors.append("SOURCE_SCHEMA_INVALID")
        if source.get("status") != "PASS__PINNED_EXACT_BYTES__PYCOMPILE__6_OF_6__BOUNDED_R11_FIREWALL_SEMANTICS__ZERO_GLOBAL_LEAF_CREDIT":
            errors.append("SOURCE_STATUS_NOT_ADMITTED")
        exact = source.get("exact_blobs")
        if not isinstance(exact, dict) or exact.get("runtime") != compiler_declared:
            errors.append("SOURCE_RUNTIME_MISMATCH")
        replay = source.get("replay")
        if not isinstance(replay, dict) or replay.get("tests_run") != 6 or replay.get("tests_passed") != 6 or replay.get("tests_failed") != 0:
            errors.append("SOURCE_REPLAY_INVALID")
        cscope = source.get("claim_scope")
        claim_scope = cscope
        if not isinstance(cscope, dict) or cscope.get("kind") != R11_SEMANTIC_KIND:
            errors.append("SOURCE_CLAIM_SCOPE_INVALID")
        else:
            if not expected_guarantees <= set(cscope.get("guarantees") or []):
                errors.append("SOURCE_REQUIRED_GUARANTEES_MISSING")
            if not expected_limits <= set(cscope.get("limitations") or []):
                errors.append("SOURCE_REQUIRED_LIMITATIONS_MISSING")
        if source.get("semantic_leaf_credit") is not False:
            errors.append("SOURCE_SEMANTIC_LEAF_CREDIT_FORBIDDEN")
        if source.get("global_leaf_closure") is not False:
            errors.append("SOURCE_GLOBAL_LEAF_CLOSURE_FORBIDDEN")

    if verifier is not None:
        if verifier.get("schema") != R11_SEMANTIC_SOURCE_SCHEMA:
            errors.append("VERIFIER_SCHEMA_INVALID")
        exact = verifier.get("exact_blobs")
        if not isinstance(exact, dict) or exact.get("runtime") != compiler_declared:
            errors.append("VERIFIER_RUNTIME_MISMATCH")

    if scope is not None:
        if scope.get("schema") != R11_SEMANTIC_SCOPE_SCHEMA:
            errors.append("SCOPE_SCHEMA_INVALID")
        if scope.get("status") != "ACTIVE_SCOPED_CLEAN_EVALUATION_LANE_POST_IDENTITY_REVOCATION_SEMANTICS__6_OF_6_INDEPENDENT_REPLAY__ZERO_GLOBAL_LEAF_CREDIT":
            errors.append("SCOPE_STATUS_INVALID")
        components = scope.get("exact_components")
        if not isinstance(components, dict):
            errors.append("SCOPE_COMPONENTS_INVALID")
        else:
            runtime = components.get("runtime")
            verification = components.get("verification")
            firewall = components.get("firewall_governance")
            if not isinstance(runtime, dict) or runtime.get("git_blob_sha") != compiler_declared:
                errors.append("SCOPE_RUNTIME_MISMATCH")
            source_declared = (entry.get("source_receipt") or {}).get("git_blob_sha") if isinstance(entry.get("source_receipt"), dict) else None
            if not isinstance(verification, dict) or verification.get("git_blob_sha") != source_declared:
                errors.append("SCOPE_VERIFICATION_MISMATCH")
            source_exact = source.get("exact_blobs") if isinstance(source, dict) else None
            if not isinstance(firewall, dict) or not isinstance(source_exact, dict) or firewall.get("git_blob_sha") != source_exact.get("governance"):
                errors.append("SCOPE_FIREWALL_GOVERNANCE_MISMATCH")
        if not expected_guarantees <= set(scope.get("guarantees") or []):
            errors.append("SCOPE_REQUIRED_GUARANTEES_MISSING")
        if not expected_limits <= set(scope.get("limitations") or []):
            errors.append("SCOPE_REQUIRED_LIMITATIONS_MISSING")
        if claim_scope is None:
            claim_scope = {
                "kind": R11_SEMANTIC_KIND,
                "guarantees": sorted(expected_guarantees),
                "limitations": sorted(expected_limits),
            }
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



def _validate_r4(
    entry: dict[str, Any],
    source: dict[str, Any] | None,
    governance: dict[str, Any] | None,
    compiler_declared: Any,
    repo_root: Path,
) -> tuple[list[str], Any]:
    errors = _common_checks(entry, R4_ROOT, R4_LEAVES)
    claim_scope = None
    measurement_binding = entry.get("measurement_runtime")
    measurement_path = _resolve(
        repo_root,
        measurement_binding.get("path") if isinstance(measurement_binding, dict) else None,
    )
    measurement_declared = (
        measurement_binding.get("git_blob_sha")
        if isinstance(measurement_binding, dict)
        else None
    )
    if measurement_path is None:
        errors.append("MEASUREMENT_RUNTIME_PATH_INVALID")
    elif not measurement_path.exists():
        errors.append("MEASUREMENT_RUNTIME_MISSING")
    elif git_blob_sha(measurement_path) != measurement_declared:
        errors.append("MEASUREMENT_RUNTIME_STALE")

    if source is not None:
        if source.get("schema") != R4_SOURCE_SCHEMA:
            errors.append("SOURCE_SCHEMA_INVALID")
        if source.get("status") != "INDEPENDENT_SPRITE_PASS__8_OF_8__ZERO_CREDIT":
            errors.append("SOURCE_STATUS_NOT_ADMITTED")
        result = source.get("result")
        if not isinstance(result, dict) or result.get("passed") != 8 or result.get("total") != 8:
            errors.append("SOURCE_REPLAY_INVALID")
        blobs = source.get("blobs")
        if not isinstance(blobs, dict):
            errors.append("SOURCE_EXACT_BLOBS_INVALID")
        else:
            if blobs.get("measured_acceptance") != compiler_declared:
                errors.append("SOURCE_MEASURED_ACCEPTANCE_RUNTIME_MISMATCH")
            if blobs.get("measurement") != measurement_declared:
                errors.append("SOURCE_MEASUREMENT_RUNTIME_MISMATCH")
        required_verified = {
            "ARTIFACT_SHA_AND_MEASUREMENTS_DERIVED_FROM_REAL_BYTES",
            "XLSX_DOCX_PPTX_MECHANICAL_FACTS_MEASURED",
            "FAILED_XLSX_PROPERTY_FALSIFIES_ACCEPTANCE",
            "PATH_ESCAPE_FAILS_CLOSED",
            "FIELD_TYPE_MISMATCH_FAILS_CLOSED",
        }
        if not required_verified <= set(source.get("verified") or []):
            errors.append("SOURCE_REQUIRED_MEASUREMENT_ASSERTIONS_MISSING")

    if governance is not None:
        if governance.get("schema") != R4_GOVERNANCE_SCHEMA:
            errors.append("MEASUREMENT_GOVERNANCE_SCHEMA_INVALID")
        if governance.get("status") != "CANDIDATE_MEASUREMENT_BRIDGE__INDEPENDENT_REPLAY_PASS__ZERO_TERMINAL_CREDIT":
            errors.append("MEASUREMENT_GOVERNANCE_STATUS_INVALID")
        repair = governance.get("repair")
        if not isinstance(repair, dict):
            errors.append("MEASUREMENT_GOVERNANCE_REPAIR_INVALID")
        else:
            if repair.get("measurement_runtime") != R4_MEASUREMENT_RUNTIME:
                errors.append("MEASUREMENT_GOVERNANCE_RUNTIME_PATH_MISMATCH")
            if repair.get("measured_acceptance_runtime") != "canonical/runtime/measured_typed_acceptance_program_v1.py":
                errors.append("MEASUREMENT_GOVERNANCE_ACCEPTANCE_PATH_MISMATCH")
            supported = set(repair.get("supported_v1") or [])
            required_kinds = {
                "FILE_BASENAME", "FILE_SUFFIX", "FILE_SIZE_BYTES",
                "OOXML_MEMBER_EXISTS", "XLSX_SHEET_EXISTS", "XLSX_SHEET_COUNT",
                "DOCX_TEXT_CONTAINS", "DOCX_PARAGRAPH_COUNT", "DOCX_TABLE_COUNT",
                "PPTX_SLIDE_COUNT", "PPTX_TEXT_CONTAINS",
            }
            if not required_kinds <= supported:
                errors.append("MEASUREMENT_GOVERNANCE_SUPPORTED_KINDS_MISSING")
        nonclaims = set(governance.get("hard_nonclaims") or [])
        required_nonclaims = {
            "NO_CLAIM_FIELD_TO_RUBRIC_SEMANTIC_ALIGNMENT_IS_AUTOMATIC",
            "NO_CLAIM_HOLISTIC_OR_VISUAL_QUALITY_IS_MEASURED",
            "NO_TERMINAL_CREDIT",
        }
        if not required_nonclaims <= nonclaims:
            errors.append("MEASUREMENT_GOVERNANCE_SCOPE_LIMITATIONS_MISSING")
        claim_scope = {
            "kind": R4_KIND,
            "measurement_kinds": sorted((governance.get("repair") or {}).get("supported_v1") or []),
            "guarantees": [
                "MECHANICAL_VALUES_DERIVED_FROM_CONTENT_ADDRESSED_ARTIFACT_BYTES",
                "MEASURED_FIELD_SET_AND_TYPES_MUST_MATCH_TYPED_ACCEPTANCE_PROGRAM",
                "PATH_ESCAPE_AND_FIELD_TYPE_MISMATCH_FAIL_CLOSED",
            ],
            "limitations": [
                "NO_AUTOMATIC_RUBRIC_OR_CONSTRUCT_SEMANTIC_ALIGNMENT",
                "NO_HOLISTIC_OR_VISUAL_QUALITY_MEASUREMENT",
                "NO_GLOBAL_R4_LEAF_OR_ROOT_CLOSURE",
            ],
        }
    return errors, claim_scope


def _validate_r5(
    entry: dict[str, Any],
    source: dict[str, Any] | None,
    governance: dict[str, Any] | None,
    compiler_declared: Any,
) -> tuple[list[str], Any]:
    errors = _common_checks(entry, R5_ROOT, R5_LEAVES)
    claim_scope = None
    if source is not None:
        if source.get("schema") != R5_SOURCE_SCHEMA:
            errors.append("SOURCE_SCHEMA_INVALID")
        if source.get("status") != "INDEPENDENT_SPRITE_EXACT_BLOB_REPLAY_PASS__11_OF_11__SEMANTIC_DECOMPOSITION_UNVERIFIED__ZERO_CREDIT":
            errors.append("SOURCE_STATUS_NOT_ADMITTED")
        subject = source.get("subject")
        runtime = subject.get("runtime") if isinstance(subject, dict) else None
        if not isinstance(runtime, dict) or runtime.get("git_blob_sha") != compiler_declared:
            errors.append("SOURCE_RUNTIME_MISMATCH")
        replay = source.get("replay")
        if not isinstance(replay, dict) or replay.get("tests_passed") != 11 or replay.get("tests_total") != 11 or replay.get("failures") != []:
            errors.append("SOURCE_REPLAY_INVALID")
        required_mechanics = {
            "POSITIVE_ROBUST_MARGIN_CERTIFICATE_PASSES",
            "UNPROVED_DECOMPOSITION_FAILS_CLOSED",
            "PUBLIC_RUBRIC_ONLY_SEMANTIC_CLASS_IS_FIREWALLED",
            "NONINDEPENDENT_DECOMPOSITION_RECEIPT_FAILS_CLOSED",
            "NONZERO_MASS_DIFFERENCE_VECTOR_FAILS_CLOSED",
            "NONORTHOGONAL_LINEALITY_FAILS_EVEN_WITH_LARGE_NOMINAL_MARGIN",
            "BOUNDED_UNCERTAINTY_CAN_BE_ABSORBED_BY_SUFFICIENT_CERTIFIED_MARGIN",
            "EXCESS_BOUNDED_UNCERTAINTY_FAILS",
            "DIMENSION_MISMATCH_FAILS_CLOSED",
        }
        if not required_mechanics <= set(source.get("verified_mechanics") or []):
            errors.append("SOURCE_REQUIRED_EVALUATOR_MECHANICS_MISSING")
        boundary = " ".join(source.get("verification_boundary") or [])
        if "DOES_NOT_PROVE_THE_TRUE_CURRENT_GDPVAL_OWNER_EVALUATOR" not in boundary:
            errors.append("SOURCE_SEMANTIC_DECOMPOSITION_LIMIT_MISSING")
        if "NO_GDPVAL_ACCEPTANCE_FAMILY_CAPABILITY_OWNERSHIP_OR_TERMINAL_CREDIT" not in boundary:
            errors.append("SOURCE_GLOBAL_SCOPE_LIMIT_MISSING")

    if governance is not None:
        if governance.get("schema") != R5_GOVERNANCE_SCHEMA:
            errors.append("EVALUATOR_GOVERNANCE_SCHEMA_INVALID")
        if governance.get("status") != "CANDIDATE_CONDITIONAL_THEOREM__ARITHMETIC_ONLY__ZERO_GDPVAL_AND_TERMINAL_CREDIT":
            errors.append("EVALUATOR_GOVERNANCE_STATUS_INVALID")
        runtime = governance.get("runtime")
        if not isinstance(runtime, dict) or runtime.get("path") != "canonical/runtime/gdpval_hybrid_evaluator_uncertainty_v1.py":
            errors.append("EVALUATOR_GOVERNANCE_RUNTIME_PATH_MISMATCH")
        elif runtime.get("promotion_authority") is not False:
            errors.append("EVALUATOR_GOVERNANCE_PROMOTION_AUTHORITY_INVALID")
        reality = governance.get("current_reality")
        if not isinstance(reality, dict):
            errors.append("EVALUATOR_CURRENT_REALITY_INVALID")
        else:
            for field in (
                "sound_complete_gdpval_owner_decomposition_bound",
                "current_owner_pairwise_relation_bound",
                "complete_opus55_220_evaluator_facing_laws_bound",
                "gdpval_closed",
            ):
                if reality.get(field) is not False:
                    errors.append("EVALUATOR_GLOBAL_OVERCLAIM:" + field)
        firewall = governance.get("soundness_firewall")
        if not isinstance(firewall, dict):
            errors.append("EVALUATOR_SOUNDNESS_FIREWALL_INVALID")
        else:
            allowed = set(firewall.get("admissible_decomposition_proof_classes") or [])
            required_allowed = {
                "AUTHENTIC_CURRENT_OWNER_SEMANTICS",
                "EXTENSIONALLY_EQUIVALENT_CURRENT_PREFERENCE_RELATION",
                "INDEPENDENTLY_VERIFIED_RESTRICTED_OWNER_CLASS",
                "EVALUATOR_INDEPENDENT_SCOPE_COMPLETE_BOUND",
            }
            if not required_allowed <= allowed:
                errors.append("EVALUATOR_ALLOWED_PROOF_CLASSES_MISSING")
            forbidden = set(firewall.get("forbidden_as_semantic_containment_proof") or [])
            if "PUBLIC_RUBRIC_ONLY" not in forbidden or "UNVERIFIED_RECONSTRUCTED_GRADER" not in forbidden:
                errors.append("EVALUATOR_FORBIDDEN_PROOF_CLASSES_MISSING")
        claim_scope = {
            "kind": R5_KIND,
            "guarantees": [
                "ROBUST_MARGIN_CHECKED_WITH_EXACT_RATIONAL_ARITHMETIC",
                "UNPROVED_OR_NONINDEPENDENT_DECOMPOSITION_FAILS_CLOSED",
                "ARBITRARY_LINEALITY_REQUIRES_EXACT_ORTHOGONALITY",
                "BOUNDED_UNCERTAINTY_MUST_FIT_CERTIFIED_MARGIN",
            ],
            "limitations": [
                "NO_PROOF_THE_TRUE_CURRENT_OWNER_EVALUATOR_IS_IN_THE_DECOMPOSITION",
                "NO_PUBLIC_RUBRIC_TO_OWNER_SEMANTIC_PROMOTION",
                "NO_GLOBAL_R5_LEAF_OR_ROOT_CLOSURE",
            ],
        }
    return errors, claim_scope


def _validate_r1_semantic(
    entry: dict[str, Any],
    source: dict[str, Any] | None,
    verifier: dict[str, Any] | None,
    compiler_declared: Any,
    repo_root: Path,
) -> tuple[list[str], Any]:
    errors = _common_checks(entry, R1_ROOT, R1_SEMANTIC_LEAVES)
    claim_scope = None
    scope, e = _read_bound(repo_root, entry.get("scope_governance"), "SCOPE_GOVERNANCE")
    errors.extend(e)

    expected_guarantees = {
        "OBJECTIVE_AUDIENCE_EVIDENCE_ARTIFACT_TYPE_CONSTRAINTS_AND_CURRENT_DRAFT_ARE_EXPLICIT_RUNTIME_PARAMETERS",
        "SUCCESS_FAILURE_TARGET_CONSTRUCT_SCOPE_AND_EVIDENCE_BOUNDARY_ARE_BOUND_TO_EXACT_CONTRACT_FIELDS",
        "CONTRACT_TARGET_DRIFT_FAILS_CLOSED_BY_CONTENT_DIGEST",
        "UNIQUE_OPTIMUM_IS_NOT_INFERRED_FROM_NONUNIQUE_SUCCESS_SEMANTICS",
        "UNRESOLVED_RUNTIME_TASK_AMBIGUITY_REMAINS_OPEN",
    }
    expected_limits = {
        "NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS",
        "NO_SOURCE_EXTRACTION_COMPLETENESS",
        "NO_UNIQUE_BEST_PLAN",
        "NO_GLOBAL_R1_SEMANTIC_LEAF_CLOSURE",
        "NO_GLOBAL_R1_ROOT_CLOSURE",
    }

    if source is not None:
        if source.get("schema") != R1_SEMANTIC_SOURCE_SCHEMA:
            errors.append("SOURCE_SCHEMA_INVALID")
        if source.get("status") != "PASS__PINNED_EXACT_BYTES__PYCOMPILE__5_OF_5__BOUNDED_R1_TARGET_SEMANTICS__ZERO_GLOBAL_LEAF_CREDIT":
            errors.append("SOURCE_STATUS_NOT_ADMITTED")
        blobs = source.get("exact_blobs")
        if not isinstance(blobs, dict) or blobs.get("runtime") != compiler_declared:
            errors.append("SOURCE_RUNTIME_MISMATCH")
        replay = source.get("replay")
        if not isinstance(replay, dict) or replay.get("tests_run") != 5 or replay.get("tests_passed") != 5 or replay.get("tests_failed") != 0:
            errors.append("SOURCE_REPLAY_INVALID")
        cscope = source.get("claim_scope")
        claim_scope = cscope
        if not isinstance(cscope, dict) or cscope.get("kind") != R1_SEMANTIC_KIND:
            errors.append("SOURCE_CLAIM_SCOPE_INVALID")
        else:
            if cscope.get("behavior_id") != "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":
                errors.append("SOURCE_BEHAVIOR_ID_INVALID")
            if not expected_guarantees <= set(cscope.get("guarantees") or []):
                errors.append("SOURCE_REQUIRED_GUARANTEES_MISSING")
            if not expected_limits <= set(cscope.get("limitations") or []):
                errors.append("SOURCE_REQUIRED_LIMITATIONS_MISSING")
        if source.get("semantic_leaf_credit") is not False:
            errors.append("SOURCE_SEMANTIC_LEAF_CREDIT_FORBIDDEN")
        if source.get("global_leaf_closure") is not False:
            errors.append("SOURCE_GLOBAL_LEAF_CLOSURE_FORBIDDEN")

    if verifier is not None:
        if verifier.get("schema") != R1_SEMANTIC_SOURCE_SCHEMA:
            errors.append("VERIFIER_SCHEMA_INVALID")
        exact = verifier.get("exact_blobs")
        if not isinstance(exact, dict) or exact.get("runtime") != compiler_declared:
            errors.append("VERIFIER_RUNTIME_MISMATCH")

    if scope is not None:
        if scope.get("schema") != R1_SEMANTIC_SCOPE_SCHEMA:
            errors.append("SCOPE_SCHEMA_INVALID")
        if scope.get("status") != "ACTIVE_SCOPED_EXACT_PARAMETERIZED_PROFESSIONAL_ARTIFACT_TARGET_SEMANTICS__5_OF_5_INDEPENDENT_REPLAY__ZERO_GLOBAL_LEAF_CREDIT":
            errors.append("SCOPE_STATUS_INVALID")
        if scope.get("behavior_id") != "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":
            errors.append("SCOPE_BEHAVIOR_ID_INVALID")
        components = scope.get("exact_components")
        if not isinstance(components, dict):
            errors.append("SCOPE_COMPONENTS_INVALID")
        else:
            runtime = components.get("runtime")
            verification = components.get("verification")
            if not isinstance(runtime, dict) or runtime.get("git_blob_sha") != compiler_declared:
                errors.append("SCOPE_RUNTIME_MISMATCH")
            source_declared = (entry.get("source_receipt") or {}).get("git_blob_sha") if isinstance(entry.get("source_receipt"), dict) else None
            if not isinstance(verification, dict) or verification.get("git_blob_sha") != source_declared:
                errors.append("SCOPE_VERIFICATION_MISMATCH")
        if not expected_guarantees <= set(scope.get("guarantees") or []):
            errors.append("SCOPE_REQUIRED_GUARANTEES_MISSING")
        if not expected_limits <= set(scope.get("limitations") or []):
            errors.append("SCOPE_REQUIRED_LIMITATIONS_MISSING")
        if claim_scope is None:
            claim_scope = {
                "kind": R1_SEMANTIC_KIND,
                "behavior_id": scope.get("behavior_id"),
                "guarantees": sorted(expected_guarantees),
                "limitations": sorted(expected_limits),
            }
    return errors, claim_scope


def _validate_r1(
    entry: dict[str, Any],
    source: dict[str, Any] | None,
    governance: dict[str, Any] | None,
    compiler_declared: Any,
    repo_root: Path,
) -> tuple[list[str], Any]:
    errors = _common_checks(entry, R1_ROOT, R1_LEAVES)
    claim_scope = None

    def _bound_file(binding: Any, label: str) -> tuple[str | None, str | None]:
        if not isinstance(binding, dict):
            errors.append(label + "_BINDING_INVALID")
            return None, None
        path = _resolve(repo_root, binding.get("path"))
        declared = binding.get("git_blob_sha")
        if path is None:
            errors.append(label + "_PATH_INVALID")
            return None, declared
        if not path.exists():
            errors.append(label + "_MISSING")
            return str(binding.get("path")), declared
        if git_blob_sha(path) != declared:
            errors.append(label + "_STALE")
        return str(binding.get("path")), declared

    schema_path, schema_declared = _bound_file(entry.get("contract_schema"), "CONTRACT_SCHEMA")
    registry_path, registry_declared = _bound_file(entry.get("contract_registry"), "CONTRACT_REGISTRY")
    static_path, static_declared = _bound_file(
        entry.get("registry_extension_runtime"), "REGISTRY_EXTENSION_RUNTIME"
    )
    dynamic_path, dynamic_declared = _bound_file(
        entry.get("dynamic_extension_runtime"), "DYNAMIC_EXTENSION_RUNTIME"
    )

    if source is not None:
        if source.get("schema") != R1_SOURCE_SCHEMA:
            errors.append("SOURCE_SCHEMA_INVALID")
        if source.get("status") != "PASS__PINNED_EXACT_BYTES__PYCOMPILE__21_OF_21__THREE_LAYER_STRUCTURAL_TARGET_COVER__ZERO_GLOBAL_LEAF_CREDIT":
            errors.append("SOURCE_STATUS_NOT_ADMITTED")
        exact = source.get("exact_blobs")
        if not isinstance(exact, dict):
            errors.append("SOURCE_EXACT_BLOBS_INVALID")
        else:
            if exact.get("base_runtime") != compiler_declared:
                errors.append("SOURCE_BASE_RUNTIME_MISMATCH")
            if exact.get("current_registry_extension_runtime") != static_declared:
                errors.append("SOURCE_REGISTRY_EXTENSION_RUNTIME_MISMATCH")
            if exact.get("dynamic_extension_runtime") != dynamic_declared:
                errors.append("SOURCE_DYNAMIC_EXTENSION_RUNTIME_MISMATCH")
            if exact.get("contract_schema") != schema_declared:
                errors.append("SOURCE_CONTRACT_SCHEMA_MISMATCH")
            if exact.get("contract_registry") != registry_declared:
                errors.append("SOURCE_CONTRACT_REGISTRY_MISMATCH")
        replay = source.get("replay")
        if (
            not isinstance(replay, dict)
            or replay.get("tests_run") != 21
            or replay.get("tests_passed") != 21
            or replay.get("tests_failed") != 0
        ):
            errors.append("SOURCE_REPLAY_INVALID")
        required_proved = {
            "ALL_13_CURRENT_BEHAVIORAL_CONTRACTS_COMPILE_ALL_REQUIRED_CANONICAL_BASE_FIELDS",
            "REQUIRED_CANONICAL_FIELD_OMISSION_FAILS_CLOSED",
            "POSITIVE_POLICY_COVER_DOES_NOT_REQUIRE_CANDIDATE_POLICY_SET_COMPLETENESS",
            "ALL_CURRENT_REGISTRY_NONBASE_EXTENSION_FIELDS_ARE_ROLE_CLASSIFIED",
            "UNKNOWN_CURRENT_REGISTRY_EXTENSION_FIELDS_FAIL_CLOSED",
            "DECLARED_NONSCHEMA_REQUIREMENTS_CAN_BE_PRESERVED_AS_OPAQUE_CONTENT_ADDRESSED_EXTENSION_ATOMS",
            "UNBOUND_OR_IGNORED_DYNAMIC_EXTENSION_ATOMS_FAIL_CLOSED",
        }
        if not required_proved <= set(source.get("proved") or []):
            errors.append("SOURCE_REQUIRED_STRUCTURAL_PROPERTIES_MISSING")
        required_nonclaims = {
            "OPAQUE_FIELD_OR_EXTENSION_SEMANTIC_TRUTH",
            "CERTIFICATE_TRUTH",
            "SOURCE_EXTRACTION_COMPLETENESS",
            "POLICY_ADEQUACY",
            "NEGATIVE_POLICY_ABSENCE_OR_GLOBAL_MINIMALITY",
            "GLOBAL_R1_SEMANTIC_OR_EXECUTION_LEAF_CLOSURE",
        }
        if not required_nonclaims <= set(source.get("not_proved") or []):
            errors.append("SOURCE_SCOPE_NONCLAIMS_MISSING")
        truth = source.get("current_truth")
        if not isinstance(truth, dict):
            errors.append("SOURCE_CURRENT_TRUTH_INVALID")
        else:
            if truth.get("semantic_truth_closed") is not False:
                errors.append("SOURCE_SEMANTIC_TRUTH_OVERCLAIM")
            if truth.get("global_r1_root_closed") is not False:
                errors.append("SOURCE_GLOBAL_R1_OVERCLAIM")

    if governance is not None:
        if governance.get("schema") != R1_GOVERNANCE_SCHEMA:
            errors.append("R1_GOVERNANCE_SCHEMA_INVALID")
        if governance.get("status") != "ACTIVE_SCOPED_STRUCTURAL_TARGET_CONTRACT__21_OF_21_INDEPENDENT_REPLAY__ZERO_GLOBAL_LEAF_CREDIT":
            errors.append("R1_GOVERNANCE_STATUS_INVALID")
        components = governance.get("exact_components")
        if not isinstance(components, dict):
            errors.append("R1_GOVERNANCE_COMPONENTS_INVALID")
        else:
            checks = (
                ("base_runtime", compiler_declared),
                ("current_registry_extension_runtime", static_declared),
                ("dynamic_extension_runtime", dynamic_declared),
                ("contract_schema", schema_declared),
                ("contract_registry", registry_declared),
            )
            for label, expected in checks:
                row = components.get(label)
                if not isinstance(row, dict) or row.get("git_blob_sha") != expected:
                    errors.append("R1_GOVERNANCE_COMPONENT_MISMATCH:" + label)
        limitations = set(governance.get("limitations") or [])
        required_limits = {
            "NO_OPAQUE_FIELD_OR_EXTENSION_SEMANTIC_INTERPRETATION",
            "NO_CERTIFICATE_TRUTH_SELF_VERIFICATION",
            "NO_SOURCE_EXTRACTION_COMPLETENESS_CLAIM",
            "NO_POLICY_ADEQUACY_FROM_STRUCTURAL_PRESERVATION_ALONE",
            "NO_NEGATIVE_POLICY_ABSENCE_OR_GLOBAL_MINIMALITY_WITHOUT_SEPARATE_COMPLETENESS_PROOF",
            "NO_GLOBAL_R1_SEMANTIC_OR_EXECUTION_LEAF_CLOSURE",
            "NO_GLOBAL_R1_ROOT_CLOSURE",
        }
        if not required_limits <= limitations:
            errors.append("R1_GOVERNANCE_SCOPE_LIMITATIONS_MISSING")
        claim_scope = {
            "kind": R1_KIND,
            "guarantees": [
                "CANONICAL_REQUIRED_BEHAVIORAL_CONTRACT_FIELDS_ARE_CONTENT_ADDRESSED_AS_OBLIGATIONS",
                "REQUIRED_BASE_FIELDS_CANNOT_SILENTLY_DISAPPEAR_FROM_ASSIGNED_ASSURANCE_LAYERS",
                "POSITIVE_POLICY_COVER_DOES_NOT_REQUIRE_COMPLETE_POLICY_SET_ENUMERATION",
                "CURRENT_REGISTRY_NONBASE_FIELDS_REQUIRE_EXPLICIT_ROLE_CLASSIFICATION",
                "UNKNOWN_REGISTRY_EXTENSIONS_FAIL_CLOSED",
                "DECLARED_NONSCHEMA_REQUIREMENTS_CAN_BE_PRESERVED_AS_OPAQUE_EXTENSION_ATOMS",
                "POLICIES_CANNOT_IGNORE_REQUIRED_EXTENSION_ATOMS_WITHOUT_CERTIFICATE_BOUND_DISCHARGE",
            ],
            "limitations": sorted(required_limits),
        }
    return errors, claim_scope


def _validate_r2(
    entry: dict[str, Any],
    source: dict[str, Any] | None,
    governance: dict[str, Any] | None,
    compiler_declared: Any,
    repo_root: Path,
) -> tuple[list[str], Any]:
    errors = _common_checks(entry, R2_ROOT, R2_LEAVES)
    claim_scope = None
    minimax = entry.get("minimax_runtime")
    minimax_path = _resolve(
        repo_root,
        minimax.get("path") if isinstance(minimax, dict) else None,
    )
    minimax_declared = (
        minimax.get("git_blob_sha") if isinstance(minimax, dict) else None
    )
    if minimax_path is None:
        errors.append("MINIMAX_RUNTIME_PATH_INVALID")
    elif not minimax_path.exists():
        errors.append("MINIMAX_RUNTIME_MISSING")
    elif git_blob_sha(minimax_path) != minimax_declared:
        errors.append("MINIMAX_RUNTIME_STALE")

    if source is not None:
        if source.get("schema") != R2_SOURCE_SCHEMA:
            errors.append("SOURCE_SCHEMA_INVALID")
        if source.get("status") != "PASS__PINNED_EXACT_BYTES__PYCOMPILE__9_OF_9__FINITE_SCOPE_COMPLETE_SEARCH_REFINEMENT__ZERO_GLOBAL_LEAF_CREDIT":
            errors.append("SOURCE_STATUS_NOT_ADMITTED")
        exact = source.get("exact_blobs")
        if not isinstance(exact, dict):
            errors.append("SOURCE_EXACT_BLOBS_INVALID")
        else:
            if exact.get("orchestrator_runtime") != compiler_declared:
                errors.append("SOURCE_ORCHESTRATOR_RUNTIME_MISMATCH")
            if exact.get("minimax_runtime") != minimax_declared:
                errors.append("SOURCE_MINIMAX_RUNTIME_MISMATCH")
        replay = source.get("replay")
        if (
            not isinstance(replay, dict)
            or replay.get("tests_run") != 9
            or replay.get("tests_passed") != 9
            or replay.get("tests_failed") != 0
        ):
            errors.append("SOURCE_REPLAY_INVALID")
        required_proved = {
            "SCOPE_INCOMPLETE_REGIONS_NEVER_AUTHORIZE_U_SUBTRACTION",
            "INDEPENDENT_POLICY_ADEQUACY_IS_REQUIRED",
            "WHOLE_REGION_COMMON_POLICY_STOPS_WITHOUT_UNNECESSARY_OBSERVATION",
            "WHEN_NO_COMMON_POLICY_EXISTS_THE_EXACT_MINIMAX_SOLVER_SELECTS_THE_CHEAPEST_DECLARED_RESOLVING_OBSERVATION",
            "OVERLAPPING_POLICY_REGIONS_ALLOW_STOPPING_BEFORE_WORLD_IDENTIFICATION",
            "INDISTINGUISHABLE_INCOMPATIBLE_WORLDS_FAIL_CLOSED",
            "NO_COMMON_POLICY_RETURNS_A_TRUTHFUL_DISCRIMINATOR_PLAN_NOT_FAKE_CLOSURE",
        }
        if not required_proved <= set(source.get("proved") or []):
            errors.append("SOURCE_REQUIRED_SEARCH_PROPERTIES_MISSING")
        required_nonclaims = {
            "GLOBAL_CANDIDATE_SEARCH_COMPLETENESS",
            "ESCAPE_PROGRESS_TOTALITY",
            "OPEN_WORLD_HYPOTHESIS_SET_COMPLETENESS",
            "POLICY_GENERATION_COMPLETENESS",
            "GLOBAL_R2_SEMANTIC_OR_EXECUTION_LEAF_CLOSURE",
        }
        if not required_nonclaims <= set(source.get("not_proved") or []):
            errors.append("SOURCE_SCOPE_NONCLAIMS_MISSING")

    if governance is not None:
        if governance.get("schema") != R2_GOVERNANCE_SCHEMA:
            errors.append("R2_GOVERNANCE_SCHEMA_INVALID")
        if governance.get("status") != "ACTIVE_SCOPED_FINITE_SCOPE_COMPLETE_SEARCH_REFINEMENT__9_OF_9_INDEPENDENT_REPLAY__ZERO_GLOBAL_LEAF_CREDIT":
            errors.append("R2_GOVERNANCE_STATUS_INVALID")
        components = governance.get("exact_components")
        if not isinstance(components, dict):
            errors.append("R2_GOVERNANCE_COMPONENTS_INVALID")
        else:
            orch = components.get("orchestrator_runtime")
            mini = components.get("minimax_runtime")
            if not isinstance(orch, dict) or orch.get("git_blob_sha") != compiler_declared:
                errors.append("R2_GOVERNANCE_ORCHESTRATOR_MISMATCH")
            if not isinstance(mini, dict) or mini.get("git_blob_sha") != minimax_declared:
                errors.append("R2_GOVERNANCE_MINIMAX_MISMATCH")
        limitations = set(governance.get("limitations") or [])
        required_limits = {
            "NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS",
            "NO_ESCAPE_PROGRESS_TOTALITY",
            "NO_OPEN_WORLD_HYPOTHESIS_COMPLETENESS",
            "NO_POLICY_GENERATION_COMPLETENESS",
            "NO_GLOBAL_R2_SEMANTIC_OR_EXECUTION_LEAF_CLOSURE",
            "NO_GLOBAL_R2_ROOT_CLOSURE",
        }
        if not required_limits <= limitations:
            errors.append("R2_GOVERNANCE_SCOPE_LIMITATIONS_MISSING")
        claim_scope = {
            "kind": R2_KIND,
            "guarantees": [
                "COMMON_INDEPENDENTLY_ADEQUATE_POLICY_CLOSES_A_SCOPE_COMPLETE_FINITE_REGION_WITHOUT_EXTRA_OBSERVATION",
                "NO_COMMON_POLICY_RETURNS_EXACT_MINIMAX_DECLARED_TRUTHFUL_DISCRIMINATOR_PLAN",
                "OVERLAPPING_POLICY_REGIONS_CAN_RESOLVE_BEFORE_WORLD_IDENTIFICATION",
                "SCOPE_INCOMPLETENESS_OR_UNRESOLVABLE_INCOMPATIBILITY_FAILS_CLOSED",
                "DISCRIMINATOR_PLAN_ALONE_NEVER_AUTHORIZES_U_SUBTRACTION",
            ],
            "limitations": sorted(required_limits),
        }
    return errors, claim_scope


def _validate_r9(
    entry: dict[str, Any],
    source: dict[str, Any] | None,
    governance: dict[str, Any] | None,
    compiler_declared: Any,
) -> tuple[list[str], Any]:
    errors = _common_checks(entry, R9_ROOT, R9_LEAVES)
    claim_scope = None
    if source is not None:
        if source.get("schema") != R9_SOURCE_SCHEMA:
            errors.append("SOURCE_SCHEMA_INVALID")
        if source.get("status") != "PASS__PINNED_EXACT_BYTES__PYCOMPILE__5_OF_5__211_OF_211_FINAL_SUCCESS_COUNTS__ZERO_GLOBAL_LEAF_CREDIT":
            errors.append("SOURCE_STATUS_NOT_ADMITTED")
        exact = source.get("exact_blobs")
        if not isinstance(exact, dict) or exact.get("runtime") != compiler_declared:
            errors.append("SOURCE_RUNTIME_MISMATCH")
        replay = source.get("replay")
        if (
            not isinstance(replay, dict)
            or replay.get("unit_tests_run") != 5
            or replay.get("unit_tests_passed") != 5
            or replay.get("exhaustive_final_success_counts_checked") != 211
        ):
            errors.append("SOURCE_REPLAY_INVALID")
        required_proved = {
            "FIXED_210_SLOT_DENOMINATOR_CANNOT_SHRINK",
            "ONLY_EXACT_SUCCESS_COUNTS_POSITIVE",
            "MISSING_OR_FINAL_NON_SUCCESS_COUNTS_ZERO_AT_FINALIZATION",
            "RESOURCE_TIMEOUT_INFRA_AND_OTHER_FINAL_FAILURES_CREATE_ZERO_POSITIVE_CREDIT",
            "FAILURE_LOCK_OCCURS_WHEN_MAXIMUM_POSSIBLE_SUCCESS_COUNT_DROPS_BELOW_TARGET",
            "DUPLICATE_OR_OUT_OF_UNIVERSE_RECORDS_FAIL_CLOSED",
            "PASS_BOUNDARY_IS_EXHAUSTIVELY_CORRECT_FOR_ALL_211_FINAL_SUCCESS_COUNTS",
        }
        if not required_proved <= set(source.get("proved") or []):
            errors.append("SOURCE_REQUIRED_CENSORING_PROPERTIES_MISSING")
        required_nonclaims = {
            "MULTIHORIZON_DEPLOYMENT_VALIDITY",
            "RARE_EVENT_COVERAGE",
            "DISTRIBUTION_SHIFT_TRANSPORT",
            "PERFORMATIVE_OR_EQUILIBRIUM_STABILITY",
            "GLOBAL_R9_SEMANTIC_OR_EXECUTION_LEAF_CLOSURE",
        }
        if not required_nonclaims <= set(source.get("not_proved") or []):
            errors.append("SOURCE_SCOPE_NONCLAIMS_MISSING")

    if governance is not None:
        if governance.get("schema") != R9_GOVERNANCE_SCHEMA:
            errors.append("R9_GOVERNANCE_SCHEMA_INVALID")
        if governance.get("status") != "ACTIVE_SCOPED_FIXED_DENOMINATOR_CONSERVATIVE_CENSORING__211_OF_211_BOUNDARY_REPLAY__ZERO_GLOBAL_LEAF_CREDIT":
            errors.append("R9_GOVERNANCE_STATUS_INVALID")
        components = governance.get("exact_components")
        if not isinstance(components, dict):
            errors.append("R9_GOVERNANCE_COMPONENTS_INVALID")
        else:
            row = components.get("runtime")
            if not isinstance(row, dict) or row.get("git_blob_sha") != compiler_declared:
                errors.append("R9_GOVERNANCE_RUNTIME_MISMATCH")
        limitations = set(governance.get("limitations") or [])
        required_limits = {
            "NO_MULTIHORIZON_DEPLOYMENT_VALIDITY",
            "NO_RARE_EVENT_COVERAGE_CLAIM",
            "NO_DISTRIBUTION_SHIFT_TRANSPORT_CLAIM",
            "NO_PERFORMATIVE_OR_EQUILIBRIUM_STABILITY",
            "NO_GLOBAL_R9_SEMANTIC_OR_EXECUTION_LEAF_CLOSURE",
            "NO_GLOBAL_R9_ROOT_CLOSURE",
        }
        if not required_limits <= limitations:
            errors.append("R9_GOVERNANCE_SCOPE_LIMITATIONS_MISSING")
        claim_scope = {
            "kind": R9_KIND,
            "guarantees": [
                "FROZEN_DENOMINATOR_NEVER_SHRINKS",
                "ONLY_EXACT_SUCCESS_COUNTS_POSITIVE",
                "FINAL_MISSING_AND_NON_SUCCESS_OUTCOMES_COUNT_ZERO",
                "DUPLICATE_OR_OUT_OF_UNIVERSE_RECORDS_FAIL_CLOSED",
                "PASS_AND_FAIL_LOCKS_ARE_MONOTONE_WITH_REMAINING_POSSIBLE_SUCCESS",
            ],
            "limitations": sorted(required_limits),
        }
    return errors, claim_scope


def _validate_r8(
    entry: dict[str, Any],
    source: dict[str, Any] | None,
    verifier: dict[str, Any] | None,
    compiler_declared: Any,
    repo_root: Path,
) -> tuple[list[str], Any]:
    errors = _common_checks(entry, R8_ROOT, R8_LEAVES)
    claim_scope = None
    scope, e = _read_bound(repo_root, entry.get("scope_governance"), "SCOPE_GOVERNANCE")
    errors.extend(e)
    if source is not None:
        if source.get("schema") != R8_SOURCE_SCHEMA:
            errors.append("SOURCE_SCHEMA_INVALID")
        if source.get("status") != "INDEPENDENT_PASS__EXACT_CURRENT_512_CASE_BINDING_PREFLIGHT__ZERO_TERMINAL_RESULT":
            errors.append("SOURCE_STATUS_NOT_ADMITTED")
        exact = source.get("exact_bound_blobs")
        if not isinstance(exact, dict) or exact.get("canonical/runtime/delegation_terminal_population_binding_v1.py") != compiler_declared:
            errors.append("SOURCE_RUNTIME_MISMATCH")
        required_verified = {
            "FROZEN_BINDING_MANIFEST_INVARIANTS_PASS",
            "FRESH_512_CASE_PRE_BEACON_POPULATION_PASSES",
            "ALL_SIX_FROZEN_DELEGATION_CASE_CLASSES_PRESENT",
            "ZERO_CASE_REPLACEMENT",
            "ZERO_ADAPTIVE_CASE_SELECTION",
            "ZERO_TUNING_REPLAY",
        }
        if not required_verified <= set(source.get("verified") or []):
            errors.append("SOURCE_REQUIRED_POPULATION_PROPERTIES_MISSING")
        if "PREFLIGHT_ONLY__POST_FREEZE_TERMINAL_BEACON_NOT_CONSUMED" not in set(source.get("limitations") or []):
            errors.append("SOURCE_PREFLIGHT_LIMIT_MISSING")
        if source.get("terminal_results_observed") != 0:
            errors.append("SOURCE_TERMINAL_RESULTS_OVERCLAIM")
    if verifier is not None:
        if verifier.get("schema") != R8_SOURCE_SCHEMA:
            errors.append("VERIFIER_SCHEMA_INVALID")
        if verifier.get("status") != "INDEPENDENT_PASS__EXACT_CURRENT_512_CASE_BINDING_PREFLIGHT__ZERO_TERMINAL_RESULT":
            errors.append("VERIFIER_STATUS_NOT_ADMITTED")
    if scope is not None:
        if scope.get("schema") != R8_SCOPE_SCHEMA:
            errors.append("SCOPE_SCHEMA_INVALID")
        if scope.get("status") != "ACTIVE_SCOPED_FROZEN_512_CASE_DELEGATION_POPULATION_BINDING__ZERO_GLOBAL_LEAF_CREDIT":
            errors.append("SCOPE_STATUS_INVALID")
        components = scope.get("exact_components")
        if not isinstance(components, dict):
            errors.append("SCOPE_COMPONENTS_INVALID")
        else:
            runtime = components.get("runtime")
            source_row = components.get("source_receipt")
            if not isinstance(runtime, dict) or runtime.get("git_blob_sha") != compiler_declared:
                errors.append("SCOPE_RUNTIME_MISMATCH")
            declared_source = (entry.get("source_receipt") or {}).get("git_blob_sha") if isinstance(entry.get("source_receipt"), dict) else None
            if not isinstance(source_row, dict) or source_row.get("git_blob_sha") != declared_source:
                errors.append("SCOPE_SOURCE_MISMATCH")
        required_limits = {
            "PREFLIGHT_ONLY__NO_POST_FREEZE_TERMINAL_RESULT",
            "NO_CONSTITUENCY_SUPPORT_CLAIM",
            "NO_PRESENTER_OR_OPERATOR_GENERALIZATION",
            "NO_MEASUREMENT_INVARIANCE_CLAIM",
            "NO_SOCIAL_INFLUENCE_OR_REACTIVITY_CLOSURE",
            "NO_GLOBAL_R8_SEMANTIC_OR_EXECUTION_LEAF_CLOSURE",
            "NO_GLOBAL_R8_ROOT_CLOSURE",
        }
        if not required_limits <= set(scope.get("limitations") or []):
            errors.append("SCOPE_LIMITATIONS_MISSING")
        claim_scope = {
            "kind": R8_KIND,
            "guarantees": [
                "FROZEN_512_CASE_PRE_BEACON_POPULATION_PASSES",
                "ALL_SIX_FROZEN_DELEGATION_CASE_CLASSES_PRESENT",
                "ZERO_CASE_REPLACEMENT",
                "ZERO_ADAPTIVE_CASE_SELECTION",
                "ZERO_TUNING_REPLAY",
            ],
            "limitations": sorted(required_limits),
        }
    return errors, claim_scope


def _validate_r12(
    entry: dict[str, Any],
    source: dict[str, Any] | None,
    verifier: dict[str, Any] | None,
    compiler_declared: Any,
    repo_root: Path,
) -> tuple[list[str], Any]:
    errors = _common_checks(entry, R12_ROOT, R12_LEAVES)
    claim_scope = None
    scope, e = _read_bound(repo_root, entry.get("scope_governance"), "SCOPE_GOVERNANCE")
    errors.extend(e)
    if source is not None:
        if source.get("schema") != R12_SOURCE_SCHEMA:
            errors.append("SOURCE_SCHEMA_INVALID")
        if source.get("status") != "PASS__PINNED_CURRENT_GENERATION__PYCOMPILE__18_OF_18__ZERO_TERMINAL_CREDIT":
            errors.append("SOURCE_STATUS_NOT_ADMITTED")
        exact = source.get("exact_blobs")
        if not isinstance(exact, dict) or exact.get("uvck_runtime") != compiler_declared:
            errors.append("SOURCE_RUNTIME_MISMATCH")
        replay = source.get("replay")
        if not isinstance(replay, dict) or replay.get("tests_run") != 18 or replay.get("tests_passed") != 18 or replay.get("tests_failed") != 0:
            errors.append("SOURCE_REPLAY_INVALID")
        required_proved = {
            "SUPPORTED_DEFEATER_DOMINANCE_IS_ORDER_INDEPENDENT_ON_CURRENT_GENERATION",
            "GENERIC_GRAPH_STILL_CANNOT_SELF_CERTIFY_EXECUTION_OR_ADVERSARIAL_CLOSURE",
            "UNMAPPED_CHALLENGE_FAILS_CLOSED",
            "KNOWN_PROFESSIONAL_QUALITY_ATTACK_SET_REQUIRES_NO_NEW_UVCK_PRIMITIVE",
        }
        if not required_proved <= set(source.get("proves") or []):
            errors.append("SOURCE_REQUIRED_META_PROPERTIES_MISSING")
        required_nonclaims = {
            "UNKNOWN_DEFEATER_COMPLETENESS",
            "PROFESSIONAL_QUALITY_DOMAIN_PROOF_CLOSURE",
            "PROFESSIONAL_QUALITY_DOMAIN_EXECUTION_CLOSURE",
            "FULL_PRIVATE_CURRENT_MAIN_FULL_SYSTEM_REGRESSION",
            "LIVE_DEFAULT_PROMOTION",
        }
        if not required_nonclaims <= set(source.get("not_proved") or []):
            errors.append("SOURCE_SCOPE_NONCLAIMS_MISSING")
    if verifier is not None:
        if verifier.get("schema") != R12_VERIFY_SCHEMA:
            errors.append("VERIFIER_SCHEMA_INVALID")
        if verifier.get("status") != "PASS__EXACT_BLOBS__PYCOMPILE__11_OF_11__ZERO_CREDIT":
            errors.append("VERIFIER_STATUS_NOT_ADMITTED")
        if verifier.get("runtime_git_blob_sha") != compiler_declared:
            errors.append("VERIFIER_RUNTIME_MISMATCH")
    if scope is not None:
        if scope.get("schema") != R12_SCOPE_SCHEMA:
            errors.append("SCOPE_SCHEMA_INVALID")
        if scope.get("status") != "ACTIVE_SCOPED_UVCK_META_COMPOSITION_AND_DEFEATER_SOUNDNESS__ZERO_GLOBAL_LEAF_CREDIT":
            errors.append("SCOPE_STATUS_INVALID")
        components = scope.get("exact_components")
        if not isinstance(components, dict):
            errors.append("SCOPE_COMPONENTS_INVALID")
        else:
            runtime = components.get("runtime")
            replay_row = components.get("current_generation_replay")
            order_row = components.get("order_soundness_verification")
            if not isinstance(runtime, dict) or runtime.get("git_blob_sha") != compiler_declared:
                errors.append("SCOPE_RUNTIME_MISMATCH")
            source_declared = (entry.get("source_receipt") or {}).get("git_blob_sha") if isinstance(entry.get("source_receipt"), dict) else None
            verifier_declared = (entry.get("compiler_verification") or {}).get("git_blob_sha") if isinstance(entry.get("compiler_verification"), dict) else None
            if not isinstance(replay_row, dict) or replay_row.get("git_blob_sha") != source_declared:
                errors.append("SCOPE_SOURCE_MISMATCH")
            if not isinstance(order_row, dict) or order_row.get("git_blob_sha") != verifier_declared:
                errors.append("SCOPE_VERIFIER_MISMATCH")
        required_limits = {
            "NO_UNKNOWN_DEFEATER_COMPLETENESS",
            "NO_DOMAIN_SEMANTIC_CLOSURE",
            "NO_DOMAIN_EXECUTION_CLOSURE",
            "NO_FULL_PRIVATE_REPOSITORY_REGRESSION",
            "NO_LIVE_DEFAULT_PROMOTION",
            "NO_GLOBAL_R12_SEMANTIC_OR_EXECUTION_LEAF_CLOSURE",
            "NO_GLOBAL_R12_ROOT_CLOSURE",
        }
        if not required_limits <= set(scope.get("limitations") or []):
            errors.append("SCOPE_LIMITATIONS_MISSING")
        claim_scope = {
            "kind": R12_KIND,
            "guarantees": [
                "SUPPORTED_DEFEATER_DOMINANCE_IS_ORDER_INDEPENDENT",
                "GENERIC_GRAPH_CANNOT_SELF_CERTIFY_EXECUTION_OR_ADVERSARIAL_CLOSURE",
                "UNMAPPED_CHALLENGE_FAILS_CLOSED",
                "KNOWN_PROFESSIONAL_QUALITY_ATTACK_SET_REQUIRES_NO_NEW_UVCK_PRIMITIVE",
            ],
            "limitations": sorted(required_limits),
        }
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
    elif kind == R11_SEMANTIC_KIND:
        handler_errors, claim_scope = _validate_r11_semantic(
            entry, source, verifier, compiler_declared, repo_root
        )
    elif kind == R11_KIND:
        handler_errors, claim_scope = _validate_r11(entry, source, verifier, compiler_declared)
    elif kind == R10_KIND:
        handler_errors, claim_scope = _validate_r10(entry, source, verifier, compiler_declared)
    elif kind == R6_KIND:
        handler_errors, claim_scope = _validate_r6(entry, source, verifier, compiler_declared)
    elif kind == R4_KIND:
        handler_errors, claim_scope = _validate_r4(
            entry, source, verifier, compiler_declared, repo_root
        )
    elif kind == R5_KIND:
        handler_errors, claim_scope = _validate_r5(entry, source, verifier, compiler_declared)
    elif kind == R1_SEMANTIC_KIND:
        handler_errors, claim_scope = _validate_r1_semantic(
            entry, source, verifier, compiler_declared, repo_root
        )
    elif kind == R1_KIND:
        handler_errors, claim_scope = _validate_r1(
            entry, source, verifier, compiler_declared, repo_root
        )
    elif kind == R2_KIND:
        handler_errors, claim_scope = _validate_r2(
            entry, source, verifier, compiler_declared, repo_root
        )
    elif kind == R9_KIND:
        handler_errors, claim_scope = _validate_r9(
            entry, source, verifier, compiler_declared
        )
    elif kind == R8_KIND:
        handler_errors, claim_scope = _validate_r8(
            entry, source, verifier, compiler_declared, repo_root
        )
    elif kind == R12_KIND:
        handler_errors, claim_scope = _validate_r12(
            entry, source, verifier, compiler_declared, repo_root
        )
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
