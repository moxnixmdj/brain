"""Tool Discovery common-authority manifest V2 for the V6 policy.

This environment-side adapter makes the public tool identity universe finite,
exact, content-addressed, and discoverable without exposing hidden capability
support. Safe-probe permission is public metadata; capability support is not.

It grants no acceptance/family/execution/promotion credit.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5

SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_COMMON_AUTHORITY_MANIFEST_V2"
PUBLIC_TOOL_KEYS=frozenset({
    "tool_id","cost","available","authorized","epoch",
    "safe_probe_capabilities","meta",
})

class ManifestError(ValueError):
    pass

def _canon(value: Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def _sha256(value: Any)->str:
    return "sha256:"+hashlib.sha256(_canon(value)).hexdigest()

def _norm_tool(raw: Mapping[str,Any])->dict[str,Any]:
    if not isinstance(raw,Mapping):
        raise ManifestError("TOOL_NOT_MAPPING")
    extra=set(raw)-PUBLIC_TOOL_KEYS
    if extra:
        raise ManifestError("TOOL_NONPUBLIC_FIELDS:"+",".join(sorted(extra)))
    tid=str(raw.get("tool_id") or "")
    if not tid:
        raise ManifestError("TOOL_ID_REQUIRED")
    cost=raw.get("cost")
    if isinstance(cost,bool) or not isinstance(cost,(int,float)) or not math.isfinite(float(cost)) or float(cost)<0:
        raise ManifestError("TOOL_COST_INVALID:"+tid)
    if not isinstance(raw.get("available"),bool):
        raise ManifestError("TOOL_AVAILABLE_INVALID:"+tid)
    if not isinstance(raw.get("authorized"),bool):
        raise ManifestError("TOOL_AUTHORIZED_INVALID:"+tid)
    epoch=raw.get("epoch")
    if isinstance(epoch,bool) or not isinstance(epoch,int) or epoch<0:
        raise ManifestError("TOOL_EPOCH_INVALID:"+tid)
    safe=raw.get("safe_probe_capabilities")
    if not isinstance(safe,list):
        raise ManifestError("SAFE_PROBE_CAPABILITIES_NOT_LIST:"+tid)
    safe_ids=sorted({str(x) for x in safe if str(x)})
    if any(any(ch.isspace() for ch in x) for x in safe_ids):
        raise ManifestError("SAFE_PROBE_CAPABILITY_ID_CONTAINS_WHITESPACE:"+tid)
    meta=raw.get("meta",{})
    if not isinstance(meta,Mapping):
        raise ManifestError("TOOL_META_INVALID:"+tid)
    return {
        "tool_id":tid,
        "cost":float(cost),
        "available":raw["available"],
        "authorized":raw["authorized"],
        "epoch":epoch,
        "safe_probe_capabilities":safe_ids,
        "meta":dict(meta),
    }

def authority_rows(instance: Mapping[str,Any])->list[dict[str,Any]]:
    rows=[_norm_tool(x) for x in instance.get("authority_tools",[])]
    rows.sort(key=lambda x:x["tool_id"])
    return rows

def _norm_sources(instance: Mapping[str,Any], by_id: Mapping[str,Mapping[str,Any]])->list[dict[str,Any]]:
    rows=[]
    seen=set()
    for raw in instance.get("discovery_sources",[]):
        if not isinstance(raw,Mapping):
            raise ManifestError("SOURCE_NOT_MAPPING")
        sid=str(raw.get("source_id") or "")
        if not sid or sid in seen:
            raise ManifestError("SOURCE_ID_INVALID_OR_DUPLICATE:"+sid)
        seen.add(sid)
        cost=raw.get("cost",0.0)
        if isinstance(cost,bool) or not isinstance(cost,(int,float)) or not math.isfinite(float(cost)) or float(cost)<0:
            raise ManifestError("SOURCE_COST_INVALID:"+sid)
        for field in ("available","authorized","authoritative"):
            if not isinstance(raw.get(field),bool):
                raise ManifestError("SOURCE_"+field.upper()+"_INVALID:"+sid)
        epoch=raw.get("source_epoch")
        if isinstance(epoch,bool) or not isinstance(epoch,int) or epoch<0:
            raise ManifestError("SOURCE_EPOCH_INVALID:"+sid)
        ids=[str(x) for x in raw.get("tool_ids",[])]
        if not ids or len(ids)!=len(set(ids)):
            raise ManifestError("SOURCE_TOOL_IDS_INVALID:"+sid)
        missing=sorted(set(ids)-set(by_id))
        if missing:
            raise ManifestError("SOURCE_UNKNOWN_TOOL_IDS:"+sid+":"+",".join(missing))
        tool_rows=[dict(by_id[x]) for x in sorted(ids)]
        rows.append({
            "source_id":sid,
            "cost":float(cost),
            "available":raw["available"],
            "authorized":raw["authorized"],
            "authoritative":raw["authoritative"],
            "source_epoch":epoch,
            "tool_ids":sorted(ids),
            "source_digest":v5._tools_digest(tool_rows),
        })
    rows.sort(key=lambda x:x["source_id"])
    return rows

def validate_instance(instance: Mapping[str,Any])->dict[str,Any]:
    if not isinstance(instance,Mapping) or instance.get("schema")!=SCHEMA:
        raise ManifestError("SCHEMA_MISMATCH")
    decision_epoch=instance.get("decision_epoch")
    if isinstance(decision_epoch,bool) or not isinstance(decision_epoch,int) or decision_epoch<0:
        raise ManifestError("DECISION_EPOCH_INVALID")

    tools=authority_rows(instance)
    ids=[x["tool_id"] for x in tools]
    if not ids or len(ids)!=len(set(ids)):
        raise ManifestError("AUTHORITY_TOOL_IDS_INVALID")
    by_id={x["tool_id"]:x for x in tools}

    root=_sha256(tools)
    if str(instance.get("authority_sha256") or "")!=root:
        raise ManifestError("AUTHORITY_HASH_MISMATCH")

    initial=[str(x) for x in instance.get("initial_visible_tool_ids",[])]
    if len(initial)!=len(set(initial)) or set(initial)-set(ids):
        raise ManifestError("INITIAL_VISIBLE_IDS_INVALID")

    sources=_norm_sources(instance,by_id)
    members=list(initial)
    for s in sources:
        # If a source owns hidden authority identities, it must be an available,
        # authorized authoritative discovery path in this decision epoch.
        if not (s["available"] and s["authorized"] and s["authoritative"]):
            raise ManifestError("PARTITION_SOURCE_NOT_DISCOVERABLE:"+s["source_id"])
        members.extend(s["tool_ids"])

    if len(members)!=len(set(members)):
        raise ManifestError("PARTITION_OVERLAP")
    if set(members)!=set(ids):
        raise ManifestError("PARTITION_NOT_EXACT")

    source_public=[
        {
            "source_id":s["source_id"],
            "cost":s["cost"],
            "available":s["available"],
            "authorized":s["authorized"],
            "authoritative":s["authoritative"],
            "source_epoch":s["source_epoch"],
            "source_digest":s["source_digest"],
        }
        for s in sources
    ]
    partition={
        "decision_epoch":decision_epoch,
        "authority_sha256":root,
        "initial_visible_tool_ids":sorted(initial),
        "sources":[
            {
                "source_id":s["source_id"],
                "tool_ids":s["tool_ids"],
                "source_epoch":s["source_epoch"],
                "source_digest":s["source_digest"],
            }
            for s in sources
        ],
    }
    partition_root=_sha256(partition)
    if str(instance.get("partition_sha256") or "")!=partition_root:
        raise ManifestError("PARTITION_HASH_MISMATCH")

    return {
        "decision_epoch":decision_epoch,
        "authority_sha256":root,
        "partition_sha256":partition_root,
        "authority_tool_count":len(tools),
        "complete_exact_partition":True,
        "source_public":source_public,
        "source_set_digest":v5._source_set_digest(source_public),
    }

def build_instance(
    *,
    decision_epoch:int,
    authority_tools:list[Mapping[str,Any]],
    initial_visible_tool_ids:list[str],
    discovery_sources:list[Mapping[str,Any]],
)->dict[str,Any]:
    tools=[_norm_tool(x) for x in authority_tools]
    tools.sort(key=lambda x:x["tool_id"])
    by_id={x["tool_id"]:x for x in tools}
    sources=_norm_sources({"discovery_sources":discovery_sources},by_id)
    initial=sorted(str(x) for x in initial_visible_tool_ids)
    root=_sha256(tools)
    partition={
        "decision_epoch":decision_epoch,
        "authority_sha256":root,
        "initial_visible_tool_ids":initial,
        "sources":[
            {
                "source_id":s["source_id"],
                "tool_ids":s["tool_ids"],
                "source_epoch":s["source_epoch"],
                "source_digest":s["source_digest"],
            }
            for s in sources
        ],
    }
    out={
        "schema":SCHEMA,
        "decision_epoch":decision_epoch,
        "authority_tools":tools,
        "authority_sha256":root,
        "initial_visible_tool_ids":initial,
        "discovery_sources":[
            {
                "source_id":s["source_id"],
                "cost":s["cost"],
                "available":s["available"],
                "authorized":s["authorized"],
                "authoritative":s["authoritative"],
                "source_epoch":s["source_epoch"],
                "tool_ids":s["tool_ids"],
            }
            for s in sources
        ],
        "partition_sha256":_sha256(partition),
    }
    validate_instance(out)
    return out

def initial_public(
    instance: Mapping[str,Any],
    *,
    required_capabilities:list[str],
    constraint:Any=None,
    prior_probe_receipts:list[Mapping[str,Any]]|None=None,
)->dict[str,Any]:
    state=validate_instance(instance)
    by_id={x["tool_id"]:x for x in authority_rows(instance)}
    return {
        "required_capabilities":list(required_capabilities),
        "decision_epoch":state["decision_epoch"],
        "constraint":constraint,
        "visible_tools":[dict(by_id[x]) for x in sorted(instance["initial_visible_tool_ids"])],
        "discovery_sources":[dict(x) for x in state["source_public"]],
        "discovery_receipts":[],
        "prior_probe_receipts":[dict(x) for x in (prior_probe_receipts or [])],
        "version_events":[],
        "_authority_sha256":state["authority_sha256"],
        "_partition_sha256":state["partition_sha256"],
    }

def discover(instance: Mapping[str,Any], public: Mapping[str,Any], source_id:str, query:str)->dict[str,Any]:
    state=validate_instance(instance)
    if public.get("decision_epoch")!=state["decision_epoch"]:
        raise ManifestError("PUBLIC_DECISION_EPOCH_MISMATCH")
    source=next((x for x in state["source_public"] if x["source_id"]==str(source_id)),None)
    raw_source=next((x for x in instance["discovery_sources"] if str(x["source_id"])==str(source_id)),None)
    if source is None or raw_source is None:
        raise ManifestError("SOURCE_UNKNOWN:"+str(source_id))
    by_id={x["tool_id"]:x for x in authority_rows(instance)}
    rows=[dict(by_id[str(x)]) for x in sorted(raw_source["tool_ids"])]
    if v5._tools_digest(rows)!=source["source_digest"]:
        raise ManifestError("SOURCE_CONTENT_DRIFT:"+str(source_id))
    return {
        "kind":"DISCOVERY_RESULT",
        "source_id":source["source_id"],
        "complete":True,
        "decision_epoch":state["decision_epoch"],
        "source_epoch":source["source_epoch"],
        "source_digest":source["source_digest"],
        "source_set_digest":state["source_set_digest"],
        "query":str(query),
        "tools":rows,
    }

def append_discovery(public: Mapping[str,Any], receipt: Mapping[str,Any])->dict[str,Any]:
    out=dict(public)
    receipts=[dict(x) for x in public.get("discovery_receipts",[])]
    if any(str(x.get("source_id") or "")==str(receipt.get("source_id") or "") for x in receipts):
        raise ManifestError("DUPLICATE_SOURCE_RECEIPT")
    receipts.append(dict(receipt))
    out["discovery_receipts"]=receipts
    return out

def append_probe(
    public: Mapping[str,Any],
    *,
    tool_id:str,
    capability:str,
    supported:bool,
)->dict[str,Any]:
    # Environment emits truth only after the candidate has asked for a probe
    # whose permission is explicitly public. This helper never stores hidden
    # support in the authority manifest.
    tools,err=v5._catalog(public,{
        str(x.get("source_id") or ""):x
        for x in public.get("discovery_receipts",[])
        if isinstance(x,Mapping)
    })
    if err:
        raise ManifestError(err)
    tool=next((x for x in tools if str(x.get("tool_id") or "")==str(tool_id)),None)
    if tool is None:
        raise ManifestError("PROBE_UNKNOWN_TOOL")
    safe=tool.get("safe_probe_capabilities")
    if not isinstance(safe,list) or capability not in {str(x) for x in safe}:
        raise ManifestError("PROBE_NOT_EXPLICITLY_SAFE")
    out=dict(public)
    receipts=[dict(x) for x in public.get("prior_probe_receipts",[])]
    receipts.append({
        "kind":"SAFE_CAPABILITY_PROBE",
        "tool_id":str(tool_id),
        "capability":str(capability),
        "epoch":tool["epoch"],
        "supported":bool(supported),
    })
    out["prior_probe_receipts"]=receipts
    return out
