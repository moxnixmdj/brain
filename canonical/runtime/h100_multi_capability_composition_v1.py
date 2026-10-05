"""Frozen multi-capability composition experiment for H100."""
from __future__ import annotations
import json, statistics, time
from pathlib import Path
from typing import Any

from canonical.runtime import h100_verified_capability_registry_v1 as registry
from canonical.runtime import h100_zero_learned_transfer_v1 as transfer

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_MULTI_CAPABILITY_COMPOSITION_PRECOMMIT_V1.json"
TRANSFER_PRE=ROOT/"canonical/governance/H100_ZERO_LEARNED_TRANSFER_PREEXPOSURE_V1.json"
SCHEMA="PROJECT_BRAIN_H100_MULTI_CAPABILITY_COMPOSITION_RESULT_V1"

class CompositionError(ValueError): pass

def _truth(task_id:str,x:float)->float:
    if task_id=="CUBIC_CONTROL":
        return x**3+0.123*x
    return transfer._truth(task_id,x)

def _wrap(rows:list[dict[str,float]],fmt:str):
    if fmt=="JSON_ROWS_REQUEST_RESPONSE":
        return "JSON_ROWS",[{"request":{"x":r["x"]},"response":{"y":r["y"]}} for r in rows]
    if fmt=="JSON_ROWS_PARAMS_OUTPUT":
        return "JSON_ROWS",[{"params":{"x":r["x"]},"output":{"y":r["y"]}} for r in rows]
    if fmt=="EVENT_STREAM":
        out=[]
        for i,r in enumerate(rows):
            cid=f"c{i}"
            out.append({"call_id":cid,"event":"request","data":{"x":r["x"]}})
            out.append({"call_id":cid,"event":"response","data":{"y":r["y"]}})
        return "EVENT_STREAM",out
    raise CompositionError("TRACE_FORMAT_UNKNOWN")

def execute_task(task:dict[str,Any],tpre:dict[str,Any])->dict[str,Any]:
    # Stage 1: language -> declared schema.
    lang=registry.invoke("CAP_COMPOSITIONAL_LANGUAGE_V1",{"text":task["schema_text"]})
    lres=lang["result"]
    if lres.get("status")!="ROLES_IDENTIFIED" or lres.get("inputs")!=["x"] or lres.get("target")!="y":
        raise CompositionError("LANGUAGE_STAGE_FAILED:"+task["id"])

    train=[{"x":float(x),"y":_truth(task["truth_task_id"],float(x))} for x in tpre["training_x"]]
    fmt,payload=_wrap(train,task["trace_format"])

    # Stage 2: tool trace -> typed rows.
    tr=registry.invoke("CAP_TOOL_TRACE_NORMALIZER_V1",{
        "payload":payload,"inputs":lres["inputs"],"target":lres["target"],"format_hint":fmt
    })
    tres=tr["result"]
    if tres.get("status")!="TYPED_NUMERIC_SCHEMA_COMPILED":
        raise CompositionError("TRACE_STAGE_FAILED:"+task["id"])
    rows=tres["rows"]

    # Stage 3: verified structural family lookup.
    resolution=registry.resolve_verified_capability(rows,target="y",input_name="x")
    expected=task["expected_capability_id"]
    if expected is None:
        ok=resolution.get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED"
        return {
            "task_id":task["id"],
            "status":"LIBRARY_MISS__RAW_SYNTHESIS_REQUIRED" if ok else "FAIL__NEGATIVE_CONTROL_FALSE_HIT",
            "language_capability_id":"CAP_COMPOSITIONAL_LANGUAGE_V1",
            "trace_capability_id":"CAP_TOOL_TRACE_NORMALIZER_V1",
            "resolved_capability_id":None if resolution.get("match") is None else resolution["match"].get("capability_id"),
            "raw_synthesis_attempts_executed":0,
            "raw_synthesis_required":ok,
            "holdout_nrmse":None,
            "pass":ok,
        }

    if resolution.get("status")!="LIBRARY_HIT__VERIFY_BEFORE_USE":
        return {"task_id":task["id"],"status":"FAIL__EXPECTED_LIBRARY_HIT_MISSING","pass":False}
    got=resolution["match"]["capability_id"]
    if got!=expected:
        return {"task_id":task["id"],"status":"FAIL__WRONG_LIBRARY_CAPABILITY","resolved_capability_id":got,"pass":False}

    hold=[{"x":float(x),"y":_truth(task["truth_task_id"],float(x))} for x in tpre["holdout_x"]]
    preds=[registry.predict(resolution,{"x":r["x"]}) for r in hold]
    err=transfer._nrmse([r["y"] for r in hold],preds)
    ok=err<=float(json.loads(PRE.read_text())["data_contract"]["positive_holdout_nrmse_max"])
    return {
        "task_id":task["id"],
        "status":"COMPOSED_VERIFIED_CAPABILITY" if ok else "FAIL__COMPOSED_CAPABILITY_VERIFICATION",
        "language_capability_id":"CAP_COMPOSITIONAL_LANGUAGE_V1",
        "trace_capability_id":"CAP_TOOL_TRACE_NORMALIZER_V1",
        "resolved_capability_id":got,
        "raw_synthesis_attempts_before_hit":resolution["raw_synthesis_attempts_before_hit"],
        "raw_synthesis_attempts_executed":0,
        "holdout_nrmse":err,
        "pass":ok,
    }

