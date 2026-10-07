from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
THEOREM=ROOT/"canonical/governance/TERMINAL_ONE_PREDICATE_ABCD_NORMAL_FORM_THEOREM_20261007_V1.json"

EXPECTED={
 "canonical/governance/L1_UNIVERSAL_ABC_NORMAL_FORM_THEOREM_20261007_V1.json":"cff6a95cad0027f3e142a32fd028a27566a00ea5",
 "canonical/governance/ROOT3_CREDITED_ROUTE_EFFECT_FOOTPRINT_TOTALITY_20261007_V1.json":"9fd755465ae17b19335987b78c154afa6434ab3a",
 "canonical/verification/ROOT3_CREDITED_ROUTE_EFFECT_FOOTPRINT_TOTALITY_WOLFRAM_VERIFICATION_20261007_V1.json":"47496b53eec767ea39a1ca147837df0baba65a0a",
 "canonical/governance/D_ACCEPTED_ROUTE_EFFECT_CLOSURE_REDUCTION_20261007_V1.json":"63e76c571e5fc14b0135de238db7a3228f046a71",
 "canonical/governance/CURRENT_ACCEPTED_FIVE_D_REDUCTION_20261007_V1.json":"a1d2dac1ab98462c3505543f8047442a60017d19",
 "canonical/verification/CURRENT_ACCEPTED_FIVE_D_REDUCTION_SPRITE_VERIFICATION_20261007_V1.json":"9b3d8906862e92ac17db8d307551607d90c28024",
 "canonical/verification/TERMINAL_V3_DONOR_DELETION_CLEANROOM_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"d3144bf0aa618b15ef594d24de54d55cbdb329fd",
 "canonical/verification/GLOBAL_OWNERSHIP_POSTCONDITIONS_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"e0dbd996c18bdb818693ab0d217d751594a03d0f",
 "canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V8.md":"04483828097a9804b1d5f8af19863546d7b3d892",
 "canonical/verification/MISSION_LOCK_V8_RECONCILIATION_VERIFICATION_20261007_V1.json":"d8112421ff9b41cc842dc812ecfd8e13b58bb3ac",
}

def blob(rel:str)->str:
    p=ROOT/rel
    if not p.exists(): return ""
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(rel:str):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def route_owned(r:dict)->bool:
    return (
      r.get("brain_owned") is True
      and r.get("donor_independent") is True
      and r.get("external_capability_provider") is not True
      and r.get("incremental_spend_usd")==0
    )

def route_abcd_current(r:dict)->bool:
    return (
      r.get("current") is True
      and route_owned(r)
      and all(r.get(k) is True for k in ("A","B","C","D"))
    )

def terminal_cover(contexts:set[str], selected:dict[str,list[dict]], finality:dict):
    invalid_credited=[]
    good_by_context={}
    for c,routes in selected.items():
        good=[]
        for i,r in enumerate(routes or []):
            credited=r.get("credited") is True
            ok=route_abcd_current(r)
            if credited and not ok:
                invalid_credited.append(f"{c}:{i}")
            if credited and ok:
                good.append(r)
        good_by_context[c]=good

    missing=[c for c in sorted(contexts) if not good_by_context.get(c)]
    finality_ok=all(finality.get(k) is True for k in (
      "route_set_content_addressed",
      "route_set_fixed",
      "D_recomputed_for_final_route_set",
      "donor_removal_cleanroom_pass",
    ))
    return {
      "pass":not missing and not invalid_credited and finality_ok,
      "missing_contexts":missing,
      "invalid_credited_routes":invalid_credited,
      "finality_pass":finality_ok,
      "independent_terminal_predicate":"COMPLETE_SELECTED_CONTEXT_ABCD_COVER",
      "terminal_credit_delta":0,
    }

def _owned_route(**overrides):
    r={
      "A":True,"B":True,"C":True,"D":True,"current":True,"credited":True,
      "brain_owned":True,"donor_independent":True,
      "external_capability_provider":False,"incremental_spend_usd":0,
    }
    r.update(overrides)
    return r

def _finality(**overrides):
    x={
      "route_set_content_addressed":True,
      "route_set_fixed":True,
      "D_recomputed_for_final_route_set":True,
      "donor_removal_cleanroom_pass":True,
    }
    x.update(overrides)
    return x

