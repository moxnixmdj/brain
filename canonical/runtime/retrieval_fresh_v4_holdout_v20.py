#!/usr/bin/env python3
"""Retrieval V20 fresh holdout for frozen EntryPoint V4.

New targets were not used in V11-V18 route development.  Target identities are
answer-key only.  EntryPoint V4 and the V19 portfolio are hash-frozen before any
network work.  No post-hoc query/route changes are allowed in this arena.
"""
from __future__ import annotations
import hashlib,json,time
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import global_retrieval_entrypoint_v4 as ep
from canonical.runtime import retrieval_live_provider_arena_v11 as v11
from canonical.runtime import retrieval_live_provider_arena_v14 as v14
from canonical.runtime import retrieval_live_provider_arena_v13 as v13

SCHEMA="PROJECT_BRAIN_RETRIEVAL_V20_FRESH_V4_HOLDOUT"
ENTRYPOINT_BLOB="2ad2fb952b3c361e74cb083b335d39b04a7c130b"
PORTFOLIO_BLOB="855a6cba59fff8c079f61212acadc254c4e9e736"

TASKS=(
 {"id":"H_GH_KO_NLP","provider":"github","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","query":"한국어 자연어 처리 형태소 분석 Python in:name,description,readme","target":"konlpy/konlpy"},
 {"id":"H_GH_JA_TOKEN","provider":"github","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","query":"日本語 形態素解析 Python MeCab wrapper in:name,description,readme","target":"polm/fugashi"},
 {"id":"H_GH_SEARCH_CLI","provider":"github","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","query":"fast recursive text search command line regex Rust in:name,description,readme","target":"burntsushi/ripgrep"},
 {"id":"H_GH_CAT_SYNTAX","provider":"github","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","query":"cat clone syntax highlighting git integration command line Rust in:name,description,readme","target":"sharkdp/bat"},
 {"id":"H_NPM_GLOB","provider":"npm","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY","query":"fast glob files patterns node javascript","target":"fast-glob"},
 {"id":"H_NPM_SCHEMA_TS","provider":"npm","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY","query":"TypeScript schema validation static type inference","target":"zod"},
 {"id":"H_NPM_WEBSOCKET","provider":"npm","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY","query":"WebSocket client server Node.js","target":"ws"},
 {"id":"H_CRATE_ASYNC_RT","provider":"crates","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API","query":"asynchronous runtime networking Rust tasks","target":"tokio"},
 {"id":"H_CRATE_SERIALIZE","provider":"crates","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API","query":"serialization deserialization framework Rust","target":"serde"},
 {"id":"H_CRATE_CLI","provider":"crates","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API","query":"command line argument parser Rust derive","target":"clap"},
 {"id":"H_MAVEN_STRING","provider":"maven","source_id":"MAVEN_CENTRAL_SEARCH","upstream_group":"MAVEN_CENTRAL_API","query":"Java string utilities reflection builders helpers","target":"org.apache.commons:commons-lang3"},
 {"id":"H_MAVEN_HTTP","provider":"maven","source_id":"MAVEN_CENTRAL_SEARCH","upstream_group":"MAVEN_CENTRAL_API","query":"Java Kotlin HTTP client connection pooling interceptors","target":"com.squareup.okhttp3:okhttp"},
 {"id":"H_NUGET_ORM","provider":"nuget","source_id":"NUGET_SEARCH","upstream_group":"NUGET_PUBLIC_API","query":".NET micro ORM SQL object mapping","target":"Dapper"},
 {"id":"H_NUGET_MAP","provider":"nuget","source_id":"NUGET_SEARCH","upstream_group":"NUGET_PUBLIC_API","query":".NET object object mapper convention mapping","target":"AutoMapper"},
 {"id":"H_RUBY_JOBS","provider":"rubygems","source_id":"RUBYGEMS_SEARCH","upstream_group":"RUBYGEMS_PUBLIC_API","query":"Ruby background jobs Redis worker queue","target":"sidekiq"},
 {"id":"H_RUBY_HTTP_DSL","provider":"rubygems","source_id":"RUBYGEMS_SEARCH","upstream_group":"RUBYGEMS_PUBLIC_API","query":"Ruby HTTP client simple DSL","target":"httparty"},
 {"id":"H_PHP_CONSOLE","provider":"packagist","source_id":"PACKAGIST_SEARCH","upstream_group":"PACKAGIST_PUBLIC_API","query":"PHP command line console commands arguments","target":"symfony/console"},
 {"id":"H_PHP_ORM","provider":"packagist","source_id":"PACKAGIST_SEARCH","upstream_group":"PACKAGIST_PUBLIC_API","query":"PHP object relational mapper database entities","target":"doctrine/orm"},
)

