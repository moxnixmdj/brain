from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
THEOREM=ROOT/"canonical/governance/DIRECT_END_TO_END_ROUTE_DOMINANCE_LOCAL_C_NECESSITY_FALSIFICATION_20261007_V1.json"

EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V11.json":"97412c8b7b107789c01906012163d3088991f1a4",
 "canonical/governance/SELECTED_COVER_LOCAL_TRANSFORM_CLOSURE_THEOREM_20261007_V1.json":"ea48341b1962c7c90cc78c6ef9affcabbe9abd26",
 "canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V8.md":"04483828097a9804b1d5f8af19863546d7b3d892",
}

def blob(rel:str)->str:
    p=ROOT/rel
    if not p.exists(): return ""
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def bypass_decision(cert:dict)->dict:
    required=(
      "exact_final_route_bound",
      "scope_complete",
      "evaluator_complete",
      "hard_constraint_complete",
      "independent_or_objective",
      "final_route_noninferior",
    )
    missing=[k for k in required if cert.get(k) is not True]
    upstream=cert.get("upstream_only") is True
    if upstream:
        missing.append("UPSTREAM_ONLY")
    return {
      "pass":not missing,
      "separate_local_C_required":False if not missing else True,
      "missing":missing,
      "terminal_credit_delta":0,
    }

def verify():
    errors=[]
    for rel,want in EXPECTED.items():
        if blob(rel)!=want:
            errors.append("SOURCE_DRIFT:"+rel)
    th=json.loads(THEOREM.read_text(encoding="utf-8"))
    local=json.loads((ROOT/"canonical/governance/SELECTED_COVER_LOCAL_TRANSFORM_CLOSURE_THEOREM_20261007_V1.json").read_text(encoding="utf-8"))
    v11=json.loads((ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V11.json").read_text(encoding="utf-8"))

    if local.get("theorem",{}).get("sufficiency") is None:
        errors.append("LOCAL_C_SUFFICIENCY_MISSING")
    if v11.get("normal_form",{}).get("ABC_COMPLETE_SELECTED_CONTEXT_COVER",{}).get("closed") is not False:
        errors.append("V11_ABC_FALSELY_CLOSED")

    good=bypass_decision({
      "exact_final_route_bound":True,
      "scope_complete":True,
      "evaluator_complete":True,
      "hard_constraint_complete":True,
      "independent_or_objective":True,
      "final_route_noninferior":True,
      "upstream_only":False,
    })
    if not good["pass"] or good["separate_local_C_required"]:
        errors.append("DIRECT_E2E_BYPASS_POSITIVE_MODEL_FAIL")

    bad_upstream=bypass_decision({
      "exact_final_route_bound":True,
      "scope_complete":True,
      "evaluator_complete":True,
      "hard_constraint_complete":True,
      "independent_or_objective":True,
      "final_route_noninferior":True,
      "upstream_only":True,
    })
    if bad_upstream["pass"]:
        errors.append("UPSTREAM_CERT_FALSELY_BYPASSES")

    rule=str(th.get("theorem",{}).get("bypass_rule") or "")
    for token in ("EXACT_DEPLOYED_ROUTE","SCOPE_COMPLETE","EVERY_LOAD_BEARING_EVALUATOR","HARD_CONSTRAINT","INDEPENDENT_OR_OBJECTIVE"):
        if token not in rule:
            errors.append("BYPASS_RULE_MISSING:"+token)

    return {
      "schema":"PROJECT_BRAIN_DIRECT_END_TO_END_LOCAL_C_NECESSITY_VERIFIER_V1",
      "status":"PASS__DIRECT_FINAL_ROUTE_SCOPE_COMPLETE_PROOF_MAY_BYPASS_SEPARATE_LOCAL_C__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
