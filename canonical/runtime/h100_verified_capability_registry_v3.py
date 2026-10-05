"""H100 verified capability registry V3.

V3 preserves Registry V2 unchanged and adds only four patch structures that
passed the frozen multi-family seed->transfer experiment:
- affine + x^5
- affine + hinge(x-t)
- affine + exp(-gamma*x^2)
- affine + tanh(gamma*x)

All parameters are fitted at runtime. No persistent learned state is added.
Unknown and ambiguous structures fail closed.
"""
from __future__ import annotations
import json, math
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_verified_capability_registry_v2 as v2
from canonical.runtime import h100_generic_patch_search_transfer_v1 as generic

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_GENERIC_PATCH_SEARCH_TRANSFER_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_VERIFIED_CAPABILITY_REGISTRY_V3"
PRIOR="canonical/verification/H100_GENERIC_PATCH_SEARCH_TRANSFER_SECOND_CARRIER_VERIFICATION_20261005_V1.json"

ADDITIONS=(
    {"capability_id":"CAP_AFFINE_POWER5_V1","family_id":"POWER","shape_policy":"FIXED_POWER_5"},
    {"capability_id":"CAP_AFFINE_HINGE_V1","family_id":"HINGE","shape_policy":"REFIT_THRESHOLD_GRID"},
    {"capability_id":"CAP_AFFINE_GAUSSIAN_V1","family_id":"GAUSSIAN","shape_policy":"REFIT_GAMMA_GRID"},
    {"capability_id":"CAP_AFFINE_TANH_V1","family_id":"TANH","shape_policy":"REFIT_GAMMA_GRID"},
)
REGISTRY=tuple(v2.REGISTRY)+tuple({
    **row,
    "kind":"PARAMETRIC_PATCH",
    "route":"GENERIC_PATCH_SEARCH_TRANSFER_V1",
    "prior_verification":PRIOR,
} for row in ADDITIONS)

_BY_FAMILY={row["family_id"]:row for row in ADDITIONS}

class CapabilityRegistryV3Error(ValueError):
    pass

def registry_snapshot()->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"VERIFIED_CAPABILITY_REGISTRY_V3_READY",
        "entry_count":len(REGISTRY),
        "entries":[dict(x) for x in REGISTRY],
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "routing_priority":"REGISTRY_V2_THEN_TRANSFER_VERIFIED_PATCH_FAMILIES_THEN_RAW_SEARCH",
    }

def _candidate_for_family(rows:Sequence[Mapping[str,Any]], family_id:str):
    pre=json.loads(PRE.read_text())
    xs=[float(r["x"]) for r in rows]
    specs=generic._specs(pre,family=family_id,train_x=xs)
    if family_id=="POWER":
        specs=[s for s in specs if s[1]==5]
    candidates=[]
    for spec in specs:
        c=generic._fit_candidate(list(rows),list(rows),*spec)
        if c is not None:
            candidates.append(c)
    candidates.sort(key=lambda c:(c["train_nrmse"],str(c["shape_parameter"])))
    return candidates[0] if candidates else None

def resolve_verified_capability(
    rows:Sequence[Mapping[str,Any]],
    *,
    target:str,
    input_name:str|None=None,
    exact_nrmse:float=1e-8,
)->dict[str,Any]:
    base=v2.resolve_verified_capability(
        rows,target=target,input_name=input_name,exact_nrmse=exact_nrmse
    )
    if base.get("status")=="LIBRARY_HIT__VERIFY_BEFORE_USE":
        out=dict(base)
        out["schema"]=SCHEMA
        out["registry_version"]=3
        return out

    if str(target)!="y" or (input_name is not None and str(input_name)!="x"):
        return {
            "schema":SCHEMA,"status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",
            "registry_version":3,"reason":"PATCH_SCHEMA_UNSUPPORTED","match":None,
            "persistent_learned_bytes":0,"external_learned_capability_calls":0,
        }

    passing=[]
    for family_id,entry in _BY_FAMILY.items():
        try:
            cand=_candidate_for_family(rows,family_id)
        except Exception:
            cand=None
        if isinstance(cand,Mapping) and float(cand.get("train_nrmse",float("inf")))<=exact_nrmse:
            passing.append((family_id,entry,cand))

    if len(passing)==1:
        family_id,entry,cand=passing[0]
        return {
            "schema":SCHEMA,
            "status":"LIBRARY_HIT__VERIFY_BEFORE_USE",
            "registry_version":3,
            "match":{
                "capability_id":entry["capability_id"],
                "family":family_id,
                "route":"GENERIC_PATCH_SEARCH_TRANSFER_V1",
                "candidate":dict(cand),
                "prior_verification":PRIOR,
            },
            "persistent_learned_bytes":0,
            "external_learned_capability_calls":0,
            "raw_synthesis_attempts_before_hit":0,
        }
    if len(passing)>1:
        return {
            "schema":SCHEMA,"status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",
            "registry_version":3,"reason":"AMBIGUOUS_MULTIPLE_VERIFIED_PATCH_FAMILIES",
            "candidate_families":[x[0] for x in passing],"match":None,
            "persistent_learned_bytes":0,"external_learned_capability_calls":0,
        }
    return {
        "schema":SCHEMA,"status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",
        "registry_version":3,"reason":"NO_VERIFIED_EXACT_LIBRARY_FAMILY","match":None,
        "persistent_learned_bytes":0,"external_learned_capability_calls":0,
    }

def _feature(family_id:str,param:Any,x:float)->float:
    if family_id=="POWER": return x**int(param)
    if family_id=="HINGE": return max(0.0,x-float(param))
    if family_id=="GAUSSIAN": return math.exp(-float(param)*x*x)
    if family_id=="TANH": return math.tanh(float(param)*x)
    raise CapabilityRegistryV3Error("PATCH_FAMILY_UNKNOWN")

def predict(resolution:Mapping[str,Any],point:Mapping[str,Any])->float:
    if resolution.get("status")!="LIBRARY_HIT__VERIFY_BEFORE_USE":
        raise CapabilityRegistryV3Error("RESOLUTION_NOT_LIBRARY_HIT")
    match=resolution.get("match")
    if not isinstance(match,Mapping):
        raise CapabilityRegistryV3Error("MATCH_INVALID")
    if match.get("route")!="GENERIC_PATCH_SEARCH_TRANSFER_V1":
        return v2.predict(resolution,point)
    cand=match.get("candidate")
    if not isinstance(cand,Mapping):
        raise CapabilityRegistryV3Error("CANDIDATE_INVALID")
    if "x" not in point:
        raise CapabilityRegistryV3Error("INPUT_MISSING")
    x=float(point["x"])
    coeff=cand.get("coefficients")
    if not isinstance(coeff,list) or len(coeff)!=3:
        raise CapabilityRegistryV3Error("COEFFICIENTS_INVALID")
    z=_feature(str(cand["family_id"]),cand.get("shape_parameter"),x)
    y=float(coeff[0])+float(coeff[1])*x+float(coeff[2])*z
    if not math.isfinite(y):
        raise CapabilityRegistryV3Error("PREDICTION_NONFINITE")
    return y

def invoke(capability_id:str,payload:Mapping[str,Any])->dict[str,Any]:
    if capability_id in {x["capability_id"] for x in ADDITIONS}:
        raise CapabilityRegistryV3Error("PARAMETRIC_CAPABILITY_REQUIRES_RESOLUTION")
    out=v2.invoke(capability_id,payload)
    row=dict(out);row["schema"]=SCHEMA;row["registry_version"]=3
    return row
