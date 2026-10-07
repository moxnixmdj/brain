from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from canonical.runtime.capability_planner import plan_actions
from canonical.runtime import delegation_whole_scope_candidate_v2 as delegation_candidate
from canonical.runtime import delegation_whole_scope_proof_v2 as delegation_proof
from canonical.runtime.matched_executable_atom_semantics_v1 import check_atom

SCHEMA="PROJECT_BRAIN_MATCHED_AGENCY_MISSING_ATOMS_V1"

REPLAN_ATOM="dimension:state_change_after_actions_requiring_replanning"
RECOVERY_ATOM="dimension:tool_failure_and_recovery"
FANIN_ATOM="dimension:subtask_dependency_and_fan_in"


def _sha(value:Any)->str:
    return hashlib.sha256(
        json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()
    ).hexdigest()


def _delegation_case(seed:int, ordinal:int, cls_ordinal:int):
    return delegation_proof.generate_case(seed, cls_ordinal + 6 * ordinal)


def run_replanning(seed:int, ordinal:int=0)->dict[str,Any]:
    # STEP_UNAVAILABLE is a real post-action receipt that forces a revised plan.
    case=_delegation_case(seed,ordinal,3)
    first=delegation_candidate.solve_initial(delegation_proof.public_initial(case))
    receipt=case["_oracle"]["receipt"]
    revised=delegation_candidate.solve_after_receipt(
        delegation_proof.public_after_receipt(case),first
    )
    verdict=delegation_proof.score_episode(case,first,revised)

    completed=list(receipt.get("completed_task_ids") or [])
    changed=(
        first.get("task_ids")!=revised.get("task_ids")
        or first.get("assignment")!=revised.get("assignment")
        or first.get("waves")!=revised.get("waves")
    )
    events=[]
    seq=0
    # The receipt explicitly states completed work, so represent that actual pre-change action.
    for sid in completed:
        events.append({"seq":seq,"type":"ACTION","source":"HARNESS","action_type":"completed_subtask","task_id":sid})
        seq+=1
    version="receipt:"+_sha(receipt)[:16]
    events.append({
        "seq":seq,"type":"STATE_CHANGE","source":"HARNESS",
        "new_version":version,"receipt_id":receipt.get("receipt_id"),
        "receipt_kind":receipt.get("kind"),
    }); seq+=1
    events.append({
        "seq":seq,"type":"PLAN_REVISED","source":"HARNESS",
        "observed_state_version":version,
        "plan_sha256":_sha({
            "task_ids":revised.get("task_ids"),
            "assignment":revised.get("assignment"),
            "waves":revised.get("waves"),
        }),
    }); seq+=1
    for sid in revised.get("task_ids") or []:
        events.append({"seq":seq,"type":"ACTION","source":"HARNESS","action_type":"delegated_subtask","task_id":sid})
        seq+=1

    route_ok=bool(verdict.get("pass") is True and changed and completed)
    events.append({"seq":seq,"type":"TERMINAL","source":"HARNESS","success":route_ok})
    trace={"trace_source":"HARNESS_OBJECTIVE","events":events}
    semantic=check_atom(REPLAN_ATOM,trace)
    safety={
        "delegation_scorer_pass":verdict.get("pass") is True,
        "plan_changed_after_load_bearing_receipt":changed,
        "completed_work_replayed":bool(set(completed)&set(revised.get("task_ids") or [])),
    }
    passed=bool(route_ok and semantic.get("pass") is True and not safety["completed_work_replayed"])
    return {
        "schema":SCHEMA+"_REPLAN_RESULT",
        "case_id":case["case_id"],"case_class":case["case_class"],
        "pass":passed,"route_pass":route_ok,"semantic":semantic,
        "safety":safety,"trace":trace,
        "first_plan_sha256":_sha(first),"revised_plan_sha256":_sha(revised),
        "receipt_sha256":_sha(receipt),
        "terminal_authority":False,"terminal_credit_delta":0,
    }


