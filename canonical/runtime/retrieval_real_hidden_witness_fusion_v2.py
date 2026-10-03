#!/usr/bin/env python3
"""Cross-validated rank fusion for the frozen real hidden-witness arena.

Goal: reduce verification depth without sacrificing monotonic pooled recall.
Training is leave-one-target-out. The held-out target never influences the
weight/k selection used for its cases.

This is finite regression evidence only. It is not a live-provider oracle.
"""
from __future__ import annotations

import itertools
import json
import math
import statistics
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import retrieval_real_hidden_witness_arena_v1 as arena

SCHEMA="PROJECT_BRAIN_RETRIEVAL_REAL_HIDDEN_WITNESS_FUSION_V2"
ROUTES=tuple(arena.ROUTES)
WEIGHTS=(0,1,2,3,4)
K_VALUES=(0,1,3,10,30,60)


def _case_rows(root:Path)->list[dict[str,Any]]:
    catalog_obj=arena.load_catalog(root)
    catalog=catalog_obj["targets"]
    trees=arena.load_tree_fingerprints(root)
    content=arena.load_content_fingerprints(root)
    rows=[]
    for profile in arena.PROFILES:
        for target in catalog:
            for qi,query in enumerate(target.get("behavioral_queries") or []):
                ranks={}
                orders={}
                for route in ROUTES:
                    ranked=arena.rank(
                        catalog,str(query),profile=profile,route=route,
                        tree_fingerprints=trees,content_fingerprints=content,
                    )
                    ids=[str(x["id"]) for x in ranked]
                    orders[route]=ids
                    ranks[route]={cid:i+1 for i,cid in enumerate(ids)}
                rows.append({
                    "case_id":f"{profile}:{target['id']}:Q{qi}",
                    "profile":profile,
                    "target_id":str(target["id"]),
                    "query":str(query),
                    "orders":orders,
                    "ranks":ranks,
                    "candidate_ids":[str(x["id"]) for x in catalog],
                })
    return rows


def _fused_order(case:Mapping[str,Any],weights:tuple[int,...],k:int)->list[str]:
    if len(weights)!=len(ROUTES):
        raise ValueError("WEIGHT_ROUTE_ARITY_MISMATCH")
    rows=[]
    for cid in case["candidate_ids"]:
        score=0.0
        best=10**9
        for w,route in zip(weights,ROUTES):
            rank=int(case["ranks"][route][cid])
            best=min(best,rank)
            if w:
                score += float(w)/(float(k)+float(rank))
        rows.append((score,best,cid))
    rows.sort(key=lambda x:(-x[0],x[1],x[2]))
    return [x[2] for x in rows]


def _metrics(cases:list[Mapping[str,Any]],weights:tuple[int,...],k:int)->dict[str,float]:
    if not cases:
        return {"top1":0.0,"top3":0.0,"top5":0.0,"mrr":0.0,"mean_rank":9999.0}
    ranks=[]
    for case in cases:
        order=_fused_order(case,weights,k)
        ranks.append(order.index(case["target_id"])+1)
    n=len(ranks)
    return {
        "top1":sum(r==1 for r in ranks)/n,
        "top3":sum(r<=3 for r in ranks)/n,
        "top5":sum(r<=5 for r in ranks)/n,
        "mrr":sum(1.0/r for r in ranks)/n,
        "mean_rank":statistics.fmean(ranks),
    }


def _parameter_grid():
    for weights in itertools.product(WEIGHTS,repeat=len(ROUTES)):
        if not any(weights):
            continue
        # Remove scale-equivalent duplicates such as (1,1,1) vs (2,2,2).
        g=0
        for w in weights:
            g=math.gcd(g,int(w))
        if g>1:
            continue
        for k in K_VALUES:
            yield tuple(int(x) for x in weights),int(k)


def _select(training:list[Mapping[str,Any]])->tuple[tuple[int,...],int,dict[str,float]]:
    best=None
    for weights,k in _parameter_grid():
        m=_metrics(training,weights,k)
        # Optimize user-relevant verification depth first, then broad safety.
        key=(
            m["top1"],
            m["top3"],
            m["mrr"],
            -m["mean_rank"],
            m["top5"],
            -sum(weights),
            -k,
            tuple(-x for x in weights),
        )
        if best is None or key>best[0]:
            best=(key,weights,k,m)
    assert best is not None
    return best[1],best[2],best[3]


