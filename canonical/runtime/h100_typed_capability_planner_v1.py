"""Deterministic typed-capability planner for H100.

Plans over monotonic resource contracts only. Task values, task IDs, formulas,
and expected capability IDs are not inputs to the planner.
"""
from __future__ import annotations

import json
import statistics
import time
from collections import deque
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import h100_verified_capability_registry_v1 as registry
from canonical.runtime import h100_multi_capability_composition_v1 as composition
from canonical.runtime import h100_zero_learned_transfer_v1 as transfer

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_TYPED_CAPABILITY_PLANNER_PRECOMMIT_V1.json"
COMP_PRE=ROOT/"canonical/governance/H100_MULTI_CAPABILITY_COMPOSITION_PRECOMMIT_V1.json"
TRANSFER_PRE=ROOT/"canonical/governance/H100_ZERO_LEARNED_TRANSFER_PREEXPOSURE_V1.json"
SCHEMA="PROJECT_BRAIN_H100_TYPED_CAPABILITY_PLANNER_RESULT_V1"

class PlannerError(ValueError): pass

def _spec():
    d=json.loads(PRE.read_text())
    if d.get("status")!="FROZEN_BEFORE_PLANNER_IMPLEMENTATION_AND_OUTCOMES__RETROSPECTIVE_EXECUTION_ON_PRIOR_FROZEN_COMPOSITION_TASKS__ZERO_CREDIT":
        raise PlannerError("PRECOMMIT_NOT_FROZEN")
    return d

def derive_plan(initial_resources:list[str]|tuple[str,...],goal_resource:str)->dict[str,Any]:
    spec=_spec()
    initial=frozenset(str(x) for x in initial_resources)
    goal=str(goal_resource)
    ops=sorted(spec["operators"],key=lambda x:str(x["operator_id"]))
    max_len=int(spec["planning_algorithm"]["maximum_plan_length"])
    q=deque([(initial,tuple())])
    seen={initial}
    expanded=0
    while q:
        resources,path=q.popleft()
        expanded+=1
        if goal in resources:
            return {
                "status":"PLAN_FOUND",
                "plan":list(path),
                "plan_length":len(path),
                "expanded_states":expanded,
                "final_resources":sorted(resources),
            }
        if len(path)>=max_len:
            continue
        for op in ops:
            oid=str(op["operator_id"])
            if oid in path:
                continue
            requires=set(map(str,op["requires"]))
            provides=set(map(str,op["provides"]))
            if not requires.issubset(resources):
                continue
            new=frozenset(set(resources)|provides)
            if new==resources or new in seen:
                continue
            seen.add(new)
            q.append((new,path+(oid,)))
    return {
        "status":"NO_PLAN",
        "plan":None,
        "plan_length":None,
        "expanded_states":expanded,
        "final_resources":None,
    }

def _operator_map()->dict[str,dict[str,Any]]:
    return {str(x["operator_id"]):dict(x) for x in _spec()["operators"]}

