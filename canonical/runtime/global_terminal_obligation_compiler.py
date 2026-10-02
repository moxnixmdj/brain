#!/usr/bin/env python3
"""Compile Project Brain terminal state into a finite typed obligation graph.

Fail-closed rules:
- every open family must map to one or more known complete behavioral contracts;
- every mapped residual must exist in the active registry;
- all schema-required behavior fields must be present/nonempty;
- family ownership status determines whether the family terminal hole is proof-only
  or still contains a mechanism gap;
- target-basis completeness remains a specification hole until a separate exhaustive
  coverage proof closes it. Structural mapping alone may not self-certify completeness.

The output is intended to be the canonical finite input substrate for evidence
saturation, deductive closure, and the exact minimum-reality-cut solver.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_BEHAVIOR_FIELDS = (
    "behavior_id",
    "inputs",
    "environment_state",
    "allowed_information",
    "required_output_or_action",
    "success_condition",
    "failure_condition",
    "terminal_consequence",
    "verification_route",
    "dependency_boundary",
    "scope",
)

PROOF_ONLY_FAMILY_STATUS = {"BRAIN_CONFIGURED_VERIFICATION_PENDING"}
MECHANISM_GAP_FAMILY_STATUS = {
    "EXTERNAL_CAPABILITY_SPECIMEN_FOUND",
    "OWNED_COMPONENT_NOT_FULL_FAMILY",
}


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def compile_graph(
    manifest: dict[str, Any],
    registry: dict[str, Any],
    *,
    manifest_sha: str | None = None,
    registry_sha: str | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    families = manifest.get("families")
    if not isinstance(families, list):
        families = []
        errors.append("MANIFEST_FAMILIES_NOT_LIST")

    residuals = registry.get("active_contracted_residuals")
    if not isinstance(residuals, list):
        residuals = []
        errors.append("REGISTRY_ACTIVE_RESIDUALS_NOT_LIST")

    family_map = registry.get("family_to_residual_contracts")
    if not isinstance(family_map, dict):
        family_map = {}
        errors.append("REGISTRY_FAMILY_MAP_NOT_OBJECT")

    residual_by_id: dict[str, dict[str, Any]] = {}
    for i, residual in enumerate(residuals):
        if not isinstance(residual, dict):
            errors.append(f"RESIDUAL_{i}_MALFORMED")
            continue
        rid = residual.get("behavior_id")
        if not isinstance(rid, str) or not rid.strip():
            errors.append(f"RESIDUAL_{i}_ID_INVALID")
            continue
        rid = rid.strip()
        if rid in residual_by_id:
            errors.append(f"DUPLICATE_RESIDUAL:{rid}")
            continue
        residual_by_id[rid] = residual
        for field in REQUIRED_BEHAVIOR_FIELDS:
            if not _nonempty(residual.get(field)):
                errors.append(f"INCOMPLETE_BEHAVIOR_CONTRACT:{rid}:{field}")

    family_by_id: dict[str, dict[str, Any]] = {}
    for i, family in enumerate(families):
        if not isinstance(family, dict):
            errors.append(f"FAMILY_{i}_MALFORMED")
            continue
        fid = family.get("id")
        if not isinstance(fid, str) or not fid.strip():
            errors.append(f"FAMILY_{i}_ID_INVALID")
            continue
        fid = fid.strip()
        if fid in family_by_id:
            errors.append(f"DUPLICATE_FAMILY:{fid}")
            continue
        family_by_id[fid] = family

    open_ids = sorted(
        fid for fid, family in family_by_id.items()
        if family.get("closure_state") != "PASS"
    )
    closed_ids = sorted(
        fid for fid, family in family_by_id.items()
        if family.get("closure_state") == "PASS"
    )

    if manifest.get("expected_family_count") != 19 or len(families) != 19:
        errors.append("TARGET_FAMILY_COUNT_NOT_EXACTLY_19")

    for fid in open_ids:
        mapped = family_map.get(fid)
        if not isinstance(mapped, list) or not mapped:
            errors.append(f"OPEN_FAMILY_UNMAPPED:{fid}")
            continue
        for rid in mapped:
            if rid not in residual_by_id:
                errors.append(f"FAMILY_REFERENCES_UNKNOWN_RESIDUAL:{fid}:{rid}")

    unknown_family_mappings = sorted(set(family_map) - set(family_by_id))
    for fid in unknown_family_mappings:
        errors.append(f"MAPPING_FOR_UNKNOWN_FAMILY:{fid}")

    nodes: list[dict[str, Any]] = []

    nodes.append({
        "id": "GLOBAL_BEHAVIOR_BASIS_COMPLETENESS_001",
        "kind": "SPECIFICATION_GATE",
        "hole_type": "?S",
        "status": "OPEN",
        "reason": (
            "All open families may be structurally mapped, but the terminal manifest "
            "still does not prove exhaustive atomic behavioral completeness."
        ),
        "closes_when": [
            "every_required_behavior_contracted == true",
            "uncontracted_required_behaviors == 0",
            "coverage proof demonstrates no target behavior is omitted by the residual basis",
        ],
        "dependencies": [],
        "affected_families": open_ids,
    })

    terminal_residual_ids = sorted({
        rid
        for fid in open_ids
        for rid in (family_map.get(fid) if isinstance(family_map.get(fid), list) else [])
    })
    supporting_residual_ids = sorted(set(residual_by_id) - set(terminal_residual_ids))

    for rid in terminal_residual_ids:
        residual = residual_by_id[rid]
        mechanism_state = residual.get("mechanism_state")
        remaining_scope = residual.get("remaining_scope")
        full_owned = (
            isinstance(mechanism_state, str)
            and mechanism_state.startswith("VERIFIED_BRAIN_OWNED")
            and not remaining_scope
        )
        node = {
            "id": f"RESIDUAL::{rid}",
            "kind": "BEHAVIORAL_RESIDUAL",
            "hole_type": "?P" if full_owned else "?M",
            "status": "OPEN",
            "behavior_id": rid,
            "mechanism_state": mechanism_state,
            "mechanism_artifact": residual.get("mechanism_artifact"),
            "remaining_scope": remaining_scope,
            "verification_route": residual.get("verification_route"),
            "dependency_boundary": residual.get("dependency_boundary"),
            "dependencies": ["GLOBAL_BEHAVIOR_BASIS_COMPLETENESS_001"],
            "affected_families": sorted(
                fid for fid in open_ids
                if isinstance(family_map.get(fid), list) and rid in family_map[fid]
            ),
        }
        nodes.append(node)

    for fid in open_ids:
        family = family_by_id[fid]
        ownership = family.get("ownership_status")
        if ownership not in PROOF_ONLY_FAMILY_STATUS | MECHANISM_GAP_FAMILY_STATUS:
            errors.append(f"UNKNOWN_OPEN_FAMILY_OWNERSHIP_STATUS:{fid}:{ownership}")
        mapped = family_map.get(fid) if isinstance(family_map.get(fid), list) else []
        nodes.append({
            "id": f"FAMILY::{fid}",
            "kind": "FAMILY_ACCEPTANCE",
            "hole_type": "?P",
            "status": "OPEN",
            "ownership_status": ownership,
            "acceptance_basis": family.get("acceptance_basis"),
            "unresolved": family.get("unresolved"),
            "dependencies": [
                "GLOBAL_BEHAVIOR_BASIS_COMPLETENESS_001",
                *[f"RESIDUAL::{rid}" for rid in mapped],
            ],
            "affected_families": [fid],
        })

    family_nodes = [f"FAMILY::{fid}" for fid in open_ids]
    nodes.extend([
        {
            "id": "GLOBAL_COMPOSITION_CLOSURE_001",
            "kind": "TERMINAL_PROOF",
            "hole_type": "?P",
            "status": "OPEN",
            "dependencies": family_nodes,
            "closes_when": [
                "unresolved_composition_failures == 0",
                "unresolved_composition_failures_zero == true",
            ],
        },
        {
            "id": "GLOBAL_DONOR_DELETION_CLEANROOM_001",
            "kind": "TERMINAL_PROOF",
            "hole_type": "?P",
            "status": "OPEN",
            "dependencies": ["GLOBAL_COMPOSITION_CLOSURE_001", *family_nodes],
            "closes_when": [
                "donor_dependent_required_behaviors == 0",
                "donor_dependent_required_behaviors_zero == true",
                "final_donor_deletion_cleanroom_pass == true",
            ],
        },
        {
            "id": "GLOBAL_PROOF_BUNDLE_FREEZE_001",
            "kind": "TERMINAL_PROOF",
            "hole_type": "?P",
            "status": "OPEN",
            "dependencies": ["GLOBAL_DONOR_DELETION_CLEANROOM_001"],
            "closes_when": [
                "every_required_behavior_has_admissible_proof == true",
                "all_frozen_opus_acceptance_predicates_pass == true",
                "proof_bundle_frozen == true",
            ],
        },
    ])

    node_ids = [n["id"] for n in nodes]
    if len(node_ids) != len(set(node_ids)):
        errors.append("DUPLICATE_OBLIGATION_NODE_ID")
    known_nodes = set(node_ids)
    for node in nodes:
        for dep in node.get("dependencies", []):
            if dep not in known_nodes:
                errors.append(f"DANGLING_OBLIGATION_DEPENDENCY:{node['id']}:{dep}")

    hole_counts = {"?S": 0, "?M": 0, "?P": 0}
    for node in nodes:
        ht = node.get("hole_type")
        if ht in hole_counts:
            hole_counts[ht] += 1

    result = {
        "schema": "PROJECT_BRAIN_GLOBAL_TERMINAL_OBLIGATION_GRAPH_V1",
        "status": "FAIL_CLOSED_INVALID" if errors else "COMPILED_FAIL_CLOSED",
        "source": {
            "terminal_manifest_sha": manifest_sha,
            "behavioral_registry_sha": registry_sha,
        },
        "counts": {
            "target_families": len(families),
            "closed_families": len(closed_ids),
            "open_families": len(open_ids),
            "active_residual_contracts": len(residual_by_id),
            "terminal_residual_contracts": len(terminal_residual_ids),
            "supporting_nonterminal_residual_contracts": len(supporting_residual_ids),
            "obligation_nodes": len(nodes),
            "hole_types": hole_counts,
        },
        "closed_families": closed_ids,
        "open_families": open_ids,
        "terminal_residual_ids": terminal_residual_ids,
        "supporting_nonterminal_residual_ids": supporting_residual_ids,
        "structural_mapping_complete": not any(
            e.startswith("OPEN_FAMILY_UNMAPPED:")
            or e.startswith("FAMILY_REFERENCES_UNKNOWN_RESIDUAL:")
            for e in errors
        ),
        "semantic_basis_complete": False,
        "minimum_reality_cut_ready": False,
        "minimum_reality_cut_blockers": [
            "GLOBAL_BEHAVIOR_BASIS_COMPLETENESS_001",
            "EXISTING_EVIDENCE_SATURATION_NOT_COMPILED_TO_NODE_STATES",
            "DEDUCTIVE_AND_COUNTERFACTUAL_CLOSURE_NOT_APPLIED_TO_ALL_OPEN_NODES",
            "CANDIDATE_IRREDUCIBLE_OBSERVATIONS_NOT_YET_DECLARED_WITH_COVERAGE_AND_COST",
        ],
        "nodes": nodes,
        "errors": sorted(set(errors)),
        "rule": (
            "ONLY RESIDUALS REFERENCED BY OPEN-FAMILY COVERAGE ARE TERMINAL BASIS NODES; "
            "SUPPORTING NARROW CONTRACTS ARE PRESERVED WITHOUT OVERCONSTRAINING TERMINAL CLOSURE; "
            "FAMILY NODES ARE PROOF-ONLY BECAUSE MECHANISM GAPS LIVE IN RESIDUAL DEPENDENCIES; "
            "STRUCTURAL MAPPING IS NOT TERMINAL SEMANTIC COMPLETENESS; "
            "NO FRESH REALITY QUERY IS AUTHORIZED BY THIS GRAPH ALONE"
        ),
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("registry", type=Path)
    ap.add_argument("--manifest-sha")
    ap.add_argument("--registry-sha")
    args = ap.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    result = compile_graph(
        manifest,
        registry,
        manifest_sha=args.manifest_sha,
        registry_sha=args.registry_sha,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