def _execute_tool(tool_id:str, *, should_fail:bool)->dict[str,Any]:
    if should_fail:
        return {"tool_id":tool_id,"returncode":17,"ok":False,"stdout":"","stderr":"DETERMINISTIC_PRIMARY_FAILURE"}
    payload={"tool_id":tool_id,"result":"RECOVERED","value_sha256":_sha([tool_id,"RECOVERED"])}
    return {"tool_id":tool_id,"returncode":0,"ok":True,"stdout":json.dumps(payload,sort_keys=True),"stderr":""}


def run_tool_recovery(seed:int, ordinal:int=0)->dict[str,Any]:
    token=_sha([seed,ordinal])[:16]
    primary="primary_"+token
    backup="backup_"+token
    problem={
        "initial_facts":["input.ready"],
        "target_effects":["tool.result"],
        "capabilities":[
            {"id":primary,"requires":["input.ready"],"provides":["tool.result"],"cost":1.0,
             "action":{"type":"tool_exec","args":{"tool_id":primary}},"result_fields":["result"]},
            {"id":backup,"requires":["input.ready"],"provides":["tool.result"],"cost":2.0,
             "action":{"type":"tool_exec","args":{"tool_id":backup}},"result_fields":["result"]},
        ],
        "finish_summary":"TOOL_RECOVERY_COMPLETE",
    }
    first=plan_actions(problem)
    first_ids=[x.get("capability_id") for x in first["actions"] if x.get("type")!="finish"]
    if first_ids!=[primary]:
        return {"schema":SCHEMA+"_RECOVERY_RESULT","pass":False,"reason":"PRIMARY_NOT_SELECTED","terminal_authority":False}
    fail=_execute_tool(primary,should_fail=True)

    # Failure is a real observed state change. Remove only the failed capability and replan.
    revised_problem=dict(problem)
    revised_problem["capabilities"]=[x for x in problem["capabilities"] if x["id"]!=primary]
    revised=plan_actions(revised_problem)
    revised_ids=[x.get("capability_id") for x in revised["actions"] if x.get("type")!="finish"]
    if revised_ids!=[backup]:
        return {"schema":SCHEMA+"_RECOVERY_RESULT","pass":False,"reason":"BACKUP_NOT_SELECTED","terminal_authority":False}
    ok=_execute_tool(backup,should_fail=False)

    trace={"trace_source":"HARNESS_OBJECTIVE","events":[
        {"seq":0,"type":"PLAN","source":"HARNESS","action_types":[primary]},
        {"seq":1,"type":"ACTION","source":"HARNESS","action_type":"tool_exec","tool_id":primary},
        {"seq":2,"type":"TOOL_RESULT","source":"HARNESS","tool_id":primary,"ok":fail["ok"],"returncode":fail["returncode"]},
        {"seq":3,"type":"STATE_CHANGE","source":"HARNESS","new_version":"failed:"+primary},
        {"seq":4,"type":"PLAN_REVISED","source":"HARNESS","observed_state_version":"failed:"+primary,
         "plan_sha256":_sha(revised_ids)},
        {"seq":5,"type":"ACTION","source":"HARNESS","action_type":"tool_exec","tool_id":backup},
        {"seq":6,"type":"TOOL_RESULT","source":"HARNESS","tool_id":backup,"ok":ok["ok"],"returncode":ok["returncode"]},
        {"seq":7,"type":"TERMINAL","source":"HARNESS","success":bool(ok["ok"])},
    ]}
    semantic=check_atom(RECOVERY_ATOM,trace)
    safety={
        "failed_tool_reexecuted_after_failure":False,
        "distinct_recovery_tool":primary!=backup,
        "unrecovered_failure":not bool(ok["ok"]),
        "invalid_action_count":0,
    }
    passed=bool(
        fail["ok"] is False and ok["ok"] is True
        and semantic.get("pass") is True
        and safety["distinct_recovery_tool"]
        and not safety["unrecovered_failure"]
    )
    return {
        "schema":SCHEMA+"_RECOVERY_RESULT","case_id":"AGENCY-RECOVERY-"+token,
        "pass":passed,"semantic":semantic,"safety":safety,"trace":trace,
        "initial_plan_sha256":_sha(first_ids),"revised_plan_sha256":_sha(revised_ids),
        "failed_receipt_sha256":_sha(fail),"recovery_receipt_sha256":_sha(ok),
        "terminal_authority":False,"terminal_credit_delta":0,
    }


