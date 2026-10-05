"""Two-binary-node transient composition with zero persistent M_fit."""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr
from canonical.runtime import h100_sign_quotient_depth8_v1 as q8
from canonical.runtime import h100_binary_composition_transient_v1 as bin1

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_NESTED_BINARY_TRANSIENT_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_NESTED_BINARY_TRANSIENT_RESULT_V1"

class NestedBinaryError(ValueError):
    pass

def _unary_basis2():
    base=json.loads(q8.PRE.read_text())
    pre=dict(base)
    pre["max_depth"]=2
    basis=q8.build_transient_basis(pre)
    reps=[]
    for d in (1,2):
        reps.extend(basis["by_depth"][str(d)])
    reps.sort(key=lambda r:(r["depth"],r["signature"]))
    return pre,basis,reps

def _inner_signature(op:str,left:Mapping[str,Any],right:Mapping[str,Any])->str:
    a=str(left["signature"]); b=str(right["signature"])
    if op in {"add","mul","sub"} and b<a:
        a,b=b,a
    return f"{op}({a},{b})"

def build_inner_classes(reps:Sequence[Mapping[str,Any]])->dict[str,Any]:
    start=time.perf_counter()
    classes={}
    proposed=0

    def add(op,left,right):
        nonlocal proposed
        proposed+=1
        vals=bin1._binary_vector(op,left["values"],right["values"])
        key=q8._sign_key(vals)
        rec={
            "op":op,
            "left_sequence":list(left["sequence"]),
            "right_sequence":list(right["sequence"]),
            "values":vals,
            "complexity":int(left["depth"])+int(right["depth"])+1,
            "signature":_inner_signature(op,left,right),
        }
        old=classes.get(key)
        if old is None or (rec["complexity"],rec["signature"]) < (old["complexity"],old["signature"]):
            classes[key]=rec

    n=len(reps)
    for i,left in enumerate(reps):
        for j in range(i,n):
            right=reps[j]
            add("add",left,right)
            add("sub",left,right)
            add("mul",left,right)
    for left in reps:
        for right in reps:
            add("stable_div",left,right)

    out=sorted(classes.values(),key=lambda r:(r["complexity"],r["signature"]))
    return {
        "classes":out,
        "raw_proposal_count":proposed,
        "sign_class_count":len(out),
        "build_seconds":time.perf_counter()-start,
    }

def _outer_signature(op:str,inner:Mapping[str,Any],third:Mapping[str,Any],reverse:bool)->str:
    a=str(inner["signature"]); b=str(third["signature"])
    if op in {"add","mul","sub"}:
        if b<a:
            a,b=b,a
        return f"{op}({a},{b})"
    return f"stable_div({b},{a})" if reverse else f"stable_div({a},{b})"

def build_terminal_index(pre2:Mapping[str,Any],inners:Sequence[Mapping[str,Any]],unary:Sequence[Mapping[str,Any]])->dict[str,Any]:
    train_x=[float(x) for x in pre2["train_x"]]
    ntrain=len(train_x)
    start=time.perf_counter()
    index={}
    proposed=0

    def add(op,inner,third,reverse=False):
        nonlocal proposed
        proposed+=1
        if reverse:
            vals=bin1._binary_vector("stable_div",third["values"],inner["values"])
        else:
            vals=bin1._binary_vector(op,inner["values"],third["values"])
        key=bin1._fast_residual_key(vals[:ntrain],train_x)
        if key==("AFFINE",):
            return
        rec={
            "outer_op":op,
            "outer_reverse":bool(reverse),
            "inner_op":inner["op"],
            "inner_left_sequence":list(inner["left_sequence"]),
            "inner_right_sequence":list(inner["right_sequence"]),
            "third_sequence":list(third["sequence"]),
            "complexity":int(inner["complexity"])+int(third["depth"])+1,
            "signature":_outer_signature(op,inner,third,reverse),
        }
        index.setdefault(key,[]).append(rec)

    for inner in inners:
        for third in unary:
            add("add",inner,third)
            add("sub",inner,third)
            add("mul",inner,third)
            add("stable_div",inner,third,False)
            add("stable_div",inner,third,True)

    for bucket in index.values():
        bucket.sort(key=lambda r:(r["complexity"],r["signature"]))
    return {
        "index":index,
        "raw_proposal_count":proposed,
        "terminal_residual_key_count":len(index),
        "build_seconds":time.perf_counter()-start,
        "uses_target_y":False,
    }

def _eval_unary(seq:Sequence[str],xs:Sequence[float])->list[float]:
    return bin1._eval_unary(seq,xs)

def _eval_inner(op:str,left_seq:Sequence[str],right_seq:Sequence[str],xs:Sequence[float])->list[float]:
    left=_eval_unary(left_seq,xs)
    right=_eval_unary(right_seq,xs)
    return [bin1._binary_scalar(op,a,b) for a,b in zip(left,right)]

def _eval_spec(spec:Mapping[str,Any],xs:Sequence[float])->list[float]:
    inner=_eval_inner(spec["inner_op"],spec["inner_left_sequence"],spec["inner_right_sequence"],xs)
    third=_eval_unary(spec["third_sequence"],xs)
    if bool(spec["outer_reverse"]):
        return [bin1._binary_scalar("stable_div",t,i) for i,t in zip(inner,third)]
    return [bin1._binary_scalar(spec["outer_op"],i,t) for i,t in zip(inner,third)]

