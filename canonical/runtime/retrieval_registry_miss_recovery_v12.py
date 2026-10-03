#!/usr/bin/env python3
"""V12 live recovery for the twelve V11 non-GitHub misses."""
from __future__ import annotations
import hashlib,json,time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
from typing import Any,Mapping
from canonical.runtime import retrieval_live_provider_arena_v1 as base
from canonical.runtime import retrieval_live_provider_arena_v11 as v11

SCHEMA="PROJECT_BRAIN_RETRIEVAL_REGISTRY_MISS_RECOVERY_V12"
CASES=(
 {"episode_id":"NPM_PROCESS_EXEC","provider":"npm","source_id":"NPM_REGISTRY_SEARCH","group":"NPM_PUBLIC_REGISTRY","target":"execa","queries":["process execution for humans","javascript child process promise runner","child process command runner javascript"]},
 {"episode_id":"CRATE_ERROR","provider":"crates","source_id":"CRATES_IO_SEARCH","group":"CRATES_IO_PUBLIC_API","target":"anyhow","queries":["flexible concrete error type std error Rust","application error context Rust","convenient error handling Rust"]},
 {"episode_id":"CRATE_PARSER","provider":"crates","source_id":"CRATES_IO_SEARCH","group":"CRATES_IO_PUBLIC_API","target":"nom","queries":["byte oriented zero copy parser combinators Rust","streaming parser combinator Rust","binary parser combinator Rust"]},
 {"episode_id":"HF_TEXT2TEXT","provider":"huggingface","source_id":"HUGGINGFACE_MODEL_SEARCH","group":"HUGGINGFACE_HUB_API","target":"google/flan-t5-base","queries":["instruction finetuned T5 text to text","instruction tuned text2text transformer","text to text transfer transformer instruction model"]},
 {"episode_id":"MAVEN_COLLECTIONS","provider":"maven","source_id":"MAVEN_CENTRAL_SEARCH","group":"MAVEN_CENTRAL_API","target":"com.google.guava:guava","queries":["Java core libraries collections cache immutable collections","Java utilities collections caching concurrency","Java collections utilities cache primitives"]},
 {"episode_id":"MAVEN_JSON_BIND","provider":"maven","source_id":"MAVEN_CENTRAL_SEARCH","group":"MAVEN_CENTRAL_API","target":"com.fasterxml.jackson.core:jackson-databind","queries":["Java JSON databind object mapper serialization","Java JSON POJO data binding","Java object JSON mapping library"]},
 {"episode_id":"MAVEN_LOG_FACADE","provider":"maven","source_id":"MAVEN_CENTRAL_SEARCH","group":"MAVEN_CENTRAL_API","target":"org.slf4j:slf4j-api","queries":["Java simple logging facade API","Java logging abstraction facade","Java logging facade interface"]},
 {"episode_id":"NUGET_JSON","provider":"nuget","source_id":"NUGET_SEARCH","group":"NUGET_PUBLIC_API","target":"Newtonsoft.Json","queries":[".NET high performance JSON framework serializer","LINQ JSON .NET serialization converter","JSON object serializer .NET framework"]},
 {"episode_id":"NUGET_STRUCT_LOG","provider":"nuget","source_id":"NUGET_SEARCH","group":"NUGET_PUBLIC_API","target":"Serilog","queries":[".NET structured logging diagnostic events sinks","message templates structured logging .NET","structured event logging .NET sinks"]},
 {"episode_id":"RUBY_HTTP","provider":"rubygems","source_id":"RUBYGEMS_SEARCH","group":"RUBYGEMS_PUBLIC_API","target":"faraday","queries":["HTTP client library middleware adapters Ruby","Ruby HTTP client middleware connection adapters","HTTP networking client Ruby middleware"]},
 {"episode_id":"PHP_HTTP","provider":"packagist","source_id":"PACKAGIST_SEARCH","group":"PACKAGIST_PUBLIC_API","target":"guzzlehttp/guzzle","queries":["PHP PSR-7 HTTP client requests middleware","PHP HTTP client promises PSR requests","PHP HTTP request client middleware PSR"]},
 {"episode_id":"PHP_LOGGING","provider":"packagist","source_id":"PACKAGIST_SEARCH","group":"PACKAGIST_PUBLIC_API","target":"monolog/monolog","queries":["PHP PSR-3 logging handlers processors","PHP logging handlers formatters library","PSR logging handlers PHP"]},
)
PROVIDERS={"npm":base.npm,"crates":base.crates,"huggingface":base.huggingface,"maven":v11.maven,"nuget":v11.nuget,"rubygems":v11.rubygems,"packagist":v11.packagist}

