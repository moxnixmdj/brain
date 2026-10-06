import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
S={
 "a":("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V2.json","f17f2f83e7ac8173b0bf54a5cde65646125a15fd"),
 "k":("canonical/governance/K6_SEMANTIC_BINDING_RESIDUAL_PROJECTION_20261006_V3.json","21d9f8551326f9741a5b13e6cc5d1494c23d9e34"),
 "s":("canonical/governance/S0_G0_ZERO_REALITY_SATURATION_V1.json","31effb16940e6d5c0c95259871b2e3c00cb5e400"),
 "r":("canonical/governance/ATOMIC_SURVIVOR_EXECUTION_AUTHORITY_RECONCILIATION_V1.json","19b363f3f6be080b73ba144f82ef5f0a481217b1"),
 "v":("canonical/verification/K6_DECISION_REFINEMENT_COMPILER_SPRITE_VERIFICATION_20261006_V1.json","e7a98cd6c9f80c2120f1f53562338cd63e9d1581")
}
def blob(p):
 b=(R/p).read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p): return json.loads((R/p).read_text())
def verify():
 e=[]
 for n,(p,h) in S.items():
  if blob(p)!=h:e.append("DRIFT:"+n)
 k=load(S["k"][0]); s=load(S["s"][0]); r=load(S["r"][0]); v=load(S["v"][0])
 if k.get("verified_operator",{}).get("state")!="BRAIN_OWNED_FOR_FINITE_DECLARED_INSTANCES":e.append("OPERATOR_NOT_OWNED")
 if k.get("remaining_unbound_residual",{}).get("id")!="K6_TARGET_ACCEPTABILITY_AND_DISCRIMINATOR_SEMANTIC_BINDING":e.append("RESIDUAL_DRIFT")
 if "IMPLEMENTATION_FRONTIER_SATURATED" not in str(s.get("status")):e.append("SATURATION_DRIFT")
 if r.get("facts",{}).get("current_preproof_implementation_residual_count")!=0:e.append("IMPLEMENTATION_REOPENED")
 if not str(v.get("status","")).startswith("INDEPENDENT_SPRITE"):e.append("OPERATOR_VERIFICATION_DRIFT")
 ok=not e
 return {"status":"PASS__ZERO_PREPROOF_IMPLEMENTATION_GENERATORS__ONE_SEMANTIC_BINDING_INTERFACE" if ok else "FAIL_CLOSED","pass":ok,"errors":e,"unbound_preproof_implementation_generators":0 if ok else None,"open_semantic_information_interfaces":1 if ok else None,"terminal_credit_delta":0}
if __name__=="__main__":
 print(json.dumps(verify(),sort_keys=True)); raise SystemExit(0 if verify()["pass"] else 1)
