#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BRIDGE = "canonical/governance/COMPOSITION_ARTIFACT_CREATION_SCOPE_COMPLETE_BRIDGE_V1.json"
PROTOCOLS = "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
MANIFEST = "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json"
REGISTRY = "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
PARTITION = "canonical/verification/ARTIFACT_UNCOVERED_SCOPE_PARTITION_PROOF_20261002_V1.json"
LEDGER = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"

EXPECTED = {
    PROTOCOLS: "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    MANIFEST: "9efbf3e81e67fbd15e34be2fcd86fbfc626b246d",
    REGISTRY: "ee187f611a0e82b2de495ee377682f39bc31dd31",
    PARTITION: "11aaa9915906511acf9f8a48e02b993b670fe44d",
    LEDGER: "a3fd20e58fdbd9b86278b7de0c245de3063dce27",
}


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def git_blob_sha(rel: str) -> str:
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def normalize_literal(value: str) -> str:
    return value.upper().replace(" ", "_")


def main() -> int:
    bridge = load(BRIDGE)
    protocols = load(PROTOCOLS)
    manifest = load(MANIFEST)
    registry = load(REGISTRY)
    partition = load(PARTITION)
    ledger = load(LEDGER)

    # Independent content-address check: verifier owns these expected source identities.
    for path, expected in EXPECTED.items():
        actual = git_blob_sha(path)
        assert actual == expected, (path, actual, expected)
        declared = next(
            x["git_blob_sha"]
            for x in bridge["authority"].values()
            if x["path"] == path
        )
        assert declared == expected, (path, declared, expected)

    composition = next(
        p for p in protocols["protocols"]
        if p["family"] == "MULTI_CAPABILITY_COMPOSITION"
    )
    dimensions = composition["task_dimensions"]
    literal = "artifact creation"
    interface = "research+tool use+artifact creation"

    # Exact literal membership only. No semantic/synonym transport.
    assert interface in dimensions
    tokens = [token for dim in dimensions for token in dim.split("+")]
    assert literal in tokens
    assert "artifact production" in tokens
    assert literal != "artifact production"
    assert normalize_literal(literal) == "ARTIFACT_CREATION"

    rows = [
        row for row in manifest["interfaces"]
        if row["component_id"] == literal
    ]
    assert len(rows) == 1
    row = rows[0]
    assert row["interface_id"] == interface
    assert row["source_component_literal"] == literal
    assert row["required_properties"] == ["SCOPED_ACCEPTANCE_PROOF"]
    assert row["family_binding"] is None
    assert row["receipt_binding"] is None

    expected_contracts = {
        "NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001",
        "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
    }
    family_contracts = set(
        registry["family_to_residual_contracts"]["ARTIFACT_CREATION"]
    )
    partition_contracts = {
        x["contract"] for x in partition["frozen_contract_partition"]
    }
    assert family_contracts == expected_contracts
    assert partition_contracts == expected_contracts
    assert family_contracts == partition_contracts
    assert partition["no_uncovered_contracted_leaf"] is True
    assert partition["status"].startswith(
        "PASS__FROZEN_CONTRACTED_ARTIFACT_SCOPE_PARTITIONS_COMPLETELY"
    )

    exclusions = set(partition["exclusions"])
    assert "DOES_NOT_ASSERT_BRAIN_MEETS_AA_BRIEFCASE_1822_ELO" in exclusions
    assert "DOES_NOT_INHERIT_PUBLIC_BAR_PERFORMANCE_CREDIT" in exclusions

    proof = next(
        x for x in ledger["claims"]
        if x.get("predicate_id") == "ARTIFACT_UNCOVERED_FORMAT_SCOPE_AUDIT"
    )
    assert proof["state"] == "PROVED"
    assert proof["scope_complete"] is True
    assert proof["independent_or_objective"] is True
    assert proof["source_path"] == PARTITION
    assert proof["source_sha"] == EXPECTED[PARTITION]
    assert "ZERO" in proof["performance_credit"]

    # Verify bridge is exactly the narrow claim the sources support.
    binding = bridge["component_binding"]
    assert binding["component_id"] == literal
    assert binding["interface_id"] == interface
    assert binding["normalized_component_id"] == "ARTIFACT_CREATION"
    assert binding["proved_properties_after_independent_verification"] == [
        "SCOPED_ACCEPTANCE_PROOF"
    ]

    guard = bridge["scope_guard"]
    assert "ARTIFACT_PRODUCTION_COMPONENT" in guard["excluded"]
    assert "AA_BRIEFCASE_GE_1822_PERFORMANCE" in guard["excluded"]
    assert "GENERAL_MULTI_CAPABILITY_COMPOSITION_INTERACTION_SUCCESS" in guard["excluded"]
    assert "CROSS_CAPABILITY_STATE_HANDOFF_AND_ROLLBACK" in guard["excluded"]

    effect = bridge["expected_effect_after_independent_verification"]
    assert effect["current_composition_scoped_proved_components_before"] == 4
    assert effect["projected_scoped_proved_components_after"] == 5
    assert effect["projected_open_components_after"] == 7
    assert effect["parent_component_dependency_predicate_closed"] is False
    assert effect["parent_composition_predicate_closed"] is False
    assert effect["strict_opus55_acceptance_delta"] == 0

    assert bridge["acceptance_credit_delta"] == 0
    assert bridge["family_credit_delta"] == 0
    assert bridge["capability_credit_delta"] == 0
    assert bridge["ownership_credit_delta"] == 0
    assert bridge["execution_authority"] is False
    assert bridge["promotion_authority"] is False
    assert bridge["fresh_reality_authority"] is False

    print("INDEPENDENT_COMPOSITION_ARTIFACT_CREATION_BRIDGE_VERIFIER_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
