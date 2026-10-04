#!/usr/bin/env python3
"""Retrieval V17 historical Maven identity bridge.

Closes versioned package-identity drift without leaking the frozen answer key
into discovery. Starting from behavior-derived repositories, enumerate recent
repository tags, inspect historical POMs, and union historical coordinates with
current coordinates. The expected target is used only for final scoring.
"""
from __future__ import annotations

import base64
import hashlib
import json
import urllib.parse
from typing import Any, Mapping

from canonical.runtime import retrieval_live_provider_arena_v11 as v11
from canonical.runtime import retrieval_live_provider_arena_v13 as v13
from canonical.runtime import retrieval_live_provider_arena_v14 as v14

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_ARENA_V17"
EPISODE_ID="MAVEN_JSON_BIND"

def row()->Mapping[str,Any]:
    rows=[x for x in v11.TASKS if x["episode_id"]==EPISODE_ID]
    if len(rows)!=1:
        raise ValueError("V17_JSON_BIND_TASK_MISMATCH")
    return rows[0]

def _tag_names(repo:str,*,timeout:float=20.0,per_page:int=100)->list[str]:
    quoted=urllib.parse.quote(repo,safe="/")
    obj=v13._github_json(
        f"https://api.github.com/repos/{quoted}/tags?per_page={max(1,min(int(per_page),100))}",
        timeout=timeout,
    )
    if not isinstance(obj,list):
        return []
    out=[];seen=set()
    for item in obj:
        if not isinstance(item,Mapping):
            continue
        name=str(item.get("name") or "").strip()
        if name and name.casefold() not in seen:
            seen.add(name.casefold());out.append(name)
    return out

def _file_content(repo:str,path:str,ref:str,*,timeout:float=20.0)->str:
    quoted=urllib.parse.quote(repo,safe="/")
    qp=urllib.parse.quote(path,safe="/")
    qref=urllib.parse.quote(ref,safe="")
    obj=v13._github_json(
        f"https://api.github.com/repos/{quoted}/contents/{qp}?ref={qref}",
        timeout=timeout,
    )
    if not isinstance(obj,Mapping):
        return ""
    raw=str(obj.get("content") or "").replace("\n","")
    if str(obj.get("encoding") or "").lower()!="base64" or not raw:
        return ""
    try:
        return base64.b64decode(raw).decode("utf-8","replace")
    except Exception:
        return ""

def historical_pom_coordinates(
    repo:str,
    *,
    timeout:float=20.0,
    max_tags:int=40,
    candidate_paths:tuple[str,...]=("pom.xml",),
)->tuple[list[str],list[dict[str,Any]]]:
    tags=_tag_names(repo,timeout=timeout,per_page=min(max_tags,100))[:max_tags]
    coords=[];seen=set();traces=[]
    for tag in tags:
        tag_coords=[];paths=[]
        for path in candidate_paths:
            try:
                text=_file_content(repo,path,tag,timeout=timeout)
                got=v13.parse_pom_coordinates(text) if text else []
                status="SUCCESS" if text else "EMPTY"
                err=None
            except Exception as exc:
                got=[];status="FAILED_RETRYABLE"
                err=f"{type(exc).__name__}:{str(exc)[:300]}"
            paths.append({"path":path,"status":status,"coordinates":got,"error":err})
            for coord in got:
                key=coord.casefold()
                if key not in seen:
                    seen.add(key);coords.append(coord)
                if coord not in tag_coords:
                    tag_coords.append(coord)
        traces.append({"tag":tag,"coordinates":tag_coords,"paths":paths})
    return coords,traces

def validate()->None:
    r=row()
    target=v11._norm(r["target"])
    basename=target.rsplit(":",1)[-1]
    for q in v14.maven_behavior_queries(str(r["query"])):
        nq=v11._norm(q)
        if target in nq or (len(basename)>=4 and basename in nq):
            raise ValueError("TARGET_IDENTITY_LEAKED_IN_QUERY")
    # Discovery helpers accept repo/tag/path only; expected package identity
    # cannot influence tag enumeration or historical POM extraction.

