#!/usr/bin/env python3
"""Zero-key HN Algolia candidate provider for technical/social discovery.

Candidate discovery only. No result implies nothing about nonexistence and no
returned candidate can grant acceptance, ownership, or promotion credit.
"""
from __future__ import annotations
import html, json, re, urllib.parse, urllib.request
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_SOCIAL_TECHNICAL_DISCUSSION_PROVIDER_V1"
SURFACE="SOCIAL_TECHNICAL_DISCUSSION"
UA="ProjectBrain-SocialDiscovery/1.0 (+zero-cost candidate discovery)"

def _canon(v: Any)->str:
    return " ".join(str(v or "").strip().split())

def _strip_html(v: Any)->str:
    return _canon(html.unescape(re.sub(r"<[^>]+>"," ",str(v or ""))))

def _fetch(url: str, timeout: int, opener=None)->dict[str,Any]:
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
    fn=opener or urllib.request.urlopen
    with fn(req,timeout=timeout) as resp:
        raw=resp.read(2_000_000)
    value=json.loads(raw.decode("utf-8","replace"))
    if not isinstance(value,dict):
        raise ValueError("HN_RESPONSE_NOT_OBJECT")
    return value

def search(action: Mapping[str,Any], *, limit: int=20, timeout: int=15, opener=None)->dict[str,Any]:
    if not isinstance(action,Mapping):
        raise ValueError("ACTION_MAPPING_REQUIRED")
    if _canon(action.get("surface"))!=SURFACE:
        raise ValueError("SOCIAL_SURFACE_REQUIRED")
    query=_canon(action.get("query"))
    if not query:
        raise ValueError("QUERY_REQUIRED")
    limit=max(1,min(int(limit),50))
    timeout=max(2,min(int(timeout),30))
    endpoint="https://hn.algolia.com/api/v1/search?"+urllib.parse.urlencode({
        "query":query,
        "hitsPerPage":limit,
    })
    data=_fetch(endpoint,timeout,opener=opener)
    rows=[]
    seen=set()
    for hit in data.get("hits") or []:
        if not isinstance(hit,Mapping):
            continue
        oid=_canon(hit.get("objectID"))
        if not oid:
            continue
        discussion_url="https://news.ycombinator.com/item?id="+urllib.parse.quote(oid,safe="")
        if discussion_url in seen:
            continue
        seen.add(discussion_url)
        external=_canon(hit.get("url") or hit.get("story_url")) or None
        rows.append({
            "candidate_id":discussion_url,
            "url":discussion_url,
            "external_url":external,
            "title":_canon(hit.get("title") or hit.get("story_title")) or None,
            "author":_canon(hit.get("author")) or None,
            "created_at":_canon(hit.get("created_at")) or None,
            "snippet":_strip_html(hit.get("comment_text") or hit.get("story_text"))[:1200] or None,
            "source_class":"SOCIAL_TECHNICAL_DISCUSSION_CANDIDATE",
            "discovery_backend":"HN_ALGOLIA_PUBLIC_SEARCH",
            "authority_status":"UNVERIFIED",
            "sufficiency_status":"UNVERIFIED",
        })
        if len(rows)>=limit:
            break
    return {
        "schema":SCHEMA,
        "backend_id":"HN_ALGOLIA_PUBLIC_SEARCH_V1",
        "source_epoch":"HN_ALGOLIA_PUBLIC_SEARCH_V1",
        "surface":SURFACE,
        "query":query,
        "candidates":rows,
        "candidate_count":len(rows),
        "complete":False,
        "independently_complete":False,
        "sufficiency_status":"UNVERIFIED",
        "no_result_means_nonexistence":False,
        "candidate_only":True,
        "acceptance_credit":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "incremental_spend_usd":0,
    }
