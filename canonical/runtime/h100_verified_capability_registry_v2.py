"""H100 verified capability registry V2.

V2 preserves every V1 route unchanged and adds one separately verified,
zero-learned cubic polynomial family. Unknown inputs still fail closed.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_verified_capability_registry_v1 as v1
from canonical.runtime import h100_zero_learned_polynomial_patch_v1 as poly

SCHEMA="PROJECT_BRAIN_H100_VERIFIED_CAPABILITY_REGISTRY_V2"
CUBIC={
    "capability_id":"CAP_AFFINE_CUBIC_V1",
    "kind":"PARAMETRIC_POLY",
    "family":"affine_plus_power",
    "fixed_power":3,
    "route":"ZERO_LEARNED_POLYNOMIAL_PATCH_V1",
    "prior_verification":"canonical/verification/H100_MINIMAL_PATCH_SEARCH_SEPARATE_RUNTIME_VERIFICATION_20261005_V1.json",
}
REGISTRY=tuple(v1.REGISTRY)+(CUBIC,)

class CapabilityRegistryV2Error(ValueError):
    pass

def registry_snapshot()->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"VERIFIED_CAPABILITY_REGISTRY_V2_READY",
        "entry_count":len(REGISTRY),
        "entries":[dict(x) for x in REGISTRY],
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "routing_priority":"V1_LIBRARY_THEN_VERIFIED_CUBIC_THEN_RAW_SEARCH",
    }

def _input_name(rows:Sequence[Mapping[str,Any]], target:str, input_name:str|None)->str|None:
    if input_name is not None:
        text=str(input_name).strip()
        return text or None
    if not rows or not isinstance(rows[0],Mapping):
        return None
    names=[str(k) for k in rows[0] if str(k)!=str(target)]
    return names[0] if len(names)==1 else None

def resolve_verified_capability(
    rows:Sequence[Mapping[str,Any]],
    *,
    target:str,
    input_name:str|None=None,
    exact_nrmse:float=1e-8,
)->dict[str,Any]:
    base=v1.resolve_verified_capability(
        rows,target=target,input_name=input_name,exact_nrmse=exact_nrmse
    )
    if base.get("status")=="LIBRARY_HIT__VERIFY_BEFORE_USE":
        out=dict(base)
        out["schema"]=SCHEMA
        out["registry_version"]=2
        return out

    name=_input_name(rows,target,input_name)
    if name is not None:
        try:
            cand=poly.fit(rows,target=target,input_name=name,power=3)
        except poly.PolynomialPatchError:
            cand=None
        if isinstance(cand,Mapping) and float(cand.get("train_nrmse",float("inf"))) <= exact_nrmse:
            return {
                "schema":SCHEMA,
                "status":"LIBRARY_HIT__VERIFY_BEFORE_USE",
                "registry_version":2,
                "match":{
                    "capability_id":CUBIC["capability_id"],
                    "family":CUBIC["family"],
                    "route":CUBIC["route"],
                    "candidate":dict(cand),
                    "prior_verification":CUBIC["prior_verification"],
                },
                "persistent_learned_bytes":0,
                "external_learned_capability_calls":0,
                "raw_synthesis_attempts_before_hit":0,
            }

    return {
        "schema":SCHEMA,
        "status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",
        "registry_version":2,
        "reason":"NO_VERIFIED_EXACT_LIBRARY_FAMILY",
        "match":None,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
    }

def predict(resolution:Mapping[str,Any],point:Mapping[str,Any])->float:
    if resolution.get("status")!="LIBRARY_HIT__VERIFY_BEFORE_USE":
        raise CapabilityRegistryV2Error("RESOLUTION_NOT_LIBRARY_HIT")
    match=resolution.get("match")
    if not isinstance(match,Mapping):
        raise CapabilityRegistryV2Error("MATCH_INVALID")
    if match.get("route")==CUBIC["route"]:
        return poly.predict(match["candidate"],point)
    return v1.predict(resolution,point)

def invoke(capability_id:str,payload:Mapping[str,Any])->dict[str,Any]:
    if capability_id==CUBIC["capability_id"]:
        raise CapabilityRegistryV2Error("PARAMETRIC_CAPABILITY_REQUIRES_RESOLUTION")
    out=v1.invoke(capability_id,payload)
    row=dict(out)
    row["schema"]=SCHEMA
    row["registry_version"]=2
    return row
