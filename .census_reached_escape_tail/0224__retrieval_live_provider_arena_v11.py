#!/usr/bin/env python3
"""Retrieval V11 difficulty-stratified live provider arena.

Expands the tiny V10 live labeled set into harder, more diverse live tasks:
- multilingual repository search,
- behavior-only repository search,
- npm/crates registries,
- provider-native Hugging Face filters,
- Maven Central, NuGet, RubyGems, and Packagist.

Answer-key identities are used only for scoring. They are forbidden from query
text. Misses are first-class evidence and remain UNKNOWN for the open world.
"""
from __future__ import annotations
import hashlib,json,time,urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any,Callable,Mapping

from canonical.runtime import retrieval_live_provider_arena_v1 as base
from canonical.runtime import retrieval_live_provider_arena_v2 as v2

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_ARENA_V11"

TASKS=(
 # Multilingual GitHub repository discovery.
 {"episode_id":"GITHUB_ZH_SEGMENTATION","difficulty":"MULTILINGUAL","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"NATIVE_LANGUAGE_BEHAVIOR_V11","provider":"github","query":"中文 分词 自然语言处理 Python","target":"fxsjy/jieba"},
 {"episode_id":"GITHUB_ZH_PINYIN","difficulty":"MULTILINGUAL","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"NATIVE_LANGUAGE_BEHAVIOR_V11","provider":"github","query":"汉字 拼音 转换 Python","target":"mozillazg/python-pinyin"},
 {"episode_id":"GITHUB_ZH_DOMAIN_SEGMENT","difficulty":"MULTILINGUAL","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"NATIVE_LANGUAGE_BEHAVIOR_V11","provider":"github","query":"中文 分词 多领域 Python","target":"lancopku/pkuseg-python"},
 {"episode_id":"GITHUB_RU_NLP","difficulty":"MULTILINGUAL","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"NATIVE_LANGUAGE_BEHAVIOR_V11","provider":"github","query":"обработка русского языка морфология именованные сущности Python","target":"natasha/natasha"},
 {"episode_id":"GITHUB_AR_TEXT","difficulty":"MULTILINGUAL","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"NATIVE_LANGUAGE_BEHAVIOR_V11","provider":"github","query":"معالجة النص العربي Python تشكيل حروف","target":"linuxscout/pyarabic"},

 # Behavior-only repository discovery.
 {"episode_id":"GITHUB_JSON_CLI","difficulty":"BEHAVIOR_ONLY","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"github","query":"command line JSON processor filter transform in:name,description,readme","target":"jqlang/jq"},
 {"episode_id":"GITHUB_FUZZY_FINDER","difficulty":"BEHAVIOR_ONLY","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"github","query":"interactive command line fuzzy finder terminal in:name,description,readme","target":"junegunn/fzf"},
 {"episode_id":"GITHUB_PY_LINTER","difficulty":"BEHAVIOR_ONLY","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"github","query":"fast Python linter formatter static analysis in:name,description,readme","target":"astral-sh/ruff"},
 {"episode_id":"GITHUB_PY_HTTP","difficulty":"BEHAVIOR_ONLY","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"github","query":"async Python HTTP client HTTP2 in:name,description,readme","target":"encode/httpx"},
 {"episode_id":"GITHUB_PY_CLI","difficulty":"BEHAVIOR_ONLY","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"github","query":"Python command line interface toolkit decorators parameters in:name,description,readme","target":"pallets/click"},

 # NPM.
 {"episode_id":"NPM_PROMISE_LIMIT","difficulty":"REGISTRY_BEHAVIOR","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"npm","query":"limit concurrent promise async operations","target":"p-limit"},
 {"episode_id":"NPM_FILE_WATCH","difficulty":"REGISTRY_BEHAVIOR","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"npm","query":"filesystem watcher node recursive files","target":"chokidar"},
 {"episode_id":"NPM_JSON_SCHEMA","difficulty":"REGISTRY_BEHAVIOR","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"npm","query":"JSON schema validator javascript","target":"ajv"},
 {"episode_id":"NPM_PROCESS_EXEC","difficulty":"REGISTRY_BEHAVIOR","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"npm","query":"execute child process promise shell command javascript","target":"execa"},

 # crates.io.
 {"episode_id":"CRATE_PARALLEL","difficulty":"REGISTRY_BEHAVIOR","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"crates","query":"data parallelism work stealing Rust","target":"rayon"},
 {"episode_id":"CRATE_ERROR","difficulty":"REGISTRY_BEHAVIOR","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"crates","query":"flexible application error handling Rust","target":"anyhow"},
 {"episode_id":"CRATE_HTTP","difficulty":"REGISTRY_BEHAVIOR","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"crates","query":"HTTP client async Rust","target":"reqwest"},
 {"episode_id":"CRATE_PARSER","difficulty":"REGISTRY_BEHAVIOR","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"crates","query":"parser combinator byte string Rust","target":"nom"},

 # Provider-native Hugging Face route.
 {"episode_id":"HF_ZERO_SHOT","difficulty":"PROVIDER_NATIVE_ENUM","source_id":"HUGGINGFACE_MODEL_PIPELINE_ENUM","upstream_group":"HUGGINGFACE_HUB_API","strategy_id":"PROVIDER_NATIVE_ENUM_V11","provider":"huggingface_pipeline","query":"zero-shot-classification","target":"facebook/bart-large-mnli"},
 {"episode_id":"HF_TEXT2TEXT","difficulty":"PROVIDER_NATIVE_ENUM","source_id":"HUGGINGFACE_MODEL_PIPELINE_ENUM","upstream_group":"HUGGINGFACE_HUB_API","strategy_id":"PROVIDER_NATIVE_ENUM_V11","provider":"huggingface_pipeline","query":"text2text-generation","target":"google/flan-t5-base"},

 # New registry ecosystems.
 {"episode_id":"MAVEN_COLLECTIONS","difficulty":"NEW_ECOSYSTEM","source_id":"MAVEN_CENTRAL_SEARCH","upstream_group":"MAVEN_CENTRAL_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"maven","query":"Java collections caching primitives utilities","target":"com.google.guava:guava"},
 {"episode_id":"MAVEN_JSON_BIND","difficulty":"NEW_ECOSYSTEM","source_id":"MAVEN_CENTRAL_SEARCH","upstream_group":"MAVEN_CENTRAL_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"maven","query":"Java JSON object data binding","target":"com.fasterxml.jackson.core:jackson-databind"},
 {"episode_id":"MAVEN_LOG_FACADE","difficulty":"NEW_ECOSYSTEM","source_id":"MAVEN_CENTRAL_SEARCH","upstream_group":"MAVEN_CENTRAL_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"maven","query":"Java logging facade API","target":"org.slf4j:slf4j-api"},

 {"episode_id":"NUGET_JSON","difficulty":"NEW_ECOSYSTEM","source_id":"NUGET_SEARCH","upstream_group":"NUGET_PUBLIC_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"nuget","query":".NET JSON serializer converter LINQ JSON","target":"Newtonsoft.Json"},
 {"episode_id":"NUGET_STRUCT_LOG","difficulty":"NEW_ECOSYSTEM","source_id":"NUGET_SEARCH","upstream_group":"NUGET_PUBLIC_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"nuget","query":".NET structured logging message templates sinks","target":"Serilog"},
 {"episode_id":"NUGET_RESILIENCE","difficulty":"NEW_ECOSYSTEM","source_id":"NUGET_SEARCH","upstream_group":"NUGET_PUBLIC_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"nuget","query":".NET retry circuit breaker resilience","target":"Polly"},

 {"episode_id":"RUBY_XML_HTML","difficulty":"NEW_ECOSYSTEM","source_id":"RUBYGEMS_SEARCH","upstream_group":"RUBYGEMS_PUBLIC_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"rubygems","query":"HTML XML parser Ruby","target":"nokogiri"},
 {"episode_id":"RUBY_HTTP","difficulty":"NEW_ECOSYSTEM","source_id":"RUBYGEMS_SEARCH","upstream_group":"RUBYGEMS_PUBLIC_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"rubygems","query":"HTTP client middleware Ruby","target":"faraday"},

 {"episode_id":"PHP_HTTP","difficulty":"NEW_ECOSYSTEM","source_id":"PACKAGIST_SEARCH","upstream_group":"PACKAGIST_PUBLIC_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"packagist","query":"PHP HTTP client PSR requests","target":"guzzlehttp/guzzle"},
 {"episode_id":"PHP_LOGGING","difficulty":"NEW_ECOSYSTEM","source_id":"PACKAGIST_SEARCH","upstream_group":"PACKAGIST_PUBLIC_API","strategy_id":"BEHAVIOR_ANCHOR_V11","provider":"packagist","query":"PHP logging library PSR-3 handlers","target":"monolog/monolog"},
)

def maven(query:str,*,limit:int=20,timeout:float=20.0,fetch:Callable[...,Any]=base._url_json)->list[str]:
    url="https://search.maven.org/solrsearch/select?"+urllib.parse.urlencode({"q":query,"rows":limit,"wt":"json"})
    obj=fetch(url,timeout=timeout)
    return [str(x.get("id")) for x in ((obj.get("response") or {}).get("docs") or []) if x.get("id")][:limit]

def nuget(query:str,*,limit:int=20,timeout:float=20.0,fetch:Callable[...,Any]=base._url_json)->list[str]:
    url="https://azuresearch-usnc.nuget.org/query?"+urllib.parse.urlencode({"q":query,"take":limit,"prerelease":"false"})
    obj=fetch(url,timeout=timeout)
    return [str(x.get("id")) for x in (obj.get("data") or []) if x.get("id")][:limit]

def rubygems(query:str,*,limit:int=20,timeout:float=20.0,fetch:Callable[...,Any]=base._url_json)->list[str]:
    url="https://rubygems.org/api/v1/search.json?"+urllib.parse.urlencode({"query":query})
    obj=fetch(url,timeout=timeout)
    return [str(x.get("name")) for x in (obj or []) if isinstance(x,Mapping) and x.get("name")][:limit]

def packagist(query:str,*,limit:int=20,timeout:float=20.0,fetch:Callable[...,Any]=base._url_json)->list[str]:
    url="https://packagist.org/search.json?"+urllib.parse.urlencode({"q":query,"per_page":limit})
    obj=fetch(url,timeout=timeout)
    return [str(x.get("name")) for x in (obj.get("results") or []) if x.get("name")][:limit]

PROVIDERS={
    "github":base.github,
    "npm":base.npm,
    "crates":base.crates,
    "huggingface_pipeline":v2.huggingface_pipeline,
    "maven":maven,
    "nuget":nuget,
    "rubygems":rubygems,
    "packagist":packagist,
}

def _norm(value:Any)->str:
    return str(value or "").strip().casefold()

def validate_tasks()->None:
    seen=set()
    for row in TASKS:
        key=(row["episode_id"],row["source_id"],row["strategy_id"])
        if key in seen:
            raise ValueError("DUPLICATE_TASK:"+repr(key))
        seen.add(key)
        q=_norm(row["query"])
        target=_norm(row["target"])
        if target and target in q:
            raise ValueError("TARGET_IDENTITY_LEAKED_IN_QUERY:"+row["episode_id"])
        basename=target.rsplit("/",1)[-1].rsplit(":",1)[-1]
        if len(basename)>=4 and basename in q:
            raise ValueError("TARGET_BASENAME_LEAKED_IN_QUERY:"+row["episode_id"])

def _run_provider_group(rows:list[tuple[int,Mapping[str,Any]]],*,limit:int,timeout:float)->list[dict[str,Any]]:
    events=[]
    for seq,row in rows:
        provider=PROVIDERS[row["provider"]]
        start=time.perf_counter()
        try:
            ids=provider(row["query"],limit=limit,timeout=timeout)
            status="SUCCESS"; error=None
        except Exception as exc:
            ids=[]; status="FAILED_RETRYABLE"; error=f"{type(exc).__name__}:{str(exc)[:500]}"
        latency=max(0.0,time.perf_counter()-start)
        normalized=[_norm(x) for x in ids if _norm(x)]
        target=_norm(row["target"])
        hit=target in normalized
        rank=normalized.index(target)+1 if hit else None
        seed=f"{row['episode_id']}\0{row['source_id']}\0{row['strategy_id']}\0{row['query']}"
        events.append({
            "episode_id":row["episode_id"],"difficulty":row["difficulty"],
            "source_id":row["source_id"],"upstream_group":row["upstream_group"],
            "strategy_id":row["strategy_id"],"provider":row["provider"],
            "query":row["query"],
            "action_id":"LIVEV11:"+hashlib.sha256(seed.encode()).hexdigest()[:24],
            "sequence":seq,"status":status,"candidate_ids":normalized,
            "expected_target_answer_key":target,"target_hit":hit,"target_rank":rank,
            "latency_seconds":latency,"request_count":1,"error":error,
        })
    return events

def run(*,limit:int=20,timeout:float=20.0)->dict[str,Any]:
    validate_tasks()
    grouped=defaultdict(list)
    for seq,row in enumerate(TASKS,1):
        grouped[row["provider"]].append((seq,row))
    events=[]
    with ThreadPoolExecutor(max_workers=max(1,min(8,len(grouped)))) as pool:
        futures=[
            pool.submit(_run_provider_group,rows,limit=limit,timeout=timeout)
            for _,rows in sorted(grouped.items())
        ]
        for fut in as_completed(futures):
            events.extend(fut.result())
    events.sort(key=lambda x:x["sequence"])

    successful=[x for x in events if x["status"]=="SUCCESS"]
    hits=[x for x in successful if x["target_hit"]]
    misses=[x for x in successful if not x["target_hit"]]

    def metrics(key:str)->dict[str,Any]:
        out={}
        for value in sorted({str(x[key]) for x in events}):
            rows=[x for x in events if str(x[key])==value]
            good=[x for x in rows if x["status"]=="SUCCESS"]
            hh=[x for x in good if x["target_hit"]]
            out[value]={
                "task_count":len(rows),
                "successful_task_count":len(good),
                "target_hit_count":len(hh),
                "target_recall_on_successful_tasks":len(hh)/len(good) if good else None,
                "mean_latency_seconds":sum(x["latency_seconds"] for x in good)/len(good) if good else None,
            }
        return out

    return {
        "schema":SCHEMA,
        "status":"LIVE_DIFFICULTY_STRATIFIED_PROVIDER_PROBE_COMPLETE",
        "task_count":len(events),
        "successful_task_count":len(successful),
        "failed_retryable_task_count":len(events)-len(successful),
        "target_hit_count":len(hits),
        "target_miss_count":len(misses),
        "target_recall_on_successful_tasks":len(hits)/len(successful) if successful else None,
        "difficulty_metrics":metrics("difficulty"),
        "provider_metrics":metrics("provider"),
        "source_metrics":metrics("source_id"),
        "miss_episode_ids":[x["episode_id"] for x in misses],
        "failed_episode_ids":[x["episode_id"] for x in events if x["status"]!="SUCCESS"],
        "events":events,
        "answer_key_identity_used_for_query_generation":False,
        "execution_model":"PROVIDER_GROUPS_PARALLEL__WITHIN_PROVIDER_SEQUENTIAL",
        "open_world_completeness_claim":False,
        "incremental_spend_usd":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "hard_rules":[
            "LIVE_NETWORK_RESULTS_ONLY",
            "ANSWER_KEY_IDENTITIES_ARE_SCORING_ONLY",
            "MISSES_ARE_DATA_NOT_FAILURES_TO_HIDE",
            "FAILED_PROVIDER_CALLS_REMAIN_RETRYABLE",
            "LIVE_TASK_RECALL_IS_NOT_OPEN_WORLD_COMPLETENESS",
            "EVERY_VERIFIED_LIVE_MISS_MUST_FEED_STRATEGY_IMPROVEMENT_OR_PERMANENT_REGRESSION",
        ],
    }

def main()->int:
    out=run()
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0 if out["successful_task_count"]>0 else 1

if __name__=="__main__":
    raise SystemExit(main())
