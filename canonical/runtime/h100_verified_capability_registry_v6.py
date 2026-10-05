"""H100 verified capability registry V6.

V6 preserves Registry V5 and compiles two independently verified stdlib-math
operator families acquired by the generic safe operator gate: atan and tanh.
No arbitrary module import or arbitrary code execution is introduced.
"""
from __future__ import annotations
import math
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_verified_capability_registry_v5 as v5
from canonical.runtime import h100_safe_stdlib_operator_acquisition_v1 as acq

SCHEMA="PROJECT_BRAIN_H100_VERIFIED_CAPABILITY_REGISTRY_V6"
PRIOR="canonical/verification/H100_SAFE_STDLIB_OPERATOR_ACQUISITION_SECOND_CARRIER_VERIFICATION_20261005_V1.json"

NEW=(
    {
        "capability_id":"CAP_AFFINE_ATAN_V1",
        "kind":"PARAMETRIC_STDLIB_OPERATOR",
        "family":"AFFINE_ATAN",
        "attribute":"atan",
        "route":"VERIFIED_SAFE_STDLIB_OPERATOR_REFIT",
        "gamma_grid":[0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.2,1.3,1.4,1.5,1.6,1.7,1.8,1.9,2.0],
        "prior_verification":PRIOR,
    },
    {
        "capability_id":"CAP_AFFINE_TANH_V1",
        "kind":"PARAMETRIC_STDLIB_OPERATOR",
        "family":"AFFINE_TANH",
        "attribute":"tanh",
        "route":"VERIFIED_SAFE_STDLIB_OPERATOR_REFIT",
        "gamma_grid":[0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.2,1.3,1.4,1.5,1.6,1.7,1.8,1.9,2.0],
        "prior_verification":PRIOR,
    },
)
REGISTRY=tuple(v5.REGISTRY)+NEW

class CapabilityRegistryV6Error(ValueError):
    pass

def registry_snapshot()->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"VERIFIED_CAPABILITY_REGISTRY_V6_READY",
        "entry_count":len(REGISTRY),
        "entries":[dict(x) for x in REGISTRY],
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "routing_priority":"REGISTRY_V5_THEN_VERIFIED_ATAN_TANH_THEN_RAW_SEARCH",
    }

def _best(rows:Sequence[Mapping[str,Any]],entry:Mapping[str,Any]):
    fn=getattr(math,str(entry["attribute"]))
    out=[]
    for g in entry["gamma_grid"]:
        c=acq._fit(rows,fn,float(g))
        if c is not None:
            row=dict(c)
            row["attribute"]=entry["attribute"]
            out.append(row)
    out.sort(key=lambda c:(c["train_nrmse"],c["gamma"],c["attribute"]))
    return out[0] if out else None

def resolve_verified_capability(
    rows:Sequence[Mapping[str,Any]],
    *,
    target:str,
    input_name:str|None=None,
    exact_nrmse:float=1e-8,
)->dict[str,Any]:
    base=v5.resolve_verified_capability(rows,target=target,input_name=input_name,exact_nrmse=exact_nrmse)
    if base.get("status")=="LIBRARY_HIT__VERIFY_BEFORE_USE":
        out=dict(base); out["schema"]=SCHEMA; out["registry_version"]=6
        return out
    if str(target)!="y" or (input_name is not None and str(input_name)!="x"):
        return {
            "schema":SCHEMA,"status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED","registry_version":6,
            "reason":"STDLIB_OPERATOR_SCHEMA_UNSUPPORTED","match":None,
            "persistent_learned_bytes":0,"external_learned_capability_calls":0,
        }
    candidates=[]
    for entry in NEW:
        c=_best(rows,entry)
        if c is not None and float(c["train_nrmse"])<=exact_nrmse:
            candidates.append((float(c["train_nrmse"]),str(entry["capability_id"]),entry,c))
    if candidates:
        candidates.sort(key=lambda x:(x[0],x[1]))
        _err,_id,entry,cand=candidates[0]
        return {
            "schema":SCHEMA,"status":"LIBRARY_HIT__VERIFY_BEFORE_USE","registry_version":6,
            "match":{
                "capability_id":entry["capability_id"],
                "family":entry["family"],
                "route":entry["route"],
                "candidate":dict(cand),
                "prior_verification":entry["prior_verification"],
            },
            "persistent_learned_bytes":0,
            "external_learned_capability_calls":0,
            "raw_synthesis_attempts_before_hit":0,
        }
    return {
        "schema":SCHEMA,"status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED","registry_version":6,
        "reason":"NO_VERIFIED_EXACT_LIBRARY_FAMILY","match":None,
        "persistent_learned_bytes":0,"external_learned_capability_calls":0,
    }

def predict(resolution:Mapping[str,Any],point:Mapping[str,Any])->float:
    if resolution.get("status")!="LIBRARY_HIT__VERIFY_BEFORE_USE":
        raise CapabilityRegistryV6Error("RESOLUTION_NOT_LIBRARY_HIT")
    match=resolution.get("match")
    if not isinstance(match,Mapping):
        raise CapabilityRegistryV6Error("MATCH_INVALID")
    if match.get("route")!="VERIFIED_SAFE_STDLIB_OPERATOR_REFIT":
        return v5.predict(resolution,point)
    cand=match["candidate"]
    fn=getattr(math,str(cand["attribute"]))
    x=float(point["x"])
    coeff=cand["coefficients"]; g=float(cand["gamma"])
    y=float(coeff[0])+float(coeff[1])*x+float(coeff[2])*float(fn(g*x))
    if not math.isfinite(y):
        raise CapabilityRegistryV6Error("PREDICTION_NONFINITE")
    return y

def invoke(capability_id:str,payload:Mapping[str,Any])->dict[str,Any]:
    if capability_id in {x["capability_id"] for x in NEW}:
        raise CapabilityRegistryV6Error("PARAMETRIC_CAPABILITY_REQUIRES_RESOLUTION")
    out=v5.invoke(capability_id,payload)
    row=dict(out); row["schema"]=SCHEMA; row["registry_version"]=6
    return row
