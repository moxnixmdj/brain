from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
THEOREM="canonical/governance/HONESTY_SELECTED_COVER_LOCALITY_THEOREM_20261007_V1.json"
SOURCES={
 "canonical/governance/L1_UNIVERSAL_ABC_NORMAL_FORM_THEOREM_20261007_V1.json":"cff6a95cad0027f3e142a32fd028a27566a00ea5",
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V11.json":"97412c8b7b107789c01906012163d3088991f1a4",
 "canonical/governance/SELECTED_COVER_LOCAL_TRANSFORM_CLOSURE_THEOREM_20261007_V1.json":"ea48341b1962c7c90cc78c6ef9affcabbe9abd26",
 "canonical/governance/HONESTY_CLOSED_WORLD_TOTALIZATION_V1.json":"7996512bdaa76c37ce79e0fabfbaafb77256f2d0",
 "canonical/verification/HONESTY_TARGET_SEMANTIC_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261006_V1.json":"1e164984ff1d41741246b489647b39373bd5c66f",
 "canonical/governance/HONESTY_ROOT3_SHARED_BOUNDARY_REDUCTION_V1.json":"e6e566fb2dbbdc58724433cc09d53d251be2e613",
 "canonical/governance/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_THEOREM_20261006_V1.json":"333bdc8306a19f005a600a47b415a4bd9cf9868c",
}

def blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load(rel:str):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def selected_honesty(routes:dict[str,bool], selected:set[str], influence:list[tuple[str,str]])->bool:
    closure=set(selected)
    changed=True
    while changed:
        changed=False
        for upstream,downstream in influence:
            if downstream in closure and upstream not in closure:
                closure.add(upstream); changed=True
    return all(routes.get(r) is True for r in closure)

def verify():
    errors=[]
    for rel,want in SOURCES.items():
        p=ROOT/rel
        if not p.is_file():
            errors.append("SOURCE_MISSING:"+rel); continue
        got=blob(p.read_bytes())
        if got!=want:
            errors.append("SOURCE_DRIFT:"+rel+":"+got)

    t=load(THEOREM)
    l1=load("canonical/governance/L1_UNIVERSAL_ABC_NORMAL_FORM_THEOREM_20261007_V1.json")
    v11=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V11.json")
    lc=load("canonical/governance/SELECTED_COVER_LOCAL_TRANSFORM_CLOSURE_THEOREM_20261007_V1.json")
    cw=load("canonical/governance/HONESTY_CLOSED_WORLD_TOTALIZATION_V1.json")
    sb=load("canonical/verification/HONESTY_TARGET_SEMANTIC_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261006_V1.json")
    hr=load("canonical/governance/HONESTY_ROOT3_SHARED_BOUNDARY_REDUCTION_V1.json")
    obs=load("canonical/governance/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_THEOREM_20261006_V1.json")

    if (l1.get("normal_form_effect_if_verified") or {}).get("independent_L1_predicates")!=["COMPLETE_SELECTED_CONTEXT_ABC"]:
        errors.append("L1_NOT_SINGLE_ABC")
    if (v11.get("current_truth") or {}).get("independent_top_level_terminal_predicates")!=["COMPLETE_SELECTED_CONTEXT_ABC","D_FINAL_ROUTE_OWNERSHIP_EFFECT_DONOR_INDEPENDENCE_FINALITY"]:
        errors.append("V11_TERMINAL_FORM_DRIFT")
    if ((v11.get("normal_form") or {}).get("ABC_COMPLETE_SELECTED_CONTEXT_COVER") or {}).get("scheduler_priority")!=1:
        errors.append("V11_ABC_NOT_PRIORITY_ONE")
    if "UNUSED_TRANSFORM_RULE" in "":
        pass
    local_rule=((lc.get("theorem") or {}).get("unused_transform_rule") or "")
    if "NO_C_CERTIFICATE_IS_REQUIRED" not in local_rule:
        errors.append("LOCAL_UNUSED_ROUTE_RULE_MISSING")
    if cw.get("remaining_single_root")!="CREDITED_CLOSED_WORLD_ENTRY_DOMINANCE":
        errors.append("HONESTY_NOT_REDUCED_TO_ENTRY_DOMINANCE")
    if ((sb.get("root_effect") or {}).get("independently_verified_closed_semantic_root")!="HONESTY_TARGET_SEMANTIC_BRIDGE"):
        errors.append("HONESTY_SEMANTIC_BRIDGE_NOT_VERIFIED")
    if hr.get("remaining_shared_root")!="C_EFFECT_BOUNDARY_CLOSURE_V2_WITH_HONESTY_GUARD_BINDING":
        errors.append("HONESTY_SHARED_BOUNDARY_ROOT_DRIFT")
    if ((obs.get("critical_split") or {}).get("target_universe_scope_state")!="STRUCTURALLY_SUPERSET_BY_OBSERVABLE_TRACE_DEFINITION"):
        errors.append("OBSERVABLE_SCOPE_NOT_BOUND")

    # Positive countermodel: unused bypass exists but cannot affect selected route.
    r1={"A":True,"Z":False}
    local1=selected_honesty(r1,{"A"},[])
    global1=all(r1.values())
    if not local1 or global1:
        errors.append("UNUSED_BYPASS_COUNTERMODEL_FAILED")

    # Negative canary: the same bypass becomes load-bearing upstream.
    if selected_honesty(r1,{"A"},[("Z","A")]):
        errors.append("CAUSAL_BYPASS_DID_NOT_REOPEN")

    # Negative canary: selected route itself unguarded.
    if selected_honesty({"A":False},{"A"},[]):
        errors.append("UNGUARDED_SELECTED_ROUTE_DID_NOT_REOPEN")

    # Positive canary: all selected causal closure members guarded; unrelated bypass ignored.
    r2={"A":True,"B":True,"Z":False}
    if not selected_honesty(r2,{"A"},[("B","A")]):
        errors.append("GUARDED_CAUSAL_CLOSURE_FALSE_NEGATIVE")

    c=t.get("consequence") or {}
    if c.get("global_honesty_entry_dominance_precondition_required") is not False:
        errors.append("THEOREM_GLOBAL_PRECONDITION_DRIFT")
    if c.get("selected_route_causal_closure_honesty_required") is not True:
        errors.append("THEOREM_LOCAL_REQUIREMENT_DRIFT")
    if c.get("current_complete_abc_closed") is not False:
        errors.append("THEOREM_FALSE_ABC_CREDIT")

    return {
      "schema":"PROJECT_BRAIN_HONESTY_SELECTED_COVER_LOCALITY_VERIFIER_V1",
      "status":"PASS__GLOBAL_HONESTY_ENTRY_DOMINANCE_STRONGER_THAN_NECESSARY__SELECTED_CAUSAL_CLOSURE_HONESTY_REQUIRED__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "countermodel":{"local_selected_honesty":local1,"global_all_route_honesty":global1},
      "negative_canaries_passed":not selected_honesty(r1,{"A"},[("Z","A")]) and not selected_honesty({"A":False},{"A"},[]),
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
    raise SystemExit(0 if verify()["pass"] else 1)
