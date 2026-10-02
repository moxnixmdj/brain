from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime.composition_component_proof_slicer_v1 import evaluate

ROOT=Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

activation=load("canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_ACTIVATION_V1.json")
bridge_receipt=load("canonical/verification/COMPOSITION_BEHAVIORAL_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
slice_input=load("canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V1.json")

assert bridge_receipt["status"] == "INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_TWO_COMPONENT_BEHAVIORAL_BRIDGE__ZERO_CREDIT", bridge_receipt
assert bridge_receipt["derived_binding_count"] == 2
assert bridge_receipt["independently_verified_components"] == ["delegation","tool discovery"]
assert bridge_receipt["capability_credit_delta"] == 0
assert bridge_receipt["family_credit_delta"] == 0

assert activation["expected_projection"]["total_interfaces"] == 12
assert activation["expected_projection"]["newly_scoped_proved_interfaces"] == 2
assert activation["expected_projection"]["expected_open_interfaces"] == 10
assert activation["expected_projection"]["composition_component_parent_predicate_closed"] is False
assert activation["execution_authority"] is False
assert activation["promotion_authority"] is False

receipts=slice_input["receipts"]
assert len(receipts) == 2
assert {r["component_id"] for r in receipts} == {"delegation","tool discovery"}
assert all(r["verified"] is True for r in receipts)
assert all(r["independent"] is True for r in receipts)
assert all(r["contamination_clean"] is True for r in receipts)
assert all(r["acceptance_scoped"] is True for r in receipts)
assert all(r["binds_frozen_claim"] == slice_input["claim_id"] for r in receipts)

out=evaluate(slice_input)
assert out["status"] == "RESIDUAL_COMPONENT_INTERFACE_PROOFS_OPEN", out
assert out["all_used_component_interfaces_scoped_proved"] is False
proved=[x for x in out["interfaces"] if x["state"]=="SCOPED_PROVED"]
opened=[x for x in out["interfaces"] if x["state"]=="OPEN"]
assert len(proved) == 2, out
assert len(opened) == 10, out
assert {x["component_id"] for x in proved} == {"delegation","tool discovery"}, out
assert out["new_reality_units_consumed"] == 0
assert out["capability_credit_delta"] == 0
assert out["family_credit_delta"] == 0

print("test_composition_behavioral_bridge_activation_v1: PASS")