def _truth_feature(task:Mapping[str,Any],xs:Sequence[float])->list[float]:
    inner=_eval_inner(task["inner_op"],task["left"],task["right"],xs)
    third=_eval_unary(task["third"],xs)
    if task["outer_op"]=="stable_div_reverse":
        return [bin1._binary_scalar("stable_div",t,i) for i,t in zip(inner,third)]
    return [bin1._binary_scalar(task["outer_op"],i,t) for i,t in zip(inner,third)]

def _truth_y(task:Mapping[str,Any],phase:str,xs:Sequence[float])->list[float]:
    f=_truth_feature(task,xs)
    c=[float(x) for x in task[phase]]
    return [c[0]+c[1]*float(x)+c[2]*z for x,z in zip(xs,f)]

def solve_task(task:Mapping[str,Any],pre2:Mapping[str,Any],idx:Mapping[str,Any])->dict[str,Any]:
    train_x=[float(x) for x in pre2["train_x"]]
    hold_x=[float(x) for x in pre2["holdout_x"]]
    train_y=_truth_y(task,"seed",train_x)
    hold_y=_truth_y(task,"seed",hold_x)
    t0=time.perf_counter()
    key=bin1._fast_residual_key(train_y,train_x)
    bucket=list(idx["index"].get(key,[]))
    lookup=time.perf_counter()-t0

    all_x=train_x+hold_x
    t1=time.perf_counter()
    verified=[]
    for spec in bucket:
        vals=_eval_spec(spec,all_x)
        fit=bin1._fit_feature(
            train_x,hold_x,train_y,hold_y,
            vals[:len(train_x)],vals[len(train_x):]
        )
        if fit is None or fit["holdout_nrmse"] is None:
            continue
        if fit["train_nrmse"]<=1e-10 and fit["holdout_nrmse"]<=1e-8:
            verified.append({**spec,**fit})
    verified.sort(key=lambda r:(r["complexity"],r["signature"]))
    return {
        "hash_bucket_size":len(bucket),
        "verified_bucket_matches":len(verified),
        "selected":verified[0] if verified else None,
        "lookup_seconds":lookup,
        "lookup_plus_verification_seconds":lookup+(time.perf_counter()-t1),
    }

def transfer_task(task:Mapping[str,Any],pre2:Mapping[str,Any],selected:Mapping[str,Any])->dict[str,Any]:
    train_x=[float(x) for x in pre2["train_x"]]
    hold_x=[float(x) for x in pre2["holdout_x"]]
    train_y=_truth_y(task,"transfer",train_x)
    hold_y=_truth_y(task,"transfer",hold_x)
    all_x=train_x+hold_x
    vals=_eval_spec(selected,all_x)
    fit=bin1._fit_feature(
        train_x,hold_x,train_y,hold_y,
        vals[:len(train_x)],vals[len(train_x):]
    )
    if fit is None or fit["holdout_nrmse"] is None:
        return {"status":"TRANSFER_FAILED"}
    return {"status":"TRANSFER_OK",**fit}

def run()->dict[str,Any]:
    pre=json.loads(PRE.read_text())
    if "FROZEN_BEFORE_FRESH_NESTED_BINARY_OUTCOMES" not in str(pre.get("status","")):
        raise NestedBinaryError("PRECOMMIT_NOT_FROZEN")
    pre2,basis,unary=_unary_basis2()
    inner=build_inner_classes(unary)
    idx=build_terminal_index(pre2,inner["classes"],unary)
    rows=[]
    for task in pre["fresh_tasks"]:
        solved=solve_task(task,pre2,idx)
        trans=None if solved["selected"] is None else transfer_task(task,pre2,solved["selected"])
        rows.append({"task_id":task["id"],"solve":solved,"transfer":trans})
    med=median(r["solve"]["lookup_plus_verification_seconds"] for r in rows)
    passed=(
        idx["uses_target_y"] is False
        and all(r["solve"]["hash_bucket_size"]>0 for r in rows)
        and all(r["solve"]["selected"] is not None and r["solve"]["selected"]["holdout_nrmse"]<=1e-8 for r in rows)
        and all(r["transfer"] is not None and r["transfer"]["status"]=="TRANSFER_OK" and r["transfer"]["holdout_nrmse"]<=1e-8 for r in rows)
    )
    return {
        "schema":SCHEMA,
        "status":"PASS__NESTED_BINARY_TRANSIENT__ZERO_PERSISTENT_M_fit" if passed else "FAIL__NESTED_BINARY_RESIDUAL",
        "unary":{
            "class_count":len(unary),
            "basis_generation_seconds":basis["basis_generation_seconds"],
        },
        "inner":{
            "raw_proposal_count":inner["raw_proposal_count"],
            "sign_class_count":inner["sign_class_count"],
            "build_seconds":inner["build_seconds"],
        },
        "terminal":{
            "raw_proposal_count":idx["raw_proposal_count"],
            "residual_key_count":idx["terminal_residual_key_count"],
            "build_seconds":idx["build_seconds"],
            "uses_target_y":idx["uses_target_y"],
        },
        "tasks":rows,
        "median_lookup_plus_verification_seconds":med,
        "persistent_m_fit_bytes":0,
        "persistent_inner_binary_classes":0,
        "persistent_terminal_index":0,
        "persistent_selected_structure":0,
        "writes_discovery":False,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "THIS_IS_TWO_BINARY_NODES_NOT_ARBITRARY_RECURSIVE_TREE_DEPTH",
            "EXACT_HASHING_DOES_NOT_SOLVE_NOISY_TARGETS",
            "M_cap_AND_M_dev_ARE_SEPARATE_FROM_M_fit",
        ],
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
