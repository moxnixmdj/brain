#!/usr/bin/env python3
"""Retrieval V17 Maven JSON versioned-identity recovery.

Replays only the independently observed MAVEN_JSON_BIND residual. Discovery is
answer-key blind:
1) behavior-only GitHub search using the frozen requirement,
2) current repository POM coordinate extraction,
3) Maven Central enumeration by artifactId derived from those discovered POMs.

The frozen historical groupId is used only for final scoring.
"""
from __future__ import annotations
import hashlib, json, time, urllib.parse
from typing import Any, Mapping

from canonical.runtime import retrieval_live_provider_arena_v11 as v11
from canonical.runtime import retrieval_live_provider_arena_v13 as v13
from canonical.runtime import retrieval_live_provider_arena_v14 as v14

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_ARENA_V17"
EPISODE_ID="MAVEN_JSON_BIND"

def row()->Mapping[str,Any]:
    rows=[x for x in v11.TASKS if x["episode_id"]==EPISODE_ID]
    if len(rows)!=1:
        raise ValueError("V17_JSON_TASK_MISMATCH")
    return rows[0]

def artifact_lineage(
    coordinates:list[str],
    *,
    timeout:float=20.0,
    limit:int=80,
)->tuple[list[str],list[dict[str,Any]]]:
    aliases=[];seen=set();seen_artifacts=set();traces=[]
    for coord in coordinates:
        if ":" not in coord:
            continue
        artifact=coord.split(":",1)[1].strip()
        if len(artifact)<3 or artifact.casefold() in seen_artifacts:
            continue
        seen_artifacts.add(artifact.casefold())
        q=f'a:"{artifact}"'
        url="https://search.maven.org/solrsearch/select?"+urllib.parse.urlencode({
            "q":q,"rows":limit,"wt":"json",
        })
        start=time.perf_counter()
        try:
            obj=v13.base._url_json(url,timeout=timeout)
            docs=((obj.get("response") or {}).get("docs") or []) if isinstance(obj,dict) else []
            ids=[str(x.get("id") or "") for x in docs if str(x.get("id") or "").strip()]
            status="SUCCESS";err=None
        except Exception as exc:
            ids=[];status="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:300]}"
        for mid in ids:
            key=mid.casefold()
            if key not in seen:
                seen.add(key);aliases.append(mid)
        traces.append({
            "artifact_id":artifact,
            "query":q,
            "status":status,
            "candidate_count":len(ids),
            "error":err,
            "latency_seconds":max(0.0,time.perf_counter()-start),
        })
    return aliases,traces

def validate()->None:
    r=row()
    target=v11._norm(r["target"])
    basename=target.rsplit(":",1)[-1]
    for q in v14.maven_behavior_queries(str(r["query"])):
        nq=v11._norm(q)
        if target in nq or (len(basename)>=4 and basename in nq):
            raise ValueError("TARGET_IDENTITY_LEAKED_IN_QUERY")

def run(*,timeout:float=20.0)->dict[str,Any]:
    validate()
    r=row()
    query=str(r["query"])
    start=time.perf_counter()

    queries=v14.maven_behavior_queries(query)
    repos,search_traces=v14.repo_union(queries,limit_per_query=10,timeout=timeout)

    direct=[];seen=set();manifest_traces=[]
    # V14 evidence puts the relevant repository at rank 1. Inspect a small
    # bounded prefix; no answer-key repository is injected.
    for repo in repos[:4]:
        try:
            got,trace=v13.repository_pom_coordinates(repo,timeout=timeout,max_poms=12)
            status="SUCCESS";err=None
        except Exception as exc:
            got=[];trace={"repository":repo,"pom_files":[]}
            status="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:300]}"
        trace["status"]=status;trace["error"]=err
        manifest_traces.append(trace)
        for coord in got:
            key=coord.casefold()
            if key not in seen:
                seen.add(key);direct.append(coord)

    aliases,lineage_traces=artifact_lineage(direct,timeout=timeout,limit=80)
    merged=list(direct);mseen={x.casefold() for x in merged}
    for alias in aliases:
        if alias.casefold() not in mseen:
            mseen.add(alias.casefold());merged.append(alias)

    target=v11._norm(r["target"])
    candidates=[v11._norm(x) for x in merged]
    hit=target in set(candidates)
    failures=sum(1 for x in search_traces if x["status"]!="SUCCESS")
    failures+=sum(1 for x in manifest_traces if x["status"]!="SUCCESS")
    failures+=sum(1 for x in lineage_traces if x["status"]!="SUCCESS")

    return {
        "schema":SCHEMA,
        "status":"LIVE_MAVEN_JSON_VERSIONED_IDENTITY_PROBE_COMPLETE",
        "episode_id":EPISODE_ID,
        "generated_queries":queries,
        "repository_candidates":repos,
        "direct_manifest_coordinates":[v11._norm(x) for x in direct],
        "lineage_aliases":[v11._norm(x) for x in aliases],
        "candidate_ids":candidates,
        "expected_target_answer_key":target,
        "target_hit":hit,
        "target_rank":candidates.index(target)+1 if hit else None,
        "answer_key_identity_used_for_query_generation":False,
        "answer_key_identity_used_for_lineage_generation":False,
        "search_traces":search_traces,
        "manifest_traces":manifest_traces,
        "lineage_traces":lineage_traces,
        "request_failure_count":failures,
        "latency_seconds":max(0.0,time.perf_counter()-start),
        "v14_union_hits":28,
        "v14_union_recall":28/30,
        "v14_plus_v17_union_hits":29 if hit else 28,
        "v14_plus_v17_union_recall":(29 if hit else 28)/30,
        "open_world_completeness_claim":False,
        "incremental_spend_usd":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "hard_rules":[
            "ONLY_THE_INDEPENDENTLY_OBSERVED_MAVEN_JSON_BIND_RESIDUAL_IS_PROBED",
            "ANSWER_KEY_IDENTITY_IS_SCORING_ONLY",
            "LINEAGE_QUERY_ARTIFACT_IDS_MUST_DERIVE_FROM_DISCOVERED_POM_COORDINATES",
            "NO_HISTORICAL_GROUP_ID_IS_INJECTED_INTO_DISCOVERY",
            "FAILED_CALLS_REMAIN_RETRYABLE",
            "FINITE_LIVE_RECOVERY_IS_NOT_OPEN_WORLD_COMPLETENESS",
        ],
    }

def main()->int:
    out=run()
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0 if out["target_hit"] else 2

if __name__=="__main__":
    raise SystemExit(main())
