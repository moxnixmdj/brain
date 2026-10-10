"""Fresh generated proof cases for the six remaining terminal behavioral routes.

Evaluation infrastructure only. Candidate code must never import this module.
"""
from __future__ import annotations

import base64, hashlib, random
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_REMAINING_BEHAVIOR_PROOF_SUITES_V1"

OBLIGATION_MAP={
 "aggregate":("component_omission","component_mapping","weight_or_factor","correlation_or_interaction","unit_or_scale","aggregation_formula"),
 "selection":("ordering_precedence","missing_value","tie_or_duplicate","fallback_scope"),
 "entity_reconciliation":("identifier_variant","ambiguity","independent_identity_evidence"),
 "hierarchy_closure":("transitive_or_superclass_closure","duplicate_or_cycle"),
 "geometry_reconstruction":("global_mass_property","topology","envelope","curvature","watertightness"),
 "numeric_formula":("unit_or_scale","boundary_or_extreme","alternate_derivation"),
 "artifact":("existence","schema","roundtrip_or_parse"),
 "state_transition":("ordering_precedence","idempotence","failure_recovery"),
 "measurement_calibration":("standard_composition","measurement_channel_scope","reference_decay_or_time_alignment","blank_or_background_treatment"),
 "signal_correction":("cross_talk_direction","correction_parameter_identity","correction_order","unphysical_solution_rejection"),
 "method_model_selection":("method_variant","assumptions_to_formula","dimensional_form","limiting_case"),
}

CONTRACTS=(
 "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001",
 "NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001",
 "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001",
 "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001",
 "BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001",
 "TASK_TO_DELEGATION_GRAPH_001",
)

def _rng(seed:int)->random.Random:
    if not isinstance(seed,int) or isinstance(seed,bool): raise ValueError("SEED")
    return random.Random(seed)

