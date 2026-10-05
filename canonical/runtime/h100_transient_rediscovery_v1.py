"""Transient rediscovery experiment for representation-correct H100 accounting.

Search-selected structures and fitted coefficients live only in process memory.
Nothing discovered by the search is written into a persistent capability
registry. This tests the compute-for-persistent-fit-state trade.
"""
from __future__ import annotations

import itertools
import json
import math
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_TRANSIENT_REDISCOVERY_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_TRANSIENT_REDISCOVERY_RESULT_V1"

class TransientRediscoveryError(ValueError):
    pass

def _apply(x:float, sequence:Sequence[str])->float:
    v=float(x)
    for op in sequence:
        nxt=expr._apply_unary(str(op),v)
        if nxt is None or not math.isfinite(float(nxt)):
            raise TransientRediscoveryError("CHAIN_NONFINITE:"+str(op))
        v=float(nxt)
    return v

def _signature(sequence:Sequence[str])->str:
    tree:dict[str,Any]={"op":"var","name":"x"}
    for op in sequence:
        tree={"op":str(op),"arg":tree}
    return expr._structural_signature(tree,("x",))

def _rows(task:Mapping[str,Any], phase:str, xs:Sequence[float])->list[dict[str,float]]:
    coeff=[float(x) for x in task[phase]]
    seq=[str(x) for x in task["sequence"]]
    out=[]
    for raw in xs:
        x=float(raw)
        f=_apply(x,seq)
        y=coeff[0]+coeff[1]*x+coeff[2]*f
        out.append({"x":x,"y":float(y)})
    return out

def _fit(train:Sequence[Mapping[str,float]], hold:Sequence[Mapping[str,float]], sequence:Sequence[str])->dict[str,Any]|None:
    try:
        tx=[float(r["x"]) for r in train]
        ty=[float(r["y"]) for r in train]
        hx=[float(r["x"]) for r in hold]
        hy=[float(r["y"]) for r in hold]
        tf=[_apply(x,sequence) for x in tx]
        hf=[_apply(x,sequence) for x in hx]
    except Exception:
        return None
    coeff=expr._fit_linear_features([tx,tf],ty)
    if coeff is None:
        return None
    ptrain=[coeff[0]+coeff[1]*x+coeff[2]*f for x,f in zip(tx,tf)]
    phold=[coeff[0]+coeff[1]*x+coeff[2]*f for x,f in zip(hx,hf)]
    return {
        "sequence":[str(x) for x in sequence],
        "signature":_signature(sequence),
        "depth":len(sequence),
        "coefficients":[float(x) for x in coeff],
        "train_nrmse":float(expr._nrmse(ty,ptrain)),
        "holdout_nrmse":float(expr._nrmse(hy,phold)),
    }

def rediscover(task:Mapping[str,Any], pre:Mapping[str,Any])->dict[str,Any]:
    ops=[str(x) for x in pre["operator_order"]]
    train=_rows(task,"seed",[float(x) for x in pre["train_x"]])
    hold=_rows(task,"seed",[float(x) for x in pre["holdout_x"]])
    counts={}
    exact={}
    start=time.perf_counter()
    for depth in range(1,int(pre["max_depth"])+1):
        rows=[]
        count=0
        for seq in itertools.product(ops,repeat=depth):
            count+=1
            fit=_fit(train,hold,seq)
            if fit is not None and fit["train_nrmse"]<=1e-10 and fit["holdout_nrmse"]<=1e-8:
                rows.append(fit)
        rows.sort(key=lambda r:r["signature"])
        counts[str(depth)]=count
        exact[str(depth)]=rows
    elapsed=time.perf_counter()-start
    first=next((d for d in range(1,int(pre["max_depth"])+1) if exact[str(d)]),None)
    selected=None if first is None else exact[str(first)][0]
    return {
        "counts_by_depth":counts,
        "cumulative_count":sum(counts.values()),
        "first_exact_depth":first,
        "exact_count_by_depth":{k:len(v) for k,v in exact.items()},
        "selected":selected,
        "wall_clock_seconds":elapsed,
    }

def transfer(task:Mapping[str,Any], selected:Mapping[str,Any], pre:Mapping[str,Any])->dict[str,Any]:
    train=_rows(task,"transfer",[float(x) for x in pre["train_x"]])
    hold=_rows(task,"transfer",[float(x) for x in pre["holdout_x"]])
    fit=_fit(train,hold,[str(x) for x in selected["sequence"]])
    if fit is None:
        return {"status":"TRANSFER_FIT_FAILED"}
    return {
        "status":"TRANSFER_OK",
        "train_nrmse":fit["train_nrmse"],
        "holdout_nrmse":fit["holdout_nrmse"],
        "sequence":fit["sequence"],
        "coefficients":fit["coefficients"],
    }

def run()->dict[str,Any]:
    pre=json.loads(PRE.read_text())
    if "FROZEN_BEFORE_REDISCOVERY_OUTCOMES" not in str(pre.get("status","")):
        raise TransientRediscoveryError("PRECOMMIT_NOT_FROZEN")
    rows=[]
    for task in pre["tasks"]:
        search=rediscover(task,pre)
        selected=search["selected"]
        trans=None if selected is None else transfer(task,selected,pre)
        rows.append({
            "task_id":task["id"],
            "truth_sequence":task["sequence"],
            "rediscovery":search,
            "transfer":trans,
        })
    passed=all(
        r["rediscovery"]["cumulative_count"]==1554
        and r["rediscovery"]["selected"] is not None
        and r["rediscovery"]["selected"]["holdout_nrmse"]<=1e-8
        and r["transfer"] is not None
        and r["transfer"]["status"]=="TRANSFER_OK"
        and r["transfer"]["holdout_nrmse"]<=1e-8
        for r in rows
    )
    return {
        "schema":SCHEMA,
        "status":"PASS__FIVE_FRESH_STRUCTURES_TRANSIENTLY_REDISCOVERED__ZERO_PERSISTENT_M_fit" if passed else "FAIL__TRANSIENT_REDISCOVERY_RESIDUAL",
        "task_count":len(rows),
        "tasks":rows,
        "persistent_m_fit_bytes":0,
        "persistent_search_selected_structures":0,
        "persistent_fitted_coefficients":0,
        "writes_discovered_structure_to_registry":False,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "GENERIC_SEARCH_CODE_CONTRIBUTES_TO_M_cap",
            "EVIDENCE_RESPONSIVE_ENGINEERING_OF_SEARCH_CODE_MAY_CONTRIBUTE_TO_M_dev",
            "FINITE_DEPTH4_UNARY_SEARCH_IS_NOT_GENERAL_PROGRAM_SEARCH",
        ],
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
