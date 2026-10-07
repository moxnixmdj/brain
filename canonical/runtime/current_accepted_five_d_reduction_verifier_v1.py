from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

SOURCES={
 "canonical/capabilities/opus55/OPUS55_LONG_HORIZON_MEMORY_AND_CONTINUITY_V1.json":"2d912cf8df64bd806fffb6a1070d95644d005470",
 "canonical/governance/D_ACCEPTED_ROUTE_EFFECT_CLOSURE_REDUCTION_20261007_V1.json":"63e76c571e5fc14b0135de238db7a3228f046a71",
 "canonical/verification/CONTINUITY_SELECTED_ROUTE_D_VERIFICATION_20261007_V2.json":"423d3298db4499131c4b2e27dee985e61c8e9af0",
 "canonical/governance/CONTINUITY_CREDITED_REBIND_20261007_V1.json":"839af46fd8ef214251b44bd1398fa2d1543f00c5",
 "canonical/governance/ACCEPTED_PURE_ROUTE_EFFECT_FOOTPRINT_OUTPUT_20261007_V2.json":"0720daf2fccce24932538e6ee0cc53db3d0472da",
 "canonical/governance/L1_UNIVERSAL_ABC_NORMAL_FORM_THEOREM_20261007_V1.json":"cff6a95cad0027f3e142a32fd028a27566a00ea5",
}
EXPECTED_EFFECTS={"file.open_write","file.remove","file.rename","file.directory_mutation"}
EXPECTED_PREFIXES={
 "canonical/same_identity_worker/state",
 "canonical/same_identity_worker/evidence",
 "canonical/same_identity_worker/external_tool_bridge",
}
EFFECT_FREE={
 "accepted.delegation","accepted.exact_symbolic","accepted.recovery","accepted.tool_discovery"
}

def blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load(rel:str):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def reduce_current_d(*,effect_free_count:int,continuity_owned:bool,continuity_confined:bool,
                     raw_subprocess_reachable:bool,downstream_separate:bool):
    errors=[]
    if effect_free_count!=4: errors.append("EFFECT_FREE_COUNT_NOT_FOUR")
    if not continuity_owned: errors.append("CONTINUITY_NOT_OWNED")
    if not continuity_confined: errors.append("CONTINUITY_EFFECT_ESCAPE")
    if raw_subprocess_reachable: errors.append("CONTINUITY_RAW_SUBPROCESS_REACHABLE")
    if not downstream_separate: errors.append("DOWNSTREAM_SCOPE_CONFLATION")
    return {
      "pass":not errors,
      "errors":errors,
      "current_accepted_family_effect_mediator_residual_count":0 if not errors else None,
      "global_D_closed":False,
    }

