#!/usr/bin/env python3
"""Fail-closed verifier for the five-public-bar observable-target scope reduction.

This verifier checks only deterministic repository relations. It does not award
performance, family, capability, or ownership credit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

PATHS = {
    "candidate": "canonical/governance/FIVE_PUBLIC_BAR_OBSERVABLE_TARGET_SCOPE_CLOSURE_REDUCTION_20261005_V1.json",
    "envelope": "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json",
    "task_union": "canonical/governance/PUBLIC_BAR_TASK_UNION_SCOPE_COVERAGE_AUDIT_20261005_V1.json",
    "guard": "canonical/governance/TARGET_BEHAVIOR_MECHANISM_SCOPE_SEPARATION_20261005_V1.json",
    "bindings": "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json",
    "target_conditioned": "canonical/verification/PUBLIC_BAR_TASK_UNION_TARGET_CONDITIONED_RESIDUAL_RECONCILIATION_CONNECTOR_VERIFICATION_20261005_V1.json",
}

EXPECTED_FAMILIES = {
    "ADVANCED_AGENTIC_CODING",
    "PROFESSIONAL_KNOWLEDGE_WORK",
    "BUSINESS_WORKFLOW_AUTOMATION",
    "MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING",
    "AGENTIC_SCIENTIFIC_RESEARCH",
}


def load_json(root: Path, rel: str) -> dict[str, Any]:
    with (root / rel).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def sha256_file(root: Path, rel: str) -> str:
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify(root: Path = ROOT) -> dict[str, Any]:
    docs = {k: load_json(root, v) for k, v in PATHS.items()}
    candidate = docs["candidate"]
    envelope = docs["envelope"]
    task_union = docs["task_union"]
    guard = docs["guard"]
    bindings = docs["bindings"]
    target_conditioned = docs["target_conditioned"]

    families = candidate["families"]
    family_ids = {f["family"] for f in families}
    require(family_ids == EXPECTED_FAMILIES, f"family set mismatch: {family_ids!r}")

    envelope_map = {f["id"]: f for f in envelope["families"]}
    audit_map = {m["family"]: m for m in task_union["mappings"]}
    claim_map = {c["predicate_id"]: c for c in bindings["claims"]}
    guard_edges = {
        (e["family"], e["behavior_id"]): e
        for e in guard["current_frontier_audit"]["edges"]
    }

    checks: list[str] = []
    for family in families:
        fid = family["family"]
        require(fid in envelope_map, f"{fid}: missing envelope family")
        require(fid in audit_map, f"{fid}: missing task-union mapping")
        require(
            family["frozen_useful_behavior"] == envelope_map[fid]["useful_behavior"],
            f"{fid}: frozen useful_behavior drift",
        )
        checks.append(f"{fid}:exact_frozen_useful_behavior")

        audit_ids = [leaf["id"] for leaf in audit_map[fid]["leaves"]]
        require(
            family["audit_basis_leaf_ids"] == audit_ids,
            f"{fid}: audit leaf basis mismatch",
        )
        checks.append(f"{fid}:exact_task_union_leaf_basis")

        require(
            family.get("structural_scope_residuals") == [],
            f"{fid}: structural_scope_residuals is not empty",
        )
        require(
            bool(family.get("remaining_load_bearing")),
            f"{fid}: performance/target-identity obligations were accidentally deleted",
        )
        checks.append(f"{fid}:performance_obligations_preserved")

        for receipt in family.get("stronger_observable_receipts", []):
            pid = receipt["predicate"]
            require(pid in claim_map, f"{fid}: missing stronger receipt {pid}")
            claim = claim_map[pid]
            require(claim.get("state") == "PROVED", f"{fid}: {pid} not PROVED")
            require(claim.get("scope_complete") is True, f"{fid}: {pid} not scope complete")
            checks.append(f"{fid}:proved_stronger_receipt:{pid}")

        for behavior_id in family.get("nonmandatory_mechanisms", []):
            edge = guard_edges.get((fid, behavior_id))
            require(edge is not None, f"{fid}: guard edge missing for {behavior_id}")
            require(
                edge.get("mandatory_from_registry_incidence") is False,
                f"{fid}: {behavior_id} is mandatory under active guard",
            )
            checks.append(f"{fid}:nonmandatory_guard_edge:{behavior_id}")

    tc_checks = target_conditioned["checks"]
    require(
        tc_checks["mandatory_new_behavioral_residual_count_after_target_conditioning"] == 0,
        "target-conditioned reconciliation has nonzero mandatory new residuals",
    )
    checks.append("target_conditioned_new_mandatory_residuals_zero")

    require(candidate["aggregate"]["public_performance_predicates_deleted"] == 0,
            "candidate deletes public performance predicates")
    require(candidate["aggregate"]["target_epoch_or_harness_guards_deleted"] == 0,
            "candidate deletes target epoch/harness guards")
    require(candidate["accounting"]["acceptance_credit_delta"] == 0,
            "candidate grants acceptance credit")
    require(candidate["accounting"]["family_credit_delta"] == 0,
            "candidate grants family credit")
    require(candidate["accounting"]["capability_credit_delta"] == 0,
            "candidate grants capability credit")
    require(candidate["accounting"]["ownership_credit_delta"] == 0,
            "candidate grants ownership credit")
    checks.append("zero_credit_and_target_guards_preserved")

    multi = envelope_map["MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING"]["useful_behavior"].lower()
    sci = envelope_map["AGENTIC_SCIENTIFIC_RESEARCH"]["useful_behavior"].lower()
    biz = envelope_map["BUSINESS_WORKFLOW_AUTOMATION"]["useful_behavior"].lower()
    require("multimodal" not in multi, "multidisciplinary frozen target explicitly says multimodal")
    require("hypothesis" not in sci and "communication" not in sci,
            "scientific frozen target explicitly adds hypothesis/communication")
    require("browser" not in biz and "visual" not in biz,
            "business frozen target explicitly adds browser/visual grounding")
    checks.append("negative_literal_target_checks")

    return {
        "schema": "FIVE_PUBLIC_BAR_OBSERVABLE_TARGET_SCOPE_CLOSURE_VERIFIER_V1",
        "status": "PASS",
        "family_count": len(families),
        "check_count": len(checks),
        "checks": checks,
        "source_sha256": {k: sha256_file(root, v) for k, v in PATHS.items()},
        "acceptance_credit_delta": 0,
        "fresh_reality_units_consumed": 0,
    }


def main() -> None:
    print(json.dumps(verify(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
