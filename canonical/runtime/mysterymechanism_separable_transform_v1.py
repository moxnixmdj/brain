"""Generic separable 2D transform discovery for sparse active-science tasks.

The learner stores no task formulas. It searches low-complexity univariate
transform families and fits a bilinear interaction surface

    y = b0 + b1*f(x1) + b2*g(x2) + b3*f(x1)*g(x2)

using all evidence except the reserved final experiment. The final experiment is
used as a prospective validation point, matching the public MysteryMechanism
2D shape (four corner interventions plus one interior intervention).

This is a candidate generator only. Public-development success is not a private
benchmark score and carries zero acceptance/family/ownership credit.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from canonical.runtime import mysterymechanism_sparse_symbolic_adapter_v1 as sparse

SCHEMA="PROJECT_BRAIN_MYSTERYMECHANISM_SEPARABLE_TRANSFORM_V1"
_RATIONAL=(0.25,1/3,0.5,0.625,2/3,0.8,1.0,1.5,2.0)
_BOUNDARY_P=tuple(round(0.5+0.1*i,10) for i in range(26))
_EPS=1e-12


class SeparableTransformError(ValueError):
    pass


def _descriptor_key(d: Mapping[str,Any]) -> tuple:
    return (str(d["kind"]),str(d.get("variable","")),round(float(d.get("power",0)),10),
            round(float(d.get("anchor",0)),10))


def _transform(d: Mapping[str,Any], x: float) -> float | None:
    kind=str(d["kind"])
    p=float(d.get("power",1.0))
    ax=abs(float(x))
    try:
        if kind=="identity":
            y=float(x)
        elif kind=="power":
            y=ax**p
        elif kind=="inv1p":
            y=1.0/(1.0+ax**p)
        elif kind=="satp":
            u=ax**p
            y=u/(1.0+u)
        elif kind in {"boundary_inverse","boundary_ratio"}:
            distance=abs(float(d["anchor"])-float(x))
            if distance<=_EPS:
                return None
            denom=distance**p
            y=1.0/denom if kind=="boundary_inverse" else float(x)/denom
        else:
            return None
    except (OverflowError,ValueError,ZeroDivisionError):
        return None
    return y if math.isfinite(y) else None


def _expr(d: Mapping[str,Any]) -> str:
    v=str(d["variable"])
    kind=str(d["kind"])
    p=repr(float(d.get("power",1.0)))
    if kind=="identity":
        return v
    if kind=="power":
        return f"(abs({v})**({p}))"
    if kind=="inv1p":
        return f"(1/(1+abs({v})**({p})))"
    if kind=="satp":
        return f"((abs({v})**({p}))/(1+abs({v})**({p})))"
    anchor=repr(float(d["anchor"]))
    base=f"abs(({anchor})-{v})**({p})"
    if kind=="boundary_inverse":
        return f"(1/({base}))"
    if kind=="boundary_ratio":
        return f"({v}/({base}))"
    raise SeparableTransformError("DESCRIPTOR_INVALID")


def _library(variable: str, values: Sequence[float], bound: tuple[float,float]) -> list[dict[str,Any]]:
    lo,hi=bound
    span=hi-lo
    descs=[{"kind":"identity","variable":variable}]
    for p in _RATIONAL:
        for kind in ("power","inv1p","satp"):
            descs.append({"kind":kind,"variable":variable,"power":p})
    anchors={-2.0,-1.0,0.0,1.0,2.0,lo-span,hi+span}
    for anchor in sorted(anchors):
        # A boundary singularity is admissible only if the anchor is provably
        # outside the declared physical interval.
        if lo <= anchor <= hi:
            continue
        for p in _BOUNDARY_P:
            descs.append({"kind":"boundary_inverse","variable":variable,"power":p,"anchor":anchor})
            descs.append({"kind":"boundary_ratio","variable":variable,"power":p,"anchor":anchor})

    out=[]
    seen=set()
    for d in descs:
        vec=[_transform(d,x) for x in values]
        if any(v is None or not math.isfinite(v) for v in vec):
            continue
        scale=max(1.0,max(abs(float(v)) for v in vec))
        key=tuple(round(float(v)/scale,10) for v in vec)
        if key in seen:
            continue
        seen.add(key)
        out.append({"descriptor":d,"values":[float(v) for v in vec]})
    out.sort(key=lambda r:_descriptor_key(r["descriptor"]))
    return out


def _fit_bilinear(a: Sequence[float], b: Sequence[float], y: Sequence[float]):
    interaction=[x*z for x,z in zip(a,b)]
    coeff=sparse._fit([a,b,interaction],y)
    if coeff is None:
        return None
    pred=[coeff[0]+coeff[1]*a[i]+coeff[2]*b[i]+coeff[3]*interaction[i] for i in range(len(y))]
    return coeff,pred


def discover(
    rows: Sequence[Mapping[str,Any]],
    *,
    bounds: Mapping[str,Sequence[Any]],
    target: str="out",
    validation_index: int=-1,
) -> dict[str,Any]:
    b=sparse._normalize_bounds(bounds)
    if len(b)!=2:
        raise SeparableTransformError("EXACTLY_TWO_INPUTS_REQUIRED")
    target,names,data=sparse._normalize_rows(rows,target,list(b))
    if len(data)<7:
        raise SeparableTransformError("AT_LEAST_SEVEN_ROWS_REQUIRED")
    if validation_index<0:
        validation_index=len(data)+validation_index
    if not 0<=validation_index<len(data):
        raise SeparableTransformError("VALIDATION_INDEX_INVALID")

    fit_indices=[i for i in range(len(data)) if i!=validation_index]
    if len(fit_indices)<6:
        raise SeparableTransformError("SIX_FIT_ROWS_REQUIRED")
    y_all=[float(r[target]) for r in data]
    y_fit=[y_all[i] for i in fit_indices]
    global_scale=max(
        math.sqrt(sum((v-sum(y_all)/len(y_all))**2 for v in y_all)/len(y_all)),
        max(abs(v) for v in y_all)*1e-9,_EPS
    )

    n1,n2=names
    vals1=[float(r[n1]) for r in data]
    vals2=[float(r[n2]) for r in data]
    l1=_library(n1,vals1,b[n1])
    l2=_library(n2,vals2,b[n2])

    best=None
    considered=0
    for left in l1:
        af=[left["values"][i] for i in fit_indices]
        for right in l2:
            considered+=1
            bf=[right["values"][i] for i in fit_indices]
            fit=_fit_bilinear(af,bf,y_fit)
            if fit is None:
                continue
            coeff,pred_fit=fit
            train_error=sparse._nrmse(y_fit,pred_fit)
            av=left["values"][validation_index]
            bv=right["values"][validation_index]
            validation_prediction=coeff[0]+coeff[1]*av+coeff[2]*bv+coeff[3]*av*bv
            validation_error=abs(validation_prediction-y_all[validation_index])/global_scale
            complexity=(
                1
                + (1 if left["descriptor"]["kind"]=="identity" else 3)
                + (1 if right["descriptor"]["kind"]=="identity" else 3)
                + (1 if "boundary" not in left["descriptor"]["kind"] else 2)
                + (1 if "boundary" not in right["descriptor"]["kind"] else 2)
            )
            score=max(train_error,validation_error)+1e-6*complexity
            key=(score,max(train_error,validation_error),complexity,
                 _descriptor_key(left["descriptor"]),_descriptor_key(right["descriptor"]))
            if best is None or key<best[0]:
                best=(key,{
                    "left":left["descriptor"],
                    "right":right["descriptor"],
                    "coefficients":[float(x) for x in coeff],
                    "fit_nrmse":float(train_error),
                    "reserved_validation_nrmse":float(validation_error),
                    "reserved_validation_prediction":float(validation_prediction),
                    "reserved_validation_actual":float(y_all[validation_index]),
                    "complexity":complexity,
                })
    if best is None:
        return {
            "schema":SCHEMA,"status":"SEPARABLE_GRAMMAR_EXHAUSTED","candidate":None,
            "transform_pairs_considered":considered,"acceptance_credit_delta":0,
            "family_credit_delta":0,"persistent_learned_bytes":0,
            "external_learned_capability_calls":0,
        }
    candidate=best[1]
    # Refit the selected structure on every observed row only after prospective
    # validation chose it.
    avec=[_transform(candidate["left"],x) for x in vals1]
    bvec=[_transform(candidate["right"],x) for x in vals2]
    refit=_fit_bilinear(avec,bvec,y_all)
    if refit is None:
        raise SeparableTransformError("FINAL_REFIT_FAILED")
    coeff,pred=refit
    candidate["coefficients"]=[float(x) for x in coeff]
    candidate["all_row_nrmse"]=float(sparse._nrmse(y_all,pred))
    candidate["prospective_selection_preserved"]=True
    expression=serialize(candidate)
    return {
        "schema":SCHEMA,
        "status":"SEPARABLE_CANDIDATE_FOUND__PUBLIC_OR_SYNTHETIC_ONLY",
        "input_variables":list(names),
        "row_count":len(data),
        "validation_index":validation_index,
        "left_library_size":len(l1),
        "right_library_size":len(l2),
        "transform_pairs_considered":considered,
        "candidate":candidate,
        "expression":expression,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "dynamic_code_execution":False,
        "random_search":False,
        "private_score_claimed":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
    }


def predict(candidate: Mapping[str,Any], point: Mapping[str,Any]) -> float:
    left,right=candidate["left"],candidate["right"]
    x=sparse._finite(point[str(left["variable"])],str(left["variable"]))
    z=sparse._finite(point[str(right["variable"])],str(right["variable"]))
    a=_transform(left,x); b=_transform(right,z)
    if a is None or b is None:
        raise SeparableTransformError("POINT_OUTSIDE_CANDIDATE_DOMAIN")
    c=[float(v) for v in candidate["coefficients"]]
    y=c[0]+c[1]*a+c[2]*b+c[3]*a*b
    if not math.isfinite(y):
        raise SeparableTransformError("PREDICTION_NONFINITE")
    return y


def serialize(candidate: Mapping[str,Any]) -> str:
    c=[float(v) for v in candidate["coefficients"]]
    a=_expr(candidate["left"])
    b=_expr(candidate["right"])
    return (
        repr(c[0])+"+("+repr(c[1])+")*("+a+")+("+repr(c[2])+")*("+b+")+"
        "("+repr(c[3])+")*("+a+")*("+b+")"
    )