def execute_derived_plan(task:Mapping[str,Any],tpre:Mapping[str,Any],plan:list[str])->dict[str,Any]:
    train=[{"x":float(x),"y":composition._truth(str(task["truth_task_id"]),float(x))} for x in tpre["training_x"]]
    fmt,payload=composition._wrap(train,str(task["trace_format"]))
    ctx:dict[str,Any]={
        "SCHEMA_TEXT":str(task["schema_text"]),
        "RAW_TOOL_TRACE":{"format_hint":fmt,"payload":payload},
    }
    opmap=_operator_map()
    executed=[]
    for oid in plan:
        if oid not in opmap:
            raise PlannerError("PLAN_OPERATOR_UNKNOWN:"+oid)
        if oid=="OP_COMPOSITIONAL_LANGUAGE":
            out=registry.invoke("CAP_COMPOSITIONAL_LANGUAGE_V1",{"text":ctx["SCHEMA_TEXT"]})
            res=out["result"]
            if res.get("status")!="ROLES_IDENTIFIED":
                raise PlannerError("LANGUAGE_EXECUTION_FAILED")
            ctx["DECLARED_SCHEMA"]={"inputs":res["inputs"],"target":res["target"]}
        elif oid=="OP_TOOL_TRACE_NORMALIZER":
            schema=ctx["DECLARED_SCHEMA"]; raw=ctx["RAW_TOOL_TRACE"]
            out=registry.invoke("CAP_TOOL_TRACE_NORMALIZER_V1",{
                "payload":raw["payload"],"inputs":schema["inputs"],"target":schema["target"],"format_hint":raw["format_hint"]
            })
            res=out["result"]
            if res.get("status")!="TYPED_NUMERIC_SCHEMA_COMPILED":
                raise PlannerError("TRACE_EXECUTION_FAILED")
            ctx["TYPED_NUMERIC_ROWS"]=res["rows"]
        elif oid=="OP_PARAMETRIC_REGISTRY_RESOLVER":
            ctx["PREDICTOR_RESOLUTION"]=registry.resolve_verified_capability(
                ctx["TYPED_NUMERIC_ROWS"],target="y",input_name="x"
            )
        elif oid in {"OP_OEWN_LEXICAL","OP_LEXICAL_SOURCE_FALLBACK"}:
            raise PlannerError("UNSATISFIED_DECOY_OPERATOR_SHOULD_NOT_EXECUTE")
        else:
            raise PlannerError("EXECUTOR_OPERATOR_UNSUPPORTED:"+oid)
        executed.append(oid)

    if "PREDICTOR_RESOLUTION" not in ctx:
        raise PlannerError("PLAN_DID_NOT_PRODUCE_GOAL")

    resolution=ctx["PREDICTOR_RESOLUTION"]
    expected=task.get("expected_capability_id")
    if expected is None:
        ok=resolution.get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED"
        return {
            "task_id":task["id"],"pass":ok,
            "status":"LIBRARY_MISS__RAW_SYNTHESIS_REQUIRED" if ok else "FAIL__NEGATIVE_CONTROL_FALSE_HIT",
            "executed_plan":executed,
            "resolved_capability_id":None if resolution.get("match") is None else resolution["match"].get("capability_id"),
            "holdout_nrmse":None,
            "raw_synthesis_attempts_executed":0,
        }

    if resolution.get("status")!="LIBRARY_HIT__VERIFY_BEFORE_USE":
        return {"task_id":task["id"],"pass":False,"status":"FAIL__EXPECTED_HIT_MISSING","executed_plan":executed}
    got=resolution["match"]["capability_id"]
    hold=[{"x":float(x),"y":composition._truth(str(task["truth_task_id"]),float(x))} for x in tpre["holdout_x"]]
    preds=[registry.predict(resolution,{"x":r["x"]}) for r in hold]
    err=transfer._nrmse([r["y"] for r in hold],preds)
    ok=(got==expected and err<=1e-7)
    return {
        "task_id":task["id"],"pass":ok,
        "status":"AUTONOMOUS_TYPED_PLAN_COMPOSED_VERIFIED_CAPABILITY" if ok else "FAIL__COMPOSED_VERIFICATION",
        "executed_plan":executed,
        "resolved_capability_id":got,
        "holdout_nrmse":err,
        "raw_synthesis_attempts_executed":0,
    }

def _planning_timing(repetitions:int=1000)->dict[str,float]:
    spec=_spec()
    def once():
        return derive_plan(spec["initial_resources"],spec["goal_resource"])
    warm=once()
    if warm["status"]!="PLAN_FOUND": raise PlannerError("WARMUP_PLAN_FAILED")
    vals=[]
    last=None
    for _ in range(repetitions):
        st=time.perf_counter(); last=once(); vals.append(time.perf_counter()-st)
        if last["status"]!="PLAN_FOUND": raise PlannerError("TIMED_PLAN_FAILED")
    return {
        "median_seconds":statistics.median(vals),
        "min_seconds":min(vals),
        "max_seconds":max(vals),
        "repetitions":repetitions,
        "plan":last["plan"],
        "plan_length":last["plan_length"],
        "expanded_states":last["expanded_states"],
    }

def run()->dict[str,Any]:
    spec=_spec()
    plan=derive_plan(spec["initial_resources"],spec["goal_resource"])
    if plan["status"]!="PLAN_FOUND": raise PlannerError("NO_FROZEN_PLAN")
    timing=_planning_timing(1000)
    comp=json.loads(COMP_PRE.read_text())
    tpre=json.loads(TRANSFER_PRE.read_text())
    rows=[execute_derived_plan(dict(task),tpre,list(plan["plan"])) for task in comp["tasks"]]
    positives=[x for x in rows if x["task_id"]!="COMP_CUBIC_NEGATIVE_CONTROL"]
    negative=[x for x in rows if x["task_id"]=="COMP_CUBIC_NEGATIVE_CONTROL"][0]
    all_pass=all(x["pass"] for x in rows)
    return {
        "schema":SCHEMA,
        "status":"AUTONOMOUS_TYPED_CAPABILITY_PLAN_PASS__ZERO_CREDIT" if all_pass else "AUTONOMOUS_TYPED_PLAN_RESIDUAL",
        "derived_plan":plan,
        "planning_timing":timing,
        "positive_tasks_passed":sum(x["pass"] for x in positives),
        "positive_tasks_total":len(positives),
        "negative_control_fail_closed":negative["pass"],
        "task_results":rows,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "TYPED_MONOTONIC_RESOURCE_PLANNING_IS_NOT_OPEN_WORLD_SEMANTIC_PLANNING",
            "RETROSPECTIVE_EXECUTION_REUSES_PRIOR_COMPOSITION_TASKS",
            "NO_SIDE_EFFECT_OR_IRREVERSIBLE_ACTION_PLANNING",
            "NO_H100_TERMINAL_CREDIT"
        ],
        "h100_terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
