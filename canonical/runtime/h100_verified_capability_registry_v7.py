"""H100 verified capability registry V7.

V7 preserves Registry V6 and compiles two independently verified non-stdlib
declarative operator-pack families. Packs are content-addressed data interpreted
by the bounded declarative runtime, never imported or executed as Python code.
"""
from __future__ import annotations
import math
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_verified_capability_registry_v6 as v6
from canonical.runtime import h100_declarative_operator_pack_acquisition_v1 as packrt

SCHEMA="PROJECT_BRAIN_H100_VERIFIED_CAPABILITY_REGISTRY_V7"
PRIOR="canonical/verification/H100_DECLARATIVE_OPERATOR_PACK_ACQUISITION_SECOND_CARRIER_VERIFICATION_20261005_V1.json"

NEW=(
    {
        "capability_id":"CAP_AFFINE_ASYM_CLAMP_V1",
        "kind":"PARAMETRIC_DECLARATIVE_PACK",
        "family":"AFFINE_DECLARATIVE_ASYM_CLAMP",
        "operator_id":"ASYM_CLAMP_V1",
        "route":"VERIFIED_DECLARATIVE_OPERATOR_PACK_REFIT",
        "pack_path":"canonical/capabilities/h100/operator_packs/ASYM_CLAMP_V1.json",
        "pack_git_blob_sha":"3e61fca61e75a4725bdad4071e767dba63e7e708",
        "gamma_grid":[0.25,0.5,0.75,0.8,1.0,1.25,1.3,1.5,1.75,2.0],
        "prior_verification":PRIOR,
    },
    {
        "capability_id":"CAP_AFFINE_TRIANGLE_V1",
        "kind":"PARAMETRIC_DECLARATIVE_PACK",
        "family":"AFFINE_DECLARATIVE_TRIANGLE",
        "operator_id":"TRIANGLE_V1",
        "route":"VERIFIED_DECLARATIVE_OPERATOR_PACK_REFIT",
        "pack_path":"canonical/capabilities/h100/operator_packs/TRIANGLE_V1.json",
        "pack_git_blob_sha":"fbd4a385207261f015a6ba62a610c5f0a02be5c0",
        "gamma_grid":[0.25,0.5,0.75,1.0,1.25,1.5,1.75,2.0],
        "prior_verification":PRIOR,
    },
)
REGISTRY=tuple(v6.REGISTRY)+NEW

class CapabilityRegistryV7Error(ValueError):
    pass

def registry_snapshot()->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"VERIFIED_CAPABILITY_REGISTRY_V7_READY",
        "entry_count":len(REGISTRY),
        "entries":[dict(x) for x in REGISTRY],
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "routing_priority":"REGISTRY_V6_THEN_VERIFIED_DECLARATIVE_PACKS_THEN_RAW_SEARCH",
    }

def _contract():
    import json
    pre=json.loads(packrt.PRE.read_text())
    return pre["pack_contract"]

def _loaded(entry:Mapping[str,Any]):
    return packrt.load_pack(
        packrt.ROOT/str(entry["pack_path"]),
        str(entry["pack_git_blob_sha"]),
        _contract(),
    )

def _best(rows:Sequence[Mapping[str,Any]],entry:Mapping[str,Any]):
    loaded=_loaded(entry)
    out=[]
    for g in entry["gamma_grid"]:
        c=packrt._fit(rows,loaded,float(g))
        if c is not None:
            row=dict(c)
            row["operator_id"]=entry["operator_id"]
            out.append(row)
    out.sort(key=lambda c:(c["train_nrmse"],c["gamma"],c["operator_id"]))
    return out[0] if out else None

def resolve_verified_capability(
    rows:Sequence[Mapping[str,Any]],
    *,
    target:str,
    input_name:str|None=None,
    exact_nrmse:float=1e-8,
)->dict[str,Any]:
    base=v6.resolve_verified_capability(rows,target=target,input_name=input_name,exact_nrmse=exact_nrmse)
    if base.get("status")=="LIBRARY_HIT__VERIFY_BEFORE_USE":
        out=dict(base); out["schema"]=SCHEMA; out["registry_version"]=7
        return out
    if str(target)!="y" or (input_name is not None and str(input_name)!="x"):
        return {
            "schema":SCHEMA,"status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED","registry_version":7,
            "reason":"DECLARATIVE_PACK_SCHEMA_UNSUPPORTED","match":None,
            "persistent_learned_bytes":0,"external_learned_capability_calls":0,
        }
    candidates=[]
    for entry in NEW:
        c=_best(rows,entry)
        if c is not None and float(c["train_nrmse"])<=exact_nrmse:
            candidates.append((float(c["train_nrmse"]),str(entry["capability_id"]),entry,c))
    if candidates:
        candidates.sort(key=lambda x:(x[0],x[1]))
        _err,_cid,entry,cand=candidates[0]
        return {
            "schema":SCHEMA,"status":"LIBRARY_HIT__VERIFY_BEFORE_USE","registry_version":7,
            "match":{
                "capability_id":entry["capability_id"],
                "family":entry["family"],
                "route":entry["route"],
                "candidate":dict(cand),
                "pack_path":entry["pack_path"],
                "pack_git_blob_sha":entry["pack_git_blob_sha"],
                "prior_verification":entry["prior_verification"],
            },
            "persistent_learned_bytes":0,
            "external_learned_capability_calls":0,
            "raw_synthesis_attempts_before_hit":0,
        }
    return {
        "schema":SCHEMA,"status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED","registry_version":7,
        "reason":"NO_VERIFIED_EXACT_LIBRARY_FAMILY","match":None,
        "persistent_learned_bytes":0,"external_learned_capability_calls":0,
    }

def predict(resolution:Mapping[str,Any],point:Mapping[str,Any])->float:
    if resolution.get("status")!="LIBRARY_HIT__VERIFY_BEFORE_USE":
        raise CapabilityRegistryV7Error("RESOLUTION_NOT_LIBRARY_HIT")
    match=resolution.get("match")
    if not isinstance(match,Mapping):
        raise CapabilityRegistryV7Error("MATCH_INVALID")
    if match.get("route")!="VERIFIED_DECLARATIVE_OPERATOR_PACK_REFIT":
        return v6.predict(resolution,point)
    entry=next((e for e in NEW if e["capability_id"]==match["capability_id"]),None)
    if entry is None:
        raise CapabilityRegistryV7Error("DECLARATIVE_ENTRY_UNKNOWN")
    loaded=_loaded(entry)
    cand=match["candidate"]
    x=float(point["x"])
    coeff=cand["coefficients"]; g=float(cand["gamma"])
    y=float(coeff[0])+float(coeff[1])*x+float(coeff[2])*packrt.evaluate_pack(loaded,g*x)
    if not math.isfinite(y):
        raise CapabilityRegistryV7Error("PREDICTION_NONFINITE")
    return y

def invoke(capability_id:str,payload:Mapping[str,Any])->dict[str,Any]:
    if capability_id in {x["capability_id"] for x in NEW}:
        raise CapabilityRegistryV7Error("PARAMETRIC_CAPABILITY_REQUIRES_RESOLUTION")
    out=v6.invoke(capability_id,payload)
    row=dict(out); row["schema"]=SCHEMA; row["registry_version"]=7
    return row