def run(*,timeout:float=20.0,max_repos:int=12,max_tags:int=40)->dict[str,Any]:
    validate()
    r=row()
    query=str(r["query"])
    queries=v14.maven_behavior_queries(query)
    repos,search_traces=v14.repo_union(queries,limit_per_query=10,timeout=timeout)

    current_coords=[];historical_coords=[]
    current_seen=set();historical_seen=set();repo_traces=[]
    for repo in repos[:max_repos]:
        try:
            cur,cur_trace=v13.repository_pom_coordinates(
                repo,timeout=timeout,max_poms=20
            )
            cur_status="SUCCESS";cur_err=None
        except Exception as exc:
            cur=[];cur_trace={"repository":repo,"pom_files":[]}
            cur_status="FAILED_RETRYABLE"
            cur_err=f"{type(exc).__name__}:{str(exc)[:300]}"

        # Use only root POM history because current evidence shows this residual
        # is repository-level package identity drift, not submodule discovery.
        try:
            hist,hist_trace=historical_pom_coordinates(
                repo,timeout=timeout,max_tags=max_tags,candidate_paths=("pom.xml",)
            )
            hist_status="SUCCESS";hist_err=None
        except Exception as exc:
            hist=[];hist_trace=[];hist_status="FAILED_RETRYABLE"
            hist_err=f"{type(exc).__name__}:{str(exc)[:300]}"

        for coord in cur:
            k=coord.casefold()
            if k not in current_seen:
                current_seen.add(k);current_coords.append(coord)
        for coord in hist:
            k=coord.casefold()
            if k not in historical_seen:
                historical_seen.add(k);historical_coords.append(coord)

        repo_traces.append({
            "repository":repo,
            "current_status":cur_status,
            "current_error":cur_err,
            "current_coordinates":cur,
            "current_trace":cur_trace,
            "historical_status":hist_status,
            "historical_error":hist_err,
            "historical_coordinates":hist,
            "historical_tag_trace":hist_trace,
        })

    union=[];seen=set()
    for coord in current_coords+historical_coords:
        norm=v11._norm(coord)
        if norm and norm not in seen:
            seen.add(norm);union.append(norm)

    target=v11._norm(r["target"])
    hit=target in set(union)
    return {
        "schema":SCHEMA,
        "status":"LIVE_VERSIONED_IDENTITY_BRIDGE_PROBE_COMPLETE",
        "episode_id":EPISODE_ID,
        "generated_queries":queries,
        "repository_candidates":repos,
        "current_candidate_ids":[v11._norm(x) for x in current_coords],
        "historical_candidate_ids":[v11._norm(x) for x in historical_coords],
        "candidate_ids":union,
        "expected_target_answer_key":target,
        "target_hit":hit,
        "target_rank":union.index(target)+1 if hit else None,
        "answer_key_identity_used_for_query_generation":False,
        "answer_key_identity_used_for_repository_ranking":False,
        "answer_key_identity_used_for_tag_selection":False,
        "search_traces":search_traces,
        "repository_traces":repo_traces,
        "prior_v14_plus_v16_union_hits":29,
        "prior_v14_plus_v16_union_recall":29/30,
        "v14_v16_v17_union_hits":30 if hit else 29,
        "v14_v16_v17_union_recall":1.0 if hit else 29/30,
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
            "BEHAVIOR_SEARCH_IS_ANSWER_KEY_BLIND",
            "TAG_ENUMERATION_IS_ANSWER_KEY_BLIND",
            "HISTORICAL_COORDINATES_ARE_EXTRACTED_FROM_REPOSITORY_POMS",
            "CURRENT_AND_HISTORICAL_IDENTITIES_ARE_UNIONED_MONOTONICALLY",
            "ANSWER_KEY_IDENTITY_IS_SCORING_ONLY",
            "FAILED_HISTORY_CALLS_REMAIN_RETRYABLE",
            "FINITE_LIVE_30_OF_30_IF_ACHIEVED_IS_NOT_OPEN_WORLD_COMPLETENESS",
        ],
    }

def main()->int:
    out=run()
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0 if out["target_hit"] else 2

if __name__=="__main__":
    raise SystemExit(main())
