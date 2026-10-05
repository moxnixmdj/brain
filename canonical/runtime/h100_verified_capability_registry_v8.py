"""H100 verified capability registry V8.

V8 preserves Registry V7 and compiles exactly three independently verified
depth-4 unary-chain structures. It does not compile the full search grammar.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_verified_capability_registry_v7 as v7
from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr

SCHEMA="PROJECT_BRAIN_H100_VERIFIED_CAPABILITY_REGISTRY_V8"
PRIOR="canonical/verification/H100_COMPLETE_UNARY_CHAIN_SEARCH_SECOND_CARRIER_VERIFICATION_20261005_V1.json"

NEW=(
    {
        "capability_id":"CAP_AFFINE_CHAIN_SQUARE_LOG_SQRT_SAT_V1",
        "kind":"PARAMETRIC_FIXED_UNARY_CHAIN",
        "family":"AFFINE_FIXED_UNARY_CHAIN",
        "sequence":["square","log1p_abs","sqrt_abs","sat"],
        "signature":"sat(sqrt_abs(log1p_abs(square(v0))))",
        "route":"VERIFIED_FIXED_UNARY_CHAIN_REFIT",
        "prior_verification":PRIOR,
    },
    {
        "capability_id":"CAP_AFFINE_CHAIN_SAT_SQUARE_LOG_SQRT_V1",
        "kind":"PARAMETRIC_FIXED_UNARY_CHAIN",
        "family":"AFFINE_FIXED_UNARY_CHAIN",
        "sequence":["sat","square","log1p_abs","sqrt_abs"],
        "signature":"sqrt_abs(log1p_abs(square(sat(v0))))",
        "route":"VERIFIED_FIXED_UNARY_CHAIN_REFIT",
        "prior_verification":PRIOR,
    },
    {
        "capability_id":"CAP_AFFINE_CHAIN_LOG_SAT_SQRT_LOG_V1",
        "kind":"PARAMETRIC_FIXED_UNARY_CHAIN",
        "family":"AFFINE_FIXED_UNARY_CHAIN",
        "sequence":["log1p_abs","sat","sqrt_abs","log1p_abs"],
        "signature":"log1p_abs(sqrt_abs(sat(log1p_abs(v0))))",
        "route":"VERIFIED_FIXED_UNARY_CHAIN_REFIT",
        "prior_verification":PRIOR,
    },
)
REGISTRY=tuple(v7.REGISTRY)+NEW


class CapabilityRegistryV8Error(ValueError):
    pass


def registry_snapshot()->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"VERIFIED_CAPABILITY_REGISTRY_V8_READY",
        "entry_count":len(REGISTRY),
        "entries":[dict(x) for x in REGISTRY],
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "routing_priority":"REGISTRY_V7_THEN_THREE_VERIFIED_DEPTH4_CHAINS_THEN_RAW_SEARCH",
    }


def _apply_sequence(x:float, sequence:Sequence[str])->float:
    value=float(x)
    for op in sequence:
        out=expr._apply_unary(str(op),value)
        if out is None:
            raise CapabilityRegistryV8Error("CHAIN_NONFINITE:"+str(op))
        value=float(out)
    return value


def _fit(rows:Sequence[Mapping[str,Any]], sequence:Sequence[str], *, target:str, input_name:str):
    if len(rows)<8:
        return None
    xs=[]
    ys=[]
    chain=[]
    try:
        for row in rows:
            x=float(row[input_name])
            y=float(row[target])
            if not math.isfinite(x) or not math.isfinite(y):
                return None
            xs.append(x)
            ys.append(y)
            chain.append(_apply_sequence(x,sequence))
    except (KeyError,TypeError,ValueError,CapabilityRegistryV8Error):
        return None
    coeff=expr._fit_linear_features([xs,chain],ys)
    if coeff is None:
        return None
    pred=[coeff[0]+coeff[1]*x+coeff[2]*f for x,f in zip(xs,chain)]
    err=expr._nrmse(ys,pred)
    return {
        "coefficients":[float(x) for x in coeff],
        "train_nrmse":float(err),
        "sequence":[str(x) for x in sequence],
    }


def resolve_verified_capability(
    rows:Sequence[Mapping[str,Any]],
    *,
    target:str,
    input_name:str|None=None,
    exact_nrmse:float=1e-8,
)->dict[str,Any]:
    base=v7.resolve_verified_capability(rows,target=target,input_name=input_name,exact_nrmse=exact_nrmse)
    if base.get("status")=="LIBRARY_HIT__VERIFY_BEFORE_USE":
        out=dict(base)
        out["schema"]=SCHEMA
        out["registry_version"]=8
        return out

    name=str(input_name or "").strip()
    if str(target)!="y" or name!="x":
        return {
            "schema":SCHEMA,
            "status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",
            "registry_version":8,
            "reason":"FIXED_CHAIN_SCHEMA_UNSUPPORTED",
            "match":None,
            "persistent_learned_bytes":0,
            "external_learned_capability_calls":0,
        }

    candidates=[]
    for entry in NEW:
        cand=_fit(rows,entry["sequence"],target="y",input_name="x")
        if cand is not None and float(cand["train_nrmse"])<=exact_nrmse:
            candidates.append((float(cand["train_nrmse"]),str(entry["capability_id"]),entry,cand))
    if candidates:
        candidates.sort(key=lambda x:(x[0],x[1]))
        _err,_cid,entry,cand=candidates[0]
        return {
            "schema":SCHEMA,
            "status":"LIBRARY_HIT__VERIFY_BEFORE_USE",
            "registry_version":8,
            "match":{
                "capability_id":entry["capability_id"],
                "family":entry["family"],
                "route":entry["route"],
                "candidate":dict(cand),
                "sequence":list(entry["sequence"]),
                "signature":entry["signature"],
                "prior_verification":entry["prior_verification"],
            },
            "persistent_learned_bytes":0,
            "external_learned_capability_calls":0,
            "raw_synthesis_attempts_before_hit":0,
        }

    return {
        "schema":SCHEMA,
        "status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",
        "registry_version":8,
        "reason":"NO_VERIFIED_EXACT_LIBRARY_FAMILY",
        "match":None,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
    }


def predict(resolution:Mapping[str,Any], point:Mapping[str,Any])->float:
    if resolution.get("status")!="LIBRARY_HIT__VERIFY_BEFORE_USE":
        raise CapabilityRegistryV8Error("RESOLUTION_NOT_LIBRARY_HIT")
    match=resolution.get("match")
    if not isinstance(match,Mapping):
        raise CapabilityRegistryV8Error("MATCH_INVALID")
    if match.get("route")!="VERIFIED_FIXED_UNARY_CHAIN_REFIT":
        return v7.predict(resolution,point)
    cand=match.get("candidate")
    if not isinstance(cand,Mapping):
        raise CapabilityRegistryV8Error("CANDIDATE_INVALID")
    x=float(point["x"])
    seq=match.get("sequence")
    if not isinstance(seq,Sequence) or isinstance(seq,(str,bytes)):
        raise CapabilityRegistryV8Error("SEQUENCE_INVALID")
    f=_apply_sequence(x,[str(s) for s in seq])
    coeff=[float(z) for z in cand["coefficients"]]
    if len(coeff)!=3:
        raise CapabilityRegistryV8Error("COEFFICIENT_COUNT_INVALID")
    y=coeff[0]+coeff[1]*x+coeff[2]*f
    if not math.isfinite(y):
        raise CapabilityRegistryV8Error("PREDICTION_NONFINITE")
    return y


def invoke(capability_id:str,payload:Mapping[str,Any])->dict[str,Any]:
    if capability_id in {x["capability_id"] for x in NEW}:
        raise CapabilityRegistryV8Error("PARAMETRIC_CAPABILITY_REQUIRES_RESOLUTION")
    out=v7.invoke(capability_id,payload)
    row=dict(out)
    row["schema"]=SCHEMA
    row["registry_version"]=8
    return row
