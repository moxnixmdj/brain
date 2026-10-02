"""Information-safe bounded preflight for browser goal-to-action grounding.

Candidate-visible state contains only a plain bounded goal, current structured
DOM/accessibility/OCR observations, raw status text, and prior action receipts.
The target element identity and successful terminal state remain hidden in the
oracle. The environment can inject a no-progress first target action and then
replace element identities after refresh, forcing observation-driven recovery.

This is a bounded preflight. It is not whole-contract or terminal authority.
"""
from __future__ import annotations

import random
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_BROWSER_GOAL_ACTION_INFORMATION_SAFE_PROOF_V1"
_CASES=(
    ("Submit report","Submit report","Report submitted"),
    ("Save draft","Save draft","Draft saved"),
    ("Open settings","Open settings","Settings opened"),
)


def generate_case(seed:int, ordinal:int)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool):
        raise ValueError("SEED_MUST_BE_INTEGER")
    if not isinstance(ordinal,int) or ordinal<0:
        raise ValueError("ORDINAL_MUST_BE_NONNEGATIVE")
    r=random.Random((seed<<17)^ordinal^0xB05E)
    goal,target_label,success_text=_CASES[ordinal%len(_CASES)]
    suffix=str(r.randrange(10000,99999))
    target_id=f"target-{suffix}-0"
    refresh_id=f"refresh-{suffix}-0"
    distractors=[
        {
            "element_id":f"d-{suffix}-0",
            "role":"button","name":"Submit feedback","text":"Submit feedback",
            "ocr_text":"Submit feedback","attrs":{"kind":"secondary"},
            "actions":["click"],"visible":True,"enabled":True,
        },
        {
            "element_id":f"d-{suffix}-1",
            "role":"button","name":"Save report","text":"Save report",
            "ocr_text":"Save report","attrs":{"kind":"secondary"},
            "actions":["click"],"visible":True,"enabled":True,
        },
        {
            "element_id":f"d-{suffix}-2",
            "role":"button","name":"Open help","text":"Open help",
            "ocr_text":"Open help","attrs":{"kind":"secondary"},
            "actions":["click"],"visible":True,"enabled":True,
        },
    ]
    r.shuffle(distractors)
    elements=[
        {
            "element_id":target_id,
            "role":"button","name":target_label,"text":target_label,
            "ocr_text":target_label,"attrs":{"kind":"primary"},
            "actions":["click"],"visible":True,"enabled":True,
        },
        {
            "element_id":refresh_id,
            "role":"button","name":"Refresh","text":"Refresh",
            "ocr_text":"Refresh","attrs":{"kind":"system"},
            "actions":["click"],"visible":True,"enabled":True,
        },
        *distractors,
    ]
    fail_first=(ordinal%2)==1
    return {
        "schema":SCHEMA,
        "case_id":f"BROWSER-GOAL-{seed}-{ordinal}",
        "goal":goal,
        "initial_elements":elements,
        "initial_status_text":"Ready",
        "_oracle":{
            "target_label":target_label,
            "target_id":target_id,
            "refresh_id":refresh_id,
            "success_text":success_text,
            "fail_first_target_action":fail_first,
            "target_generation":0,
            "suffix":suffix,
        },
    }


def public_state(case:Mapping[str,Any],state:Mapping[str,Any])->dict[str,Any]:
    return {
        "schema":case["schema"],
        "case_id":case["case_id"],
        "goal":case["goal"],
        "elements":[dict(x) for x in state["elements"]],
        "status_text":state["status_text"],
        "history":[dict(x) for x in state["history"]],
    }


def _initial_state(case:Mapping[str,Any])->dict[str,Any]:
    return {
        "elements":[dict(x) for x in case["initial_elements"]],
        "status_text":case["initial_status_text"],
        "history":[],
        "refresh_count":0,
        "target_attempts":0,
    }


def _replace_ids_after_refresh(case:Mapping[str,Any],state:dict[str,Any])->None:
    suffix=case["_oracle"]["suffix"]
    generation=state["refresh_count"]
    remap={}
    for row in state["elements"]:
        old=str(row["element_id"])
        if old.startswith("target-"):
            new=f"target-{suffix}-{generation}"
        elif old.startswith("refresh-"):
            new=f"refresh-{suffix}-{generation}"
        else:
            new=old
        remap[old]=new
        row["element_id"]=new


