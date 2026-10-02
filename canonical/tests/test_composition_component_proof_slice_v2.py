from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime.composition_component_proof_slicer_v1 import evaluate

ROOT=Path(__file__).resolve().parents[2]
def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

base=load("canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V1.json")
activation=load("canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_ACTIVATION_V1.json")
activation_verify=load("canonical/verification/COMPOSITION_BEHAVIORAL_BRIDGE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
v2=load("canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V2.json")
expected=load("canonical/verification/COMPOSITION_COMPONENT_PROOF_SLICE_20261002_V2.json")

assert activation_verify["status"]=="INDEPENDENT_PUBLIC_RUNNER_PASS__TWO_CLAIM_BOUND_COMPONENT_RECEIPTS__2_SCOPED_PROVED_10_OPEN__ZERO_CREDIT", activation_verify
assert v2["interfaces"]==base["interfaces"], v2
assert v2["receipts"]==activation["receipts"], v2
assert len(v2["receipts"])==2, v2
assert {x["component_id"] for x in v2["receipts"]}=={"delegation","tool discovery"}, v2
assert v2["authority"]["baseline_slice_input"]["git_blob_sha"]=="adc7db65b20361be54fa26935e36aa88babf373d"
assert v2["authority"]["bridge_activation"]["git_blob_sha"]=="59504f4608f9490022c1aa58214e34191fb0b6e9"
assert v2["authority"]["bridge_activation_independent_verification"]["git_blob_sha"]=="11784ce21ea55506559bc6fb8752b2b1b5585af5"

actual=evaluate(v2)
assert actual==expected,(actual,expected)
proved=[x for x in actual["interfaces"] if x["state"]=="SCOPED_PROVED"]
opened=[x for x in actual["interfaces"] if x["state"]=="OPEN"]
assert len(proved)==2, proved
assert len(opened)==10, opened
assert {x["component_id"] for x in proved}=={"delegation","tool discovery"}, proved
assert actual["all_used_component_interfaces_scoped_proved"] is False
assert actual["capability_credit_delta"]==0
assert actual["family_credit_delta"]==0
print("test_composition_component_proof_slice_v2: PASS")
