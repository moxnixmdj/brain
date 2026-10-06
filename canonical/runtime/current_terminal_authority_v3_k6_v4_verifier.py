import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
S={
 "a2":("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V2.json","f17f2f83e7ac8173b0bf54a5cde65646125a15fd"),
 "c4":("canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V4.json","a878bd9b658e4db295dce49bc5b3aa2ba580c59e"),
 "kr":("canonical/governance/K6_CURRENT_AUTHORITY_RECONCILIATION_20261006_V2.json","cf391fad7a1af7238cd247b3b39b41bf2d7c5684"),
 "k4":("canonical/governance/K6_POSITIVE_COVER_SEMANTIC_RESIDUAL_PROJECTION_20261006_V4.json","3e021b353dfe3dd6e9c5ea9843968e7fe75a02eb"),
 "k4v":("canonical/verification/K6_POSITIVE_COVER_SEMANTIC_RESIDUAL_V4_SPRITE_VERIFICATION_20261006_V1.json","59fcbc1244879e5f3516ba900cf7167a0679b59e")
}
def blob(p):
    b=(R/p).read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p): return json.loads((R/p).read_text())
def verify():
    e=[]
    for k,(p,h) in S.items():
        if blob(p)!=h:e.append("DRIFT:"+k)
    a=load(S["a2"][0]); c=load(S["c4"][0]); kr=load(S["kr"][0]); k4=load(S["k4"][0]); k4v=load(S["k4v"][0])
    if a["current_truth"]["current_open_truth_obligations"]!=29:e.append("AUTHORITY_TRUTH_COUNT")
    if c["projection"]["truth_obligations"]!=29:e.append("COVERAGE_TRUTH_COUNT")
    if c["projection"]["truth_obligations_deleted"]!=3:e.append("DELETION_COUNT")
    if kr["correction"]["current_unbound_preproof_implementation_generator_count"]!=0:e.append("GENERIC_IMPLEMENTATION_REOPENED")
    if k4["remaining_unbound_residual"]["id"]!="K6_SOUND_POLICY_COVER_WITNESS_AND_SELECTED_DISCRIMINATOR_BINDING":e.append("K6_V4_RESIDUAL_DRIFT")
    if k4["candidate_global_compression"]["current_generic_unbound_preproof_implementation_generator_count"]!=0:e.append("K6_V4_IMPLEMENTATION_REOPENED")
    if not str(k4v["status"]).startswith("INDEPENDENT_SPRITE"):e.append("K6_V4_VERIFICATION_DRIFT")
    ok=not e
    return {
      "pass":ok,
      "status":"PASS__29_TRUTHS__K6_POSITIVE_COVER_PROOF_INTERFACE__ZERO_NEW_TRUTH_OR_IMPLEMENTATION_GENERATOR" if ok else "FAIL_CLOSED",
      "errors":e,
      "truth_obligations":29 if ok else None,
      "k6_preproof_generic_implementation_generators":0 if ok else None,
      "k6_additional_terminal_truth_variables":0 if ok else None,
      "terminal_credit_delta":0
    }
if __name__=="__main__":
    out=verify();print(json.dumps(out,sort_keys=True));raise SystemExit(0 if out["pass"] else 1)
