"""Hardened V2 information-safe proof for TOOL_ROUTE_DISCOVERY_AND_SELECTION_001.

V2 preserves the V1 hidden-capability, transfer, and version-change population and
adds the contract branches V1 did not exercise:
- cheaper route unavailable,
- cheaper route unauthorized,
- no sufficient tool route, which must escalate only after relevant safe probes.

The candidate remains the exact V1 Brain policy. This proof is still preterminal:
no post-freeze beacon or terminal case is consumed here.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from canonical.runtime import tool_discovery_information_safe_proof as v1

SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_INFORMATION_SAFE_PROOF_V2"
CLASSES=(
    "NO_CHANGE",
    "SELECTED_TOOL_LOSES_CAPABILITY",
    "CHEAPER_TOOL_GAINS_CAPABILITY",
    "CHEAPER_TOOL_UNAVAILABLE",
    "CHEAPER_TOOL_UNAUTHORIZED",
    "NO_SUFFICIENT_ROUTE",
)


def generate_case(seed:int,ordinal:int)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool):
        raise ValueError("SEED")
    if not isinstance(ordinal,int) or ordinal<0:
        raise ValueError("ORDINAL")
    cls=CLASSES[ordinal%len(CLASSES)]
    # V1's three original classes map directly by ordinal 0..2.
    if cls in CLASSES[:3]:
        case=v1.generate_case(seed,ordinal%3)
        case["schema"]=SCHEMA
        case["case_id"]=f"TOOL-DISCOVERY-V2-{seed}-{ordinal}"
        case["case_class"]=cls
        return case

    # Start from a stable no-change V1 world and mutate only public route status
    # or hidden capability support as required by the additional contract branch.
    case=v1.generate_case(seed,0)
    case["schema"]=SCHEMA
    case["case_id"]=f"TOOL-DISCOVERY-V2-{seed}-{ordinal}"
    case["case_class"]=cls
    cheapest=case["tools"][0]
    if cls=="CHEAPER_TOOL_UNAVAILABLE":
        cheapest["available"]=False
    elif cls=="CHEAPER_TOOL_UNAUTHORIZED":
        cheapest["authorized"]=False
    elif cls=="NO_SUFFICIENT_ROUTE":
        required=set(case["stage1"]["required_capabilities"])
        for table_name in ("epoch0","epoch1"):
            table=case["_oracle"][table_name]
            for tid in list(table):
                table[tid]=set(table[tid])-required
        # Stage 2 is irrelevant after a justified stage-1 escalation.
        case["stage2"]["version_events"]=[]
    return case


def public_stage(case:Mapping[str,Any],stage:int,receipts=()):
    # Reuse the V1 information boundary exactly.
    return v1.public_stage(case,stage,receipts)


def _execute_allow_escalate(
    case:Mapping[str,Any],
    stage:int,
    policy,
    receipts:list[dict[str,Any]],
    *,
    max_actions:int=24,
)->dict[str,Any]:
    seen_probe_keys={
        (int(r["stage"]),str(r["tool_id"]),str(r["capability"]),int(r["epoch"]))
        for r in receipts if r.get("kind")=="SAFE_CAPABILITY_PROBE"
    }
    actions=[]
    for i in range(max_actions):
        public=v1._public_stage(case,stage,receipts)
        action=policy(public)
        if not isinstance(action,Mapping):
            return {"pass":False,"reason":"ACTION_NOT_MAPPING","actions":actions}
        kind=action.get("action")
        if kind=="PROBE":
            try:
                rec=v1._probe_receipt(case,stage,action,i)
            except Exception as exc:
                return {"pass":False,"reason":type(exc).__name__+":"+str(exc),"actions":actions}
            key=(stage,rec["tool_id"],rec["capability"],rec["epoch"])
            if key in seen_probe_keys:
                return {"pass":False,"reason":"DUPLICATE_PROBE_SAME_EPOCH","actions":actions}
            seen_probe_keys.add(key)
            receipts.append(rec)
            actions.append({
                "action":"PROBE","tool_id":rec["tool_id"],
                "capability":rec["capability"],"epoch":rec["epoch"],
            })
            continue
        if kind=="SELECT":
            try:
                expected=v1._oracle_best_tool(case,stage)
            except ValueError as exc:
                if str(exc)=="NO_SUFFICIENT_TOOL":
                    return {"pass":False,"reason":"SELECTED_WHEN_NO_SUFFICIENT_TOOL","actions":actions}
                raise
            tid=str(action.get("tool_id") or "")
            if tid!=expected:
                return {"pass":False,"reason":"NONOPTIMAL_OR_INSUFFICIENT_SELECTION","selected":tid,"expected":expected,"actions":actions}
            if not v1._selection_is_evidence_supported(case,stage,receipts,tid):
                return {"pass":False,"reason":"SELECTION_WITHOUT_CURRENT_POSITIVE_EVIDENCE","actions":actions}
            actions.append({"action":"SELECT","tool_id":tid})
            return {
                "pass":True,"reason":"PASS","selected":tid,"actions":actions,
                "probe_count":sum(1 for x in actions if x["action"]=="PROBE"),
            }
        if kind=="ESCALATE":
            try:
                expected=v1._oracle_best_tool(case,stage)
            except ValueError as exc:
                if str(exc)!="NO_SUFFICIENT_TOOL":
                    return {"pass":False,"reason":"ORACLE_ERROR:"+str(exc),"actions":actions}
                # Escalation is admissible only after every currently eligible
                # tool has at least one current negative receipt for a required
                # capability. Otherwise the policy abandoned an untested route.
                req=set((case["stage1"] if stage==1 else case["stage2"])["required_capabilities"])
                evidence=v1._valid_receipt_map(case,stage,receipts)
                epochs=v1._epoch_map(case,stage)
                eligible=[
                    t for t in case["tools"]
                    if t.get("available") is True and t.get("authorized") is True
                ]
                for tool in eligible:
                    tid=str(tool["tool_id"])
                    negatives=[
                        evidence.get((tid,cap)) is False
                        for cap in req
                        if (tid,cap) in evidence
                    ]
                    if not any(negatives):
                        return {"pass":False,"reason":"PREMATURE_ESCALATION_WITH_UNTESTED_ROUTE","tool_id":tid,"actions":actions}
                actions.append({"action":"ESCALATE"})
                return {
                    "pass":True,"reason":"PASS_ESCALATE_NO_SUFFICIENT_ROUTE",
                    "selected":None,"actions":actions,
                    "probe_count":sum(1 for x in actions if x["action"]=="PROBE"),
                }
            return {"pass":False,"reason":"ESCALATED_DESPITE_SUFFICIENT_ROUTE","expected":expected,"actions":actions}
        return {"pass":False,"reason":"UNKNOWN_ACTION","actions":actions}
    return {"pass":False,"reason":"ACTION_BUDGET_EXHAUSTED","actions":actions}


def score_episode(case:Mapping[str,Any],policy)->dict[str,Any]:
    receipts=[]
    if case["case_class"]=="NO_SUFFICIENT_ROUTE":
        s1=_execute_allow_escalate(case,1,policy,receipts)
        return {
            "schema":SCHEMA,
            "pass":bool(s1["pass"] and s1["reason"]=="PASS_ESCALATE_NO_SUFFICIENT_ROUTE"),
            "reason":s1["reason"],
            "stage1":s1,
            "terminal_authority":False,
            "capability_credit_delta":0,
        }

    # The V1 scorer already checks hidden capability discovery, least-cost
    # sufficient selection, evidence transfer, version invalidation, and
    # reselection. It naturally honors availability/authorization because the
    # oracle and candidate both exclude ineligible routes.
    verdict=v1.score_episode(case,policy)
    verdict=dict(verdict)
    verdict["schema"]=SCHEMA
    return verdict


def run_batch(seed:int,case_count:int,policy)->dict[str,Any]:
    rows=[]
    by_class=defaultdict(lambda:{"pass":0,"total":0,"reasons":defaultdict(int)})
    for ordinal in range(case_count):
        case=generate_case(seed,ordinal)
        try:
            verdict=score_episode(case,policy)
        except Exception as exc:
            verdict={"pass":False,"reason":"CANDIDATE_EXCEPTION:"+type(exc).__name__+":"+str(exc)}
        cls=case["case_class"]
        by_class[cls]["total"]+=1
        by_class[cls]["pass"]+=int(bool(verdict["pass"]))
        by_class[cls]["reasons"][verdict["reason"]]+=1
        rows.append({"case_id":case["case_id"],"class":cls,"pass":bool(verdict["pass"]),"reason":verdict["reason"]})
    passed=sum(int(x["pass"]) for x in rows)
    return {
        "schema":"PROJECT_BRAIN_TOOL_DISCOVERY_INFORMATION_SAFE_PREFLIGHT_RESULT_V2",
        "seed":seed,"case_count":case_count,"passed":passed,
        "failed":case_count-passed,"all_pass":passed==case_count,
        "by_class":{
            cls:{
                "pass":v["pass"],"total":v["total"],
                "fraction":v["pass"]/v["total"] if v["total"] else 0.0,
                "reasons":dict(sorted(v["reasons"].items())),
            }
            for cls,v in sorted(by_class.items())
        },
        "failures":[x for x in rows if not x["pass"]],
        "terminal_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "incremental_spend_usd":0,
    }
