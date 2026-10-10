from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V2"
PROFILE_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_V1"

TRIGGER_ROOTS={
"NEAR_DECISION_BOUNDARY":["R4_MEASUREMENT_CONSTRUCT","R5_EVALUATOR_REFERENCE","R10_ANALYSIS_DECISION"],
"QUALIFIED_JUDGE_DISAGREEMENT":["R5_EVALUATOR_REFERENCE","R10_ANALYSIS_DECISION"],
"NOVEL_OR_OOD_ARTIFACT":["R2_CANDIDATE_SEARCH","R5_EVALUATOR_REFERENCE"],
"HEAVY_OPTIMIZATION_AGAINST_DEVELOPMENT_JUDGE":["R5_EVALUATOR_REFERENCE","R11_ADAPTIVE_INTEGRITY_SECURITY"],
"MATERIAL_INVARIANCE_FAILURE":["R4_MEASUREMENT_CONSTRUCT","R8_POPULATION_CONTEXT_OPERATOR"],
"REFERENCE_AMBIGUITY_OR_PLURALITY":["R5_EVALUATOR_REFERENCE","R10_ANALYSIS_DECISION"],
"MODEL_OR_ANALYSIS_MULTIPLICITY_DECISION_SENSITIVE":["R6_EVIDENCE_GROUNDING_DEPENDENCE","R10_ANALYSIS_DECISION"],
"HIGH_CONSEQUENCE_OR_VETO_DIMENSION":["R10_ANALYSIS_DECISION","R12_META_COMPOSITION_CLOSURE"],
"UNSUPPORTED_OR_LOSSY_OBSERVATION_CHANNEL":["R3_REALIZATION_OBSERVATION","R12_META_COMPOSITION_CLOSURE"],
"POPULATION_CONTEXT_OPERATOR_OR_TIME_TRANSPORT_GAP":["R8_POPULATION_CONTEXT_OPERATOR","R9_TEMPORAL_DEPLOYMENT"],
"ADAPTIVE_CONTAMINATION_OR_HOLDOUT_EXPOSURE":["R11_ADAPTIVE_INTEGRITY_SECURITY"],
"UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER":["R12_META_COMPOSITION_CLOSURE"],
}
STEP_STATES={"PASS","OPEN","FAIL","NOT_RUN"}

def _base(status:str)->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":status,
        "quality_judgment_authority":False,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "new_root_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "capability_credit_delta":0,
        "incremental_spend_usd":0,
    }

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {**_base("FAIL_CLOSED"),"reason":reason,**extra}

def _profile(repo_root:str|Path|None)->dict[str,Any]:
    root=Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    p=root/"canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V1.json"
    data=json.loads(p.read_text())
    if data.get("schema")!=PROFILE_SCHEMA:
        raise ValueError("PROFILE_SCHEMA_INVALID")
    return data

def route(state:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    if not isinstance(state,Mapping):
        return _fail("STATE_NOT_OBJECT")
    try:
        profile=_profile(repo_root)
    except Exception as exc:
        return _fail("PROFILE_LOAD_OR_SCHEMA_FAILURE:"+type(exc).__name__)
    steps=list(profile.get("steps") or [])
    declared=set(profile.get("escalation_triggers") or [])
    if not steps or declared!=set(TRIGGER_ROOTS):
        return _fail("PROFILE_ROUTER_CONTRACT_DRIFT")

    triggers=state.get("detected_triggers",[])
    if not isinstance(triggers,list) or not all(isinstance(x,str) and x for x in triggers):
        return _fail("DETECTED_TRIGGERS_INVALID")
    unknown=sorted(set(triggers)-declared)
    if unknown:
        return _fail("UNKNOWN_ESCALATION_TRIGGER",unknown_triggers=unknown)

    results=state.get("step_results",{})
    if not isinstance(results,Mapping):
        return _fail("STEP_RESULTS_NOT_OBJECT")
    unknown_steps=sorted(set(results)-set(steps))
    if unknown_steps:
        return _fail("UNKNOWN_P1_STEP",unknown_steps=unknown_steps)
    invalid={k:v for k,v in results.items() if v not in STEP_STATES}
    if invalid:
        return _fail("STEP_RESULT_STATE_INVALID",invalid_step_states=invalid)

    failed=[s for s in steps if results.get(s)=="FAIL"]
    unresolved=[s for s in steps if results.get(s,"NOT_RUN") in {"OPEN","NOT_RUN"}]
    if failed:
        return {**_base("ABSTAIN__P1_HARD_FAILURE"),"route":"ABSTAIN","blocking_steps":failed}
    if unresolved:
        return {**_base("ABSTAIN__P1_INCOMPLETE"),"route":"ABSTAIN","blocking_steps":unresolved}

    unmapped=state.get("unmapped_material_false_certification_path")
    rep=state.get("unmapped_path_representation")
    if unmapped not in {None,False,True}:
        return _fail("UNMAPPED_PATH_FLAG_INVALID")
    if rep not in {None,"EXISTING_ROOTS","UNREPRESENTABLE","UNKNOWN"}:
        return _fail("UNMAPPED_PATH_REPRESENTATION_INVALID")
    if unmapped is True and rep in {None,"UNKNOWN"}:
        return {**_base("ABSTAIN__UNMAPPED_PATH_REPRESENTATION_UNKNOWN"),"route":"ABSTAIN"}
    if unmapped is True and rep=="UNREPRESENTABLE":
        return {**_base("ESCALATE__NEW_ROOT_CANDIDATE_REQUIRES_PROOF"),"route":"ARCHITECTURE_REVIEW","new_root_candidate":True}

    unique=sorted(set(triggers))
    roots=sorted({r for t in unique for r in TRIGGER_ROOTS[t]})
    if unique:
        return {**_base("ROUTE__ESCALATE_EXISTING_ASSURANCE_ROOTS"),"route":"ESCALATE","detected_triggers":unique,"escalation_root_ids":roots,"new_root_candidate":False}
    return {**_base("ROUTE__P1_ORDINARY"),"route":"P1","detected_triggers":[],"escalation_root_ids":[],"profile_steps":steps}
