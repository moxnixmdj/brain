from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
THEOREM="canonical/governance/DIRECT_END_TO_END_SELECTED_CELL_CERTIFICATE_THEOREM_20261007_V1.json"
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V13.json":"0d18488b51a222e5da414329ccd9d33cbc1fc31c",
 "canonical/governance/SELECTED_COVER_LOCAL_TRANSFORM_CLOSURE_THEOREM_20261007_V1.json":"ea48341b1962c7c90cc78c6ef9affcabbe9abd26",
 "canonical/governance/L1_UNIVERSAL_ABC_NORMAL_FORM_THEOREM_20261007_V1.json":"cff6a95cad0027f3e142a32fd028a27566a00ea5",
}
def blob(data:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def cell_certified(*,complete_semantics:bool,exact_route:bool,e2e:bool,primitive:bool,local_c:bool)->bool:
 return bool(complete_semantics and exact_route and (e2e or (primitive and local_c)))
def verify():
 errors=[]
 for p,w in EXPECTED.items():
  q=ROOT/p
  if not q.is_file(): errors.append("SOURCE_MISSING:"+p); continue
  if blob(q.read_bytes())!=w: errors.append("SOURCE_DRIFT:"+p)
 if not cell_certified(complete_semantics=True,exact_route=True,e2e=True,primitive=False,local_c=False):
  errors.append("DIRECT_E2E_DID_NOT_CERTIFY")
 if not cell_certified(complete_semantics=True,exact_route=True,e2e=False,primitive=True,local_c=True):
  errors.append("LOCAL_C_ROUTE_BROKEN")
 if cell_certified(complete_semantics=False,exact_route=True,e2e=True,primitive=False,local_c=False):
  errors.append("INCOMPLETE_SEMANTICS_FALSE_POSITIVE")
 if cell_certified(complete_semantics=True,exact_route=False,e2e=True,primitive=False,local_c=False):
  errors.append("UNBOUND_ROUTE_FALSE_POSITIVE")
 if cell_certified(complete_semantics=True,exact_route=True,e2e=False,primitive=True,local_c=False):
  errors.append("PARTIAL_DECOMPOSITION_FALSE_POSITIVE")
 return {"status":"PASS__DIRECT_E2E_OR_PRIMITIVE_PLUS_LOCAL_C__ZERO_CREDIT" if not errors else "FAIL_CLOSED","pass":not errors,"errors":errors,"terminal_credit_delta":0}
if __name__=="__main__": print(json.dumps(verify(),indent=2,sort_keys=True))
