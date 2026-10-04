#!/usr/bin/env python3
"""Retrieval V18 version-line Maven identity recovery.

Repairs the V17 failure where prerelease suffix digits (for example rc10)
were misclassified as the semantic major version. V18 parses the first
dotted semantic version in a tag name, samples repository tags by true major
line, and extracts historical Maven coordinates from representative tags.

The frozen answer key is used only for final scoring.
"""
from __future__ import annotations

import base64
import json
import re
import time
import urllib.parse
from typing import Any, Mapping

from canonical.runtime import retrieval_live_provider_arena_v11 as v11
from canonical.runtime import retrieval_live_provider_arena_v13 as v13
from canonical.runtime import retrieval_live_provider_arena_v14 as v14

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_ARENA_V18"
EPISODE_ID="MAVEN_JSON_BIND"
SEMVER=re.compile(r"(?<!\d)(\d+)\.(\d+)(?:\.(\d+))?")

def row()->Mapping[str,Any]:
    rows=[x for x in v11.TASKS if x["episode_id"]==EPISODE_ID]
    if len(rows)!=1:
        raise ValueError("V18_JSON_BIND_TASK_MISMATCH")
    return rows[0]

def semantic_version_from_tag(name:str)->tuple[int,int,int|None]|None:
    """Parse the first dotted semantic version, ignoring prerelease suffix digits."""
    m=SEMVER.search(str(name or ""))
    if not m:
        return None
    return (int(m.group(1)),int(m.group(2)),int(m.group(3)) if m.group(3) is not None else None)

def list_tags(repo:str,*,timeout:float=20.0,max_pages:int=3)->list[dict[str,Any]]:
    quoted=urllib.parse.quote(repo,safe="/")
    out=[];seen=set()
    for page in range(1,max(1,min(max_pages,5))+1):
        obj=v13._github_json(
            f"https://api.github.com/repos/{quoted}/tags?per_page=100&page={page}",
            timeout=timeout,
        )
        if not isinstance(obj,list) or not obj:
            break
        for item in obj:
            if not isinstance(item,Mapping):
                continue
            name=str(item.get("name") or "").strip()
            commit=item.get("commit") if isinstance(item.get("commit"),Mapping) else {}
            sha=str(commit.get("sha") or "").strip()
            key=(name.casefold(),sha)
            if not name or key in seen:
                continue
            seen.add(key)
            ver=semantic_version_from_tag(name)
            out.append({
                "name":name,
                "commit_sha":sha,
                "semantic_version":list(ver) if ver else None,
                "version_major":ver[0] if ver else None,
                "version_minor":ver[1] if ver else None,
                "version_patch":ver[2] if ver else None,
            })
        if len(obj)<100:
            break
    return out

def select_version_line_tags(tags:list[Mapping[str,Any]],*,max_per_major:int=2,max_unknown:int=2)->list[dict[str,Any]]:
    """Preserve major-version diversity without using package answer keys."""
    by_major:dict[int,list[dict[str,Any]]]={}
    unknown=[]
    for raw in tags:
        row=dict(raw)
        major=row.get("version_major")
        if isinstance(major,int):
            by_major.setdefault(major,[]).append(row)
        else:
            unknown.append(row)

    selected=[]
    # Prefer recent representatives from every observed major line.
    for major in sorted(by_major,reverse=True):
        selected.extend(by_major[major][:max(1,max_per_major)])
    selected.extend(unknown[:max_unknown])
    return selected

def repository_pom_paths(repo:str,*,timeout:float=20.0,max_poms:int=20)->list[str]:
    quoted=urllib.parse.quote(repo,safe="/")
    info=v13._github_json(f"https://api.github.com/repos/{quoted}",timeout=timeout)
    branch=str(info.get("default_branch") or "main")
    tree=v13._github_json(
        f"https://api.github.com/repos/{quoted}/git/trees/{urllib.parse.quote(branch,safe='')}?recursive=1",
        timeout=timeout,
    )
    rows=[
        str(x.get("path"))
        for x in (tree.get("tree") or [])
        if isinstance(x,Mapping)
        and x.get("type")=="blob"
        and str(x.get("path") or "").endswith("pom.xml")
    ]
    rows.sort(key=lambda p:(p.count("/"),len(p),p))
    return rows[:max_poms]

def pom_at_ref(repo:str,path:str,ref:str,*,timeout:float=20.0)->str:
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

