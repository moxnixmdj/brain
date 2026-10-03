#!/usr/bin/env python3
"""Authorized empirical global retrieval entrypoint V2."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import global_retrieval_authority_guard_v1 as guard
from canonical.runtime import global_retrieval_controller_v2 as controller
from canonical.runtime import retrieval_live_event_ledger_v1 as ledger
from canonical.runtime import global_retrieval_controller_v1 as state_base

SCHEMA="PROJECT_BRAIN_GLOBAL_RETRIEVAL_ENTRYPOINT_V2"


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
        path=root/"canonical/state/retrieval_live_events_v1.jsonl"
        live_events=ledger.load_jsonl(path)
    calibrated=ledger.aggregate(live_events)
    plan=controller.compile_global_plan(
        query_actions=query_actions,
        sources=sources,
        live_calibration=calibrated,
        state=state or state_base.new_state(),
    )
    return {
        "schema":SCHEMA,
        "status":"PASS__AUTHORIZED_EMPIRICAL_GLOBAL_RETRIEVAL_PLAN_COMPILED",
        "authority_gate":gate,
        "live_calibration":{
            "event_count":calibrated["event_count"],
            "episode_count":calibrated["episode_count"],
            "source_stats":calibrated["source_stats"],
            "pairwise_candidate_overlap":calibrated["pairwise_candidate_overlap"],
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
            "LIVE_PROVIDER_EVENTS_CALIBRATE_PROVIDER_ROUTING",
            "FINITE_HIDDEN_WITNESS_ARENA_IS_NOT_USED_AS_A_LIVE_PROVIDER_ORACLE",
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
