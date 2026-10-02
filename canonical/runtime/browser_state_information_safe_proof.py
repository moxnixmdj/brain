"""Information-safe bounded browser-state proof for BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001.

The candidate sees the declared goal, current rendered element observations, available
actions, and prior action/observation receipts. Hidden transition truth and terminal
success remain evaluator-only. Cases exercise navigation, action, confirmation,
stale-state rebinding, and ambiguity fail-closed behavior.

Preflight only; not whole browser/computer-use scope.
"""
from __future__ import annotations
import copy, random
from collections import defaultdict
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_BROWSER_STATE_INFORMATION_SAFE_PROOF_V1"
CLASSES=("DIRECT","NAVIGATE","CONFIRM","STALE_REBIND","AMBIGUOUS")


def _el(eid,role,name,text,actions,attrs=None,ocr=None):
    return {
        "element_id":eid,"role":role,"name":name,"text":text,
        "ocr_text":ocr if ocr is not None else text,
        "attrs":dict(attrs or {}),"actions":list(actions),
        "visible":True,"enabled":True,
    }


def generate_case(seed:int,ordinal:int)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool) or not isinstance(ordinal,int) or ordinal<0:
        raise ValueError("INPUT")
    r=random.Random((seed<<13)^ordinal^0xB205)
    cls=CLASSES[ordinal%len(CLASSES)]
    target=f"R{r.randrange(1000,9999)}"
    decoys=[f"R{r.randrange(1000,9999)}" for _ in range(2)]
    if target in decoys:
        decoys=[target+"A",target+"B"]
    selected=target if cls in {"DIRECT","CONFIRM","AMBIGUOUS"} else decoys[0]
    state={
        "generation":0,
        "selected":selected,
        "statuses":{target:"pending",decoys[0]:"pending",decoys[1]:"pending"},
        "confirm_open":False,
        "stale_once":cls=="STALE_REBIND",
        "stale_consumed":False,
    }
    return {
        "schema":SCHEMA,
        "behavior_id":"BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001",
        "case_id":f"BROWSER-{seed}-{ordinal}",
        "case_class":cls,
        "goal":{"record_id":target,"desired_status":"approved"},
        "_initial_state":state,
        "_oracle":{"target":target,"expected_terminal_status":"approved","ambiguous":cls=="AMBIGUOUS"},
    }


def _render(case:Mapping[str,Any],state:Mapping[str,Any])->list[dict[str,Any]]:
    gen=int(state["generation"])
    target=case["_oracle"]["target"]
    ids=[target,*[x for x in state["statuses"] if x!=target]]
    rows=[]
    for idx,rid in enumerate(ids):
        attrs={"record_id":rid,"selected":"true" if state["selected"]==rid else "false"}
        rows.append(_el(f"g{gen}-row-{idx}","row",f"Record {rid}",f"Record {rid}",["click"],attrs))
    if case["_oracle"]["ambiguous"]:
        rows.append(_el(f"g{gen}-row-dup","row",f"Record {target}",f"Record {target}",["click"],{"record_id":target,"selected":"false"}))
    selected=state["selected"]
    status=state["statuses"][selected]
    controls=[
        _el(f"g{gen}-status","status","Current status",status,[],{"record_id":selected}),
        _el(f"g{gen}-approve","button","Approve","Approve",["click"],{"record_id":selected}),
    ]
    if state["confirm_open"]:
        controls.append(_el(f"g{gen}-confirm","button","Confirm","Confirm",["click"],{"record_id":selected}))
    return rows+controls


def public_state(case:Mapping[str,Any],state:Mapping[str,Any],history)->dict[str,Any]:
    return {
        "schema":case["schema"],"behavior_id":case["behavior_id"],"case_id":case["case_id"],
        "goal":dict(case["goal"]),
        "render_generation":int(state["generation"]),
        "elements":_render(case,state),
        "action_schema":{"click":{"required":["element_id"]}},
        "history":[dict(x) for x in history],
    }


def _find_current_element(case,state,eid):
    return next((x for x in _render(case,state) if x["element_id"]==eid),None)


