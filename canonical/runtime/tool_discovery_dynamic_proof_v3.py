"""Information-safe dynamic discovery proof V3 for TOOL_ROUTE_DISCOVERY_AND_SELECTION_001.

The candidate starts from a partial catalog. Discovery actions reveal only public
metadata; hidden capabilities remain oracle-only and can be learned only through
safe-probe receipts.  Cases exercise generic constraints, multiple discovery
sources, transfer, version invalidation, and justified escalation.
"""
from __future__ import annotations
import random
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_DYNAMIC_PROOF_V3"
CLASSES=(
 "DYNAMIC_DISCOVERY",
 "GENERIC_CONSTRAINT",
 "MULTI_SOURCE",
 "TRANSFER",
 "VERSION_CHANGE",
 "NO_ROUTE",
)

def _tool(i,cost,pop,region,risk,tags):
    return {
      "tool_id":f"T{i}","cost":float(cost),"popularity":int(pop),
      "available":True,"authorized":True,"epoch":0,
      "meta":{"region":region,"risk":risk,"tags":list(tags),"provider":f"P{i%3}"},
      "schema_tags":["CAP_A","generic"],
    }

def generate_case(seed:int,ordinal:int)->dict[str,Any]:
    r=random.Random((int(seed)<<11)^int(ordinal)^0xA17E)
    cls=CLASSES[ordinal%len(CLASSES)]
    tools=[
      _tool(0,1,100,"US",3,["prod"]),
      _tool(1,2,80,"EU",1,["prod","safe"]),
      _tool(2,3,60,"EU",2,["safe"]),
      _tool(3,4,50,"US",1,["prod"]),
      _tool(4,5,40,"EU",1,["prod"]),
      _tool(5,6,30,"US",2,["safe"]),
    ]
    # Catalog structure is public only after a DISCOVER action.
    sources=[
      {"source_id":"S0","cost":0.1,"available":True,"tool_ids":["T1","T2"]},
      {"source_id":"S1","cost":0.2,"available":True,"tool_ids":["T3","T4","T5"]},
    ]
    hidden0={t["tool_id"]:False for t in tools}
    hidden1=dict(hidden0)
    constraint=None
    if cls=="DYNAMIC_DISCOVERY":
        hidden0["T1"]=True; hidden1["T1"]=True
    elif cls=="GENERIC_CONSTRAINT":
        # T0 and T2 could satisfy capability, but only T1 satisfies the entire
        # generic public predicate tree.
        hidden0["T0"]=True; hidden0["T1"]=True; hidden0["T2"]=True
        hidden1=dict(hidden0)
        constraint={"op":"and","args":[
          {"op":"eq","path":"meta.region","value":"EU"},
          {"op":"le","path":"meta.risk","value":1},
          {"op":"contains","path":"meta.tags","value":"prod"},
          {"op":"not","arg":{"op":"eq","path":"meta.provider","value":"P2"}},
        ]}
    elif cls=="MULTI_SOURCE":
        hidden0["T4"]=True; hidden1["T4"]=True
    elif cls=="TRANSFER":
        hidden0["T1"]=True; hidden1["T1"]=True
    elif cls=="VERSION_CHANGE":
        hidden0["T1"]=True
        hidden1["T1"]=False; hidden1["T2"]=True
    elif cls=="NO_ROUTE":
        pass
    return {
      "schema":SCHEMA,
      "behavior_id":"TOOL_ROUTE_DISCOVERY_AND_SELECTION_001",
      "case_id":f"TOOL-V3-{seed}-{ordinal}",
      "case_class":cls,
      "required_capabilities":["CAP_A"],
      "constraint":constraint,
      "initial_visible":["T0"],
      "tools":tools,
      "discovery_sources":sources,
      "_oracle":{"epoch0":hidden0,"epoch1":hidden1},
    }

def _public_tool(t):
    return {k:v for k,v in t.items() if k!="hidden_capabilities"}

def _public(case,visible,receipts,discoveries,version_events=()):
    byid={t["tool_id"]:t for t in case["tools"]}
    return {
      "required_capabilities":list(case["required_capabilities"]),
      "constraint":case["constraint"],
      "visible_tools":[_public_tool(byid[x]) for x in sorted(visible)],
      "discovery_sources":[{"source_id":s["source_id"],"cost":s["cost"],"available":s["available"]} for s in case["discovery_sources"]],
      "prior_probe_receipts":list(receipts),
      "discovery_receipts":list(discoveries),
      "version_events":list(version_events),
    }