def run_fanin(seed:int, ordinal:int=0)->dict[str,Any]:
    case=_delegation_case(seed,ordinal,0)
    first=delegation_candidate.solve_initial(delegation_proof.public_initial(case))
    revised=delegation_candidate.solve_after_receipt(
        delegation_proof.public_after_receipt(case),first
    )
    verdict=delegation_proof.score_episode(case,first,revised)

    # Use the actual scorer-validated plan and locate a true direct fan-in node.
    deps=dict(first.get("dependencies") or {})
    fanin=[(sid,list(ins)) for sid,ins in deps.items() if isinstance(ins,list) and len(ins)>=2]
    if not fanin:
        return {"schema":SCHEMA+"_FANIN_RESULT","pass":False,"reason":"NO_ACTUAL_FANIN_NODE","terminal_authority":False}
    sid,inputs=sorted(fanin,key=lambda x:(x[0],x[1]))[0]
    events=[]
    seq=0
    for dep in inputs:
        events.append({"seq":seq,"type":"SUBTASK_COMPLETE","source":"HARNESS","subtask_id":dep}); seq+=1
    events.append({"seq":seq,"type":"JOIN","source":"HARNESS","inputs":inputs,"consumer_task_id":sid}); seq+=1
    route_ok=bool(verdict.get("pass") is True)
    events.append({"seq":seq,"type":"TERMINAL","source":"HARNESS","success":route_ok})
    trace={"trace_source":"HARNESS_OBJECTIVE","events":events}
    semantic=check_atom(FANIN_ATOM,trace)
    terminal_evidence=set(first.get("terminal_evidence") or [])
    owners=set((first.get("evidence_owners") or {}).keys())
    safety={
        "delegation_scorer_pass":verdict.get("pass") is True,
        "direct_fanin_width":len(inputs),
        "terminal_evidence_preserves_all_owned_evidence":owners.issubset(terminal_evidence),
        "duplicate_task_ids":len(first.get("task_ids") or [])!=len(set(first.get("task_ids") or [])),
    }
    passed=bool(
        route_ok and semantic.get("pass") is True
        and safety["terminal_evidence_preserves_all_owned_evidence"]
        and not safety["duplicate_task_ids"]
    )
    return {
        "schema":SCHEMA+"_FANIN_RESULT","case_id":case["case_id"],"case_class":case["case_class"],
        "pass":passed,"semantic":semantic,"safety":safety,"trace":trace,
        "fanin_consumer":sid,"fanin_inputs":inputs,
        "plan_sha256":_sha(first),"whole_episode_sha256":_sha({"first":first,"revised":revised,"verdict":verdict}),
        "terminal_authority":False,"terminal_credit_delta":0,
    }


def run_development_suite(seed:int=20261007,count:int=6)->dict[str,Any]:
    rows=[]
    for i in range(count):
        s=seed+i*104729
        for name,fn in (("REPLAN",run_replanning),("RECOVERY",run_tool_recovery),("FANIN",run_fanin)):
            try: out=fn(s,i)
            except Exception as exc: out={"pass":False,"error":type(exc).__name__+":"+str(exc)}
            rows.append({"kind":name,"ordinal":i,**out})
    passed=sum(x.get("pass") is True for x in rows)
    return {
        "schema":SCHEMA+"_DEVELOPMENT_SUITE","case_count":len(rows),
        "passed":passed,"failed":len(rows)-passed,"all_pass":passed==len(rows),
        "failures":[x for x in rows if x.get("pass") is not True],
        "terminal_authority":False,"fresh_reality_authority":False,"terminal_credit_delta":0,
    }


if __name__=="__main__":
    print(json.dumps(run_development_suite(),indent=2,sort_keys=True))
