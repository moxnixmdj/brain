#!/usr/bin/env python3
"""Authorized global retrieval entrypoint V4 with verified recovery portfolio."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import global_retrieval_authority_guard_v1 as guard
from canonical.runtime import global_retrieval_controller_v1 as state_base
from canonical.runtime import global_retrieval_controller_v3 as controller
from canonical.runtime import retrieval_route_strategy_calibration_v2 as calibration
from canonical.runtime import retrieval_verified_route_portfolio_v1 as portfolio

SCHEMA="PROJECT_BRAIN_GLOBAL_RETRIEVAL_ENTRYPOINT_V4"

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
    route_portfolio=portfolio.compile_portfolio(query_actions,sources)
    combined=[dict(x) for x in query_actions]+[
        dict(x) for x in route_portfolio["actions"]
    ]
    plan=controller.compile_global_plan(
        query_actions=combined,
        sources=sources,
        route_strategy_calibration=calibrated,
        state=state or state_base.new_state(),
    )
    return {
        "schema":SCHEMA,
        "status":"PASS__AUTHORIZED_EMPIRICAL_PLAN_WITH_VERIFIED_RECOVERY_PORTFOLIO",
        "authority_gate":gate,
        "route_portfolio":route_portfolio,
        "route_strategy_calibration":{
            "event_count":calibrated["event_count"],
            "case_count":calibrated["case_count"],
            "best_known_strategy_union":calibrated["best_known_strategy_union"],
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
            "FAIL_CLOSED_AUTHORITY_GUARD_PRECEDES_PLAN_COMPILATION",
            "V11_TO_V18_VERIFIED_RECOVERY_ROUTES_ARE_AVAILABLE_AS_GENERIC_FALLBACK_ACTIONS",
            "RECOVERY_ROUTES_USE_ONLY_REQUEST_AND_SOURCE_SHAPE_NOT_ANSWER_KEY_IDENTITY",
            "RECOVERY_ROUTES_REQUIRE_DECLARED_PRIOR_MISS_BEFORE_EXECUTION",
            "CURRENT_EMPIRICAL_CONTROLLER_V3_REMAINS_THE_RANKER",
            "FINITE_30_OF_30_IS_REGRESSION_EVIDENCE_NOT_OPEN_WORLD_COMPLETENESS",
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
