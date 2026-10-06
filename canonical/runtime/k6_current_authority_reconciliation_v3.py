from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"canonical/governance/K6_CURRENT_AUTHORITY_RECONCILIATION_20261006_V3.json"
SOURCES={
 "current_terminal_authority":("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V2.json","dc79f409fd486d9ca0fe52eea4422169f1b61403"),
 "prior_k6_authority":("canonical/governance/K6_CURRENT_AUTHORITY_RECONCILIATION_20261006_V2.json","cf391fad7a1af7238cd247b3b39b41bf2d7c5684"),
 "v4_residual":("canonical/governance/K6_POSITIVE_COVER_SEMANTIC_RESIDUAL_PROJECTION_20261006_V4.json","3e021b353dfe3dd6e9c5ea9843968e7fe75a02eb"),
 "v4_verification":("canonical/verification/K6_POSITIVE_COVER_SEMANTIC_RESIDUAL_V4_SPRITE_VERIFICATION_20261006_V1.json","59fcbc1244879e5f3516ba900cf7167a0679b59e"),
 "positive_cover_theorem":("canonical/governance/K6_POSITIVE_ADEQUACY_COVER_CERTIFICATE_THEOREM_20261006_V1.json","8a235f91ad3064714fab3ea73b324487d9b7f8e5"),
 "positive_cover_verification":("canonical/verification/K6_POSITIVE_ADEQUACY_COVER_CERTIFICATE_SPRITE_VERIFICATION_20261006_V1.json","de91c37808fe53bc133b399ebc7630f2b82bb0e3"),
}

def blob(p):
    b=(ROOT/p).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(p):
    return json.loads((ROOT/p).read_text())

def verify():
    d=load("canonical/governance/K6_CURRENT_AUTHORITY_RECONCILIATION_20261006_V3.json")
    errors=[]
    for name,(path,sha) in SOURCES.items():
        if blob(path)!=sha: errors.append("SOURCE_DRIFT:"+name)
        b=d["sources"].get(name)
        if not isinstance(b,dict) or b.get("path")!=path or b.get("git_blob_sha")!=sha:
            errors.append("BINDING_DRIFT:"+name)

    a=load(SOURCES["current_terminal_authority"][0])
    c=d["correction"]
    if a.get("status")!="ACTIVE_FAIL_CLOSED__29_LOAD_BEARING_TRUTHS__TERMINAL_FALSE__ZERO_CREDIT":
        errors.append("TERMINAL_AUTHORITY_STATUS_DRIFT")
    if "K6_POSITIVE_COVER_WITNESS_FIXED_POINT" not in (a.get("next") or []):
        errors.append("CURRENT_NEXT_NOT_REBOUND")
    if c.get("current_terminal_truth_count")!=29:
        errors.append("TRUTH_COUNT_DRIFT")
    if c.get("current_unbound_preproof_implementation_generator_count")!=0:
        errors.append("GENERIC_K6_IMPLEMENTATION_REOPENED")
    if c.get("current_open_semantic_information_interface_count")!=1:
        errors.append("SEMANTIC_INTERFACE_COUNT_DRIFT")
    if c.get("current_open_interface")!="K6_SOUND_POLICY_COVER_WITNESS_AND_SELECTED_DISCRIMINATOR_BINDING":
        errors.append("OPEN_INTERFACE_DRIFT")
    if c.get("truth_obligations_deleted_by_this_reconciliation")!=0:
        errors.append("TRUTH_DELETION_OVERCLAIM")

    if d["authority"].get("generic_k6_implementation")!="DENIED_PREPROOF":
        errors.append("GENERIC_K6_AUTHORITY_DRIFT")
    for key in ("execution_authority","promotion_authority","fresh_reality_authority"):
        if d.get(key) is not False: errors.append("AUTHORITY_OVERCLAIM:"+key)
    if any(v!=0 for k,v in d["accounting"].items() if k.endswith("_delta")):
        errors.append("CREDIT_OVERCLAIM")

    ok=not errors
    return {
      "status":"PASS__K6_CURRENT_AUTHORITY_V3__29_TRUTHS__ONE_POSITIVE_COVER_INTERFACE__ZERO_PREPROOF_IMPLEMENTATION_GENERATORS__ZERO_CREDIT" if ok else "FAIL_CLOSED",
      "pass":ok,"errors":errors,"truth_count":29 if ok else None,
      "unbound_preproof_implementation_generators":0 if ok else None,
      "open_semantic_information_interfaces":1 if ok else None,
      "terminal_credit_delta":0
    }

if __name__=="__main__":
    out=verify(); print(json.dumps(out,sort_keys=True)); raise SystemExit(0 if out["pass"] else 1)
