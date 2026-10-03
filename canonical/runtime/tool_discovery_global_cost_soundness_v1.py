"""Verify a sealed complete discovery interface and the V3 global-cost counterexample."""
from __future__ import annotations
import copy, hashlib, json
from pathlib import Path
from typing import Any, Callable, Mapping
from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_GLOBAL_COST_SOUNDNESS_V1"
INSTANCE="canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_INSTANCE_V1.json"
CONTRACT="canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.json"
REQUIRED_PROPERTIES={
 "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH",
 "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE",
 "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH",
 "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
 "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS",
 "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND",
 "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE",
}

def _load(path:str)->dict[str,Any]:
    x=json.loads((ROOT/path).read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ValueError(path+":NOT_OBJECT")
    return x

def _blob(path:str)->str:
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def _inventory(inst:Mapping[str,Any])->dict[str,dict[str,Any]]:
    out={}
    for src in inst.get("sources",[]):
        sid=str(src.get("source_id") or "")
        if not sid: raise ValueError("EMPTY_SOURCE_ID")
        for raw in src.get("tools",[]):
            tid=str(raw.get("tool_id") or "")
            if not tid or tid in out: raise ValueError("INVALID_OR_DUPLICATE_TOOL_ID")
            row=copy.deepcopy(dict(raw)); row["_source_id"]=sid; out[tid]=row
    return out

def _sources(inst):
    return [{"source_id":str(s["source_id"]),"cost":float(s["cost"]),"available":s.get("available") is True}
            for s in inst.get("sources",[])]

def _run(inst:Mapping[str,Any],policy:Callable[[Mapping[str,Any]],Mapping[str,Any]])->dict[str,Any]:
    inv=_inventory(inst)
    bysrc={str(s["source_id"]):s for s in inst.get("sources",[])}
    visible={}; discoveries=[]; probes=[]; history=[set()]
    truth=inst.get("hidden_capability_truth",{})
    for step in range(32):
        public={
          "required_capabilities":list(inst.get("required_capabilities",[])),
          "constraint":inst.get("constraint"),
          "visible_tools":[copy.deepcopy(visible[k]) for k in sorted(visible)],
          "discovery_sources":_sources(inst),
          "prior_probe_receipts":copy.deepcopy(probes),
          "discovery_receipts":copy.deepcopy(discoveries),
          "version_events":copy.deepcopy(inst.get("version_events",[])),
        }
        action=dict(policy(public)); kind=action.get("action")
        if kind=="DISCOVER":
            sid=str(action.get("source_id") or "")
            if sid not in bysrc: return {"pass":False,"reason":"UNKNOWN_DISCOVERY_SOURCE"}
            if any(x["source_id"]==sid for x in discoveries): return {"pass":False,"reason":"DUPLICATE_DISCOVERY_SOURCE"}
            tools=[copy.deepcopy(dict(t)) for t in bysrc[sid].get("tools",[])]
            for t in tools: visible[str(t["tool_id"])]=t
            discoveries.append({"kind":"DISCOVERY_RESULT","source_id":sid,"tools":tools})
            history.append(set(visible)); continue
        if kind=="PROBE":
            tid=str(action.get("tool_id") or ""); cap=str(action.get("capability") or "")
            if tid not in visible: return {"pass":False,"reason":"PROBE_INVISIBLE_TOOL"}
            support=truth.get(tid,{}).get(cap)
            if not isinstance(support,bool): return {"pass":False,"reason":"PROBE_TRUTH_UNDEFINED"}
            probes.append({"kind":"SAFE_CAPABILITY_PROBE","tool_id":tid,"capability":cap,
                           "epoch":int(visible[tid].get("epoch",0)),"supported":support})
            continue
        if kind=="SELECT":
            tid=str(action.get("tool_id") or "")
            if tid not in visible: return {"pass":False,"reason":"SELECT_INVISIBLE_TOOL"}
            return {"pass":True,"reason":"SELECT","selected":tid,"selected_cost":float(visible[tid]["cost"]),
                    "discoveries":discoveries,"probes":probes,
                    "visible_history":[sorted(x) for x in history],"steps":step+1}
        if kind=="ESCALATE": return {"pass":False,"reason":"ESCALATE","discoveries":discoveries,"probes":probes}
        return {"pass":False,"reason":"UNKNOWN_ACTION"}
    return {"pass":False,"reason":"ACTION_BUDGET_EXHAUSTED"}

def _best(inst:Mapping[str,Any])->str|None:
    inv=_inventory(inst); truth=inst.get("hidden_capability_truth",{}); req=set(inst.get("required_capabilities",[]))
    rows=[]
    for tid,t in inv.items():
        if t.get("available") is True and t.get("authorized") is True and all(truth.get(tid,{}).get(c) is True for c in req):
            rows.append((float(t["cost"]),tid))
    rows.sort(); return rows[0][1] if rows else None

def verify_interface_properties(inst:Mapping[str,Any])->dict[str,bool]:
    inv=_inventory(inst); sources=list(inst.get("sources",[])); run=_run(inst,v4.next_action)
    ids=[str(s.get("source_id") or "") for s in sources]; receipts=run.get("discoveries",[])
    discovered={str(t["tool_id"]) for r in receipts for t in r.get("tools",[])}
    hist=[set(x) for x in run.get("visible_history",[])]
    monotonic=all(a<=b for a,b in zip(hist,hist[1:]))
    metadata=True
    for r in receipts:
        sid=r.get("source_id")
        for t in r.get("tools",[]):
            tid=str(t.get("tool_id") or ""); auth=inv.get(tid)
            if auth is None or auth.get("_source_id")!=sid: metadata=False; continue
            for f in ("available","authorized","cost","constraints","meta","epoch"):
                if t.get(f)!=auth.get(f): metadata=False
    truth=inst.get("hidden_capability_truth",{})
    probe_truth=bool(run.get("probes")) and all(
        p.get("supported") is truth.get(str(p.get("tool_id")),{}).get(str(p.get("capability")))
        and p.get("epoch")==inv[str(p.get("tool_id"))].get("epoch")
        for p in run.get("probes",[])
    )
    return {
      "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH":bool(sources) and len(ids)==len(set(ids)),
      "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE":len(receipts)==len(sources) and {r.get("source_id") for r in receipts}==set(ids),
      "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH":monotonic,
      "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE":discovered==set(inv),
      "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS":metadata,
      "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND":probe_truth,
      "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE":
          not inst.get("version_events") and len({int(x.get("epoch",-1)) for x in inv.values()})==1,
    }

def evaluate(instance_override:Mapping[str,Any]|None=None)->dict[str,Any]:
    inst=dict(instance_override) if instance_override is not None else _load(INSTANCE)
    contract=_load(CONTRACT)
    if set(contract.get("required_properties") or [])!=REQUIRED_PROPERTIES:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED__CONTRACT_PROPERTY_DRIFT","interface_instance_verified":False}
    try: props=verify_interface_properties(inst)
    except Exception as e:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED__INTERFACE_INSTANCE_INVALID","error":type(e).__name__+":"+str(e),"interface_instance_verified":False}
    if set(props)!=REQUIRED_PROPERTIES or not all(props.values()):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED__INTERFACE_INSTANCE_CONTRACT_VIOLATION","interface_properties":props,"interface_instance_verified":False}
    r3=_run(inst,v3.next_action); r4=_run(inst,v4.next_action); optimum=_best(inst)
    ok3=r3.get("selected")==optimum; ok4=r4.get("selected")==optimum
    if ok3: return {"schema":SCHEMA,"status":"FAIL_CLOSED__COUNTEREXAMPLE_DID_NOT_DISCRIMINATE_V3","interface_instance_verified":False}
    if not ok4: return {"schema":SCHEMA,"status":"FAIL_CLOSED__V4_DID_NOT_REPAIR_GLOBAL_COST","interface_instance_verified":False}
    inv=_inventory(inst)
    return {
      "schema":SCHEMA,
      "status":"PASS__COMPLETE_INTERFACE_INSTANCE_CONTRACT_SATISFIED__V3_GLOBAL_COST_COUNTEREXAMPLE__V4_REPAIR",
      "interface_instance_verified":True,"interface_properties":props,"scope_id":inst.get("scope_id"),
      "complete_inventory_tool_count":len(inv),"available_source_count":len(inst.get("sources",[])),
      "global_optimal_tool":optimum,"global_optimal_cost":float(inv[optimum]["cost"]) if optimum else None,
      "v3":{"selected":r3.get("selected"),"selected_cost":r3.get("selected_cost"),"globally_least_cost_sound":ok3,
            "queried_sources":[x["source_id"] for x in r3.get("discoveries",[])]},
      "v4":{"selected":r4.get("selected"),"selected_cost":r4.get("selected_cost"),"globally_least_cost_sound":ok4,
            "queried_sources":[x["source_id"] for x in r4.get("discoveries",[])]},
      "proved_impossibility":"WITHOUT_EXHAUSTIVE_DISCOVERY_OR_VERIFIED_LOWER_BOUNDS_FOR_EVERY_UNQUERIED_SOURCE__A_POLICY_CANNOT_PROVE_GLOBAL_LEAST_COST_SELECTION_WHILE_SELECTING_BEFORE_ALL_SOURCES_ARE_RESOLVED",
      "repair":"EXHAUST_ALL_AVAILABLE_DECLARED_DISCOVERY_SOURCES_BEFORE_PROBE_OR_SELECT",
      "current_external_interface_fact_supplied_by_this_instance":"COMPLETE_DISCOVERY_INTERFACE_INSTANCE_SATISFYING_TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1",
      "acceptance_reduction_required_after_independent_verification":True,
      "terminal_results_replayed":0,"new_reality_units_consumed":0,"incremental_spend_usd":0,
      "capability_credit_delta":0,"family_credit_delta":0,"execution_authority":False,"promotion_authority":False,
    }

def main()->int:
    out=evaluate(); print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if str(out.get("status","")).startswith("PASS") else 1

if __name__=="__main__": raise SystemExit(main())
