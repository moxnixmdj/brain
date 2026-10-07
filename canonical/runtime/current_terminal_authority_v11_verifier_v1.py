from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUTH="canonical/governance/CURRENT_TERMINAL_AUTHORITY_V11.json"
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V10.json":"86d7cd3f96afc9330d5b474a33cc43018fc6ff6b",
 "canonical/governance/L1_UNIVERSAL_ABC_NORMAL_FORM_THEOREM_20261007_V1.json":"cff6a95cad0027f3e142a32fd028a27566a00ea5",
 "canonical/verification/L1_UNIVERSAL_ABC_NORMAL_FORM_SPRITE_VERIFICATION_20261007_V1.json":"ba3f84a6b9d9cdf520205c633626dbd33bff462c",
 "canonical/governance/CURRENT_ACCEPTED_FIVE_D_REDUCTION_20261007_V1.json":"a1d2dac1ab98462c3505543f8047442a60017d19",
 "canonical/verification/CURRENT_ACCEPTED_FIVE_D_REDUCTION_SPRITE_VERIFICATION_20261007_V1.json":"9b3d8906862e92ac17db8d307551607d90c28024",
 "canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V8.md":"04483828097a9804b1d5f8af19863546d7b3d892",
}
TOP=["COMPLETE_SELECTED_CONTEXT_ABC","D_FINAL_ROUTE_OWNERSHIP_EFFECT_DONOR_INDEPENDENCE_FINALITY"]

def blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load(rel:str):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def logical_normal_form(*,top:list[str],abc_closed:bool,d_closed:bool,l1_independent_count:int,current_d_residual:int):
    errors=[]
    if top!=TOP: errors.append("TOP_LEVEL_PREDICATE_SET_DRIFT")
    if l1_independent_count!=1: errors.append("L1_NOT_COLLAPSED_TO_ONE_ABC")
    if current_d_residual!=0: errors.append("CURRENT_ACCEPTED_D_RESIDUAL_NOT_ZERO")
    if abc_closed: errors.append("ABC_FALSELY_CLOSED")
    if d_closed: errors.append("D_FALSELY_CLOSED")
    return {"pass":not errors,"errors":errors}

def verify():
    errors=[]
    for rel,want in EXPECTED.items():
        p=ROOT/rel
        if not p.is_file():
            errors.append("SOURCE_MISSING:"+rel); continue
        got=blob(p.read_bytes())
        if got!=want: errors.append("SOURCE_DRIFT:"+rel+":"+got)
    a=load(AUTH)
    l1=load("canonical/governance/L1_UNIVERSAL_ABC_NORMAL_FORM_THEOREM_20261007_V1.json")
    l1v=load("canonical/verification/L1_UNIVERSAL_ABC_NORMAL_FORM_SPRITE_VERIFICATION_20261007_V1.json")
    d=load("canonical/governance/CURRENT_ACCEPTED_FIVE_D_REDUCTION_20261007_V1.json")
    dv=load("canonical/verification/CURRENT_ACCEPTED_FIVE_D_REDUCTION_SPRITE_VERIFICATION_20261007_V1.json")

    ct=a.get("current_truth") or {}
    if ct.get("independent_top_level_terminal_predicate_count")!=2: errors.append("TOP_COUNT_NOT_TWO")
    if ct.get("independent_top_level_terminal_predicates")!=TOP: errors.append("TOP_SET_DRIFT")
    if ct.get("accepted_families")!=5 or ct.get("open_families")!=14: errors.append("FAMILY_COUNTS_DRIFT")
    if ct.get("current_19_L1_rows_are_refinement_partitions") is not True: errors.append("L1_ROWS_NOT_REFINEMENTS")
    if ct.get("current_accepted_family_effect_mediator_residual_count")!=0: errors.append("D_CURRENT_RESIDUAL_NOT_ZERO")
    if ct.get("terminal") is not False: errors.append("TERMINAL_FALSE_REQUIRED")

    l1nf=l1.get("normal_form_effect_if_verified") or {}
    if l1nf.get("independent_L1_predicates")!=["COMPLETE_SELECTED_CONTEXT_ABC"]: errors.append("L1_SOURCE_NOT_ONE_ABC")
    if l1nf.get("D_ownership_effect_closure")!="REMAINS_SEPARATE_AND_OPEN": errors.append("L1_SOURCE_D_NOT_OPEN")
    if (l1v.get("verified") or {}).get("independent_l1_predicate_count")!=1: errors.append("L1_VERIFICATION_COUNT")
    if not str(l1v.get("status","")).startswith("INDEPENDENT_SPRITE_EXACT_BLOB_REPLAY_PASS"): errors.append("L1_VERIFICATION_NOT_PASS")

    if (d.get("current_D_effect_frontier") or {}).get("current_accepted_family_effect_mediator_residual_count")!=0: errors.append("D_SOURCE_CURRENT_RESIDUAL")
    if (d.get("current_D_effect_frontier") or {}).get("global_D_closed") is not False: errors.append("D_SOURCE_FALSELY_CLOSED")
    if (dv.get("result") or {}).get("current_accepted_family_effect_mediator_residual_count")!=0: errors.append("D_VERIFICATION_CURRENT_RESIDUAL")
    if (dv.get("result") or {}).get("global_D_closed") is not False: errors.append("D_VERIFICATION_FALSELY_CLOSED")
    if not str(dv.get("status","")).startswith("INDEPENDENT_SPRITE_EXACT_BYTE_REPLAY_PASS"): errors.append("D_VERIFICATION_NOT_PASS")

    nf=a.get("normal_form") or {}
    abc=nf.get("ABC_COMPLETE_SELECTED_CONTEXT_COVER") or {}
    dg=nf.get("D_FINAL_ROUTE_OWNERSHIP_EFFECT_DONOR_INDEPENDENCE_FINALITY") or {}
    ln=logical_normal_form(
      top=ct.get("independent_top_level_terminal_predicates") or [],
      abc_closed=bool(abc.get("closed")),
      d_closed=bool(dg.get("closed")),
      l1_independent_count=(l1v.get("verified") or {}).get("independent_l1_predicate_count",-1),
      current_d_residual=ct.get("current_accepted_family_effect_mediator_residual_count",-1),
    )
    errors.extend("NORMAL_FORM:"+x for x in ln["errors"])
    if a.get("terminal_form")!="COMPLETE_SELECTED_CONTEXT_ABC__AND__D_FINAL_ROUTE_OWNERSHIP_EFFECT_DONOR_INDEPENDENCE_FINALITY":
        errors.append("TERMINAL_FORM_DRIFT")
    return {
      "schema":"PROJECT_BRAIN_CURRENT_TERMINAL_AUTHORITY_V11_VERIFIER_V1",
      "status":"PASS__TWO_TOP_LEVEL_PREDICATES__ABC_ACTIVE_FRONTIER__CURRENT_ACCEPTED_D_LEAVES_SATURATED__GLOBAL_D_OPEN__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "independent_top_level_terminal_predicate_count":2 if not errors else None,
      "current_positive_frontier":"COMPLETE_SELECTED_CONTEXT_ABC" if not errors else None,
      "current_accepted_family_effect_mediator_residual_count":0 if not errors else None,
      "global_D_closed":False,
      "terminal":False,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
