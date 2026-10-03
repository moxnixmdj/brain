"""Fail-closed P1 shared-batch normalizer V1.

This module performs no causal inference. It validates and canonicalizes the exact
candidate-visible fields for the one shared P1 failure-semantics batch. The load-
bearing DIRECT_CONTRACT versus DERIVED_UPSTREAM label must already be supplied by
source-bound normalization/instrumentation. Missing labels never default to direct.
"""
from __future__ import annotations
import copy
from typing import Any, Mapping

ALLOWED_FAILURE_SEMANTICS={"DIRECT_CONTRACT","DERIVED_UPSTREAM"}

def normalize(raw: Mapping[str,Any]) -> dict[str,Any]:
    if not isinstance(raw,Mapping):
        return {"status":"FAIL_CLOSED","reason":"RAW_NOT_MAPPING"}
    surface_id=raw.get("surface_id")
    task=raw.get("task")
    if not isinstance(surface_id,str) or not surface_id:
        return {"status":"FAIL_CLOSED","reason":"SURFACE_ID_MISSING"}
    if not isinstance(task,Mapping):
        return {"status":"FAIL_CLOSED","reason":"TASK_INVALID"}
    rows=task.get("trajectory")
    failed_resources=task.get("terminal_failed_resources")
    goal=task.get("goal")
    if not isinstance(rows,list) or not rows:
        return {"status":"FAIL_CLOSED","reason":"TRAJECTORY_INVALID"}
    if not isinstance(failed_resources,list) or not failed_resources or any(not isinstance(x,str) or not x for x in failed_resources):
        return {"status":"FAIL_CLOSED","reason":"TERMINAL_FAILED_RESOURCES_INVALID"}
    if not isinstance(goal,str) or not goal:
        return {"status":"FAIL_CLOSED","reason":"GOAL_INVALID"}

    out_rows=[]
    direct=0
    derived=0
    for row in rows:
        if not isinstance(row,Mapping):
            return {"status":"FAIL_CLOSED","reason":"ROW_INVALID"}
        required=("action_id","reads","writes","depends_on","checks")
        if any(k not in row for k in required):
            return {"status":"FAIL_CLOSED","reason":"ROW_FIELD_MISSING"}
        aid=row.get("action_id")
        if not isinstance(aid,str) or not aid:
            return {"status":"FAIL_CLOSED","reason":"ACTION_ID_INVALID"}
        for field in ("reads","writes","depends_on"):
            value=row.get(field)
            if not isinstance(value,list) or any(not isinstance(x,str) or not x for x in value):
                return {"status":"FAIL_CLOSED","reason":field.upper()+"_INVALID"}
        comp=row.get("dependency_composition","SEQUENTIAL")
        if comp not in {"SEQUENTIAL","CONJUNCTIVE","ALTERNATIVE"}:
            return {"status":"FAIL_CLOSED","reason":"DEPENDENCY_COMPOSITION_INVALID"}
        checks=row.get("checks")
        if not isinstance(checks,list):
            return {"status":"FAIL_CLOSED","reason":"CHECKS_INVALID"}
        out_checks=[]
        for check in checks:
            if not isinstance(check,Mapping):
                return {"status":"FAIL_CLOSED","reason":"CHECK_INVALID"}
            if not isinstance(check.get("id"),str) or not check.get("id"):
                return {"status":"FAIL_CLOSED","reason":"CHECK_ID_INVALID"}
            if not isinstance(check.get("kind"),str) or not check.get("kind"):
                return {"status":"FAIL_CLOSED","reason":"CHECK_KIND_INVALID"}
            if type(check.get("pass")) is not bool:
                return {"status":"FAIL_CLOSED","reason":"CHECK_PASS_INVALID"}
            evidence=check.get("evidence")
            if not isinstance(evidence,list) or any(not isinstance(x,str) or not x for x in evidence):
                return {"status":"FAIL_CLOSED","reason":"CHECK_EVIDENCE_INVALID"}
            item={
                "kind":check["kind"],
                "id":check["id"],
                "pass":check["pass"],
                "evidence":list(evidence),
            }
            if check["pass"] is False:
                if "failure_semantics" not in check:
                    return {"status":"FAIL_CLOSED","reason":"FAILED_CHECK_FAILURE_SEMANTICS_MISSING"}
                semantics=check.get("failure_semantics")
                if semantics not in ALLOWED_FAILURE_SEMANTICS:
                    return {"status":"FAIL_CLOSED","reason":"FAILED_CHECK_FAILURE_SEMANTICS_INVALID"}
                if not evidence:
                    return {"status":"FAIL_CLOSED","reason":"FAILED_CHECK_CAUSAL_RECEIPT_MISSING"}
                item["failure_semantics"]=semantics
                if semantics=="DIRECT_CONTRACT":
                    direct+=1
                else:
                    derived+=1
            elif "failure_semantics" in check:
                semantics=check.get("failure_semantics")
                if semantics not in ALLOWED_FAILURE_SEMANTICS:
                    return {"status":"FAIL_CLOSED","reason":"PASSING_CHECK_FAILURE_SEMANTICS_INVALID"}
                item["failure_semantics"]=semantics
            out_checks.append(item)
        out_rows.append({
            "action_id":aid,
            "reads":list(row["reads"]),
            "writes":list(row["writes"]),
            "depends_on":list(row["depends_on"]),
            "dependency_composition":comp,
            "checks":out_checks,
        })
    return {
        "status":"PASS",
        "surface_id":surface_id,
        "task":{
            "trajectory":out_rows,
            "terminal_failed_resources":list(failed_resources),
            "goal":goal,
        },
        "direct_failed_check_count":direct,
        "derived_failed_check_count":derived,
    }
