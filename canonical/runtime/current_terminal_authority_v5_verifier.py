from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
S={
 "v4":("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V4.json","4f9e7adefafd23268f590614b4a0b821fe0d6472"),
 "a":("canonical/governance/FINITE_BLACKBOX_TARGET_COMPLETENESS_LOWER_BOUND_20261007_V1.json","a2c2a7f7acccd3c650deb7d2fc7ee2a2d2dad7cc"),
 "c":("canonical/governance/DOMINANCE_PRESERVING_TRANSFORM_CLOSURE_THEOREM_20261007_V1.json","a16ec6380fdcaf6c140d531f6eef3cc3a67d98c7"),
 "d":("canonical/governance/ROOT3_CREDITED_ROUTE_EFFECT_FOOTPRINT_COMPILER_20261007_V1.json","a8448eb871831242a204fdb579bce6717d7b6621"),
 "m":("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json","cf736088c1ff460283f9b62d873b8e0710374e79"),
}
def blob(p):
    b=(ROOT/p).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
def verify():
    e=[f"DRIFT:{k}" for k,(p,h) in S.items() if blob(p)!=h]
    if e:return {"pass":False,"errors":e,"terminal":False}
    v4,a,c,d,m=[load(S[k][0]) for k in ("v4","a","c","d","m")]
    if v4["preserved_current_truth"]["current_open_truth_obligations"]!=29:e.append("TRUTH_COUNT")
    if v4["preserved_current_truth"]["accepted_families"]!=5:e.append("ACCEPTED_COUNT")
    if v4["preserved_current_truth"]["open_families"]!=14:e.append("OPEN_COUNT")
    if len(a["closure_routes"])!=4:e.append("A_ROUTES")
    if "finite_closure" not in c["theorem"]:e.append("C_THEOREM")
    if "NO_CURRENT_CREDITED_ROUTE_FOOTPRINT_COMPILED" not in d["hard_nonclaims"]:e.append("D_BOUNDARY")
    rows=m.get("families") or m.get("rows") or m.get("capabilities") or []
    if sum(x.get("status")=="VERIFIED_OWNED_EQUAL_OR_BETTER" for x in rows)!=5:e.append("OWNED_COUNT")
    return {
      "pass":not e,"errors":e,"open_truth_obligations":29 if not e else None,
      "accepted_families":5 if not e else None,"open_families":14 if not e else None,
      "A_blackbox_global_finality":False,
      "C_arbitrary_sequence_enumeration_required":False,
      "D_effect_footprint_compiler_integrated":True if not e else None,
      "terminal":False,"terminal_credit_delta":0}
if __name__=="__main__":
    o=verify();print(json.dumps(o,sort_keys=True));raise SystemExit(0 if o["pass"] else 1)
