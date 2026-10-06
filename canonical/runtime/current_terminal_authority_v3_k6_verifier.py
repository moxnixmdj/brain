import hashlib, json
from pathlib import Path

R=Path(__file__).resolve().parents[2]
S={
 "a2":("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V2.json","f17f2f83e7ac8173b0bf54a5cde65646125a15fd"),
 "c4":("canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V4.json","a878bd9b658e4db295dce49bc5b3aa2ba580c59e"),
 "k6":("canonical/governance/K6_CURRENT_AUTHORITY_RECONCILIATION_20261006_V2.json","cf391fad7a1af7238cd247b3b39b41bf2d7c5684"),
 "pc":("canonical/governance/K6_POSITIVE_ADEQUACY_COVER_CERTIFICATE_THEOREM_20261006_V1.json","8a235f91ad3064714fab3ea73b324487d9b7f8e5")
}
def blob(path):
    b=(R/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(path):
    return json.loads((R/path).read_text())
def verify():
    errors=[]
    for key,(path,sha) in S.items():
        if blob(path)!=sha: errors.append("DRIFT:"+key)
    a2=load(S["a2"][0]); c4=load(S["c4"][0]); k6=load(S["k6"][0]); pc=load(S["pc"][0])
    t=a2["current_truth"]
    if t["current_open_truth_obligations"]!=29: errors.append("AUTHORITY_TRUTH_COUNT")
    if c4["projection"]["truth_obligations"]!=29: errors.append("COVERAGE_TRUTH_COUNT")
    if c4["projection"]["truth_obligations_deleted"]!=3: errors.append("DELETION_COUNT")
    if k6["correction"]["current_unbound_preproof_implementation_generator_count"]!=0: errors.append("K6_IMPLEMENTATION_REOPENED")
    if k6["correction"]["new_label"]!="ONE_UNBOUND_SEMANTIC_INFORMATION_BINDING_INTERFACE": errors.append("K6_ROLE_DRIFT")
    if pc["consequence_for_current_k6_residual"]["candidate_successor"]!="K6_SOUND_POLICY_COVER_WITNESS_AND_SELECTED_DISCRIMINATOR_BINDING": errors.append("K6_RESIDUAL_DRIFT")
    ok=not errors
    return {
      "pass":ok,
      "status":"PASS__29_TRUTHS__K6_PROOF_INPUT_BINDING_NOT_NEW_TRUTH_OR_IMPLEMENTATION_GENERATOR" if ok else "FAIL_CLOSED",
      "errors":errors,
      "truth_obligations":29 if ok else None,
      "k6_preproof_implementation_generators":0 if ok else None,
      "k6_additional_terminal_truth_variables":0 if ok else None,
      "terminal_credit_delta":0
    }
if __name__=="__main__":
    out=verify(); print(json.dumps(out,sort_keys=True)); raise SystemExit(0 if out["pass"] else 1)
