#!/usr/bin/env python3
"""Live provider strategy arena V2.

A/B counterpart to RAW_BEHAVIOR_V1. Uses behavior-derived compressed anchors and
provider-native structured routes without inserting answer-key identities into
queries. Hugging Face tasks use pipeline-tag enumeration rather than lexical
model-name search, explicitly testing zero-lexical-bridge recovery.
"""
from __future__ import annotations
import hashlib,json,time,urllib.parse
from typing import Any,Callable,Mapping
from canonical.runtime import retrieval_live_provider_arena_v1 as base

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_ARENA_V2"

TASKS=(
 {"episode_id":"SOFTWARE_OCR_ENGINE","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"ANCHOR_COMPRESSED_V2","provider":"github","query":"OCR engine in:name,description,readme","target":"tesseract-ocr/tesseract"},
 {"episode_id":"SOFTWARE_COMPUTER_VISION","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"ANCHOR_COMPRESSED_V2","provider":"github","query":"computer vision library in:name,description,readme","target":"opencv/opencv"},
 {"episode_id":"SOFTWARE_MULTILINGUAL_NLP","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"ANCHOR_COMPRESSED_V2","provider":"github","query":"NLP tokenization parsing in:name,description,readme","target":"stanfordnlp/stanza"},

 {"episode_id":"PACKAGE_TYPED_JS","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY","strategy_id":"ANCHOR_COMPRESSED_V2","provider":"npm","query":"typed superset javascript","target":"typescript"},
 {"episode_id":"PACKAGE_JS_LINT","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY","strategy_id":"ANCHOR_COMPRESSED_V2","provider":"npm","query":"javascript lint","target":"eslint"},
 {"episode_id":"PACKAGE_CODE_FORMAT","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY","strategy_id":"ANCHOR_COMPRESSED_V2","provider":"npm","query":"code formatter javascript","target":"prettier"},

 {"episode_id":"PACKAGE_RUST_SERIALIZE","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API","strategy_id":"ANCHOR_COMPRESSED_V2","provider":"crates","query":"serialize deserialize","target":"serde"},
 {"episode_id":"PACKAGE_RUST_ASYNC","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API","strategy_id":"ANCHOR_COMPRESSED_V2","provider":"crates","query":"async runtime","target":"tokio"},
 {"episode_id":"PACKAGE_RUST_CLI","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API","strategy_id":"ANCHOR_COMPRESSED_V2","provider":"crates","query":"command line parser","target":"clap"},

 {"episode_id":"MODEL_SENTENCE_EMBEDDING","source_id":"HUGGINGFACE_MODEL_PIPELINE_ENUM","upstream_group":"HUGGINGFACE_HUB_API","strategy_id":"PROVIDER_NATIVE_ENUM_V2","provider":"huggingface_pipeline","query":"sentence-similarity","target":"sentence-transformers/all-MiniLM-L6-v2"},
 {"episode_id":"MODEL_SPEECH_RECOGNITION","source_id":"HUGGINGFACE_MODEL_PIPELINE_ENUM","upstream_group":"HUGGINGFACE_HUB_API","strategy_id":"PROVIDER_NATIVE_ENUM_V2","provider":"huggingface_pipeline","query":"automatic-speech-recognition","target":"openai/whisper-large-v3"},

 {"episode_id":"PAPER_BERT","source_id":"CROSSREF_TITLE_SEARCH","upstream_group":"CROSSREF_PUBLIC_API","strategy_id":"PROVIDER_NATIVE_TITLE_V2","provider":"crossref_title","query":"bidirectional transformers language understanding pretraining","target":"10.18653/v1/N19-1423"},
 {"episode_id":"PAPER_RESNET","source_id":"CROSSREF_TITLE_SEARCH","upstream_group":"CROSSREF_PUBLIC_API","strategy_id":"PROVIDER_NATIVE_TITLE_V2","provider":"crossref_title","query":"deep residual learning image recognition","target":"10.1109/CVPR.2016.90"},
 {"episode_id":"PAPER_BERT","source_id":"OPENALEX_WORK_SEARCH","upstream_group":"OPENALEX_PUBLIC_API","strategy_id":"TITLE_ANCHOR_V2","provider":"openalex","query":"pre-training deep bidirectional transformers language understanding","target":"10.18653/v1/N19-1423"},
 {"episode_id":"PAPER_RESNET","source_id":"OPENALEX_WORK_SEARCH","upstream_group":"OPENALEX_PUBLIC_API","strategy_id":"TITLE_ANCHOR_V2","provider":"openalex","query":"deep residual learning image recognition","target":"10.1109/CVPR.2016.90"},
)

def huggingface_pipeline(query:str,*,limit:int=10,timeout:float=20.0,fetch:Callable[...,Any]=base._url_json)->list[str]:
    url="https://huggingface.co/api/models?"+urllib.parse.urlencode({"pipeline_tag":query,"sort":"downloads","direction":"-1","limit":limit,"full":"false"})
    obj=fetch(url,timeout=timeout)
    return [str(x.get("id") or x.get("modelId")) for x in (obj or []) if (x.get("id") or x.get("modelId"))][:limit]

def crossref_title(query:str,*,limit:int=10,timeout:float=20.0,fetch:Callable[...,Any]=base._url_json)->list[str]:
    url="https://api.crossref.org/works?"+urllib.parse.urlencode({"query.title":query,"rows":limit,"select":"DOI,title"})
    obj=fetch(url,timeout=timeout)
    return [base._doi(x.get("DOI")) for x in ((obj.get("message") or {}).get("items") or []) if base._doi(x.get("DOI"))][:limit]

PROVIDERS={
 "github":base.github,"npm":base.npm,"crates":base.crates,
 "huggingface_pipeline":huggingface_pipeline,
 "crossref_title":crossref_title,
 "openalex":base.openalex,
}

def validate_tasks()->None:
    seen=set()
    for row in TASKS:
        key=(row["episode_id"],row["source_id"],row["strategy_id"])
        if key in seen: raise ValueError("DUPLICATE_TASK:"+repr(key))
        seen.add(key)
        q=str(row["query"]).casefold(); target=str(row["target"]).casefold()
        if target in q: raise ValueError("TARGET_IDENTITY_LEAKED_IN_QUERY:"+row["episode_id"])

def run(*,limit:int=10,timeout:float=20.0)->dict[str,Any]:
    validate_tasks()
    events=[]
    for seq,row in enumerate(TASKS,1):
        provider=PROVIDERS[row["provider"]]
        start=time.perf_counter()
        try:
            ids=provider(row["query"],limit=limit,timeout=timeout)
            status="SUCCESS"; error=None
        except Exception as exc:
            ids=[]; status="FAILED_RETRYABLE"; error=f"{type(exc).__name__}:{str(exc)[:400]}"
        latency=max(0.0,time.perf_counter()-start)
        scholarly=row["provider"] in {"crossref_title","openalex"}
        target=base._doi(row["target"]) if scholarly else row["target"]
        normalized=[base._doi(x) if scholarly else str(x) for x in ids]
        hit=target in normalized
        rank=normalized.index(target)+1 if hit else None
        seed=f"{row['episode_id']}\0{row['source_id']}\0{row['strategy_id']}\0{row['query']}"
        events.append({
          "episode_id":row["episode_id"],"source_id":row["source_id"],
          "upstream_group":row["upstream_group"],"strategy_id":row["strategy_id"],
          "action_id":"LIVEV2:"+hashlib.sha256(seed.encode()).hexdigest()[:24],
          "sequence":seq,"provider":row["provider"],"query":row["query"],
          "status":status,"candidate_ids":normalized,
          "expected_target_answer_key":target,"target_hit":hit,"target_rank":rank,
          "latency_seconds":latency,"request_count":1,"error":error,
        })
    ok=[x for x in events if x["status"]=="SUCCESS"]; hits=[x for x in ok if x["target_hit"]]
    route_metrics={}
    for key in sorted({(x["source_id"],x["strategy_id"]) for x in events}):
        rows=[x for x in events if (x["source_id"],x["strategy_id"])==key]
        good=[x for x in rows if x["status"]=="SUCCESS"]; hh=[x for x in good if x["target_hit"]]
        route_metrics[f"{key[0]}::{key[1]}"]={
          "task_count":len(rows),"success_count":len(good),"target_hit_count":len(hh),
          "target_recall_on_successful_tasks":len(hh)/len(good) if good else None,
          "mean_latency_seconds":sum(x["latency_seconds"] for x in good)/len(good) if good else None,
        }
    return {
      "schema":SCHEMA,"status":"LIVE_PROVIDER_STRATEGY_PROBE_COMPLETE",
      "task_count":len(events),"successful_task_count":len(ok),"target_hit_count":len(hits),
      "target_recall_on_successful_tasks":len(hits)/len(ok) if ok else None,
      "route_metrics":route_metrics,"events":events,
      "open_world_completeness_claim":False,"incremental_spend_usd":0,
      "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,
      "ownership_credit_delta":0,"execution_authority":False,"promotion_authority":False,
      "hard_rules":[
        "LIVE_NETWORK_RESULTS_ONLY",
        "ANSWER_KEY_IDENTITIES_ARE_NOT_QUERY_TERMS",
        "ROUTE_EQUALS_PROVIDER_X_STRATEGY_NOT_PROVIDER_ALONE",
        "PROVIDER_NATIVE_ENUMERATION_IS_ALLOWED_WHEN_BEHAVIOR_MAPS_TO_AN_AUTHORITATIVE_BOUNDED_FILTER",
        "FAILED_PROVIDER_CALLS_REMAIN_RETRYABLE",
        "TARGET_HIT_IS_FINITE_TASK_RECALL_NOT_OPEN_WORLD_COMPLETENESS",
      ],
    }

def main()->int:
    out=run(); print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0 if out["successful_task_count"]>0 else 1

if __name__=="__main__": raise SystemExit(main())
