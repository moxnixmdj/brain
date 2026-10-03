"""Complete discovery-source interface for universal tool-discovery V4.

This module is the executable meaning of a valid frozen discovery authority.
It is verifier/harness code, not hidden information supplied to the candidate.

A valid case must expose every tool identity in the common frozen authority
through either initial visibility or at least one available declared discovery
source. DISCOVER returns all public metadata bound to that source. Hidden
capability truth is never emitted.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

PUBLIC_TOOL_KEYS=(
    "tool_id","cost","available","authorized","epoch",
    "popularity","meta","schema_tags",
)

class InterfaceError(ValueError):
    pass

def _finite_nonnegative(value:Any,label:str)->float:
    if isinstance(value,bool):
        raise InterfaceError(label+":BOOLEAN_NOT_NUMBER")
    try:
        x=float(value)
    except (TypeError,ValueError):
        raise InterfaceError(label+":NOT_NUMBER")
    if not math.isfinite(x) or x<0:
        raise InterfaceError(label+":NOT_FINITE_NONNEGATIVE")
    return x

def _public_tool(raw:Mapping[str,Any])->dict[str,Any]:
    out={k:raw[k] for k in PUBLIC_TOOL_KEYS if k in raw}
    if not str(out.get("tool_id") or ""):
        raise InterfaceError("TOOL_ID_MISSING")
    _finite_nonnegative(out.get("cost",0.0),"TOOL_COST")
    if out.get("available") not in (True,False):
        raise InterfaceError("TOOL_AVAILABLE_NOT_BOOLEAN")
    if out.get("authorized") not in (True,False):
        raise InterfaceError("TOOL_AUTHORIZED_NOT_BOOLEAN")
    epoch=out.get("epoch",0)
    if isinstance(epoch,bool) or not isinstance(epoch,int) or epoch<0:
        raise InterfaceError("TOOL_EPOCH_INVALID")
    return out

def _canonical(obj:Any)->str:
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def validate_frozen_case(case:Mapping[str,Any])->dict[str,Any]:
    raw_tools=case.get("tools")
    raw_sources=case.get("discovery_sources")
    initial=case.get("initial_visible",[])
    if not isinstance(raw_tools,list) or not isinstance(raw_sources,list) or not isinstance(initial,list):
        raise InterfaceError("CASE_SHAPE_INVALID")

    tools:dict[str,dict[str,Any]]={}
    for raw in raw_tools:
        if not isinstance(raw,Mapping):
            raise InterfaceError("TOOL_NOT_MAPPING")
        pub=_public_tool(raw)
        tid=str(pub["tool_id"])
        if tid in tools:
            raise InterfaceError("DUPLICATE_TOOL_ID:"+tid)
        tools[tid]=pub

    initial_ids=[str(x) for x in initial]
    if len(set(initial_ids))!=len(initial_ids):
        raise InterfaceError("DUPLICATE_INITIAL_TOOL_ID")
    unknown_initial=sorted(set(initial_ids)-set(tools))
    if unknown_initial:
        raise InterfaceError("INITIAL_TOOL_UNKNOWN:"+",".join(unknown_initial))

    source_ids:set[str]=set()
    available_coverage:set[str]=set(initial_ids)
    normalized_sources=[]
    for raw in raw_sources:
        if not isinstance(raw,Mapping):
            raise InterfaceError("SOURCE_NOT_MAPPING")
        sid=str(raw.get("source_id") or "")
        if not sid:
            raise InterfaceError("SOURCE_ID_MISSING")
        if sid in source_ids:
            raise InterfaceError("DUPLICATE_SOURCE_ID:"+sid)
        source_ids.add(sid)
        _finite_nonnegative(raw.get("cost",0.0),"SOURCE_COST")
        available=raw.get("available")
        if available not in (True,False):
            raise InterfaceError("SOURCE_AVAILABLE_NOT_BOOLEAN")
        ids=raw.get("tool_ids")
        if not isinstance(ids,list):
            raise InterfaceError("SOURCE_TOOL_IDS_NOT_LIST:"+sid)
        tids=[str(x) for x in ids]
        if len(set(tids))!=len(tids):
            raise InterfaceError("DUPLICATE_SOURCE_TOOL_ID:"+sid)
        unknown=sorted(set(tids)-set(tools))
        if unknown:
            raise InterfaceError("SOURCE_TOOL_UNKNOWN:"+sid+":"+",".join(unknown))
        if available:
            available_coverage.update(tids)
        normalized_sources.append({
            "source_id":sid,
            "cost":float(raw.get("cost",0.0)),
            "available":available,
            "tool_ids":tids,
        })

    all_ids=set(tools)
    missing=sorted(all_ids-available_coverage)
    extra=sorted(available_coverage-all_ids)
    if missing or extra:
        raise InterfaceError(
            "INCOMPLETE_FROZEN_AUTHORITY_COVERAGE:"
            +"missing="+",".join(missing)+";extra="+",".join(extra)
        )

    public_manifest={
        "tools":[tools[k] for k in sorted(tools)],
        "initial_visible":sorted(initial_ids),
        "discovery_sources":sorted(normalized_sources,key=lambda x:x["source_id"]),
    }
    digest=hashlib.sha256(_canonical(public_manifest).encode("utf-8")).hexdigest()
    return {
        "valid":True,
        "tool_count":len(tools),
        "source_count":len(normalized_sources),
        "complete_identity_coverage":True,
        "authority_manifest_sha256":digest,
        "public_manifest":public_manifest,
    }

def initial_public_state(
    case:Mapping[str,Any],
    required_capabilities:list[str],
    constraint:Any=None,
    prior_probe_receipts:list[Mapping[str,Any]]|None=None,
    version_events:list[Mapping[str,Any]]|None=None,
)->dict[str,Any]:
    v=validate_frozen_case(case)
    manifest=v["public_manifest"]
    byid={x["tool_id"]:x for x in manifest["tools"]}
    return {
        "required_capabilities":list(required_capabilities),
        "constraint":constraint,
        "visible_tools":[byid[x] for x in manifest["initial_visible"]],
        "discovery_sources":[
            {"source_id":s["source_id"],"cost":s["cost"],"available":s["available"]}
            for s in manifest["discovery_sources"]
        ],
        "prior_probe_receipts":list(prior_probe_receipts or []),
        "discovery_receipts":[],
        "version_events":list(version_events or []),
        "frozen_authority_manifest_sha256":v["authority_manifest_sha256"],
    }

def discover(case:Mapping[str,Any],source_id:str,query:str)->dict[str,Any]:
    v=validate_frozen_case(case)
    manifest=v["public_manifest"]
    sid=str(source_id or "")
    if not isinstance(query,str) or not query.strip():
        raise InterfaceError("DISCOVERY_QUERY_EMPTY")
    source=next(
        (s for s in manifest["discovery_sources"] if s["source_id"]==sid),
        None,
    )
    if source is None or source["available"] is not True:
        raise InterfaceError("DISCOVERY_SOURCE_INVALID:"+sid)
    byid={x["tool_id"]:x for x in manifest["tools"]}
    return {
        "kind":"DISCOVERY_RESULT",
        "source_id":sid,
        "complete":True,
        "authority_manifest_sha256":v["authority_manifest_sha256"],
        "tools":[byid[x] for x in source["tool_ids"]],
    }

def apply_discovery(public:Mapping[str,Any],receipt:Mapping[str,Any])->dict[str,Any]:
    if receipt.get("kind")!="DISCOVERY_RESULT" or receipt.get("complete") is not True:
        raise InterfaceError("DISCOVERY_RECEIPT_NOT_COMPLETE")
    authority=str(public.get("frozen_authority_manifest_sha256") or "")
    if not authority or receipt.get("authority_manifest_sha256")!=authority:
        raise InterfaceError("DISCOVERY_AUTHORITY_MANIFEST_MISMATCH")
    sid=str(receipt.get("source_id") or "")
    sources={
        str(s.get("source_id")):s
        for s in public.get("discovery_sources",[])
        if isinstance(s,Mapping)
    }
    if sid not in sources or sources[sid].get("available") is not True:
        raise InterfaceError("DISCOVERY_RECEIPT_SOURCE_INVALID:"+sid)
    old_receipts=list(public.get("discovery_receipts",[]))
    if any(isinstance(x,Mapping) and str(x.get("source_id") or "")==sid for x in old_receipts):
        raise InterfaceError("DISCOVERY_SOURCE_ALREADY_QUERIED:"+sid)

    visible={
        str(t.get("tool_id")):dict(t)
        for t in public.get("visible_tools",[])
        if isinstance(t,Mapping)
    }
    for raw in receipt.get("tools",[]):
        if not isinstance(raw,Mapping):
            raise InterfaceError("DISCOVERED_TOOL_NOT_MAPPING")
        tool=_public_tool(raw)
        tid=str(tool["tool_id"])
        if tid in visible and _canonical(visible[tid])!=_canonical(tool):
            raise InterfaceError("CONFLICTING_PUBLIC_TOOL_METADATA:"+tid)
        visible[tid]=tool

    out=dict(public)
    out["visible_tools"]=[visible[k] for k in sorted(visible)]
    out["discovery_receipts"]=old_receipts+[dict(receipt)]
    return out
