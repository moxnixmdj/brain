#!/usr/bin/env python3
"""Live multi-provider retrieval calibration arena V1.

Executes behavior-only queries against independent public provider APIs.
Expected identities are answer-key only and are never inserted into queries.
Results are observations, not completeness proof. Provider successes may later
be admitted to the append-only live event ledger only after an independent
runner receipt binds the exact live output.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any, Callable, Mapping

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_ARENA_V1"
USER_AGENT="ProjectBrain-RetrievalCalibration/1.0"

TASKS=(
    {"episode_id":"SOFTWARE_OCR_ENGINE","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API",
     "provider":"github","query":"open source optical character recognition engine","target":"tesseract-ocr/tesseract"},
    {"episode_id":"SOFTWARE_COMPUTER_VISION","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API",
     "provider":"github","query":"general computer vision image processing library","target":"opencv/opencv"},
    {"episode_id":"SOFTWARE_MULTILINGUAL_NLP","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API",
     "provider":"github","query":"multilingual tokenization named entity parsing toolkit","target":"stanfordnlp/stanza"},

    {"episode_id":"PACKAGE_TYPED_JS","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY",
     "provider":"npm","query":"typed javascript compiler language tooling","target":"typescript"},
    {"episode_id":"PACKAGE_JS_LINT","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY",
     "provider":"npm","query":"javascript lint static analysis code quality","target":"eslint"},
    {"episode_id":"PACKAGE_CODE_FORMAT","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY",
     "provider":"npm","query":"opinionated code formatter javascript","target":"prettier"},

    {"episode_id":"PACKAGE_RUST_SERIALIZE","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API",
     "provider":"crates","query":"serialization framework rust","target":"serde"},
    {"episode_id":"PACKAGE_RUST_ASYNC","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API",
     "provider":"crates","query":"asynchronous runtime networking rust","target":"tokio"},
    {"episode_id":"PACKAGE_RUST_CLI","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API",
     "provider":"crates","query":"command line argument parser rust","target":"clap"},

    {"episode_id":"MODEL_SENTENCE_EMBEDDING","source_id":"HUGGINGFACE_MODEL_SEARCH","upstream_group":"HUGGINGFACE_HUB_API",
     "provider":"huggingface","query":"compact sentence embedding transformer","target":"sentence-transformers/all-MiniLM-L6-v2"},
    {"episode_id":"MODEL_SPEECH_RECOGNITION","source_id":"HUGGINGFACE_MODEL_SEARCH","upstream_group":"HUGGINGFACE_HUB_API",
     "provider":"huggingface","query":"multilingual automatic speech recognition transformer","target":"openai/whisper-large-v3"},

    {"episode_id":"PAPER_BERT","source_id":"CROSSREF_WORK_SEARCH","upstream_group":"CROSSREF_PUBLIC_API",
     "provider":"crossref","query":"bidirectional transformer pretraining language understanding","target":"10.18653/v1/N19-1423"},
    {"episode_id":"PAPER_RESNET","source_id":"CROSSREF_WORK_SEARCH","upstream_group":"CROSSREF_PUBLIC_API",
     "provider":"crossref","query":"deep residual learning image recognition neural network","target":"10.1109/CVPR.2016.90"},
    {"episode_id":"PAPER_BERT","source_id":"OPENALEX_WORK_SEARCH","upstream_group":"OPENALEX_PUBLIC_API",
     "provider":"openalex","query":"bidirectional transformer pretraining language understanding","target":"10.18653/v1/N19-1423"},
    {"episode_id":"PAPER_RESNET","source_id":"OPENALEX_WORK_SEARCH","upstream_group":"OPENALEX_PUBLIC_API",
     "provider":"openalex","query":"deep residual learning image recognition neural network","target":"10.1109/CVPR.2016.90"},
)

def _canon(x:Any)->str:
    return " ".join(str(x or "").strip().split())

def _doi(x:Any)->str:
    s=_canon(x).lower()
    for prefix in ("https://doi.org/","http://doi.org/","doi:"):
        if s.startswith(prefix):
            s=s[len(prefix):]
    return s

def _url_json(url:str, *, timeout:float=20.0, headers:Mapping[str,str]|None=None)->Any:
    h={"User-Agent":USER_AGENT,"Accept":"application/json"}
    if headers:
        h.update({str(k):str(v) for k,v in headers.items()})
    req=urllib.request.Request(url,headers=h)
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def github(query:str, *, limit:int=10, timeout:float=20.0, fetch:Callable[...,Any]=_url_json)->list[str]:
    url="https://api.github.com/search/repositories?"+urllib.parse.urlencode({"q":query,"per_page":limit,"sort":"best-match"})
    headers={}
    token=os.environ.get("GITHUB_TOKEN","").strip()
    if token:
        headers["Authorization"]="Bearer "+token
        headers["X-GitHub-Api-Version"]="2022-11-28"
    obj=fetch(url,timeout=timeout,headers=headers)
    return [str(x.get("full_name")) for x in (obj.get("items") or []) if x.get("full_name")][:limit]

def npm(query:str, *, limit:int=10, timeout:float=20.0, fetch:Callable[...,Any]=_url_json)->list[str]:
    url="https://registry.npmjs.org/-/v1/search?"+urllib.parse.urlencode({"text":query,"size":limit})
    obj=fetch(url,timeout=timeout)
    return [str((x.get("package") or {}).get("name")) for x in (obj.get("objects") or []) if (x.get("package") or {}).get("name")][:limit]

def crates(query:str, *, limit:int=10, timeout:float=20.0, fetch:Callable[...,Any]=_url_json)->list[str]:
    url="https://crates.io/api/v1/crates?"+urllib.parse.urlencode({"q":query,"per_page":limit})
    obj=fetch(url,timeout=timeout)
    return [str(x.get("id") or x.get("name")) for x in (obj.get("crates") or []) if (x.get("id") or x.get("name"))][:limit]

def huggingface(query:str, *, limit:int=10, timeout:float=20.0, fetch:Callable[...,Any]=_url_json)->list[str]:
    url="https://huggingface.co/api/models?"+urllib.parse.urlencode({"search":query,"limit":limit,"full":"false"})
    obj=fetch(url,timeout=timeout)
    return [str(x.get("id") or x.get("modelId")) for x in (obj or []) if (x.get("id") or x.get("modelId"))][:limit]

def crossref(query:str, *, limit:int=10, timeout:float=20.0, fetch:Callable[...,Any]=_url_json)->list[str]:
    url="https://api.crossref.org/works?"+urllib.parse.urlencode({"query":query,"rows":limit,"select":"DOI,title"})
    obj=fetch(url,timeout=timeout)
    items=((obj.get("message") or {}).get("items") or [])
    return [_doi(x.get("DOI")) for x in items if _doi(x.get("DOI"))][:limit]

def openalex(query:str, *, limit:int=10, timeout:float=20.0, fetch:Callable[...,Any]=_url_json)->list[str]:
    url="https://api.openalex.org/works?"+urllib.parse.urlencode({"search":query,"per-page":limit})
    obj=fetch(url,timeout=timeout)
    out=[]
    for x in (obj.get("results") or []):
        doi=_doi(x.get("doi"))
        if doi:
            out.append(doi)
    return out[:limit]

PROVIDERS={"github":github,"npm":npm,"crates":crates,"huggingface":huggingface,"crossref":crossref,"openalex":openalex}

def validate_tasks()->None:
    seen=set()
    for row in TASKS:
        key=(row["episode_id"],row["source_id"])
        if key in seen:
            raise ValueError("DUPLICATE_EPISODE_SOURCE_TASK:"+repr(key))
        seen.add(key)
        q=_canon(row["query"]).casefold()
        target=_canon(row["target"]).casefold()
        # The exact answer-key identity must not simply be the query.
        if target and target in q:
            raise ValueError("TARGET_IDENTITY_LEAKED_IN_QUERY:"+row["episode_id"])

def run(*, limit:int=10, timeout:float=20.0)->dict[str,Any]:
    validate_tasks()
    events=[]
    for sequence,row in enumerate(TASKS,1):
        provider=PROVIDERS[row["provider"]]
        start=time.perf_counter()
        try:
            ids=provider(row["query"],limit=limit,timeout=timeout)
            status="SUCCESS"
            error=None
        except Exception as exc:
            ids=[]
            status="FAILED_RETRYABLE"
            error=f"{type(exc).__name__}:{str(exc)[:400]}"
        latency=max(0.0,time.perf_counter()-start)
        target=_doi(row["target"]) if row["provider"] in {"crossref","openalex"} else row["target"]
        normalized=[_doi(x) if row["provider"] in {"crossref","openalex"} else str(x) for x in ids]
        hit=target in normalized
        rank=(normalized.index(target)+1) if hit else None
        action_seed=f"{row['episode_id']}\0{row['source_id']}\0{row['query']}"
        events.append({
            "episode_id":row["episode_id"],
            "source_id":row["source_id"],
            "upstream_group":row["upstream_group"],
            "action_id":"LIVE:"+hashlib.sha256(action_seed.encode()).hexdigest()[:24],
            "sequence":sequence,
            "provider":row["provider"],
            "query":row["query"],
            "status":status,
            "candidate_ids":normalized,
            "expected_target_answer_key":target,
            "target_hit":hit,
            "target_rank":rank,
            "latency_seconds":latency,
            "request_count":1,
            "error":error,
        })
    successes=[x for x in events if x["status"]=="SUCCESS"]
    hits=[x for x in successes if x["target_hit"]]
    by_source={}
    for src in sorted({x["source_id"] for x in events}):
        rows=[x for x in events if x["source_id"]==src]
        ok=[x for x in rows if x["status"]=="SUCCESS"]
        sh=[x for x in ok if x["target_hit"]]
        by_source[src]={
            "task_count":len(rows),
            "success_count":len(ok),
            "target_hit_count":len(sh),
            "target_recall_on_successful_tasks":len(sh)/len(ok) if ok else None,
            "mean_latency_seconds":sum(x["latency_seconds"] for x in ok)/len(ok) if ok else None,
        }
    return {
        "schema":SCHEMA,
        "status":"LIVE_PROVIDER_PROBE_COMPLETE",
        "task_count":len(events),
        "successful_task_count":len(successes),
        "target_hit_count":len(hits),
        "target_recall_on_successful_tasks":len(hits)/len(successes) if successes else None,
        "source_metrics":by_source,
        "events":events,
        "open_world_completeness_claim":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "hard_rules":[
            "LIVE_NETWORK_RESULTS_ONLY",
            "EXPECTED_IDENTITIES_ARE_ANSWER_KEY_ONLY_AND_ARE_NOT_QUERY_TERMS",
            "FAILED_PROVIDER_CALLS_REMAIN_RETRYABLE",
            "TARGET_HIT_IS_FINITE_TASK_RECALL_NOT_OPEN_WORLD_COMPLETENESS",
            "LIVE_OUTPUT_MUST_BE_INDEPENDENTLY_RECEIPT_BOUND_BEFORE_LEDGER_ADMISSION",
            "NO_PROVIDER_RESULT_SELF_GRANTS_ACCEPTANCE_OR_CAPABILITY_CREDIT",
        ],
    }

def main()->int:
    out=run()
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0 if out["successful_task_count"]>0 else 1

if __name__=="__main__":
    raise SystemExit(main())
