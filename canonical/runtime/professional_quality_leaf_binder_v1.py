"""Professional-quality semantic/execution leaf binder.

This module makes the UVCK V2 domain promotion gate executable without
granting semantic or execution authority. It checks structure and evidence
freshness, then exposes the exact remaining semantic/execution leaves.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json"
GRAPH = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_ASSURANCE_GRAPH_20261009_V2.json"

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_BINDER_V1"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("utf-8")
    return sha1(header + data).hexdigest()


def load() -> tuple[dict[str, Any], dict[str, Any]]:
    return json.loads(MANIFEST.read_text()), json.loads(GRAPH.read_text())


def evaluate() -> dict[str, Any]:
    manifest, graph = load()
    expected_roots = set(graph.get("root_ids") or [])
    rows = manifest.get("roots") or []
    seen_roots = {row.get("root_id") for row in rows}
    structural_errors: list[str] = []
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

    leaf_ids: list[str] = []
    open_semantic: list[str] = []
    open_execution: list[str] = []
    evidence_rows: list[dict[str, Any]] = []
    stale_evidence: list[dict[str, Any]] = []
    missing_evidence: list[dict[str, Any]] = []

    for row in rows:
        rid = row.get("root_id")
        for kind, field, sink in (
            ("SEMANTIC", "semantic_leaf", open_semantic),
            ("EXECUTION", "execution_leaf", open_execution),
        ):
            leaf = row.get(field) or {}
            leaf_id = leaf.get("id")
            if not isinstance(leaf_id, str) or not leaf_id:
                structural_errors.append(f"{kind}_LEAF_ID_INVALID:{rid}")
                continue
            leaf_ids.append(leaf_id)
            if leaf.get("status") != "VERIFIED":
                sink.append(leaf_id)

        evidence = row.get("existing_evidence") or []
        if not evidence:
            structural_errors.append(f"NO_EXISTING_EVIDENCE:{rid}")
        for ev in evidence:
            path_text = ev.get("path")
            declared = ev.get("git_blob_sha")
            if not isinstance(path_text, str) or not path_text.startswith("canonical/"):
                structural_errors.append(f"EVIDENCE_PATH_INVALID:{rid}")
                continue
            path = ROOT / path_text
            if not path.exists():
                rec = {"root_id": rid, "path": path_text, "declared_git_blob_sha": declared}
                missing_evidence.append(rec)
                evidence_rows.append({**rec, "status": "MISSING"})
                continue
            actual = git_blob_sha(path)
            rec = {
                "root_id": rid,
                "path": path_text,
                "declared_git_blob_sha": declared,
                "actual_git_blob_sha": actual,
                "supports": ev.get("supports"),
            }
            if actual != declared:
                stale_evidence.append(rec)
                evidence_rows.append({**rec, "status": "STALE"})
            else:
                evidence_rows.append({**rec, "status": "FRESH"})

    if len(leaf_ids) != len(set(leaf_ids)):
        structural_errors.append("DUPLICATE_LEAF_ID")

    all_leaves_verified = not open_semantic and not open_execution
    evidence_current = not stale_evidence and not missing_evidence
    promotion_ready = (
        not structural_errors
        and all_leaves_verified
        and evidence_current
        and manifest.get("terminal_authority") is False
    )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__PROMOTION_INPUTS_STRUCTURALLY_READY"
            if promotion_ready
            else "OPEN__DOMAIN_LEAVES_OR_EVIDENCE_FRESHNESS_REMAIN"
        ),
        "pass": promotion_ready,
        "structural_errors": sorted(set(structural_errors)),
        "root_count": len(rows),
        "semantic_leaf_count": 12,
        "execution_leaf_count": 12,
        "open_semantic_leaf_ids": sorted(open_semantic),
        "open_execution_leaf_ids": sorted(open_execution),
        "open_leaf_count": len(open_semantic) + len(open_execution),
        "evidence_current": evidence_current,
        "fresh_evidence_count": sum(1 for x in evidence_rows if x["status"] == "FRESH"),
        "stale_evidence": stale_evidence,
        "missing_evidence": missing_evidence,
        "promotion_ready": promotion_ready,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
