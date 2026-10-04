#!/usr/bin/env python3
"""Post-holdout recovery experiment for the four immutable V20 misses.

Uses only generic post-holdout mechanisms:
- progressive semantic/conjunction relaxation;
- behavior -> GitHub repository -> ecosystem manifest identity bridge.

Target identities are loaded only after all retrieval executions finish.
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import retrieval_live_provider_arena_v11 as v11
from canonical.runtime import retrieval_progressive_query_relaxation_v1 as relax
from canonical.runtime import retrieval_repository_manifest_bridge_v1 as manifest

SCHEMA="PROJECT_BRAIN_RETRIEVAL_V20_MISS_RECOVERY_V1"
ANSWER_KEY="canonical/governance/RETRIEVAL_V20_FRESH_HOLDOUT_ANSWER_KEY_V1.json"
MISS_IDS=(
    "H20_GITHUB_RUST_SEARCH",
    "H20_GITHUB_AR_NLP",
    "H20_MAVEN_LANG_UTIL",
    "H20_RUBY_JOBS",
)

def _norm(x:Any)->str:
    return " ".join(str(x or "").strip().split()).casefold()

def _request(root:Path,eid:str)->dict[str,Any]:
    p=root/f"canonical/governance/retrieval_v20_holdout_requests/{eid}.json"
    return json.loads(p.read_text(encoding="utf-8"))

def _run_queries(provider,queries,*,limit:int,timeout:float)->dict[str,Any]:
    ids=[];seen=set();traces=[];failures=0
    for q in queries:
        start=time.perf_counter()
        try:
            got=provider(q,limit=limit,timeout=timeout)
            status="SUCCESS";err=None
        except Exception as exc:
            got=[];status="FAILED_RETRYABLE";failures+=1
            err=f"{type(exc).__name__}:{str(exc)[:400]}"
        norm=[_norm(x) for x in got if _norm(x)]
        for x in norm:
            if x not in seen:seen.add(x);ids.append(x)
        traces.append({"query":q,"status":status,"candidate_count":len(norm),"error":err,"latency_seconds":max(0.0,time.perf_counter()-start)})
    return {"candidate_ids":ids,"traces":traces,"failed_request_count":failures}

def _repo_manifest_candidates(request:Mapping[str,Any],ecosystem:str,*,timeout:float)->dict[str,Any]:
    qplan=relax.generate(request["query_action"],provider="github",max_queries=18)
    repos=_run_queries(v11.PROVIDERS["github"],qplan["queries"],limit=30,timeout=timeout)
    identities=[];seen=set();traces=[]
    for repo in repos["candidate_ids"][:32]:
        try:
            row=manifest.repository_identities(repo,ecosystem,timeout=timeout,max_files=32)
            status="SUCCESS";err=None
        except Exception as exc:
            row={"repository":repo,"identities":[],"traces":[]}
            status="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:400]}"
        traces.append({"repository":repo,"status":status,"error":err,"manifest":row})
        for ident in row.get("identities") or []:
            key=_norm(ident)
            if key and key not in seen:
                seen.add(key);identities.append(key)
    return {"repository_candidates":repos["candidate_ids"],"candidate_ids":identities,"query_traces":repos["traces"],"manifest_traces":traces}

def execute_case(root:Path,eid:str,*,timeout:float=20.0)->dict[str,Any]:
    req=_request(root,eid)
    source=req["source"];provider_name=str(source["provider"])
    qplan=relax.generate(req["query_action"],provider=provider_name,max_queries=24)
    base=_run_queries(v11.PROVIDERS[provider_name],qplan["queries"],limit=50,timeout=timeout)
    union=list(base["candidate_ids"]);seen=set(union)
    bridge=None

    ecosystem=str(source.get("ecosystem") or "")
    if provider_name=="maven":
        bridge=_repo_manifest_candidates(req,"maven",timeout=timeout)
    elif provider_name=="rubygems":
        bridge=_repo_manifest_candidates(req,"rubygems",timeout=timeout)

    if bridge:
        for x in bridge["candidate_ids"]:
            if x not in seen:seen.add(x);union.append(x)

    return {
        "episode_id":eid,
        "provider":provider_name,
        "generated_query_count":len(qplan["queries"]),
        "generated_queries":qplan["queries"],
        "candidate_ids":union,
        "candidate_count":len(union),
        "provider_query_traces":base["traces"],
        "repository_manifest_bridge":bridge,
        "answer_key_identity_used_for_query_generation":False,
        "answer_key_identity_used_for_repository_selection":False,
    }

def run(*,root:Path|None=None,timeout:float=20.0)->dict[str,Any]:
    root=root or Path(__file__).resolve().parents[2]
    results=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs={pool.submit(execute_case,root,eid,timeout=timeout):eid for eid in MISS_IDS}
        for fut in as_completed(futs):
            results.append(fut.result())
    results.sort(key=lambda x:MISS_IDS.index(x["episode_id"]))

    # Answer key is loaded only after all recovery retrieval calls finish.
    answer=json.loads((root/ANSWER_KEY).read_text(encoding="utf-8"))
    targets=answer["targets"]
    scored=[]
    for row in results:
        target=_norm(targets[row["episode_id"]])
        ids=[_norm(x) for x in row["candidate_ids"]]
        hit=target in ids
        scored.append({
            "episode_id":row["episode_id"],
            "provider":row["provider"],
            "target_hit":hit,
            "target_rank":ids.index(target)+1 if hit else None,
            "candidate_count":len(ids),
            "generated_query_count":row["generated_query_count"],
        })
    hits=[x for x in scored if x["target_hit"]]
    return {
        "schema":SCHEMA,
        "status":"POST_HOLDOUT_GENERIC_MISS_RECOVERY_COMPLETE",
        "frozen_original_holdout_recall":8/12,
        "miss_case_count":4,
        "recovered_count":len(hits),
        "recovery_rate":len(hits)/4,
        "remaining_miss_episode_ids":[x["episode_id"] for x in scored if not x["target_hit"]],
        "cases":scored,
        "events":results,
        "answer_key_loaded_only_after_all_retrieval_execution":True,
        "answer_key_identity_used_for_query_generation":False,
        "original_v20_result_reclassified":False,
        "open_world_completeness_claim":False,
        "incremental_spend_usd":0,
        "hard_rules":[
            "ORIGINAL_V20_8_OF_12_RESULT_REMAINS_IMMUTABLE",
            "REPAIRS_ARE_GENERIC_FAILURE_CLASS_MECHANISMS_NOT_TARGET_IDENTITY_QUERIES",
            "RECOVERY_ON_OLD_MISSES_IS_TRAINING_EVIDENCE_NOT_NEW_HOLDOUT_EVIDENCE",
            "A_NEW_FRESH_HOLDOUT_IS_REQUIRED_FOR_GENERALIZATION_CREDIT"
        ]
    }

def main()->int:
    out=run()
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