def generate_case(contract:str,seed:int,difficulty:int=3)->dict[str,Any]:
    if contract not in CONTRACTS: raise ValueError("CONTRACT")
    if not 1<=difficulty<=5: raise ValueError("DIFFICULTY")
    r=_rng(seed)
    if contract=="SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001":
        kinds=sorted(r.sample(list(OBLIGATION_MAP),k=min(1+difficulty//2,len(OBLIGATION_MAP))))
        reqs=[]
        expected={}
        for i in range(max(2,difficulty)):
            ks=[kinds[i%len(kinds)]]
            if difficulty>=4 and len(kinds)>1: ks=sorted({ks[0],kinds[(i+1)%len(kinds)]})
            rid=f"R{i}"
            reqs.append({"id":rid,"critical":True,"transform_kinds":ks,"builder_dependencies":[f"raw:{rid}"],"must_detect_failure_modes":[]})
            expected[rid]=sorted({m for k in ks for m in OBLIGATION_MAP[k]})
        return {"schema":SCHEMA,"contract":contract,"seed":seed,"task":{"requirements":reqs},"_oracle":{"expected":expected}}

    if contract=="NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001":
        raw=(f"BRAIN-ARTIFACT-{seed}-{difficulty}|".encode()*max(2,difficulty)) + bytes([seed%251,difficulty])
        sha=hashlib.sha256(raw).hexdigest()
        return {"schema":SCHEMA,"contract":contract,"seed":seed,
          "task":{"target_b64":base64.b64encode(raw).decode(),"target_sha256":sha,"output_name":f"artifact-{seed}-{difficulty}.bin"},
          "_oracle":{"target_sha256":sha,"target_bytes":raw}}

    if contract=="ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001":
        n=max(2,difficulty+1)
        reqs=[{"id":f"R{i}","text":f"material requirement {seed} {i}","material":True} for i in range(n)]
        resolved={f"R{i}" for i in range(n//3)}
        actions=[]
        for i in range(n):
            actions.append({"id":f"A{i}","covers":[f"R{i}"],"cost":float(1+(i%3)),"reliability":1.0,"verified":True})
        # Add a multi-cover route whose score may dominate.
        unresolved=[x["id"] for x in reqs if x["id"] not in resolved]
        actions.append({"id":"A_MULTI","covers":unresolved[:max(1,min(3,len(unresolved)))],"cost":1.5,"reliability":0.95,"verified":True})
        def score(a):
            new=len(set(a["covers"])&set(unresolved))
            if not a["verified"] or not new:return None
            denom=a["cost"] if a["cost"]>0 else 1e-12
            return (new*a["reliability"]/denom,new,a["reliability"],-a["cost"],a["id"])
        ranked=[(score(a),a) for a in actions if score(a) is not None]
        ranked.sort(key=lambda x:x[0],reverse=True)
        chosen=ranked[0][1]
        target=sorted(set(chosen["covers"])&set(unresolved))[0] if unresolved else None
        return {"schema":SCHEMA,"contract":contract,"seed":seed,
          "task":{"objective":"resolve all material requirements","material_requirements":reqs,"resolved_requirement_ids":sorted(resolved),"candidate_actions":actions},
          "_oracle":{"status":"STOP" if not unresolved else "ACT","selected_action_id":None if not unresolved else chosen["id"],"target_requirement_id":target}}

    if contract=="TOOL_ROUTE_DISCOVERY_AND_SELECTION_001":
        req={"read","write"} if difficulty<3 else {"read","write","analyze"}
        caps=sorted(req|{"extra"})
        routes=[
          {"route_id":"R_EXPENSIVE","capabilities":caps,"cost":5.0,"available":True,"authorized":True,"verified":True},
          {"route_id":"R_BEST","capabilities":sorted(req),"cost":1.0,"available":True,"authorized":True,"verified":True},
          {"route_id":"R_UNVERIFIED","capabilities":sorted(req),"cost":0.0,"available":True,"authorized":True,"verified":False},
        ]
        return {"schema":SCHEMA,"contract":contract,"seed":seed,"task":{"required":sorted(req),"routes":routes},"_oracle":{"route_id":"R_BEST"}}

    if contract=="BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001":
        target=f"target-{seed}"
        elements=[
          {"element_id":"E_TARGET","role":"button","name":target,"text":target,"ocr_text":target,"attrs":{"data-id":str(seed)},"actions":["click"],"visible":True,"enabled":True},
          {"element_id":"E_DISTRACTOR","role":"button","name":target+"-other","text":target+"-other","ocr_text":target+"-other","attrs":{"data-id":"x"},"actions":["click"],"visible":True,"enabled":True},
        ]
        request={"action":"click","role":"button","name":target,"text":target,"attrs":{"data-id":str(seed)},"min_independent_cues":3}
        return {"schema":SCHEMA,"contract":contract,"seed":seed,"task":{"request":request,"elements":elements},"_oracle":{"element_id":"E_TARGET"}}

    # TASK_TO_DELEGATION_GRAPH_001
    branches=max(2,min(5,difficulty))
    steps=[{"id":"A","requires":["RAW"],"produces":["X"],"cost":1.0,"capability":"PARSE"}]
    fact_universe=["RAW","X","FINAL"]
    workers=[{"id":"W_PARSE","capabilities":["PARSE","INTEGRATE"]}]
    for i in range(branches):
        y=f"Y{i}"; cap=f"C{i}"
        fact_universe.append(y)
        steps.append({"id":f"B{i}","requires":["X"],"produces":[y],"cost":1.0,"capability":cap})
        workers.append({"id":f"W{i}","capabilities":[cap]})
    steps.append({"id":"D","requires":[f"Y{i}" for i in range(branches)],"produces":["FINAL"],"cost":1.0,"capability":"INTEGRATE"})
    steps.append({"id":"DISTRACTOR","requires":["RAW"],"produces":["FINAL"],"cost":100.0,"capability":"INTEGRATE"})
    public={"fact_universe":fact_universe,"initial_facts":["RAW"],"required_outputs":["FINAL"],"steps":steps,"workers":workers}
    return {"schema":SCHEMA,"contract":contract,"seed":seed,"task":public,"_oracle":{}}

def public_task(case:Mapping[str,Any])->dict[str,Any]:
    return {k:v for k,v in case.items() if k!="_oracle"}

def score_case(case:Mapping[str,Any],candidate:Mapping[str,Any],*,artifact_bytes:bytes|None=None)->dict[str,Any]:
    c=case["contract"]
    if c=="SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001":
        if candidate.get("status")!="COMPILED": return {"pass":False,"reason":"NOT_COMPILED"}
        plans={p.get("requirement_id"):p for p in candidate.get("plans",[]) if isinstance(p,Mapping)}
        expected=case["_oracle"]["expected"]
        ok=set(plans)==set(expected) and all(sorted(plans[r].get("required_failure_modes",[]))==expected[r] for r in expected)
        return {"pass":ok,"reason":"PASS" if ok else "ACCEPTANCE_OBLIGATIONS_MISMATCH"}

    if c=="NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001":
        ok=candidate.get("status")=="PASS" and isinstance(artifact_bytes,bytes) and hashlib.sha256(artifact_bytes).hexdigest()==case["_oracle"]["target_sha256"] and artifact_bytes==case["_oracle"]["target_bytes"]
        return {"pass":ok,"reason":"PASS" if ok else "ARTIFACT_BYTES_MISMATCH"}

    if c=="ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001":
        o=case["_oracle"]
        ok=candidate.get("status")==o["status"]
        if o["status"]=="ACT":
            ok=ok and candidate.get("selected_action_id")==o["selected_action_id"] and candidate.get("target_requirement_id")==o["target_requirement_id"]
        return {"pass":ok,"reason":"PASS" if ok else "RESEARCH_CONTROL_MISMATCH"}

    if c=="TOOL_ROUTE_DISCOVERY_AND_SELECTION_001":
        ok=candidate.get("status")=="SELECT" and candidate.get("route_id")==case["_oracle"]["route_id"]
        return {"pass":ok,"reason":"PASS" if ok else "TOOL_ROUTE_MISMATCH"}

    if c=="BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001":
        ok=candidate.get("status")=="SELECT" and candidate.get("element_id")==case["_oracle"]["element_id"]
        return {"pass":ok,"reason":"PASS" if ok else "DOM_GROUNDING_MISMATCH"}

    if c=="TASK_TO_DELEGATION_GRAPH_001":
        from canonical.runtime.delegation_contract_proof_suite import score
        return score(case["task"],candidate)

    raise ValueError("CONTRACT")
