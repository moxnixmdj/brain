from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "canonical/governance/COMPOSITION_SCOPED_ACCEPTANCE_ADMISSIBILITY_SEMANTIC_GATE_V1.json"

EXPECTED = {
    "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json": "9efbf3e81e67fbd15e34be2fcd86fbfc626b246d",
    "canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json": "5bb089582a5bc2ee4a44143c8d3a11e919fecdff",
    "canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V6.json": "cb15018cd7a913bdf250d1cef884d4b1005d3d67",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json": "a3fd20e58fdbd9b86278b7de0c245de3063dce27",
    "canonical/verification/SYNTHESIS_LOSSLESS_SCOPE_DECOMPOSITION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json": "1852516f725f5b72badfc2f65be22e542ed83623",
    "canonical/verification/ARTIFACT_UNCOVERED_SCOPE_PARTITION_PROOF_20261002_V1.json": "11aaa9915906511acf9f8a48e02b993b670fe44d",
}

def blob(rel: str) -> str:
    b = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()

def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def test_global_semantic_gate_fails_closed_on_scope_only_receipts():
    for rel, expected in EXPECTED.items():
        assert blob(rel) == expected, (rel, blob(rel), expected)

    gate = json.loads(GATE.read_text(encoding="utf-8"))
    manifest = load("canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json")
    authority = load("canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json")
    slice_v6 = load("canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V6.json")
    ledger = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
    synth = load("canonical/verification/SYNTHESIS_LOSSLESS_SCOPE_DECOMPOSITION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")

    assert "acceptance scoped receipts" in manifest["next"].lower().replace("_", " ")
    assert "ACCEPTANCE_SCOPED" in authority["hard_rules"][0]
    assert authority["truth"]["current_admissible_scoped_proved"] == 4
    assert authority["truth"]["current_open"] == 8

    receipts = slice_v6["receipts"]
    assert {r["component_id"] for r in receipts} == {"memory", "recovery", "delegation", "tool discovery"}
    assert all(r["acceptance_scoped"] is True for r in receipts)
    bridge_receipts = [r for r in receipts if r["component_id"] != "memory"]
    assert all("source_acceptance_receipt" in r for r in bridge_receipts)

    assert synth["verified"]["acceptance_closed"] is False
    art = next(x for x in ledger["claims"] if x.get("predicate_id") == "ARTIFACT_UNCOVERED_FORMAT_SCOPE_AUDIT")
    assert art["state"] == "PROVED"
    assert art["scope_complete"] is True
    assert art["performance_credit"] == "ZERO__AA_BRIEFCASE_GE_1822_REMAINS_REQUIRED"

    proj = gate["projection"]
    assert proj["safe_projection_without_semantic_discharge"] == 4
    assert proj["artifact_only_5_of_12_authorized"] is False
    assert proj["artifact_plus_synthesis_6_of_12_authorized"] is False
    assert gate["acceptance_credit_delta"] == 0
    assert gate["fresh_reality_authority"] is False


def test_scope_completeness_does_not_imply_acceptance_under_current_authority():
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    ff = gate["formal_falsification"]
    assert ff["result"] == "FALSE"
    assert ff["canonical_counterexample"]["scope_complete"] is True
    assert ff["canonical_counterexample"]["acceptance_closed"] is False
    assert ff["canonical_counterexample"]["implication_evaluation"] is False
    assert ff["independent_logic_check"]["tautology_q_scope_implies_acceptance"] is False
    assert ff["independent_logic_check"]["countermodel_exists_for_scope_true_acceptance_false"] is True
    assert gate["semantic_gate"]["current_answer"].startswith("PROVED_FAIL_CLOSED")
