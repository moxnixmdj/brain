"""Common-authority Tool Discovery harness adapter V1.

The matched protocol freezes a common tool boundary for Brain and Opus. This
adapter converts any finite explicit boundary into an information-safe V4
discovery interface without narrowing that boundary:

* candidate public state initially contains only the chosen visible subset;
* one harness-owned DISCOVER source represents every remaining route identity;
* DISCOVER reveals only public route metadata, never hidden capability truth;
* safe PROBE reveals exactly one capability bit as a receipt;
* the private boundary/capability oracle is harness state, not candidate input.

Thus identity completeness is by construction relative to the exact common
frozen tool authority supplied by the harness, not by an external global
registry claim.
"""
from __future__ import annotations

from copy import deepcopy
import math
from typing import Any, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4

SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_COMMON_AUTHORITY_ADAPTER_V1"
SOURCE_PREFIX="COMMON_FROZEN_TOOL_AUTHORITY"

class AdapterError(ValueError):
    pass

def _finite_number(value:Any,field:str)->float:
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise AdapterError("NONNUMERIC:"+field)
    out=float(value)
    if not math.isfinite(out):
        raise AdapterError("NONFINITE:"+field)
    return out

def _tool_rows(case:Mapping[str,Any])->list[dict[str,Any]]:
    raw=case.get("tool_boundary")
    if not isinstance(raw,list) or not raw:
        raise AdapterError("TOOL_BOUNDARY_REQUIRED")
    out=[]; seen=set()
    for i,row in enumerate(raw):
        if not isinstance(row,Mapping):
            raise AdapterError(f"TOOL_NOT_OBJECT:{i}")
        tid=str(row.get("tool_id") or "")
        if not tid or tid in seen:
            raise AdapterError("TOOL_ID_EMPTY_OR_DUPLICATE:"+tid)
        seen.add(tid)
        if row.get("available") not in (True,False):
            raise AdapterError("AVAILABLE_NOT_BOOLEAN:"+tid)
        if row.get("authorized") not in (True,False):
            raise AdapterError("AUTHORIZED_NOT_BOOLEAN:"+tid)
        epoch=row.get("epoch",0)
        if isinstance(epoch,bool) or not isinstance(epoch,int) or epoch<0:
            raise AdapterError("INVALID_TOOL_EPOCH:"+tid)
        item=deepcopy(dict(row))
        item["tool_id"]=tid
        item["cost"]=_finite_number(row.get("cost"),tid+".cost")
        item["epoch"]=epoch
        out.append(item)
    return out

def _truth(case:Mapping[str,Any],ids:set[str])->dict[str,dict[str,bool]]:
    raw=case.get("hidden_capabilities")
    if not isinstance(raw,Mapping) or set(map(str,raw.keys()))!=ids:
        raise AdapterError("HIDDEN_CAPABILITY_TOOL_SET_MISMATCH")
    out={}
    for tid in sorted(ids):
        caps=raw.get(tid)
        if not isinstance(caps,Mapping):
            raise AdapterError("HIDDEN_CAPABILITIES_NOT_OBJECT:"+tid)
        row={}
        for cap,val in caps.items():
            cid=str(cap)
            if not cid or val not in (True,False):
                raise AdapterError("INVALID_HIDDEN_CAPABILITY:"+tid+":"+cid)
            row[cid]=bool(val)
        out[tid]=row
    return out

