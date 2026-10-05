"""Deterministic zero-learned polynomial patch family for H100."""
from __future__ import annotations
import math
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_H100_ZERO_LEARNED_POLYNOMIAL_PATCH_V1"

class PolynomialPatchError(ValueError): pass

def _finite(v:Any,label:str)->float:
    if isinstance(v,bool): raise PolynomialPatchError(label+"_INVALID")
    try: x=float(v)
    except Exception as exc: raise PolynomialPatchError(label+"_INVALID") from exc
    if not math.isfinite(x): raise PolynomialPatchError(label+"_NONFINITE")
    return x

def _solve(a:list[list[float]],b:list[float])->list[float]|None:
    n=len(b); m=[list(map(float,a[i]))+[float(b[i])] for i in range(n)]
    for c in range(n):
        p=max(range(c,n),key=lambda r:abs(m[r][c]))
        if abs(m[p][c])<=1e-12: return None
        m[c],m[p]=m[p],m[c]
        div=m[c][c]; m[c]=[x/div for x in m[c]]
        for r in range(n):
            if r==c: continue
            f=m[r][c]
            if abs(f)<=1e-18: continue
            m[r]=[x-f*y for x,y in zip(m[r],m[c])]
    out=[m[i][-1] for i in range(n)]
    return out if all(math.isfinite(x) for x in out) else None

def _least_squares(cols:Sequence[Sequence[float]],y:Sequence[float])->list[float]|None:
    p=len(cols)
    if p==0 or not y or any(len(c)!=len(y) for c in cols): return None
    xtx=[[0.0]*p for _ in range(p)]; xty=[0.0]*p
    for r,t in enumerate(y):
        vals=[float(c[r]) for c in cols]
        for i in range(p):
            xty[i]+=vals[i]*float(t)
            for j in range(p): xtx[i][j]+=vals[i]*vals[j]
    for i in range(p): xtx[i][i]+=1e-13
    return _solve(xtx,xty)

def _nrmse(actual:Sequence[float],pred:Sequence[float])->float:
    mean=sum(actual)/len(actual)
    spread=math.sqrt(sum((x-mean)**2 for x in actual)/len(actual))
    scale=max(spread,max(abs(x) for x in actual)*1e-9,1e-12)
    return math.sqrt(sum((a-b)**2 for a,b in zip(actual,pred))/len(actual))/scale

def fit(rows:Sequence[Mapping[str,Any]],*,target:str,input_name:str,power:int)->dict[str,Any]:
    if power not in (2,3,4): raise PolynomialPatchError("POWER_NOT_IN_FROZEN_GRAMMAR")
    if not isinstance(rows,Sequence) or len(rows)<5: raise PolynomialPatchError("ROWS_INVALID")
    xs=[]; ys=[]
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping) or input_name not in row or target not in row:
            raise PolynomialPatchError("ROW_SCHEMA_MISMATCH:"+str(i))
        xs.append(_finite(row[input_name],input_name)); ys.append(_finite(row[target],target))
    coeff=_least_squares([[1.0]*len(xs),xs,[x**power for x in xs]],ys)
    if coeff is None: raise PolynomialPatchError("FIT_SINGULAR")
    pred=[coeff[0]+coeff[1]*x+coeff[2]*(x**power) for x in xs]
    return {
        "schema":SCHEMA,
        "family":"affine_plus_power",
        "power":power,
        "intercept":coeff[0],
        "linear":coeff[1],
        "power_coefficient":coeff[2],
        "input_name":input_name,
        "train_nrmse":_nrmse(ys,pred),
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
    }

def predict(candidate:Mapping[str,Any],point:Mapping[str,Any])->float:
    name=str(candidate.get("input_name") or "")
    if name not in point: raise PolynomialPatchError("INPUT_MISSING")
    x=_finite(point[name],name)
    p=int(candidate["power"])
    y=float(candidate["intercept"])+float(candidate["linear"])*x+float(candidate["power_coefficient"])*(x**p)
    if not math.isfinite(y): raise PolynomialPatchError("PREDICTION_NONFINITE")
    return y
