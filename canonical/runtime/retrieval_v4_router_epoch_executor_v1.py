#!/usr/bin/env python3
"""Execute one Retrieval V4 federation epoch through the verified OPEN_WEB router.

This is an execution adapter only:
- federation selection remains public_source_federation_v2;
- plan/subprogram construction remains federated_retrieval_epoch_gate_v1;
- backend execution remains residual_witness_backend_router_v1;
- source-cell epoch admission remains federated_retrieval_epoch_gate_v1.evaluate.

The only additional rule is candidate-domain filtering before the verified router
normalizes results, so a site-scoped cell cannot retain an off-domain result.
A query attempt may still consume its source cell when the backend actually ran;
empty/off-domain-only results remain UNKNOWN and never imply nonexistence.
"""
from __future__ import annotations

import copy
import urllib.parse
from typing import Any, Callable, Mapping

from canonical.runtime import federated_retrieval_epoch_gate_v1 as epoch_gate
from canonical.runtime import residual_witness_backend_router_v1 as router
from canonical.runtime import residual_witness_retrieval_compiler_v1 as core

SCHEMA="PROJECT_BRAIN_RETRIEVAL_V4_ROUTER_EPOCH_EXECUTOR_V1"


def _host_matches(url: Any, domain: str) -> bool:
    try:
        host=(urllib.parse.urlsplit(str(url or "")).hostname or "").lower().strip(".")
    except Exception:
        return False
    domain=str(domain or "").lower().strip(".")
    return bool(host and domain and (host==domain or host.endswith("."+domain)))


def _domain_scoped_provider(
    base_provider: Callable[[Mapping[str,Any]],Mapping[str,Any]],
    action: Mapping[str,Any],
) -> Mapping[str,Any]:
    raw=base_provider(dict(action))
    if not isinstance(raw,Mapping):
        raise ValueError("BASE_PROVIDER_RESULT_MAPPING_REQUIRED")
    domain=str(action.get("source_domain") or "").strip()
    if not domain:
        raise ValueError("SOURCE_DOMAIN_REQUIRED")
    out=copy.deepcopy(dict(raw))
    rows=out.get("candidates") or []
    if not isinstance(rows,list):
        raise ValueError("BASE_PROVIDER_CANDIDATES_LIST_REQUIRED")
    out["candidates"]=[
        dict(x) for x in rows
        if isinstance(x,Mapping) and _host_matches(x.get("url"),domain)
    ]
    out["source_domain_filter"]=domain
    out["off_domain_candidate_count"]=len(rows)-len(out["candidates"])
    return out


def execute_epoch(
    base_program: Mapping[str,Any],
    federation: Mapping[str,Any],
    *,
    open_web_provider: Callable[[Mapping[str,Any]],Mapping[str,Any]]|None=None,
) -> dict[str,Any]:
    plan=epoch_gate.compile_router_plan(base_program,federation)
    sub=epoch_gate.router_subprogram(base_program,plan)
    state=core.initial_state(sub)

    if open_web_provider is None:
        open_web_provider=router.default_providers().get("OPEN_WEB")
    if not callable(open_web_provider):
        raise ValueError("OPEN_WEB_PROVIDER_REQUIRED")

    receipts=[]
    candidates=[]
    cells=[]
    for action in plan["actions"]:
        provider=lambda a, _p=open_web_provider: _domain_scoped_provider(_p,a)
        result=router.execute_action(sub,state,action,provider)
        state=result["state"]
        normalized=result.get("result") if isinstance(result.get("result"),Mapping) else {}
        cands=normalized.get("candidates") or []
        if isinstance(cands,list):
            candidates.extend(copy.deepcopy(cands))
        receipt={
            "action_id":action["action_id"],
            "query_id":action["query_id"],
            "source_domain":action.get("source_domain"),
            "router_status":result.get("status"),
            "acceptance_credit":result.get("acceptance_credit",0),
            "candidate_count":len(cands) if isinstance(cands,list) else 0,
        }
        if result.get("status") in {"BACKEND_FAILED_TRANSIENT","BACKEND_REJECTED_PERMANENT"}:
            receipt["error_class"]=result.get("error_class")
            receipt["error"]=result.get("error")
        receipts.append(receipt)
        cells.append({
            "action_id":action["action_id"],
            "source_domain":action.get("source_domain"),
            "query":action.get("query"),
            "router_status":result.get("status"),
            "candidate_count":receipt["candidate_count"],
        })

    verdict=epoch_gate.evaluate(plan,receipts)
    return {
        "schema":SCHEMA,
        "status":"PASS__V4_ROUTER_EPOCH_EXECUTED__ZERO_CREDIT" if verdict.get("pass") is True else "FAIL_CLOSED",
        "base_program_sha256":base_program.get("retrieval_program_sha256"),
        "federation_program_sha256":federation.get("federation_program_sha256"),
        "router_plan_sha256":plan.get("plan_sha256"),
        "plan_action_count":plan.get("action_count"),
        "receipt_count":len(receipts),
        "receipts":receipts,
        "cells":cells,
        "candidates":candidates,
        "candidate_count":len(candidates),
        "epoch_verdict":verdict,
        "source_epoch_sha256":verdict.get("source_epoch_sha256"),
        "complete":False,
        "nonexistence_claim_authorized":False,
        "acceptance_credit":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "hard_rules":[
            "FEDERATION_V2_SELECTION_IS_UNCHANGED",
            "EVERY_SELECTED_CELL_RUNS_THROUGH_EXACT_VERIFIED_OPEN_WEB_ROUTER",
            "OFF_DOMAIN_CANDIDATES_ARE_DROPPED_BEFORE_ROUTER_NORMALIZATION",
            "ONE_ROUTER_RECEIPT_PER_SELECTED_CELL_REQUIRED_FOR_EPOCH_CONSUMPTION",
            "EMPTY_FAILED_OR_OFF_DOMAIN_ONLY_RESULTS_NEVER_AUTHORIZE_NONEXISTENCE",
            "CANDIDATES_REMAIN_UNVERIFIED_AND_ZERO_CREDIT",
        ],
    }