def _pred(expr,tool):
    # Independent evaluator implementation of the public predicate language.
    if expr in (None,{},[]): return True
    op=expr["op"]
    def get(path):
        cur=tool
        for p in path.split("."):
            if not isinstance(cur,Mapping) or p not in cur:return None
            cur=cur[p]
        return cur
    if op=="and": return all(_pred(x,tool) for x in expr["args"])
    if op=="or": return any(_pred(x,tool) for x in expr["args"])
    if op=="not": return not _pred(expr["arg"],tool)
    v=get(expr.get("path","")); x=expr.get("value")
    if op=="exists": return (v is not None) is bool(x)
    if op=="eq": return v==x
    if op=="neq": return v!=x
    if op=="in": return isinstance(x,list) and v in x
    if op=="not_in": return isinstance(x,list) and v not in x
    if op=="contains": return isinstance(v,(str,list,tuple,set)) and x in v
    if op=="lt": return v<x
    if op=="le": return v<=x
    if op=="gt": return v>x
    if op=="ge": return v>=x
    return False

def _epoch_map(case,stage):
    out={t["tool_id"]:0 for t in case["tools"]}
    if stage==2 and case["case_class"]=="VERSION_CHANGE":
        out["T1"]=1
    return out

def _best(case,stage,visible):
    table=case["_oracle"]["epoch0" if stage==1 else "epoch1"]
    candidates=[]
    for t in case["tools"]:
        if t["tool_id"] not in visible: continue
        if not t["available"] or not t["authorized"] or not _pred(case["constraint"],t): continue
        if all(table[t["tool_id"]] for _ in case["required_capabilities"]):
            candidates.append(t)
    if not candidates: return None
    candidates.sort(key=lambda x:(x["cost"],x["tool_id"]))
    return candidates[0]["tool_id"]

def _discover(case,source_id,query):
    if not isinstance(query,str) or "CAP_A" not in query.split():
        raise ValueError("DISCOVERY_QUERY_DOES_NOT_TARGET_REQUIREMENT")
    src=next((s for s in case["discovery_sources"] if s["source_id"]==source_id and s["available"]),None)
    if src is None: raise ValueError("DISCOVERY_SOURCE_INVALID")
    byid={t["tool_id"]:t for t in case["tools"]}
    return {
      "kind":"DISCOVERY_RESULT","source_id":source_id,
      "tools":[_public_tool(byid[x]) for x in src["tool_ids"]],
    }

def _probe(case,stage,tool_id,capability):
    if capability not in case["required_capabilities"]: raise ValueError("IRRELEVANT_PROBE")
    table=case["_oracle"]["epoch0" if stage==1 else "epoch1"]
    epochs=_epoch_map(case,stage)
    if tool_id not in table: raise ValueError("UNKNOWN_TOOL")
    return {"kind":"SAFE_CAPABILITY_PROBE","tool_id":tool_id,"capability":capability,
            "epoch":epochs[tool_id],"supported":bool(table[tool_id])}

