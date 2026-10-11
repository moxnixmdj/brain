from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P={
"fixed":"canonical/governance/COMPOSITION_CURRENT_UPSTREAM_BRIDGE_FIXED_POINT_V1.json",
"authority":"canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json",
"manifest":"canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json",
"ownership":"canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json",
"memory":"canonical/governance/COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V2.json",
"recovery":"canonical/governance/COMPOSITION_RECOVERY_SCOPE_COMPLETE_BRIDGE_V1.json",
"delegation":"canonical/governance/COMPOSITION_DELEGATION_SCOPE_COMPLETE_BRIDGE_V1.json",
"tool":"canonical/governance/COMPOSITION_TOOL_DISCOVERY_SCOPE_COMPLETE_BRIDGE_V1.json",
}
EXPECTED={
P["authority"]:"5bb089582a5bc2ee4a44143c8d3a11e919fecdff",
P["manifest"]:"9efbf3e81e67fbd15e34be2fcd86fbfc626b246d",
P["ownership"]:"a5f5e15c25f617d36a18cc157f068d078d4235c9",
P["memory"]:"6ed8434359c784634aa76a000ae61a024ce7ae64",
P["recovery"]:"05f68ee39ebef0a9a1fe1cb0ac2df0cede0725f9",
P["delegation"]:"2b5887a7a49ff934d90a46eea349f2da31183a8c",
P["tool"]:"89d2ec6b677c211ecaf5372d8c68dae6881b1bc5",
}
def blob(path):
 b=(ROOT/path).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(path): return json.loads((ROOT/path).read_text())
for p,h in EXPECTED.items(): assert blob(p)==h,(p,blob(p),h)

fx=load(P["fixed"]); a=load(P["authority"]); m=load(P["manifest"]); o=load(P["ownership"])
bridges=[load(P[x]) for x in ("memory","recovery","delegation","tool")]

owned=set()
def walk(x):
 if isinstance(x,list):
  for v in x: walk(v)
 elif isinstance(x,dict):
  if x.get("family") and x.get("status")=="VERIFIED_OWNED_EQUAL_OR_BETTER":
   owned.add(x["family"])
  for v in x.values(): walk(v)
walk(o)
expected_owned={"LONG_HORIZON_MEMORY_AND_CONTINUITY","SUBAGENT_DELEGATION_AND_COORDINATION","SELF_VERIFICATION_DEBUGGING_AND_RECOVERY","TOOL_DISCOVERY_SELECTION_AND_LEARNING","EXACT_SYMBOLIC_COMPUTATION","COMPLEX_MULTI_TOOL_AGENCY","INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT"}
assert owned==expected_owned,owned

truth=a["truth"]
assert truth["frozen_interface_count"]==12
assert truth["current_admissible_scoped_proved"]==4
assert truth["current_open"]==8
proved=set(truth["current_scoped_proved_components"])
assert proved=={"memory","recovery","delegation","tool discovery"}

components={x["component_id"] for x in m["interfaces"]}
assert len(components)==12
assert "EXACT_SYMBOLIC_COMPUTATION" not in components
assert "exact symbolic computation" not in components
assert m["hard_rules"] and "NO_FAMILY_MAPPING_BY_NAME_OR_ANALOGY" in m["hard_rules"]
assert "NO_SEMANTIC_EQUIVALENCE_INFERENCE" in m["hard_rules"]

bindings={}
excluded=set()
for b in bridges:
 cb=b["component_binding"]
 sf=(b.get("derivation") or {}).get("source_family_id") or (b.get("derivation") or {}).get("memory_family_id")
 bindings[sf]=cb["component_id"]
 for x in (b.get("scope_guard") or {}).get("excluded_scope",[]):
  excluded.add(str(x).lower().replace("_"," "))
assert bindings=={
 "LONG_HORIZON_MEMORY_AND_CONTINUITY":"memory",
 "SUBAGENT_DELEGATION_AND_COORDINATION":"delegation",
 "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY":"recovery",
 "TOOL_DISCOVERY_SELECTION_AND_LEARNING":"tool discovery",
}

open_expected={"research","tool use","artifact creation","browser/computer action","coding","debugging","evidence synthesis","artifact production"}
assert components-proved==open_expected
assert fx["fixed_point"]["additional_component_credit_from_current_verified_owned_family_set"]==0
assert set(fx["fixed_point"]["open"])==open_expected
assert fx["accounting"]["acceptance_credit_delta"]==0
assert fx["fresh_reality_authority"] is False

print(json.dumps({
 "status":"PASS__CURRENT_VERIFIED_OWNED_COMPOSITION_BRIDGE_FIXED_POINT_4_OF_12__8_OPEN__ZERO_CREDIT",
 "verified_owned":sorted(owned),
 "bound_components":bindings,
 "scoped_proved":sorted(proved),
 "open":sorted(open_expected),
 "additional_current_owned_family_component_credit":0,
 "fresh_reality_authority":False,
},indent=2,sort_keys=True))
