"""Professional-quality semantic/execution leaf binder V2.

V1 exposed the 24 domain leaves but trusted each manifest leaf's literal status
field. V2 removes that self-certification path. Leaf closure is derived only
from scope-matched, content-addressed verification receipts whose own evidence
basis is also content-addressed and current.

This module still grants no semantic, execution, acceptance, or terminal
authority. It is a structural admission gate for evidence already produced by
independent domain verification.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_semantic_totality_claim_pack_v3 as semantic_pack_v3

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json"
GRAPH = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_ASSURANCE_GRAPH_20261009_V2.json"
REGISTRY = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_20261010_V2.json"

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_BINDER_V2"
RECEIPT_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_VERIFICATION_RECEIPT_V1"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("utf-8")
    return sha1(header + data).hexdigest()


def semantic_sha(text: Any) -> str:
    if not isinstance(text, str):
        text = ""
    return sha256(text.encode("utf-8")).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _resolve(repo_root: Path, path_text: Any) -> Path | None:
    if not isinstance(path_text, str) or not path_text.startswith("canonical/"):
        return None
    return repo_root / path_text


def _check_content_addressed_file(
    *,
    repo_root: Path,
    path_text: Any,
    declared_sha: Any,
) -> tuple[bool, dict[str, Any]]:
    path = _resolve(repo_root, path_text)
    if path is None:
        return False, {
            "status": "INVALID_PATH",
            "path": path_text,
            "declared_git_blob_sha": declared_sha,
        }
    if not path.exists():
        return False, {
            "status": "MISSING",
            "path": path_text,
            "declared_git_blob_sha": declared_sha,
        }
    actual = git_blob_sha(path)
    return actual == declared_sha, {
        "status": "FRESH" if actual == declared_sha else "STALE",
        "path": path_text,
        "declared_git_blob_sha": declared_sha,
        "actual_git_blob_sha": actual,
    }


def _semantic_receipt_errors(
    receipt: Mapping[str, Any],
    current_claim: Mapping[str, Any] | None,
) -> list[str]:
    """Return fail-closed semantic-admission errors for one leaf receipt."""
    if not isinstance(current_claim, Mapping):
        return ["CURRENT_SEMANTIC_CLAIM_REQUIRED"]
    frozen = current_claim.get("frozen_claim")
    if not isinstance(frozen, Mapping):
        return ["CURRENT_SEMANTIC_FROZEN_CLAIM_REQUIRED"]

    checks = (
        (receipt.get("semantic_claim_id") == frozen.get("claim_id"), "SEMANTIC_CLAIM_ID_MISMATCH"),
        (receipt.get("semantic_scope_sha256") == frozen.get("scope_sha256"), "SEMANTIC_SCOPE_BINDING_MISMATCH"),
        (receipt.get("semantic_target_predicate_sha256") == frozen.get("target_predicate_sha256"), "SEMANTIC_TARGET_BINDING_MISMATCH"),
        (receipt.get("semantic_semantics_sha256") == frozen.get("semantics_sha256"), "SEMANTIC_SEMANTICS_BINDING_MISMATCH"),
        (receipt.get("claim_scoped_totality_proved") is True, "CLAIM_SCOPED_TOTALITY_NOT_PROVED"),
        (receipt.get("cc_r1_reality_containment_proved") is True, "CC_R1_NOT_PROVED"),
        (receipt.get("cc_r2_mission_soundness_proved") is True, "CC_R2_NOT_PROVED"),
        (receipt.get("cc_r3_terminal_closure_proved") is True, "CC_R3_NOT_PROVED"),
        (receipt.get("r4_proof_realization_authority") is True, "R4_NOT_PROVED"),
    )
    return [error for ok, error in checks if not ok]


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
    semantic_claim: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    path_text = entry.get("path")
    declared_sha = entry.get("git_blob_sha")
    fresh, file_record = _check_content_addressed_file(
        repo_root=repo_root,
        path_text=path_text,
        declared_sha=declared_sha,
    )
    result = {
        "leaf_id": leaf_id,
        "root_id": root_id,
        "kind": kind,
        "path": path_text,
        "declared_git_blob_sha": declared_sha,
        "admitted": False,
        "errors": [],
    }
    if not fresh:
        result["errors"].append("RECEIPT_FILE_NOT_CURRENT")
        result["file_record"] = file_record
        return result

    receipt_path = _resolve(repo_root, path_text)
    assert receipt_path is not None
    try:
        receipt = _load(receipt_path)
    except Exception:
        result["errors"].append("RECEIPT_JSON_INVALID")
        return result

    checks = (
        (receipt.get("schema") == RECEIPT_SCHEMA, "RECEIPT_SCHEMA_INVALID"),
        (receipt.get("leaf_id") == leaf_id, "LEAF_ID_MISMATCH"),
        (receipt.get("root_id") == root_id, "ROOT_ID_MISMATCH"),
        (receipt.get("leaf_kind") == kind, "LEAF_KIND_MISMATCH"),
        (receipt.get("verdict") == "PASS", "VERDICT_NOT_PASS"),
        (receipt.get("closure_scope") == "EXACT_LEAF", "CLOSURE_SCOPE_INVALID"),
        (
            receipt.get("acceptance_sha256") == semantic_sha(acceptance),
            "ACCEPTANCE_BINDING_MISMATCH",
        ),
        (
            receipt.get("root_contract_sha256") == semantic_sha(contract),
            "ROOT_CONTRACT_BINDING_MISMATCH",
        ),
        (
            receipt.get("manifest_git_blob_sha") == manifest_blob_sha,
            "MANIFEST_BINDING_MISMATCH",
        ),
        (
            receipt.get("terminal_authority") is False,
            "RECEIPT_TERMINAL_AUTHORITY_INVALID",
        ),
    )
    for ok, error in checks:
        if not ok:
            result["errors"].append(error)

    if kind == "SEMANTIC":
        if receipt.get("leaf_semantic_satisfied") is not True:
            result["errors"].append("SEMANTIC_SATISFACTION_NOT_PROVED")
        result["errors"].extend(_semantic_receipt_errors(receipt, semantic_claim))
    elif kind == "EXECUTION":
        if receipt.get("leaf_execution_satisfied") is not True:
            result["errors"].append("EXECUTION_SATISFACTION_NOT_PROVED")

    basis = receipt.get("verification_basis")
    if not isinstance(basis, list) or not basis:
        result["errors"].append("VERIFICATION_BASIS_REQUIRED")
        basis = []
    basis_records = []
    for item in basis:
        if not isinstance(item, dict):
            result["errors"].append("VERIFICATION_BASIS_ENTRY_INVALID")
            continue
        ok, record = _check_content_addressed_file(
            repo_root=repo_root,
            path_text=item.get("path"),
            declared_sha=item.get("git_blob_sha"),
        )
        basis_records.append(record)
        if not ok:
            result["errors"].append("VERIFICATION_BASIS_NOT_CURRENT")

    result["basis_records"] = basis_records
    result["admitted"] = not result["errors"]
    return result


def evaluate(
    *,
    manifest_path: Path = MANIFEST,
    graph_path: Path = GRAPH,
    registry_path: Path = REGISTRY,
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    manifest = _load(manifest_path)
    graph = _load(graph_path)
    registry = _load(registry_path)

    structural_errors: list[str] = []
    expected_roots = set(graph.get("root_ids") or [])
    rows = manifest.get("roots") or []
    seen_roots = {row.get("root_id") for row in rows}

    if manifest.get("root_count") != 12:
        structural_errors.append("ROOT_COUNT_INVALID")
    if manifest.get("semantic_leaf_count") != 12:
        structural_errors.append("SEMANTIC_LEAF_COUNT_INVALID")
    if manifest.get("execution_leaf_count") != 12:
        structural_errors.append("EXECUTION_LEAF_COUNT_INVALID")
    if manifest.get("total_leaf_count") != 24:
        structural_errors.append("TOTAL_LEAF_COUNT_INVALID")
    if seen_roots != expected_roots:
        structural_errors.append("ROOT_SET_MISMATCH")
    if registry.get("schema") != "PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_V1":
        structural_errors.append("REGISTRY_SCHEMA_INVALID")
    if registry.get("receipt_schema") != RECEIPT_SCHEMA:
        structural_errors.append("REGISTRY_RECEIPT_SCHEMA_INVALID")

    manifest_blob_sha = git_blob_sha(manifest_path)
    graph_blob_sha = git_blob_sha(graph_path)
    reg_manifest = registry.get("manifest") or {}
    reg_graph = registry.get("graph") or {}
    if reg_manifest.get("git_blob_sha") != manifest_blob_sha:
        structural_errors.append("REGISTRY_MANIFEST_BINDING_STALE")
    if reg_graph.get("git_blob_sha") != graph_blob_sha:
        structural_errors.append("REGISTRY_GRAPH_BINDING_STALE")

    leaf_receipts = registry.get("leaf_receipts")
    if not isinstance(leaf_receipts, dict):
        structural_errors.append("LEAF_RECEIPTS_NOT_OBJECT")
        leaf_receipts = {}

    semantic_claims: dict[str, Mapping[str, Any]] = {}
    semantic_receipts_present = any(
        isinstance(leaf_id, str)
        and leaf_id.endswith("::SEMANTIC")
        and isinstance(entries, list)
        and bool(entries)
        for leaf_id, entries in leaf_receipts.items()
    )
    if semantic_receipts_present:
        try:
            semantic_pack = semantic_pack_v3.verify(repo_root=repo_root)
        except Exception as exc:
            semantic_pack = {"pass": False, "reason": type(exc).__name__ + ":" + str(exc)}
        if semantic_pack.get("pass") is not True:
            structural_errors.append("CURRENT_SEMANTIC_CLAIM_PACK_NOT_PASS")
        else:
            for claim in semantic_pack.get("claims") or []:
                if isinstance(claim, Mapping) and isinstance(claim.get("leaf_id"), str):
                    semantic_claims[claim["leaf_id"]] = claim

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
            ok, rec = _check_content_addressed_file(
                repo_root=repo_root,
                path_text=ev.get("path") if isinstance(ev, dict) else None,
                declared_sha=ev.get("git_blob_sha") if isinstance(ev, dict) else None,
            )
            existing_evidence_records.append({
                "root_id": root_id,
                **rec,
            })
            if not ok:
                existing_evidence_current = False

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
                    results.append({
                        "leaf_id": leaf_id,
                        "root_id": root_id,
                        "kind": kind,
                        "admitted": False,
                        "errors": ["REGISTRY_ENTRY_INVALID"],
                    })
                    continue
                results.append(_receipt_result(
                    repo_root=repo_root,
                    entry=entry,
                    leaf_id=leaf_id,
                    root_id=str(root_id),
                    kind=kind,
                    acceptance=leaf.get("acceptance") or "",
                    contract=contract,
                    manifest_blob_sha=manifest_blob_sha,
                    semantic_claim=(semantic_claims.get(leaf_id) if kind == "SEMANTIC" else None),
                ))
            receipt_results.extend(results)

            admitted = any(x.get("admitted") is True for x in results)
            if admitted:
                verified_sink.append(leaf_id)
            else:
                open_sink.append(leaf_id)
                if leaf.get("status") == "VERIFIED":
                    declared_verified_without_receipt.append(leaf_id)

    unknown_registry_leaf_ids = sorted(set(leaf_receipts) - expected_leaf_ids)
    if unknown_registry_leaf_ids:
        structural_errors.append("REGISTRY_UNKNOWN_LEAF_IDS")

    rejected_receipts = [x for x in receipt_results if x.get("admitted") is not True]
    all_leaves_verified = len(verified_semantic) == 12 and len(verified_execution) == 12
    receipt_set_clean = not rejected_receipts
    promotion_ready = (
        not structural_errors
        and existing_evidence_current
        and receipt_set_clean
        and all_leaves_verified
        and manifest.get("terminal_authority") is False
        and registry.get("terminal_authority") is False
    )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__ALL_24_LEAVES_DERIVED_FROM_SCOPE_MATCHED_RECEIPTS"
            if promotion_ready
            else "OPEN__LEAF_RECEIPTS_OR_EVIDENCE_REMAIN"
        ),
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
