"""Converged Tool Discovery policy V5.

V5 repairs three load-bearing defects found in V3/V4 candidates:
1. no PROBE/SELECT while a current authoritative discovery source lacks an
   exact, complete, current-epoch, exact-query-bound receipt;
2. discovered tool metadata is merged by the policy and conflicting identities
   fail closed;
3. an unresolved cheaper admissible route that cannot be safely probed blocks
   selection of a more expensive route.

This module grants no acceptance/capability/family/execution/promotion credit.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

CMP={"eq","neq","in","not_in","lt","le","gt","ge","contains","exists"}


def _get(obj: Mapping[str, Any], path: str):
    cur: Any=obj
    for part in str(path).split("."):
        if not isinstance(cur,Mapping) or part not in cur:
            return None
        cur=cur[part]
    return cur


def _pred(expr: Any, tool: Mapping[str, Any]) -> bool:
    if expr in (None,{},[]):
        return True
    if not isinstance(expr,Mapping):
        return False
    op=str(expr.get("op") or "")
    if op=="and":
        xs=expr.get("args")
        return isinstance(xs,list) and all(_pred(x,tool) for x in xs)
    if op=="or":
        xs=expr.get("args")
        return isinstance(xs,list) and bool(xs) and any(_pred(x,tool) for x in xs)
    if op=="not":
        return not _pred(expr.get("arg"),tool)
    if op not in CMP:
        return False
    value=_get(tool,str(expr.get("path") or ""))
    target=expr.get("value")
    if op=="exists": return (value is not None) is bool(target)
    if op=="eq": return value==target
    if op=="neq": return value!=target
    if op=="in": return isinstance(target,list) and value in target
    if op=="not_in": return isinstance(target,list) and value not in target
    if op=="contains": return isinstance(value,(str,list,tuple,set)) and target in value
    if isinstance(value,bool) or isinstance(target,bool):
        return False
    if not isinstance(value,(int,float)) or not isinstance(target,(int,float)):
        return False
    if op=="lt": return value<target
    if op=="le": return value<=target
    if op=="gt": return value>target
    if op=="ge": return value>=target
    return False


def _requirements(public: Mapping[str, Any]) -> tuple[list[str], str | None]:
    raw=public.get("required_capabilities",[])
    if not isinstance(raw,list):
        return [],"REQUIRED_CAPABILITIES_NOT_LIST"
    required=sorted({str(x) for x in raw if str(x)})
    if not required:
        return [],"NO_REQUIRED_CAPABILITIES"
    if any(any(ch.isspace() for ch in cap) for cap in required):
        return [],"REQUIRED_CAPABILITY_ID_CONTAINS_WHITESPACE"
    return required," ".join(required)


def _decision_epoch(public: Mapping[str, Any]) -> int | None:
    value=public.get("decision_epoch",0)
    if isinstance(value,bool) or not isinstance(value,int) or value<0:
        return None
    return value


def _tools_digest(tools: Any) -> str:
    if not isinstance(tools,list):
        return ""
    if any(not isinstance(row,Mapping) for row in tools):
        return ""
    rows=[dict(row) for row in tools]
    rows.sort(key=lambda row:str(row.get("tool_id") or ""))
    try:
        raw=json.dumps(rows,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    except (TypeError,ValueError):
        return ""
    return "sha256:"+hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _source_set_digest(sources: list[Mapping[str, Any]]) -> str:
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
        })
    payload.sort(key=lambda row:row["source_id"])
    try:
        raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    except (TypeError,ValueError):
        return ""
    return "sha256:"+hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _source_valid_shape(source: Mapping[str, Any]) -> bool:
    sid=str(source.get("source_id") or "")
    cost=source.get("cost")
    epoch=source.get("source_epoch")
    digest=str(source.get("source_digest") or "")
    return bool(
        sid
        and not isinstance(cost,bool)
        and isinstance(cost,(int,float))
        and float(cost)>=0
        and not isinstance(epoch,bool)
        and isinstance(epoch,int)
        and epoch>=0
        and digest
    )


def _active_sources(public: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], str, str | None]:
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
    digest=_source_set_digest(all_sources)
    if raw and not digest:
        return [],"","SOURCE_SET_DIGEST_COMPUTATION_FAILED"
    return active,digest,None


def _receipt_matches(
    rec: Mapping[str, Any],
    source: Mapping[str, Any],
    *,
    decision_epoch: int,
    source_set_digest: str,
    query: str,
) -> bool:
    return bool(
        rec.get("kind")=="DISCOVERY_RESULT"
        and str(rec.get("source_id") or "")==str(source.get("source_id"))
        and rec.get("complete") is True
        and rec.get("decision_epoch")==decision_epoch
        and rec.get("source_epoch")==source.get("source_epoch")
        and str(rec.get("source_digest") or "")==str(source.get("source_digest"))
        and str(rec.get("source_set_digest") or "")==source_set_digest
        and str(rec.get("query") or "")==query
        and isinstance(rec.get("tools"),list)
        and _tools_digest(rec.get("tools"))==str(source.get("source_digest") or "")
    )


def _valid_receipts(
    public: Mapping[str, Any],
    sources: list[Mapping[str, Any]],
    *,
    decision_epoch: int,
    source_set_digest: str,
    query: str,
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
                decision_epoch=decision_epoch,
                source_set_digest=source_set_digest,
                query=query,
            )
        ]
        if len(matches)>1:
            first=matches[0]
            if any(rec!=first for rec in matches[1:]):
                return {},"CONFLICTING_CURRENT_DISCOVERY_RECEIPTS"
        if matches:
            out[str(source.get("source_id"))]=matches[0]
    return out,None


def _catalog(
    public: Mapping[str, Any],
    receipts: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], str | None]:
    byid: dict[str,dict[str,Any]]={}

    def add(raw: Any) -> str | None:
        if not isinstance(raw,Mapping):
            return "TOOL_METADATA_NOT_OBJECT"
        tid=str(raw.get("tool_id") or "")
        if not tid:
            return "TOOL_ID_MISSING"
        row=dict(raw)
        prior=byid.get(tid)
        if prior is not None and prior!=row:
            return "DISCOVERY_METADATA_CONFLICT"
        byid[tid]=row
        return None

    initial=public.get("visible_tools",[])
    if not isinstance(initial,list):
        return [],"VISIBLE_TOOLS_NOT_LIST"
    for row in initial:
        err=add(row)
        if err: return [],err
    for rec in receipts.values():
        for row in rec.get("tools",[]):
            err=add(row)
            if err: return [],err
    return list(byid.values()),None


def _epochs(public: Mapping[str, Any], tools: list[dict[str, Any]]) -> tuple[dict[str,int], str | None]:
    out={}
    for tool in tools:
        tid=str(tool.get("tool_id") or "")
        epoch=tool.get("epoch",0)
        if isinstance(epoch,bool) or not isinstance(epoch,int) or epoch<0:
            return {},"TOOL_EPOCH_INVALID"
        out[tid]=epoch
    events=public.get("version_events",[])
    if not isinstance(events,list):
        return {},"VERSION_EVENTS_NOT_LIST"
    for ev in events:
        if not isinstance(ev,Mapping) or ev.get("kind")!="TOOL_VERSION_CHANGED":
            continue
        tid=str(ev.get("tool_id") or "")
        new_epoch=ev.get("new_epoch")
        if tid in out:
            if isinstance(new_epoch,bool) or not isinstance(new_epoch,int) or new_epoch<0:
                return {},"VERSION_EVENT_EPOCH_INVALID"
            out[tid]=new_epoch
    return out,None


def _evidence(
    public: Mapping[str, Any],
    tools: list[dict[str, Any]],
) -> tuple[dict[tuple[str,str],bool], str | None]:
    epochs,err=_epochs(public,tools)
    if err:
        return {},err
    receipts=public.get("prior_probe_receipts",[])
    if not isinstance(receipts,list):
        return {},"PROBE_RECEIPTS_NOT_LIST"
    out={}
    for rec in receipts:
        if not isinstance(rec,Mapping) or rec.get("kind")!="SAFE_CAPABILITY_PROBE":
            continue
        tid=str(rec.get("tool_id") or "")
        cap=str(rec.get("capability") or "")
        if tid in epochs and rec.get("epoch")==epochs[tid]:
            key=(tid,cap)
            value=rec.get("supported") is True
            if key in out and out[key] is not value:
                return {},"CONFLICTING_CURRENT_PROBE_RECEIPTS"
            out[key]=value
    return out,None


def _probe_allowed(tool: Mapping[str, Any], capability: str) -> bool:
    allowed=tool.get("safe_probe_capabilities")
    return isinstance(allowed,list) and capability in {str(x) for x in allowed}


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    required,query=_requirements(public)
    if query=="NO_REQUIRED_CAPABILITIES":
        return {"action":"ESCALATE","reason":"NO_REQUIRED_CAPABILITIES"}
    if query is None or not required:
        return {"action":"ESCALATE","reason":query or "INVALID_REQUIREMENTS"}

    decision_epoch=_decision_epoch(public)
    if decision_epoch is None:
        return {"action":"ESCALATE","reason":"DECISION_EPOCH_INVALID"}

    sources,source_set_digest,err=_active_sources(public)
    if err:
        return {"action":"ESCALATE","reason":err}
    receipts,err=_valid_receipts(
        public,sources,
        decision_epoch=decision_epoch,
        source_set_digest=source_set_digest,
        query=query,
    )
    if err:
        return {"action":"ESCALATE","reason":err}

    # No probe/select/final no-route conclusion before every authoritative source
    # has an exact complete receipt for this exact decision epoch and requirement query.
    for source in sources:
        sid=str(source.get("source_id"))
        if sid not in receipts:
            return {"action":"DISCOVER","source_id":sid,"query":query}

    tools,err=_catalog(public,receipts)
    if err:
        return {"action":"ESCALATE","reason":err}
    evidence,err=_evidence(public,tools)
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
            and _pred(constraint,tool)
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

        # Crucial soundness rule: a cheaper unresolved route cannot simply be
        # skipped because probing it is unsafe. It blocks a more expensive choice.
        probeable=[cap for cap in unknown if _probe_allowed(tool,cap)]
        if probeable:
            return {"action":"PROBE","tool_id":tid,"capability":probeable[0]}
        return {
            "action":"ESCALATE",
            "reason":"CHEAPER_ADMISSIBLE_ROUTE_UNRESOLVED_NO_SAFE_PROBE",
            "tool_id":tid,
        }

    return {"action":"ESCALATE","reason":"NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY"}
