from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CAND="canonical/governance/CURRENT_27_ZERO_REALITY_FRONTIER_V2.json"
OLD="canonical/governance/CURRENT_27_INFORMATION_DOMINANCE_V1.json"
OLDV="canonical/verification/CURRENT_27_INFORMATION_DOMINANCE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
REC="canonical/verification/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
EXPECTED={OLD:"fae786d6051277865ed6ecde69be5da98e2bf509",OLDV:"1931ae5a7edb5dde2021a8a4f7e7a3ad0fd821f1",REC:"6ec5f6d808c88bf9ea728fb7f259edc3b4ae5a51"}
REQ={
"BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_FINANCE_JUDGMENT_SOURCE_GATE_PASS",
"BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_UNKNOWN_DOMAIN_JUDGMENT_SOURCE_GATE_PASS",
}
CERT={"FINANCE_JUDGMENT_SOURCE_CERTIFICATE","UNKNOWN_DOMAIN_JUDGMENT_SOURCE_CERTIFICATE"}

def blob(path):
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def load(path): return json.loads((ROOT/path).read_text(encoding="utf-8"))

def evaluate():
    drift={p:{"expected":h,"actual":blob(p)} for p,h in EXPECTED.items() if blob(p)!=h}
    if drift: return {"pass":False,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT","errors":["SOURCE_BLOB_DRIFT"],"drift":drift}
    c,o,ov,r=load(CAND),load(OLD),load(OLDV),load(REC)
    errors=[]
    if not str(ov.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"): errors.append("PRIOR_DOMINANCE_NOT_VERIFIED")
    if not str(r.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"): errors.append("DISCHARGE_NOT_VERIFIED")
    if set((r.get("verified") or {}).get("discharged_requirements") or [])!=REQ: errors.append("DISCHARGE_RECEIPT_SET_DRIFT")
    oldreq=set(o.get("required_propositions") or [])
    oldcert=set(o.get("nondominated_certificate_ids") or [])
    if set(c.get("discharged_requirements") or [])!=REQ: errors.append("CANDIDATE_DISCHARGED_SET_DRIFT")
    if set(c.get("completed_certificates") or [])!=CERT: errors.append("CANDIDATE_COMPLETED_CERT_SET_DRIFT")
    if set(c.get("active_required_propositions") or [])!=(oldreq-REQ): errors.append("ACTIVE_REQUIREMENT_SET_NOT_EXACT_SUBTRACTION")
    if set(c.get("active_nondominated_certificate_ids") or [])!=(oldcert-CERT): errors.append("ACTIVE_CERT_SET_NOT_EXACT_SUBTRACTION")
    lw=c.get("live_world") or {}
    if (lw.get("prior_zero_reality_requirements"),lw.get("discharged_zero_reality_requirements"),lw.get("active_zero_reality_requirements"))!=(19,2,17): errors.append("REQUIREMENT_COUNTS")
    if (lw.get("prior_nondominated_certificates"),lw.get("completed_certificates"),lw.get("active_nondominated_certificates"))!=(16,2,14): errors.append("CERTIFICATE_COUNTS")
    if (lw.get("proved_predicates"),lw.get("unresolved_predicates"))!=(11,27): errors.append("PREDICATE_COUNTS_CHANGED")
    if c.get("acceptance_predicate_delta")!=0 or c.get("family_acceptance_delta")!=0 or c.get("ownership_delta")!=0: errors.append("CREDIT_OVERCLAIM")
    if c.get("fresh_reality_authority") is not False: errors.append("FRESH_REALITY_OVERCLAIM")
    ok=not errors
    return {"pass":ok,"status":"PASS__EXACT_19_MINUS_2_EQUALS_17_ZERO_REALITY_REQUIREMENT_FRONTIER__27_ACCEPTANCE_PREDICATES_UNCHANGED" if ok else "FAIL_CLOSED","errors":sorted(set(errors)),"active_requirement_count":17 if ok else None,"active_certificate_count":14 if ok else None,"unresolved_predicates":27,"acceptance_predicate_delta":0,"fresh_reality_authority":False}

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