def _baseline(cases:list[Mapping[str,Any]])->dict[str,Any]:
    # Existing objects: HYBRID route, plus monotonic union of route top-k.
    n=len(cases)
    hybrid_ranks=[]
    pooled={}
    for kk in (1,3,5):
        hits=0; sizes=[]
        for case in cases:
            pool=[]
            seen=set()
            for route in ROUTES:
                for cid in case["orders"][route][:kk]:
                    if cid not in seen:
                        seen.add(cid);pool.append(cid)
            hits += case["target_id"] in seen
            sizes.append(len(seen))
        pooled[str(kk)]={
            "recall":hits/n,
            "mean_candidate_pool_size":statistics.fmean(sizes),
            "max_candidate_pool_size":max(sizes),
        }
    for case in cases:
        hybrid_ranks.append(case["orders"]["HYBRID"].index(case["target_id"])+1)
    return {
        "hybrid_top1":sum(x==1 for x in hybrid_ranks)/n,
        "hybrid_top3":sum(x<=3 for x in hybrid_ranks)/n,
        "hybrid_top5":sum(x<=5 for x in hybrid_ranks)/n,
        "hybrid_mrr":sum(1.0/x for x in hybrid_ranks)/n,
        "hybrid_mean_rank":statistics.fmean(hybrid_ranks),
        "monotonic_pooled":pooled,
    }


def evaluate(root:Path)->dict[str,Any]:
    cases=_case_rows(root)
    target_ids=sorted({x["target_id"] for x in cases})
    heldout=[]
    heldout_ranks=[]
    for target_id in target_ids:
        train=[x for x in cases if x["target_id"]!=target_id]
        test=[x for x in cases if x["target_id"]==target_id]
        weights,k,train_metrics=_select(train)
        test_ranks=[]
        for case in test:
            order=_fused_order(case,weights,k)
            r=order.index(case["target_id"])+1
            test_ranks.append(r)
            heldout_ranks.append(r)
        heldout.append({
            "heldout_target_id":target_id,
            "selected_weights":dict(zip(ROUTES,weights)),
            "selected_k":k,
            "training_metrics":train_metrics,
            "heldout_case_count":len(test),
            "heldout_top1":sum(x==1 for x in test_ranks)/len(test),
            "heldout_top3":sum(x<=3 for x in test_ranks)/len(test),
            "heldout_top5":sum(x<=5 for x in test_ranks)/len(test),
            "heldout_mrr":sum(1.0/x for x in test_ranks)/len(test),
            "heldout_mean_rank":statistics.fmean(test_ranks),
        })
    n=len(heldout_ranks)
    cv={
        "case_count":n,
        "target_fold_count":len(target_ids),
        "top1_recall":sum(x==1 for x in heldout_ranks)/n,
        "top3_recall":sum(x<=3 for x in heldout_ranks)/n,
        "top5_recall":sum(x<=5 for x in heldout_ranks)/n,
        "mrr":sum(1.0/x for x in heldout_ranks)/n,
        "mean_rank":statistics.fmean(heldout_ranks),
        "max_rank":max(heldout_ranks),
    }
    baseline=_baseline(cases)
    return {
        "schema":SCHEMA,
        "status":"MEASURED__LEAVE_ONE_TARGET_OUT_CROSS_VALIDATED_RANK_FUSION",
        "routes":list(ROUTES),
        "weight_grid":list(WEIGHTS),
        "k_values":list(K_VALUES),
        "baseline":baseline,
        "cross_validated":cv,
        "folds":heldout,
        "improves_hybrid_top1":cv["top1_recall"]>baseline["hybrid_top1"],
        "improves_hybrid_mrr":cv["mrr"]>baseline["hybrid_mrr"],
        "preserves_existing_pooled_top5_recall":baseline["monotonic_pooled"]["5"]["recall"]==1.0,
        "promotion_gate":{
            "minimum_cv_top1":baseline["hybrid_top1"],
            "minimum_cv_top3":baseline["hybrid_top3"],
            "minimum_cv_top5":1.0,
            "requires_strict_mrr_improvement":True,
        },
        "promotion_eligible":bool(
            cv["top1_recall"]>=baseline["hybrid_top1"]
            and cv["top3_recall"]>=baseline["hybrid_top3"]
            and cv["top5_recall"]>=1.0
            and cv["mrr"]>baseline["hybrid_mrr"]
        ),
        "open_world_recall_claim":False,
        "live_provider_oracle":False,
        "hard_rules":[
            "HELD_OUT_TARGET_NEVER_INFLUENCES_ITS_FUSION_PARAMETER_SELECTION",
            "FUSION_IS_VERIFICATION_ORDERING_ONLY__MONOTONIC_CANDIDATE_MEMORY_REMAINS_AUTHORITATIVE",
            "NO_FINITE_ARENA_TO_LIVE_PROVIDER_PROBABILITY_TRANSFER",
            "NO_PROMOTION_UNLESS_HELD_OUT_METRICS_CLEAR_EXPLICIT_GATE",
        ],
    }


def main()->int:
    root=Path(__file__).resolve().parents[2]
    out=evaluate(root)
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["preserves_existing_pooled_top5_recall"] else 1


if __name__=="__main__":
    raise SystemExit(main())
