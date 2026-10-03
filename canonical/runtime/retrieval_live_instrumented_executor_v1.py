#!/usr/bin/env python3
"""Fail-closed live retrieval execution with automatic empirical instrumentation.

Every provider action executed through this module:
1. validates the current global retrieval authority,
2. refuses duplicate (episode_id, action_id) execution,
3. measures real wall-clock latency with perf_counter,
4. extracts candidate identities without trusting provider self-certification,
5. appends exactly one validated event to the live JSONL ledger,
6. recomputes empirical calibration from the append-only ledger.

Provider results remain candidate-only. A verified sufficient candidate may be
recorded only when the caller supplies an independent receipt explicitly.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import global_retrieval_authority_guard_v1 as authority_guard
from canonical.runtime import retrieval_live_event_ledger_v1 as ledger

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_INSTRUMENTED_EXECUTOR_V1"


class LiveRetrievalExecutionError(RuntimeError):
    pass


def _s(x:Any)->str:
    return " ".join(str(x or "").strip().split())


def _candidate_id(row:Mapping[str,Any],index:int)->str:
    for key in ("candidate_id","canonical_url","url","repository","package","project","tool_id","name"):
        value=_s(row.get(key))
        if value:
            return value
    return f"ANONYMOUS_CANDIDATE_{index:04d}"


def _candidate_rows(result:Mapping[str,Any])->list[Mapping[str,Any]]:
    direct=result.get("candidates")
    if isinstance(direct,list):
        return [x for x in direct if isinstance(x,Mapping)]
    nested=result.get("result")
    if isinstance(nested,Mapping) and isinstance(nested.get("candidates"),list):
        return [x for x in nested["candidates"] if isinstance(x,Mapping)]
    return []


def _provider_authority_violation(result:Mapping[str,Any])->str|None:
    forbidden=("verified_sufficient","verified_witness","acceptance_credit","family_credit","capability_credit","ownership_credit","promotion_authority")
    for key in forbidden:
        if result.get(key) not in (None,False,0,[],{}):
            return "PROVIDER_AUTHORITY_VIOLATION:"+key
    for row in _candidate_rows(result):
        for key in forbidden:
            if row.get(key) not in (None,False,0,[],{}):
                return "CANDIDATE_AUTHORITY_VIOLATION:"+key
    if result.get("verified_sufficient_candidate_ids"):
        return "PROVIDER_SELF_CERTIFIED_SUFFICIENCY"
    return None


def _status_from_result(result:Mapping[str,Any])->str:
    status=_s(result.get("status")).upper()
    if "FAILED_PERMANENT" in status or "REJECTED_PERMANENT" in status:
        return "FAILED_PERMANENT"
    if "FAILED" in status or "PARTIAL" in status:
        return "FAILED_RETRYABLE"
    return "SUCCESS"


def _request_count(result:Mapping[str,Any],default:int)->int:
    for key in ("executed_request_count","request_count"):
        try:
            if result.get(key) is not None:
                return max(0,int(result.get(key)))
        except Exception:
            pass
    return max(0,int(default))


def _validate_no_duplicate(events:Sequence[Mapping[str,Any]],episode_id:str,action_id:str)->None:
    for row in events:
        if _s(row.get("episode_id"))==episode_id and _s(row.get("action_id"))==action_id:
            raise LiveRetrievalExecutionError("DUPLICATE_EPISODE_ACTION_EVENT")


def append_event(path:Path,event:Mapping[str,Any])->dict[str,Any]:
    existing=ledger.load_jsonl(path)
    episode=_s(event.get("episode_id")); action=_s(event.get("action_id"))
    _validate_no_duplicate(existing,episode,action)
    # Aggregate first: validates the event and duplicate semantics before bytes mutate.
    calibrated=ledger.aggregate([*existing,dict(event)])
    path.parent.mkdir(parents=True,exist_ok=True)
    encoded=json.dumps(dict(event),ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n"
    with path.open("a",encoding="utf-8") as f:
        f.write(encoded)
        f.flush()
        os.fsync(f.fileno())
    return calibrated


def execute_observed(
    *,
    root:Path,
    episode_id:str,
    sequence:int,
    action:Mapping[str,Any],
    provider:Callable[[Mapping[str,Any]],Mapping[str,Any]],
    source_id:str|None=None,
    upstream_group:str|None=None,
    event_path:Path|None=None,
    request_count_default:int=1,
    verified_sufficient_candidate_ids:Sequence[str]|None=None,
    independent_receipt:str|None=None,
)->dict[str,Any]:
    gate=authority_guard.evaluate_repository(root)
    if gate.get("pass") is not True:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED__GLOBAL_RETRIEVAL_AUTHORITY_INVALID",
            "authority_gate":gate,
            "event_appended":False,
            "execution_authority":False,
            "promotion_authority":False,
            "acceptance_credit_delta":0,
            "family_credit_delta":0,
            "capability_credit_delta":0,
            "ownership_credit_delta":0,
        }
    if not callable(provider):
        raise ValueError("PROVIDER_CALLABLE_REQUIRED")
    episode=_s(episode_id)
    aid=_s(action.get("action_id") or action.get("request_id") or action.get("query_id"))
    sid=_s(source_id or action.get("source_id") or action.get("domain") or action.get("backend_id"))
    group=_s(upstream_group or action.get("upstream_group") or sid)
    if not episode or not aid or not sid:
        raise ValueError("EPISODE_ACTION_SOURCE_ID_REQUIRED")
    path=event_path or (root/"canonical/state/retrieval_live_events_v1.jsonl")
    existing=ledger.load_jsonl(path)
    _validate_no_duplicate(existing,episode,aid)

    start=time.perf_counter()
    result:Mapping[str,Any]|None=None
    error:Exception|None=None
    event_status="SUCCESS"
    authority_violation=None
    try:
        raw=provider(dict(action))
        if not isinstance(raw,Mapping):
            raise LiveRetrievalExecutionError("PROVIDER_RESULT_MAPPING_REQUIRED")
        result=dict(raw)
        authority_violation=_provider_authority_violation(result)
        if authority_violation:
            event_status="FAILED_PERMANENT"
        else:
            event_status=_status_from_result(result)
    except Exception as exc:
        error=exc
        event_status="FAILED_RETRYABLE"
    latency=max(1e-9,time.perf_counter()-start)

    candidates=[]
    requests=max(0,int(request_count_default))
    if result is not None and not authority_violation:
        candidates=sorted({_candidate_id(x,i) for i,x in enumerate(_candidate_rows(result))})
        requests=_request_count(result,request_count_default)

    sufficient=sorted({_s(x) for x in (verified_sufficient_candidate_ids or []) if _s(x)})
    receipt=_s(independent_receipt)
    if sufficient:
        if not receipt:
            raise LiveRetrievalExecutionError("SUFFICIENT_EVENT_REQUIRES_INDEPENDENT_RECEIPT")
        outside=set(sufficient)-set(candidates)
        if outside:
            raise LiveRetrievalExecutionError("SUFFICIENT_CANDIDATE_NOT_IN_EVENT_CANDIDATES")

    event={
        "episode_id":episode,
        "source_id":sid,
        "upstream_group":group,
        "action_id":aid,
        "sequence":max(0,int(sequence)),
        "status":event_status,
        "candidate_ids":candidates,
        "verified_sufficient_candidate_ids":sufficient,
        "independent_receipt":receipt or None,
        "latency_seconds":latency,
        "request_count":requests,
    }
    calibrated=append_event(path,event)
    return {
        "schema":SCHEMA,
        "status":(
            "PASS__LIVE_RETRIEVAL_EVENT_APPENDED"
            if event_status=="SUCCESS"
            else "RECORDED__"+event_status
        ),
        "authority_gate":gate,
        "provider_result":dict(result) if result is not None else None,
        "provider_error_class":type(error).__name__ if error else None,
        "provider_error":str(error)[:1000] if error else authority_violation,
        "event":event,
        "event_appended":True,
        "live_calibration_after":{
            "event_count":calibrated["event_count"],
            "episode_count":calibrated["episode_count"],
            "source_stats":calibrated["source_stats"],
            "pairwise_candidate_overlap":calibrated["pairwise_candidate_overlap"],
        },
        "execution_authority":False,
        "promotion_authority":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "incremental_spend_usd":0,
        "hard_rules":[
            "CURRENT_GLOBAL_RETRIEVAL_AUTHORITY_MUST_PASS_BEFORE_PROVIDER_EXECUTION",
            "EVERY_EXECUTED_PROVIDER_ACTION_APPENDS_ONE_MEASURED_LIVE_EVENT",
            "DUPLICATE_EPISODE_ACTION_EXECUTION_FAILS_BEFORE_PROVIDER_CALL",
            "PROVIDER_SELF_CERTIFICATION_IS_RECORDED_AS_PERMANENT_FAILURE",
            "SUFFICIENCY_REQUIRES_CALLER_SUPPLIED_INDEPENDENT_RECEIPT",
            "LATENCY_IS_MEASURED_WITH_PERF_COUNTER_NOT_INVENTED",
            "LIVE_EVENTS_ARE_APPEND_ONLY",
            "OPEN_WORLD_MISS_REMAINS_UNKNOWN",
        ],
    }
