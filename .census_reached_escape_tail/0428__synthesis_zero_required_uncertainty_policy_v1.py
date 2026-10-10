from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import synthesis_certified_visible_support_policy_v2 as v2

SCHEMA="PROJECT_BRAIN_SYNTHESIS_ZERO_REQUIRED_UNCERTAINTY_POLICY_V1"
INPUT_SCHEMA="PROJECT_BRAIN_SYNTHESIS_ZERO_REQUIRED_UNCERTAINTY_INPUT_V1"


def _fail(reason:str)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "terminal_authority":False,
        "promotion_authority":False,
        "terminal_credit_delta":0,
    }


def solve(public:Any)->dict[str,Any]:
    if not isinstance(public,Mapping) or public.get("schema")!=INPUT_SCHEMA:
        return _fail("INPUT_SCHEMA_INVALID")
    task=public.get("task")
    if not isinstance(task,Mapping):
        return _fail("TASK_INVALID")
    units=task.get("required_uncertainty_or_disagreement_units")
    if units != []:
        return _fail("ZERO_REQUIRED_UNCERTAINTY_NOT_CERTIFIED")
    delegated=dict(public)
    delegated["schema"]=v2.INPUT_SCHEMA
    out=v2.solve(delegated)
    if out.get("status")!="PASS":
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "reason":"V2_BASE_POLICY_NOT_CERTIFIED",
            "base":out,
            "terminal_authority":False,
            "promotion_authority":False,
            "terminal_credit_delta":0,
        }
    return {
        "schema":SCHEMA,
        "status":"PASS",
        "base":out,
        "matched_quality_projection":{
            "required_uncertainty_or_disagreement_units_total":0,
            "uncertainty_and_disagreement_preservation":1,
            "other_v2_top_law_coordinates_required":True,
        },
        "terminal_authority":False,
        "promotion_authority":False,
        "terminal_credit_delta":0,
    }


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return solve(args or {})
