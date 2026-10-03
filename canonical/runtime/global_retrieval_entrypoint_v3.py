#!/usr/bin/env python3
"""Authorized dual-empirical global retrieval entrypoint V3."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import global_retrieval_authority_guard_v1 as guard
from canonical.runtime import global_retrieval_controller_v1 as state_base
from canonical.runtime import global_retrieval_controller_v3 as controller
from canonical.runtime import retrieval_live_event_ledger_v1 as live_ledger
from canonical.runtime import retrieval_live_provider_calibration_v1 as labeled

SCHEMA="PROJECT_BRAIN_GLOBAL_RETRIEVAL_ENTRYPOINT_V3"

def compile_authorized_plan(
    *,
    root:Path,
    query_actions:Sequence[Mapping[str,Any]],
    sources:Sequence[Mapping[str,Any]],
    state:Mapping[str,Any]|None=None,
    live_events:Sequence[Mapping[str,Any]]|None=None,
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
    if live_events is None:
        live_events=live_ledger.load_jsonl(root/"canonical/state/retrieval_live_events_v1.jsonl")
    live_cal=live_ledger.aggregate(live_events)
    labeled_cal=labeled.calibrate_repository(root)
    plan=controller.compile_global_plan(
        query_actions=query_actions,
        sources=sources,
        live_calibration=live_cal,
        labeled_calibration=labeled_cal,
        state=state or state_base.new_state(),
    )
    return {
        "schema":SCHEMA,
        "status":"PASS__AUTHORIZED_DUAL_EMPIRICAL_GLOBAL_RETRIEVAL_PLAN_COMPILED",
        "authority_gate":gate,
        "live_open_world_calibration":{
            "event_count":live_cal["event_count"],
            "episode_count":live_cal["episode_count"],
            "source_stats":live_cal["source_stats"],
        },
        "labeled_provider_calibration":{
            "route_query_family_stats":labeled_cal["route_query_family_stats"],
            "routing_recommendations":labeled_cal["routing_recommendations"],
            "live_provider_calibration_complete":labeled_cal["live_provider_calibration_complete"],
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
            "AUTHORITY_GUARD_MUST_PASS_BEFORE_PLAN_COMPILATION",
            "OPEN_WORLD_NOVELTY_AND_LABELED_TARGET_RECOVERY_BOTH_INFORM_ROUTING",
            "FINITE_HIDDEN_WITNESS_ARENAS_REMAIN_REGRESSION_EVIDENCE_NOT_OPEN_WORLD_ORACLES",
            "PROVIDER_QUERY_FAMILY_MISSES_DEMOTE_BUT_NEVER_AUTHORIZE_NONEXISTENCE",
            "PLAN_ACTIONS_REMAIN_CANDIDATE_DISCOVERY_ONLY",
        ],
    }

def main()->int:
    root=Path(__file__).resolve().parents[2]
    out=compile_authorized_plan(root=root,query_actions=[],sources=[])
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out.get("status","").startswith("PASS") else 1

if __name__=="__main__":
    raise SystemExit(main())
