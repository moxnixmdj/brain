"""Claim-scoped professional-quality evidence registry validator.

Admits reusable bounded domain capability evidence without allowing it to close
the global semantic/execution leaves. This is the bookkeeping bridge between
verified claim-scoped capability and the still-open universal domain root.
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
SOURCE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R7_SINGLE_EDIT_CAUSAL_INSTANCE_VERIFY_V1"
COMPILER_VERIFY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_EDIT_CAUSAL_CERTIFICATE_VERIFY_V1"
R7_ROOT = "R7_CAUSAL_PRESCRIPTIVE"
R7_LEAVES = {
    "PQ::R7_CAUSAL_PRESCRIPTIVE::SEMANTIC",
    "PQ::R7_CAUSAL_PRESCRIPTIVE::EXECUTION",
}
CLAIM_KIND = "EXACT_SINGLE_EDIT_PROFESSIONAL_CODE_INTERVENTION_INSTANCE"


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
    errors: list[str] = []
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
        errors.append(f"{label}_STALE")
        return None, errors
    try:
        return _load(path), errors
    except Exception:
        return None, [f"{label}_JSON_INVALID"]


def validate_entry(entry: dict[str, Any], *, repo_root: Path = ROOT) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(entry, dict):
        return {"admitted": False, "errors": ["ENTRY_INVALID"]}

    scope_id = entry.get("scope_id")
    root_id = entry.get("root_id")
    leaf_ids = entry.get("contributes_to_leaf_ids")
    if not isinstance(scope_id, str) or not scope_id:
        errors.append("SCOPE_ID_INVALID")
    if root_id != R7_ROOT:
        errors.append("ROOT_ID_INVALID")
    if not isinstance(leaf_ids, list) or set(leaf_ids) != R7_LEAVES:
        errors.append("R7_LEAF_BINDING_INVALID")
    if entry.get("claim_kind") != CLAIM_KIND:
        errors.append("CLAIM_KIND_INVALID")
    if entry.get("global_leaf_closure") is not False:
        errors.append("GLOBAL_LEAF_CLOSURE_FORBIDDEN")
    if entry.get("global_root_closure") is not False:
        errors.append("GLOBAL_ROOT_CLOSURE_FORBIDDEN")
    if entry.get("terminal_credit_delta") != 0:
        errors.append("TERMINAL_CREDIT_FORBIDDEN")

    source, e = _read_bound(repo_root, entry.get("source_receipt"), "SOURCE_RECEIPT")
    errors.extend(e)
    compiler_verify, e = _read_bound(
        repo_root, entry.get("compiler_verification"), "COMPILER_VERIFICATION"
    )
    errors.extend(e)
    compiler_path = _resolve(
        repo_root,
        (entry.get("reusable_compiler") or {}).get("path")
        if isinstance(entry.get("reusable_compiler"), dict)
        else None,
    )
    compiler_declared = (
        (entry.get("reusable_compiler") or {}).get("git_blob_sha")
        if isinstance(entry.get("reusable_compiler"), dict)
        else None
    )
    if compiler_path is None:
        errors.append("COMPILER_PATH_INVALID")
    elif not compiler_path.exists():
        errors.append("COMPILER_MISSING")
    elif git_blob_sha(compiler_path) != compiler_declared:
        errors.append("COMPILER_STALE")

    if source is not None:
        if source.get("schema") != SOURCE_SCHEMA:
            errors.append("SOURCE_SCHEMA_INVALID")
        if source.get("root_id") != R7_ROOT:
            errors.append("SOURCE_ROOT_INVALID")
        scope = source.get("claim_scope")
        conclusions = source.get("conclusions")
        dispositions = source.get("r7_defeater_disposition")
        if not isinstance(scope, dict) or scope.get("kind") != CLAIM_KIND:
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
        if compiler_verify.get("schema") != COMPILER_VERIFY_SCHEMA:
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

    admitted = not errors
    claim_scope = source.get("claim_scope") if isinstance(source, dict) else None
    return {
        "scope_id": scope_id,
        "root_id": root_id,
        "admitted": admitted,
        "errors": sorted(set(errors)),
        "claim_scope": claim_scope,
        "contributes_to_leaf_ids": sorted(leaf_ids) if isinstance(leaf_ids, list) else [],
        "global_leaf_credit": False,
        "global_root_credit": False,
        "terminal_credit_delta": 0,
    }


def evaluate(*, registry_path: Path = REGISTRY, repo_root: Path = ROOT) -> dict[str, Any]:
    registry = _load(registry_path)
    errors: list[str] = []
    if registry.get("schema") != REGISTRY_SCHEMA:
        errors.append("REGISTRY_SCHEMA_INVALID")
    entries = registry.get("entries")
    if not isinstance(entries, list):
        entries = []
        errors.append("REGISTRY_ENTRIES_INVALID")

    results = [
        validate_entry(entry, repo_root=repo_root)
        for entry in entries
        if isinstance(entry, dict)
    ]
    scope_ids = [x.get("scope_id") for x in results]
    if len(scope_ids) != len(set(scope_ids)):
        errors.append("DUPLICATE_SCOPE_ID")

    admitted = [x for x in results if x.get("admitted") is True]
    rejected = [x for x in results if x.get("admitted") is not True]
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__SCOPED_CAPABILITIES_ADMITTED_WITH_ZERO_GLOBAL_LEAF_CREDIT"
            if not errors and not rejected
            else "OPEN__SCOPED_EVIDENCE_REGISTRY_ERRORS"
        ),
        "pass": not errors and not rejected,
        "structural_errors": sorted(set(errors)),
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
