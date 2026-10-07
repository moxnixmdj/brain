from __future__ import annotations
import json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V8.json"

EXPECTED={
  "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V7.json":"5ad4fd7600fe6db3cf7e28c925600d22470f5757",
  "canonical/governance/C_LOAD_BEARING_STATE_QUOTIENT_THEOREM_20261007_V1.json":"01f1caa2b9cce4e4a0279f6b38ac44d8d225d95e",
  "canonical/verification/C_LOAD_BEARING_STATE_QUOTIENT_WOLFRAM_VERIFICATION_20261007_V1.json":"d69033a23ffce8b8f4907450b42b9f21f2903c2e",
  "canonical/governance/STOCHASTIC_KERNEL_TRANSFORM_UNIVERSALITY_20261007_V1.json":"658f12eba91a85dbf67dac82b8fb1f6650cc3934",
  "canonical/governance/ROOT3_CREDITED_ROUTE_EFFECT_FOOTPRINT_COMPILER_20261007_V1.json":"a8448eb871831242a204fdb579bce6717d7b6621",
}

def git_blob(rel:str)->str:
    cp=subprocess.run(["git","-C",str(ROOT),"rev-parse",f"HEAD:{rel}"],text=True,capture_output=True,check=False)
    return cp.stdout.strip() if cp.returncode==0 else ""

def verify()->dict:
    errors=[]
    for rel,sha in EXPECTED.items():
        if git_blob(rel)!=sha:
            errors.append("SOURCE_DRIFT:"+rel)
    d=json.loads(AUTH.read_text(encoding="utf-8"))
    p=d["preserved_truth"]
    if (p["open_truth_obligations"],p["accepted_families"],p["open_families"],p["terminal"])!=(29,5,14,False):
        errors.append("TRUTH_COUNTS_DRIFT")
    c=d["invariant_normal_form"]["C_COMPOSITION_AND_TRANSFORM_CLOSURE"]
    if "FULL_INTERNAL_SOURCE_AND_TARGET_STATE_ENUMERATION_AS_A_SEPARATE_REQUIREMENT" not in c["deleted_requirements"]:
        errors.append("FULL_STATE_REQUIREMENT_REOPENED")
    if "BIND_ONLY_A_COMPLETE_LOAD_BEARING_STATE_QUOTIENT" not in c["state_boundary_rule"]:
        errors.append("QUOTIENT_RULE_MISSING")
    if d["accounting"]["terminal_credit_delta"]!=0:
        errors.append("NONZERO_CREDIT")
    return {
      "status":"PASS__V8_LOAD_BEARING_QUOTIENT_AUTHORITY_BOUND" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "terminal_credit_delta":0
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
