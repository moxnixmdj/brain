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
    if r.get("brain_owned") is not True:
        return False
    if r.get("donor_independent") is not True:
        return False
    if r.get("external_capability_provider") is True:
        return False
    if r.get("incremental_spend_usd") != 0:
        return False
    return True

def terminal_cover(contexts:set[str], selected:dict[str,list[dict]]):
    missing=[]
    for c in sorted(contexts):
        routes=selected.get(c) or []
        good=[]
        for r in routes:
            if r.get("current") is not True:
                continue
            if not route_owned(r):
                continue
            if all(r.get(k) is True for k in ("A","B","C","D")):
                good.append(r)
        if not good:
            missing.append(c)
    return {
      "pass":not missing,
      "missing_contexts":missing,
      "independent_terminal_predicate":"COMPLETE_SELECTED_CONTEXT_ABCD_COVER",
      "terminal_credit_delta":0,
    }

def _owned_route(**overrides):
    r={
      "A":True,"B":True,"C":True,"D":True,"current":True,
      "brain_owned":True,"donor_independent":True,
      "external_capability_provider":False,"incremental_spend_usd":0,
    }
    r.update(overrides)
    return r

def verify():
    errors=[]
    for rel,want in EXPECTED.items():
        if blob(rel)!=want:
            errors.append("SOURCE_DRIFT:"+rel)

    th=json.loads(THEOREM.read_text(encoding="utf-8"))
    l1=load("canonical/governance/L1_UNIVERSAL_ABC_NORMAL_FORM_THEOREM_20261007_V1.json")
    r3=load("canonical/governance/ROOT3_CREDITED_ROUTE_EFFECT_FOOTPRINT_TOTALITY_20261007_V1.json")
    r3v=load("canonical/verification/ROOT3_CREDITED_ROUTE_EFFECT_FOOTPRINT_TOTALITY_WOLFRAM_VERIFICATION_20261007_V1.json")
    dr=load("canonical/governance/D_ACCEPTED_ROUTE_EFFECT_CLOSURE_REDUCTION_20261007_V1.json")
    donor=load("canonical/verification/TERMINAL_V3_DONOR_DELETION_CLEANROOM_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
    own=load("canonical/verification/GLOBAL_OWNERSHIP_POSTCONDITIONS_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
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
    if nf.get("D_ownership_effect_closure")!="REMAINS_SEPARATE_AND_OPEN":
        errors.append("L1_SOURCE_D_STATE_DRIFT")

    rt=r3.get("theorem") or {}
    premises=set(rt.get("required_premises") or [])
    needed={
      "CREDITED_ROUTE_IDENTITY: every route receiving terminal credit is content-addressed and included in R.",
      "FAIL_CLOSED_OUTSIDE_FOOTPRINT: an attempted material effect not in the proved footprint cannot commit.",
      "INVALIDATION_RULE: any change to credited route bytes routing effect wrappers broker registry or support paths invalidates the footprint certificate until recomputed.",
    }
    if not needed<=premises:
        errors.append("ROOT3_ROUTE_LOCAL_PREMISES_INCOMPLETE")
    if "CREDITED_DEPLOYED_ROUTE_SET" not in str(rt.get("conclusion") or ""):
        errors.append("ROOT3_CONCLUSION_NOT_ROUTE_LOCAL")
    if "PASS" not in str(r3v.get("status") or ""):
        errors.append("ROOT3_VERIFICATION_NOT_PASS")

    part=dr.get("accepted_route_partition") or {}
    ef=(part.get("effect_free_selected_routes") or {})
    if ef.get("count")!=4 or (ef.get("compiled_footprint") or {}).get("material_effect_count")!=0:
        errors.append("CURRENT_EFFECT_FREE_PARTITION_DRIFT")
    cont=part.get("continuity_selected_route") or {}
    want_effects={"file.open_write","file.remove","file.rename","file.directory_mutation"}
    if set(cont.get("owned_effect_classes") or [])!=want_effects:
        errors.append("CONTINUITY_EFFECT_SET_DRIFT")
    if "NO_D_CLOSURE" not in (dr.get("hard_nonclaims") or []):
        errors.append("D_REDUCTION_FALSELY_CLOSED")

    if donor.get("donor_classification")!="NO_TARGET_CAPABILITY_DONOR_REACHABLE_IN_FROZEN_TERMINAL_EXECUTION_ROUTE":
        errors.append("HISTORICAL_DONOR_WITNESS_DRIFT")
    if donor.get("behavior_preserved") is not True:
        errors.append("HISTORICAL_DONOR_BEHAVIOR_NOT_PRESERVED")
    op=(own.get("result") or {}).get("terminal_predicates") or {}
    if op.get("final_donor_deletion_cleanroom_pass") is not True:
        errors.append("HISTORICAL_OWNERSHIP_CLEANROOM_NOT_PASS")

    defs=th.get("definitions") or {}
    d=str(defs.get("D") or "")
    for token in ("BRAIN_OWNED","DONOR_INDEPENDENT","MATERIAL_EFFECT_FOOTPRINT","FAIL_CLOSED","DRIFT"):
        if token not in d:
            errors.append("D_DEFINITION_MISSING:"+token)
    tm=str((th.get("theorem") or {}).get("terminal_normal_form") or "")
    if "FOR_EVERY_c_IN_U" not in tm or "ABCD(c,r)" not in tm:
        errors.append("TERMINAL_NORMAL_FORM_INVALID")
    sched=th.get("scheduler_effect") or []
    if not any("CO_CERTIFY_D" in x for x in sched):
        errors.append("D_NOT_CO_CERTIFIED")

    positive=terminal_cover({"c0","c1"},{"c0":[_owned_route()],"c1":[_owned_route()]})
    if not positive["pass"]:
        errors.append("FINITE_POSITIVE_MODEL_FAIL")

    external=terminal_cover({"c"},{"c":[_owned_route(external_capability_provider=True)]})
    if external["pass"]:
        errors.append("EXTERNAL_PROVIDER_FALSELY_OWNED")

    paid=terminal_cover({"c"},{"c":[_owned_route(incremental_spend_usd=1)]})
    if paid["pass"]:
        errors.append("NONZERO_SPEND_FALSELY_ADMITTED")

    return {
      "schema":"PROJECT_BRAIN_TERMINAL_ONE_PREDICATE_ABCD_NORMAL_FORM_VERIFIER_V2",
      "status":"PASS__MISSION_V8_BOUND__ONE_INDEPENDENT_TERMINAL_PREDICATE_ABCD_COVER__D_ROUTE_LOCALIZED__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "independent_terminal_predicate_count":1 if not errors else None,
      "independent_terminal_predicate":"COMPLETE_SELECTED_CONTEXT_ABCD_COVER" if not errors else None,
      "mission_lock":"V8" if not errors else None,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
