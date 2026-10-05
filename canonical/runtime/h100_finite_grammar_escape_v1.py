"""Finite-patch-grammar escape via deterministic expression-tree search."""
from __future__ import annotations
import json, math, time
from pathlib import Path
from typing import Any

from canonical.runtime import h100_verified_capability_registry_v3 as registry
from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_FINITE_GRAMMAR_ESCAPE_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_FINITE_GRAMMAR_ESCAPE_RESULT_V1"

def _truth(which:str,x:float)->float:
    if which=="SEED":
        return 0.2+0.1*x+0.7/(1.0+x*x)
    if which=="TRANSFER":
        return -0.4+0.25*x-1.1/(1.0+x*x)
    raise ValueError(which)

def _rows(which:str,xs:list[float]):
    return [{"x":float(x),"y":_truth(which,float(x))} for x in xs]

def _nrmse(actual,pred):
    return expr._nrmse(actual,pred)

def _registry_miss(rows):
    return registry.resolve_verified_capability(rows,target="y",input_name="x").get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED"

def _refit_structure(features,train_rows):
    cols=[[expr.evaluate_tree(tree,row) for row in train_rows] for tree in features]
    ys=[float(r["y"]) for r in train_rows]
    coeff=expr._fit_linear_features(cols,ys)
    if coeff is None:
        return None
    return {"features":features,"coefficients":coeff}

def run()->dict[str,Any]:
    pre=json.loads(PRE.read_text())
    cfg=pre["search_config"]
    seed=_rows("SEED",[float(x) for x in pre["x_population"]["training_x"]])
    transfer_train=_rows("TRANSFER",[float(x) for x in pre["x_population"]["training_x"]])
    transfer_hold=_rows("TRANSFER",[float(x) for x in pre["x_population"]["transfer_holdout_x"]])

    seed_miss=_registry_miss(seed)
    transfer_miss=_registry_miss(transfer_train)

    st=time.perf_counter()
    search=expr.discover(
        seed,target="y",inputs=["x"],
        max_depth=int(cfg["max_depth"]),
        beam_width=int(cfg["beam_width"]),
        pair_feature_pool=int(cfg["pair_feature_pool"]),
        exact_nrmse=float(cfg["exact_nrmse"]),
    )
    search_seconds=time.perf_counter()-st
    best=search.get("best_candidate")
    exact=search.get("status")=="EXACT_CANDIDATE_FOUND" and isinstance(best,dict)

    transfer_candidate=None
    transfer_holdout_nrmse=None
    if exact:
        features=best["features"]
        transfer_candidate=_refit_structure(features,transfer_train)
        if transfer_candidate is not None:
            pred=[expr.predict(transfer_candidate,row) for row in transfer_hold]
            transfer_holdout_nrmse=_nrmse([r["y"] for r in transfer_hold],pred)

    passed=bool(
        seed_miss and transfer_miss and exact and
        transfer_holdout_nrmse is not None and transfer_holdout_nrmse<=1e-8
    )
    return {
        "schema":SCHEMA,
        "status":"PASS__FINITE_PATCH_GRAMMAR_ESCAPE_AND_STRUCTURE_TRANSFER__ZERO_CREDIT" if passed else "FAIL__FINITE_GRAMMAR_ESCAPE_RESIDUAL",
        "baseline_seed_registry_v3_miss":seed_miss,
        "baseline_transfer_registry_v3_miss":transfer_miss,
        "seed_search_status":search.get("status"),
        "seed_best_nrmse":None if not best else best.get("nrmse"),
        "seed_best_validation_nrmse":None if not best else best.get("validation_nrmse"),
        "seed_feature_signatures":None if not best else best.get("feature_signatures"),
        "seed_feature_trees":None if not best else best.get("features"),
        "seed_generated_tree_count":search.get("generated_tree_count"),
        "seed_unique_feature_count":search.get("unique_feature_count"),
        "seed_candidate_count":search.get("candidate_count"),
        "search_wall_clock_seconds":search_seconds,
        "transfer_structure_only_refit":transfer_candidate is not None,
        "transfer_holdout_nrmse":transfer_holdout_nrmse,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "ONE_RATIONAL_ESCAPE_DOES_NOT_PROVE_UNIVERSAL_SEARCH_PRACTICALITY",
            "FROZEN_DEPTH_EXPRESSION_GRAMMAR_REMAINS_FINITE",
            "NO_H100_TERMINAL_CREDIT"
        ],
        "h100_terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
