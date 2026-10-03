#!/usr/bin/env python3
"""Validated canonical source universe for global retrieval.

Converts the governance source map into controller-compatible source rows while
preserving scope limits. It never widens search-only sources into enumerable
ones and never fabricates an epoch or runtime scope.
"""
from __future__ import annotations
import json,re
from pathlib import Path
from typing import Any,Mapping,Sequence

SCHEMA="PROJECT_BRAIN_RETRIEVAL_SOURCE_UNIVERSE_RUNTIME_V1"
REGISTRY_SCHEMA="PROJECT_BRAIN_GLOBAL_RETRIEVAL_SOURCE_UNIVERSE_V1"
_PLACEHOLDER=re.compile(r"\{([A-Za-z0-9_]+)\}")


def load_registry(root:Path)->dict[str,Any]:
    p=root/"canonical/governance/GLOBAL_RETRIEVAL_SOURCE_UNIVERSE_V1.json"
    obj=json.loads(p.read_text(encoding="utf-8"))
    if obj.get("schema")!=REGISTRY_SCHEMA:
        raise ValueError("SOURCE_UNIVERSE_SCHEMA_INVALID")
    rows=obj.get("sources")
    if not isinstance(rows,list) or not rows:
        raise ValueError("SOURCE_UNIVERSE_NONEMPTY_LIST_REQUIRED")
    ids=[]
    for row in rows:
        if not isinstance(row,Mapping):
            raise ValueError("SOURCE_ROW_MAPPING_REQUIRED")
        sid=str(row.get("source_id") or "").strip()
        if not sid:
            raise ValueError("SOURCE_ID_REQUIRED")
        ids.append(sid)
        auth=row.get("authoritative_enumeration") is True
        bounded=row.get("bounded_scope") is True
        if auth and not bounded:
            raise ValueError("AUTHORITATIVE_ENUMERATION_REQUIRES_BOUNDED_SCOPE:"+sid)
        if auth and not str(row.get("scope_id_template") or "").strip():
            raise ValueError("AUTHORITATIVE_ENUMERATION_REQUIRES_SCOPE_TEMPLATE:"+sid)
        if row.get("queryless_default_enabled") is True and not auth:
            raise ValueError("QUERYLESS_DEFAULT_REQUIRES_AUTHORITATIVE_ENUMERATION:"+sid)
    if len(ids)!=len(set(ids)):
        raise ValueError("DUPLICATE_SOURCE_ID")
    return obj


def _bind_template(template:str,bindings:Mapping[str,Any])->str|None:
    needed=_PLACEHOLDER.findall(template)
    missing=[x for x in needed if not str(bindings.get(x) or "").strip()]
    if missing:
        return None
    return template.format(**{k:str(bindings[k]).strip() for k in needed})


def bind_sources(
    registry:Mapping[str,Any],
    *,
    epoch:str,
    runtime_bindings:Mapping[str,Mapping[str,Any]]|None=None,
    include_source_ids:Sequence[str]|None=None,
    include_high_volume_defaults:bool=False,
)->dict[str,Any]:
    if registry.get("schema")!=REGISTRY_SCHEMA:
        raise ValueError("SOURCE_UNIVERSE_SCHEMA_INVALID")
    epoch=str(epoch or "").strip()
    if not epoch:
        raise ValueError("EXPLICIT_SOURCE_EPOCH_REQUIRED")
    runtime_bindings=runtime_bindings or {}
    selected=set(str(x) for x in include_source_ids) if include_source_ids is not None else None
    rows=[]
    skipped=[]
    for raw in registry["sources"]:
        row=dict(raw)
        sid=str(row["source_id"])
        if selected is not None and sid not in selected:
            continue
        bindings={"epoch":epoch}
        extra=runtime_bindings.get(sid) or {}
        if isinstance(extra,Mapping):
            bindings.update({str(k):v for k,v in extra.items()})
        auth=row.get("authoritative_enumeration") is True
        scope=None
        if auth:
            scope=_bind_template(str(row["scope_id_template"]),bindings)
            if scope is None:
                skipped.append({"source_id":sid,"reason":"MISSING_RUNTIME_SCOPE_BINDING"})
                continue
        enabled=row.get("queryless_default_enabled") is True
        volume=str(row.get("expected_volume_class") or "")
        if enabled and volume in {"VERY_HIGH","EXTREME"} and not include_high_volume_defaults:
            enabled=False
        rows.append({
            "source_id":sid,
            "upstream_group":str(row.get("upstream_group") or sid),
            "source_class":str(row.get("source_class") or "UNSPECIFIED"),
            "bounded_scope":bool(row.get("bounded_scope")),
            "authoritative_enumeration":auth,
            "scope_id":scope,
            "enumeration_transport":row.get("enumeration_transport"),
            "queryless_default_enabled":enabled,
            "expected_volume_class":volume,
            "candidate_authority":"CANDIDATE_ONLY",
        })
    return {
        "schema":SCHEMA,
        "status":"BOUND_TO_EXPLICIT_EPOCH",
        "epoch":epoch,
        "sources":rows,
        "skipped_sources":skipped,
        "authoritative_enumerable_source_count":sum(x["authoritative_enumeration"] for x in rows),
        "queryless_default_source_count":sum(
            x["authoritative_enumeration"] and x["queryless_default_enabled"] for x in rows
        ),
        "search_only_source_count":sum(not x["authoritative_enumeration"] for x in rows),
        "complete_global_source_universe":False,
        "nonexistence_claim_authorized":False,
        "hard_rules":[
            "EVERY_ENUMERABLE_SOURCE_IS_BOUND_TO_AN_EXPLICIT_SCOPE_AND_EPOCH",
            "MISSING_RUNTIME_SCOPE_BINDINGS_SKIP_THE_SOURCE_INSTEAD_OF_WIDENING_SCOPE",
            "SEARCH_ONLY_SOURCES_REMAIN_NONAUTHORITATIVE",
            "HIGH_VOLUME_ENUMERATION_REQUIRES_EXPLICIT_ENABLEMENT_WHEN_NOT_DEFAULT",
            "BOUND_SOURCE_ROWS_REMAIN_CANDIDATE_GENERATION_AUTHORITY_ONLY",
        ],
    }


def controller_sources(bound:Mapping[str,Any])->list[dict[str,Any]]:
    if bound.get("schema")!=SCHEMA:
        raise ValueError("BOUND_SOURCE_UNIVERSE_REQUIRED")
    out=[]
    for row in bound.get("sources") or []:
        if not isinstance(row,Mapping):
            continue
        # Only default-enabled authoritative enumerators are exposed as
        # queryless actions. Search-only sources are still returned for query
        # action metadata/routing.
        item=dict(row)
        if item.get("authoritative_enumeration") is True and item.get("queryless_default_enabled") is not True:
            item["authoritative_enumeration"]=False
        out.append(item)
    return out


def main()->int:
    root=Path(__file__).resolve().parents[2]
    reg=load_registry(root)
    out=bind_sources(reg,epoch="EXAMPLE_EPOCH",runtime_bindings={})
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
