from __future__ import annotations
import hashlib, json
from pathlib import Path
from canonical.runtime.composition_component_proof_slicer_v1 import evaluate

ROOT=Path(__file__).resolve().parents[2]
INPUT="canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V6.json"
CAND="canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_CANDIDATE_V6.json"
EXPECTED={
 "canonical/runtime/composition_component_proof_slicer_v1.py":"0e5028d8547bc3e17e7128b6311f734ac30a16d8",
 "canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V5.json":"efc59990dc08d4262dca7f8d1fbb672111d1219b",
 "canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V5.json":"4c51caa97fc10e429b36b7cb82aa1dc83ad784f2",
 "canonical/verification/COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"88783df170065d3ff23e4ff3c2d2ab30ec7bc314",
 "canonical/verification/COMPOSITION_DELEGATION_SCOPE_COMPLETE_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"367eaa457c930d5bfcdb44778358ca665d999ae7",
 "canonical/verification/COMPOSITION_RECOVERY_SCOPE_COMPLETE_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"2c18b5029b1a953488b2aefacb00f67b88d27659",
 "canonical/verification/COMPOSITION_TOOL_DISCOVERY_SCOPE_COMPLETE_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"936057358b55a98f6510a8e6ca9062ab903ea83a",
}
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
def blob(p):
 b=(ROOT/p).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def test_exact_sources():
 assert {p:blob(p) for p in EXPECTED}==EXPECTED

def test_v6_is_v5_plus_exactly_new_tool_discovery_receipt():
 v5=load("canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V5.json")
 v6=load(INPUT)
 old={x["receipt_id"] for x in v5["receipts"]}
 new=[x for x in v6["receipts"] if x["receipt_id"] not in old]
 assert len(v5["receipts"])==3
 assert len(v6["receipts"])==4
 assert len(new)==1,new
 assert new[0]["receipt_id"]=="COMPOSITION_SCOPE_COMPLETE_BRIDGE::TOOL_DISCOVERY_SELECTION_AND_LEARNING::tool_discovery::V1"
 assert new[0]["component_id"]=="tool discovery"
 assert new[0]["verified"] is True and new[0]["independent"] is True
 assert "COMPOSITION_BRIDGE::TOOL_ROUTE_DISCOVERY_AND_SELECTION_001::tool_discovery" not in {x["receipt_id"] for x in v6["receipts"]}

def test_exact_slicer_recomputes_four_of_twelve():
 out=evaluate(load(INPUT))
 assert out["status"]=="RESIDUAL_COMPONENT_INTERFACE_PROOFS_OPEN",out
 proved=sorted(x["component_id"] for x in out["interfaces"] if x["state"]=="SCOPED_PROVED")
 assert proved==["delegation","memory","recovery","tool discovery"],proved
 assert sum(x["state"]=="SCOPED_PROVED" for x in out["interfaces"])==4
 assert sum(x["state"]=="OPEN" for x in out["interfaces"])==8
 assert out["all_used_component_interfaces_scoped_proved"] is False
 cand=load(CAND)
 for key in ("schema","errors","claim_id","interfaces","all_used_component_interfaces_scoped_proved","rule","new_reality_units_consumed","capability_credit_delta","family_credit_delta"):
  assert cand[key]==out[key],(key,cand[key],out[key])

if __name__=="__main__":
 test_exact_sources(); test_v6_is_v5_plus_exactly_new_tool_discovery_receipt(); test_exact_slicer_recomputes_four_of_twelve()
 print("test_composition_component_proof_slice_v6: PASS")