def _execute(case:Mapping[str,Any],state:dict[str,Any],action:Mapping[str,Any])->dict[str,Any]:
    if action.get("action")!="click" or not isinstance(action.get("element_id"),str):
        return {"ok":False,"reason":"ACTION_INVALID"}
    eid=action["element_id"]
    rows={str(x["element_id"]):x for x in state["elements"]}
    row=rows.get(eid)
    if row is None or row.get("visible") is not True or row.get("enabled") is not True:
        return {"ok":False,"reason":"ELEMENT_NOT_ACTIONABLE"}

    label=str(row.get("name") or "")
    before=state["status_text"]
    changed=False
    if label=="Refresh":
        state["refresh_count"]+=1
        state["status_text"]="Ready"
        _replace_ids_after_refresh(case,state)
        changed=True
    elif label==case["_oracle"]["target_label"]:
        state["target_attempts"]+=1
        if not (case["_oracle"]["fail_first_target_action"] and state["target_attempts"]==1):
            state["status_text"]=case["_oracle"]["success_text"]
            changed=True
    else:
        state["status_text"]="No relevant change"

    receipt={
        "kind":"ACTION_RECEIPT",
        "action":"click",
        "element_id":eid,
        "accessible_name":label,
        "state_changed":changed,
        "status_before":before,
        "status_after":state["status_text"],
    }
    state["history"].append(receipt)
    return {"ok":True,"receipt":receipt}


def score_episode(case:Mapping[str,Any],policy,max_actions:int=8)->dict[str,Any]:
    state=_initial_state(case)
    actions=[]
    for step in range(max_actions):
        public=public_state(case,state)
        out=policy(public)
        if not isinstance(out,Mapping):
            return {"pass":False,"reason":"POLICY_OUTPUT_NOT_MAPPING","actions":actions}
        if out.get("status")=="DONE":
            if state["status_text"]!=case["_oracle"]["success_text"]:
                return {"pass":False,"reason":"PREMATURE_DONE","actions":actions}
            if case["_oracle"]["fail_first_target_action"] and state["refresh_count"]<1:
                return {"pass":False,"reason":"NO_RECOVERY_AFTER_NO_PROGRESS","actions":actions}
            return {
                "pass":True,
                "reason":"PASS",
                "actions":actions,
                "refresh_count":state["refresh_count"],
                "target_attempts":state["target_attempts"],
                "terminal_authority":False,
                "capability_credit_delta":0,
            }
        if out.get("status")!="ACT":
            return {"pass":False,"reason":"POLICY_DID_NOT_ACT_OR_FINISH","actions":actions,"policy":dict(out)}
        action={"action":out.get("action"),"element_id":out.get("element_id")}
        receipt=_execute(case,state,action)
        actions.append(action)
        if receipt.get("ok") is not True:
            return {"pass":False,"reason":"EXECUTION_"+str(receipt.get("reason")),"actions":actions}
    return {"pass":False,"reason":"ACTION_BUDGET_EXHAUSTED","actions":actions}


def run_batch(seed:int,case_count:int,policy)->dict[str,Any]:
    rows=[]
    for ordinal in range(case_count):
        case=generate_case(seed,ordinal)
        verdict=score_episode(case,policy)
        rows.append({
            "case_id":case["case_id"],
            "fail_first":case["_oracle"]["fail_first_target_action"],
            "pass":bool(verdict.get("pass")),
            "reason":verdict.get("reason"),
        })
    passed=sum(int(x["pass"]) for x in rows)
    return {
        "schema":"PROJECT_BRAIN_BROWSER_GOAL_ACTION_INFORMATION_SAFE_PREFLIGHT_RESULT_V1",
        "case_count":case_count,
        "passed":passed,
        "failed":case_count-passed,
        "all_pass":passed==case_count,
        "failures":[x for x in rows if not x["pass"]],
        "terminal_authority":False,
        "capability_credit_delta":0,
    }
