"""Exact common-frozen-authority identity-scope theorem for Tool Discovery.

This proves only an identity/scope relation for one frozen matched Brain/Opus
tool-authority instance. It does NOT prove that such an instance currently
exists, that capabilities are observable, or that Tool Discovery acceptance
closes. Those remain separate obligations.

A proof instance is admissible iff:
* Brain and Opus are bound to the exact same finite public authority manifest;
* authoritative discovery source IDs are unique and finite;
* each admitted source result is exact, current-epoch and source-bound;
* the union of authoritative discovery results equals the frozen manifest
  exactly: no missing and no extra tool identities or metadata.

The theorem is deliberately capability-agnostic. Hidden capability truth is not
allowed into the identity proof.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_COMMON_FROZEN_AUTHORITY_SCOPE_THEOREM_V1"


def _canon(value: Any) -> bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")


def _sha(value: Any) -> str:
    return "sha256:"+hashlib.sha256(_canon(value)).hexdigest()


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema":SCHEMA,
        "status":"FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "identity_scope_complete":False,
        "scope_relation":None,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }


def _public_tool(raw: Any) -> tuple[dict[str,Any] | None,str | None]:
    if not isinstance(raw,Mapping):
        return None,"TOOL_NOT_OBJECT"
    tid=str(raw.get("tool_id") or "")
    if not tid:
        return None,"TOOL_ID_MISSING"
    forbidden={"hidden_capabilities","supported_capabilities","capabilities","_oracle","oracle"}
    if forbidden & set(raw):
        return None,"HIDDEN_CAPABILITY_FIELD_IN_PUBLIC_MANIFEST:"+tid
    cost=raw.get("cost",0.0)
    if isinstance(cost,bool) or not isinstance(cost,(int,float)) or not math.isfinite(float(cost)) or float(cost)<0:
        return None,"TOOL_COST_INVALID:"+tid
    out=dict(raw)
    out["tool_id"]=tid
    out["cost"]=float(cost)
    return out,None


def prove(instance: Mapping[str,Any]) -> dict[str,Any]:
    errors:list[str]=[]
    epoch=instance.get("decision_epoch")
    if isinstance(epoch,bool) or not isinstance(epoch,int) or epoch<0:
        errors.append("DECISION_EPOCH_INVALID")

    raw_manifest=instance.get("authority_manifest")
    if not isinstance(raw_manifest,list) or not raw_manifest:
        return _fail("AUTHORITY_MANIFEST_MUST_BE_NONEMPTY_FINITE_LIST")

    manifest:list[dict[str,Any]]=[]
    ids:set[str]=set()
    for raw in raw_manifest:
        row,err=_public_tool(raw)
        if err:
            errors.append(err); continue
        assert row is not None
        tid=row["tool_id"]
        if tid in ids:
            errors.append("DUPLICATE_MANIFEST_TOOL_ID:"+tid)
        ids.add(tid); manifest.append(row)
    manifest.sort(key=lambda r:r["tool_id"])
    manifest_digest=_sha(manifest)

    for route in ("brain","opus"):
        view=instance.get(route)
        if not isinstance(view,Mapping):
            errors.append(route.upper()+"_VIEW_MISSING")
            continue
        if view.get("decision_epoch")!=epoch:
            errors.append(route.upper()+"_DECISION_EPOCH_MISMATCH")
        if str(view.get("authority_manifest_sha256") or "")!=manifest_digest:
            errors.append(route.upper()+"_AUTHORITY_DIGEST_MISMATCH")

    sources=instance.get("discovery_sources")
    if not isinstance(sources,list) or not sources:
        return _fail(*(errors+["DISCOVERY_SOURCES_MUST_BE_NONEMPTY_FINITE_LIST"]))
    source_ids:set[str]=set()
    active:dict[str,Mapping[str,Any]]={}
    for raw in sources:
        if not isinstance(raw,Mapping):
            errors.append("DISCOVERY_SOURCE_NOT_OBJECT"); continue
        sid=str(raw.get("source_id") or "")
        if not sid:
            errors.append("DISCOVERY_SOURCE_ID_MISSING"); continue
        if sid in source_ids:
            errors.append("DUPLICATE_DISCOVERY_SOURCE_ID:"+sid)
        source_ids.add(sid)
        for flag in ("authoritative","available","authorized"):
            if not isinstance(raw.get(flag),bool):
                errors.append("DISCOVERY_SOURCE_"+flag.upper()+"_NOT_BOOL:"+sid)
        se=raw.get("source_epoch")
        if isinstance(se,bool) or not isinstance(se,int) or se<0:
            errors.append("DISCOVERY_SOURCE_EPOCH_INVALID:"+sid)
        if raw.get("authoritative") is True and raw.get("available") is True and raw.get("authorized") is True:
            active[sid]=raw

    results=instance.get("discovery_results")
    if not isinstance(results,list):
        return _fail(*(errors+["DISCOVERY_RESULTS_NOT_LIST"]))

    by_source:dict[str,Mapping[str,Any]]={}
    for rec in results:
        if not isinstance(rec,Mapping):
            errors.append("DISCOVERY_RESULT_NOT_OBJECT"); continue
        sid=str(rec.get("source_id") or "")
        if sid not in active:
            errors.append("DISCOVERY_RESULT_NOT_ACTIVE_AUTHORITATIVE_SOURCE:"+sid); continue
        if sid in by_source:
            errors.append("DUPLICATE_DISCOVERY_RESULT:"+sid); continue
        src=active[sid]
        if rec.get("complete") is not True:
            errors.append("DISCOVERY_RESULT_NOT_COMPLETE:"+sid)
        if rec.get("decision_epoch")!=epoch:
            errors.append("DISCOVERY_RESULT_DECISION_EPOCH_MISMATCH:"+sid)
        if rec.get("source_epoch")!=src.get("source_epoch"):
            errors.append("DISCOVERY_RESULT_SOURCE_EPOCH_MISMATCH:"+sid)
        raw_tools=rec.get("tools")
        if not isinstance(raw_tools,list):
            errors.append("DISCOVERY_RESULT_TOOLS_NOT_LIST:"+sid); continue
        rows=[]
        local_ids=set()
        for raw in raw_tools:
            row,err=_public_tool(raw)
            if err:
                errors.append("RESULT_"+err); continue
            assert row is not None
            tid=row["tool_id"]
            if tid in local_ids:
                errors.append("DUPLICATE_RESULT_TOOL_ID:"+sid+":"+tid)
            local_ids.add(tid); rows.append(row)
        rows.sort(key=lambda r:r["tool_id"])
        expected=str(src.get("result_sha256") or "")
        got=_sha(rows)
        if expected!=got:
            errors.append("DISCOVERY_RESULT_CONTENT_DIGEST_MISMATCH:"+sid)
        by_source[sid]={**dict(rec),"_normalized_tools":rows}

    missing_sources=sorted(set(active)-set(by_source))
    if missing_sources:
        errors.extend("AUTHORITATIVE_SOURCE_RESULT_MISSING:"+sid for sid in missing_sources)

    union:dict[str,dict[str,Any]]={}
    for sid,rec in by_source.items():
        for row in rec["_normalized_tools"]:
            tid=row["tool_id"]
            prior=union.get(tid)
            if prior is not None and prior!=row:
                errors.append("CROSS_SOURCE_METADATA_CONFLICT:"+tid)
            union[tid]=row
    union_rows=sorted(union.values(),key=lambda r:r["tool_id"])

    if union_rows!=manifest:
        union_ids={r["tool_id"] for r in union_rows}
        manifest_ids={r["tool_id"] for r in manifest}
        for tid in sorted(manifest_ids-union_ids):
            errors.append("COMMON_AUTHORITY_TOOL_MISSING_FROM_DISCOVERY:"+tid)
        for tid in sorted(union_ids-manifest_ids):
            errors.append("DISCOVERY_EXTRA_TOOL_OUTSIDE_COMMON_AUTHORITY:"+tid)
        for tid in sorted(manifest_ids & union_ids):
            want=next(r for r in manifest if r["tool_id"]==tid)
            got=union[tid]
            if want!=got:
                errors.append("COMMON_AUTHORITY_METADATA_MISMATCH:"+tid)

    if errors:
        return _fail(*errors)

    return {
        "schema":SCHEMA,
        "status":"PASS__EXACT_COMMON_FROZEN_AUTHORITY_IDENTITY_SCOPE",
        "errors":[],
        "identity_scope_complete":True,
        "scope_relation":"EXACT",
        "decision_epoch":epoch,
        "authority_manifest_sha256":manifest_digest,
        "authority_tool_count":len(manifest),
        "active_authoritative_source_count":len(active),
        "brain_opus_same_frozen_authority":True,
        "discovery_union_exactly_equals_common_authority":True,
        "capability_truth_proved":False,
        "observability_proved":False,
        "acceptance_proved":False,
        "new_reality_units_consumed":0,
        "terminal_results_replayed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }
