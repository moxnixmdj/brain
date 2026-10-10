"""Tool Discovery policy V7: transferable catalog receipts across tasks.

V5/V6 bind discovery completion to the current task's capability query and
decision epoch. That is safe but forces DISCOVER again whenever a later task
changes its requirement set, even if the tool authority, source contents and
tool metadata are unchanged. The frozen family explicitly requires later-task
transfer without rediscovery.

V7 separates two clocks:
  * authority/source epochs govern catalog-discovery receipts;
  * tool epochs govern capability-probe receipts.

A complete source catalog is queried with the source's canonical catalog_query,
not with task requirements. The receipt remains reusable across task/decision
changes until authority/source/tool metadata changes. Capability evidence remains
tool-epoch bound and is reused only while current.

Zero acceptance/family/execution/promotion credit is granted here.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5


def _restart_event(public: Mapping[str, Any]) -> Mapping[str, Any] | None:
    events=public.get("version_events",[])
    if not isinstance(events,list):
        return {"kind":"INVALID_VERSION_EVENTS"}
    for ev in events:
        if not isinstance(ev,Mapping):
            continue
        if ev.get("kind") in {"TOOL_VERSION_CHANGED","TOOL_AUTHORITY_CHANGED"}:
            return ev
    return None


def _authority_epoch(public: Mapping[str, Any]) -> int | None:
    value=public.get("authority_epoch",0)
    if isinstance(value,bool) or not isinstance(value,int) or value<0:
        return None
    return value


def _source_valid_shape(source: Mapping[str, Any]) -> bool:
    sid=str(source.get("source_id") or "")
    cost=source.get("cost")
    epoch=source.get("source_epoch")
    digest=str(source.get("source_digest") or "")
    query=str(source.get("catalog_query") or "")
    return bool(
        sid
        and not isinstance(cost,bool)
        and isinstance(cost,(int,float))
        and float(cost)>=0
        and not isinstance(epoch,bool)
        and isinstance(epoch,int)
        and epoch>=0
        and digest
        and query
    )


def _source_set_digest(
    sources: list[Mapping[str, Any]],
    *,
    authority_epoch: int,
) -> str:
    payload=[]
    for source in sources:
        payload.append({
            "source_id":str(source.get("source_id") or ""),
            "cost":float(source.get("cost",0.0)),
            "available":source.get("available"),
            "authorized":source.get("authorized"),
            "authoritative":source.get("authoritative"),
            "source_epoch":source.get("source_epoch"),
            "source_digest":str(source.get("source_digest") or ""),
            "catalog_query":str(source.get("catalog_query") or ""),
        })
    payload.sort(key=lambda row:row["source_id"])
    raw=json.dumps(
        {"authority_epoch":authority_epoch,"sources":payload},
        sort_keys=True,separators=(",",":"),ensure_ascii=False,
    )
    return "sha256:"+hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _active_sources(
    public: Mapping[str, Any],
    *,
    authority_epoch: int,
) -> tuple[list[Mapping[str, Any]], str, str | None]:
    raw=public.get("discovery_sources",[])
    if not isinstance(raw,list):
        return [],"","DISCOVERY_SOURCES_NOT_LIST"
    active=[]
    all_sources=[]
    ids=set()
    for source in raw:
        if not isinstance(source,Mapping):
            return [],"","DISCOVERY_SOURCE_NOT_OBJECT"
        for field in ("authoritative","available","authorized"):
            if not isinstance(source.get(field),bool):
                return [],"","DISCOVERY_SOURCE_"+field.upper()+"_UNDECLARED"
        if not _source_valid_shape(source):
            return [],"","DISCOVERY_SOURCE_MALFORMED"
        sid=str(source.get("source_id"))
        if sid in ids:
            return [],"","DUPLICATE_DISCOVERY_SOURCE_ID"
        ids.add(sid)
        all_sources.append(source)
        if (
            source.get("authoritative") is True
            and source.get("available") is True
            and source.get("authorized") is True
        ):
            active.append(source)
    active.sort(key=lambda s:(float(s.get("cost",0.0)),str(s.get("source_id"))))
    try:
        digest=_source_set_digest(all_sources,authority_epoch=authority_epoch)
    except (TypeError,ValueError):
        return [],"","SOURCE_SET_DIGEST_COMPUTATION_FAILED"
    return active,digest,None


def _receipt_matches(
    rec: Mapping[str, Any],
    source: Mapping[str, Any],
    *,
    authority_epoch: int,
    source_set_digest: str,
) -> bool:
    return bool(
        rec.get("kind")=="DISCOVERY_RESULT"
        and str(rec.get("source_id") or "")==str(source.get("source_id"))
        and rec.get("complete") is True
        and rec.get("authority_epoch")==authority_epoch
        and rec.get("source_epoch")==source.get("source_epoch")
        and str(rec.get("source_digest") or "")==str(source.get("source_digest") or "")
        and str(rec.get("source_set_digest") or "")==source_set_digest
        and str(rec.get("query") or "")==str(source.get("catalog_query") or "")
        and isinstance(rec.get("tools"),list)
        and v5._tools_digest(rec.get("tools"))==str(source.get("source_digest") or "")
    )


def _valid_receipts(
    public: Mapping[str, Any],
    sources: list[Mapping[str, Any]],
    *,
    authority_epoch: int,
    source_set_digest: str,
) -> tuple[dict[str, Mapping[str, Any]], str | None]:
    raw=public.get("discovery_receipts",[])
    if not isinstance(raw,list):
        return {},"DISCOVERY_RECEIPTS_NOT_LIST"
    out={}
    for source in sources:
        matches=[
            rec for rec in raw
            if isinstance(rec,Mapping)
            and _receipt_matches(
                rec,source,
                authority_epoch=authority_epoch,
                source_set_digest=source_set_digest,
            )
        ]
        if len(matches)>1:
            first=matches[0]
            if any(rec!=first for rec in matches[1:]):
                return {},"CONFLICTING_CURRENT_DISCOVERY_RECEIPTS"
        if matches:
            out[str(source.get("source_id"))]=matches[0]
    return out,None


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    ev=_restart_event(public)
    if ev is not None:
        if ev.get("kind")=="INVALID_VERSION_EVENTS":
            return {"action":"ESCALATE","reason":"VERSION_EVENTS_NOT_LIST"}
        if ev.get("kind")=="TOOL_VERSION_CHANGED":
            return {
                "action":"ESCALATE",
                "reason":"TOOL_VERSION_CHANGED_RESTART_EPISODE",
                "tool_id":str(ev.get("tool_id") or ""),
                "new_epoch":ev.get("new_epoch"),
            }
        return {
            "action":"ESCALATE",
            "reason":"TOOL_AUTHORITY_CHANGED_RESTART_EPISODE",
            "new_authority_epoch":ev.get("new_authority_epoch"),
        }

    required,_=v5._requirements(public)
    if not required:
        return {"action":"ESCALATE","reason":"NO_REQUIRED_CAPABILITIES"}

    authority_epoch=_authority_epoch(public)
    if authority_epoch is None:
        return {"action":"ESCALATE","reason":"AUTHORITY_EPOCH_INVALID"}

    sources,source_set_digest,err=_active_sources(
        public,authority_epoch=authority_epoch,
    )
    if err:
        return {"action":"ESCALATE","reason":err}
    receipts,err=_valid_receipts(
        public,sources,
        authority_epoch=authority_epoch,
        source_set_digest=source_set_digest,
    )
    if err:
        return {"action":"ESCALATE","reason":err}

    # Discovery completion is authority/catalog scoped, not task scoped.
    # Therefore a later task can reuse the exact same complete catalog receipt.
    for source in sources:
        sid=str(source.get("source_id"))
        if sid not in receipts:
            return {
                "action":"DISCOVER",
                "source_id":sid,
                "query":str(source.get("catalog_query")),
                "authority_epoch":authority_epoch,
            }

    tools,err=v5._catalog(public,receipts)
    if err:
        return {"action":"ESCALATE","reason":err}
    evidence,err=v5._evidence(public,tools)
    if err:
        return {"action":"ESCALATE","reason":err}

    constraint=public.get("constraint")
    admissible=[]
    for tool in tools:
        cost=tool.get("cost")
        if isinstance(cost,bool) or not isinstance(cost,(int,float)) or float(cost)<0:
            return {"action":"ESCALATE","reason":"TOOL_COST_INVALID"}
        if (
            tool.get("available") is True
            and tool.get("authorized") is True
            and v5._pred(constraint,tool)
        ):
            admissible.append(tool)
    admissible.sort(key=lambda t:(float(t.get("cost",0.0)),str(t.get("tool_id") or "")))

    for tool in admissible:
        tid=str(tool.get("tool_id") or "")
        unknown=[]
        falsified=False
        for cap in required:
            value=evidence.get((tid,cap))
            if value is False:
                falsified=True
                break
            if value is None:
                unknown.append(cap)
        if falsified:
            continue
        if not unknown:
            return {"action":"SELECT","tool_id":tid}
        probeable=[cap for cap in unknown if v5._probe_allowed(tool,cap)]
        if probeable:
            return {"action":"PROBE","tool_id":tid,"capability":probeable[0]}
        return {
            "action":"ESCALATE",
            "reason":"CHEAPER_ADMISSIBLE_ROUTE_UNRESOLVED_NO_SAFE_PROBE",
            "tool_id":tid,
        }

    return {
        "action":"ESCALATE",
        "reason":"NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY",
    }
