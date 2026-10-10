from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BUNDLE="canonical/governance/SELECTED_DISCRIMINATOR_POLICY_COVER_BRIDGE_20261007_V1.json"
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json":"0cab18a7c3c2b10221cb0a269671f4d374010534",
 "canonical/governance/SHARED_SEMANTIC_TAIL_SELECTED_DISCRIMINATOR_TRUTH_REPAIR_20261007_V1.json":"15048c3627cb19e7425139c93a0d51e9aeb6850b",
 "canonical/governance/K6_POSITIVE_ADEQUACY_COVER_CERTIFICATE_THEOREM_20261006_V1.json":"8a235f91ad3064714fab3ea73b324487d9b7f8e5",
 "canonical/governance/K6_MINIMUM_ADEQUATE_POLICY_COVER_THEOREM_20261006_V1.json":"9bc8e53c8e5a59d540dd77ddb69e9f4100812668",
 "canonical/capabilities/opus55/SEMANTIC_IDENTIFIABILITY_GATE_001.json":"721ceeae858e92b4bee89130e89f6c329cfe323c",
 "canonical/capabilities/opus55/SOURCE_TRACEABLE_SEMANTIC_IR_001.json":"b1aeb7a60f1f8d6bb1b8b378ff7802f42c618145",
}
ALLOWED={"COMMON_POLICY_CERTIFICATE","SELECTED_DISCRIMINATOR_POLICY_COVER_CERTIFICATE","FAIL_CLOSED_UNRESOLVED"}

def blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load(path:str):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def verify():
    errors=[]
    for path,want in EXPECTED.items():
        p=ROOT/path
        if not p.is_file():
            errors.append("SOURCE_MISSING:"+path); continue
        got=blob(p.read_bytes())
        if got!=want:
            errors.append("SOURCE_DRIFT:"+path+":"+got)
    b=load(BUNDLE)
    outs=set((b.get("interface") or {}).get("output_one_of") or [])
    if outs!=ALLOWED:
        errors.append("OUTPUT_ALGEBRA_DRIFT")
    steps=b.get("procedure") or []
    if [x.get("name") for x in steps] != ["COMMON_POLICY_FIRST","SELECTED_DISCRIMINATOR_SEARCH","FAIL_CLOSED"]:
        errors.append("PROCEDURE_ORDER_DRIFT")
    if (b.get("owned_component_reuse") or {}).get("new_general_semantic_model_required") is not False:
        errors.append("GENERAL_MODEL_FALSE_PREREQUISITE")
    if (b.get("owned_component_reuse") or {}).get("new_general_router_required") is not False:
        errors.append("GENERAL_ROUTER_FALSE_PREREQUISITE")
    nonclaims=set(b.get("hard_nonclaims") or [])
    for required in {"NO_CLAIM_U_IS_EMPTY.","NO_CLAIM_COMPLETE_SELECTED_CONTEXT_ABC_IS_CLOSED.","NO_TERMINAL_CREDIT."}:
        if required not in nonclaims:
            errors.append("MISSING_NONCLAIM:"+required)
    return {
      "schema":"PROJECT_BRAIN_SELECTED_DISCRIMINATOR_POLICY_COVER_BRIDGE_VERIFY_V1",
      "status":"PASS__SHARED_POLICY_COVER_BRIDGE_BOUND__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "abc_closed":False,
      "terminal":False,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
    raise SystemExit(0 if verify()["pass"] else 1)
