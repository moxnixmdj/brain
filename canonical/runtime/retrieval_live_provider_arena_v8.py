#!/usr/bin/env python3
"""Retrieval V12 residual recovery arena.

Targets ONLY the seven misses exposed by the independently receipt-bound V11
coverage run.

Recovery hypotheses:
1. Cross-language GitHub failure was caused by over-constraining native and
   translated terms in one AND-style query. Test translated technical anchors
   as a separate route, never as native+English concatenation.
2. Registry ranking misses can be recovered through GitHub repository search,
   but package recovery is credited only when public registry metadata verifies
   repository -> package identity.

Answer-key package/repository identities are evaluation-only and never inserted
into discovery queries.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from canonical.runtime import retrieval_live_provider_arena_v1 as base
from canonical.runtime import retrieval_registry_repository_bridge_v1 as bridge

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_ARENA_V8"

CASES=(
 {"case_id":"XLANG_COMPUTER_VISION","query_family":"TRANSLATED_TECHNICAL_ANCHOR_ONLY_V12",
  "query":"computer vision library in:name,description,readme",
  "target_repository":"opencv/opencv","package_ecosystem":None,"package_id":None},
 {"case_id":"XLANG_MACHINE_LEARNING","query_family":"TRANSLATED_TECHNICAL_ANCHOR_ONLY_V12",
  "query":"machine learning python library in:name,description,readme",
  "target_repository":"scikit-learn/scikit-learn","package_ecosystem":None,"package_id":None},
 {"case_id":"XLANG_ASYNC_WEB_API","query_family":"TRANSLATED_TECHNICAL_ANCHOR_ONLY_V12",
  "query":"python async API framework in:name,description,readme",
  "target_repository":"fastapi/fastapi","package_ecosystem":None,"package_id":None},

 {"case_id":"PACKAGE_NODE_WEB","query_family":"CROSS_ECOSYSTEM_REPO_BRIDGE_V12",
  "query":"node web framework in:name,description,readme",
  "target_repository":"expressjs/express","package_ecosystem":"npm","package_id":"express"},
 {"case_id":"PACKAGE_JS_BUNDLER","query_family":"CROSS_ECOSYSTEM_REPO_BRIDGE_V12",
  "query":"javascript module bundler in:name,description,readme",
  "target_repository":"webpack/webpack","package_ecosystem":"npm","package_id":"webpack"},
 {"case_id":"PACKAGE_RUST_HTTP","query_family":"CROSS_ECOSYSTEM_REPO_BRIDGE_V12",
  "query":"rust http client in:name,description,readme",
  "target_repository":"seanmonstar/reqwest","package_ecosystem":"crates","package_id":"reqwest"},
 {"case_id":"PACKAGE_RUST_PARALLEL","query_family":"CROSS_ECOSYSTEM_REPO_BRIDGE_V12",
  "query":"rust data parallelism library in:name,description,readme",
  "target_repository":"rayon-rs/rayon","package_ecosystem":"crates","package_id":"rayon"},
)

def validate_cases()->None:
 if len(CASES)!=7:
  raise ValueError("EXPECTED_SEVEN_V11_RESIDUAL_CASES")
 if len({x["case_id"] for x in CASES})!=7:
  raise ValueError("DUPLICATE_RESIDUAL_CASE")
 for row in CASES:
  q=str(row["query"]).casefold()
  if str(row["target_repository"]).casefold() in q:
   raise ValueError("REPOSITORY_ANSWER_KEY_LEAKED_IN_QUERY:"+row["case_id"])
  package=str(row.get("package_id") or "").casefold()
  # Package names such as "express" can be ordinary words, so do not ban a
  # substring by accident. Exact package identity is never programmatically
  # appended to the query.
  if package and q.strip()==package:
   raise ValueError("PACKAGE_ANSWER_KEY_USED_AS_QUERY:"+row["case_id"])
 for case in CASES[:3]:
  if case["query_family"]!="TRANSLATED_TECHNICAL_ANCHOR_ONLY_V12":
   raise ValueError("XLANG_RECOVERY_MUST_USE_SEPARATE_TRANSLATED_ANCHOR_ROUTE")

def _registry_bridge(ecosystem:str,package_id:str,target_repository:str,*,timeout:float)->dict[str,Any]:
 start=time.perf_counter()
 try:
  if ecosystem=="npm":
   meta=bridge.npm_metadata(package_id,timeout=timeout)
  elif ecosystem=="crates":
   meta=bridge.crates_metadata(package_id,timeout=timeout)
  else:
   raise ValueError("UNSUPPORTED_ECOSYSTEM")
  status="SUCCESS"; error=None
 except Exception as exc:
  meta={};status="FAILED_RETRYABLE";error=f"{type(exc).__name__}:{str(exc)[:400]}"
 observed=bridge.canon_repo(meta.get("repository_url"))
 expected=str(target_repository).casefold()
 return {
  "status":status,
  "observed_package_id":meta.get("package_id"),
  "observed_repository_url":meta.get("repository_url"),
  "observed_repository_canonical":observed,
  "expected_repository_canonical":expected,
  "bridge_match":status=="SUCCESS" and observed==expected,
  "latency_ms":max(0.0,(time.perf_counter()-start)*1000.0),
  "error":error,
 }

def run(*,limit:int=10,timeout:float=20.0)->dict[str,Any]:
 validate_cases()
 observations=[]
 for row in CASES:
  start=time.perf_counter()
  try:
   ids=base.github(row["query"],limit=limit,timeout=timeout)
   status="SUCCESS";error=None
  except Exception as exc:
   ids=[];status="FAILED_RETRYABLE";error=f"{type(exc).__name__}:{str(exc)[:400]}"
  repo_latency_ms=max(0.0,(time.perf_counter()-start)*1000.0)
  target=str(row["target_repository"])
  repo_hit=target.casefold() in {str(x).casefold() for x in ids}
  rank=next((i+1 for i,x in enumerate(ids) if str(x).casefold()==target.casefold()),None)

  bridge_result=None
  final_hit=repo_hit
  request_count=1
  if row["package_ecosystem"]:
   # Package recovery is not credited from a repo hit alone.
   if repo_hit:
    bridge_result=_registry_bridge(
     str(row["package_ecosystem"]),str(row["package_id"]),target,timeout=timeout
    )
    request_count+=1
    final_hit=bool(bridge_result["bridge_match"])
   else:
    final_hit=False

  seed=f"{row['case_id']}\0{row['query_family']}\0{row['query']}"
  observations.append({
   "case_id":row["case_id"],
   "provider_route":"GITHUB_REPOSITORY_SEARCH" if not row["package_ecosystem"] else "GITHUB_REPOSITORY_SEARCH_PLUS_REGISTRY_BRIDGE",
   "upstream_group":"GITHUB_PUBLIC_API" if not row["package_ecosystem"] else "GITHUB_PUBLIC_API_PLUS_REGISTRY_METADATA",
   "query_family":row["query_family"],
   "query":row["query"],
   "action_id":"LIVEV12:"+hashlib.sha256(seed.encode()).hexdigest()[:24],
   "transport_status":status,
   "candidate_ids":[str(x) for x in ids],
   "expected_target_answer_key":row["package_id"] or target,
   "repository_target_answer_key":target,
   "repository_hit":repo_hit,
   "repository_rank":rank,
   "bridge":bridge_result,
   "hit_at_pool":bool(final_hit),
   "rank_in_pool":rank if final_hit else None,
   "candidate_pool_size":len(ids),
   "latency_ms":repo_latency_ms+(float(bridge_result["latency_ms"]) if bridge_result else 0.0),
   "request_count":request_count,
   "error":error,
  })

 usable=[x for x in observations if x["transport_status"]=="SUCCESS"]
 hits=[x for x in usable if x["hit_at_pool"]]
 return {
  "schema":SCHEMA,
  "status":"V11_RESIDUAL_RECOVERY_COMPLETE",
  "case_count":len(CASES),
  "usable_case_count":len(usable),
  "recovered_case_count":len(hits),
  "finite_residual_recovery_rate":len(hits)/len(CASES),
  "miss_case_ids":[x["case_id"] for x in usable if not x["hit_at_pool"]],
  "observations":observations,
  "open_world_completeness_claim":False,
  "incremental_spend_usd":0,
  "acceptance_credit_delta":0,
  "family_credit_delta":0,
  "capability_credit_delta":0,
  "ownership_credit_delta":0,
  "execution_authority":False,
  "promotion_authority":False,
  "hard_rules":[
   "ONLY_THE_SEVEN_INDEPENDENTLY_OBSERVED_V11_MISSES_ARE_TARGETED",
   "NATIVE_AND_TRANSLATED_TERMS_ARE_NOT_AND_CONCATENATED_IN_THE_XLANG_RECOVERY_ROUTE",
   "PACKAGE_RECOVERY_REQUIRES_REPOSITORY_HIT_PLUS_PUBLIC_REGISTRY_IDENTITY_BRIDGE",
   "FAILED_TRANSPORT_OR_BRIDGE_CALLS_REMAIN_RETRYABLE",
   "FINITE_RESIDUAL_RECOVERY_IS_NOT_OPEN_WORLD_COMPLETENESS",
   "NO_ACCEPTANCE_FAMILY_CAPABILITY_OWNERSHIP_EXECUTION_OR_PROMOTION_CREDIT"
  ]
 }

def main()->int:
 out=run()
 print("RETRIEVAL_V12_LIVE_OUTPUT="+json.dumps(out,ensure_ascii=False,sort_keys=True,separators=(",",":")))
 return 0 if out["usable_case_count"]>0 else 1

if __name__=="__main__":
 raise SystemExit(main())
