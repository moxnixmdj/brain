#!/usr/bin/env python3
"""Model-independent first-party source-root discovery via Wikidata P856.

Scope is intentionally narrow: given a research subject/entity query, return
entity candidates and official website roots explicitly present in Wikidata's
P856 claims. This module does not claim that an official homepage contains the
answer to a research question and does not perform arbitrary web search.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import urllib.parse
import urllib.request

API="https://www.wikidata.org/w/api.php"
UA="ProjectBrain-FirstPartySourceDiscovery/1.0"
SCHEMA="PROJECT_BRAIN_FIRST_PARTY_SOURCE_ROOT_DISCOVERY_V1"


def _safe_path(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p!=root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _clean_query(value):
    q=" ".join(str(value or "").strip().split())
    if not q:
        raise RuntimeError("SOURCE_DISCOVERY_QUERY_REQUIRED")
    if len(q)>512:
        raise RuntimeError("SOURCE_DISCOVERY_QUERY_TOO_LONG")
    if any(ord(ch)<32 for ch in q):
        raise RuntimeError("SOURCE_DISCOVERY_QUERY_CONTROL_CHARACTER")
    return q


def _get_json(params, timeout_s=20, max_bytes=3_000_000):
    url=API+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(
        url,
        headers={
            "User-Agent":UA,
            "Accept":"application/json",
        },
    )
    with urllib.request.urlopen(req,timeout=max(1,min(int(timeout_s),60))) as resp:
        raw=resp.read(max_bytes+1)
        if len(raw)>max_bytes:
            raise RuntimeError("SOURCE_DISCOVERY_RESPONSE_TOO_LARGE")
        if getattr(resp,"status",200)!=200:
            raise RuntimeError("SOURCE_DISCOVERY_HTTP_STATUS_"+str(resp.status))
    try:
        payload=json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("SOURCE_DISCOVERY_JSON_INVALID") from exc
    if not isinstance(payload,dict):
        raise RuntimeError("SOURCE_DISCOVERY_JSON_NOT_OBJECT")
    return url,payload


def _official_urls(entity):
    claims=(entity or {}).get("claims") or {}
    rows=claims.get("P856") or []
    out=[]
    for row in rows:
        try:
            value=row["mainsnak"]["datavalue"]["value"]
        except Exception:
            continue
        if not isinstance(value,str):
            continue
        value=value.strip()
        try:
            parsed=urllib.parse.urlsplit(value)
        except Exception:
            continue
        if parsed.scheme not in {"http","https"} or not parsed.netloc:
            continue
        out.append(value)
    return list(dict.fromkeys(out))


def discover(query, language="en", max_results=8, timeout_s=20):
    q=_clean_query(query)
    language=str(language or "en").strip().lower()
    if not re.fullmatch(r"[a-z]{2,12}(?:-[a-z0-9]{2,12})?",language):
        raise RuntimeError("SOURCE_DISCOVERY_LANGUAGE_INVALID")
    limit=max(1,min(int(max_results),20))
    search_url,search_payload=_get_json(
        {
            "action":"wbsearchentities",
            "search":q,
            "language":language,
            "uselang":language,
            "format":"json",
            "limit":limit,
            "type":"item",
        },
        timeout_s=timeout_s,
    )
    search=search_payload.get("search") or []
    ids=[
        str(item.get("id") or "")
        for item in search
        if isinstance(item,dict) and re.fullmatch(r"Q[1-9][0-9]*",str(item.get("id") or ""))
    ]
    ids=list(dict.fromkeys(ids))[:limit]
    entities_url=None
    entities={}
    if ids:
        entities_url,entity_payload=_get_json(
            {
                "action":"wbgetentities",
                "ids":"|".join(ids),
                "props":"labels|descriptions|claims",
                "languages":language,
                "languagefallback":"1",
                "format":"json",
            },
            timeout_s=timeout_s,
        )
        entities=entity_payload.get("entities") or {}
        if not isinstance(entities,dict):
            entities={}

    candidates=[]
    by_id={str(item.get("id")):item for item in search if isinstance(item,dict)}
    for rank,qid in enumerate(ids,1):
        entity=entities.get(qid) or {}
        urls=_official_urls(entity)
        if not urls:
            continue
        item=by_id.get(qid) or {}
        label=str(item.get("label") or ((entity.get("labels") or {}).get(language) or {}).get("value") or "")
        description=str(item.get("description") or ((entity.get("descriptions") or {}).get(language) or {}).get("value") or "")
        candidates.append({
            "entity_id":qid,
            "search_rank":rank,
            "label":label,
            "description":description,
            "official_urls":urls,
            "authority_basis":"WIKIDATA_P856_OFFICIAL_WEBSITE",
        })
    return {
        "schema":SCHEMA,
        "status":"CANDIDATES_FOUND" if candidates else "NO_OFFICIAL_SITE_CANDIDATE",
        "query":q,
        "language":language,
        "candidate_count":len(candidates),
        "candidates":candidates,
        "provenance":{
            "provider":"Wikidata",
            "api":"MediaWiki/Wikibase API",
            "search_url":search_url,
            "entities_url":entities_url,
            "property":"P856",
            "property_semantics":"official website",
        },
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }


def run(args, root):
    out=discover(
        args.get("query"),
        language=args.get("language","en"),
        max_results=args.get("max_results",8),
        timeout_s=args.get("timeout_s",20),
    )
    path=_safe_path(root,args.get("output_path"))
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(out,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
    path.write_bytes(raw)
    return {
        "adapter":"authoritative_root_discovery_wikidata",
        "status":out["status"],
        "candidate_count":out["candidate_count"],
        "output_path":str(path.relative_to(pathlib.Path(root).resolve())),
        "output_sha256":hashlib.sha256(raw).hexdigest(),
        "output_verified":True,
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
