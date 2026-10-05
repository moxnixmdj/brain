"""Iterative-depth escape experiment for H100 expression search."""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr
from canonical.runtime import h100_verified_capability_registry_v4 as registry

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_ITERATIVE_DEPTH_ESCAPE_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_ITERATIVE_DEPTH_ESCAPE_RESULT_V1"


def _deep_log(x: float) -> float:
    y=float(x)
    for _ in range(4):
        y=math.log1p(abs(y))
    return y


def _truth(which: str, x: float) -> float:
    f=_deep_log(x)
    if which=="SEED":
        return 0.35-0.12*x+1.7*f
    if which=="TRANSFER":
        return -0.8+0.27*x-0.9*f
    raise ValueError(which)


def _rows(which: str, xs: list[float]):
    return [{"x":float(x),"y":_truth(which,float(x))} for x in xs]


def _registry_miss(rows):
    out=registry.resolve_verified_capability(rows,target="y",input_name="x")
    return out.get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED"


def _refit(features, rows):
    columns=[[expr.evaluate_tree(tree,row) for row in rows] for tree in features]
    ys=[float(r["y"]) for r in rows]
    coeff=expr._fit_linear_features(columns,ys)
    if coeff is None:
        return None
    return {"features":features,"coefficients":coeff}


def run() -> dict[str,Any]:
    pre=json.loads(PRE.read_text())
    train_x=[float(x) for x in pre["x_population"]["training_x"]]
    hold_x=[float(x) for x in pre["x_population"]["transfer_holdout_x"]]
    seed=_rows("SEED",train_x)
    transfer_train=_rows("TRANSFER",train_x)
    transfer_hold=_rows("TRANSFER",hold_x)

    rows=[]
    first_exact=None
    first_exact_best=None
    for cfg in pre["search_schedule"]:
        st=time.perf_counter()
        out=expr.discover(
            seed,target="y",inputs=["x"],
            max_depth=int(cfg["max_depth"]),
            beam_width=int(cfg["beam_width"]),
            pair_feature_pool=int(cfg["pair_feature_pool"]),
            exact_nrmse=float(pre["exact_nrmse"]),
        )
        elapsed=time.perf_counter()-st
        best=out.get("best_candidate")
        row={
            "max_depth":cfg["max_depth"],
            "status":out.get("status"),
            "generated_tree_count":out.get("generated_tree_count"),
            "unique_feature_count":out.get("unique_feature_count"),
            "candidate_count":out.get("candidate_count"),
            "wall_clock_seconds":elapsed,
            "best_nrmse":None if not best else best.get("nrmse"),
            "best_validation_nrmse":None if not best else best.get("validation_nrmse"),
            "best_feature_signatures":None if not best else best.get("feature_signatures"),
        }
        rows.append(row)
        if first_exact is None and out.get("status")=="EXACT_CANDIDATE_FOUND":
            first_exact=int(cfg["max_depth"])
            first_exact_best=best
            break

    transfer_candidate=None
    transfer_nrmse=None
    if first_exact_best is not None:
        transfer_candidate=_refit(first_exact_best["features"],transfer_train)
        if transfer_candidate is not None:
            pred=[expr.predict(transfer_candidate,row) for row in transfer_hold]
            transfer_nrmse=expr._nrmse([r["y"] for r in transfer_hold],pred)

    shallower=[r for r in rows if int(r["max_depth"])<4]
    pass_gate=bool(
        _registry_miss(seed)
        and _registry_miss(transfer_train)
        and len(shallower)==3
        and all(r["status"]!="EXACT_CANDIDATE_FOUND" for r in shallower)
        and first_exact==4
        and transfer_nrmse is not None
        and transfer_nrmse<=float(pre["exact_nrmse"])
    )
    return {
        "schema":SCHEMA,
        "status":"PASS__DEPTH4_ESCAPE_AND_DISTINCT_TRANSFER__ZERO_CREDIT" if pass_gate else "FAIL__DEPTH_ESCAPE_RESIDUAL",
        "baseline_seed_registry_v4_miss":_registry_miss(seed),
        "baseline_transfer_registry_v4_miss":_registry_miss(transfer_train),
        "first_exact_depth":first_exact,
        "search_by_depth":rows,
        "first_exact_feature_signatures":None if first_exact_best is None else first_exact_best.get("feature_signatures"),
        "transfer_structure_only_refit":transfer_candidate is not None,
        "transfer_holdout_nrmse":transfer_nrmse,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "ONE_DEPTH4_ESCAPE_DOES_NOT_PROVE_PRACTICAL_UNBOUNDED_SEARCH",
            "OPERATOR_SET_REMAINS_FIXED",
            "MAX_DEPTH_4_REMAINS_FINITE",
            "NO_H100_TERMINAL_CREDIT",
        ],
        "h100_terminal_credit_delta":0,
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
