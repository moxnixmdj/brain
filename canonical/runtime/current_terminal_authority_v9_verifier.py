from __future__ import annotations
import json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V9.json"

EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V8.json":"6e15e2163beae2c613287f69387b9d00cd88010b",
 "canonical/governance/SELECTED_COVER_LOCAL_TRANSFORM_CLOSURE_THEOREM_20261007_V1.json":"ea48341b1962c7c90cc78c6ef9affcabbe9abd26",
 "canonical/verification/SELECTED_COVER_LOCAL_TRANSFORM_CLOSURE_WOLFRAM_VERIFICATION_20261007_V1.json":"583c6a73c5e495292da88753309a6142d26ea338",
 "canonical/governance/FIVE_PRIMITIVE_ROLE_SINGLE_SEMANTIC_FRONTIER_20261007_V1.json":"eb316b0a674a3542280c71706fffe850d22e44fa",
 "canonical/governance/TARGET_UNDOMINATED_ESCAPE_REDUCTION_20261007_V1.json":"c6757e71f862dd592402199ac12afb8bca45c256",
 "canonical/governance/ROOT3_CREDITED_ROUTE_EFFECT_FOOTPRINT_COMPILER_20261007_V1.json":"a8448eb871831242a204fdb579bce6717d7b6621",
}

def blob(rel):
    cp=subprocess.run(["git","-C",str(ROOT),"rev-parse",f"HEAD:{rel}"],text=True,capture_output=True,check=False)
    return cp.stdout.strip() if cp.returncode==0 else ""

def verify():
    errors=[]
    for rel,sha in EXPECTED.items():
        if blob(rel)!=sha:
            errors.append("SOURCE_DRIFT:"+rel)
    d=json.loads(AUTH.read_text(encoding="utf-8"))
    p=d["preserved_truth"]
    if (p["open_truth_obligations"],p["accepted_families"],p["open_families"],p["terminal"])!=(29,5,14,False):
        errors.append("TRUTH_COUNTS_DRIFT")
    abc=d["proof_surfaces"]["ABC_SELECTED_CONTEXT_COVER"]
    req=set(abc["per_selected_cell_required"])
    needed={
      "SOUND_TARGET_OR_SUPERDOMAIN_CELL_BINDING",
      "SOUND_BRAIN_POLICY_PRIMITIVE_ADEQUACY_OR_DISTRIBUTIONAL_DOMINANCE_WITNESS",
      "CONTENT_ADDRESSED_ACTUAL_ROUTE_AND_TRANSFORM_BINDINGS",
      "COMPLETE_LOAD_BEARING_SOURCE_AND_TARGET_STATE_QUOTIENTS_FOR_TRANSFORMS_USED_BY_THE_ROUTE",
      "QUOTIENT_LEVEL_EVALUATOR_PULLBACK_CERTIFICATES",
      "HARD_CONSTRAINT_PREIMAGE_OR_FAIL_CLOSED_INVARIANT_WITNESSES",
    }
    if not needed <= req:
        errors.append("ABC_CELL_REQUIREMENTS_INCOMPLETE")
    if "GLOBAL_C_FIRST_AS_A_PRECONDITION_TO_ALL_A_B_WORK" not in d["deleted_scheduler_work"]:
        errors.append("GLOBAL_C_FIRST_NOT_DELETED")
    if d["proof_surfaces"]["D_BRAIN_OWNERSHIP_AND_EFFECT_CLOSURE"]["closed"] is not False:
        errors.append("D_FALSELY_CLOSED")
    if d["accounting"]["terminal_credit_delta"]!=0:
        errors.append("NONZERO_TERMINAL_CREDIT")
    return {"status":"PASS__V9_SELECTED_CONTEXT_ABC_AUTHORITY_BOUND" if not errors else "FAIL_CLOSED","pass":not errors,"errors":errors,"terminal_credit_delta":0}

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
