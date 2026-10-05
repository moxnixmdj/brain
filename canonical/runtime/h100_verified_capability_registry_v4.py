"""H100 verified capability registry V4.

V4 preserves Registry V3 and adds only the rational feature structure that was
discovered by the broader expression-tree escape and transferred on a distinct
frozen task: [x, sat(square(x))].
"""
from __future__ import annotations
import math
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_verified_capability_registry_v3 as v3
from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr

SCHEMA="PROJECT_BRAIN_H100_VERIFIED_CAPABILITY_REGISTRY_V4"
PRIOR="canonical/verification/H100_FINITE_GRAMMAR_ESCAPE_SECOND_CARRIER_VERIFICATION_20261005_V1.json"

RATIONAL={
    "capability_id":"CAP_AFFINE_RATIONAL_SAT_SQUARE_V1",
    "kind":"PARAMETRIC_EXPRESSION",
    "family":"RATIONAL_SAT_SQUARE",
    "route":"FIXED_EXPRESSION_STRUCTURE_LINEAR_REFIT",
    "prior_verification":PRIOR,
}
REGISTRY=tuple(v3.REGISTRY)+(RATIONAL,)

TREES=[
    {"op":"var","name":"x"},
    {"op":"sat","arg":{"op":"square","arg":{"op":"var","name":"x"}}},
]

class CapabilityRegistryV4Error(ValueError):
    pass

def registry_snapshot()->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"VERIFIED_CAPABILITY_REGISTRY_V4_READY",
        "entry_count":len(REGISTRY),
        "entries":[dict(x) for x in REGISTRY],
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "routing_priority":"REGISTRY_V3_THEN_VERIFIED_RATIONAL_STRUCTURE_THEN_RAW_SEARCH",
    }

def _fit(rows:Sequence[Mapping[str,Any]]):
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or len(rows)<8:
        return None
    try:
        cols=[[expr.evaluate_tree(tree,row) for row in rows] for tree in TREES]
        ys=[float(row["y"]) for row in rows]
    except Exception:
        return None
    coeff=expr._fit_linear_features(cols,ys)
    if coeff is None:
        return None
    candidate={"features":TREES,"coefficients":coeff}
    try:
        pred=[expr.predict(candidate,row) for row in rows]
    except Exception:
        return None
    return {
        "candidate":candidate,
        "train_nrmse":expr._nrmse(ys,pred),
    }

def resolve_verified_capability(
    rows:Sequence[Mapping[str,Any]],
    *,
    target:str,
    input_name:str|None=None,
    exact_nrmse:float=1e-8,
)->dict[str,Any]:
    base=v3.resolve_verified_capability(
        rows,target=target,input_name=input_name,exact_nrmse=exact_nrmse
    )
    if base.get("status")=="LIBRARY_HIT__VERIFY_BEFORE_USE":
        out=dict(base);out["schema"]=SCHEMA;out["registry_version"]=4
        return out

    if str(target)!="y" or (input_name is not None and str(input_name)!="x"):
        return {
            "schema":SCHEMA,"status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",
            "registry_version":4,"reason":"RATIONAL_SCHEMA_UNSUPPORTED","match":None,
            "persistent_learned_bytes":0,"external_learned_capability_calls":0,
        }

    fit=_fit(rows)
    if fit is not None and float(fit["train_nrmse"])<=exact_nrmse:
        cand=dict(fit["candidate"])
        cand["train_nrmse"]=fit["train_nrmse"]
        cand["family_id"]="RATIONAL_SAT_SQUARE"
        cand["feature_signatures"]=["v0","sat(square(v0))"]
        return {
            "schema":SCHEMA,
            "status":"LIBRARY_HIT__VERIFY_BEFORE_USE",
            "registry_version":4,
            "match":{
                "capability_id":RATIONAL["capability_id"],
                "family":RATIONAL["family"],
                "route":RATIONAL["route"],
                "candidate":cand,
                "prior_verification":PRIOR,
            },
            "persistent_learned_bytes":0,
            "external_learned_capability_calls":0,
            "raw_synthesis_attempts_before_hit":0,
        }

    return {
        "schema":SCHEMA,"status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",
        "registry_version":4,"reason":"NO_VERIFIED_EXACT_LIBRARY_FAMILY","match":None,
        "persistent_learned_bytes":0,"external_learned_capability_calls":0,
    }

def predict(resolution:Mapping[str,Any],point:Mapping[str,Any])->float:
    if resolution.get("status")!="LIBRARY_HIT__VERIFY_BEFORE_USE":
        raise CapabilityRegistryV4Error("RESOLUTION_NOT_LIBRARY_HIT")
    match=resolution.get("match")
    if not isinstance(match,Mapping):
        raise CapabilityRegistryV4Error("MATCH_INVALID")
    if match.get("route")==RATIONAL["route"]:
        return expr.predict(match["candidate"],point)
    return v3.predict(resolution,point)

def invoke(capability_id:str,payload:Mapping[str,Any])->dict[str,Any]:
    if capability_id==RATIONAL["capability_id"]:
        raise CapabilityRegistryV4Error("PARAMETRIC_CAPABILITY_REQUIRES_RESOLUTION")
    out=v3.invoke(capability_id,payload)
    row=dict(out);row["schema"]=SCHEMA;row["registry_version"]=4
    return row
