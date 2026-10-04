#!/usr/bin/env python3
"""Fresh answer-key-blind live holdout for frozen global retrieval entrypoint V4."""
from __future__ import annotations
import hashlib,json,time
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import global_retrieval_entrypoint_v4 as entrypoint
from canonical.runtime import retrieval_live_provider_arena_v11 as p

SCHEMA="PROJECT_BRAIN_RETRIEVAL_FRESH_HOLDOUT_V20"

TASKS=(
 {"id":"H_GH_RICH","provider":"github","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","query":"Python terminal text styling tables markdown syntax highlighting","target":"textualize/rich"},
 {"id":"H_GH_FLASK","provider":"github","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","query":"Python lightweight WSGI web framework routing templates","target":"pallets/flask"},
 {"id":"H_GH_PYTEST","provider":"github","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","query":"Python testing framework fixtures assertions plugins","target":"pytest-dev/pytest"},
 {"id":"H_GH_FASTAPI","provider":"github","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","query":"Python async API web framework type hints OpenAPI","target":"fastapi/fastapi"},
 {"id":"H_NPM_COMMANDER","provider":"npm","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY","query":"Node command line argument parser options commands","target":"commander"},
 {"id":"H_NPM_AXIOS","provider":"npm","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY","query":"promise HTTP client browser node","target":"axios"},
 {"id":"H_NPM_ZOD","provider":"npm","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY","query":"TypeScript schema validation static type inference","target":"zod"},
 {"id":"H_CRATE_REGEX","provider":"crates","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API","query":"regular expression engine Rust Unicode","target":"regex"},
 {"id":"H_CRATE_TRACING","provider":"crates","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API","query":"structured diagnostics instrumentation async Rust","target":"tracing"},
 {"id":"H_CRATE_ITERTOOLS","provider":"crates","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API","query":"iterator adaptors extra methods Rust","target":"itertools"},
 {"id":"H_NUGET_DAPPER","provider":"nuget","source_id":"NUGET_SEARCH","upstream_group":"NUGET_PUBLIC_API","query":".NET micro ORM SQL object mapping","target":"Dapper"},
 {"id":"H_NUGET_AUTOMAPPER","provider":"nuget","source_id":"NUGET_SEARCH","upstream_group":"NUGET_PUBLIC_API","query":".NET object object mapping conventions","target":"AutoMapper"},
 {"id":"H_RUBY_SIDEKIQ","provider":"rubygems","source_id":"RUBYGEMS_SEARCH","upstream_group":"RUBYGEMS_PUBLIC_API","query":"Ruby background job processing Redis concurrency","target":"sidekiq"},
 {"id":"H_PHP_CONSOLE","provider":"packagist","source_id":"PACKAGIST_SEARCH","upstream_group":"PACKAGIST_PUBLIC_API","query":"PHP command line console component commands input output","target":"symfony/console"},
)

def norm(x:Any)->str:return str(x or "").strip().casefold()

def validate():
 seen=set()
 for row in TASKS:
  if row["id"] in seen:raise ValueError("DUPLICATE_ID")
  seen.add(row["id"])
  q=norm(row["query"]);target=norm(row["target"]);base=target.rsplit("/",1)[-1].rsplit(":",1)[-1]
  if target in q or (len(base)>=4 and base in q):raise ValueError("TARGET_LEAK:"+row["id"])

def run(*,limit:int=20,timeout:float=20.0)->dict[str,Any]:
 validate();root=Path(__file__).resolve().parents[2];events=[]
 for seq,row in enumerate(TASKS,1):
  qa={"action_id":"HOLDOUT:"+hashlib.sha256((row["id"]+"\0"+row["query"]).encode()).hexdigest()[:24],
      "source_id":row["source_id"],"provider_route":row["source_id"],"strategy_id":"FRESH_HOLDOUT_RAW_V20","query":row["query"]}
  src={"source_id":row["source_id"],"upstream_group":row["upstream_group"],
       "source_class":"repository" if row["provider"]=="github" else "registry",
       "ecosystem":"maven" if row["provider"]=="maven" else row["provider"]}
  plan=entrypoint.compile_authorized_plan(root=root,query_actions=[qa],sources=[src])
  strategies=[str(x.get("strategy_id") or "") for x in (plan.get("plan") or {}).get("actions",[])]
  fn=p.PROVIDERS[row["provider"]];start=time.perf_counter()
  try:ids=fn(row["query"],limit=limit,timeout=timeout);status="SUCCESS";err=None
  except Exception as exc:ids=[];status="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:300]}"
  candidates=[norm(x) for x in ids if norm(x)];target=norm(row["target"]);hit=target in candidates
  events.append({"sequence":seq,"case_id":row["id"],"source_id":row["source_id"],"provider":row["provider"],
    "query":row["query"],"status":status,"candidate_ids":candidates,"target_hit":hit,
    "target_rank":candidates.index(target)+1 if hit else None,"expected_target_answer_key":target,
    "entrypoint_v4_status":plan.get("status"),"frozen_planned_strategies":strategies,
    "latency_seconds":max(0.0,time.perf_counter()-start),"error":err})
 good=[x for x in events if x["status"]=="SUCCESS"];hits=[x for x in good if x["target_hit"]]
 return {"schema":SCHEMA,"status":"FRESH_HOLDOUT_COMPLETE","task_count":len(events),
  "successful_task_count":len(good),"target_hit_count":len(hits),"target_miss_count":len(good)-len(hits),
  "raw_top20_recall":len(hits)/len(good) if good else None,
  "miss_case_ids":[x["case_id"] for x in good if not x["target_hit"]],
  "failed_case_ids":[x["case_id"] for x in events if x["status"]!="SUCCESS"],
  "events":events,"answer_key_identity_used_for_query_generation":False,
  "frozen_entrypoint_v4_used":True,"post_hoc_route_changes":False,
  "open_world_completeness_claim":False,"incremental_spend_usd":0,
  "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,
  "ownership_credit_delta":0,"execution_authority":False,"promotion_authority":False}

if __name__=="__main__":
 out=run();print(json.dumps(out,ensure_ascii=False,sort_keys=True));raise SystemExit(0 if out["successful_task_count"] else 1)