def verify():
    errors=[]
    for rel,want in SOURCES.items():
        p=ROOT/rel
        if not p.is_file():
            errors.append("SOURCE_MISSING:"+rel); continue
        got=blob(p.read_bytes())
        if got!=want: errors.append("SOURCE_DRIFT:"+rel+":"+got)

    pkg=load("canonical/capabilities/opus55/OPUS55_LONG_HORIZON_MEMORY_AND_CONTINUITY_V1.json")
    dred=load("canonical/governance/D_ACCEPTED_ROUTE_EFFECT_CLOSURE_REDUCTION_20261007_V1.json")
    cver=load("canonical/verification/CONTINUITY_SELECTED_ROUTE_D_VERIFICATION_20261007_V2.json")
    reb=load("canonical/governance/CONTINUITY_CREDITED_REBIND_20261007_V1.json")
    foot=load("canonical/governance/ACCEPTED_PURE_ROUTE_EFFECT_FOOTPRINT_OUTPUT_20261007_V2.json")
    l1=load("canonical/governance/L1_UNIVERSAL_ABC_NORMAL_FORM_THEOREM_20261007_V1.json")

    if pkg.get("family")!="LONG_HORIZON_MEMORY_AND_CONTINUITY": errors.append("FAMILY_DRIFT")
    if pkg.get("status")!="VERIFIED_OWNED_EQUAL_OR_BETTER": errors.append("CONTINUITY_NOT_ACCEPTED_OWNED")
    br=pkg.get("brain_owned_route") or {}
    if br.get("external_hidden_capability_provider_required") is not False: errors.append("HIDDEN_PROVIDER_REQUIRED")
    if br.get("supervisor_git_blob")!="47c461f502e840def0c38728e1bfd7c6401cb804": errors.append("ACCEPTED_SUPERVISOR_BLOB_DRIFT")
    excl=set(pkg.get("excluded_scope") or [])
    if "ARBITRARY_COGNITIVE_COMPETENCE" not in excl: errors.append("ARBITRARY_COGNITION_NOT_EXCLUDED")
    own=pkg.get("ownership_tests") or {}
    if not str(own.get("no_hidden_capability_provider_test","")).startswith("PASS"): errors.append("OWNERSHIP_PROVIDER_TEST_NOT_PASS")
    if not str(own.get("general_substrate_test","")).startswith("PASS"): errors.append("OWNERSHIP_SUBSTRATE_TEST_NOT_PASS")

    if reb.get("accepted_blob")!="47c461f502e840def0c38728e1bfd7c6401cb804": errors.append("REBIND_ACCEPTED_BLOB_DRIFT")
    if reb.get("credited_path_blob")!=reb.get("accepted_blob"): errors.append("CREDITED_BLOB_NOT_ACCEPTED_BLOB")

    routes=foot.get("credited_routes") or []
    if foot.get("status")!="PASS__CREDITED_ROUTE_EFFECT_FOOTPRINT_COMPILED": errors.append("FOOTPRINT_NOT_PASS")
    if int(foot.get("credited_route_count",-1))!=4: errors.append("FOOTPRINT_ROUTE_COUNT")
    if int(foot.get("material_effect_count",-1))!=0: errors.append("FOOTPRINT_NONZERO_EFFECTS")
    if {r.get("route_id") for r in routes}!=EFFECT_FREE: errors.append("EFFECT_FREE_ROUTE_SET_DRIFT")

    cont=(dred.get("accepted_route_partition") or {}).get("continuity_selected_route") or {}
    if set(cont.get("owned_effect_classes") or [])!=EXPECTED_EFFECTS: errors.append("CONTINUITY_EFFECT_CLASS_DRIFT")
    if set(cont.get("confined_prefixes") or [])!=EXPECTED_PREFIXES: errors.append("CONTINUITY_PREFIX_DRIFT")

    reach=cver.get("reachability") or {}
    fs=cver.get("filesystem") or {}
    te=cver.get("truth_effect") or {}
    if reach.get("raw_default_subprocess_executor_reachable") is not False: errors.append("RAW_SUBPROCESS_REACHABLE")
    if fs.get("result")!="PASS__FIXED_SELECTED_ROUTE_FILESYSTEM_EFFECTS_CONFINED": errors.append("FILESYSTEM_CONFINEMENT_NOT_PASS")
    if set(fs.get("effect_classes") or [])!=EXPECTED_EFFECTS: errors.append("VERIFIED_EFFECT_SET_DRIFT")
    if set(fs.get("allowed_prefixes") or [])!=EXPECTED_PREFIXES: errors.append("VERIFIED_PREFIX_SET_DRIFT")
    if te.get("downstream_mission_effects")!="SEPARATE_ROOT3_GOVERNED_COMPOSED_ROUTE_LEAF": errors.append("DOWNSTREAM_NOT_SEPARATE")

    nf=l1.get("normal_form_effect_if_verified") or {}
    if nf.get("independent_L1_predicates")!=["COMPLETE_SELECTED_CONTEXT_ABC"]: errors.append("L1_NOT_ONE_ABC")
    if nf.get("D_ownership_effect_closure")!="REMAINS_SEPARATE_AND_OPEN": errors.append("D_FALSELY_CLOSED_UPSTREAM")

    reduced=reduce_current_d(
      effect_free_count=int(foot.get("credited_route_count",-1)),
      continuity_owned=not any(x in errors for x in ["CONTINUITY_NOT_ACCEPTED_OWNED","HIDDEN_PROVIDER_REQUIRED","OWNERSHIP_PROVIDER_TEST_NOT_PASS","OWNERSHIP_SUBSTRATE_TEST_NOT_PASS","CREDITED_BLOB_NOT_ACCEPTED_BLOB"]),
      continuity_confined=fs.get("result")=="PASS__FIXED_SELECTED_ROUTE_FILESYSTEM_EFFECTS_CONFINED",
      raw_subprocess_reachable=bool(reach.get("raw_default_subprocess_executor_reachable")),
      downstream_separate=te.get("downstream_mission_effects")=="SEPARATE_ROOT3_GOVERNED_COMPOSED_ROUTE_LEAF",
    )
    errors.extend("REDUCTION:"+e for e in reduced["errors"])
    return {
      "schema":"PROJECT_BRAIN_CURRENT_ACCEPTED_FIVE_D_REDUCTION_VERIFIER_V1",
      "status":"PASS__CURRENT_ACCEPTED_FIVE_HAVE_ZERO_EFFECT_MEDIATOR_RESIDUAL__GLOBAL_D_STILL_OPEN_FOR_FUTURE_ROUTES_AND_FINALITY__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "current_accepted_family_effect_mediator_residual_count":0 if not errors else None,
      "global_D_closed":False,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
