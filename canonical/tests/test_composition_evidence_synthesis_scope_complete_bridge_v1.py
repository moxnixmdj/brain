#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BRIDGE = ROOT / "canonical/governance/COMPOSITION_EVIDENCE_SYNTHESIS_SCOPE_COMPLETE_BRIDGE_V1.json"
PROTOCOLS = ROOT / "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
MANIFEST = ROOT / "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json"
REGISTRY = ROOT / "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
CERT = ROOT / "canonical/governance/SYNTHESIS_SCOPE_CERTIFICATE_V1.json"
VERIFY = ROOT / "canonical/verification/SYNTHESIS_LOSSLESS_SCOPE_DECOMPOSITION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"

EXPECTED_DIMS = {
    "claim-to-source fidelity",
    "required evidence coverage",
    "uncertainty/disagreement preservation",
    "audience adaptation",
    "format/style constraints",
    "compression without decision-relevant loss",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    bridge = load(BRIDGE)
    protocols = load(PROTOCOLS)
    manifest = load(MANIFEST)
    registry = load(REGISTRY)
    cert = load(CERT)
    verification = load(VERIFY)

    composition = next(x for x in protocols["protocols"] if x["family"] == "MULTI_CAPABILITY_COMPOSITION")
    synthesis = next(x for x in protocols["protocols"] if x["family"] == "COMMUNICATION_AND_SYNTHESIS")

    assert "delegation+evidence synthesis+artifact production" in composition["task_dimensions"]
    comp_rows = [x for x in manifest["interfaces"] if x["component_id"] == "evidence synthesis"]
    assert len(comp_rows) == 1
    assert comp_rows[0]["interface_id"] == "delegation+evidence synthesis+artifact production"
    assert comp_rows[0]["required_properties"] == ["SCOPED_ACCEPTANCE_PROOF"]

    family_map = registry["family_to_residual_contracts"]["COMMUNICATION_AND_SYNTHESIS"]
    assert family_map == ["EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"]
    residual = next(
        x for x in registry["active_contracted_residuals"]
        if x["behavior_id"] == "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
    )
    assert residual["scope"] == "Grounded evidence synthesis under audience and format constraints"

    assert set(synthesis["task_dimensions"]) == EXPECTED_DIMS
    assert cert["verified"] is True
    assert cert["independent"] is True
    assert cert["scope_relation"] == "PROVEN_STRONGER"
    assert cert["coverage_complete"] is True
    assert cert["coverage_relation"] == "EXACT_UNION"
    assert cert["coverage_proof_verified"] is True
    assert cert["witness_scope_id"] == "scope://brain/EVIDENCE_TO_AUDIENCE_SYNTHESIS_001/T1_T3_TERMINAL"
    assert cert["target_scope_id"] == "scope://opus55/SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
    assert len(cert["children"]) == 6
    assert all(x["verified"] is True and x["independent"] is True for x in cert["children"])
    assert all(x["formal_completeness"] is True and x["all_admissible_target_inputs_proved"] is True for x in cert["children"])

    assert verification["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
    assert verification["verified"]["target_dimension_count"] == 6
    assert verification["verified"]["bound_dimension_count"] == 6
    assert verification["verified"]["exact_dimension_set"] is True
    assert verification["verified"]["exact_contract_fragment_witnesses"] is True
    assert verification["verified"]["scope_relation"] == "PROVEN_STRONGER"
    assert verification["verified"]["root3_scope_relation_closed"] is True
    assert verification["verified"]["acceptance_closed"] is False

    receipt = bridge["candidate_receipt"]
    assert receipt["component_id"] == "evidence synthesis"
    assert receipt["interface_id"] == "delegation+evidence synthesis+artifact production"
    assert receipt["proved_properties"] == ["SCOPED_ACCEPTANCE_PROOF"]
    assert receipt["verified"] is False and receipt["independent"] is False
    assert receipt["contamination_clean"] is True and receipt["acceptance_scoped"] is True
    assert receipt["binds_frozen_claim"] == "MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1"
    assert bridge["expected_effect_after_independent_verification"]["projected_scoped_proved_components_after"] == 5
    assert bridge["expected_effect_after_independent_verification"]["projected_open_components_after"] == 7
    assert bridge["expected_effect_after_independent_verification"]["strict_opus55_acceptance_delta"] == 0
    assert bridge["execution_authority"] is False
    assert bridge["promotion_authority"] is False
    assert bridge["fresh_reality_authority"] is False
    assert bridge["acceptance_credit_delta"] == 0

    print("composition evidence-synthesis scope bridge candidate PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
