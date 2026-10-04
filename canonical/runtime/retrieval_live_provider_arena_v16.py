#!/usr/bin/env python3
"""Retrieval V16 relevance-scored candidate-graph snowball recovery.

Replays the independently observed MAVEN_COLLECTIONS residual. Starting from
answer-key-blind V14 repository search results, it follows outbound GitHub
repository links whose *local surrounding text* overlaps the original behavior
requirement, then verifies Maven coordinates from linked repositories' POMs.

This operationalizes the global V6 candidate-graph policy. Target identity is
used only for final scoring, never for link extraction, ranking, or traversal.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time
import urllib.parse
from typing import Any, Mapping

from canonical.runtime import retrieval_live_provider_arena_v11 as v11
from canonical.runtime import retrieval_live_provider_arena_v13 as v13
from canonical.runtime import retrieval_live_provider_arena_v14 as v14

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_ARENA_V16"
EPISODE_ID="MAVEN_COLLECTIONS"
WORD=re.compile(r"[^\W_]+",re.UNICODE)
GH_LINK=re.compile(r"https?://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)",re.IGNORECASE)
LOW_INFO={
    "java","library","libraries","toolkit","tools","api","open","source",
    "fast","flexible","general","support","supports",
}

def _canon(x:Any)->str:
    return " ".join(str(x or "").strip().split())

def _stem(token:str)->str:
    t=token.casefold()
    if len(t)>5 and t.endswith("ies"):
        return t[:-3]+"y"
    if len(t)>5 and t.endswith("ing"):
        return t[:-3]
    if len(t)>4 and (t.endswith("ses") or t.endswith("xes") or t.endswith("zes") or t.endswith("ches") or t.endswith("shes")):
        return t[:-2]
    if len(t)>4 and t.endswith("s"):
        return t[:-1]
    return t

def behavior_concepts(query:str)->set[str]:
    out=set()
    for raw in WORD.findall(query):
        low=raw.casefold()
        if low in LOW_INFO or len(low)<3:
            continue
        out.add(_stem(low))
    return out

def behavior_link_candidates(
    markdown:str,
    query:str,
    *,
    max_links:int=32,
    context_radius:int=220,
)->list[dict[str,Any]]:
    concepts=behavior_concepts(query)
    by_repo={}
    for match in GH_LINK.finditer(markdown or ""):
        repo=match.group(1).rstrip(".,;:")
        if repo.lower().endswith(".git"):
            repo=repo[:-4]
        lo=max(0,match.start()-context_radius)
        hi=min(len(markdown),match.end()+context_radius)
        context=markdown[lo:hi]
        ctx={_stem(t) for t in WORD.findall(context) if len(t)>=3}
        overlap=sorted(concepts & ctx)
        if not overlap:
            continue
        # Prefer links explained by more of the requested behavior. The score
        # depends only on query concepts and local candidate context.
        score=(len(overlap)/max(1,len(concepts))) + 0.08*len(overlap)
        row={
            "repository":repo,
            "score":score,
            "matched_behavior_concepts":overlap,
            "context_excerpt":_canon(context)[:600],
        }
        key=repo.casefold()
        if key not in by_repo or row["score"]>by_repo[key]["score"]:
            by_repo[key]=row
    rows=list(by_repo.values())
    rows.sort(key=lambda x:(-float(x["score"]),-len(x["matched_behavior_concepts"]),x["repository"].casefold()))
    return rows[:max_links]

def repository_readme(repo:str,*,timeout:float=20.0)->str:
    quoted=urllib.parse.quote(repo,safe="/")
    obj=v13._github_json(f"https://api.github.com/repos/{quoted}/readme",timeout=timeout)
    if not isinstance(obj,Mapping):
        return ""
    raw=str(obj.get("content") or "").replace("\n","")
    if str(obj.get("encoding") or "").lower()!="base64" or not raw:
        return ""
    try:
        return base64.b64decode(raw).decode("utf-8","replace")
    except Exception:
        return ""

def graph_snowball(
    query:str,
    seed_repos:list[str],
    *,
    timeout:float=20.0,
    max_seed_repos:int=8,
    max_links_per_seed:int=24,
)->tuple[list[str],list[dict[str,Any]]]:
    ranked={}
    traces=[]
    for seed_rank,repo in enumerate(seed_repos[:max_seed_repos],1):
        start=time.perf_counter()
        try:
            text=repository_readme(repo,timeout=timeout)
            links=behavior_link_candidates(
                text,query,max_links=max_links_per_seed,context_radius=220
            )
            status="SUCCESS";err=None
        except Exception as exc:
            links=[];status="FAILED_RETRYABLE"
            err=f"{type(exc).__name__}:{str(exc)[:300]}"
        for row in links:
            key=row["repository"].casefold()
            enriched=dict(row)
            enriched["seed_repository"]=repo
            enriched["seed_rank"]=seed_rank
            if key not in ranked or enriched["score"]>ranked[key]["score"]:
                ranked[key]=enriched
        traces.append({
            "seed_repository":repo,
            "seed_rank":seed_rank,
            "status":status,
            "linked_candidate_count":len(links),
            "error":err,
            "latency_seconds":max(0.0,time.perf_counter()-start),
        })
    rows=list(ranked.values())
    rows.sort(key=lambda x:(-float(x["score"]),x["seed_rank"],x["repository"].casefold()))
    return [x["repository"] for x in rows],[
        {"repository":x["repository"],"score":x["score"],
         "matched_behavior_concepts":x["matched_behavior_concepts"],
         "seed_repository":x["seed_repository"],"seed_rank":x["seed_rank"]}
        for x in rows
    ]+traces

def row()->Mapping[str,Any]:
    rows=[x for x in v11.TASKS if x["episode_id"]==EPISODE_ID]
    if len(rows)!=1:
        raise ValueError("V16_COLLECTIONS_TASK_MISMATCH")
    return rows[0]

def validate()->None:
    r=row()
    target=v11._norm(r["target"])
    basename=target.rsplit(":",1)[-1]
    query=str(r["query"])
    for q in v14.maven_behavior_queries(query):
        nq=v11._norm(q)
        if target in nq or (len(basename)>=4 and basename in nq):
            raise ValueError("TARGET_IDENTITY_LEAKED_IN_SEED_QUERY")
    # Graph extraction/ranking accepts only query and candidate text; there is
    # deliberately no target parameter to those functions.

def run(*,timeout:float=20.0)->dict[str,Any]:
    validate()
    r=row()
    query=str(r["query"])
    start=time.perf_counter()

    seed_queries=v14.maven_behavior_queries(query)
    seed_repos,seed_search_traces=v14.repo_union(
        seed_queries,limit_per_query=10,timeout=timeout
    )
    linked_repos,graph_traces=graph_snowball(
        query,seed_repos,timeout=timeout,max_seed_repos=8,max_links_per_seed=24
    )

    # Monotonic union: keep direct seeds, then add relevance-ranked graph
    # neighbors. Inspect graph neighbors first because they are the new route.
    inspection=[]
    seen=set()
    for repo in linked_repos+seed_repos:
        key=repo.casefold()
        if key not in seen:
            seen.add(key);inspection.append(repo)

    coords=[];coord_seen=set();manifest_traces=[]
    for repo in inspection[:32]:
        try:
            got,trace=v13.repository_pom_coordinates(repo,timeout=timeout,max_poms=20)
            status="SUCCESS";err=None
        except Exception as exc:
            got=[];trace={"repository":repo,"pom_files":[]}
            status="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:300]}"
        trace["status"]=status;trace["error"]=err
        manifest_traces.append(trace)
        for coord in got:
            key=coord.casefold()
            if key not in coord_seen:
                coord_seen.add(key);coords.append(coord)

    target=v11._norm(r["target"])
    norm=[v11._norm(x) for x in coords]
    hit=target in set(norm)
    return {
        "schema":SCHEMA,
        "status":"LIVE_CANDIDATE_GRAPH_SNOWBALL_PROBE_COMPLETE",
        "episode_id":EPISODE_ID,
        "seed_queries":seed_queries,
        "seed_repositories":seed_repos,
        "linked_repositories":linked_repos,
        "inspection_repositories":inspection,
        "candidate_ids":norm,
        "expected_target_answer_key":target,
        "target_hit":hit,
        "target_rank":norm.index(target)+1 if hit else None,
        "answer_key_identity_used_for_query_generation":False,
        "answer_key_identity_used_for_graph_ranking":False,
        "seed_search_traces":seed_search_traces,
        "graph_traces":graph_traces,
        "manifest_traces":manifest_traces,
        "latency_seconds":max(0.0,time.perf_counter()-start),
        "v14_union_hits":28,
        "v14_union_recall":28/30,
        "v14_plus_v16_union_hits":29 if hit else 28,
        "v14_plus_v16_union_recall":(29 if hit else 28)/30,
        "open_world_completeness_claim":False,
        "incremental_spend_usd":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "hard_rules":[
            "ONLY_THE_INDEPENDENTLY_OBSERVED_MAVEN_COLLECTIONS_RESIDUAL_IS_PROBED",
            "GRAPH_NEIGHBORS_ARE_RANKED_ONLY_BY_ORIGINAL_BEHAVIOR_AND_LOCAL_CANDIDATE_CONTEXT",
            "ANSWER_KEY_IDENTITY_IS_SCORING_ONLY",
            "SEED_AND_GRAPH_CANDIDATES_ARE_UNIONED_MONOTONICALLY",
            "FAILED_GRAPH_OR_MANIFEST_CALLS_REMAIN_RETRYABLE",
            "PACKAGE_CREDIT_REQUIRES_POM_GROUP_ARTIFACT_EXTRACTION",
            "FINITE_LIVE_RECOVERY_IS_NOT_OPEN_WORLD_COMPLETENESS",
        ],
    }

def main()->int:
    out=run()
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0 if out["target_hit"] else 2

if __name__=="__main__":
    raise SystemExit(main())
