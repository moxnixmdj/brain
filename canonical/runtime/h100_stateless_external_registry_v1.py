from __future__ import annotations
import math
from typing import Any,Mapping,Sequence
from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr

class StatelessRegistryError(ValueError): pass

def _apply(x:float,seq:Sequence[str])->float:
    v=float(x)
    for op in seq:
        out=expr._apply_unary(str(op),v)
        if out is None: raise StatelessRegistryError("CHAIN_NONFINITE")
        v=float(out)
    return v

def _fit(rows,seq):
    xs=[float(r["x"]) for r in rows]
    ys=[float(r["y"]) for r in rows]
    feat=[_apply(x,seq) for x in xs]
    coeff=expr._fit_linear_features([xs,feat],ys)
    if coeff is None: return None
    pred=[coeff[0]+coeff[1]*x+coeff[2]*f for x,f in zip(xs,feat)]
    return {"coefficients":[float(z) for z in coeff],"train_nrmse":float(expr._nrmse(ys,pred))}

def resolve(rows,manifest,exact_nrmse:float=1e-8):
    if not isinstance(manifest,Sequence) or isinstance(manifest,(str,bytes)):
        raise StatelessRegistryError("MANIFEST_INVALID")
    candidates=[]
    for e in manifest:
        if not isinstance(e,Mapping): raise StatelessRegistryError("ENTRY_INVALID")
        cid=str(e["capability_id"])
        seq=[str(x) for x in e["sequence"]]
        fit=_fit(rows,seq)
        if fit is not None and fit["train_nrmse"]<=exact_nrmse:
            candidates.append((fit["train_nrmse"],cid,seq,fit))
    if not candidates:
        return {"status":"MISS","internal_persistent_causal_learned_bits":0}
    candidates.sort(key=lambda x:(x[0],x[1]))
    err,cid,seq,fit=candidates[0]
    return {"status":"HIT","capability_id":cid,"sequence":seq,"fit":fit,"internal_persistent_causal_learned_bits":0}

def predict(resolution,point):
    if resolution.get("status")!="HIT": raise StatelessRegistryError("NOT_HIT")
    a,b,c=resolution["fit"]["coefficients"]
    x=float(point["x"])
    return a+b*x+c*_apply(x,resolution["sequence"])
