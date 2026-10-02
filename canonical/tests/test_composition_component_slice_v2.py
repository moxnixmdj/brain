from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime.composition_component_proof_slicer_v1 import evaluate

ROOT=Path(__file__).resolve().parents[2]
def load(rel): return json.loads((ROOT/rel).read_text(encoding="utf-8"))

receipt=load("canonical/verification/COMPOSITION_BEHAVIORAL_BRIDGE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
inp=load("canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V2.json")
expected=load("canonical/verification/COMPOSITION_COMPONENT_PROOF_SLICE_20261002_V2.json")

assert receipt["status"]=="INDEPENDENT_PUBLIC_RUNNER_PASS__TWO_CLAIM_BOUND_COMPONENT_RECEIPTS__2_PROVED_10_OPEN__ZERO_CREDIT", receipt
assert receipt["public_runner"]["pull_request"]==926
assert receipt["public_runner"]["conclusion"]=="success"
assert receipt["activated_components"]==["delegation","tool discovery"]
assert receipt["parent_predicate_closed"] is False

actual=evaluate({
    "claim_id": inp["claim_id"],
    "interfaces": inp["interfaces"],
    "receipts": inp["receipts"],
})
assert actual==expected,(actual,expected)
proved=[x for x in actual["interfaces"] if x["state"]=="SCOPED_PROVED"]
opened=[x for x in actual["interfaces"] if x["state"]=="OPEN"]
assert len(proved)==2
assert len(opened)==10
assert {x["component_id"] for x in proved}=={"delegation","tool discovery"}
assert actual["all_used_component_interfaces_scoped_proved"] is False
assert inp["new_reality_units_consumed"]==0
assert inp["capability_credit_delta"]==0
assert inp["family_credit_delta"]==0

print("test_composition_component_slice_v2: PASS")