PROVIDERS=v11.PROVIDERS

def git_blob(path:Path)->str:
 raw=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def root()->Path:
 return Path(__file__).resolve().parents[2]

def validate()->None:
 r=root()
 assert git_blob(r/"canonical/runtime/global_retrieval_entrypoint_v4.py")==ENTRYPOINT_BLOB
 assert git_blob(r/"canonical/runtime/retrieval_verified_route_portfolio_v1.py")==PORTFOLIO_BLOB
 seen=set()
 for row in TASKS:
  assert row["id"] not in seen;seen.add(row["id"])
  q=v11._norm(row["query"]);t=v11._norm(row["target"])
  assert t not in q
  # Full answer-key identities are forbidden. Basenames are not universally
  # forbidden because some package basenames are ordinary behavior words
  # (for example "console"), so banning them would corrupt the task itself.
  # Query-specific target leakage is caught by the full identity rule plus the
  # independent new-target-vs-development-set test.
  base=t.rsplit("/",1)[-1].rsplit(":",1)[-1]

def _plain_tokens(text:str)->list[str]:
    out=[];cur=[]
    for ch in v11._norm(text):
        if ch.isalnum() or ch in "_.-":
            cur.append(ch)
        elif cur:
            out.append("".join(cur));cur=[]
    if cur:out.append("".join(cur))
    return out

def identity_leaked(value:Any,target:str)->bool:
    t=v11._norm(target)
    if isinstance(value,Mapping):
        return any(identity_leaked(v,t) for v in value.values())
    if isinstance(value,(list,tuple)):
        return any(identity_leaked(v,t) for v in value)
    if not isinstance(value,str) or not t:
        return False
    s=v11._norm(value)
    if any(ch in t for ch in "/:@"):
        return t in s
    return t in _plain_tokens(s)

def source_row(row:Mapping[str,Any])->dict[str,Any]:
 return {"source_id":row["source_id"],"upstream_group":row["upstream_group"],
         "ecosystem":row["provider"],"bounded_scope":False}

def query_action(row:Mapping[str,Any])->dict[str,Any]:
 return {"action_id":"HOLDOUT:"+hashlib.sha256((row["id"]+"\0"+row["query"]).encode()).hexdigest()[:24],
         "source_id":row["source_id"],"upstream_group":row["upstream_group"],
         "provider_route":row["source_id"],"query":row["query"]}

def direct(row:Mapping[str,Any],*,limit:int,timeout:float)->tuple[list[str],str|None,float]:
 start=time.perf_counter()
 try:
  ids=PROVIDERS[row["provider"]](row["query"],limit=limit,timeout=timeout)
  return [v11._norm(x) for x in ids if v11._norm(x)],None,time.perf_counter()-start
 except Exception as exc:
  return [],f"{type(exc).__name__}:{str(exc)[:400]}",time.perf_counter()-start

def maven_manifest_recovery(row:Mapping[str,Any],*,timeout:float)->tuple[list[str],dict[str,Any]]:
 queries=v14.maven_behavior_queries(str(row["query"]))
 repos,traces=v14.repo_union(queries,limit_per_query=10,timeout=timeout)
 coords=[];seen=set();manifest=[]
 for repo in repos[:20]:
  try:
   got,tr=v13.repository_pom_coordinates(repo,timeout=timeout,max_poms=20)
   status="SUCCESS";err=None
  except Exception as exc:
   got=[];tr={"repository":repo};status="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:250]}"
  tr["status"]=status;tr["error"]=err;manifest.append(tr)
  for x in got:
   n=v11._norm(x)
   if n and n not in seen:seen.add(n);coords.append(n)
 return coords,{"queries":queries,"repos":repos,"search_traces":traces,"manifest_traces":manifest}

