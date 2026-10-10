"""UVCK V2 shadow integration over the existing R2 fixed point.

This module is observational only. It does not replace the R2 front door, does
not mutate an R2 result, and cannot promote an R2 result to success. It simply
runs (or accepts an injected runner for testing) the existing fixed point and
computes the non-authoritative V2 assurance projection beside that result.

The production fixed-point import is deliberately lazy so this shadow adapter
can be tested independently from the large R2 dependency graph.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

from canonical.runtime import assurance_closure_compiler_v1 as assurance

SCHEMA="PROJECT_BRAIN_R2_ASSURANCE_SHADOW_V1"
DEFAULT_RUNNER="canonical.runtime.general_adequate_decision_fixed_point_v2.run"


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "r2_pass":False,
        "shadow_authority":False,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
        **extra,
    }


def _default_runner(request:Mapping[str,Any],**kwargs:Any)->Mapping[str,Any]:
    from canonical.runtime.general_adequate_decision_fixed_point_v2 import run
    return run(request,**kwargs)


def observe_result(result:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(result,Mapping):
        return _fail("R2_RESULT_NOT_OBJECT")
    r2=deepcopy(dict(result))
    projection=assurance.evaluate_controller_result(r2)
    return {
        "schema":SCHEMA,
        "status":(
            "SHADOW_OBSERVED_R2_PASS"
            if r2.get("pass") is True
            else "SHADOW_OBSERVED_R2_OPEN_OR_FAIL"
        ),
        "r2_pass":r2.get("pass") is True,
        "r2_status":r2.get("status"),
        "r2_result":r2,
        "assurance_result":projection,
        "assurance_status":projection.get("status"),
        "assurance_live_default":False,
        "shadow_authority":False,
        "semantic_truth_authority":False,
        "policy_adequacy_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


def run(
    request:Mapping[str,Any],
    *,
    fixed_point_runner:Callable[...,Mapping[str,Any]]|None=None,
    fixed_point_kwargs:Mapping[str,Any]|None=None,
)->dict[str,Any]:
    if not isinstance(request,Mapping):
        return _fail("REQUEST_NOT_OBJECT")
    if fixed_point_kwargs is not None and not isinstance(fixed_point_kwargs,Mapping):
        return _fail("FIXED_POINT_KWARGS_NOT_OBJECT")
    runner=fixed_point_runner or _default_runner
    try:
        result=runner(request,**dict(fixed_point_kwargs or {}))
    except Exception as exc:
        return _fail("R2_RUNNER_EXCEPTION:"+type(exc).__name__+":"+str(exc))
    return observe_result(result)
