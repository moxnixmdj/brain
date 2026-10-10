"""Project bounded professional-quality scoped evidence onto the 24 global leaves.

Frontier/accounting only. Bounded scoped capabilities may reduce an uncovered
leaf region, but they never close the global leaf by themselves.

Whole-leaf closure remains owned by the existing leaf binder and requires either
an exact scope-matched receipt, independently verified same-or-broader scope
transport, or a certified complete union of scoped regions.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from canonical.runtime import professional_quality_scoped_evidence_v1 as scoped

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json"

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_COVERAGE_PROJECTION_V1"
VERIFIED_SUPERSET_SCOPE_PREDICATE = "STRUCTURAL_MATCH_V1"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def project(
    *,
    manifest_path: Path = MANIFEST,
    scoped_registry_path: Path = scoped.REGISTRY,
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    manifest = _load(manifest_path)
    scoped_out = scoped.evaluate(
        registry_path=scoped_registry_path,
        repo_root=repo_root,
    )
    structural_errors: list[str] = []

    rows = manifest.get("roots")
    if not isinstance(rows, list) or manifest.get("total_leaf_count") != 24:
        structural_errors.append("LEAF_MANIFEST_INVALID")
        rows = []

    leaf_meta: dict[str, dict[str, str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            structural_errors.append("LEAF_MANIFEST_ROW_INVALID")
            continue
        root_id = row.get("root_id")
        for kind, field in (("SEMANTIC", "semantic_leaf"), ("EXECUTION", "execution_leaf")):
            leaf = row.get(field)
            if not isinstance(leaf, dict):
                structural_errors.append(f"LEAF_MANIFEST_{kind}_INVALID:{root_id}")
                continue
            leaf_id = leaf.get("id")
            if not isinstance(leaf_id, str) or not leaf_id:
                structural_errors.append(f"LEAF_ID_INVALID:{root_id}:{kind}")
                continue
            if leaf_id in leaf_meta:
                structural_errors.append(f"DUPLICATE_LEAF_ID:{leaf_id}")
                continue
            leaf_meta[leaf_id] = {"root_id": str(root_id), "kind": kind}

    if len(leaf_meta) != 24:
        structural_errors.append("EXPECTED_24_LEAVES")

    if scoped_out.get("pass") is not True:
        structural_errors.append("SCOPED_EVIDENCE_NOT_ADMITTED")

    contributions: dict[str, list[dict[str, Any]]] = {
        leaf_id: [] for leaf_id in leaf_meta
    }
    unknown_contribution_leaf_ids: set[str] = set()

    for row in scoped_out.get("admitted_scopes") or []:
        if not isinstance(row, dict):
            structural_errors.append("SCOPED_RESULT_INVALID")
            continue
        if row.get("global_leaf_credit") is not False:
            structural_errors.append("SCOPED_GLOBAL_LEAF_CREDIT_FORBIDDEN")
        if row.get("semantic_leaf_credit") is not False:
            structural_errors.append("SCOPED_SEMANTIC_LEAF_CREDIT_FORBIDDEN")
        if row.get("execution_leaf_credit") is not False:
            structural_errors.append("SCOPED_EXECUTION_LEAF_CREDIT_FORBIDDEN")
        for leaf_id in row.get("contributes_to_leaf_ids") or []:
            if leaf_id not in leaf_meta:
                unknown_contribution_leaf_ids.add(str(leaf_id))
                continue
            contributions[leaf_id].append({
                "scope_id": row.get("scope_id"),
                "root_id": row.get("root_id"),
                "claim_kind": row.get("claim_kind"),
                "claim_scope": row.get("claim_scope"),
                "scope_relation_to_global_leaf": "BOUNDED_SUBSET_ONLY",
                "leaf_closure_credit": False,
                "terminal_credit_delta": 0,
            })

    if unknown_contribution_leaf_ids:
        structural_errors.append("UNKNOWN_CONTRIBUTION_LEAF_IDS")

    partial_leaf_ids = sorted(
        leaf_id for leaf_id, items in contributions.items() if items
    )
    no_scoped_evidence_leaf_ids = sorted(
        leaf_id for leaf_id, items in contributions.items() if not items
    )
    semantic_partial = sorted(
        leaf_id
        for leaf_id in partial_leaf_ids
        if leaf_meta[leaf_id]["kind"] == "SEMANTIC"
    )
    execution_partial = sorted(
        leaf_id
        for leaf_id in partial_leaf_ids
        if leaf_meta[leaf_id]["kind"] == "EXECUTION"
    )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__BOUNDED_SCOPE_COVERAGE_PROJECTED__ZERO_GLOBAL_LEAF_CREDIT"
            if not structural_errors
            else "FAIL_CLOSED__COVERAGE_PROJECTION_INVALID"
        ),
        "pass": not structural_errors,
        "structural_errors": sorted(set(structural_errors)),
        "expected_leaf_count": len(leaf_meta),
        "admitted_scoped_capability_count": scoped_out.get(
            "admitted_scope_count", 0
        ),
        "partial_coverage_leaf_count": len(partial_leaf_ids),
        "semantic_partial_coverage_leaf_count": len(semantic_partial),
        "execution_partial_coverage_leaf_count": len(execution_partial),
        "no_scoped_evidence_leaf_count": len(no_scoped_evidence_leaf_ids),
        "partial_coverage_leaf_ids": partial_leaf_ids,
        "semantic_partial_coverage_leaf_ids": semantic_partial,
        "execution_partial_coverage_leaf_ids": execution_partial,
        "no_scoped_evidence_leaf_ids": no_scoped_evidence_leaf_ids,
        "contributions_by_leaf": contributions,
        "unknown_contribution_leaf_ids": sorted(
            unknown_contribution_leaf_ids
        ),
        "verified_global_leaf_count": 0,
        "open_global_leaf_count": len(leaf_meta),
        "global_leaf_closure": False,
        "domain_semantic_closure": False,
        "domain_execution_closure": False,
        "promotion_rule": {
            "partial_scope_never_closes_leaf": True,
            "allowed_whole_leaf_routes": [
                "EXACT_SCOPE_MATCHED_LEAF_RECEIPT",
                "INDEPENDENTLY_VERIFIED_PROVEN_SUPERSET_WITH_STRUCTURAL_MATCH_V1",
                "CERTIFIED_COMPLETE_UNION_OF_SCOPED_REGIONS",
            ],
            "required_superset_scope_predicate": VERIFIED_SUPERSET_SCOPE_PREDICATE,
            "finite_declared_scope_replay_available": (
                "canonical/runtime/finite_symbolic_cover_replay_v1.py"
            ),
            "global_leaf_binder": (
                "canonical/runtime/professional_quality_leaf_binder_v2.py"
            ),
        },
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


if __name__ == "__main__":
    print(json.dumps(project(), indent=2, sort_keys=True))