def verify():
    errors=[]
    for rel,want in EXPECTED.items():
        if blob(rel)!=want:
            errors.append("SOURCE_DRIFT:"+rel)

    th=json.loads(THEOREM.read_text(encoding="utf-8"))
    l1=load("canonical/governance/L1_UNIVERSAL_ABC_NORMAL_FORM_THEOREM_20261007_V1.json")
    r3=load("canonical/governance/ROOT3_CREDITED_ROUTE_EFFECT_FOOTPRINT_TOTALITY_20261007_V1.json")
    r3v=load("canonical/verification/ROOT3_CREDITED_ROUTE_EFFECT_FOOTPRINT_TOTALITY_WOLFRAM_VERIFICATION_20261007_V1.json")
    current5=load("canonical/governance/CURRENT_ACCEPTED_FIVE_D_REDUCTION_20261007_V1.json")
    current5v=load("canonical/verification/CURRENT_ACCEPTED_FIVE_D_REDUCTION_SPRITE_VERIFICATION_20261007_V1.json")
    mission=(ROOT/"canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V8.md").read_text(encoding="utf-8")

    for token in (
      "Brain must permanently possess the useful capabilities of Claude Opus 5.5 at equal-or-better useful performance.",
      "Capability(ExactBrainOwnedRoute(C)) >= Capability(Opus5.5(C))",
      'If the only operative instruction is "call model/service X because X already has C", C is not owned.',
      "invention or architecture redesign is admissible",
    ):
        if token not in mission:
            errors.append("MISSION_V8_SEMANTIC_DRIFT:"+token[:40])

    nf=l1.get("normal_form_effect_if_verified") or {}
    if nf.get("independent_L1_predicates")!=["COMPLETE_SELECTED_CONTEXT_ABC"]:
        errors.append("L1_NOT_ONE_PREDICATE")

    rt=r3.get("theorem") or {}
    premises=set(rt.get("required_premises") or [])
    for need in (
      "CREDITED_ROUTE_IDENTITY: every route receiving terminal credit is content-addressed and included in R.",
      "FAIL_CLOSED_OUTSIDE_FOOTPRINT: an attempted material effect not in the proved footprint cannot commit.",
      "INVALIDATION_RULE: any change to credited route bytes routing effect wrappers broker registry or support paths invalidates the footprint certificate until recomputed.",
    ):
        if need not in premises:
            errors.append("ROOT3_MISSING:"+need.split(":")[0])
    if "PASS" not in str(r3v.get("status") or ""):
        errors.append("ROOT3_VERIFICATION_NOT_PASS")

    frontier=current5.get("current_D_effect_frontier") or {}
    if frontier.get("current_accepted_family_effect_mediator_residual_count")!=0:
        errors.append("CURRENT_ACCEPTED_FIVE_D_RESIDUAL_NONZERO")
    if frontier.get("global_D_closed") is not False:
        errors.append("CURRENT_ACCEPTED_FIVE_FALSELY_GLOBAL_CLOSED")
    future=set(frontier.get("future_contingent_residuals") or [])
    if "FINAL_DONOR_REMOVAL_AND_CLEAN_ROOM_REPLAY_OVER_THE_FINAL_CREDITED_ROUTE_SET" not in future:
        errors.append("FINAL_CLEANROOM_NOT_PRESERVED")
    if "PASS" not in str(current5v.get("status") or ""):
        errors.append("CURRENT_ACCEPTED_FIVE_VERIFICATION_NOT_PASS")

    defs=th.get("definitions") or {}
    if "FINAL_CONTENT_ADDRESSED_SET" not in str(defs.get("R") or ""):
        errors.append("FINAL_R_NOT_DEFINED")
    d=str(defs.get("D") or "")
    for token in ("D(R,r)","BRAIN_OWNED","DONOR_INDEPENDENT","FINAL_D_RECOMPUTE_DONOR_REMOVAL","CLEAN_ROOM_REPLAY"):
        if token not in d:
            errors.append("D_FINALITY_DEFINITION_MISSING:"+token)
    tm=str((th.get("theorem") or {}).get("terminal_normal_form") or "")
    for token in ("FINAL_CONTENT_ADDRESSED_CREDITED_ROUTE_SET_R","FOR_EVERY_c_IN_U","ABCD(R,c,r)","CLEAN_ROOM_REPLAY"):
        if token not in tm:
            errors.append("TERMINAL_NORMAL_FORM_MISSING:"+token)

    positive=terminal_cover({"c0","c1"},{"c0":[_owned_route()],"c1":[_owned_route()]},_finality())
    if not positive["pass"]:
        errors.append("FINITE_POSITIVE_MODEL_FAIL")
    if terminal_cover({"c"},{"c":[_owned_route(D=False)]},_finality())["pass"]:
        errors.append("MISSING_D_FALSELY_PASSES")
    if terminal_cover({"c"},{"c":[_owned_route()]},_finality(donor_removal_cleanroom_pass=False))["pass"]:
        errors.append("MISSING_FINAL_CLEANROOM_FALSELY_PASSES")
    if terminal_cover({"c"},{"c":[_owned_route(),_owned_route(credited=True,D=False)]},_finality())["pass"]:
        errors.append("INVALID_CREDITED_ROUTE_FALSELY_IGNORED")

    return {
      "schema":"PROJECT_BRAIN_TERMINAL_ONE_PREDICATE_ABCD_NORMAL_FORM_VERIFIER_V3",
      "status":"PASS__MISSION_V8__ONE_TERMINAL_PREDICATE__FINAL_ROUTESET_D_CLEANROOM_BOUND__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "independent_terminal_predicate_count":1 if not errors else None,
      "independent_terminal_predicate":"COMPLETE_SELECTED_CONTEXT_ABCD_COVER" if not errors else None,
      "mission_lock":"V8" if not errors else None,
      "current_accepted_five_D_effect_residual_count":0 if not errors else None,
      "final_route_set_cleanroom_required":True if not errors else None,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
