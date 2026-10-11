#!/usr/bin/env python3
"""Model-independent Wikidata entity discovery V1.

Uses Wikidata's public MediaWiki Action API wbsearchentities endpoint to expose
structured entity labels/descriptions as candidate evidence. This primitive
does not answer questions, infer relations, or grant correctness authority.
"""
from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from typing import Any, Callable, Mapping

SCHEMA="PROJECT_BRAIN_WIKIDATA_ENTITY_SEARCH_V1"
API="https://www.wikidata.org/w/api.php"
UA="ProjectBrain-WikidataEntitySearch/1.0 (+zero-cost model-independent research)"

class WikidataSearchError(RuntimeError):
    pass

def _canon(v:Any)->str:
    return " ".join(str(v or "").strip().split())

def _fetch(url:str, *, timeout:int=15)->bytes:
    req=urllib.request.Request(
        url,
        headers={"User-Agent":UA,"Accept":"application/json"},
    )
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        return resp.read(2_000_000)

def search(
    query:str,
    *,
    limit:int=8,
    language:str="en",
    timeout:int=15,
    fetch_fn:Callable[...,bytes]=_fetch,
)->dict[str,Any]:
    q=_canon(query)
    if not q: raise ValueError("QUERY_REQUIRED")
    if len(q)>600: raise ValueError("QUERY_TOO_LONG")
    limit=max(1,min(int(limit),20))
    timeout=max(2,min(int(timeout),30))
    lang=_canon(language).lower()
    if not lang or len(lang)>12 or not all(ch.isalnum() or ch in "-_" for ch in lang):
        raise ValueError("LANGUAGE_INVALID")
    url=API+"?"+urllib.parse.urlencode({
        "action":"wbsearchentities",
        "search":q,
        "language":lang,
        "uselang":lang,
        "type":"item",
        "limit":str(limit),
        "format":"json",
        "origin":"*",
    })
    try:
        raw=fetch_fn(url,timeout=timeout)
        if isinstance(raw,str): raw=raw.encode("utf-8")
        data=json.loads(bytes(raw).decode("utf-8","replace"))
    except Exception as exc:
        raise WikidataSearchError(type(exc).__name__+":"+str(exc)[:400]) from exc
    rows=data.get("search") if isinstance(data,Mapping) else None
    if not isinstance(rows,list):
        raise WikidataSearchError("SEARCH_LIST_REQUIRED")
    out=[];seen=set()
    for rank,row in enumerate(rows):
        if not isinstance(row,Mapping): continue
        qid=_canon(row.get("id"))
        if not re_qid(qid) or qid in seen: continue
        seen.add(qid)
        out.append({
            "entity_id":qid,
            "label":_canon(row.get("label")),
            "description":_canon(row.get("description")),
            "concept_uri":_canon(row.get("concepturi")),
            "url":_canon(row.get("url")),
            "match":dict(row.get("match") or {}) if isinstance(row.get("match"),Mapping) else {},
            "rank":rank,
            "source":"WIKIDATA_WBSEARCHENTITIES",
            "authority_status":"UNVERIFIED_CANDIDATE_ONLY",
            "answer_authority":False,
            "correctness_authority":False,
        })
    return {
        "schema":SCHEMA,
        "status":"CANDIDATES_DISCOVERED" if out else "NO_CANDIDATES",
        "query":q,
        "query_sha256":hashlib.sha256(q.encode("utf-8")).hexdigest(),
        "language":lang,
        "candidate_count":len(out),
        "candidates":out,
        "endpoint":"WIKIDATA_MEDIAWIKI_ACTION_API_WBSEARCHENTITIES",
        "gold_accessed":False,
        "external_model_calls":0,
        "external_reasoning_model_calls":0,
        "model_dependency_count":0,
        "answer_authority":False,
        "correctness_authority":False,
        "nonexistence_claim_authorized":False,
        "incremental_spend_usd":0,
        "hard_rules":[
            "ENTITY_SEARCH_RESULTS_ARE_CANDIDATE_ONLY",
            "EMPTY_SEARCH_DOES_NOT_AUTHORIZE_NONEXISTENCE",
            "NO_MODEL_COGNITION",
            "NO_ANSWER_OR_CORRECTNESS_AUTHORITY",
        ],
    }

def re_qid(v:str)->bool:
    return len(v)>=2 and v[0]=="Q" and v[1:].isdigit()

if __name__=="__main__":
    x=search("New York",limit=1)
    print(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2))
