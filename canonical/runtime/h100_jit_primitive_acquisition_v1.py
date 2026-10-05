"""JIT deterministic primitive acquisition for H100 operator-set escape."""
from __future__ import annotations
import hashlib, importlib, json, math, platform, statistics, sys, time
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_verified_capability_registry_v4 as registry
from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_JIT_PRIMITIVE_ACQUISITION_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_JIT_PRIMITIVE_ACQUISITION_RESULT_V1"

class PrimitiveAcquisitionError(ValueError): pass

def _truth(which:str,x:float)->float:
    if which=="SEED":
        return 0.2+0.1*x+1.3*math.erf(0.8*x)
    if which=="TRANSFER":
        return -0.4+0.25*x-0.7*math.erf(1.6*x)
    raise PrimitiveAcquisitionError("TASK_UNKNOWN")

def _rows(which:str,xs:Sequence[float]):
    return [{"x":float(x),"y":_truth(which,float(x))} for x in xs]

def _solve3(a,b):
    m=[list(map(float,a[i]))+[float(b[i])] for i in range(3)]
    for c in range(3):
        p=max(range(c,3),key=lambda r:abs(m[r][c]))
        if abs(m[p][c])<=1e-12: return None
        m[c],m[p]=m[p],m[c]
        div=m[c][c]; m[c]=[v/div for v in m[c]]
        for r in range(3):
            if r==c: continue
            f=m[r][c]
            if abs(f)<=1e-18: continue
            m[r]=[x-f*y for x,y in zip(m[r],m[c])]
    out=[m[i][-1] for i in range(3)]
    return out if all(math.isfinite(x) for x in out) else None

def _fit(rows,primitive,gamma):
    xs=[float(r["x"]) for r in rows]
    ys=[float(r["y"]) for r in rows]
    z=[float(primitive(float(gamma)*x)) for x in xs]
    cols=[[1.0]*len(xs),xs,z]
    xtx=[[sum(cols[i][k]*cols[j][k] for k in range(len(xs))) for j in range(3)] for i in range(3)]
    xty=[sum(cols[i][k]*ys[k] for k in range(len(xs))) for i in range(3)]
    for i in range(3): xtx[i][i]+=1e-13
    coeff=_solve3(xtx,xty)
    if coeff is None: return None
    pred=[coeff[0]+coeff[1]*x+coeff[2]*primitive(float(gamma)*x) for x in xs]
    return {
        "gamma":float(gamma),
        "coefficients":coeff,
        "train_nrmse":expr._nrmse(ys,pred),
    }

def _score(candidate,rows,primitive):
    pred=[
        candidate["coefficients"][0]+candidate["coefficients"][1]*float(r["x"])+
        candidate["coefficients"][2]*primitive(candidate["gamma"]*float(r["x"]))
        for r in rows
    ]
    return expr._nrmse([float(r["y"]) for r in rows],pred)

def acquire_primitive(pre:Mapping[str,Any]):
    desc=pre["primitive_descriptor"]
    module_name=str(desc["module"])
    attr=str(desc["attribute"])
    if module_name!="math":
        raise PrimitiveAcquisitionError("MODULE_NOT_IN_FROZEN_STDLIB_SCOPE")
    module=importlib.import_module(module_name)
    fn=getattr(module,attr,None)
    if not callable(fn):
        raise PrimitiveAcquisitionError("PRIMITIVE_NOT_CALLABLE")
    probes=[float(x) for x in pre["primitive_verification"]["probes"]]
    first=[float(fn(x)) for x in probes]
    second=[float(fn(x)) for x in probes]
    if [x.hex() for x in first] != [x.hex() for x in second]:
        raise PrimitiveAcquisitionError("PRIMITIVE_NONDETERMINISTIC")
    if not all(math.isfinite(x) for x in first):
        raise PrimitiveAcquisitionError("PRIMITIVE_NONFINITE")
    table=dict(zip(probes,first))
    if abs(float(fn(0.0)))>1e-15:
        raise PrimitiveAcquisitionError("PRIMITIVE_ZERO_IDENTITY_FAIL")
    for x in probes:
        if -x in table and abs(table[x]+table[-x])>1e-15:
            raise PrimitiveAcquisitionError("PRIMITIVE_ODD_SYMMETRY_FAIL")
    payload={
        "module":module_name,
        "attribute":attr,
        "python":platform.python_version(),
        "probe_input_hex":[x.hex() for x in probes],
        "probe_output_hex":[x.hex() for x in first],
    }
    fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return fn,{"descriptor":desc,"fingerprint_sha256":fingerprint,"probe_payload":payload}

