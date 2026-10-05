#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

P = {
    "batch": "canonical/governance/COMPOSITION_DUAL_SCOPE_BRIDGE_BATCH_V1.json",
    "authority": "canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json",
    "artifact_bridge": "canonical/governance/COMPOSITION_ARTIFACT_CREATION_SCOPE_COMPLETE_BRIDGE_V1.json",
    "synthesis_bridge": "canonical/governance/COMPOSITION_EVIDENCE_SYNTHESIS_SCOPE_COMPLETE_BRIDGE_V1.json",
    "protocols": "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json",
    "manifest": "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json",
    "registry": "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json",
    "ledger": "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json",
    "artifact_partition": "canonical/verification/ARTIFACT_UNCOVERED_SCOPE_PARTITION_PROOF_20261002_V1.json",
    "synth_cert": "canonical/governance/SYNTHESIS_SCOPE_CERTIFICATE_V1.json",
    "synth_verify": "canonical/verification/SYNTHESIS_LOSSLESS_SCOPE_DECOMPOSITION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
}

EXPECTED_BLOBS = {
    P["authority"]: "5bb089582a5bc2ee4a44143c8d3a11e919fecdff",
    P["artifact_bridge"]: "f400756e84284c5a6ce4971af61e544e9b2f94eb",
    P["synthesis_bridge"]: "000de52136566e33531e28d17973f0ced56f92aa",
    P["protocols"]: "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    P["manifest"]: "9efbf3e81e67fbd15e34be2fcd86fbfc626b246d",
    P["registry"]: "ee187f611a0e82b2de495ee377682f39bc31dd31",
    P["ledger"]: "a3fd20e58fdbd9b86278b7de0c245de3063dce27",
    P["artifact_partition"]: "11aaa9915906511acf9f8a48e02b993b670fe44d",
    P["synth_cert"]: "dea9028f92f111ee3c8be71615fa4b02e8a8bfb6",
    P["synth_verify"]: "1852516f725f5b72badfc2f65be22e542ed83623",
}

EXPECTED_SYNTH_DIMS = {
    "claim-to-source fidelity",
    "required evidence coverage",
    "uncertainty/disagreement preservation",
    "audience adaptation",
    "format/style constraints",
    "compression without decision-relevant loss",
}

def blob(path: str) -> str:
    b = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\\0" + b).hexdigest()

def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def test_dual_scope_bridge_batch_projects_exactly_six_of_twelve_zero_credit():
    for path, expected in EXPECTED_BLOBS.items():
        assert blob(path) == expected, (path, blob(path), expected)

    batch = load(P["batch"])
    authority = load(P["authority"])
    artifact_bridge = load(P["artifact_bridge"])
    synthesis_bridge = load(P["synthesis_bridge"])
    protocols = load(P["protocols"])
    manifest = load(P["manifest"])
    registry = load(P["registry"])
    ledger = load(P["ledger"])
    artifact_partition = load(P["artifact_partition"])
    synth_cert = load(P["synth_cert"])
    synth_verify = load(P["synth_verify"])

    assert authority["truth"]["current_admissible_scoped_proved"] == 4
    existing = set(authority["truth"]["current_scoped_proved_components"])
    assert existing == {"memory", "recovery", "delegation", "tool discovery"}
    assert authority["truth"]["current_open"] == 8

    comp = next(x for x in protocols["protocols"] if x["family"] == "MULTI_CAPABILITY_COMPOSITION")
    art_family = next(x for x in protocols["protocols"] if x["family"] == "ARTIFACT_CREATION")
    synth_family = next(x for x in protocols["protocols"] if x["family"] == "COMMUNICATION_AND_SYNTHESIS")
    assert "research+tool use+artifact creation" in comp["task_dimensions"]
    assert "delegation+evidence synthesis+artifact production" in comp["task_dimensions"]
    assert art_family["family"] == "ARTIFACT_CREATION"
    assert set(synth_family["task_dimensions"]) == EXPECTED_SYNTH_DIMS

    rows = {x["component_id"]: x for x in manifest["interfaces"]}
    for component in ("artifact creation", "evidence synthesis"):
        assert rows[component]["required_properties"] == ["SCOPED_ACCEPTANCE_PROOF"]

    expected_artifact_contracts = {
        "NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001",
        "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
    }
    assert set(registry["family_to_residual_contracts"]["ARTIFACT_CREATION"]) == expected_artifact_contracts
    assert {x["contract"] for x in artifact_partition["frozen_contract_partition"]} == expected_artifact_contracts
    assert artifact_partition["no_uncovered_contracted_leaf"] is True
    artifact_row = next(x for x in ledger["claims"] if x.get("predicate_id") == "ARTIFACT_UNCOVERED_FORMAT_SCOPE_AUDIT")
    assert artifact_row["state"] == "PROVED"
    assert artifact_row["scope_complete"] is True
    assert artifact_row["independent_or_objective"] is True
    assert "ZERO" in artifact_row["performance_credit"]

    assert registry["family_to_residual_contracts"]["COMMUNICATION_AND_SYNTHESIS"] == ["EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"]
    assert synth_cert["verified"] is True and synth_cert["independent"] is True
    assert synth_cert["scope_relation"] == "PROVEN_STRONGER"
    assert synth_cert["coverage_complete"] is True
    assert synth_cert["coverage_relation"] == "EXACT_UNION"
    assert len(synth_cert["children"]) == 6
    assert all(x["verified"] is True and x["independent"] is True for x in synth_cert["children"])
    assert all(x["formal_completeness"] is True and x["all_admissible_target_inputs_proved"] is True for x in synth_cert["children"])
    assert synth_verify["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
    assert synth_verify["verified"]["root3_scope_relation_closed"] is True
    assert synth_verify["verified"]["acceptance_closed"] is False

    assert artifact_bridge["candidate_receipt"]["component_id"] == "artifact creation"
    assert synthesis_bridge["candidate_receipt"]["component_id"] == "evidence synthesis"
    assert artifact_bridge["candidate_receipt"]["verified"] is False
    assert synthesis_bridge["candidate_receipt"]["verified"] is False
    assert artifact_bridge["candidate_receipt"]["independent"] is False
    assert synthesis_bridge["candidate_receipt"]["independent"] is False

    proposed = {"artifact creation", "evidence synthesis"}
    assert existing.isdisjoint(proposed)
    projected = existing | proposed
    all_components = {x["component_id"] for x in manifest["interfaces"]}
    assert len(all_components) == 12
    assert projected <= all_components
    assert len(projected) == 6
    assert len(all_components - projected) == 6

    joint = batch["joint_derivation"]
    assert set(joint["existing_components"]) == existing
    assert set(joint["newly_proposed_components"]) == proposed
    assert joint["scoped_proved_before"] == 4
    assert joint["scoped_proved_after_if_both_independently_verified"] == 6
    assert joint["open_after_if_both_independently_verified"] == 6
    assert joint["parent_component_dependency_predicate_closed"] is False
    assert joint["parent_composition_predicate_closed"] is False
    assert joint["strict_opus55_acceptance_delta"] == 0

    assert batch["acceptance_credit_delta"] == 0
    assert batch["family_credit_delta"] == 0
    assert batch["capability_credit_delta"] == 0
    assert batch["ownership_credit_delta"] == 0
    assert batch["execution_authority"] is False
    assert batch["promotion_authority"] is False
    assert batch["fresh_reality_authority"] is False
    assert batch["independent_verification_required"] is True
