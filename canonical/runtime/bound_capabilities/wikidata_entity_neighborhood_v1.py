#!/usr/bin/env python3
"""Model-independent bounded Wikidata graph-neighborhood retrieval V1.

Given Wikidata entity IDs, fetches their structured claims with wbgetentities,
then resolves property and linked-entity labels. Output is candidate evidence
only. No relation inference, answer selection, or correctness authority.
"""
from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from typing import Any, Callable, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_WIKIDATA_ENTITY_NEIGHBORHOOD_V1"
API="https://www.wikidata.org/w/api.php"
UA="ProjectBrain-WikidataNeighborhood/1.0 (+zero-cost model-independent research)"

class WikidataNeighborhoodError(RuntimeError):
    pass

def _canon(v:Any)->str:
    return " ".join(str(v or "").strip().split())

def _valid_id(v:str)->bool:
    return len(v)>=2 and v[0] in {"Q","P"} and v[1:].isdigit()

def _fetch(url:str, *, timeout:int=15)->bytes:
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        return resp.read(5_000_000)

def _api(ids:Sequence[str], *, props:str, timeout:int, fetch_fn:Callable[...,bytes])->dict[str,Any]:
    vals=[]
    for x in ids:
        x=_canon(x)
        if _valid_id(x) and x not in vals: vals.append(x)
    if not vals: return {}
    if len(vals)>50: raise ValueError("MAX_50_ENTITY_IDS_PER_CALL")
    url=API+"?"+urllib.parse.urlencode({
        "action":"wbgetentities",
        "ids":"|".join(vals),
        "props":props,
        "languages":"en",
        "languagefallback":"1",
        "format":"json",
        "origin":"*",
    })
    try:
        raw=fetch_fn(url,timeout=timeout)
        if isinstance(raw,str): raw=raw.encode()
        data=json.loads(bytes(raw).decode("utf-8","replace"))
    except Exception as exc:
        raise WikidataNeighborhoodError(type(exc).__name__+":"+str(exc)[:400]) from exc
    entities=data.get("entities") if isinstance(data,Mapping) else None
    if not isinstance(entities,Mapping):
        raise WikidataNeighborhoodError("ENTITIES_MAPPING_REQUIRED")
    return {str(k):dict(v) for k,v in entities.items() if isinstance(v,Mapping)}

def _term(entity:Mapping[str,Any], key:str)->str:
    x=entity.get(key)
    if not isinstance(x,Mapping): return ""
    en=x.get("en")
    if isinstance(en,Mapping): return _canon(en.get("value"))
    return ""

def _target_id(datavalue:Any)->str|None:
    if not isinstance(datavalue,Mapping): return None
    v=datavalue.get("value")
    if not isinstance(v,Mapping): return None
    qid=_canon(v.get("id"))
    if _valid_id(qid) and qid.startswith("Q"): return qid
    n=v.get("numeric-id")
    if isinstance(n,int) and n>0:return "Q"+str(n)
    return None

def _literal(datavalue:Any)->str:
    if not isinstance(datavalue,Mapping): return ""
    v=datavalue.get("value")
    if isinstance(v,(str,int,float,bool)): return _canon(v)
    if isinstance(v,Mapping):
        for key in ("text","time","amount","latitude","longitude"):
            if key in v and v.get(key) not in (None,""): return _canon(v.get(key))
    return ""

def neighborhood(
    entity_ids:Sequence[str],
    *,
    max_edges_per_entity:int=40,
    max_total_edges:int=100,
    timeout:int=15,
    fetch_fn:Callable[...,bytes]=_fetch,
)->dict[str,Any]:
    ids=[]
    for x in entity_ids:
        q=_canon(x)
        if not q.startswith("Q") or not _valid_id(q): raise ValueError("QID_REQUIRED")
        if q not in ids: ids.append(q)
    if not ids: raise ValueError("AT_LEAST_ONE_QID_REQUIRED")
    if len(ids)>10: raise ValueError("MAX_10_SOURCE_ENTITIES")
    max_edges_per_entity=max(1,min(int(max_edges_per_entity),100))
    max_total_edges=max(1,min(int(max_total_edges),250))
    timeout=max(2,min(int(timeout),30))

    sources={}
    for i in range(0,len(ids),50):
        sources.update(_api(ids[i:i+50],props="labels|descriptions|claims",timeout=timeout,fetch_fn=fetch_fn))

    raw_edges=[]; referenced=set(); properties=set()
    for sid in ids:
        src=sources.get(sid) or {}
        claims=src.get("claims")
        if not isinstance(claims,Mapping): continue
        count=0
        for pid,statements in claims.items():
            pid=_canon(pid)
            if not _valid_id(pid) or not pid.startswith("P") or not isinstance(statements,list): continue
            for st in statements:
                if count>=max_edges_per_entity or len(raw_edges)>=max_total_edges: break
                if not isinstance(st,Mapping): continue
                mainsnak=st.get("mainsnak")
                if not isinstance(mainsnak,Mapping): continue
                dv=mainsnak.get("datavalue")
                target=_target_id(dv)
                literal="" if target else _literal(dv)
                if not target and not literal: continue
                properties.add(pid)
                if target: referenced.add(target)
                raw_edges.append({"source_id":sid,"property_id":pid,"target_id":target,"literal_value":literal})
                count+=1
            if count>=max_edges_per_entity or len(raw_edges)>=max_total_edges: break
        if len(raw_edges)>=max_total_edges: break

    refs=sorted(referenced|properties)
    resolved={}
    for i in range(0,len(refs),50):
        resolved.update(_api(refs[i:i+50],props="labels|descriptions",timeout=timeout,fetch_fn=fetch_fn))

    edges=[]
    for e in raw_edges:
        src=sources.get(e["source_id"]) or {}
        prop=resolved.get(e["property_id"]) or {}
        target=resolved.get(e["target_id"]) or {} if e["target_id"] else {}
        edges.append({
            **e,
            "source_label":_term(src,"labels"),
            "source_description":_term(src,"descriptions"),
            "property_label":_term(prop,"labels"),
            "property_description":_term(prop,"descriptions"),
            "target_label":_term(target,"labels") if target else "",
            "target_description":_term(target,"descriptions") if target else "",
            "authority_status":"UNVERIFIED_STRUCTURED_CANDIDATE_ONLY",
            "answer_authority":False,
            "correctness_authority":False,
        })

    return {
        "schema":SCHEMA,
        "status":"NEIGHBORHOOD_RETRIEVED" if edges else "NO_EDGES",
        "source_entity_ids":ids,
        "edge_count":len(edges),
        "edges":edges,
        "source_snapshot_sha256":hashlib.sha256(json.dumps(raw_edges,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
        "endpoint":"WIKIDATA_MEDIAWIKI_ACTION_API_WBGETENTITIES",
        "gold_accessed":False,
        "external_model_calls":0,
        "external_reasoning_model_calls":0,
        "model_dependency_count":0,
        "answer_authority":False,
        "correctness_authority":False,
        "nonexistence_claim_authorized":False,
        "incremental_spend_usd":0,
        "hard_rules":[
            "ONE_HOP_GRAPH_RETRIEVAL_ONLY",
            "NO_RELATION_INFERENCE",
            "LINKED_ENTITY_AND_PROPERTY_LABELS_ARE_CANDIDATE_EVIDENCE_ONLY",
            "NO_MODEL_COGNITION_OR_GOLD_ACCESS",
        ],
    }

if __name__=="__main__":
    print(json.dumps(neighborhood(["Q42"],max_edges_per_entity=5),indent=2,ensure_ascii=False))
