"""Transient binary composition over a target-independent unary quotient basis.

This experiment composes two transient unary features with add/sub/mul or
stable_div, builds a terminal residual-direction index without target values,
then uses target residuals only for lookup + verification.

No discovered binary structure, index, fitted coefficient, or learned macro is
persisted.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr
from canonical.runtime import h100_sign_quotient_depth8_v1 as q8

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_BINARY_COMPOSITION_TRANSIENT_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_BINARY_COMPOSITION_TRANSIENT_RESULT_V1"

class BinaryTransientError(ValueError):
    pass

def _binary_scalar(op:str,a:float,b:float)->float:
    y=expr._apply_binary(str(op),float(a),float(b))
    if y is None or not math.isfinite(float(y)):
        raise BinaryTransientError("BINARY_NONFINITE:"+str(op))
    return float(y)

def _binary_vector(op:str,a:Sequence[float],b:Sequence[float])->tuple[float,...]:
    return tuple(_binary_scalar(op,x,y) for x,y in zip(a,b))

def _fast_residual_key(values:Sequence[float], xs:Sequence[float])->tuple[float,...]|tuple[str]:
    vals=[float(v) for v in values]
    xx=[float(x) for x in xs]
    n=len(xx)
    if n!=len(vals) or n<2:
        raise BinaryTransientError("RESIDUAL_LENGTH_INVALID")
    mx=sum(xx)/n
    my=sum(vals)/n
    denom=sum((x-mx)*(x-mx) for x in xx)
    if denom<=0:
        raise BinaryTransientError("X_VARIANCE_ZERO")
    beta=sum((x-mx)*(y-my) for x,y in zip(xx,vals))/denom
    alpha=my-beta*mx
    r=[y-(alpha+beta*x) for x,y in zip(xx,vals)]
    scale=max((abs(v) for v in r),default=0.0)
    if scale<=1e-14:
        return ("AFFINE",)
    z=[v/scale for v in r]
    sign=1.0
    for v in z:
        if abs(v)>1e-14:
            if v<0:
                sign=-1.0
            break
    return tuple(round(sign*v,10) for v in z)

def _seq_signature(seq:Sequence[str])->str:
    tree:dict[str,Any]={"op":"var","name":"x"}
    for op in seq:
        tree={"op":str(op),"arg":tree}
    return expr._structural_signature(tree,("x",))

def _binary_signature(op:str,left:Sequence[str],right:Sequence[str])->str:
    a=_seq_signature(left)
    b=_seq_signature(right)
    if op in {"add","mul"} and b<a:
        a,b=b,a
    if op=="sub" and b<a:
        # sub(b,a)=-(sub(a,b)); terminal coefficient absorbs global sign.
        a,b=b,a
    return f"{op}({a},{b})"

def orientation_audit()->dict[str,Any]:
    a=[-2.7,-0.8,0.2,1.6,3.1]
    b=[1.2,-1.4,0.7,2.3,-0.5]
    canon={}
    for op in ("add","sub","mul","stable_div"):
        if op=="add":
            candidates=[_binary_vector("add",a,b),_binary_vector("sub",a,b)]
        elif op=="sub":
            candidates=[_binary_vector("sub",a,b),_binary_vector("add",a,b)]
        else:
            candidates=[_binary_vector(op,a,b)]
        canon[op]={q8._sign_key(v) for v in candidates}
    rows={}
    for op in ("add","sub","mul","stable_div"):
        ok=True
        for s1 in (-1.0,1.0):
            for s2 in (-1.0,1.0):
                left=[s1*x for x in a]
                right=[s2*x for x in b]
                out=_binary_vector(op,left,right)
                if q8._sign_key(out) not in canon[op]:
                    ok=False
        rows[op]={"pass":ok}
    return {"all_pass":all(r["pass"] for r in rows.values()),"operators":rows}

def _unary_basis4()->tuple[dict[str,Any],dict[str,Any]]:
    base=json.loads(q8.PRE.read_text())
    pre=dict(base)
    pre["max_depth"]=4
    basis=q8.build_transient_basis(pre)
    return pre,basis

def build_binary_index(pre4:Mapping[str,Any],basis:Mapping[str,Any])->dict[str,Any]:
    train_x=[float(x) for x in pre4["train_x"]]
    ntrain=len(train_x)
    reps=[]
    for d in range(1,5):
        reps.extend(basis["by_depth"][str(d)])
    reps.sort(key=lambda r:(r["depth"],r["signature"]))
    n=len(reps)

    start=time.perf_counter()
    index={}
    proposed=0

    def add_record(op:str,left:Mapping[str,Any],right:Mapping[str,Any]):
        nonlocal proposed
        proposed+=1
        try:
            vals=_binary_vector(op,left["values"],right["values"])
        except BinaryTransientError:
            return
        key=_fast_residual_key(vals[:ntrain],train_x)
        if key==("AFFINE",):
            return
        rec={
            "op":op,
            "left_sequence":list(left["sequence"]),
            "right_sequence":list(right["sequence"]),
            "complexity":int(left["depth"])+int(right["depth"])+1,
            "signature":_binary_signature(op,left["sequence"],right["sequence"]),
        }
        index.setdefault(key,[]).append(rec)

    for i,left in enumerate(reps):
        for j in range(i,n):
            right=reps[j]
            add_record("add",left,right)
            add_record("sub",left,right)
            add_record("mul",left,right)
    for left in reps:
        for right in reps:
            add_record("stable_div",left,right)

    for bucket in index.values():
        bucket.sort(key=lambda r:(r["complexity"],r["signature"]))
    elapsed=time.perf_counter()-start
    return {
        "index":index,
        "unary_class_count":n,
        "raw_binary_proposal_count":proposed,
        "terminal_residual_key_count":len(index),
        "build_seconds":elapsed,
        "uses_target_y":False,
    }

def _eval_unary(sequence:Sequence[str],xs:Sequence[float])->list[float]:
    out=[]
    for x in xs:
        v=float(x)
        for op in sequence:
            v=q8._apply_scalar(str(op),v)
        out.append(v)
    return out

def _eval_spec(spec:Mapping[str,Any],xs:Sequence[float])->list[float]:
    left=_eval_unary(spec["left_sequence"],xs)
    right=_eval_unary(spec["right_sequence"],xs)
    return [_binary_scalar(str(spec["op"]),a,b) for a,b in zip(left,right)]

def _truth_feature(task:Mapping[str,Any],xs:Sequence[float])->list[float]:
    left=_eval_unary(task["left"],xs)
    right=_eval_unary(task["right"],xs)
    return [_binary_scalar(str(task["op"]),a,b) for a,b in zip(left,right)]

def _truth_y(task:Mapping[str,Any],phase:str,xs:Sequence[float])->list[float]:
    f=_truth_feature(task,xs)
    c=[float(x) for x in task[phase]]
    return [c[0]+c[1]*float(x)+c[2]*z for x,z in zip(xs,f)]

def _fit_feature(
    train_x:Sequence[float],hold_x:Sequence[float],
    train_y:Sequence[float],hold_y:Sequence[float],
    feature_train:Sequence[float],feature_hold:Sequence[float]
)->dict[str,Any]|None:
    coeff=expr._fit_linear_features([list(train_x),list(feature_train)],list(train_y))
    if coeff is None:
        return None
    ptrain=[coeff[0]+coeff[1]*x+coeff[2]*f for x,f in zip(train_x,feature_train)]
    train_err=float(expr._nrmse(list(train_y),ptrain))
    if train_err>1e-10:
        return {"coefficients":[float(x) for x in coeff],"train_nrmse":train_err,"holdout_nrmse":None}
    phold=[coeff[0]+coeff[1]*x+coeff[2]*f for x,f in zip(hold_x,feature_hold)]
    return {
        "coefficients":[float(x) for x in coeff],
        "train_nrmse":train_err,
        "holdout_nrmse":float(expr._nrmse(list(hold_y),phold)),
    }

def solve_task(task:Mapping[str,Any],pre4:Mapping[str,Any],idx:Mapping[str,Any])->dict[str,Any]:
    train_x=[float(x) for x in pre4["train_x"]]
    hold_x=[float(x) for x in pre4["holdout_x"]]
    train_y=_truth_y(task,"seed",train_x)
    hold_y=_truth_y(task,"seed",hold_x)

    t0=time.perf_counter()
    key=_fast_residual_key(train_y,train_x)
    bucket=list(idx["index"].get(key,[]))
    lookup=time.perf_counter()-t0

    t1=time.perf_counter()
    verified=[]
    all_x=train_x+hold_x
    for spec in bucket:
        vals=_eval_spec(spec,all_x)
        fit=_fit_feature(
            train_x,hold_x,train_y,hold_y,
            vals[:len(train_x)],vals[len(train_x):]
        )
        if fit is None or fit["holdout_nrmse"] is None:
            continue
        if fit["train_nrmse"]<=1e-10 and fit["holdout_nrmse"]<=1e-8:
            verified.append({**spec,**fit})
    verified.sort(key=lambda r:(r["complexity"],r["signature"]))
    selected=verified[0] if verified else None
    total=lookup+(time.perf_counter()-t1)
    return {
        "hash_bucket_size":len(bucket),
        "verified_bucket_matches":len(verified),
        "selected":selected,
        "lookup_seconds":lookup,
        "lookup_plus_verification_seconds":total,
    }

def transfer_task(task:Mapping[str,Any],pre4:Mapping[str,Any],selected:Mapping[str,Any])->dict[str,Any]:
    train_x=[float(x) for x in pre4["train_x"]]
    hold_x=[float(x) for x in pre4["holdout_x"]]
    train_y=_truth_y(task,"transfer",train_x)
    hold_y=_truth_y(task,"transfer",hold_x)
    all_x=train_x+hold_x
    vals=_eval_spec(selected,all_x)
    fit=_fit_feature(train_x,hold_x,train_y,hold_y,vals[:len(train_x)],vals[len(train_x):])
    if fit is None or fit["holdout_nrmse"] is None:
        return {"status":"TRANSFER_FAILED"}
    return {"status":"TRANSFER_OK",**fit}

def run()->dict[str,Any]:
    pre=json.loads(PRE.read_text())
    if "FROZEN_BEFORE_FRESH_BINARY_TASK_OUTCOMES" not in str(pre.get("status","")):
        raise BinaryTransientError("PRECOMMIT_NOT_FROZEN")
    audit=orientation_audit()
    pre4,basis=_unary_basis4()
    idx=build_binary_index(pre4,basis)
    rows=[]
    for task in pre["fresh_tasks"]:
        solved=solve_task(task,pre4,idx)
        trans=None if solved["selected"] is None else transfer_task(task,pre4,solved["selected"])
        rows.append({"task_id":task["id"],"truth_op":task["op"],"solve":solved,"transfer":trans})
    med=median(r["solve"]["lookup_plus_verification_seconds"] for r in rows)
    passed=(
        audit["all_pass"]
        and idx["uses_target_y"] is False
        and all(r["solve"]["hash_bucket_size"]>0 for r in rows)
        and all(r["solve"]["selected"] is not None and r["solve"]["selected"]["holdout_nrmse"]<=1e-8 for r in rows)
        and all(r["transfer"] is not None and r["transfer"]["status"]=="TRANSFER_OK" and r["transfer"]["holdout_nrmse"]<=1e-8 for r in rows)
    )
    return {
        "schema":SCHEMA,
        "status":"PASS__TRANSIENT_BINARY_COMPOSITION__ZERO_PERSISTENT_M_fit" if passed else "FAIL__BINARY_COMPOSITION_RESIDUAL",
        "orientation_audit":audit,
        "unary_basis_generation_seconds":basis["basis_generation_seconds"],
        "index":{
            "unary_class_count":idx["unary_class_count"],
            "raw_binary_proposal_count":idx["raw_binary_proposal_count"],
            "terminal_residual_key_count":idx["terminal_residual_key_count"],
            "build_seconds":idx["build_seconds"],
            "uses_target_y":idx["uses_target_y"],
        },
        "tasks":rows,
        "median_lookup_plus_verification_seconds":med,
        "persistent_m_fit_bytes":0,
        "persistent_binary_index":0,
        "persistent_selected_binary_structures":0,
        "writes_binary_index_or_selection":False,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "THIS_IS_BINARY_COMPOSITION_OF_TWO_UNARY_FEATURES_NOT_ARBITRARY_RECURSIVE_BINARY_TREES",
            "EXACT_HASHING_DOES_NOT_SOLVE_NOISY_TARGETS",
            "M_cap_AND_M_dev_ARE_SEPARATE_FROM_M_fit",
        ],
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
