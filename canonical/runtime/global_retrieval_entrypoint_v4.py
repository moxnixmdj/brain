#!/usr/bin/env python3
"""Current composed retrieval entrypoint V4.

Planning:
- delegates to V3, which binds the canonical source universe to an explicit
  scope/epoch and uses only live empirical calibration.

Execution:
- recompiles the authorized plan for the exact source/epoch,
- requires the requested action_id to exist in that plan,
- executes the canonical action through the independently verified live
  instrumented executor,
- therefore measures latency and appends exactly one live event.

This is still candidate discovery only. It grants no sufficiency or acceptance
authority.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any,Callable,Mapping,Sequence

from canonical.runtime import global_retrieval_entrypoint_v3 as planner
from canonical.runtime import retrieval_live_instrumented_executor_v1 as instrumented

SCHEMA="PROJECT_BRAIN_GLOBAL_RETRIEVAL_ENTRYPOINT_V4"


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
    base=planner.compile_authorized_plan(
        root=root,
        query_actions=query_actions,
        source_epoch=source_epoch,
        runtime_source_bindings=runtime_source_bindings,
        include_source_ids=include_source_ids,
        include_high_volume_defaults=include_high_volume_defaults,
        state=state,
        live_events=live_events,
    )
    return {
        "schema":SCHEMA,
        "status":(
            "PASS__AUTHORIZED_SOURCE_BOUND_EMPIRICAL_RETRIEVAL_PLAN_COMPILED"
            if str(base.get("status") or "").startswith("PASS__")
            else "FAIL_CLOSED__V3_PLAN_COMPILATION_REJECTED"
        ),
        "base_entrypoint_v3":base,
        "plan":base.get("plan"),
        "execution_authority":False,
        "promotion_authority":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "incremental_spend_usd":0,
    }


def _identity(action:Mapping[str,Any])->tuple[str,str]:
    aid=str(action.get("action_id") or action.get("request_id") or action.get("query_id") or "").strip()
    sid=str(action.get("source_id") or action.get("domain") or action.get("backend_id") or "").strip()
    if not aid or not sid:
        raise ValueError("ACTION_ID_AND_SOURCE_ID_REQUIRED")
    return aid,sid


def execute_authorized_action(
    *,
    root:Path,
    episode_id:str,
    sequence:int,
    action:Mapping[str,Any],
    provider:Callable[[Mapping[str,Any]],Mapping[str,Any]],
    source_epoch:str,
    runtime_source_bindings:Mapping[str,Mapping[str,Any]]|None=None,
    include_high_volume_defaults:bool=False,
    event_path:Path|None=None,
    verified_sufficient_candidate_ids:Sequence[str]|None=None,
    independent_receipt:str|None=None,
)->dict[str,Any]:
    aid,sid=_identity(action)
    action_kind=str(action.get("action") or "QUERY_SOURCE").strip()
    query_actions=[dict(action)] if action_kind=="QUERY_SOURCE" else []

    compiled=compile_authorized_plan(
        root=root,
        query_actions=query_actions,
        source_epoch=source_epoch,
        runtime_source_bindings=runtime_source_bindings,
        include_source_ids=[sid],
        include_high_volume_defaults=include_high_volume_defaults,
    )
    if not str(compiled.get("status") or "").startswith("PASS__"):
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED__AUTHORIZED_PLAN_UNAVAILABLE",
            "compiled":compiled,
            "event_appended":False,
            "execution_authority":False,
            "promotion_authority":False,
            "acceptance_credit_delta":0,
            "family_credit_delta":0,
            "capability_credit_delta":0,
            "ownership_credit_delta":0,
        }

    rows=(compiled.get("plan") or {}).get("actions") or []
    matches=[x for x in rows if isinstance(x,Mapping) and str(x.get("action_id") or "")==aid and str(x.get("source_id") or "")==sid]
    if len(matches)!=1:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED__ACTION_NOT_IN_EXACT_AUTHORIZED_PLAN",
            "action_id":aid,
            "source_id":sid,
            "matched_action_count":len(matches),
            "event_appended":False,
            "execution_authority":False,
            "promotion_authority":False,
            "acceptance_credit_delta":0,
            "family_credit_delta":0,
            "capability_credit_delta":0,
            "ownership_credit_delta":0,
        }

    canonical_action=dict(matches[0])
    observed=instrumented.execute_observed(
        root=root,
        episode_id=episode_id,
        sequence=sequence,
        action=canonical_action,
        provider=provider,
        source_id=sid,
        upstream_group=str(canonical_action.get("upstream_group") or sid),
        event_path=event_path,
        verified_sufficient_candidate_ids=verified_sufficient_candidate_ids,
        independent_receipt=independent_receipt,
    )
    return {
        "schema":SCHEMA,
        "status":(
            "PASS__AUTHORIZED_LIVE_RETRIEVAL_ACTION_EXECUTED_AND_MEASURED"
            if observed.get("event_appended") is True
            else "FAIL_CLOSED__INSTRUMENTED_EXECUTION_REJECTED"
        ),
        "canonical_action":canonical_action,
        "instrumented_execution":observed,
        "event_appended":bool(observed.get("event_appended")),
        "execution_authority":False,
        "promotion_authority":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "incremental_spend_usd":0,
        "hard_rules":[
            "EVERY_EXECUTED_ACTION_MUST_EXIST_IN_THE_EXACT_CANONICAL_SOURCE_BOUND_PLAN",
            "UNKNOWN_OR_UNBOUND_SOURCE_ACTIONS_FAIL_BEFORE_PROVIDER_EXECUTION",
            "EVERY_EXECUTED_PROVIDER_ACTION_USES_THE_MEASURED_APPEND_ONLY_EXECUTOR",
            "PROVIDER_SELF_CERTIFICATION_REMAINS_FORBIDDEN",
            "OPEN_WORLD_MISS_REMAINS_UNKNOWN",
        ],
    }


def main()->int:
    root=Path(__file__).resolve().parents[2]
    out=compile_authorized_plan(root=root,query_actions=[],source_epoch="EXAMPLE_EPOCH")
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if str(out.get("status") or "").startswith("PASS__") else 1


if __name__=="__main__":
    raise SystemExit(main())
