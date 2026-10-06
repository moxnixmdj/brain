from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from canonical.runtime.capability_planner import plan_actions
from canonical.runtime import composition_state_capsule_guard_v2 as guard

SCHEMA="PROJECT_BRAIN_MATCHED_CROSS_CAPABILITY_HANDOFF_ROLLBACK_DIRECT_V1"

def _sha(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def _problem(seed:int)->dict[str,Any]:
    token=_sha({"seed":seed})[:16]
    return {
        "initial_facts":["input.ready"],
        "target_effects":["analysis.complete"],
        "capabilities":[
            {
                "id":"capability_a",
                "requires":["input.ready"],
                "provides":["handoff.state"],
                "cost":1.0,
                "action":{"type":"produce_state","args":{"seed_token":token}},
                "result_fields":["state_token"],
            },
            {
                "id":"capability_b",
                "requires":["handoff.state"],
                "provides":["analysis.complete"],
                "cost":1.0,
                "action":{
                    "type":"consume_state",
                    "args":{"state_token":{"$effect_result":{"effect":"handoff.state","field":"state_token"}}},
                },
                "result_fields":["accepted_state_token"],
            },
        ],
        "finish_summary":"HANDOFF_ROLLBACK_CASE_COMPLETE",
    }

def execute_case(seed:int)->dict[str,Any]:
    planned=plan_actions(_problem(seed))
    actions=planned["actions"]
    contract=planned["composition_contract"]
    initial=planned["planning"]["initial_facts"]
    validated=guard.validate_plan(actions,contract,initial)
    capsule=guard.seed_capsule(initial)

    row_a=contract[0]
    action_a=guard.resolve_action_from_capsule(capsule,row_a,actions[0])
    result_a={"state_token":action_a["args"]["seed_token"]}
    capsule_a=guard.append_action_result(capsule,row_a,action_a,result_a)
    checkpoint_id=capsule_a["head_hash"]

    row_b=contract[1]
    action_b=guard.resolve_action_from_capsule(capsule_a,row_b,actions[1])
    handoff_ok=action_b["args"]["state_token"]==result_a["state_token"]
    result_b={"accepted_state_token":action_b["args"]["state_token"]}
    capsule_b=guard.append_action_result(capsule_a,row_b,action_b,result_b)

    trace=[
        {
            "cycle":0,
            "plan":action_a,
            "result":result_a,
            "composition_capsule_head_hash":capsule_a["head_hash"],
        },
        {
            "cycle":1,
            "plan":action_b,
            "result":result_b,
            "composition_capsule_head_hash":capsule_b["head_hash"],
        },
    ]
    valid=guard.rebuild_valid_prefix(actions,contract,initial,trace)

    tampered=copy.deepcopy(trace)
    tampered[1]["result"]["accepted_state_token"]="TAMPERED-"+result_b["accepted_state_token"]
    rebuilt=guard.rebuild_valid_prefix(actions,contract,initial,tampered)
    restored=rebuilt["capsule"]
    restored_ok=(
        rebuilt["valid_count"]==1
        and restored["head_hash"]==checkpoint_id
        and guard.verify_capsule(restored).get("status")=="PASS"
    )
    failure_reason=str(rebuilt.get("reason") or "")
    tamper_detected=bool(failure_reason)

    passed=(
        validated.get("status")=="PASS"
        and valid["valid_count"]==2
        and handoff_ok
        and tamper_detected
        and restored_ok
    )

    trace_events={
        "trace_source":"HARNESS_OBJECTIVE",
        "events":[
            {
                "seq":0,"type":"CHECKPOINT","source":"HARNESS",
                "checkpoint_id":checkpoint_id,
                "capability":"capability_a",
            },
            {
                "seq":1,"type":"HANDOFF","source":"HARNESS",
                "from_capability":"capability_a",
                "to_capability":"capability_b",
                "state_token_sha256":_sha(result_a["state_token"]),
                "capsule_head_hash":checkpoint_id,
            },
            {
                "seq":2,"type":"FAILURE","source":"HARNESS",
                "capability":"capability_b",
                "reason":failure_reason,
            },
            {
                "seq":3,"type":"ROLLBACK","source":"HARNESS",
                "checkpoint_id":checkpoint_id,
                "valid_prefix_count":rebuilt["valid_count"],
            },
            {
                "seq":4,"type":"STATE_RESTORED","source":"HARNESS",
                "checkpoint_id":restored["head_hash"],
                "capsule_status":guard.verify_capsule(restored).get("status"),
            },
            {"seq":5,"type":"TERMINAL","source":"HARNESS","success":passed},
        ],
    }
    return {
        "schema":SCHEMA+"_RESULT",
        "seed":seed,
        "pass":passed,
        "planner_plan":planned["planning"]["plan"],
        "handoff_ok":handoff_ok,
        "full_prefix_valid_count":valid["valid_count"],
        "tampered_prefix_valid_count":rebuilt["valid_count"],
        "tamper_detected":tamper_detected,
        "restored_to_checkpoint":restored_ok,
        "checkpoint_id":checkpoint_id,
        "failure_reason":failure_reason,
        "objective_trace":trace_events,
        "terminal_authority":False,
        "fresh_reality_authority":False,
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }

def run_batch(seed:int,count:int=16)->dict[str,Any]:
    rows=[]
    for i in range(count):
        try: rows.append(execute_case(seed+i*8191))
        except Exception as exc:
            rows.append({"seed":seed+i*8191,"pass":False,"error":type(exc).__name__+":"+str(exc)})
    passed=sum(int(x.get("pass") is True) for x in rows)
    return {
        "schema":SCHEMA+"_BATCH_RESULT",
        "case_count":count,
        "passed":passed,
        "failed":count-passed,
        "all_pass":passed==count,
        "failures":[x for x in rows if x.get("pass") is not True][:20],
        "terminal_authority":False,
        "fresh_reality_authority":False,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(run_batch(20261007,16),indent=2,sort_keys=True))
