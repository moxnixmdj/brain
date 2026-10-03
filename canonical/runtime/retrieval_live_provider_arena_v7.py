#!/usr/bin/env python3
"""Retrieval V11 live coverage expansion arena.

Extends the receipt-bound V10 live calibration with NEW labeled cases chosen by
coverage dimension rather than convenience:
- multilingual native-only vs native+technical-anchor GitHub queries,
- new npm and crates behavioral targets,
- new Hugging Face provider-native pipeline enumeration targets,
- new scholarly targets queried through Crossref and OpenAlex.

Expected identities are evaluation-only. Results are finite live observations,
never completeness or acceptance evidence.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from canonical.runtime import retrieval_live_provider_arena_v1 as base
from canonical.runtime import retrieval_live_provider_arena_v2 as v2

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_ARENA_V7"

TASKS=(
 # Same labeled case, two cross-language strategies. This directly measures
 # whether a technical anchor recovers a native-language lexical mismatch.
 {"case_id":"XLANG_COMPUTER_VISION","provider_route":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API",
  "query_family":"NATIVE_ONLY_V11","provider":"github",
  "query":"计算机视觉 图像处理 库 in:name,description,readme","target":"opencv/opencv"},
 {"case_id":"XLANG_COMPUTER_VISION","provider_route":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API",
  "query_family":"NATIVE_PLUS_TECHNICAL_ANCHOR_V11","provider":"github",
  "query":"计算机视觉 图像处理 computer vision library in:name,description,readme","target":"opencv/opencv"},
 {"case_id":"XLANG_MACHINE_LEARNING","provider_route":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API",
  "query_family":"NATIVE_ONLY_V11","provider":"github",
  "query":"biblioteca aprendizaje automático python in:name,description,readme","target":"scikit-learn/scikit-learn"},
 {"case_id":"XLANG_MACHINE_LEARNING","provider_route":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API",
  "query_family":"NATIVE_PLUS_TECHNICAL_ANCHOR_V11","provider":"github",
  "query":"biblioteca aprendizaje automático machine learning python library in:name,description,readme","target":"scikit-learn/scikit-learn"},
 {"case_id":"XLANG_ASYNC_WEB_API","provider_route":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API",
  "query_family":"NATIVE_ONLY_V11","provider":"github",
  "query":"إطار واجهة برمجة تطبيقات بايثون غير متزامن in:name,description,readme","target":"fastapi/fastapi"},
 {"case_id":"XLANG_ASYNC_WEB_API","provider_route":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API",
  "query_family":"NATIVE_PLUS_TECHNICAL_ANCHOR_V11","provider":"github",
  "query":"إطار واجهة برمجة تطبيقات بايثون غير متزامن python async API framework in:name,description,readme","target":"fastapi/fastapi"},

 {"case_id":"PACKAGE_NODE_WEB","provider_route":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY",
  "query_family":"ANCHOR_COMPRESSED_V11","provider":"npm","query":"node web framework","target":"express"},
 {"case_id":"PACKAGE_JS_BUNDLER","provider_route":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY",
  "query_family":"ANCHOR_COMPRESSED_V11","provider":"npm","query":"javascript module bundler","target":"webpack"},
 {"case_id":"PACKAGE_JS_BUILD_TOOL","provider_route":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY",
  "query_family":"ANCHOR_COMPRESSED_V11","provider":"npm","query":"frontend build tool development server","target":"vite"},

 {"case_id":"PACKAGE_RUST_REGEX","provider_route":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API",
  "query_family":"ANCHOR_COMPRESSED_V11","provider":"crates","query":"regular expression","target":"regex"},
 {"case_id":"PACKAGE_RUST_HTTP","provider_route":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API",
  "query_family":"ANCHOR_COMPRESSED_V11","provider":"crates","query":"http client async","target":"reqwest"},
 {"case_id":"PACKAGE_RUST_PARALLEL","provider_route":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API",
  "query_family":"ANCHOR_COMPRESSED_V11","provider":"crates","query":"data parallelism","target":"rayon"},

 {"case_id":"MODEL_IMAGE_CLASSIFICATION","provider_route":"HUGGINGFACE_MODEL_PIPELINE_ENUM","upstream_group":"HUGGINGFACE_HUB_API",
  "query_family":"PROVIDER_NATIVE_ENUM_V11","provider":"huggingface_pipeline","query":"image-classification","target":"google/vit-base-patch16-224"},
 {"case_id":"MODEL_QUESTION_ANSWERING","provider_route":"HUGGINGFACE_MODEL_PIPELINE_ENUM","upstream_group":"HUGGINGFACE_HUB_API",
  "query_family":"PROVIDER_NATIVE_ENUM_V11","provider":"huggingface_pipeline","query":"question-answering","target":"deepset/roberta-base-squad2"},

 {"case_id":"PAPER_SINGLE_PASS_OBJECT_DETECTION","provider_route":"CROSSREF_TITLE_SEARCH","upstream_group":"CROSSREF_PUBLIC_API",
  "query_family":"PROVIDER_NATIVE_TITLE_V11","provider":"crossref_title",
  "query":"single pass real time object detection unified detection network","target":"10.1109/CVPR.2016.91"},
 {"case_id":"PAPER_SINGLE_PASS_OBJECT_DETECTION","provider_route":"OPENALEX_WORK_SEARCH","upstream_group":"OPENALEX_PUBLIC_API",
  "query_family":"TITLE_ANCHOR_V11","provider":"openalex",
  "query":"single pass real time object detection unified detection network","target":"10.1109/CVPR.2016.91"},
 {"case_id":"PAPER_INSTANCE_SEGMENTATION","provider_route":"CROSSREF_TITLE_SEARCH","upstream_group":"CROSSREF_PUBLIC_API",
  "query_family":"PROVIDER_NATIVE_TITLE_V11","provider":"crossref_title",
  "query":"instance segmentation object detection mask branch","target":"10.1109/ICCV.2017.322"},
 {"case_id":"PAPER_INSTANCE_SEGMENTATION","provider_route":"OPENALEX_WORK_SEARCH","upstream_group":"OPENALEX_PUBLIC_API",
  "query_family":"TITLE_ANCHOR_V11","provider":"openalex",
  "query":"instance segmentation object detection mask branch","target":"10.1109/ICCV.2017.322"},
)

PROVIDERS={
 "github":base.github,
 "npm":base.npm,
 "crates":base.crates,
 "huggingface_pipeline":v2.huggingface_pipeline,
 "crossref_title":v2.crossref_title,
 "openalex":base.openalex,
}

def validate_tasks()->None:
 if len(TASKS)!=18:
  raise ValueError("EXPECTED_18_LIVE_EVENTS")
 cases={str(x["case_id"]) for x in TASKS}
 if len(cases)!=13:
  raise ValueError("EXPECTED_13_UNIQUE_LABELED_CASES")
 seen=set()
 for row in TASKS:
  key=(row["case_id"],row["provider_route"],row["query_family"])
  if key in seen:
   raise ValueError("DUPLICATE_ROUTE_STRATEGY_CASE:"+repr(key))
  seen.add(key)
  q=str(row["query"]).casefold()
  target=str(row["target"]).casefold()
  if target and target in q:
   raise ValueError("ANSWER_KEY_IDENTITY_LEAKED_IN_QUERY:"+row["case_id"])
 for case in ("XLANG_COMPUTER_VISION","XLANG_MACHINE_LEARNING","XLANG_ASYNC_WEB_API"):
  fams={x["query_family"] for x in TASKS if x["case_id"]==case}
  if fams!={"NATIVE_ONLY_V11","NATIVE_PLUS_TECHNICAL_ANCHOR_V11"}:
   raise ValueError("XLANG_AB_PAIR_INCOMPLETE:"+case)

def run(*,limit:int=10,timeout:float=20.0)->dict[str,Any]:
 validate_tasks()
 observations=[]
 for row in TASKS:
  provider=PROVIDERS[row["provider"]]
  start=time.perf_counter()
  try:
   ids=provider(row["query"],limit=limit,timeout=timeout)
   status="SUCCESS"; error=None
  except Exception as exc:
   ids=[]; status="FAILED_RETRYABLE"; error=f"{type(exc).__name__}:{str(exc)[:400]}"
  scholarly=row["provider"] in {"crossref_title","openalex"}
  target=base._doi(row["target"]) if scholarly else str(row["target"])
  normalized=[base._doi(x) if scholarly else str(x) for x in ids]
  hit=target.casefold() in {x.casefold() for x in normalized}
  rank=next((i+1 for i,x in enumerate(normalized) if x.casefold()==target.casefold()),None)
  latency_ms=max(0.0,(time.perf_counter()-start)*1000.0)
  seed=f"{row['case_id']}\0{row['provider_route']}\0{row['query_family']}\0{row['query']}"
  observations.append({
   "case_id":row["case_id"],
   "provider_route":row["provider_route"],
   "upstream_group":row["upstream_group"],
   "query_family":row["query_family"],
   "query":row["query"],
   "action_id":"LIVEV11:"+hashlib.sha256(seed.encode()).hexdigest()[:24],
   "transport_status":status,
   "candidate_ids":normalized,
   "expected_target_answer_key":target,
   "hit_at_pool":hit,
   "rank_in_pool":rank,
   "candidate_pool_size":len(normalized),
   "latency_ms":latency_ms,
   "request_count":1,
   "error":error,
  })

 usable=[x for x in observations if x["transport_status"]=="SUCCESS"]
 hits=[x for x in usable if x["hit_at_pool"]]
 cases=sorted({x["case_id"] for x in observations})
 hit_cases=sorted({x["case_id"] for x in usable if x["hit_at_pool"]})
 route_metrics={}
 for key in sorted({(x["provider_route"],x["query_family"]) for x in observations}):
  rows=[x for x in observations if (x["provider_route"],x["query_family"])==key]
  ok=[x for x in rows if x["transport_status"]=="SUCCESS"]
  hh=[x for x in ok if x["hit_at_pool"]]
  route_metrics[f"{key[0]}::{key[1]}"]={
   "event_count":len(rows),
   "usable_transport_count":len(ok),
   "target_hit_count":len(hh),
   "target_hit_rate":len(hh)/len(ok) if ok else None,
   "mean_latency_ms":sum(float(x["latency_ms"]) for x in ok)/len(ok) if ok else None,
  }
 xlang={}
 for case in ("XLANG_COMPUTER_VISION","XLANG_MACHINE_LEARNING","XLANG_ASYNC_WEB_API"):
  rows=[x for x in observations if x["case_id"]==case]
  xlang[case]={
   x["query_family"]:{
    "usable":x["transport_status"]=="SUCCESS",
    "hit":bool(x["hit_at_pool"]),
    "rank":x["rank_in_pool"],
   } for x in rows
  }
 return {
  "schema":SCHEMA,
  "status":"LIVE_COVERAGE_EXPANSION_COMPLETE",
  "event_count":len(observations),
  "unique_labeled_case_count":len(cases),
  "usable_event_count":len(usable),
  "target_hit_event_count":len(hits),
  "target_hit_case_count":len(hit_cases),
  "finite_case_union_recall":len(hit_cases)/len(cases) if cases else 0.0,
  "route_strategy_metrics":route_metrics,
  "cross_language_ab":xlang,
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
   "ALL_QUERIES_ARE_FROZEN_BEFORE_LIVE_EXECUTION",
   "ANSWER_KEY_IDENTITIES_ARE_EVALUATION_ONLY",
   "TRANSPORT_FAILURES_REMAIN_RETRYABLE_AND_ARE_NOT_RECALL_MISSES",
   "SAME_CASE_MULTILINGUAL_AB_ROUTES_ENABLE_DIRECTIONAL_RECOVERY_MEASUREMENT",
   "FINITE_LABELED_RECALL_IS_NOT_OPEN_WORLD_COMPLETENESS",
   "LIVE_OUTPUT_REQUIRES_INDEPENDENT_PUBLIC_RUNNER_RECEIPT_BEFORE_CALIBRATION_ADMISSION",
   "NO_PROVIDER_RESULT_SELF_GRANTS_ACCEPTANCE_OR_CAPABILITY_CREDIT"
  ]
 }

def main()->int:
 out=run()
 print("RETRIEVAL_V11_LIVE_OUTPUT="+json.dumps(out,ensure_ascii=False,sort_keys=True,separators=(",",":")))
 return 0 if out["usable_event_count"]>0 else 1

if __name__=="__main__":
 raise SystemExit(main())
