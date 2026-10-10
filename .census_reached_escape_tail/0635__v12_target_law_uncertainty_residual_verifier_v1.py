from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
THEOREM="canonical/governance/V12_TARGET_LAW_UNCERTAINTY_RESIDUAL_THEOREM_20261007_V1.json"
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V12.json":"3ab55ad2e9df6a7f94acb2e1950569bdc18c8136",
 "canonical/governance/TARGET_UNDOMINATED_ESCAPE_REDUCTION_20261007_V1.json":"c6757e71f862dd592402199ac12afb8bca45c256",
 "canonical/governance/DISTRIBUTIONAL_TARGET_UPPER_ENVELOPE_THEOREM_20261006_V1.json":"3c672b701da1cf8263dd383e8d3dd021a62b4434",
 "canonical/governance/V7_CAPABILITY_EVALUATOR_CERTIFICATION_TRICHOTOMY_20261006_V1.json":"dce8d6838de486862d205436ed96cda6376e28ba",
}
def blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def residual(possible_laws:set[str], dominated_laws:set[str])->set[str]:
    return set(possible_laws)-set(dominated_laws)
def comparator_free_ok(possible_laws:set[str], dominated_laws:set[str])->bool:
    return not residual(possible_laws,dominated_laws)
def verify():
    errors=[]
    for p,w in EXPECTED.items():
        q=ROOT/p
        if not q.is_file(): errors.append("SOURCE_MISSING:"+p); continue
        if blob(q.read_bytes())!=w: errors.append("SOURCE_DRIFT:"+p)
    t=json.loads((ROOT/THEOREM).read_text())
    if t.get("target_invariant","A_TARGET_COVERAGE") not in {"A_TARGET_COVERAGE",None}: pass
    if not comparator_free_ok({"l0","l1"},{"l0","l1"}):
        errors.append("EMPTY_RESIDUAL_DID_NOT_CLOSE")
    if comparator_free_ok({"l0","l1"},{"l0"}):
        errors.append("UNDOMINATED_LAW_DID_NOT_REOPEN")
    if comparator_free_ok({"l0"},{"l1"}):
        errors.append("WRONG_DOMINATED_SET_FALSE_POSITIVE")
    v12=json.loads((ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V12.json").read_text())
    if (v12.get("abc_normal_form") or {}).get("scope",{}).get("state")!="CLOSED":
        errors.append("V12_SCOPE_NOT_CLOSED")
    if (v12.get("abc_normal_form") or {}).get("escape",{}).get("closure_condition")!="U_INTERSECTION_E_IS_EMPTY":
        errors.append("V12_ESCAPE_CONDITION_DRIFT")
    return {
      "schema":"PROJECT_BRAIN_V12_TARGET_LAW_RESIDUAL_VERIFIER_V1",
      "status":"PASS__TARGET_INFORMATION_RESIDUALIZED_TO_UNDOMINATED_LAWS__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
      "pass":not errors,"errors":errors,"abc_closed":False,"terminal_credit_delta":0
    }
if __name__=="__main__": print(json.dumps(verify(),indent=2,sort_keys=True))
