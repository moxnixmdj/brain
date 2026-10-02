"""Information-safe scorer for CAD M1 direct instrumentation inside T0.

The candidate never receives the hidden reference constraint graph, reference solid,
reference geometry metrics, geometry-class labels, or mutation identity. Independent
evaluator-side code supplies an observation mapping containing measurements of the
candidate result. This scorer compares those measurements to frozen hidden gold.

This module is a scorer, not a case generator or terminal execution authority.
"""
from __future__ import annotations
import json, math
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_CAD_T0_MULTIPLEX_SCORER_V1"
FORBIDDEN_CANDIDATE_KEYS={
    "_oracle","reference_constraint_graph","reference_geometry_metrics",
    "reference_solid","gold","mutation_identity","expected_failure_reason",
}

def public_case(case: Mapping[str,Any]) -> dict[str,Any]:
    if not isinstance(case,Mapping):
        raise ValueError("CASE_NOT_MAPPING")
    return {k:v for k,v in case.items() if k!="_oracle"}

def _canonical(v: Any) -> str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def _tol_for(name:str,tols:Mapping[str,Any])->tuple[float,float]|None:
    row=tols.get(name)
    if not isinstance(row,Mapping):
        return None
    a=row.get("abs")
    r=row.get("rel")
    if not isinstance(a,(int,float)) or isinstance(a,bool) or not math.isfinite(float(a)) or float(a)<0:
        return None
    if not isinstance(r,(int,float)) or isinstance(r,bool) or not math.isfinite(float(r)) or float(r)<0:
        return None
    return float(a),float(r)

def _close_value(ref:Any,got:Any,abs_tol:float,rel_tol:float)->bool:
    if isinstance(ref,bool) or isinstance(got,bool):
        return type(ref) is type(got) and ref==got
    if isinstance(ref,(int,float)) and isinstance(got,(int,float)) and not isinstance(got,bool):
        if not math.isfinite(float(ref)) or not math.isfinite(float(got)):
            return False
        return math.isclose(float(ref),float(got),abs_tol=abs_tol,rel_tol=rel_tol)
    if isinstance(ref,list) and isinstance(got,list):
        return len(ref)==len(got) and all(_close_value(a,b,abs_tol,rel_tol) for a,b in zip(ref,got))
    if isinstance(ref,Mapping) and isinstance(got,Mapping):
        return set(ref)==set(got) and all(_close_value(ref[k],got[k],abs_tol,rel_tol) for k in ref)
    return type(ref) is type(got) and ref==got

def _score_metrics(oracle:Mapping[str,Any],observation:Mapping[str,Any])->tuple[bool,list[str]]:
    reference=oracle.get("reference_geometry_metrics")
    measured=observation.get("candidate_geometry_metrics")
    required=oracle.get("required_geometry_metrics")
    tolerances=oracle.get("metric_tolerances")
    errors=[]
    if not isinstance(reference,Mapping) or not isinstance(measured,Mapping):
        return False,["GEOMETRY_METRICS_MISSING"]
    if not isinstance(required,list) or not required or any(not isinstance(x,str) or not x for x in required):
        return False,["REQUIRED_GEOMETRY_METRICS_INVALID"]
    if not isinstance(tolerances,Mapping):
        return False,["METRIC_TOLERANCES_MISSING"]
    for name in required:
        if name not in reference or name not in measured:
            errors.append("METRIC_MISSING:"+name)
            continue
        tol=_tol_for(name,tolerances)
        if tol is None:
            errors.append("METRIC_TOLERANCE_INVALID:"+name)
            continue
        if not _close_value(reference[name],measured[name],tol[0],tol[1]):
            errors.append("METRIC_MISMATCH:"+name)
    return not errors,errors

def score_case(case:Mapping[str,Any],candidate:Mapping[str,Any],observation:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    if not isinstance(case,Mapping) or not isinstance(candidate,Mapping) or not isinstance(observation,Mapping):
        return {"schema":SCHEMA,"pass":False,"errors":["INPUT_NOT_MAPPING"],"terminal_authority":False}
    oracle=case.get("_oracle")
    if not isinstance(oracle,Mapping):
        return {"schema":SCHEMA,"pass":False,"errors":["HIDDEN_ORACLE_MISSING"],"terminal_authority":False}
    leaked=sorted(FORBIDDEN_CANDIDATE_KEYS & set(candidate))
    if leaked:
        errors.append("CANDIDATE_HIDDEN_FIELD_LEAK:"+",".join(leaked))

    ref_graph=oracle.get("reference_constraint_graph")
    cand_graph=candidate.get("constraint_graph")
    lane_a=(ref_graph is not None and cand_graph is not None and _canonical(ref_graph)==_canonical(cand_graph))
    if not lane_a:
        errors.append("LANE_A_CONSTRAINT_GRAPH_MISMATCH")

    identifiable=oracle.get("identifiable")
    if identifiable is True:
        if candidate.get("status")!="SOLID":
            errors.append("LANE_B_IDENTIFIABLE_NOT_SOLID")
            lane_b=False
        elif observation.get("candidate_solid_valid") is not True:
            errors.append("LANE_B_SOLID_INVALID")
            lane_b=False
        elif observation.get("geometry_class_covered") is not True:
            errors.append("LANE_B_GEOMETRY_CLASS_NOT_COVERED")
            lane_b=False
        else:
            lane_b,metric_errors=_score_metrics(oracle,observation)
            errors.extend("LANE_B_"+x for x in metric_errors)
    elif identifiable is False:
        lane_b=(candidate.get("status")=="NONIDENTIFIABLE" and observation.get("ambiguity_witness_valid") is True)
        if not lane_b:
            errors.append("LANE_B_NONIDENTIFIABILITY_WITNESS_INVALID")
    else:
        lane_b=False
        errors.append("LANE_B_IDENTIFIABILITY_TRUTH_INVALID")

    lane_c=(
        observation.get("end_to_end_final_geometry_correct") is True
        and observation.get("cross_stage_state_loss") is False
        and observation.get("failure_localization_consistent") is True
    )
    if not lane_c:
        errors.append("LANE_C_COMPOSITION_ACCEPTANCE_FAILED")

    passed=lane_a and lane_b and lane_c and not leaked and not errors
    return {
        "schema":SCHEMA,
        "pass":bool(passed),
        "lane_A_m1a_pass":bool(lane_a),
        "lane_B_m1b_pass":bool(lane_b),
        "lane_C_composition_pass":bool(lane_c),
        "errors":sorted(set(errors)),
        "terminal_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }
