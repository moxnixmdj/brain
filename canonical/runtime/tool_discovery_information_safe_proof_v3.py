"""V3 hidden-world proof for TOOL_ROUTE_DISCOVERY_AND_SELECTION_001.

Exercises dynamic catalog discovery, generic explicit active constraints,
least-cost hidden-capability probing, transfer, version invalidation, escalation,
and matched schema-only/popularity baselines. Hidden capability truth and ideal
route remain verifier-only.
"""
from __future__ import annotations

from collections import defaultdict
import random
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_INFORMATION_SAFE_PROOF_V3"
CLASSES=(
 "DYNAMIC_DISCOVERY_BASELINE_TRAP",
 "ACTIVE_CONSTRAINT_TRAP",
 "TRANSFER_REUSE",
 "VERSION_INVALIDATION",
 "UNAVAILABLE_OR_UNAUTHORIZED",
 "NO_SUFFICIENT_ROUTE",
)
REQ=("CAP_A","CAP_B")


def _tool(tid,cost,pop,region,privacy,latency,*,available=True,authorized=True):
    return {
      "tool_id":tid,"cost":float(cost),"popularity":int(pop),
      "available":bool(available),"authorized":bool(authorized),"epoch":0,
      "attributes":{"region":region,"privacy_tier":int(privacy),"latency_ms":int(latency),"license":"permissive"},
    }


def generate_case(seed:int,ordinal:int)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool) or not isinstance(ordinal,int) or ordinal<0:
        raise ValueError("INPUT")
    r=random.Random((seed<<17)^ordinal^0x7001D15C)
    s=str(r.randrange(10000,99999));cls=CLASSES[ordinal%len(CLASSES)]
    ids=[f"T{i}_{s}" for i in range(5)]
    tools=[
      _tool(ids[0],1.0,100,"eu",2,80),
      _tool(ids[1],2.0,80,"eu",3,70),
      _tool(ids[2],3.0,10,"eu",3,60),
      _tool(ids[3],0.5,200,"us",1,200),
      _tool(ids[4],4.0,5,"eu",4,50),
    ]
    if cls=="UNAVAILABLE_OR_UNAUTHORIZED":
        # Exercise availability and authorization independently. Keep tool1
        # eligible-but-insufficient so schema-only/popularity baselines remain
        # discriminating instead of accidentally selecting the same oracle-best route.
        if (ordinal // len(CLASSES)) % 2 == 0:
            tools[0]["available"]=False
        else:
            tools[0]["authorized"]=False

    epoch0={
      ids[0]:{"CAP_A"},
      ids[1]:{"CAP_B"},
      ids[2]:{"CAP_A","CAP_B"},
      ids[3]:{"CAP_A","CAP_B"},
      ids[4]:{"CAP_A","CAP_B"},
    }
    epoch1={k:set(v) for k,v in epoch0.items()}
    version_events=[]
    if cls=="VERSION_INVALIDATION":
        epoch1[ids[2]]={"CAP_A"}
        version_events=[{"kind":"TOOL_VERSION_CHANGED","tool_id":ids[2],"new_epoch":1}]
    if cls=="NO_SUFFICIENT_ROUTE":
        epoch0[ids[2]]={"CAP_A"};epoch0[ids[4]]={"CAP_A"}
        epoch1={k:set(v) for k,v in epoch0.items()}

    # Discovery is intentionally paged and the eventual optimum is not present
    # in the initial page.
    pages=[[tools[0],tools[3]],[tools[1]],[tools[2],tools[4]]]
    constraints=[
      {"field":"region","op":"eq","value":"eu"},
      {"field":"privacy_tier","op":"ge","value":2},
      {"field":"latency_ms","op":"le","value":120},
      {"field":"license","op":"in","value":["permissive","public-domain"]},
    ]
    return {
      "schema":SCHEMA,"behavior_id":"TOOL_ROUTE_DISCOVERY_AND_SELECTION_001",
      "case_id":f"TOOL-V3-{seed}-{ordinal}","case_class":cls,
      "pages":pages,
      "stage1":{"required_capabilities":list(REQ),"version_events":[]},
      "stage2":{"required_capabilities":list(REQ),"version_events":version_events},
      "active_constraints":constraints,
      "_oracle":{"epoch0":epoch0,"epoch1":epoch1},
    }


def _epochs(case,stage):
    out={t["tool_id"]:0 for page in case["pages"] for t in page}
    if stage==2:
        for ev in case["stage2"]["version_events"]:
            out[ev["tool_id"]]=int(ev["new_epoch"])
    return out


def _hidden_caps(case,stage,tid):
    ep=_epochs(case,stage)[tid]
    return set(case["_oracle"]["epoch1" if ep else "epoch0"][tid])


def _constraint_ok(t,c):
    x=(t.get("attributes") or {}).get(c["field"],t.get(c["field"]))
    y=c["value"];op=c["op"]
    if op=="eq":return x==y
    if op=="ne":return x!=y
    if op=="in":return x in y
    if op=="not_in":return x not in y
    if op=="le":return x<=y
    if op=="lt":return x<y
    if op=="ge":return x>=y
    if op=="gt":return x>y
    raise ValueError(op)


def _eligible(case,stage):
    rows=[t for page in case["pages"] for t in page]
    return sorted([
      t for t in rows if t["available"] and t["authorized"]
      and all(_constraint_ok(t,c) for c in case["active_constraints"])
    ],key=lambda t:(t["cost"],t["tool_id"]))


def _oracle_best(case,stage):
    req=set(case["stage1" if stage==1 else "stage2"]["required_capabilities"])
    for t in _eligible(case,stage):
        if req.issubset(_hidden_caps(case,stage,t["tool_id"])):
            return t["tool_id"]
    raise ValueError("NO_SUFFICIENT_ROUTE")


def _receipt_map(case,stage,receipts):
    epochs=_epochs(case,stage);out={}
    for rec in receipts:
        if rec.get("kind")=="SAFE_CAPABILITY_PROBE" and rec.get("epoch")==epochs.get(rec.get("tool_id")):
            out[(rec["tool_id"],rec["capability"])]=rec["supported"] is True
    return out


def _public(case,stage,visible_pages,receipts):
    tools=[dict(t)|{"attributes":dict(t["attributes"])} for p in case["pages"][:visible_pages] for t in p]
    return {
      "schema":case["schema"],"case_id":case["case_id"],
      "required_capabilities":list(case["stage1" if stage==1 else "stage2"]["required_capabilities"]),
      "tools":tools,"active_constraints":[dict(c) for c in case["active_constraints"]],
      "prior_probe_receipts":[dict(r) for r in receipts],
      "version_events":[dict(e) for e in (case["stage2"]["version_events"] if stage==2 else [])],
      "catalog_complete":visible_pages>=len(case["pages"]),
      "discovery_cursor":None if visible_pages>=len(case["pages"]) else str(visible_pages),
    }


def public_initial(case): return _public(case,1,1,[])


def _probe(case,stage,action,receipts):
    tid=str(action.get("tool_id") or "");cap=str(action.get("capability") or "")
    visible={t["tool_id"] for p in case["pages"] for t in p}
    if tid not in visible or cap not in REQ:
        raise ValueError("INVALID_PROBE")
    ep=_epochs(case,stage)[tid]
    rec={"kind":"SAFE_CAPABILITY_PROBE","tool_id":tid,"capability":cap,"epoch":ep,
         "supported":cap in _hidden_caps(case,stage,tid),"stage":stage}
    receipts.append(rec)


def _baseline_failures(case,stage):
    eligible=_eligible(case,stage);req=set(REQ)
    if not eligible:return {"schema_only":0,"popularity":0}
    schema=eligible[0]
    popular=sorted(eligible,key=lambda t:(-t["popularity"],t["cost"],t["tool_id"]))[0]
    return {
      "schema_only":0 if req.issubset(_hidden_caps(case,stage,schema["tool_id"])) else 1,
      "popularity":0 if req.issubset(_hidden_caps(case,stage,popular["tool_id"])) else 1,
    }


def _run_stage(case,stage,policy,receipts,*,initial_pages=1,max_actions=40):
    pages=initial_pages;actions=[];seen=set();failed_route_invocations=0
    for _ in range(max_actions):
        public=_public(case,stage,pages,receipts)
        action=policy(public)
        if not isinstance(action,Mapping):return {"pass":False,"reason":"ACTION_NOT_MAPPING","actions":actions}
        kind=action.get("action")
        if kind=="DISCOVER":
            if pages>=len(case["pages"]):return {"pass":False,"reason":"DISCOVER_AFTER_COMPLETE","actions":actions}
            cursor=action.get("cursor")
            if str(cursor)!=str(pages):return {"pass":False,"reason":"WRONG_DISCOVERY_CURSOR","actions":actions}
            pages+=1;actions.append({"action":"DISCOVER","visible_pages":pages});continue
        if kind=="PROBE":
            key=(stage,str(action.get("tool_id")),str(action.get("capability")),_epochs(case,stage).get(str(action.get("tool_id"))))
            if key in seen:return {"pass":False,"reason":"DUPLICATE_PROBE","actions":actions}
            seen.add(key)
            try:_probe(case,stage,action,receipts)
            except Exception as exc:return {"pass":False,"reason":"PROBE:"+str(exc),"actions":actions}
            actions.append({"action":"PROBE","tool_id":action["tool_id"],"capability":action["capability"]});continue
        if kind=="SELECT":
            try:best=_oracle_best(case,stage)
            except ValueError:return {"pass":False,"reason":"SELECT_WHEN_NO_ROUTE","actions":actions}
            tid=str(action.get("tool_id") or "")
            if tid!=best:
                failed_route_invocations+=1
                return {"pass":False,"reason":"NONOPTIMAL_OR_INSUFFICIENT_SELECTION","actions":actions}
            evidence=_receipt_map(case,stage,receipts)
            if not all(evidence.get((tid,c)) is True for c in REQ):
                return {"pass":False,"reason":"SELECT_WITHOUT_CURRENT_EVIDENCE","actions":actions}
            base=_baseline_failures(case,stage)
            actions.append({"action":"SELECT","tool_id":tid})
            return {"pass":True,"reason":"PASS","selected":tid,"actions":actions,
                    "failed_route_invocations":failed_route_invocations,"baselines":base}
        if kind=="ESCALATE":
            try:best=_oracle_best(case,stage)
            except ValueError:
                evidence=_receipt_map(case,stage,receipts)
                for t in _eligible(case,stage):
                    if not any(evidence.get((t["tool_id"],c)) is False for c in REQ):
                        return {"pass":False,"reason":"PREMATURE_ESCALATION","actions":actions}
                base=_baseline_failures(case,stage)
                return {"pass":True,"reason":"PASS_ESCALATE","selected":None,"actions":actions,
                        "failed_route_invocations":0,"baselines":base}
            return {"pass":False,"reason":"ESCALATE_DESPITE_ROUTE:"+best,"actions":actions}
        return {"pass":False,"reason":"UNKNOWN_ACTION","actions":actions}
    return {"pass":False,"reason":"ACTION_BUDGET","actions":actions}


def score_episode(case,policy):
    receipts=[]
    s1=_run_stage(case,1,policy,receipts)
    if not s1["pass"]:return {"pass":False,"reason":"STAGE1_"+s1["reason"],"stage1":s1}
    if case["case_class"]=="NO_SUFFICIENT_ROUTE":
        base=s1["baselines"]
        strict=(s1["failed_route_invocations"]<base["schema_only"] or s1["failed_route_invocations"]<base["popularity"])
        return {"pass":strict,"reason":"PASS" if strict else "NO_BASELINE_ADVANTAGE","stage1":s1}

    probes1=sum(1 for a in s1["actions"] if a["action"]=="PROBE")
    s2=_run_stage(case,2,policy,receipts,initial_pages=len(case["pages"]))
    if not s2["pass"]:return {"pass":False,"reason":"STAGE2_"+s2["reason"],"stage1":s1,"stage2":s2}
    probes2=sum(1 for a in s2["actions"] if a["action"]=="PROBE")
    if case["case_class"]=="TRANSFER_REUSE" and probes2>=probes1:
        return {"pass":False,"reason":"TRANSFER_DID_NOT_REDUCE_PROBES","stage1":s1,"stage2":s2}
    if case["case_class"]=="VERSION_INVALIDATION" and s2["selected"]==s1["selected"]:
        return {"pass":False,"reason":"STALE_VERSION_SELECTION_NOT_REVERSED","stage1":s1,"stage2":s2}
    base=s1["baselines"]
    strict=(s1["failed_route_invocations"]<base["schema_only"] or s1["failed_route_invocations"]<base["popularity"])
    return {"pass":strict,"reason":"PASS" if strict else "NO_BASELINE_ADVANTAGE","stage1":s1,"stage2":s2}


def run_batch(seed,count,policy):
    rows=[];by=defaultdict(lambda:{"pass":0,"total":0})
    for i in range(count):
        case=generate_case(seed,i)
        try:v=score_episode(case,policy)
        except Exception as exc:v={"pass":False,"reason":"EXCEPTION:"+type(exc).__name__+":"+str(exc)}
        cls=case["case_class"];by[cls]["total"]+=1;by[cls]["pass"]+=int(bool(v["pass"]))
        rows.append({"case_id":case["case_id"],"class":cls,"pass":bool(v["pass"]),"reason":v["reason"]})
    passed=sum(int(x["pass"]) for x in rows)
    return {"schema":"PROJECT_BRAIN_TOOL_DISCOVERY_V3_PREFLIGHT_RESULT","case_count":count,
            "passed":passed,"failed":count-passed,"all_pass":passed==count,
            "by_class":dict(sorted(by.items())),"failures":[x for x in rows if not x["pass"]],
            "terminal_authority":False,"capability_credit_delta":0,"family_credit_delta":0,"incremental_spend_usd":0}
