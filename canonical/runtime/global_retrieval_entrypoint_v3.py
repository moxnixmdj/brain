#!/usr/bin/env python3
"""Authorized empirical global retrieval entrypoint V3.

V3 removes ad-hoc caller source declarations from the current path. It loads the
canonical source universe, binds every enumerable source to an explicit scope
and epoch, rejects unknown query-action sources, and then delegates ordering to
the empirically calibrated V2 controller.

It preserves the V6/V7 fail-closed authority guard and V8 live-event routing.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any,Mapping,Sequence

from canonical.runtime import global_retrieval_authority_guard_v1 as guard
from canonical.runtime import global_retrieval_controller_v2 as controller
from canonical.runtime import retrieval_live_event_ledger_v1 as ledger
from canonical.runtime import global_retrieval_controller_v1 as state_base
from canonical.runtime import retrieval_source_universe_v1 as source_universe

SCHEMA="PROJECT_BRAIN_GLOBAL_RETRIEVAL_ENTRYPOINT_V3"


def compile_authorized_plan(
    *,
    root:Path,
    query_actions:Sequence[Mapping[str,Any]],
    source_epoch:str,
    runtime_source_bindings:Mapping[str,Mapping[str,Any]]|None=None,
    include_source_ids:Sequence[str]|None=None,
    include_high_volume_defaults:bool=False,
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

    registry=source_universe.load_registry(root)
    bound=source_universe.bind_sources(
        registry,
        epoch=source_epoch,
        runtime_bindings=runtime_source_bindings or {},
        include_source_ids=include_source_ids,
        include_high_volume_defaults=include_high_volume_defaults,
    )
    sources=source_universe.controller_sources(bound)
    known={str(x.get("source_id")) for x in sources}
    unknown=sorted({
        str(x.get("source_id") or x.get("domain") or x.get("backend_id") or "")
        for x in query_actions
        if str(x.get("source_id") or x.get("domain") or x.get("backend_id") or "") not in known
    })
    if unknown:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED__QUERY_ACTION_REFERENCES_SOURCE_OUTSIDE_CANONICAL_UNIVERSE",
            "authority_gate":gate,
            "unknown_source_ids":unknown,
            "bound_source_universe":bound,
            "plan":None,
            "execution_authority":False,
            "promotion_authority":False,
            "acceptance_credit_delta":0,
            "family_credit_delta":0,
            "capability_credit_delta":0,
            "ownership_credit_delta":0,
        }

    if live_events is None:
        live_events=ledger.load_jsonl(root/"canonical/state/retrieval_live_events_v1.jsonl")
    calibrated=ledger.aggregate(live_events)
    plan=controller.compile_global_plan(
        query_actions=query_actions,
        sources=sources,
        live_calibration=calibrated,
        state=state or state_base.new_state(),
    )
    return {
        "schema":SCHEMA,
        "status":"PASS__AUTHORIZED_CANONICAL_SOURCE_EMPIRICAL_GLOBAL_RETRIEVAL_PLAN_COMPILED",
        "authority_gate":gate,
        "bound_source_universe":bound,
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
            "AUTHORIZED_SOURCE_IDS_MUST_COME_FROM_THE_CANONICAL_SOURCE_UNIVERSE",
            "ENUMERABLE_SOURCES_REQUIRE_EXPLICIT_SCOPE_AND_EPOCH_BINDING",
            "MISSING_RUNTIME_SCOPE_BINDINGS_SKIP_A_SOURCE_INSTEAD_OF_WIDENING_SCOPE",
            "LIVE_PROVIDER_EVENTS_CALIBRATE_PROVIDER_ROUTING",
            "FINITE_ARENAS_DO_NOT_CALIBRATE_LIVE_PROVIDER_ROUTING",
            "OPEN_WORLD_MISS_REMAINS_UNKNOWN",
        ],
    }


def main()->int:
    root=Path(__file__).resolve().parents[2]
    out=compile_authorized_plan(
        root=root,
        query_actions=[],
        source_epoch="EXAMPLE_EPOCH",
    )
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out.get("status","").startswith("PASS") else 1


if __name__=="__main__":
    raise SystemExit(main())