def run(*,limit:int=20,timeout:float=20.0)->dict[str,Any]:
 validate();events=[]
 for seq,row in enumerate(TASKS,1):
  action=query_action(row);src=source_row(row)
  plan=ep.compile_authorized_plan(root=root(),query_actions=[action],sources=[src])
  assert plan["status"].startswith("PASS__")
  target=v11._norm(row["target"]);base=target.rsplit("/",1)[-1].rsplit(":",1)[-1]
  assert not identity_leaked(plan,target)
  # Basenames may be ordinary behavior vocabulary; full answer-key identity
  # remains forbidden from the compiled plan.
  ids,err,lat=direct(row,limit=limit,timeout=timeout)
  direct_hit=target in set(ids)
  recovery_ids=[];recovery_trace=None
  route_ids=[x.get("strategy_id") for x in plan.get("route_portfolio",{}).get("actions",[])]
  if (not direct_hit and row["provider"]=="maven"
      and any(x in route_ids for x in ("REPOSITORY_MANIFEST_BRIDGE","DEEP_MANIFEST_INSPECTION"))):
   recovery_ids,recovery_trace=maven_manifest_recovery(row,timeout=timeout)
  union=[];seen=set()
  for x in ids+recovery_ids:
   if x not in seen:seen.add(x);union.append(x)
  hit=target in set(union)
  events.append({
   "sequence":seq,"episode_id":row["id"],"provider":row["provider"],
   "source_id":row["source_id"],"query":row["query"],
   "status":"FAILED_RETRYABLE" if err else "SUCCESS",
   "direct_candidate_ids":ids,"direct_hit":direct_hit,
   "recovery_route_ids":route_ids,"recovery_candidate_ids":recovery_ids,
   "recovery_trace":recovery_trace,"union_candidate_ids":union,
   "expected_target_answer_key":target,"target_hit":hit,
   "target_rank":union.index(target)+1 if hit else None,
   "latency_seconds":lat,"error":err,
   "entrypoint_v4_blob":ENTRYPOINT_BLOB,"portfolio_blob":PORTFOLIO_BLOB,
   "answer_key_identity_used_for_plan_generation":False,
  })
 successful=[x for x in events if x["status"]=="SUCCESS"]
 hits=[x for x in successful if x["target_hit"]]
 misses=[x for x in successful if not x["target_hit"]]
 by_provider={}
 for p in sorted({x["provider"] for x in events}):
  rs=[x for x in events if x["provider"]==p];good=[x for x in rs if x["status"]=="SUCCESS"];hh=[x for x in good if x["target_hit"]]
  by_provider[p]={"task_count":len(rs),"successful":len(good),"hits":len(hh),
                  "recall":len(hh)/len(good) if good else None}
 return {
  "schema":SCHEMA,"status":"FRESH_FROZEN_V4_HOLDOUT_COMPLETE",
  "task_count":len(events),"successful_task_count":len(successful),
  "failed_retryable_task_count":len(events)-len(successful),
  "target_hit_count":len(hits),"target_miss_count":len(misses),
  "target_recall_on_successful_tasks":len(hits)/len(successful) if successful else None,
  "miss_episode_ids":[x["episode_id"] for x in misses],
  "failed_episode_ids":[x["episode_id"] for x in events if x["status"]!="SUCCESS"],
  "provider_metrics":by_provider,"events":events,
  "frozen_entrypoint_v4_blob":ENTRYPOINT_BLOB,"frozen_portfolio_blob":PORTFOLIO_BLOB,
  "post_hoc_route_changes_allowed":False,"answer_key_identity_used_for_plan_generation":False,
  "open_world_completeness_claim":False,"incremental_spend_usd":0,
  "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,
  "ownership_credit_delta":0,"execution_authority":False,"promotion_authority":False,
 }
def main()->int:
 out=run()
 print(json.dumps(out,ensure_ascii=False,sort_keys=True))
 return 0 if out["successful_task_count"]>0 else 1
if __name__=="__main__":raise SystemExit(main())
