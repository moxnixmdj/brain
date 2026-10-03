"""Information-safe dynamic tool discovery/selection policy V4.

V4 fixes the V3 universal counterexample: a visible verified route must not be
selected while an unqueried authorized discovery source could expose a cheaper
sufficient route. The policy therefore reaches discovery closure first, then
probes admissible tools in deterministic least-cost order, reuses current-epoch
evidence, invalidates stale evidence after version changes, and escalates only
after the reachable admissible universe is exhausted.
"""
from __future__ import annotations
from typing import Any, Mapping

CMP={"eq","neq","in","not_in","lt","le","gt","ge","contains","exists"}

def _get(obj:Mapping[str,Any],path:str):
    cur:Any=obj
    for part in str(path).split("."):
        if not isinstance(cur,Mapping) or part not in cur:
            return None
        cur=cur[part]
    return cur

def _pred(expr:Any,tool:Mapping[str,Any])->bool:
    if expr in (None,{},[]): return True
    if not isinstance(expr,Mapping): return False
    op=str(expr.get("op") or "")
    if op=="and":
        xs=expr.get("args"); return isinstance(xs,list) and all(_pred(x,tool) for x in xs)
    if op=="or":
        xs=expr.get("args"); return isinstance(xs,list) and bool(xs) and any(_pred(x,tool) for x in xs)
    if op=="not": return not _pred(expr.get("arg"),tool)
    if op not in CMP: return False
    value=_get(tool,str(expr.get("path") or "")); target=expr.get("value")
    if op=="exists": return (value is not None) is bool(target)
    if op=="eq": return value==target
    if op=="neq": return value!=target
    if op=="in": return isinstance(target,list) and value in target
    if op=="not_in": return isinstance(target,list) and value not in target
    if op=="contains": return isinstance(value,(str,list,tuple,set)) and target in value
    if isinstance(value,bool) or isinstance(target,bool): return False
    if not isinstance(value,(int,float)) or not isinstance(target,(int,float)): return False
    if op=="lt": return value<target
    if op=="le": return value<=target
    if op=="gt": return value>target
    if op=="ge": return value>=target
    return False

def _epochs(public:Mapping[str,Any])->dict[str,int]:
    out={str(t.get("tool_id")):int(t.get("epoch",0)) for t in public.get("visible_tools",[]) if isinstance(t,Mapping)}
    for ev in public.get("version_events",[]):
        if isinstance(ev,Mapping) and ev.get("kind")=="TOOL_VERSION_CHANGED":
            tid=str(ev.get("tool_id") or "")
            if tid in out: out[tid]=int(ev.get("new_epoch",out[tid]+1))
    return out

def _evidence(public:Mapping[str,Any])->dict[tuple[str,str],bool]:
    epochs=_epochs(public); out={}
    for rec in public.get("prior_probe_receipts",[]):
        if not isinstance(rec,Mapping) or rec.get("kind")!="SAFE_CAPABILITY_PROBE": continue
        tid=str(rec.get("tool_id") or ""); cap=str(rec.get("capability") or "")
        if tid in epochs and int(rec.get("epoch",-1))==epochs[tid]:
            out[(tid,cap)]=rec.get("supported") is True
    return out

def _queried_sources(public:Mapping[str,Any])->set[str]:
    return {str(x.get("source_id")) for x in public.get("discovery_receipts",[])
            if isinstance(x,Mapping) and x.get("kind")=="DISCOVERY_RESULT"}

def next_action(public:Mapping[str,Any])->dict[str,Any]:
    required=sorted({str(x) for x in public.get("required_capabilities",[]) if str(x)})
    if not required:
        return {"action":"ESCALATE","reason":"NO_REQUIRED_CAPABILITIES"}

    queried=_queried_sources(public)
    sources=[s for s in public.get("discovery_sources",[])
             if isinstance(s,Mapping) and s.get("available") is True
             and str(s.get("source_id") or "") not in queried]
    sources.sort(key=lambda s:(float(s.get("cost",0.0)),str(s.get("source_id") or "")))
    if sources:
        return {"action":"DISCOVER","source_id":str(sources[0].get("source_id")),
                "query":" ".join(required)}

    constraint=public.get("constraint"); evidence=_evidence(public)
    tools=[t for t in public.get("visible_tools",[])
           if isinstance(t,Mapping) and t.get("available") is True
           and t.get("authorized") is True and _pred(constraint,t)]
    tools.sort(key=lambda t:(float(t.get("cost",0.0)),str(t.get("tool_id") or "")))

    for tool in tools:
        tid=str(tool.get("tool_id") or "")
        unknown=[]; impossible=False
        for cap in required:
            v=evidence.get((tid,cap))
            if v is False:
                impossible=True; break
            if v is None: unknown.append(cap)
        if impossible: continue
        if unknown:
            return {"action":"PROBE","tool_id":tid,"capability":unknown[0]}
        return {"action":"SELECT","tool_id":tid}

    return {"action":"ESCALATE","reason":"NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_DISCOVERY"}
