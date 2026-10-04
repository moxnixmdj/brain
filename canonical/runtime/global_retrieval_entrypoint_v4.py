#!/usr/bin/env python3
"""Authorized scope-aware empirical global retrieval entrypoint V4."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import global_retrieval_authority_guard_v1 as guard
from canonical.runtime import global_retrieval_controller_v1 as state_base
from canonical.runtime import global_retrieval_controller_v4 as controller
from canonical.runtime import retrieval_route_strategy_calibration_v3 as first_cal
from canonical.runtime import retrieval_recovery_mechanism_calibration_v1 as recovery_cal

SCHEMA="PROJECT_BRAIN_GLOBAL_RETRIEVAL_ENTRYPOINT_V4"

def compile_authorized_plan(
    *,
    root:Path,
    query_actions:Sequence[Mapping[str,Any]],
    sources:Sequence[Mapping[str,Any]],
    state:Mapping[str,Any]|None=None,
    recovery_context:Mapping[str,Any]|None=None,
)->dict[str,Any]:
    gate=guard.evaluate_repository(root)
    if gate.get("pass") is not True:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED__GLOBAL_RETRIEVAL_AUTHORITY_INVALID",
            "authority_gate":gate,
            "plan":None,
            "execution_authority":False,
            "promotion_authority":False,
            "acceptance_credit_delta":0,
            "family_credit_delta":0,
            "capability_credit_delta":0,
            "ownership_credit_delta":0,
        }
    first=first_cal.calibrate_repository(root)
    recovery=recovery_cal.calibrate_repository(root)
    plan=controller.compile_global_plan(
        query_actions=query_actions,
        sources=sources,
        route_strategy_calibration=first,
        recovery_mechanism_calibration=recovery,
        state=state or state_base.new_state(),
        recovery_context=recovery_context or {},
    )
    return {
        "schema":SCHEMA,
        "status":"PASS__AUTHORIZED_SCOPE_AWARE_EMPIRICAL_GLOBAL_RETRIEVAL_PLAN_COMPILED",
        "authority_gate":gate,
        "first_pass_calibration":{
            "schema":first["schema"],
            "event_count":first["event_count"],
            "case_count":first["case_count"],
            "best_known_strategy_union":first["best_known_strategy_union"],
            "v11_stratified_events_included":first["v11_stratified_events_included"],
        },
        "recovery_mechanism_calibration":{
            "schema":recovery["schema"],
            "mechanism_count":recovery["mechanism_count"],
            "mechanisms":recovery["mechanisms"],
        },
        "plan":plan,
        "execution_authority":False,
        "promotion_authority":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "incremental_spend_usd":0,
        "hard_rules":[
            "FAIL_CLOSED_CURRENT_RETRIEVAL_AUTHORITY_GUARD_PRECEDES_PLAN_COMPILATION",
            "V10_PLUS_V11_FIRST_PASS_LIVE_EVENTS_CALIBRATE_PROVIDER_ROUTE_X_STRATEGY",
            "V12_TO_V18_RECOVERY_MECHANISMS_REMAIN_CONDITIONAL_AND_SCOPE_LOCKED",
            "FINITE_30_OF_30_LIVE_UNION_IS_REGRESSION_TRUTH_NOT_OPEN_WORLD_COMPLETENESS",
            "PLAN_ACTIONS_REMAIN_CANDIDATE_DISCOVERY_ONLY",
            "OPEN_WORLD_MISS_REMAINS_UNKNOWN",
        ],
    }

def main()->int:
    root=Path(__file__).resolve().parents[2]
    out=compile_authorized_plan(
        root=root,
        query_actions=[],
        sources=[],
        recovery_context={},
    )
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out.get("status","").startswith("PASS") else 1

if __name__=="__main__":
    raise SystemExit(main())
