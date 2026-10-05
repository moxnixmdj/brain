"""Target-independent sign-quotient unary search through depth 8.

The quotient relation is exact equality up to a global sign on the frozen input
population. This relation is a congruence for the frozen unary operator set:
neg and sat preserve sign-equivalence; abs/square/sqrt_abs/log1p_abs collapse
it to equality. Because the terminal model fits a free coefficient on the
feature, global sign is behaviorally irrelevant.

All quotient classes and selected structures are transient process state.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_SIGN_QUOTIENT_DEPTH8_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_SIGN_QUOTIENT_DEPTH8_RESULT_V1"

class SignQuotientError(ValueError):
    pass

def _apply_scalar(op:str, x:float)->float:
    y=expr._apply_unary(str(op),float(x))
    if y is None or not math.isfinite(float(y)):
        raise SignQuotientError("NONFINITE:"+str(op))
    return float(y)

def _apply_vector(op:str, values:Sequence[float])->tuple[float,...]:
    return tuple(_apply_scalar(op,x) for x in values)

def _canonical_sign(values:Sequence[float])->tuple[float,...]:
    vals=[0.0 if float(x)==0.0 else float(x) for x in values]
    sign=1.0
    for x in vals:
        if x!=0.0:
            if x<0.0:
                sign=-1.0
            break
    return tuple(0.0 if sign*x==0.0 else sign*x for x in vals)

def _sign_key(values:Sequence[float])->tuple[str,...]:
    return tuple(float(x).hex() for x in _canonical_sign(values))

def _signature(sequence:Sequence[str])->str:
    tree:dict[str,Any]={"op":"var","name":"x"}
    for op in sequence:
        tree={"op":str(op),"arg":tree}
    return expr._structural_signature(tree,("x",))

def _truth_values(task:Mapping[str,Any], phase:str, xs:Sequence[float])->list[float]:
    seq=[str(x) for x in task["sequence"]]
    coeff=[float(x) for x in task[phase]]
    out=[]
    for x in xs:
        f=float(x)
        for op in seq:
            f=_apply_scalar(op,f)
        out.append(coeff[0]+coeff[1]*float(x)+coeff[2]*f)
    return out

def _fit_feature(
    train_x:Sequence[float],
    hold_x:Sequence[float],
    train_y:Sequence[float],
    hold_y:Sequence[float],
    feature_all:Sequence[float],
)->dict[str,Any]|None:
    n=len(train_x)
    tf=[float(x) for x in feature_all[:n]]
    hf=[float(x) for x in feature_all[n:]]
    coeff=expr._fit_linear_features([list(train_x),tf],list(train_y))
    if coeff is None:
        return None
    ptrain=[coeff[0]+coeff[1]*x+coeff[2]*f for x,f in zip(train_x,tf)]
    train_err=float(expr._nrmse(list(train_y),ptrain))
    if train_err>1e-10:
        return {"coefficients":[float(x) for x in coeff],"train_nrmse":train_err,"holdout_nrmse":None}
    phold=[coeff[0]+coeff[1]*x+coeff[2]*f for x,f in zip(hold_x,hf)]
    hold_err=float(expr._nrmse(list(hold_y),phold))
    return {
        "coefficients":[float(x) for x in coeff],
        "train_nrmse":train_err,
        "holdout_nrmse":hold_err,
    }

def congruence_audit(ops:Sequence[str], sample:Sequence[float])->dict[str,Any]:
    rows={}
    for op in ops:
        a=_apply_vector(op,sample)
        b=_apply_vector(op,[-float(x) for x in sample])
        ok=_sign_key(a)==_sign_key(b)
        rows[str(op)]={"pass":ok}
    return {
        "all_pass":all(r["pass"] for r in rows.values()),
        "operators":rows,
    }

def build_transient_basis(pre:Mapping[str,Any])->dict[str,Any]:
    ops=[str(x) for x in pre["operator_order"]]
    all_x=tuple(float(x) for x in pre["train_x"]+pre["holdout_x"])
    max_depth=int(pre["max_depth"])
    start=time.perf_counter()

    base={"values":all_x,"sequence":tuple(),"signature":"v0","depth":0}
    seen={_sign_key(all_x):0}
    frontier=[base]
    by_depth={}
    generated_edges=0

    for depth in range(1,max_depth+1):
        new={}
        for rec in frontier:
            for op in ops:
                generated_edges+=1
                values=_apply_vector(op,rec["values"])
                key=_sign_key(values)
                if key in seen or key in new:
                    continue
                seq=tuple(rec["sequence"])+(op,)
                new[key]={
                    "values":values,
                    "sequence":seq,
                    "signature":_signature(seq),
                    "depth":depth,
                }
        ordered=sorted(new.values(),key=lambda r:r["signature"])
        for rec in ordered:
            seen[_sign_key(rec["values"])]=depth
        by_depth[str(depth)]=ordered
        frontier=ordered

    elapsed=time.perf_counter()-start
    return {
        "by_depth":by_depth,
        "class_count_by_depth":{d:len(v) for d,v in by_depth.items()},
        "global_unique_class_count":len(seen)-1,
        "generated_quotient_edges":generated_edges,
        "basis_generation_seconds":elapsed,
        "raw_cumulative_sequence_count":sum(len(ops)**d for d in range(1,max_depth+1)),
    }

def solve_task(task:Mapping[str,Any], pre:Mapping[str,Any], basis:Mapping[str,Any])->dict[str,Any]:
    train_x=[float(x) for x in pre["train_x"]]
    hold_x=[float(x) for x in pre["holdout_x"]]
    train_y=_truth_values(task,"seed",train_x)
    hold_y=_truth_values(task,"seed",hold_x)
    start=time.perf_counter()
    selected=None
    first=None
    exact_count_by_depth={}
    for depth in range(1,int(pre["max_depth"])+1):
        exact=[]
        for rec in basis["by_depth"][str(depth)]:
            fit=_fit_feature(train_x,hold_x,train_y,hold_y,rec["values"])
            if fit is None or fit["holdout_nrmse"] is None:
                continue
            if fit["train_nrmse"]<=1e-10 and fit["holdout_nrmse"]<=1e-8:
                exact.append({
                    "sequence":list(rec["sequence"]),
                    "signature":rec["signature"],
                    "depth":depth,
                    **fit,
                })
        exact.sort(key=lambda r:r["signature"])
        exact_count_by_depth[str(depth)]=len(exact)
        if selected is None and exact:
            selected=exact[0]
            first=depth
    elapsed=time.perf_counter()-start
    return {
        "first_exact_depth":first,
        "selected":selected,
        "exact_count_by_depth":exact_count_by_depth,
        "solve_seconds":elapsed,
    }

def transfer_task(task:Mapping[str,Any], pre:Mapping[str,Any], selected:Mapping[str,Any])->dict[str,Any]:
    train_x=[float(x) for x in pre["train_x"]]
    hold_x=[float(x) for x in pre["holdout_x"]]
    train_y=_truth_values(task,"transfer",train_x)
    hold_y=_truth_values(task,"transfer",hold_x)
    all_x=train_x+hold_x
    feature=[]
    for x in all_x:
        v=float(x)
        for op in selected["sequence"]:
            v=_apply_scalar(str(op),v)
        feature.append(v)
    fit=_fit_feature(train_x,hold_x,train_y,hold_y,feature)
    if fit is None or fit["holdout_nrmse"] is None:
        return {"status":"TRANSFER_FAILED"}
    return {"status":"TRANSFER_OK",**fit,"sequence":list(selected["sequence"])}

def run()->dict[str,Any]:
    pre=json.loads(PRE.read_text())
    if "FROZEN_BEFORE_FRESH_DEPTH8_TASK_OUTCOMES" not in str(pre.get("status","")):
        raise SignQuotientError("PRECOMMIT_NOT_FROZEN")
    ops=[str(x) for x in pre["operator_order"]]
    audit=congruence_audit(ops,[-3.7,-1.2,-0.1,0.0,0.4,1.9,3.3])
    basis=build_transient_basis(pre)
    rows=[]
    for task in pre["fresh_tasks"]:
        solved=solve_task(task,pre,basis)
        trans=None if solved["selected"] is None else transfer_task(task,pre,solved["selected"])
        rows.append({
            "task_id":task["id"],
            "truth_sequence":task["sequence"],
            "solve":solved,
            "transfer":trans,
        })
    raw=int(basis["raw_cumulative_sequence_count"])
    unique=int(basis["global_unique_class_count"])
    deep=sum(1 for row in rows if (row["solve"]["first_exact_depth"] or 0)>=7)
    passed=(
        audit["all_pass"]
        and all(row["solve"]["selected"] is not None for row in rows)
        and all(row["solve"]["selected"]["holdout_nrmse"]<=1e-8 for row in rows)
        and all(row["transfer"] is not None and row["transfer"]["status"]=="TRANSFER_OK" and row["transfer"]["holdout_nrmse"]<=1e-8 for row in rows)
        and deep>=3
        and unique<raw
    )
    return {
        "schema":SCHEMA,
        "status":"PASS__TARGET_INDEPENDENT_SIGN_QUOTIENT_DEPTH8__ZERO_PERSISTENT_M_fit" if passed else "FAIL__SIGN_QUOTIENT_DEPTH8_RESIDUAL",
        "congruence_audit":audit,
        "basis":{
            "class_count_by_depth":basis["class_count_by_depth"],
            "global_unique_class_count":unique,
            "generated_quotient_edges":basis["generated_quotient_edges"],
            "raw_cumulative_sequence_count":raw,
            "reduction_factor_raw_over_unique":raw/unique if unique else None,
            "basis_generation_seconds":basis["basis_generation_seconds"],
        },
        "task_count":len(rows),
        "tasks":rows,
        "first_exact_depth_ge_7_count":deep,
        "persistent_m_fit_bytes":0,
        "persistent_learned_macros":0,
        "persistent_quotient_basis":0,
        "writes_selected_structure":False,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "FINITE_UNARY_DEPTH8_SEARCH_IS_NOT_GENERAL_PROGRAM_SEARCH",
            "M_cap_AND_M_dev_ARE_NOT_ZERO_BY_THIS_RESULT",
            "SIGN_QUOTIENTING_DOES_NOT_MERGE_ARBITRARY_SCALE_OR_AFFINE_PREFIXES",
        ],
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