def historical_coordinates(
    repo:str,
    *,
    timeout:float=20.0,
    max_pages:int=3,
    max_per_major:int=2,
    max_poms:int=20,
)->dict[str,Any]:
    tags=list_tags(repo,timeout=timeout,max_pages=max_pages)
    selected=select_version_line_tags(tags,max_per_major=max_per_major)
    paths=repository_pom_paths(repo,timeout=timeout,max_poms=max_poms)
    if not paths:
        paths=["pom.xml"]

    coords=[];seen=set();probes=[]
    for tag in selected:
        for path in paths:
            start=time.perf_counter()
            try:
                xml=pom_at_ref(repo,path,str(tag["name"]),timeout=timeout)
                got=v13.parse_pom_coordinates(xml) if xml else []
                status="SUCCESS" if xml else "EMPTY"
                err=None
            except Exception as exc:
                got=[];status="FAILED_RETRYABLE"
                err=f"{type(exc).__name__}:{str(exc)[:300]}"
            for coord in got:
                key=coord.casefold()
                if key not in seen:
                    seen.add(key);coords.append(coord)
            probes.append({
                "tag":tag["name"],
                "version_major":tag.get("version_major"),
                "path":path,
                "status":status,
                "coordinates":got,
                "error":err,
                "latency_seconds":max(0.0,time.perf_counter()-start),
            })
    return {
        "repository":repo,
        "tag_count":len(tags),
        "selected_tags":selected,
        "current_pom_paths":paths,
        "coordinates":coords,
        "coordinate_count":len(coords),
        "probes":probes,
    }

def validate()->None:
    r=row()
    target=v11._norm(r["target"])
    basename=target.rsplit(":",1)[-1]
    for q in v14.maven_behavior_queries(str(r["query"])):
        nq=v11._norm(q)
        if target in nq or (len(basename)>=4 and basename in nq):
            raise ValueError("TARGET_IDENTITY_LEAKED_IN_QUERY")
    # All version-line functions are independent of expected target identity.

def run(*,timeout:float=20.0,max_repos:int=12)->dict[str,Any]:
    validate()
    r=row()
    queries=v14.maven_behavior_queries(str(r["query"]))
    repos,search_traces=v14.repo_union(queries,limit_per_query=10,timeout=timeout)

    coords=[];seen=set();traces=[]
    for repo in repos[:max_repos]:
        try:
            trace=historical_coordinates(
                repo,timeout=timeout,max_pages=3,max_per_major=2,max_poms=20
            )
            status="SUCCESS";err=None
        except Exception as exc:
            trace={"repository":repo,"coordinates":[],"selected_tags":[],"probes":[]}
            status="FAILED_RETRYABLE"
            err=f"{type(exc).__name__}:{str(exc)[:400]}"
        trace["status"]=status;trace["error"]=err
        traces.append(trace)
        for coord in trace.get("coordinates") or []:
            norm=v11._norm(coord)
            if norm and norm not in seen:
                seen.add(norm);coords.append(norm)

    target=v11._norm(r["target"])
    hit=target in set(coords)
    return {
        "schema":SCHEMA,
        "status":"LIVE_VERSION_LINE_HISTORY_IDENTITY_BRIDGE_COMPLETE",
        "episode_id":EPISODE_ID,
        "generated_queries":queries,
        "repository_candidates":repos,
        "candidate_ids":coords,
        "expected_target_answer_key":target,
        "target_hit":hit,
        "target_rank":coords.index(target)+1 if hit else None,
        "answer_key_identity_used_for_query_generation":False,
        "answer_key_identity_used_for_repository_selection":False,
        "answer_key_identity_used_for_tag_selection":False,
        "answer_key_identity_used_for_pom_extraction":False,
        "search_traces":search_traces,
        "history_traces":traces,
        "prior_v16_union_hits":29,
        "prior_v16_union_recall":29/30,
        "v16_plus_v18_union_hits":30 if hit else 29,
        "v16_plus_v18_union_recall":1.0 if hit else 29/30,
        "open_world_completeness_claim":False,
        "incremental_spend_usd":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "hard_rules":[
            "ONLY_THE_INDEPENDENTLY_OBSERVED_VERSIONED_IDENTITY_RESIDUAL_IS_PROBED",
            "SEMANTIC_MAJOR_IS_PARSED_FROM_DOTTED_VERSION_NOT_PRERELEASE_SUFFIX_DIGITS",
            "TAG_SELECTION_IS_MAJOR_LINE_DIVERSE_AND_ANSWER_KEY_BLIND",
            "HISTORICAL_PACKAGE_CREDIT_REQUIRES_POM_GROUP_ARTIFACT_EXTRACTION",
            "CURRENT_AND_HISTORICAL_IDENTITIES_ARE_UNIONED_MONOTONICALLY",
            "FAILED_HISTORY_CALLS_REMAIN_RETRYABLE",
            "FINITE_30_CASE_RECALL_IS_NOT_OPEN_WORLD_COMPLETENESS",
        ],
    }

def main()->int:
    out=run()
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0 if out["target_hit"] else 2

if __name__=="__main__":
    raise SystemExit(main())
