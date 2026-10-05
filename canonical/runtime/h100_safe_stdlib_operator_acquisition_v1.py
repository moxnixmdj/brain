"""Descriptor-driven safe stdlib operator acquisition for H100.

Scope is intentionally narrow:
- module is fixed to Python stdlib math;
- only public identifiers are accepted;
- no eval/exec/subprocess/network/dynamic arbitrary module import;
- every acquired callable must pass repeated unary-float probes;
- descriptor + observed probe I/O is content-addressed;
- learned-provider calls are absent.

This is an operator-acquisition experiment, not a general external-tool sandbox.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import re
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_verified_capability_registry_v5 as registry
from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_SAFE_STDLIB_OPERATOR_ACQUISITION_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_SAFE_STDLIB_OPERATOR_ACQUISITION_RESULT_V1"
_PUBLIC=re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

class SafeOperatorAcquisitionError(ValueError):
    pass

def _solve3(a:list[list[float]],b:list[float])->list[float]|None:
    m=[list(map(float,a[i]))+[float(b[i])] for i in range(3)]
    for c in range(3):
        p=max(range(c,3),key=lambda r:abs(m[r][c]))
        if abs(m[p][c])<=1e-12:
            return None
        m[c],m[p]=m[p],m[c]
        div=m[c][c]
        m[c]=[v/div for v in m[c]]
        for r in range(3):
            if r==c:
                continue
            f=m[r][c]
            if abs(f)<=1e-18:
                continue
            m[r]=[x-f*y for x,y in zip(m[r],m[c])]
    out=[m[i][-1] for i in range(3)]
    return out if all(math.isfinite(x) for x in out) else None

def _fit(rows:Sequence[Mapping[str,Any]],fn,gamma:float)->dict[str,Any]|None:
    xs=[float(r["x"]) for r in rows]
    ys=[float(r["y"]) for r in rows]
    try:
        z=[float(fn(float(gamma)*x)) for x in xs]
    except Exception:
        return None
    if not all(math.isfinite(v) for v in z):
        return None
    cols=[[1.0]*len(xs),xs,z]
    xtx=[[sum(cols[i][k]*cols[j][k] for k in range(len(xs))) for j in range(3)] for i in range(3)]
    xty=[sum(cols[i][k]*ys[k] for k in range(len(xs))) for i in range(3)]
    for i in range(3):
        xtx[i][i]+=1e-13
    coeff=_solve3(xtx,xty)
    if coeff is None:
        return None
    pred=[coeff[0]+coeff[1]*x+coeff[2]*fn(float(gamma)*x) for x in xs]
    return {"gamma":float(gamma),"coefficients":coeff,"train_nrmse":expr._nrmse(ys,pred)}

def _score(candidate:Mapping[str,Any],rows:Sequence[Mapping[str,Any]],fn)->float:
    pred=[
        float(candidate["coefficients"][0])
        +float(candidate["coefficients"][1])*float(r["x"])
        +float(candidate["coefficients"][2])*float(fn(float(candidate["gamma"])*float(r["x"])))
        for r in rows
    ]
    return expr._nrmse([float(r["y"]) for r in rows],pred)

def acquire_operator(desc:Mapping[str,Any],policy:Mapping[str,Any]):
    if str(policy.get("allowed_module"))!="math":
        raise SafeOperatorAcquisitionError("POLICY_MODULE_INVALID")
    attr=str(desc.get("attribute") or "")
    if not _PUBLIC.fullmatch(attr) or attr.startswith("_") or "__" in attr:
        raise SafeOperatorAcquisitionError("ATTRIBUTE_NOT_PUBLIC_IDENTIFIER")
    fn=getattr(math,attr,None)
    if not callable(fn):
        raise SafeOperatorAcquisitionError("ATTRIBUTE_NOT_CALLABLE")
    probes=[float(x) for x in desc.get("probes",[])]
    if not probes:
        raise SafeOperatorAcquisitionError("PROBES_REQUIRED")
    try:
        a=[float(fn(x)) for x in probes]
        b=[float(fn(x)) for x in probes]
    except Exception as exc:
        raise SafeOperatorAcquisitionError("UNARY_FLOAT_PROBE_FAILED") from exc
    if [x.hex() for x in a] != [x.hex() for x in b]:
        raise SafeOperatorAcquisitionError("NONDETERMINISTIC_PROBES")
    if not all(math.isfinite(x) for x in a):
        raise SafeOperatorAcquisitionError("NONFINITE_PROBE_OUTPUT")
    invariants=set(str(x) for x in desc.get("invariants",[]))
    table=dict(zip(probes,a))
    if "ZERO_ABS_ERROR_LE_1E-15" in invariants and abs(float(fn(0.0)))>1e-15:
        raise SafeOperatorAcquisitionError("ZERO_INVARIANT_FAIL")
    if "ODD_ABS_ERROR_LE_1E-15" in invariants:
        for x in probes:
            if -x in table and abs(table[x]+table[-x])>1e-15:
                raise SafeOperatorAcquisitionError("ODD_INVARIANT_FAIL")
    payload={
        "source_class":"PYTHON_STDLIB_MATH_UNARY_FLOAT",
        "module":"math",
        "attribute":attr,
        "python":platform.python_version(),
        "probe_input_hex":[x.hex() for x in probes],
        "probe_output_hex":[x.hex() for x in a],
        "invariants":sorted(invariants),
    }
    fingerprint=hashlib.sha256(
        json.dumps(payload,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()
    return fn,{"fingerprint_sha256":fingerprint,"probe_payload":payload}

def _truth(operator_id:str,which:str,x:float)->float:
    if operator_id=="ATAN_V1":
        if which=="SEED": return 0.3+0.2*x+0.9*math.atan(0.7*x)
        if which=="TRANSFER": return -0.1+0.4*x-0.5*math.atan(1.4*x)
    if operator_id=="TANH_V1":
        if which=="SEED": return 0.5-0.1*x+1.1*math.tanh(0.9*x)
        if which=="TRANSFER": return -0.2+0.3*x+0.8*math.tanh(1.7*x)
    raise SafeOperatorAcquisitionError("TASK_UNKNOWN")

def _rows(operator_id:str,which:str,xs:Sequence[float])->list[dict[str,float]]:
    return [{"x":float(x),"y":_truth(operator_id,which,float(x))} for x in xs]

def _best_fit(train,hold,fn,gammas,use_holdout:bool):
    candidates=[]
    for g in gammas:
        c=_fit(train,fn,float(g))
        if c is None:
            continue
        c["holdout_nrmse"]=_score(c,hold,fn)
        candidates.append(c)
    if not candidates:
        return None
    if use_holdout:
        candidates.sort(key=lambda c:(max(c["train_nrmse"],c["holdout_nrmse"]),c["gamma"]))
    else:
        candidates.sort(key=lambda c:(c["train_nrmse"],c["gamma"]))
    return candidates[0]

def _baseline_expression(seed,config):
    out=expr.discover(
        seed,target="y",inputs=["x"],
        max_depth=int(config["max_depth"]),
        beam_width=int(config["beam_width"]),
        pair_feature_pool=int(config["pair_feature_pool"]),
        exact_nrmse=float(config["exact_nrmse"]),
    )
    return {
        "status":out.get("status"),
        "best_nrmse":None if not out.get("best_candidate") else out["best_candidate"].get("nrmse"),
        "best_validation_nrmse":None if not out.get("best_candidate") else out["best_candidate"].get("validation_nrmse"),
    }

def run()->dict[str,Any]:
    pre=json.loads(PRE.read_text())
    policy=pre["acquisition_policy"]
    tx=[float(x) for x in pre["x_population"]["training_x"]]
    hx=[float(x) for x in pre["x_population"]["holdout_x"]]
    results=[]
    all_pass=True
    for desc in pre["operators"]:
        oid=str(desc["operator_id"])
        seed=_rows(oid,"SEED",tx); seed_hold=_rows(oid,"SEED",hx)
        transfer=_rows(oid,"TRANSFER",tx); transfer_hold=_rows(oid,"TRANSFER",hx)
        seed_miss=registry.resolve_verified_capability(seed,target="y",input_name="x").get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED"
        transfer_miss=registry.resolve_verified_capability(transfer,target="y",input_name="x").get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED"
        est=time.perf_counter()
        baseline=_baseline_expression(seed,pre["baseline_expression_config"])
        baseline["seconds"]=time.perf_counter()-est
        expression_miss=baseline["status"]!="EXACT_CANDIDATE_FOUND"
        fn,verification=acquire_operator(desc,policy)
        gammas=[float(x) for x in desc["gamma_grid"]]
        sst=time.perf_counter()
        seed_best=_best_fit(seed,seed_hold,fn,gammas,True)
        seed_seconds=time.perf_counter()-sst
        tst=time.perf_counter()
        transfer_best=_best_fit(transfer,transfer_hold,fn,gammas,False)
        transfer_seconds=time.perf_counter()-tst
        seed_pass=bool(seed_best and seed_best["train_nrmse"]<=1e-10 and seed_best["holdout_nrmse"]<=1e-8)
        transfer_pass=bool(transfer_best and transfer_best["holdout_nrmse"]<=1e-8)
        passed=seed_miss and transfer_miss and expression_miss and seed_pass and transfer_pass
        all_pass=all_pass and passed
        results.append({
            "operator_id":oid,"attribute":desc["attribute"],
            "baseline_seed_registry_v5_miss":seed_miss,
            "baseline_transfer_registry_v5_miss":transfer_miss,
            "baseline_expression":baseline,
            "verification":verification,
            "seed_best":seed_best,"seed_seconds":seed_seconds,
            "transfer_best":transfer_best,"transfer_seconds":transfer_seconds,
            "pass":passed,
        })
    return {
        "schema":SCHEMA,
        "status":"PASS__GENERIC_SAFE_STDLIB_OPERATOR_ACQUISITION_TWO_OF_TWO__ZERO_CREDIT" if all_pass else "FAIL__SAFE_OPERATOR_ACQUISITION_RESIDUAL",
        "operators":results,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "arbitrary_module_imports":0,
        "arbitrary_code_execution":0,
        "hard_nonclaims":[
            "STDLIB_MATH_ONLY_DOES_NOT_PROVE_ARBITRARY_EXTERNAL_TOOL_ACQUISITION",
            "NO_H100_TERMINAL_CREDIT"
        ],
        "h100_terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
