from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ACT="canonical/governance/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_V1.json"
ROLE="canonical/verification/DUAL_JUDGMENT_GENERAL_SUBSTRATE_ROLE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
MAT="canonical/verification/DUAL_JUDGMENT_CONTROL_CURRENT_MAIN_INDEPENDENT_VERIFICATION_20261003_V1.json"
GATE="canonical/runtime/acceptance_capability_source_gate_v2.py"
EXPECTED={
 ROLE:"047b464ff60d4eaf04c31937b1103c8bf8d678fc",
 MAT:"041b73f3c212d86d870554d2dc7b8ad0b691d921",
 GATE:"b168b131f6383e158bdc0d931439d14e61f2a5de",
}
REQ={
 "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_FINANCE_JUDGMENT_SOURCE_GATE_PASS",
 "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_UNKNOWN_DOMAIN_JUDGMENT_SOURCE_GATE_PASS",
}

def blob(path):
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def evaluate():
    errors=[]
    drift={p:{"expected":h,"actual":blob(p)} for p,h in EXPECTED.items() if blob(p)!=h}
    if drift:
        return {"pass":False,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT","errors":["SOURCE_BLOB_DRIFT"],"drift":drift}
    act,role,mat=load(ACT),load(ROLE),load(MAT)
    if not str(role.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("ROLE_RECEIPT_NOT_INDEPENDENT_PASS")
    rv=role.get("verified") or {}
    if rv.get("general_substrate_test_pass") is not True: errors.append("GENERAL_SUBSTRATE_NOT_PROVED")
    if rv.get("source_gate_v2_pass") is not True: errors.append("SOURCE_GATE_NOT_PROVED")
    if set(rv.get("requirements_eligible_to_close") or []) != REQ: errors.append("ROLE_REQUIREMENT_SET_DRIFT")
    if not str(mat.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("MATERIAL_CONTROL_NOT_INDEPENDENT_PASS")
    if set(act.get("discharged_requirements") or []) != REQ: errors.append("ACTIVATION_REQUIREMENT_SET_DRIFT")
    if act.get("acceptance_predicate_delta") != 0: errors.append("ACCEPTANCE_OVERCLAIM")
    if act.get("family_acceptance_delta") != 0: errors.append("FAMILY_OVERCLAIM")
    if act.get("ownership_delta") != 0: errors.append("OWNERSHIP_OVERCLAIM")
    if act.get("new_reality_units_consumed") != 0: errors.append("REALITY_NONZERO")
    if act.get("terminal_case_content_read") != 0: errors.append("CASE_CONTENT_READ")
    if act.get("execution_authority") is not False: errors.append("GLOBAL_EXECUTION_AUTHORITY_OVERCLAIM")
    state=act.get("resulting_direct_protocol_state") or {}
    if state.get("clean_direct_case_execution_eligible") is not True: errors.append("DIRECT_PROTOCOL_NOT_ELIGIBLE")
    if state.get("global_fresh_reality_authority") is not False: errors.append("GLOBAL_FRESH_REALITY_OVERCLAIM")
    ok=not errors
    return {
      "pass":ok,
      "status":"PASS__TWO_SOURCE_GATE_REQUIREMENTS_DISCHARGED__DIRECT_LEAVES_STILL_UNEXECUTED__ZERO_REALITY" if ok else "FAIL_CLOSED",
      "errors":sorted(set(errors)),
      "discharged_requirements":sorted(REQ) if ok else [],
      "remaining_acceptance_predicate_delta":0,
      "new_reality_units_consumed":0,
      "global_fresh_reality_authority":False,
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
