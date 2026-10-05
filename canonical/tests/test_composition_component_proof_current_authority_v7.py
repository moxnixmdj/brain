from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUTH="canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V7.json"
SLICE="canonical/verification/COMPOSITION_COMPONENT_PROOF_SLICE_SPRITE_VERIFICATION_20261005_V7.json"
EXPECTED={
 "canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json":"5bb089582a5bc2ee4a44143c8d3a11e919fecdff",
 "canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V7.json":"3189a91881813996f9c4a564a8530b55172f5334",
 "canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_CANDIDATE_V7.json":"05d9bee363180154b3ece87c84ea7fde4a1edcb0",
 "canonical/verification/COMPOSITION_COMPONENT_PROOF_SLICE_SPRITE_VERIFICATION_20261005_V7.json":"21ccf99da0dd901013b4bb5000deedef50182423",
 "canonical/verification/COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"88783df170065d3ff23e4ff3c2d2ab30ec7bc314",
 "canonical/verification/COMPOSITION_DELEGATION_SCOPE_COMPLETE_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"367eaa457c930d5bfcdb44778358ca665d999ae7",
 "canonical/verification/COMPOSITION_RECOVERY_SCOPE_COMPLETE_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"2c18b5029b1a953488b2aefacb00f67b88d27659",
 "canonical/verification/COMPOSITION_TOOL_DISCOVERY_SCOPE_COMPLETE_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"936057358b55a98f6510a8e6ca9062ab903ea83a",
 "canonical/governance/COMPOSITION_DEBUGGING_SCOPE_COMPLETE_BRIDGE_V1.json":"c6ec2a46bf8e271bafc6d4fd18a138cf67b657aa",
 "canonical/verification/COMPOSITION_DEBUGGING_SCOPE_COMPLETE_BRIDGE_SPRITE_VERIFICATION_20261005_V1.json":"8aaa90a62a30d5379b3ab2f861f79e53cf7465ce",
}
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
def blob(p):
 b=(ROOT/p).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def test_exact_sources():
 assert {p:blob(p) for p in EXPECTED}==EXPECTED

def test_authority_exactly_promotes_verified_five_component_slice():
 a=load(AUTH); v=load(SLICE)
 assert str(v["status"]).startswith("INDEPENDENT_SPRITE_RECOMPUTATION_PASS"),v
 assert v["verified"]["scoped_proved_count"]==5 and v["verified"]["open_count"]==7,v
 expected=["memory","recovery","debugging","tool discovery","delegation"]
 assert v["verified"]["scoped_proved_components"]==expected,v
 assert a["truth"]["current_admissible_scoped_proved"]==5,a
 assert a["truth"]["current_open"]==7,a
 assert a["truth"]["current_scoped_proved_components"]==expected,a
 assert a["truth"]["parent_composition_predicate_closed"] is False,a
 assert len(a["current_admissible_receipts"])==5,a
 assert len({x["receipt_id"] for x in a["current_admissible_receipts"]})==5,a
 dbg=[x for x in a["current_admissible_receipts"] if x["component_id"]=="debugging"]
 assert len(dbg)==1 and dbg[0]["verification_git_blob_sha"]=="8aaa90a62a30d5379b3ab2f861f79e53cf7465ce",a
 assert a["truth"]["strict_opus55_acceptance_delta"]==0,a
 assert a["family_credit_delta"]==0 and a["ownership_credit_delta"]==0,a
 assert a["execution_authority"] is False and a["promotion_authority"] is False,a

if __name__=="__main__":
 test_exact_sources(); test_authority_exactly_promotes_verified_five_component_slice()
 print("test_composition_component_proof_current_authority_v7: PASS")
