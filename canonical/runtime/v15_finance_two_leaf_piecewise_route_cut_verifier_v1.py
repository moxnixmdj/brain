from __future__ import annotations
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
G="canonical/governance/V15_FINANCE_TWO_LEAF_PIECEWISE_ROUTE_CUT_20261007_V1.json"
E={
"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V15.json":"09f11461c7aa1ee7719409723726712f68d03da8",
"canonical/governance/FINANCE_UNCOVERED_SCOPE_DIRECT_PROOF_PROTOCOL_V1.json":"84973ca473cbb8f6160b45c025567c56f8a3d4ba",
"canonical/governance/V13_FINANCE_UNCOVERED_SCOPE_ROUTING_TRUTH_REPAIR_20261007_V1.json":"432e4587bffbf5dc08975ca2740457438a6cd85d",
"canonical/runtime/g0_finite_typed_rule_synthesis.py":"5fcd8101d65367f7c0e53bd245979ba01fb73a26",
"canonical/runtime/structured_method_normalized_rule_graph_v3.py":"79d3896818b03223348f05adf4fdcd574f6f355e",
"canonical/runtime/structured_method_normalized_rule_oracle_v3.py":"5d92b1360fbb1bb27baacc8a04adb3744abf690c",
"canonical/verification/STRUCTURED_METHOD_NORMALIZED_RULE_V3_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"1d6159334bf8e7067f5cb8d31ae0f25b7bb473c3"
}
def h(p):
 b=(R/p).read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p):return json.loads((R/p).read_text())
def verify():
 e=[]
 for p,x in E.items():
  if h(p)!=x:e.append("DRIFT:"+p)
 g=load(G); proto=load("canonical/governance/FINANCE_UNCOVERED_SCOPE_DIRECT_PROOF_PROTOCOL_V1.json")
 leaves={x["id"] for x in proto["leaves"]}
 red=set(g["leaf_reduction"])
 if leaves!=red:e.append("LEAF_SET")
 if len(red)!=2:e.append("LEAF_COUNT")
 if g["piecewise_route_theorem"]["target_information_required"] is not False:e.append("TARGET_INFO")
 if g["piecewise_route_theorem"]["fresh_reality_required_for_this_reduction"] is not False:e.append("FRESH_REALITY")
 text=(R/"canonical/runtime/structured_method_normalized_rule_graph_v3.py").read_text()
 if "rule extraction and semantic normalization are upstream" not in text:e.append("NORMALIZATION_BOUNDARY")
 g0=(R/"canonical/runtime/g0_finite_typed_rule_synthesis.py").read_text()
 if "not general semantic or program synthesis" not in g0:e.append("G0_BOUNDARY")
 if not any("RAW_RULE_OR_DOCUMENT_SEMANTICS_ARE_ALREADY_SOLVED" in x for x in g["hard_nonclaims"]):e.append("OVERCLAIM_BOUNDARY")
 return {"pass":not e,"errors":e,"residual_semantic_binding_count":2 if not e else None,"terminal":False,"terminal_credit_delta":0}
if __name__=="__main__":
 o=verify();print(json.dumps(o,sort_keys=True));raise SystemExit(0 if o["pass"] else 1)
