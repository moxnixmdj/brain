from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"canonical/governance/K6_POSITIVE_COVER_SEMANTIC_RESIDUAL_PROJECTION_20261006_V4.json"
SOURCES={
 "predecessor":("canonical/governance/K6_SEMANTIC_BINDING_RESIDUAL_PROJECTION_20261006_V3.json","21d9f8551326f9741a5b13e6cc5d1494c23d9e34"),
 "theorem":("canonical/governance/K6_POSITIVE_ADEQUACY_COVER_CERTIFICATE_THEOREM_20261006_V1.json","8a235f91ad3064714fab3ea73b324487d9b7f8e5"),
 "verification":("canonical/verification/K6_POSITIVE_ADEQUACY_COVER_CERTIFICATE_SPRITE_VERIFICATION_20261006_V1.json","de91c37808fe53bc133b399ebc7630f2b82bb0e3"),
 "operator":("canonical/governance/K6_POLICY_INDEX_REFINEMENT_AND_PERSISTENCE_COMPILER_20261006_V1.json","df1a557bc37eac67ad6446fbcca8f891128f9c94"),
 "operator_verification":("canonical/verification/K6_POLICY_INDEX_REFINEMENT_PERSISTENCE_SPRITE_VERIFICATION_20261006_V1.json","d1849b94c6a9119cc789a5e920c3687f18d81ff5"),
 "authority":("canonical/governance/ATOMIC_SURVIVOR_EXECUTION_AUTHORITY_RECONCILIATION_V1.json","19b363f3f6be080b73ba144f82ef5f0a481217b1"),
}

def blob(path):
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def verify():
    d=json.loads(P.read_text())
    errors=[]
    for _,(path,sha) in SOURCES.items():
        if blob(path)!=sha: errors.append("SOURCE_DRIFT:"+path)
    r=d["remaining_unbound_residual"]
    if r["id"]!="K6_SOUND_POLICY_COVER_WITNESS_AND_SELECTED_DISCRIMINATOR_BINDING":
        errors.append("RESIDUAL_ID_DRIFT")
    c=d["candidate_global_compression"]
    if c["current_generic_unbound_preproof_implementation_generator_count"]!=0:
        errors.append("GENERIC_K6_REOPENED")
    if d["execution_authority"] is not False or d["promotion_authority"] is not False:
        errors.append("AUTHORITY_OVERCLAIM")
    if any(v!=0 for k,v in d["accounting"].items() if k.endswith("_delta")):
        errors.append("CREDIT_OVERCLAIM")
    ok=not errors
    return {"pass":ok,"errors":errors,"status":"PASS__K6_V4_POSITIVE_COVER_RESIDUAL" if ok else "FAIL_CLOSED","terminal_credit_delta":0}

if __name__=="__main__":
    out=verify(); print(json.dumps(out,sort_keys=True)); raise SystemExit(0 if out["pass"] else 1)
