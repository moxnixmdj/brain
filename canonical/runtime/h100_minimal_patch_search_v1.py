"""Frozen minimal patch-search/transfer experiment for H100."""
from __future__ import annotations
import json, statistics, time
from pathlib import Path
from typing import Any

from canonical.runtime import h100_verified_capability_registry_v1 as registry
from canonical.runtime import h100_zero_learned_polynomial_patch_v1 as poly
from canonical.runtime import h100_zero_learned_transfer_v1 as transfer

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_MINIMAL_PATCH_SEARCH_PRECOMMIT_V1.json"
TPRE=ROOT/"canonical/governance/H100_ZERO_LEARNED_TRANSFER_PREEXPOSURE_V1.json"
SCHEMA="PROJECT_BRAIN_H100_MINIMAL_PATCH_SEARCH_RESULT_V1"

def _truth(which:str,x:float)->float:
    if which=="SEED": return x**3+0.123*x
    if which=="TRANSFER": return -0.7+0.31*x+0.42*x**3
    raise ValueError("TRUTH_UNKNOWN")

def _rows(which:str,xs:list[float])->list[dict[str,float]]:
    return [{"x":float(x),"y":_truth(which,float(x))} for x in xs]

def _score(cand,hold):
    pred=[poly.predict(cand,r) for r in hold]
    return transfer._nrmse([r["y"] for r in hold],pred)

def _baseline_miss(rows):
    out=registry.resolve_verified_capability(rows,target="y",input_name="x")
    return out.get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED"

def search_seed(tpre:dict[str,Any])->dict[str,Any]:
    train=_rows("SEED",[float(x) for x in tpre["training_x"]])
    hold=_rows("SEED",[float(x) for x in tpre["holdout_x"]])
    candidates=[]
    for rank,power in ((2,2),(3,3),(4,4)):
        c=poly.fit(train,target="y",input_name="x",power=power)
        h=_score(c,hold)
        candidates.append({"patch_id":f"AFFINE_PLUS_X{power}","power":power,"complexity_rank":rank,"train_nrmse":c["train_nrmse"],"holdout_nrmse":h,"candidate":c})
    passing=[x for x in candidates if x["train_nrmse"]<=1e-10 and x["holdout_nrmse"]<=1e-8]
    passing.sort(key=lambda x:(x["complexity_rank"],x["patch_id"]))
    return {"candidates":candidates,"selected":passing[0] if passing else None}

def _timing(tpre,reps=7):
    search_seed(tpre)
    vals=[]
    for _ in range(reps):
        st=time.perf_counter(); out=search_seed(tpre); vals.append(time.perf_counter()-st)
        if out["selected"] is None: raise RuntimeError("PATCH_SEARCH_NO_PASS")
    return statistics.median(vals),min(vals),max(vals)

def run()->dict[str,Any]:
    pre=json.loads(PRE.read_text()); tpre=json.loads(TPRE.read_text())
    if pre.get("status")!="FROZEN_BEFORE_PATCH_SEARCH_OUTCOMES__DISTINCT_TRANSFER_TASK_FROZEN__ZERO_CREDIT":
        raise RuntimeError("PRECOMMIT_NOT_FROZEN")
    seed_train=_rows("SEED",[float(x) for x in tpre["training_x"]])
    transfer_train=_rows("TRANSFER",[float(x) for x in tpre["training_x"]])
    baseline_seed=_baseline_miss(seed_train)
    baseline_transfer=_baseline_miss(transfer_train)
    search=search_seed(tpre)
    selected=search["selected"]
    if selected is None: raise RuntimeError("NO_PATCH_SELECTED")
    power=int(selected["power"])
    transfer_candidate=poly.fit(transfer_train,target="y",input_name="x",power=power)
    transfer_hold=_rows("TRANSFER",[float(x) for x in tpre["holdout_x"]])
    transfer_err=_score(transfer_candidate,transfer_hold)
    med,mn,mx=_timing(tpre,7)
    passed=(baseline_seed and baseline_transfer and selected["patch_id"]=="AFFINE_PLUS_X3" and transfer_err<=1e-8)
    return {
        "schema":SCHEMA,
        "status":"MINIMAL_PATCH_SEARCH_AND_DISTINCT_TRANSFER_PASS__ZERO_CREDIT" if passed else "PATCH_SEARCH_TRANSFER_RESIDUAL",
        "baseline_seed_registry_miss":baseline_seed,
        "baseline_transfer_registry_miss":baseline_transfer,
        "searched_patch_count":len(search["candidates"]),
        "patch_candidates":[{k:v for k,v in x.items() if k!="candidate"} for x in search["candidates"]],
        "selected_patch_id":selected["patch_id"],
        "selected_power":power,
        "seed_train_nrmse":selected["train_nrmse"],
        "seed_holdout_nrmse":selected["holdout_nrmse"],
        "transfer_train_nrmse":transfer_candidate["train_nrmse"],
        "transfer_holdout_nrmse":transfer_err,
        "patch_search_median_seconds":med,
        "patch_search_min_seconds":mn,
        "patch_search_max_seconds":mx,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "compile_candidate":{
            "capability_id":"CAP_AFFINE_CUBIC_V1",
            "family":"affine_plus_power",
            "fixed_power":3,
            "source_patch_id":"AFFINE_PLUS_X3"
        },
        "hard_nonclaims":[
            "PATCH_GRAMMAR_DESIGNED_AFTER_CUBIC_DEVELOPMENT_MISS",
            "ONE_DISTINCT_CUBIC_TRANSFER_TASK_DOES_NOT_PROVE_OPEN_WORLD_PATCH_SEARCH",
            "NO_H100_TERMINAL_CREDIT"
        ],
        "h100_terminal_credit_delta":0
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
