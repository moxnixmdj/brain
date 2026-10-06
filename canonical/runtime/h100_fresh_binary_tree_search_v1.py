from __future__ import annotations
import json
from pathlib import Path
from typing import Any,Mapping,Sequence
from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr
from canonical.runtime import h100_verified_capability_registry_v8 as registry

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_FRESH_BINARY_TREE_SEARCH_PRECOMMIT_V1.json"

def make_rows(task:Mapping[str,Any],phase:str,xs:Sequence[float]):
    a,b,c=[float(v) for v in task[phase]]
    tree=task["tree"]
    out=[]
    for x in xs:
        row={"x":float(x)}
        f=expr.evaluate_tree(tree,row)
        out.append({"x":float(x),"y":a+b*float(x)+c*f})
    return out

def transfer_candidate(candidate,train,hold):
    feats=list(candidate["features"])
    tx=[float(r["x"]) for r in train]; hx=[float(r["x"]) for r in hold]
    ty=[float(r["y"]) for r in train]; hy=[float(r["y"]) for r in hold]
    train_features=[[expr.evaluate_tree(t,{"x":x}) for x in tx] for t in feats]
    hold_features=[[expr.evaluate_tree(t,{"x":x}) for x in hx] for t in feats]
    co=expr._fit_linear_features(train_features,ty)
    if co is None:return None
    pt=[co[0]+sum(co[j+1]*train_features[j][i] for j in range(len(feats))) for i in range(len(tx))]
    ph=[co[0]+sum(co[j+1]*hold_features[j][i] for j in range(len(feats))) for i in range(len(hx))]
    return {
      "coefficients":[float(v) for v in co],
      "train_nrmse":expr._nrmse(ty,pt),
      "holdout_nrmse":expr._nrmse(hy,ph)
    }

def run():
    pre=json.loads(PRE.read_text())
    cfg=pre["search_contract"]
    rows=[]
    for task in pre["tasks"]:
        train=make_rows(task,"seed",pre["training_x"])
        hold=make_rows(task,"seed",pre["holdout_x"])
        allrows=train+hold
        base=registry.resolve_verified_capability(train,target="y",input_name="x")
        found=expr.discover(
            allrows,target="y",inputs=["x"],
            max_depth=int(cfg["max_depth"]),
            beam_width=int(cfg["beam_width"]),
            pair_feature_pool=int(cfg["pair_feature_pool"]),
            exact_nrmse=float(cfg["exact_nrmse"])
        )
        cand=found.get("best_candidate")
        transfer=None
        if found.get("status")=="EXACT_CANDIDATE_FOUND" and cand is not None:
            tt=make_rows(task,"transfer",pre["training_x"])
            th=make_rows(task,"transfer",pre["holdout_x"])
            transfer=transfer_candidate(cand,tt,th)
        rows.append({
          "id":task["id"],
          "baseline_registry_v8_miss":base.get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",
          "search_status":found.get("status"),
          "generated_tree_count":found.get("generated_tree_count"),
          "unique_feature_count":found.get("unique_feature_count"),
          "candidate_count":found.get("candidate_count"),
          "best_candidate":cand,
          "transfer":transfer
        })
    passed=all(
      r["baseline_registry_v8_miss"]
      and r["search_status"]=="EXACT_CANDIDATE_FOUND"
      and r["best_candidate"] is not None
      and float(r["best_candidate"]["nrmse"])<=1e-8
      and float(r["best_candidate"]["validation_nrmse"])<=1e-8
      and r["transfer"] is not None
      and float(r["transfer"]["holdout_nrmse"])<=1e-8
      for r in rows
    )
    return {
      "status":"PASS__FRESH_BINARY_TREE_SEARCH_AND_TRANSFER__ZERO_LEARNED" if passed else "FAIL__FRESH_BINARY_TREE_SEARCH_RESIDUAL",
      "tasks":rows,
      "persistent_learned_bytes":0,
      "external_learned_capability_calls":0,
      "h100_terminal_credit_delta":0
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
