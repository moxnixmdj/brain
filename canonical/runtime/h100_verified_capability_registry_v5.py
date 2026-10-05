"""H100 verified capability registry V5 with one JIT-verified erf family."""
from __future__ import annotations
import math
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_verified_capability_registry_v4 as v4
from canonical.runtime import h100_jit_primitive_acquisition_v1 as jit

SCHEMA="PROJECT_BRAIN_H100_VERIFIED_CAPABILITY_REGISTRY_V5"
PRIOR="canonical/verification/H100_JIT_PRIMITIVE_ACQUISITION_SECOND_CARRIER_VERIFICATION_20261005_V1.json"
ERF={
    "capability_id":"CAP_AFFINE_ERF_V1",
    "kind":"PARAMETRIC_STDLIB_PRIMITIVE",
    "family":"AFFINE_ERF",
    "route":"VERIFIED_MATH_ERF_GAMMA_REFIT",
    "prior_verification":PRIOR,
}
REGISTRY=tuple(v4.REGISTRY)+(ERF,)
GAMMAS=[0.2,0.4,0.6,0.8,1.0,1.2,1.4,1.6,1.8,2.0]

class CapabilityRegistryV5Error(ValueError): pass

def registry_snapshot()->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"VERIFIED_CAPABILITY_REGISTRY_V5_READY",
        "entry_count":len(REGISTRY),
        "entries":[dict(x) for x in REGISTRY],
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "routing_priority":"REGISTRY_V4_THEN_VERIFIED_ERF_FAMILY_THEN_RAW_SEARCH",
    }

def _best(rows:Sequence[Mapping[str,Any]]):
    out=[]
    for g in GAMMAS:
        c=jit._fit(rows,math.erf,g)
        if c is not None:
            out.append(c)
    out.sort(key=lambda c:(c["train_nrmse"],c["gamma"]))
    return out[0] if out else None

def resolve_verified_capability(rows:Sequence[Mapping[str,Any]],*,target:str,input_name:str|None=None,exact_nrmse:float=1e-8)->dict[str,Any]:
    base=v4.resolve_verified_capability(rows,target=target,input_name=input_name,exact_nrmse=exact_nrmse)
    if base.get("status")=="LIBRARY_HIT__VERIFY_BEFORE_USE":
        out=dict(base);out["schema"]=SCHEMA;out["registry_version"]=5
        return out
    if str(target)!="y" or (input_name is not None and str(input_name)!="x"):
        return {"schema":SCHEMA,"status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED","registry_version":5,"reason":"ERF_SCHEMA_UNSUPPORTED","match":None,"persistent_learned_bytes":0,"external_learned_capability_calls":0}
    cand=_best(rows)
    if cand is not None and float(cand["train_nrmse"])<=exact_nrmse:
        return {
            "schema":SCHEMA,"status":"LIBRARY_HIT__VERIFY_BEFORE_USE","registry_version":5,
            "match":{"capability_id":ERF["capability_id"],"family":ERF["family"],"route":ERF["route"],"candidate":dict(cand),"prior_verification":PRIOR},
            "persistent_learned_bytes":0,"external_learned_capability_calls":0,"raw_synthesis_attempts_before_hit":0,
        }
    return {"schema":SCHEMA,"status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED","registry_version":5,"reason":"NO_VERIFIED_EXACT_LIBRARY_FAMILY","match":None,"persistent_learned_bytes":0,"external_learned_capability_calls":0}

def predict(resolution:Mapping[str,Any],point:Mapping[str,Any])->float:
    if resolution.get("status")!="LIBRARY_HIT__VERIFY_BEFORE_USE": raise CapabilityRegistryV5Error("RESOLUTION_NOT_LIBRARY_HIT")
    match=resolution.get("match")
    if not isinstance(match,Mapping): raise CapabilityRegistryV5Error("MATCH_INVALID")
    if match.get("route")!=ERF["route"]:
        return v4.predict(resolution,point)
    cand=match["candidate"]; x=float(point["x"])
    coeff=cand["coefficients"]; g=float(cand["gamma"])
    y=float(coeff[0])+float(coeff[1])*x+float(coeff[2])*math.erf(g*x)
    if not math.isfinite(y): raise CapabilityRegistryV5Error("PREDICTION_NONFINITE")
    return y

def invoke(capability_id:str,payload:Mapping[str,Any])->dict[str,Any]:
    if capability_id==ERF["capability_id"]: raise CapabilityRegistryV5Error("PARAMETRIC_CAPABILITY_REQUIRES_RESOLUTION")
    out=v4.invoke(capability_id,payload); row=dict(out);row["schema"]=SCHEMA;row["registry_version"]=5
    return row
