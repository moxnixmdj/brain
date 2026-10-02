"""Evaluator-side CAD T0 hidden-oracle and candidate-solid measurement adapter.

Candidate code must never call prepare_hidden_case or receive its output. Reference
solids are built from evaluator-only typed geometry contracts through already-owned
M1B builders. Candidate solids are measured independently from their CadQuery/OCC
result object; candidate-supplied geometry metrics are ignored.
"""
from __future__ import annotations
import copy, math
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_CAD_T0_ORACLE_ADAPTER_V1"

def _finite(x:Any)->float:
    if not isinstance(x,(int,float)) or isinstance(x,bool) or not math.isfinite(float(x)):
        raise ValueError("non-finite metric")
    return float(x)

def measure_result(result:Any)->dict[str,Any]:
    solids=result.solids().vals()
    if len(solids)!=1:
        raise ValueError("candidate/reference result must contain exactly one solid")
    shape=result.val()
    bb=shape.BoundingBox()
    metrics={
        "volume":_finite(shape.Volume()),
        "surface_area":_finite(shape.Area()),
        "bbox":[_finite(bb.xlen),_finite(bb.ylen),_finite(bb.zlen)],
        "topology_counts":{
            "faces":len(shape.Faces()),
            "edges":len(shape.Edges()),
            "vertices":len(shape.Vertices()),
        },
    }
    if metrics["volume"]<=0 or metrics["surface_area"]<=0 or any(x<=0 for x in metrics["bbox"]):
        raise ValueError("degenerate solid metrics")
    return metrics

def _exec_source(source:str)->Any:
    ns:dict[str,Any]={}
    exec(compile(source,"<cad-t0-hidden-reference>","exec"),ns)
    if "result" not in ns:
        raise ValueError("reference builder did not define result")
    return ns["result"]

def build_reference_result(hidden_geometry_contract:Mapping[str,Any])->Any:
    if not isinstance(hidden_geometry_contract,Mapping):
        raise ValueError("hidden geometry contract missing")
    kind=hidden_geometry_contract.get("kind")
    if kind in {"spline_revolve","circle_loft","polygon_loft"}:
        from canonical.runtime.m1b_smooth_surface_compiler import compile_source
        out=compile_source(hidden_geometry_contract)
        if out.get("status")!="COMPILED":
            raise ValueError("smooth reference compile failed")
        return _exec_source(out["source"])
    from canonical.runtime.m1b_continuous_geometry_compiler import compile_contract
    from canonical.runtime.cad_partspec_generator import generate_code
    out=compile_contract(hidden_geometry_contract)
    if out.get("status")!="COMPILED":
        raise ValueError("reference contract compile failed")
    return _exec_source(generate_code(out["partspec"]))

def prepare_hidden_case(case:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(case,Mapping) or "_oracle" not in case:
        raise ValueError("hidden case required")
    out=copy.deepcopy(dict(case))
    oracle=out["_oracle"]
    if oracle.get("identifiable") is True:
        reference=build_reference_result(oracle["reference_geometry_contract"])
        metrics=measure_result(reference)
        oracle["reference_geometry_metrics"]=metrics
        oracle["required_geometry_metrics"]=list(metrics)
        oracle.setdefault("metric_tolerances",{
            "volume":{"abs":0.05,"rel":1e-7},
            "surface_area":{"abs":0.05,"rel":1e-7},
            "bbox":{"abs":0.01,"rel":1e-7},
            "topology_counts":{"abs":0,"rel":0},
        })
    return out

def _close(ref:Any,got:Any,abs_tol:float,rel_tol:float)->bool:
    if isinstance(ref,bool) or isinstance(got,bool):
        return type(ref) is type(got) and ref==got
    if isinstance(ref,(int,float)) and isinstance(got,(int,float)) and not isinstance(got,bool):
        return math.isclose(float(ref),float(got),abs_tol=abs_tol,rel_tol=rel_tol)
    if isinstance(ref,list) and isinstance(got,list):
        return len(ref)==len(got) and all(_close(a,b,abs_tol,rel_tol) for a,b in zip(ref,got))
    if isinstance(ref,Mapping) and isinstance(got,Mapping):
        return set(ref)==set(got) and all(_close(ref[k],got[k],abs_tol,rel_tol) for k in ref)
    return ref==got

def metrics_match(oracle:Mapping[str,Any],metrics:Mapping[str,Any])->bool:
    ref=oracle.get("reference_geometry_metrics")
    req=oracle.get("required_geometry_metrics")
    tols=oracle.get("metric_tolerances")
    if not isinstance(ref,Mapping) or not isinstance(req,list) or not isinstance(tols,Mapping):
        return False
    for name in req:
        if name not in ref or name not in metrics:
            return False
        t=tols.get(name)
        if not isinstance(t,Mapping):
            return False
        if not _close(ref[name],metrics[name],float(t.get("abs",-1)),float(t.get("rel",-1))):
            return False
    return True

def validate_ambiguity_witness(case:Mapping[str,Any],candidate:Mapping[str,Any])->bool:
    oracle=case.get("_oracle") if isinstance(case,Mapping) else None
    if not isinstance(oracle,Mapping) or oracle.get("identifiable") is not False:
        return False
    witness=candidate.get("ambiguity_witness") if isinstance(candidate,Mapping) else None
    if not isinstance(witness,Mapping) or witness.get("parameter")!=oracle.get("ambiguity_parameter"):
        return False
    vals=witness.get("alternatives")
    if not isinstance(vals,list) or len(vals)<2:
        return False
    clean=[]
    for v in vals:
        try:
            x=_finite(v)
        except ValueError:
            return False
        if x<=0: return False
        clean.append(x)
    return len({round(x,9) for x in clean})>=2

def observe_candidate(case:Mapping[str,Any],candidate:Mapping[str,Any],result:Any|None)->dict[str,Any]:
    oracle=case.get("_oracle") if isinstance(case,Mapping) else None
    if not isinstance(oracle,Mapping):
        raise ValueError("hidden oracle missing")
    if oracle.get("identifiable") is False:
        return {
            "ambiguity_witness_valid":validate_ambiguity_witness(case,candidate),
            "end_to_end_final_geometry_correct":candidate.get("status")=="NONIDENTIFIABLE",
            "cross_stage_state_loss":False,
            "failure_localization_consistent":True,
        }
    try:
        metrics=measure_result(result)
        solid_valid=True
    except Exception:
        metrics={}
        solid_valid=False
    graph_ok=candidate.get("constraint_graph")==oracle.get("reference_constraint_graph")
    geometry_ok=solid_valid and metrics_match(oracle,metrics)
    return {
        "candidate_solid_valid":solid_valid,
        "geometry_class_covered":solid_valid,
        "candidate_geometry_metrics":metrics,
        "end_to_end_final_geometry_correct":bool(geometry_ok),
        "cross_stage_state_loss":not bool(graph_ok),
        "failure_localization_consistent":True,
    }
