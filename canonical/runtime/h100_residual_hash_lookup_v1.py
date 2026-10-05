"""Residual-direction hash lookup over a transient sign-quotient basis.

For y=a+b*x+c*f(x), residualizing both y and f against span{1,x} yields
R(y)=c*R(f). After sign/scale normalization, an exact target can therefore
retrieve terminal feature candidates by hash. The hash is proposal-only:
ordinary train/holdout verification remains mandatory.
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
PRE=ROOT/"canonical/governance/H100_RESIDUAL_HASH_LOOKUP_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_RESIDUAL_HASH_LOOKUP_RESULT_V1"

class ResidualHashError(ValueError):
    pass

def _residual(values:Sequence[float], xs:Sequence[float])->list[float]:
    vals=[float(v) for v in values]
    xx=[float(x) for x in xs]
    coeff=expr._fit_linear_features([xx],vals)
    if coeff is None or len(coeff)!=2:
        raise ResidualHashError("RESIDUAL_FIT_FAILED")
    return [v-(coeff[0]+coeff[1]*x) for v,x in zip(vals,xx)]

def residual_key(values:Sequence[float], xs:Sequence[float])->tuple[float,...]|tuple[str]:
    r=_residual(values,xs)
    scale=max((abs(v) for v in r),default=0.0)
    if not math.isfinite(scale):
        raise ResidualHashError("RESIDUAL_SCALE_NONFINITE")
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

def theorem_audit(feature:Sequence[float], xs:Sequence[float])->dict[str,Any]:
    y=[0.37-0.22*float(x)+1.19*float(f) for x,f in zip(xs,feature)]
    return {
        "feature_key_equals_target_key":residual_key(feature,xs)==residual_key(y,xs),
    }

def build_terminal_index(basis:Mapping[str,Any], train_x:Sequence[float])->dict[str,Any]:
    start=time.perf_counter()
    n=len(train_x)
    index={}
    feature_count=0
    for depth_text,recs in basis["by_depth"].items():
        depth=int(depth_text)
        for rec in recs:
            feature_count+=1
            vals=[float(v) for v in rec["values"][:n]]
            key=residual_key(vals,train_x)
            if key==("AFFINE",):
                continue
            row={
                "depth":depth,
                "sequence":list(rec["sequence"]),
                "signature":str(rec["signature"]),
                "values":rec["values"],
            }
            index.setdefault(key,[]).append(row)
    for bucket in index.values():
        bucket.sort(key=lambda r:(r["depth"],r["signature"]))
    elapsed=time.perf_counter()-start
    return {
        "index":index,
        "key_count":len(index),
        "feature_count":feature_count,
        "build_seconds":elapsed,
        "uses_target_y":False,
    }

def solve_task(task:Mapping[str,Any], pre_basis:Mapping[str,Any], idx:Mapping[str,Any])->dict[str,Any]:
    train_x=[float(x) for x in pre_basis["train_x"]]
    hold_x=[float(x) for x in pre_basis["holdout_x"]]
    train_y=q8._truth_values(task,"seed",train_x)
    hold_y=q8._truth_values(task,"seed",hold_x)

    t0=time.perf_counter()
    key=residual_key(train_y,train_x)
    bucket=list(idx["index"].get(key,[]))
    lookup_seconds=time.perf_counter()-t0

    t1=time.perf_counter()
    verified=[]
    for rec in bucket:
        fit=q8._fit_feature(train_x,hold_x,train_y,hold_y,rec["values"])
        if fit is None or fit["holdout_nrmse"] is None:
            continue
        if fit["train_nrmse"]<=1e-10 and fit["holdout_nrmse"]<=1e-8:
            verified.append({
                "sequence":list(rec["sequence"]),
                "signature":rec["signature"],
                "depth":rec["depth"],
                **fit,
            })
    verified.sort(key=lambda r:(r["depth"],r["signature"]))
    selected=verified[0] if verified else None
    total_seconds=time.perf_counter()-t1+lookup_seconds

    return {
        "hash_bucket_size":len(bucket),
        "verified_bucket_matches":len(verified),
        "selected":selected,
        "lookup_seconds":lookup_seconds,
        "lookup_plus_verification_seconds":total_seconds,
    }

def run()->dict[str,Any]:
    pre=json.loads(PRE.read_text())
    if "FROZEN_BEFORE_FRESH_HASH_LOOKUP_TASK_OUTCOMES" not in str(pre.get("status","")):
        raise ResidualHashError("PRECOMMIT_NOT_FROZEN")
    basis_pre=json.loads(q8.PRE.read_text())

    basis=q8.build_transient_basis(basis_pre)
    train_x=[float(x) for x in basis_pre["train_x"]]
    idx=build_terminal_index(basis,train_x)

    sample=next(iter(basis["by_depth"]["8"]),None)
    theorem={"feature_key_equals_target_key":False}
    if sample is not None:
        theorem=theorem_audit(sample["values"][:len(train_x)],train_x)

    rows=[]
    for task in pre["fresh_tasks"]:
        solved=solve_task(task,basis_pre,idx)
        trans=None if solved["selected"] is None else q8.transfer_task(task,basis_pre,solved["selected"])
        rows.append({
            "task_id":task["id"],
            "truth_sequence":task["sequence"],
            "solve":solved,
            "transfer":trans,
        })

    med=median([r["solve"]["lookup_plus_verification_seconds"] for r in rows])
    passed=(
        idx["uses_target_y"] is False
        and theorem["feature_key_equals_target_key"]
        and all(r["solve"]["hash_bucket_size"]>0 for r in rows)
        and all(r["solve"]["selected"] is not None and r["solve"]["selected"]["holdout_nrmse"]<=1e-8 for r in rows)
        and all(r["transfer"] is not None and r["transfer"]["status"]=="TRANSFER_OK" and r["transfer"]["holdout_nrmse"]<=1e-8 for r in rows)
        and med<0.05
    )

    total_basis_index=basis["basis_generation_seconds"]+idx["build_seconds"]
    amortized=(total_basis_index+sum(r["solve"]["lookup_plus_verification_seconds"] for r in rows))/len(rows)

    return {
        "schema":SCHEMA,
        "status":"PASS__RESIDUAL_HASH_LOOKUP__ZERO_PERSISTENT_M_fit" if passed else "FAIL__RESIDUAL_HASH_LOOKUP_RESIDUAL",
        "theorem_audit":theorem,
        "basis":{
            "global_unique_class_count":basis["global_unique_class_count"],
            "basis_generation_seconds":basis["basis_generation_seconds"],
        },
        "index":{
            "key_count":idx["key_count"],
            "feature_count":idx["feature_count"],
            "build_seconds":idx["build_seconds"],
            "uses_target_y":idx["uses_target_y"],
        },
        "tasks":rows,
        "median_lookup_plus_verification_seconds":med,
        "amortized_seconds_per_task_for_five_task_batch":amortized,
        "persistent_m_fit_bytes":0,
        "persistent_hash_index":0,
        "persistent_selected_structures":0,
        "writes_index_or_selection":False,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "EXACT_HASH_LOOKUP_DOES_NOT_SOLVE_NOISY_APPROXIMATE_TARGETS",
            "BASIS_GENERATION_COST_REMAINS_REAL",
            "FINITE_DEPTH8_UNARY_SEARCH_IS_NOT_GENERAL_PROGRAM_SEARCH",
            "M_cap_AND_M_dev_ARE_SEPARATE_FROM_M_fit",
        ],
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
