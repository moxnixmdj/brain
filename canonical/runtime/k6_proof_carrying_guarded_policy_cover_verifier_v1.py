from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P="canonical/governance/K6_PROOF_CARRYING_GUARDED_POLICY_COVER_THEOREM_20261006_V1.json"
S={
 "current_authority":("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V3.json","142cb46ac1bf0b5c570e6d2dc121dfca6f6e1544"),
 "v4_residual":("canonical/governance/K6_POSITIVE_COVER_SEMANTIC_RESIDUAL_PROJECTION_20261006_V4.json","3e021b353dfe3dd6e9c5ea9843968e7fe75a02eb"),
 "v4_verification":("canonical/verification/K6_POSITIVE_COVER_SEMANTIC_RESIDUAL_V4_SPRITE_VERIFICATION_20261006_V1.json","59fcbc1244879e5f3516ba900cf7167a0679b59e"),
 "positive_cover_theorem":("canonical/governance/K6_POSITIVE_ADEQUACY_COVER_CERTIFICATE_THEOREM_20261006_V1.json","8a235f91ad3064714fab3ea73b324487d9b7f8e5"),
 "positive_cover_verification":("canonical/verification/K6_POSITIVE_ADEQUACY_COVER_CERTIFICATE_SPRITE_VERIFICATION_20261006_V1.json","de91c37808fe53bc133b399ebc7630f2b82bb0e3"),
}
def blob(p):
 b=(ROOT/p).read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def verify():
 d=json.loads((ROOT/P).read_text()); e=[]
 for n,(p,h) in S.items():
  if blob(p)!=h:e.append("SOURCE_DRIFT:"+n)
  b=d["sources"].get(n)
  if not isinstance(b,dict) or b.get("path")!=p or b.get("git_blob_sha")!=h:e.append("BINDING_DRIFT:"+n)
 t=d["theorem"]
 if "g_i(c)_IMPLIES" not in t["guard_soundness"]:e.append("SOUNDNESS_MISSING")
 if "THERE_EXISTS_i" not in t["guard_coverage"]:e.append("COVERAGE_MISSING")
 if d["compression"].get("candidate_successor_residual")!="K6_PROOF_CARRYING_POLICY_GUARD_SOUNDNESS_AND_COVERAGE":e.append("SUCCESSOR_DRIFT")
 if any(v!=0 for k,v in d["accounting"].items() if k.endswith("_delta")):e.append("CREDIT_OVERCLAIM")
 ok=not e
 return {"pass":ok,"errors":e,"status":"PASS__K6_GUARDED_POLICY_COVER_SOURCE_BOUND__ZERO_CREDIT" if ok else "FAIL_CLOSED","terminal_credit_delta":0}
if __name__=="__main__":
 out=verify();print(json.dumps(out,sort_keys=True));raise SystemExit(0 if out["pass"] else 1)
