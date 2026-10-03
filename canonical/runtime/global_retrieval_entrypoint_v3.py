#!/usr/bin/env python3
"""Authorized route-strategy empirical retrieval entrypoint V3."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import global_retrieval_authority_guard_v1 as guard
from canonical.runtime import global_retrieval_controller_v1 as state_base
from canonical.runtime import global_retrieval_controller_v3 as controller
from canonical.runtime import retrieval_route_strategy_calibration_v2 as calibration

SCHEMA="PROJECT_BRAIN_GLOBAL_RETRIEVAL_ENTRYPOINT_V3"

def compile_authorized_plan(
    *,
    root:Path,
    query_actions:Sequence[Mapping[str,Any]],
    sources:Sequence[Mapping[str,Any]],
    state:Mapping[str,Any]|None=None,
)->dict[str,Any]:
    gate=guard.evaluate_repository(root)
    if gate.get("pass") is not True:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED__GLOBAL_RETRIEVAL_AUTHORITY_INVALID",
            "authority_gate":gate,"plan":None,
            "execution_authority":False,"promotion_authority":False,
            "acceptance_credit_delta":0,"family_credit_delta":0,
            "capability_credit_delta":0,"ownership_credit_delta":0,
        }
    calibrated=calibration.calibrate_repository(root)
    plan=controller.compile_global_plan(
        query_actions=query_actions,
        sources=sources,
        route_strategy_calibration=calibrated,
        state=state or state_base.new_state(),
    )
    return {
        "schema":SCHEMA,
        "status":"PASS__AUTHORIZED_ROUTE_STRATEGY_EMPIRICAL_GLOBAL_RETRIEVAL_PLAN_COMPILED",
        "authority_gate":gate,
        "route_strategy_calibration":{
            "event_count":calibrated["event_count"],
            "case_count":calibrated["case_count"],
            "route_strategy_stats":calibrated["route_strategy_stats"],
            "directional_conditional_recovery":calibrated["directional_conditional_recovery"],
            "best_known_strategy_union":calibrated["best_known_strategy_union"],
        },
        "plan":plan,
        "execution_authority":False,"promotion_authority":False,
        "acceptance_credit_delta":0,"family_credit_delta":0,
        "capability_credit_delta":0,"ownership_credit_delta":0,
        "incremental_spend_usd":0,
        "hard_rules":[
            "FAIL_CLOSED_AUTHORITY_GUARD_PRECEDES_PLAN_COMPILATION",
            "PROVIDER_ONLY_PERFORMANCE_CALIBRATION_IS_FORBIDDEN",
            "LIVE_PROVIDER_ROUTE_X_STRATEGY_EVIDENCE_CALIBRATES_ROUTING",
            "FINITE_HIDDEN_WITNESS_AND_LIVE_LABELED_ARENAS_DO_NOT_PROVE_OPEN_WORLD_COMPLETENESS",
            "PLAN_ACTIONS_REMAIN_CANDIDATE_DISCOVERY_ONLY",
            "OPEN_WORLD_MISS_REMAINS_UNKNOWN",
        ],
    }

def main()->int:
    root=Path(__file__).resolve().parents[2]
    out=compile_authorized_plan(root=root,query_actions=[],sources=[])
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out.get("status","").startswith("PASS") else 1

if __name__=="__main__":
    raise SystemExit(main())
