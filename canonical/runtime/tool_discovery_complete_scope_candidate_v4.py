"""Complete-scope tool discovery/selection policy V4.

V4 repairs the V3 global least-cost hole: it never probes or selects from an
identity universe whose declared discovery sources have not all produced
scope-bound complete receipts. Hidden capability truth remains accessible only
through current-epoch safe-probe receipts.
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

def _source_map(public:Mapping[str,Any])->dict[str,Mapping[str,Any]]|None:
    out={}
    for raw in public.get("discovery_sources",[]):
        if not isinstance(raw,Mapping): return None
        sid=str(raw.get("source_id") or "")
        if not sid or sid in out: return None
        out[sid]=raw
    return out

def _scope(public:Mapping[str,Any]):
    sources=_source_map(public)
    if sources is None: return None
    rec=public.get("discovery_scope_receipt")
    if not isinstance(rec,Mapping) or rec.get("kind")!="COMPLETE_DISCOVERY_SCOPE": return None
    if rec.get("complete") is not True: return None
    scope_id=str(rec.get("target_scope_id") or "")
    fp=str(rec.get("scope_fingerprint") or "")
    ids=rec.get("source_ids")
    if not scope_id or not fp or not isinstance(ids,list): return None
    normalized=[str(x) for x in ids]
    if len(set(normalized))!=len(normalized): return None
    if sorted(normalized)!=sorted(sources): return None
    return {"scope_id":scope_id,"scope_fingerprint":fp,"sources":sources}

def _complete_discovery_receipts(public:Mapping[str,Any],scope)->set[str]:
    complete=set()
    for rec in public.get("discovery_receipts",[]):
        if not isinstance(rec,Mapping) or rec.get("kind")!="DISCOVERY_RESULT": continue
        sid=str(rec.get("source_id") or "")
        if sid not in scope["sources"]: continue
        if rec.get("complete_for_source") is not True: continue
        if str(rec.get("target_scope_id") or "")!=scope["scope_id"]: continue
        if str(rec.get("scope_fingerprint") or "")!=scope["scope_fingerprint"]: continue
        complete.add(sid)
    return complete

def _epochs(public:Mapping[str,Any])->dict[str,int]:
    out={str(t.get("tool_id")):int(t.get("epoch",0)) for t in public.get("visible_tools",[]) if isinstance(t,Mapping) and str(t.get("tool_id") or "")}
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

def next_action(public:Mapping[str,Any])->dict[str,Any]:
    required=sorted({str(x) for x in public.get("required_capabilities",[]) if str(x)})
    if not required:
        return {"action":"ESCALATE","reason":"NO_REQUIRED_CAPABILITIES"}

    scope=_scope(public)
    if scope is None:
        return {"action":"ESCALATE","reason":"DISCOVERY_SCOPE_NOT_PROVED_COMPLETE"}

    complete=_complete_discovery_receipts(public,scope)
    unqueried=[
        s for sid,s in scope["sources"].items()
        if s.get("available") is True and sid not in complete
    ]
    unqueried.sort(key=lambda s:(float(s.get("cost",0.0)),str(s.get("source_id") or "")))
    if unqueried:
        return {
            "action":"DISCOVER",
            "source_id":str(unqueried[0].get("source_id")),
            "query":" ".join(required),
            "target_scope_id":scope["scope_id"],
            "scope_fingerprint":scope["scope_fingerprint"],
        }

    evidence=_evidence(public)
    tools=[
        t for t in public.get("visible_tools",[])
        if isinstance(t,Mapping)
        and str(t.get("tool_id") or "")
        and t.get("available") is True
        and t.get("authorized") is True
        and _pred(public.get("constraint"),t)
    ]
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
        if unknown: return {"action":"PROBE","tool_id":tid,"capability":unknown[0]}
        return {"action":"SELECT","tool_id":tid}
    return {"action":"ESCALATE","reason":"NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY"}
