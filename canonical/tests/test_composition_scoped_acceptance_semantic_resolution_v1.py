from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESOLUTION = ROOT / "canonical/governance/COMPOSITION_SCOPED_ACCEPTANCE_SEMANTIC_RESOLUTION_V1.json"

EXPECTED = {
    "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json": "9efbf3e81e67fbd15e34be2fcd86fbfc626b246d",
    "canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json": "5bb089582a5bc2ee4a44143c8d3a11e919fecdff",
    "canonical/verification/SYNTHESIS_LOSSLESS_SCOPE_DECOMPOSITION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json": "1852516f725f5b72badfc2f65be22e542ed83623",
    "canonical/verification/ARTIFACT_UNCOVERED_SCOPE_PARTITION_PROOF_20261002_V1.json": "11aaa9915906511acf9f8a48e02b993b670fe44d",
}


def blob(rel: str) -> str:
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_scope_complete_does_not_imply_scoped_acceptance():
    for rel, expected in EXPECTED.items():
        assert blob(rel) == expected, (rel, blob(rel), expected)

    resolution = json.loads(RESOLUTION.read_text(encoding="utf-8"))
    manifest = load("canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json")
    authority = load("canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json")
    synthesis = load("canonical/verification/SYNTHESIS_LOSSLESS_SCOPE_DECOMPOSITION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
    artifact = load("canonical/verification/ARTIFACT_UNCOVERED_SCOPE_PARTITION_PROOF_20261002_V1.json")

    assert all(
        interface["required_properties"] == ["SCOPED_ACCEPTANCE_PROOF"]
        for interface in manifest["interfaces"]
    )
    assert authority["hard_rules"][0] == (
        "ONLY_INDEPENDENT_CONTAMINATION_CLEAN_ACCEPTANCE_SCOPED_CURRENT_SOURCE_RECEIPTS_GRANT_COMPONENT_CREDIT"
    )
    assert synthesis["verified"]["acceptance_closed"] is False
    assert "DOES_NOT_INHERIT_PUBLIC_BAR_PERFORMANCE_CREDIT" in artifact["exclusions"]

    model = resolution["countermodel"]
    assert set(model["covered_domain"]) == set(model["frozen_domain"])
    assert model["scope_complete"] is True
    assert model["brain_terminal_success_on_x"] < model["required_terminal_success_on_x"]
    assert model["scoped_acceptance"] is False

    scope_complete_implies_acceptance = (
        (not model["scope_complete"]) or model["scoped_acceptance"]
    )
    assert scope_complete_implies_acceptance is False
    assert resolution["theorem"]["result"] == "PROVED_NONIMPLICATION"
    assert resolution["scheduler_effect"]["resolved_global_gate"] == "NO"
    assert resolution["scheduler_effect"]["safe_scoped_proved_count"] == 4
    assert resolution["scheduler_effect"]["safe_open_count"] == 8
    assert resolution["acceptance_credit_delta"] == 0
    assert resolution["fresh_reality_authority"] is False