def _n(x:Any)->str:return str(x or "").strip().casefold()

def validate():
    assert len(CASES)==12
    assert len({x["episode_id"] for x in CASES})==12
    for row in CASES:
        t=_n(row["target"])
        for q in row["queries"]:
            if t in _n(q):raise ValueError("TARGET_IDENTITY_LEAKED:"+row["episode_id"])

def _case(row:Mapping[str,Any],limit:int,timeout:float)->dict[str,Any]:
    union=[];seen=set();qrows=[];errors=[];status="SUCCESS";start=time.perf_counter()
    for qi,q in enumerate(row["queries"],1):
        qs=time.perf_counter()
        try: ids=PROVIDERS[row["provider"]](q,limit=limit,timeout=timeout); st="SUCCESS";err=None
        except Exception as exc:
            ids=[];st="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:400]}"
            status="PARTIAL_RETRYABLE" if union else "FAILED_RETRYABLE";errors.append(err)
        before=len(union)
        for x in ids:
            n=_n(x)
            if n and n not in seen:seen.add(n);union.append(n)
        qrows.append({"query_index":qi,"query":q,"status":st,"new_union_candidates":len(union)-before,"latency_seconds":time.perf_counter()-qs,"error":err})
    target=_n(row["target"]);hit=target in seen
    seed=row["episode_id"]+"\0"+json.dumps(row["queries"])
    return {"episode_id":row["episode_id"],"source_id":row["source_id"],"upstream_group":row["group"],"strategy_id":"MULTI_QUERY_RECOVERY_V12","provider":row["provider"],"action_id":"LIVEV12R:"+hashlib.sha256(seed.encode()).hexdigest()[:24],"queries":list(row["queries"]),"query_rows":qrows,"status":status,"candidate_ids":union,"candidate_pool_size":len(union),"expected_target_answer_key":target,"target_hit":hit,"target_rank_in_union":union.index(target)+1 if hit else None,"latency_seconds":time.perf_counter()-start,"request_count":len(row["queries"]),"errors":errors}

def run(*,limit:int=50,timeout:float=20.0)->dict[str,Any]:
    validate();groups=defaultdict(list)
    for row in CASES:groups[row["provider"]].append(row)
    events=[]
    def group(rows):return [_case(r,limit,timeout) for r in rows]
    with ThreadPoolExecutor(max_workers=min(7,len(groups))) as pool:
        for f in as_completed([pool.submit(group,rows) for _,rows in sorted(groups.items())]):events.extend(f.result())
    order={x["episode_id"]:i for i,x in enumerate(CASES)};events.sort(key=lambda x:order[x["episode_id"]])
    usable=[x for x in events if x["status"] in {"SUCCESS","PARTIAL_RETRYABLE"}];hits=[x for x in usable if x["target_hit"]]
    return {"schema":SCHEMA,"status":"LIVE_REGISTRY_MISS_RECOVERY_COMPLETE","baseline_case_count":12,"usable_case_count":len(usable),"recovered_case_count":len(hits),"recovery_rate":len(hits)/len(usable) if usable else None,"recovered_episode_ids":[x["episode_id"] for x in hits],"residual_miss_episode_ids":[x["episode_id"] for x in usable if not x["target_hit"]],"failed_episode_ids":[x["episode_id"] for x in events if x["status"]=="FAILED_RETRYABLE"],"events":events,"open_world_completeness_claim":False,"incremental_spend_usd":0,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,"execution_authority":False,"promotion_authority":False}

if __name__=="__main__":print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