def build(case:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(case,Mapping):
        raise AdapterError("CASE_NOT_OBJECT")
    epoch=str(case.get("decision_epoch") or "")
    if not epoch:
        raise AdapterError("DECISION_EPOCH_REQUIRED")
    tools=_tool_rows(case)
    by_id={x["tool_id"]:x for x in tools}
    truth=_truth(case,set(by_id))

    required=sorted({str(x) for x in case.get("required_capabilities",[]) if str(x)})
    if not required:
        raise AdapterError("REQUIRED_CAPABILITIES_EMPTY")
    for tid,caps in truth.items():
        missing=[cap for cap in required if cap not in caps]
        if missing:
            raise AdapterError("HIDDEN_CAPABILITY_MATRIX_INCOMPLETE:"+tid+":"+",".join(missing))

    initial=case.get("initially_visible_tool_ids",[])
    if not isinstance(initial,list):
        raise AdapterError("INITIAL_VISIBLE_IDS_NOT_LIST")
    initial_ids=[str(x) for x in initial]
    if len(initial_ids)!=len(set(initial_ids)) or any(x not in by_id for x in initial_ids):
        raise AdapterError("INITIAL_VISIBLE_IDS_INVALID")

    hidden_ids=sorted(set(by_id)-set(initial_ids))
    source_id=SOURCE_PREFIX+"::"+epoch
    public={
        "required_capabilities":required,
        "constraint":deepcopy(case.get("constraint")),
        "visible_tools":[deepcopy(by_id[x]) for x in initial_ids],
        "discovery_sources":(
            [{"source_id":source_id,"cost":0.0,"available":True}]
            if hidden_ids else []
        ),
        "discovery_receipts":[],
        "prior_probe_receipts":[],
        "version_events":[],
    }
    private={
        "decision_epoch":epoch,
        "source_id":source_id,
        "hidden_tool_ids":hidden_ids,
        "boundary_by_id":deepcopy(by_id),
        "capability_truth":truth,
    }
    return {
        "schema":SCHEMA,
        "status":"READY",
        "public":public,
        "private":private,
        "terminal":None,
    }

def _visible_ids(public:Mapping[str,Any])->set[str]:
    return {
        str(x.get("tool_id"))
        for x in public.get("visible_tools",[])
        if isinstance(x,Mapping)
    }

def step(state:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(state,Mapping) or state.get("schema")!=SCHEMA:
        raise AdapterError("INVALID_STATE_SCHEMA")
    if state.get("terminal") is not None:
        raise AdapterError("STATE_ALREADY_TERMINAL")
    out=deepcopy(dict(state))
    public=out["public"]; private=out["private"]
    action=v4.next_action(public)

    if action.get("action")=="DISCOVER":
        if action.get("source_id")!=private["source_id"]:
            raise AdapterError("UNKNOWN_DISCOVERY_SOURCE")
        if any(
            isinstance(x,Mapping)
            and x.get("kind")=="DISCOVERY_RESULT"
            and x.get("source_id")==private["source_id"]
            for x in public["discovery_receipts"]
        ):
            raise AdapterError("DUPLICATE_DISCOVERY")
        rows=[
            deepcopy(private["boundary_by_id"][tid])
            for tid in private["hidden_tool_ids"]
            if tid not in _visible_ids(public)
        ]
        # Atomic state transition: discovered public rows become visible in the
        # same transition that records the source as queried.
        public["visible_tools"].extend(rows)
        public["discovery_receipts"].append({
            "kind":"DISCOVERY_RESULT",
            "source_id":private["source_id"],
            "decision_epoch":private["decision_epoch"],
            "tools":deepcopy(rows),
        })
    elif action.get("action")=="PROBE":
        tid=str(action.get("tool_id") or "")
        cap=str(action.get("capability") or "")
        if tid not in private["capability_truth"] or cap not in private["capability_truth"][tid]:
            raise AdapterError("INVALID_PROBE_TARGET")
        tool=private["boundary_by_id"][tid]
        public["prior_probe_receipts"].append({
            "kind":"SAFE_CAPABILITY_PROBE",
            "tool_id":tid,
            "capability":cap,
            "epoch":int(tool.get("epoch",0)),
            "decision_epoch":private["decision_epoch"],
            "supported":private["capability_truth"][tid][cap],
        })
    elif action.get("action") in {"SELECT","ESCALATE"}:
        out["terminal"]=deepcopy(action)
    else:
        raise AdapterError("UNKNOWN_V4_ACTION")
    out["last_action"]=deepcopy(action)
    return out

def run(case:Mapping[str,Any],max_steps:int|None=None)->dict[str,Any]:
    state=build(case)
    ntools=len(state["private"]["boundary_by_id"])
    ncaps=len(state["public"]["required_capabilities"])
    budget=max_steps if max_steps is not None else 2+ntools*ncaps+ntools
    if not isinstance(budget,int) or budget<=0:
        raise AdapterError("INVALID_STEP_BUDGET")
    for _ in range(budget):
        if state["terminal"] is not None:
            return state
        state=step(state)
    raise AdapterError("STEP_BUDGET_EXCEEDED")

def oracle_least_cost_sufficient(case:Mapping[str,Any])->str|None:
    tools=_tool_rows(case)
    truth=_truth(case,{x["tool_id"] for x in tools})
    required=sorted({str(x) for x in case.get("required_capabilities",[]) if str(x)})
    constraint=case.get("constraint")
    candidates=[]
    for tool in tools:
        if tool.get("available") is not True or tool.get("authorized") is not True:
            continue
        if not v4._pred(constraint,tool):
            continue
        tid=tool["tool_id"]
        if all(truth[tid].get(cap) is True for cap in required):
            candidates.append(tool)
    if not candidates:
        return None
    candidates.sort(key=lambda x:(float(x["cost"]),str(x["tool_id"])))
    return str(candidates[0]["tool_id"])