def _best_fit(train,hold,primitive,gammas,use_holdout):
    rows=[]
    for g in gammas:
        c=_fit(train,primitive,float(g))
        if c is None: continue
        c["holdout_nrmse"]=_score(c,hold,primitive)
        rows.append(c)
    if not rows: return None
    if use_holdout:
        rows.sort(key=lambda c:(max(c["train_nrmse"],c["holdout_nrmse"]),c["gamma"]))
    else:
        rows.sort(key=lambda c:(c["train_nrmse"],c["gamma"]))
    return rows[0]

def run()->dict[str,Any]:
    pre=json.loads(PRE.read_text())
    tx=[float(x) for x in pre["x_population"]["training_x"]]
    hx=[float(x) for x in pre["x_population"]["holdout_x"]]
    seed=_rows("SEED",tx)
    seed_hold=_rows("SEED",hx)
    transfer=_rows("TRANSFER",tx)
    transfer_hold=_rows("TRANSFER",hx)

    seed_miss=registry.resolve_verified_capability(seed,target="y",input_name="x").get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED"
    transfer_miss=registry.resolve_verified_capability(transfer,target="y",input_name="x").get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED"

    ecfg=pre["baseline_expression_config"]
    est=time.perf_counter()
    expr_out=expr.discover(
        seed,target="y",inputs=["x"],
        max_depth=int(ecfg["max_depth"]),
        beam_width=int(ecfg["beam_width"]),
        pair_feature_pool=int(ecfg["pair_feature_pool"]),
        exact_nrmse=float(ecfg["exact_nrmse"]),
    )
    expr_seconds=time.perf_counter()-est
    expression_miss=expr_out.get("status")!="EXACT_CANDIDATE_FOUND"

    primitive,verification=acquire_primitive(pre)
    gammas=[float(x) for x in pre["shape_search"]["gamma_grid"]]

    sst=time.perf_counter()
    seed_best=_best_fit(seed,seed_hold,primitive,gammas,True)
    seed_seconds=time.perf_counter()-sst
    tst=time.perf_counter()
    transfer_best=_best_fit(transfer,transfer_hold,primitive,gammas,False)
    transfer_seconds=time.perf_counter()-tst

    seed_pass=bool(seed_best and seed_best["train_nrmse"]<=1e-10 and seed_best["holdout_nrmse"]<=1e-8)
    transfer_pass=bool(transfer_best and transfer_best["holdout_nrmse"]<=1e-8)
    passed=seed_miss and transfer_miss and expression_miss and seed_pass and transfer_pass
    return {
        "schema":SCHEMA,
        "status":"PASS__FIXED_OPERATOR_SET_ESCAPE_VIA_JIT_VERIFIED_PRIMITIVE__ZERO_CREDIT" if passed else "FAIL__JIT_PRIMITIVE_RESIDUAL",
        "baseline_seed_registry_v4_miss":seed_miss,
        "baseline_transfer_registry_v4_miss":transfer_miss,
        "baseline_expression_status":expr_out.get("status"),
        "baseline_expression_best_nrmse":None if not expr_out.get("best_candidate") else expr_out["best_candidate"].get("nrmse"),
        "baseline_expression_best_validation_nrmse":None if not expr_out.get("best_candidate") else expr_out["best_candidate"].get("validation_nrmse"),
        "baseline_expression_search_seconds":expr_seconds,
        "primitive_verification":verification,
        "seed_best":seed_best,
        "seed_search_seconds":seed_seconds,
        "transfer_best":transfer_best,
        "transfer_search_seconds":transfer_seconds,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "ONE_STDLIB_PRIMITIVE_DOES_NOT_PROVE_ARBITRARY_SAFE_OPERATOR_ACQUISITION",
            "PYTHON_STDLIB_IS_AN_EXECUTION_SUBSTRATE_NOT_LEARNED_STATE",
            "NO_H100_TERMINAL_CREDIT"
        ],
        "h100_terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