def _transition(case,state,action):
    out=copy.deepcopy(state)
    eid=str(action.get("element_id") or "")
    el=_find_current_element(case,state,eid)
    if el is None or action.get("action")!="click" or "click" not in el["actions"]:
        return out,{"ok":False,"reason":"INVALID_OR_STALE_TARGET","element_id":eid}
    target=case["_oracle"]["target"]
    if el["role"]=="row":
        rid=el["attrs"]["record_id"]
        if state["stale_once"] and not state["stale_consumed"] and rid==target:
            out["stale_consumed"]=True
            out["generation"]+=1
            return out,{"ok":True,"effect":"RERENDER_NO_SELECTION_CHANGE","element_id":eid}
        out["selected"]=rid
        out["confirm_open"]=False
        out["generation"]+=1
        return out,{"ok":True,"effect":"SELECTION_CHANGED","element_id":eid}
    if el["name"]=="Approve":
        if state["selected"]!=target:
            out["generation"]+=1
            return out,{"ok":True,"effect":"NO_TARGET_PROGRESS","element_id":eid}
        if case["case_class"]=="CONFIRM":
            out["confirm_open"]=True
            out["generation"]+=1
            return out,{"ok":True,"effect":"CONFIRMATION_OPENED","element_id":eid}
        out["statuses"][target]="approved"
        out["generation"]+=1
        return out,{"ok":True,"effect":"STATUS_APPROVED","element_id":eid}
    if el["name"]=="Confirm" and state["confirm_open"] and state["selected"]==target:
        out["statuses"][target]="approved"
        out["confirm_open"]=False
        out["generation"]+=1
        return out,{"ok":True,"effect":"STATUS_APPROVED","element_id":eid}
    return out,{"ok":False,"reason":"UNSUPPORTED_TRANSITION","element_id":eid}


def run_episode(case:Mapping[str,Any],policy_fn,max_actions:int=8)->dict[str,Any]:
    state=copy.deepcopy(case["_initial_state"]); history=[]
    used_ids=[]
    for step in range(max_actions+1):
        public=public_state(case,state,history)
        action=policy_fn(public)
        if not isinstance(action,Mapping):
            return {"pass":False,"reason":"ACTION_NOT_MAPPING"}
        kind=action.get("action")
        if kind=="ESCALATE":
            if case["_oracle"]["ambiguous"]:
                return {"pass":True,"reason":"PASS_AMBIGUITY_ESCALATED","history":history}
            return {"pass":False,"reason":"UNNECESSARY_ESCALATION","history":history}
        if kind=="STOP":
            if case["_oracle"]["ambiguous"]:
                return {"pass":False,"reason":"AMBIGUITY_NOT_ESCALATED","history":history}
            ok=state["statuses"][case["_oracle"]["target"]]=="approved"
            return {"pass":ok,"reason":"PASS" if ok else "PREMATURE_STOP","history":history}
        if step>=max_actions:
            return {"pass":False,"reason":"ACTION_BUDGET_EXHAUSTED","history":history}
        eid=str(action.get("element_id") or "")
        pre_generation=state["generation"]
        state,receipt=_transition(case,state,action)
        history.append({
            "step":step,"action":"click","element_id":eid,"pre_generation":pre_generation,
            "post_generation":state["generation"],"observation":receipt,
        })
        used_ids.append(eid)
        if receipt.get("ok") is not True:
            return {"pass":False,"reason":"INVALID_ACTION","history":history}
        # A stale-rebind case must never reuse the pre-rerender element id.
        if case["case_class"]=="STALE_REBIND" and len(used_ids)>=2 and used_ids[-1]==used_ids[-2]:
            return {"pass":False,"reason":"STALE_ELEMENT_REUSED","history":history}
    return {"pass":False,"reason":"UNREACHABLE"}


def run_batch(seed:int,count:int,policy_fn)->dict[str,Any]:
    rows=[]; by_class=defaultdict(lambda:{"pass":0,"total":0})
    for ordinal in range(count):
        case=generate_case(seed,ordinal)
        try: verdict=run_episode(case,policy_fn)
        except Exception as exc:
            verdict={"pass":False,"reason":"CANDIDATE_EXCEPTION:"+type(exc).__name__+":"+str(exc)}
        cls=case["case_class"]; by_class[cls]["total"]+=1; by_class[cls]["pass"]+=int(bool(verdict.get("pass")))
        rows.append({"case_id":case["case_id"],"class":cls,"pass":bool(verdict.get("pass")),"reason":verdict.get("reason")})
    passed=sum(int(x["pass"]) for x in rows)
    return {
        "schema":"PROJECT_BRAIN_BROWSER_STATE_INFORMATION_SAFE_PREFLIGHT_RESULT_V1",
        "seed":seed,"case_count":count,"passed":passed,"failed":count-passed,"all_pass":passed==count,
        "by_class":{k:dict(v) for k,v in sorted(by_class.items())},
        "failures":[x for x in rows if not x["pass"]],
        "terminal_authority":False,"capability_credit_delta":0,
    }
