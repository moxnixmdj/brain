#!/usr/bin/env python3
"""V12 live recovery for the six V11 GitHub misses."""
from __future__ import annotations
import hashlib,json,time
from typing import Any
from canonical.runtime import retrieval_live_provider_arena_v1 as base

SCHEMA="PROJECT_BRAIN_RETRIEVAL_GITHUB_MISS_RECOVERY_V12"
CASES=(
 {"episode_id":"GITHUB_ZH_SEGMENTATION","strategy_id":"CROSS_LANGUAGE_V12","target":"fxsjy/jieba","queries":["Chinese word segmentation Python NLP in:name,description,readme","Chinese tokenizer segmentation Python in:name,description,readme"]},
 {"episode_id":"GITHUB_ZH_PINYIN","strategy_id":"CROSS_LANGUAGE_V12","target":"mozillazg/python-pinyin","queries":["Chinese characters romanization pinyin Python in:name,description,readme","Chinese character pronunciation romanization Python in:name,description,readme"]},
 {"episode_id":"GITHUB_RU_NLP","strategy_id":"CROSS_LANGUAGE_V12","target":"natasha/natasha","queries":["Russian language NLP morphology named entity recognition Python in:name,description,readme","Russian text processing morphology syntax NER Python in:name,description,readme"]},
 {"episode_id":"GITHUB_AR_TEXT","strategy_id":"CROSS_LANGUAGE_V12","target":"linuxscout/pyarabic","queries":["Arabic text processing diacritics letters Python in:name,description,readme","Arabic language text toolkit Python diacritization in:name,description,readme"]},
 {"episode_id":"GITHUB_PY_LINTER","strategy_id":"BEHAVIOR_LATTICE_V12","target":"astral-sh/ruff","queries":["Python linter formatter written in Rust fast in:name,description,readme","Python code checker formatter performance Rust in:name,description,readme","Python lint formatting tool Rust in:name,description,readme"]},
 {"episode_id":"GITHUB_PY_CLI","strategy_id":"BEHAVIOR_LATTICE_V12","target":"pallets/click","queries":["Python CLI framework decorators commands options in:name,description,readme","Python composable command line toolkit in:name,description,readme","Python command line utility framework decorators in:name,description,readme"]},
)

def validate():
    assert len(CASES)==6
    for row in CASES:
        t=row["target"].casefold()
        for q in row["queries"]:
            if t in q.casefold():
                raise ValueError("TARGET_IDENTITY_LEAKED:"+row["episode_id"])

def run(*,limit:int=50,timeout:float=20.0)->dict[str,Any]:
    validate(); events=[]
    for seq,row in enumerate(CASES,1):
        union=[];seen=set();qrows=[];errors=[];status="SUCCESS";start=time.perf_counter()
        for qi,q in enumerate(row["queries"],1):
            qs=time.perf_counter()
            try:
                ids=base.github(q,limit=limit,timeout=timeout); qstatus="SUCCESS";err=None
            except Exception as exc:
                ids=[];qstatus="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:400]}"
                status="PARTIAL_RETRYABLE" if union else "FAILED_RETRYABLE";errors.append(err)
            before=len(union)
            for x in ids:
                n=str(x).casefold()
                if n not in seen: seen.add(n);union.append(n)
            qrows.append({"query_index":qi,"query":q,"status":qstatus,"new_union_candidates":len(union)-before,"latency_seconds":time.perf_counter()-qs,"error":err})
        target=row["target"].casefold();hit=target in seen
        seed=row["episode_id"]+"\0"+row["strategy_id"]+"\0"+json.dumps(row["queries"],ensure_ascii=False)
        events.append({
          "episode_id":row["episode_id"],"source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API",
          "strategy_id":row["strategy_id"],"action_id":"LIVEV12:"+hashlib.sha256(seed.encode()).hexdigest()[:24],
          "sequence":seq,"queries":list(row["queries"]),"query_rows":qrows,"status":status,
          "candidate_ids":union,"candidate_pool_size":len(union),"expected_target_answer_key":target,
          "target_hit":hit,"target_rank_in_union":union.index(target)+1 if hit else None,
          "latency_seconds":time.perf_counter()-start,"request_count":len(row["queries"]),"errors":errors,
        })
    usable=[x for x in events if x["status"] in {"SUCCESS","PARTIAL_RETRYABLE"}]
    hits=[x for x in usable if x["target_hit"]]
    return {
      "schema":SCHEMA,"status":"LIVE_GITHUB_MISS_RECOVERY_COMPLETE","baseline_case_count":6,
      "usable_case_count":len(usable),"recovered_case_count":len(hits),
      "recovery_rate":len(hits)/len(usable) if usable else None,
      "recovered_episode_ids":[x["episode_id"] for x in hits],
      "residual_miss_episode_ids":[x["episode_id"] for x in usable if not x["target_hit"]],
      "events":events,"open_world_completeness_claim":False,"incremental_spend_usd":0,
      "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,
      "ownership_credit_delta":0,"execution_authority":False,"promotion_authority":False,
    }

if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
