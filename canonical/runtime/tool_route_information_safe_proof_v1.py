"""Information-safe bounded preflight for tool discovery and selection.

The proof world hides tool capabilities. The candidate sees only tool ids, costs,
probe permission, the required capability, and probe outcomes after it explicitly
chooses a safe probe. This is bounded preflight evidence, never terminal authority.
"""
from __future__ import annotations

import random
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TOOL_ROUTE_INFORMATION_SAFE_PREFLIGHT_V1"


def generate_case(seed:int, *, change_epoch:bool=False)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool):
        raise ValueError("SEED_MUST_BE_INTEGER")
    r=random.Random(seed)
    count=4
    costs=sorted(r.sample(range(1,20),count))
    ids=[f"T{i}" for i in range(count)]
    r.shuffle(ids)
    tools=[{"tool_id":tid,"cost":cost,"safe_probe":True} for tid,cost in zip(ids,costs)]
    # At least one incapable cheaper tool and one capable tool.
    winner_index=r.randint(1,count-1)
    winner=tools[winner_index]["tool_id"]
    capabilities={row["tool_id"]:False for row in tools}
    capabilities[winner]=True
    # Occasionally let a more expensive tool also work so least-cost matters.
    if winner_index+1<count and seed%2==0:
        capabilities[tools[winner_index+1]["tool_id"]]=True
    task1={"task_id":"A","required_capability":"CAP_X","catalog_epoch":"E1"}
    task2={"task_id":"B","required_capability":"CAP_X","catalog_epoch":"E2" if change_epoch else "E1"}
    second_caps=dict(capabilities)
    if change_epoch:
        # Rotate capability to force stale learned state invalidation.
        for k in second_caps:
            second_caps[k]=False
        second_winner=tools[min(count-1,winner_index+1)]["tool_id"]
        second_caps[second_winner]=True
    else:
        second_winner=winner
    return {
        "schema":SCHEMA,
        "behavior_id":"TOOL_ROUTE_DISCOVERY_AND_SELECTION_001",
        "seed":seed,
        "public":{
            "tools":tools,
            "tasks":[task1,task2],
            "constraints":{"probe_only_when_needed":True,"select_least_cost_verified_capable":True},
        },
        "_oracle":{
            "epochs":{"E1":capabilities,"E2":second_caps},
            "least_cost":{
                "E1":min((row["cost"],row["tool_id"]) for row in tools if capabilities[row["tool_id"]])[1],
                "E2":min((row["cost"],row["tool_id"]) for row in tools if second_caps[row["tool_id"]])[1],
            },
            "change_epoch":change_epoch,
            "second_winner":second_winner,
        },
    }


def public_task(case:Mapping[str,Any])->dict[str,Any]:
    return {
        "schema":case["schema"],
        "behavior_id":case["behavior_id"],
        "seed":case["seed"],
        "public":case["public"],
    }


def probe(case:Mapping[str,Any],task:Mapping[str,Any],tool_id:str)->dict[str,Any]:
    tools={x["tool_id"]:x for x in case["public"]["tools"]}
    if tool_id not in tools:
        return {"ok":False,"reason":"UNKNOWN_TOOL"}
    if tools[tool_id].get("safe_probe") is not True:
        return {"ok":False,"reason":"UNSAFE_PROBE"}
    epoch=str(task["catalog_epoch"])
    result=bool(case["_oracle"]["epochs"][epoch][tool_id])
    return {
        "ok":True,
        "tool_id":tool_id,
        "capability":str(task["required_capability"]),
        "catalog_epoch":epoch,
        "capable":result,
    }


def run_candidate(case:Mapping[str,Any],candidate:Any)->dict[str,Any]:
    public=public_task(case)["public"]
    state=candidate.initial_state()
    records=[]
    for task_index,task in enumerate(public["tasks"]):
        probe_count=0
        for _ in range(len(public["tools"])+1):
            chosen=candidate.select_route(task,public["tools"],state)
            if chosen.get("status")=="SELECTED":
                tool_id=chosen.get("tool_id")
                records.append({"task_id":task["task_id"],"selected":tool_id,"probe_count":probe_count})
                break
            if chosen.get("status")!="NEED_PROBE":
                return {"pass":False,"reason":"CANDIDATE_PROTOCOL_INVALID","records":records}
            tool_id=chosen.get("tool_id")
            receipt=probe(case,task,tool_id)
            if not receipt.get("ok"):
                return {"pass":False,"reason":"INVALID_PROBE","records":records}
            state=candidate.observe_probe(state,receipt)
            probe_count+=1
        else:
            return {"pass":False,"reason":"NO_SELECTION","records":records}

        expected=case["_oracle"]["least_cost"][str(task["catalog_epoch"])]
        if records[-1]["selected"]!=expected:
            return {"pass":False,"reason":"NOT_LEAST_COST_VERIFIED_CAPABLE","records":records,"expected":expected}
        if task_index==1 and not case["_oracle"]["change_epoch"] and probe_count!=0:
            return {"pass":False,"reason":"LEARNED_CAPABILITY_DID_NOT_TRANSFER","records":records}
        if task_index==1 and case["_oracle"]["change_epoch"] and probe_count==0:
            return {"pass":False,"reason":"STALE_CAPABILITY_REUSED_ACROSS_EPOCH","records":records}

    return {"pass":True,"reason":"PASS","records":records}
