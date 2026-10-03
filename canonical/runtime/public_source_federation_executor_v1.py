#!/usr/bin/env python3
"""Execute one bounded wave of federated public-source retrieval requests."""
from __future__ import annotations
import hashlib, json, urllib.parse
from typing import Any, Callable, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_PUBLIC_SOURCE_FEDERATION_EXECUTOR_V1"

def _canon(x:Any)->str:
    return " ".join(str(x or "").strip().split())

def _host(url:Any)->str:
    try: return (urllib.parse.urlsplit(str(url or "")).hostname or "").lower()
    except Exception: return ""

def _host_matches(host:str,domain:str)->bool:
    h=host.lower().strip("."); d=domain.lower().strip(".")
    return h==d or h.endswith("."+d)

def plan_wave(requests:Sequence[Mapping[str,Any]],consumed_request_ids:Sequence[str]|None=None,wave_size:int=14)->list[dict[str,Any]]:
    consumed=set(consumed_request_ids or ())
    remaining=[dict(x) for x in requests if isinstance(x,Mapping) and _canon(x.get("request_id")) not in consumed]
    remaining.sort(key=lambda x:(int(x.get("selected_rank") or 0),str(x.get("domain") or ""),str(x.get("request_id") or "")))
    return remaining[:max(1,min(int(wave_size),256))]

def execute(
    federation:Mapping[str,Any],
    *,
    discover_fn:Callable[...,Mapping[str,Any]]|None=None,
    consumed_request_ids:Sequence[str]|None=None,
    wave_size:int=14,
    per_request_limit:int=8,
    timeout:int=12,
)->dict[str,Any]:
    if federation.get("schema")!="PROJECT_BRAIN_PUBLIC_SOURCE_FEDERATION_V2":
        raise ValueError("FEDERATION_V2_REQUIRED")
    requests=federation.get("requests")
    if not isinstance(requests,list) or not requests:
        raise ValueError("FEDERATION_REQUESTS_REQUIRED")
    if discover_fn is None:
        from canonical.runtime.bound_capabilities.open_web_source_candidate_discovery import discover as discover_fn
    wave=plan_wave(requests,consumed_request_ids,wave_size)
    traces=[]; candidates=[]; consumed=set(consumed_request_ids or ())
    for req in wave:
        rid=_canon(req.get("request_id")); domain=_canon(req.get("domain")); query=_canon(req.get("query"))
        if not rid or not domain or not query:
            traces.append({"request_id":rid or None,"state":"INVALID_REQUEST__UNKNOWN"})
            continue
        try:
            result=discover_fn(query,limit=per_request_limit,timeout=timeout,query_override=query)
            raw=result.get("candidates") or []
            kept=[]
            for cand in raw if isinstance(raw,list) else []:
                if not isinstance(cand,Mapping): continue
                url=_canon(cand.get("url"))
                if not url or not _host_matches(_host(url),domain): continue
                row=dict(cand); row["federation_request_id"]=rid; row["federation_domain"]=domain
                kept.append(row); candidates.append(row)
            state="QUERIED_CANDIDATE" if kept else "QUERIED_NO_CANDIDATE__UNKNOWN"
            traces.append({"request_id":rid,"domain":domain,"query":query,"state":state,"candidate_count":len(kept),"backend_status":result.get("status")})
            consumed.add(rid)
        except Exception as exc:
            traces.append({"request_id":rid,"domain":domain,"query":query,"state":"FAILED_TRANSIENT__UNKNOWN","candidate_count":0,"error_class":type(exc).__name__,"error":str(exc)[:300]})
    unique=[]; seen=set()
    for c in candidates:
        key=_canon(c.get("url"))
        if key and key not in seen:
            seen.add(key); unique.append(c)
    payload={"federation_program_sha256":federation.get("federation_program_sha256"),"traces":traces,"candidate_urls":[x.get("url") for x in unique]}
    epoch=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
    all_ids={_canon(x.get("request_id")) for x in requests if isinstance(x,Mapping) and _canon(x.get("request_id"))}
    remaining=sorted(all_ids-consumed)
    return {"schema":SCHEMA,"status":"WAVE_EXECUTED","executed_request_count":len(wave),"successful_or_empty_request_count":sum(1 for x in traces if str(x.get("state","")).startswith("QUERIED_")),"failed_request_count":sum(1 for x in traces if str(x.get("state","")).startswith("FAILED_")),"candidate_count":len(unique),"candidates":unique,"traces":traces,"consumed_request_ids":sorted(consumed),"remaining_request_ids":remaining,"remaining_request_count":len(remaining),"source_epoch_sha256":epoch,"complete":False,"nonexistence_claim_authorized":False,"acceptance_credit":0,"incremental_spend_usd":0,"hard_rules":["EMPTY_RESULT_IS_UNKNOWN_NOT_NONEXISTENCE","FAILED_REQUEST_IS_UNKNOWN_NOT_NONEXISTENCE","FEDERATED_CANDIDATES_REQUIRE_INDEPENDENT_VERIFICATION","SOURCE_EPOCH_SATURATION_IS_NOT_OPEN_WORLD_COMPLETENESS"]}
