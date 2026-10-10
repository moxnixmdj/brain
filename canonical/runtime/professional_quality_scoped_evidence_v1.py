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