def _execute(case,stage,policy,visible,receipts,discoveries,version_events=()):
    actions=[]; failed_invocations=0
    for _ in range(40):
        pub=_public(case,visible,receipts,discoveries,version_events)
        action=policy(pub)
        if not isinstance(action,Mapping): return {"pass":False,"reason":"ACTION_NOT_MAPPING"}
        kind=action.get("action")
        if kind=="DISCOVER":
            sid=str(action.get("source_id") or "")
            if any(x["source_id"]==sid for x in discoveries): return {"pass":False,"reason":"DUPLICATE_DISCOVERY"}
            try: rec=_discover(case,sid,action.get("query"))
            except Exception as e:return {"pass":False,"reason":type(e).__name__+":"+str(e)}
            discoveries.append(rec); visible.update(x["tool_id"] for x in rec["tools"]); actions.append({"action":"DISCOVER","source_id":sid}); continue
        if kind=="PROBE":
            tid=str(action.get("tool_id") or ""); cap=str(action.get("capability") or "")
            if tid not in visible:return {"pass":False,"reason":"PROBE_INVISIBLE_TOOL"}
            rec=_probe(case,stage,tid,cap)
            key=(rec["tool_id"],rec["capability"],rec["epoch"])
            if any((x.get("tool_id"),x.get("capability"),x.get("epoch"))==key for x in receipts):
                return {"pass":False,"reason":"DUPLICATE_PROBE"}
            receipts.append(rec); actions.append({"action":"PROBE","tool_id":tid,"supported":rec["supported"]}); continue
        if kind=="SELECT":
            tid=str(action.get("tool_id") or "")
            expected=_best(case,stage,visible)
            if tid!=expected:return {"pass":False,"reason":"NONOPTIMAL_OR_UNSUPPORTED_SELECTION","expected":expected,"got":tid}
            epochs=_epoch_map(case,stage)
            for cap in case["required_capabilities"]:
                if not any(x.get("tool_id")==tid and x.get("capability")==cap and x.get("epoch")==epochs[tid] and x.get("supported") is True for x in receipts):
                    return {"pass":False,"reason":"SELECT_WITHOUT_CURRENT_POSITIVE_EVIDENCE"}
            actions.append({"action":"SELECT","tool_id":tid})
            return {"pass":True,"reason":"PASS","selected":tid,"actions":actions,"failed_invocations":failed_invocations}
        if kind=="ESCALATE":
            # Valid only after all sources are queried and each admissible
            # visible tool is ruled out by current negative evidence.
            if len({x["source_id"] for x in discoveries}) < len([s for s in case["discovery_sources"] if s["available"]]):
                return {"pass":False,"reason":"PREMATURE_ESCALATION_BEFORE_DISCOVERY"}
            if _best(case,stage,visible) is not None:return {"pass":False,"reason":"ESCALATED_WITH_SUFFICIENT_ROUTE"}
            epochs=_epoch_map(case,stage)
            for t in case["tools"]:
                if t["tool_id"] not in visible or not _pred(case["constraint"],t): continue
                if not t["available"] or not t["authorized"]: continue
                if not any(x.get("tool_id")==t["tool_id"] and x.get("epoch")==epochs[t["tool_id"]] and x.get("supported") is False for x in receipts):
                    return {"pass":False,"reason":"PREMATURE_ESCALATION_UNTESTED_TOOL"}
            return {"pass":True,"reason":"PASS_ESCALATE","selected":None,"actions":actions,"failed_invocations":failed_invocations}
        return {"pass":False,"reason":"UNKNOWN_ACTION"}
    return {"pass":False,"reason":"ACTION_BUDGET_EXHAUSTED"}

def _baseline_failure(case):
    # Schema/popularity baseline sees all public catalog metadata but performs no
    # capability probes. It chooses the most popular admissible advertised tool.
    eligible=[t for t in case["tools"] if t["available"] and t["authorized"] and _pred(case["constraint"],t) and "CAP_A" in t["schema_tags"]]
    if not eligible:return 0
    eligible.sort(key=lambda t:(-t["popularity"],t["tool_id"]))
    chosen=eligible[0]["tool_id"]
    return 0 if case["_oracle"]["epoch0"][chosen] else 1

def score_episode(case,policy):
    visible=set(case["initial_visible"]); receipts=[]; discoveries=[]
    s1=_execute(case,1,policy,visible,receipts,discoveries)
    if not s1["pass"]: return {"pass":False,"reason":"STAGE1_"+s1["reason"]}
    baseline=_baseline_failure(case)
    if case["case_class"]=="NO_ROUTE":
        ok=s1["reason"]=="PASS_ESCALATE"
        return {"pass":ok,"reason":"PASS" if ok else "NO_ROUTE_NOT_ESCALATED","baseline_failed_invocations":baseline}
    if baseline < 1:
        return {"pass":False,"reason":"BASELINE_ADVANTAGE_NOT_LOAD_BEARING"}

    if case["case_class"] in {"TRANSFER","VERSION_CHANGE"}:
        events=[]
        if case["case_class"]=="VERSION_CHANGE":
            events=[{"kind":"TOOL_VERSION_CHANGED","tool_id":"T1","new_epoch":1}]
        before_probe_count=len(receipts)
        s2=_execute(case,2,policy,visible,receipts,discoveries,events)
        if not s2["pass"]: return {"pass":False,"reason":"STAGE2_"+s2["reason"]}
        if case["case_class"]=="TRANSFER" and len(receipts)!=before_probe_count:
            return {"pass":False,"reason":"TRANSFER_DID_NOT_REUSE_CURRENT_EVIDENCE"}
    return {"pass":True,"reason":"PASS","baseline_failed_invocations":baseline}

def run_batch(seed:int,count:int,policy):
    rows=[]
    for i in range(count):
        case=generate_case(seed,i)
        try:v=score_episode(case,policy)
        except Exception as e:v={"pass":False,"reason":type(e).__name__+":"+str(e)}
        rows.append({"class":case["case_class"],**v})
    classes={c for c in CLASSES}
    seen={x["class"] for x in rows}
    return {"pass":all(x["pass"] for x in rows) and classes<=seen,
            "count":count,"failed":sum(not x["pass"] for x in rows),
            "classes":sorted(seen),"failures":[x for x in rows if not x["pass"]],
            "terminal_authority":False,"capability_credit_delta":0,"family_credit_delta":0}
