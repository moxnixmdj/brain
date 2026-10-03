from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUTH="canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json"
EXPECTED={
 "canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V5.json":"4c51caa97fc10e429b36b7cb82aa1dc83ad784f2",
 "canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V6.json":"cb15018cd7a913bdf250d1cef884d4b1005d3d67",
 "canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_CANDIDATE_V6.json":"317b3f6d58e5294577eb645c9fe5c07235efdde1",
 "canonical/verification/COMPOSITION_COMPONENT_PROOF_SLICE_PUBLIC_RUNNER_VERIFICATION_20261003_V6.json":"3d4ce142f680bd371f7b54a11938a43059ceb055",
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

def test_authority_exactly_promotes_verified_four_component_slice():
 a=load(AUTH); v=load("canonical/verification/COMPOSITION_COMPONENT_PROOF_SLICE_PUBLIC_RUNNER_VERIFICATION_20261003_V6.json")
 assert str(v["status"]).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),v
 assert v["verified"]["scoped_proved_count"]==4 and v["verified"]["open_count"]==8,v
 assert a["truth"]["current_admissible_scoped_proved"]==4,a
 assert a["truth"]["current_open"]==8,a
 assert a["truth"]["current_scoped_proved_components"]==["memory","recovery","delegation","tool discovery"],a
 assert a["truth"]["parent_composition_predicate_closed"] is False,a
 assert len(a["current_admissible_receipts"])==4,a
 assert len({x["receipt_id"] for x in a["current_admissible_receipts"]})==4,a
 assert a["strict_opus55_acceptance_delta"] if "strict_opus55_acceptance_delta" in a else a["truth"]["strict_opus55_acceptance_delta"]==0
 assert a["family_credit_delta"]==0 and a["ownership_credit_delta"]==0,a
 assert a["execution_authority"] is False and a["promotion_authority"] is False,a

if __name__=="__main__":
 test_exact_sources(); test_authority_exactly_promotes_verified_four_component_slice()
 print("test_composition_component_proof_current_authority_v6: PASS")
