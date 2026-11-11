from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ROUTE=ROOT/"canonical/governance/SHARED_S0_G0_DONOR_INDEPENDENT_ROUTE_V1.json"

def verify_route()->dict:
    route=json.loads(ROUTE.read_text())
    failures=[]
    if "UNKNOWN_ABSTAIN_OR_REQUEST_AUTHORIZED_DISCRIMINATOR_WHEN_NO_OWNED_VERIFIER_CAN_IDENTIFY_A_RESULT" not in route.get("ordering",[]):
        failures.append("MISSING_FAIL_CLOSED_FALLBACK")
    if "NO_OPAQUE_EXTERNAL_MODEL_OR_DONOR_RUNTIME" not in route.get("acceptance_policy",[]):
        failures.append("MISSING_DONOR_BAN")
    for rel in route.get("components",[]):
        path=ROOT/rel
        if not path.is_file():
            failures.append("MISSING_COMPONENT:"+rel)
            continue
        data=json.loads(path.read_text())
        if not str(data.get("status","")).startswith("VERIFIED"):
            failures.append("UNVERIFIED_COMPONENT:"+rel)
        if data.get("donor_runtime_required") is not False:
            failures.append("DONOR_RUNTIME_NOT_FALSE:"+rel)
        if data.get("external_model_or_api_required") is True:
            failures.append("OPAQUE_EXTERNAL_REQUIRED:"+rel)
    return {"status":"PASS" if not failures else "FAIL","failures":failures}

if __name__=="__main__":
    result=verify_route()
    print(json.dumps(result,sort_keys=True))
    raise SystemExit(0 if result["status"]=="PASS" else 1)
