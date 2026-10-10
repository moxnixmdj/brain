"""Professional-quality leaf binder V3.

V3 preserves V2 execution-leaf admission and hardens semantic-leaf admission.
A semantic receipt cannot close a leaf merely by self-asserting
leaf_semantic_satisfied=True with arbitrary current basis files. It must bind the
exact frozen semantic-totality claim for that leaf and an immutable,
claim-identical CC_R1/CC_R2/CC_R3 registry snapshot whose R4 proof closure
recomputes successfully. Every root certificate, semantic verifier, and
independent verification referenced by that snapshot is content-addressed and
must still exist at the declared Git blob.

This remains an admission gate only. It grants no semantic, execution, quality,
acceptance, promotion, or terminal authority by itself.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping
import json

from canonical.runtime import professional_quality_leaf_binder_v2 as v2
from canonical.runtime import coverage_root_certificate_registry_guard_v1 as root_guard

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_BINDER_V3"
MANIFEST = v2.MANIFEST
GRAPH = v2.GRAPH
REGISTRY = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_20261010_V2.json"
RECEIPT_SCHEMA = v2.RECEIPT_SCHEMA

CLAIM_PACK_PATH = ROOT / "canonical/governance/PROFESSIONAL_SEMANTIC_TOTALITY_FROZEN_CLAIM_PACK_20261010_V2.json"
CLAIM_PACK_BLOB = "f16aab3760d4f5958da986782632f3cb2bbd2646"
CLAIM_PACK_VERIFY_PATH = ROOT / "canonical/verification/PROFESSIONAL_SEMANTIC_TOTALITY_CLAIM_PACK_VERIFY_20261010_V2.json"
CLAIM_PACK_VERIFY_BLOB = "3d1f32e6e0e24d49c394daa365a7e3797c7d9984"
MISSION_POINTER_PATH = ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
ROOT_GUARD_PATH = ROOT / "canonical/runtime/coverage_root_certificate_registry_guard_v1.py"
ROOT_GUARD_BLOB = "23cb2d635d38b1b4cdea6d2c7ccd40636dca36c6"

CLAIM_FIELDS = (
    "claim_id",
    "claim_kind",
    "mission_blob_sha",
    "scope_sha256",
    "target_predicate_sha256",
    "semantics_sha256",
    "epoch",
    "authority_id",
)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_NOT_OBJECT")
    return value


def _current_semantic_claims(repo_root: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    errors: list[str] = []
    pack_path = repo_root / CLAIM_PACK_PATH.relative_to(ROOT)
    verify_path = repo_root / CLAIM_PACK_VERIFY_PATH.relative_to(ROOT)
    if not pack_path.is_file() or v2.git_blob_sha(pack_path) != CLAIM_PACK_BLOB:
        return {}, ["SEMANTIC_TOTALITY_CLAIM_PACK_STALE"]
    if not verify_path.is_file() or v2.git_blob_sha(verify_path) != CLAIM_PACK_VERIFY_BLOB:
        return {}, ["SEMANTIC_TOTALITY_CLAIM_PACK_VERIFY_STALE"]
    try:
        pack = _load_json(pack_path)
        verify = _load_json(verify_path)
    except Exception:
        return {}, ["SEMANTIC_TOTALITY_CLAIM_PACK_JSON_INVALID"]

    if not str(pack.get("status") or "").startswith("FROZEN_CURRENT_MISSION_BOUND"):
        errors.append("SEMANTIC_TOTALITY_CLAIM_PACK_STATUS_INVALID")
    if not str(verify.get("status") or "").startswith("PASS__"):
        errors.append("SEMANTIC_TOTALITY_CLAIM_PACK_VERIFY_NOT_PASS")
    replay = verify.get("independent_replay") or {}
    if replay.get("tests_failed") not in (None, 0):
        errors.append("SEMANTIC_TOTALITY_CLAIM_PACK_REPLAY_FAILED")

    rows = pack.get("claims")
    if not isinstance(rows, list) or len(rows) != 12:
        errors.append("SEMANTIC_TOTALITY_CLAIM_PACK_CARDINALITY_INVALID")
        rows = []
    claims: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            errors.append("SEMANTIC_TOTALITY_CLAIM_ROW_INVALID")
            continue
        leaf_id = row.get("leaf_id")
        claim = row.get("frozen_claim")
        if not isinstance(leaf_id, str) or not isinstance(claim, Mapping):
            errors.append("SEMANTIC_TOTALITY_CLAIM_ROW_BINDING_INVALID")
            continue
        if leaf_id in claims:
            errors.append("SEMANTIC_TOTALITY_CLAIM_DUPLICATE_LEAF")
            continue
        claims[leaf_id] = dict(claim)
    return claims, errors


def _same_claim(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return all(left.get(field) == right.get(field) for field in CLAIM_FIELDS)


def validate_semantic_totality_documents(
    *,
    leaf_id: str,
    frozen_claim: Mapping[str, Any],
    registry_snapshot: Mapping[str, Any],
    current_mission_pointer: Mapping[str, Any],
    current_mission_authority_blob_sha: str,
    current_mission_pointer_blob_sha: str,
) -> dict[str, Any]:
    errors: list[str] = []
    active = registry_snapshot.get("active_claim")
    if not isinstance(active, Mapping):
        errors.append("SEMANTIC_COVERAGE_ACTIVE_CLAIM_REQUIRED")
    elif not _same_claim(active, frozen_claim):
        errors.append("SEMANTIC_COVERAGE_ACTIVE_CLAIM_MISMATCH")

    out = root_guard.validate(
        registry_snapshot,
        current_mission_pointer=current_mission_pointer,
        current_mission_authority_blob_sha=current_mission_authority_blob_sha,
        current_mission_pointer_blob_sha=current_mission_pointer_blob_sha,
    )
    if out.get("pass") is not True:
        errors.append("SEMANTIC_COVERAGE_ROOT_REGISTRY_REJECTED")
    if out.get("r4_proof_closure") is not True:
        errors.append("SEMANTIC_COVERAGE_R4_PROOF_CLOSURE_REQUIRED")
    if set(out.get("proved_root_ids") or []) != set(root_guard.CERTIFICATE_ROOT_IDS):
        errors.append("SEMANTIC_COVERAGE_THREE_ROOTS_REQUIRED")
    if registry_snapshot.get("currently_proved_root_certificates") != 3:
        errors.append("SEMANTIC_COVERAGE_PROVED_COUNT_INVALID")
    if registry_snapshot.get("currently_open_root_certificates") != 0:
        errors.append("SEMANTIC_COVERAGE_OPEN_ROOTS_REMAIN")

    return {
        "pass": not errors,
        "leaf_id": leaf_id,
        "claim_id": frozen_claim.get("claim_id"),
        "errors": errors,
        "r4_proof_closure": out.get("r4_proof_closure") is True,
        "proved_root_ids": out.get("proved_root_ids") or [],
        "semantic_truth_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def _semantic_totality_guard(
    *,
    repo_root: Path,
    receipt: Mapping[str, Any],
    leaf_id: str,
) -> dict[str, Any]:
    claims, errors = _current_semantic_claims(repo_root)
    if errors:
        return {"pass": False, "errors": errors}
    frozen_claim = claims.get(leaf_id)
    if frozen_claim is None:
        return {"pass": False, "errors": ["SEMANTIC_TOTALITY_CLAIM_NOT_FOUND"]}

    claim_id = receipt.get("semantic_totality_claim_id")
    if claim_id != frozen_claim.get("claim_id"):
        return {"pass": False, "errors": ["SEMANTIC_TOTALITY_CLAIM_ID_MISMATCH"]}

    snapshot_ref = receipt.get("coverage_root_registry_snapshot")
    if not isinstance(snapshot_ref, Mapping):
        return {"pass": False, "errors": ["SEMANTIC_COVERAGE_ROOT_REGISTRY_SNAPSHOT_REQUIRED"]}
    snapshot_path_text = snapshot_ref.get("path")
    snapshot_sha = snapshot_ref.get("git_blob_sha")
    fresh, _ = v2._check_content_addressed_file(
        repo_root=repo_root,
        path_text=snapshot_path_text,
        declared_sha=snapshot_sha,
    )
    if not fresh:
        return {"pass": False, "errors": ["SEMANTIC_COVERAGE_ROOT_REGISTRY_SNAPSHOT_NOT_CURRENT"]}
    snapshot_path = v2._resolve(repo_root, snapshot_path_text)
    assert snapshot_path is not None
    try:
        snapshot = _load_json(snapshot_path)
    except Exception:
        return {"pass": False, "errors": ["SEMANTIC_COVERAGE_ROOT_REGISTRY_SNAPSHOT_JSON_INVALID"]}

    mission_path = repo_root / MISSION_POINTER_PATH.relative_to(ROOT)
    guard_path = repo_root / ROOT_GUARD_PATH.relative_to(ROOT)
    if not mission_path.is_file():
        return {"pass": False, "errors": ["CURRENT_MISSION_POINTER_MISSING"]}
    if not guard_path.is_file() or v2.git_blob_sha(guard_path) != ROOT_GUARD_BLOB:
        return {"pass": False, "errors": ["COVERAGE_ROOT_REGISTRY_GUARD_STALE"]}
    try:
        mission = _load_json(mission_path)
    except Exception:
        return {"pass": False, "errors": ["CURRENT_MISSION_POINTER_JSON_INVALID"]}
    authority = mission.get("authoritative_source") or {}
    authority_path_text = authority.get("path")
    authority_path = v2._resolve(repo_root, authority_path_text)
    if authority_path is None or not authority_path.is_file():
        return {"pass": False, "errors": ["CURRENT_MISSION_AUTHORITY_MISSING"]}

    doc_result = validate_semantic_totality_documents(
        leaf_id=leaf_id,
        frozen_claim=frozen_claim,
        registry_snapshot=snapshot,
        current_mission_pointer=mission,
        current_mission_authority_blob_sha=v2.git_blob_sha(authority_path),
        current_mission_pointer_blob_sha=v2.git_blob_sha(mission_path),
    )
    if doc_result.get("pass") is not True:
        return doc_result

    # Re-open every load-bearing root artifact. The registry guard validates
    # their claim identity; this layer adds actual byte currentness.
    for slot in snapshot.get("certificate_slots") or []:
        if not isinstance(slot, Mapping) or slot.get("status") != "PROVED_CURRENT":
            continue
        for field in ("certificate", "semantic_verifier", "independent_verification"):
            ref = slot.get(field)
            if not isinstance(ref, Mapping):
                return {"pass": False, "errors": [f"SEMANTIC_COVERAGE_{field.upper()}_REF_REQUIRED"]}
            fresh, _ = v2._check_content_addressed_file(
                repo_root=repo_root,
                path_text=ref.get("path"),
                declared_sha=ref.get("git_blob_sha"),
            )
            if not fresh:
                return {"pass": False, "errors": [f"SEMANTIC_COVERAGE_{field.upper()}_NOT_CURRENT"]}
        verify_ref = slot.get("independent_verification") or {}
        verify_path = v2._resolve(repo_root, verify_ref.get("path"))
        assert verify_path is not None
        try:
            verify_doc = _load_json(verify_path)
        except Exception:
            return {"pass": False, "errors": ["SEMANTIC_COVERAGE_INDEPENDENT_VERIFICATION_JSON_INVALID"]}
        if verify_doc.get("claim_id") != frozen_claim.get("claim_id"):
            return {"pass": False, "errors": ["SEMANTIC_COVERAGE_INDEPENDENT_VERIFICATION_CLAIM_MISMATCH"]}
        if not str(verify_doc.get("status") or "").startswith("PASS__"):
            return {"pass": False, "errors": ["SEMANTIC_COVERAGE_INDEPENDENT_VERIFICATION_NOT_PASS"]}
        if verify_doc.get("terminal_authority") is True:
            return {"pass": False, "errors": ["SEMANTIC_COVERAGE_TERMINAL_AUTHORITY_FORBIDDEN"]}

    return {
        **doc_result,
        "pass": True,
        "semantic_totality_claim_id": frozen_claim.get("claim_id"),
        "coverage_root_registry_snapshot_git_blob_sha": snapshot_sha,
    }


def _receipt_result(
    *,
    repo_root: Path,
    entry: dict[str, Any],
    leaf_id: str,
    root_id: str,
    kind: str,
    acceptance: str,
    contract: str,
    manifest_blob_sha: str,
) -> dict[str, Any]:
    result = v2._receipt_result(
        repo_root=repo_root,
        entry=entry,
        leaf_id=leaf_id,
        root_id=root_id,
        kind=kind,
        acceptance=acceptance,
        contract=contract,
        manifest_blob_sha=manifest_blob_sha,
    )
    if kind != "SEMANTIC" or result.get("admitted") is not True:
        return result

    receipt_path = v2._resolve(repo_root, entry.get("path"))
    assert receipt_path is not None
    receipt = _load_json(receipt_path)
    guard = _semantic_totality_guard(repo_root=repo_root, receipt=receipt, leaf_id=leaf_id)
    result["semantic_totality_guard"] = guard
    if guard.get("pass") is not True:
        result["errors"].extend(guard.get("errors") or ["SEMANTIC_TOTALITY_PROOF_REQUIRED"])
        result["admitted"] = False
    return result


def evaluate(
    *,
    manifest_path: Path = MANIFEST,
    graph_path: Path = GRAPH,
    registry_path: Path = REGISTRY,
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    # V2 evaluator is copied structurally so semantic receipts flow through the
    # V3 receipt guard while execution behavior stays identical.
    manifest = v2._load(manifest_path)
    graph = v2._load(graph_path)
    registry = v2._load(registry_path)

    structural_errors: list[str] = []
    expected_roots = set(graph.get("root_ids") or [])
    rows = manifest.get("roots") or []
    seen_roots = {row.get("root_id") for row in rows}

    if manifest.get("root_count") != 12: structural_errors.append("ROOT_COUNT_INVALID")
    if manifest.get("semantic_leaf_count") != 12: structural_errors.append("SEMANTIC_LEAF_COUNT_INVALID")
    if manifest.get("execution_leaf_count") != 12: structural_errors.append("EXECUTION_LEAF_COUNT_INVALID")
    if manifest.get("total_leaf_count") != 24: structural_errors.append("TOTAL_LEAF_COUNT_INVALID")
    if seen_roots != expected_roots: structural_errors.append("ROOT_SET_MISMATCH")
    if registry.get("schema") != "PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_V1":
        structural_errors.append("REGISTRY_SCHEMA_INVALID")
    if registry.get("receipt_schema") != RECEIPT_SCHEMA:
        structural_errors.append("REGISTRY_RECEIPT_SCHEMA_INVALID")

    manifest_blob_sha = v2.git_blob_sha(manifest_path)
    graph_blob_sha = v2.git_blob_sha(graph_path)
    reg_manifest = registry.get("manifest") or {}
    reg_graph = registry.get("graph") or {}
    if reg_manifest.get("git_blob_sha") != manifest_blob_sha: structural_errors.append("REGISTRY_MANIFEST_BINDING_STALE")
    if reg_graph.get("git_blob_sha") != graph_blob_sha: structural_errors.append("REGISTRY_GRAPH_BINDING_STALE")

    leaf_receipts = registry.get("leaf_receipts")
    if not isinstance(leaf_receipts, dict):
        structural_errors.append("LEAF_RECEIPTS_NOT_OBJECT")
        leaf_receipts = {}

    expected_leaf_ids: set[str] = set()
    declared_verified_without_receipt: list[str] = []
    verified_semantic: list[str] = []
    verified_execution: list[str] = []
    open_semantic: list[str] = []
    open_execution: list[str] = []
    receipt_results: list[dict[str, Any]] = []
    existing_evidence_records: list[dict[str, Any]] = []
    existing_evidence_current = True

    for row in rows:
        root_id = row.get("root_id")
        contract = row.get("contract") or ""
        for ev in row.get("existing_evidence") or []:
            ok, rec = v2._check_content_addressed_file(
                repo_root=repo_root,
                path_text=ev.get("path") if isinstance(ev, dict) else None,
                declared_sha=ev.get("git_blob_sha") if isinstance(ev, dict) else None,
            )
            existing_evidence_records.append({"root_id": root_id, **rec})
            if not ok: existing_evidence_current = False

        for kind, field, verified_sink, open_sink in (
            ("SEMANTIC", "semantic_leaf", verified_semantic, open_semantic),
            ("EXECUTION", "execution_leaf", verified_execution, open_execution),
        ):
            leaf = row.get(field) or {}
            leaf_id = leaf.get("id")
            if not isinstance(leaf_id, str) or not leaf_id:
                structural_errors.append(f"{kind}_LEAF_ID_INVALID:{root_id}")
                continue
            expected_leaf_ids.add(leaf_id)
            entries = leaf_receipts.get(leaf_id, [])
            if not isinstance(entries, list):
                structural_errors.append(f"LEAF_RECEIPT_LIST_INVALID:{leaf_id}")
                entries = []
            results = []
            for entry in entries:
                if not isinstance(entry, dict):
                    results.append({"leaf_id": leaf_id, "root_id": root_id, "kind": kind, "admitted": False, "errors": ["REGISTRY_ENTRY_INVALID"]})
                    continue
                results.append(_receipt_result(
                    repo_root=repo_root, entry=entry, leaf_id=leaf_id, root_id=str(root_id),
                    kind=kind, acceptance=leaf.get("acceptance") or "", contract=contract,
                    manifest_blob_sha=manifest_blob_sha,
                ))
            receipt_results.extend(results)
            admitted = any(x.get("admitted") is True for x in results)
            if admitted: verified_sink.append(leaf_id)
            else:
                open_sink.append(leaf_id)
                if leaf.get("status") == "VERIFIED": declared_verified_without_receipt.append(leaf_id)

    unknown_registry_leaf_ids = sorted(set(leaf_receipts) - expected_leaf_ids)
    if unknown_registry_leaf_ids: structural_errors.append("REGISTRY_UNKNOWN_LEAF_IDS")
    rejected_receipts = [x for x in receipt_results if x.get("admitted") is not True]
    all_leaves_verified = len(verified_semantic) == 12 and len(verified_execution) == 12
    receipt_set_clean = not rejected_receipts
    promotion_ready = (
        not structural_errors and existing_evidence_current and receipt_set_clean
        and all_leaves_verified and manifest.get("terminal_authority") is False
        and registry.get("terminal_authority") is False
    )
    return {
        "schema": SCHEMA,
        "status": "PASS__ALL_24_LEAVES_DERIVED_FROM_SCOPE_MATCHED_RECEIPTS" if promotion_ready else "OPEN__LEAF_RECEIPTS_OR_EVIDENCE_REMAIN",
        "pass": promotion_ready,
        "structural_errors": sorted(set(structural_errors)),
        "manifest_git_blob_sha": manifest_blob_sha,
        "graph_git_blob_sha": graph_blob_sha,
        "verified_semantic_leaf_ids": sorted(verified_semantic),
        "verified_execution_leaf_ids": sorted(verified_execution),
        "open_semantic_leaf_ids": sorted(open_semantic),
        "open_execution_leaf_ids": sorted(open_execution),
        "verified_leaf_count": len(verified_semantic) + len(verified_execution),
        "open_leaf_count": len(open_semantic) + len(open_execution),
        "declared_verified_without_receipt": sorted(declared_verified_without_receipt),
        "receipt_results": receipt_results,
        "rejected_receipt_count": len(rejected_receipts),
        "existing_evidence_current": existing_evidence_current,
        "existing_evidence_records": existing_evidence_records,
        "unknown_registry_leaf_ids": unknown_registry_leaf_ids,
        "promotion_ready": promotion_ready,
        "manifest_status_has_promotion_authority": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
