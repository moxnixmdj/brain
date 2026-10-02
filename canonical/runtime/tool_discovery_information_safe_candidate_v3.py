"""Information-safe V3 tool discovery/selection policy.

V3 adds dynamic catalog discovery and explicit active-constraint filtering while
retaining safe capability probes, least-cost evidence-supported selection,
second-task transfer, and epoch invalidation. Hidden capability truth is never
candidate-visible.
"""
from __future__ import annotations

from typing import Any, Mapping


_OPS={"eq","ne","in","not_in","le","lt","ge","gt"}


def _epoch_map(public:Mapping[str,Any])->dict[str,int]:
    out={str(t["tool_id"]):int(t.get("epoch",0)) for t in public.get("tools",[]) if t.get("tool_id")}
    for ev in public.get("version_events",[]):
        if ev.get("kind")=="TOOL_VERSION_CHANGED":
            tid=str(ev.get("tool_id") or "")
            if tid in out:
                out[tid]=int(ev.get("new_epoch",out[tid]+1))
    return out


def _evidence(public:Mapping[str,Any])->dict[tuple[str,str],bool]:
    epochs=_epoch_map(public)
    out={}
    for rec in public.get("prior_probe_receipts",[]):
        if rec.get("kind")!="SAFE_CAPABILITY_PROBE":
            continue
        tid=str(rec.get("tool_id") or "");cap=str(rec.get("capability") or "")
        if tid in epochs and int(rec.get("epoch",-1))==epochs[tid]:
            out[(tid,cap)]=rec.get("supported") is True
    return out


def _field(tool:Mapping[str,Any],name:str):
    if name in tool:
        return tool.get(name)
    attrs=tool.get("attributes") or {}
    return attrs.get(name) if isinstance(attrs,Mapping) else None


def _constraint_ok(tool:Mapping[str,Any],c:Mapping[str,Any])->bool:
    field=str(c.get("field") or "")
    op=str(c.get("op") or "")
    if not field or op not in _OPS:
        return False
    x=_field(tool,field);y=c.get("value")
    if x is None:
        return False
    try:
        if op=="eq": return x==y
        if op=="ne": return x!=y
        if op=="in": return x in y
        if op=="not_in": return x not in y
        if op=="le": return x<=y
        if op=="lt": return x<y
        if op=="ge": return x>=y
        if op=="gt": return x>y
    except Exception:
        return False
    return False


def _eligible(public:Mapping[str,Any])->list[Mapping[str,Any]]:
    constraints=public.get("active_constraints") or []
    rows=[]
    for t in public.get("tools",[]):
        if not isinstance(t,Mapping):
            continue
        if t.get("available") is not True or t.get("authorized") is not True:
            continue
        if not all(isinstance(c,Mapping) and _constraint_ok(t,c) for c in constraints):
            continue
        rows.append(t)
    rows.sort(key=lambda t:(float(t.get("cost",0.0)),str(t.get("tool_id") or "")))
    return rows


def next_action(public:Mapping[str,Any])->dict[str,Any]:
    # Least-cost selection over an unknown catalog is not identifiable until the
    # discovery source declares completeness. Discovery exposes metadata only,
    # never hidden capability truth.
    if public.get("catalog_complete") is not True:
        return {"action":"DISCOVER","cursor":public.get("discovery_cursor")}

    required=sorted({str(x) for x in public.get("required_capabilities",[]) if str(x)})
    if not required:
        return {"action":"ESCALATE","reason":"NO_REQUIRED_CAPABILITIES"}
    evidence=_evidence(public)

    for tool in _eligible(public):
        tid=str(tool.get("tool_id") or "")
        unknown=[];rejected=False
        for cap in required:
            value=evidence.get((tid,cap))
            if value is False:
                rejected=True;break
            if value is None:
                unknown.append(cap)
        if rejected:
            continue
        if unknown:
            return {"action":"PROBE","tool_id":tid,"capability":unknown[0]}
        return {"action":"SELECT","tool_id":tid}

    return {"action":"ESCALATE","reason":"NO_EVIDENCE_SUPPORTED_ADMISSIBLE_ROUTE"}
