#!/usr/bin/env python3
"""Residual technical-anchor recovery for V12's single GitHub miss."""
from __future__ import annotations
import json,time
from canonical.runtime import retrieval_live_provider_arena_v1 as base

QUERIES=(
 "Chinese character pronunciation heteronym tone styles Python in:name,description,readme",
 "Chinese pinyin tone styles heteronym Python in:name,description,readme",
 "Chinese romanization tone sandhi Python in:name,description,readme",
)
TARGET="mozillazg/python-pinyin"

def run(limit=100,timeout=20.0):
    union=[];seen=set();rows=[]
    for q in QUERIES:
        start=time.perf_counter()
        try: ids=base.github(q,limit=limit,timeout=timeout);status="SUCCESS";err=None
        except Exception as exc: ids=[];status="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:300]}"
        before=len(union)
        for x in ids:
            n=str(x).casefold()
            if n not in seen:seen.add(n);union.append(n)
        rows.append({"query":q,"status":status,"new_union_candidates":len(union)-before,"latency_seconds":time.perf_counter()-start,"error":err})
    target=TARGET.casefold();hit=target in seen
    return {"schema":"PROJECT_BRAIN_RETRIEVAL_PINYIN_RESIDUAL_RECOVERY_V13","status":"LIVE_RESIDUAL_PROBE_COMPLETE","query_rows":rows,"candidate_ids":union,"candidate_pool_size":len(union),"target_hit":hit,"target_rank":union.index(target)+1 if hit else None,"open_world_completeness_claim":False,"incremental_spend_usd":0,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"execution_authority":False,"promotion_authority":False}

if __name__=="__main__":print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