def _timed(task,tpre,repetitions=7):
    warm=execute_task(task,tpre)
    if not warm["pass"]: raise CompositionError("WARMUP_FAIL:"+task["id"])
    vals=[]; last=None
    for _ in range(repetitions):
        start=time.perf_counter(); last=execute_task(task,tpre); vals.append(time.perf_counter()-start)
        if not last["pass"]: raise CompositionError("TIMED_FAIL:"+task["id"])
    out=dict(last)
    out["median_end_to_end_seconds"]=statistics.median(vals)
    out["min_end_to_end_seconds"]=min(vals)
    out["max_end_to_end_seconds"]=max(vals)
    out["repetitions"]=repetitions
    return out

def run()->dict[str,Any]:
    pre=json.loads(PRE.read_text())
    if pre.get("status")!="FROZEN_BEFORE_COMPOSITION_RUNTIME_AND_OUTCOMES__ZERO_CREDIT":
        raise CompositionError("PRECOMMIT_NOT_FROZEN")
    tpre=json.loads(TRANSFER_PRE.read_text())
    rows=[_timed(dict(task),tpre) for task in pre["tasks"]]
    positives=[x for x in rows if x["task_id"]!="COMP_CUBIC_NEGATIVE_CONTROL"]
    negative=[x for x in rows if x["task_id"]=="COMP_CUBIC_NEGATIVE_CONTROL"][0]
    all_pass=all(x["pass"] for x in rows)
    return {
        "schema":SCHEMA,
        "status":"MULTI_CAPABILITY_COMPOSITION_PASS__3_POSITIVE_PLUS_1_FAIL_CLOSED_CONTROL__ZERO_CREDIT" if all_pass else "MULTI_CAPABILITY_COMPOSITION_RESIDUAL",
        "composition_plan_bits":pre["composition_plan"]["total_plan_bits"],
        "positive_tasks_passed":sum(x["pass"] for x in positives),
        "positive_tasks_total":len(positives),
        "negative_control_fail_closed":negative["pass"],
        "tasks":rows,
        "summary":{
            "positive_median_end_to_end_seconds":statistics.median(x["median_end_to_end_seconds"] for x in positives),
            "positive_max_end_to_end_seconds":max(x["median_end_to_end_seconds"] for x in positives),
            "raw_synthesis_attempts_executed":sum(int(x.get("raw_synthesis_attempts_executed",0)) for x in rows),
        },
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "EXPLICIT_PREDECLARED_COMPOSITION_SEQUENCE_NOT_AUTONOMOUS_PLANNING",
            "FOUR_SYNTHETIC_TASKS_DO_NOT_PROVE_OPEN_WORLD_COMPOSITION",
            "NO_RAW_SYNTHESIS_PERFORMED",
            "NO_H100_TERMINAL_CREDIT"
        ],
        "h100_terminal_credit_delta":0
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
