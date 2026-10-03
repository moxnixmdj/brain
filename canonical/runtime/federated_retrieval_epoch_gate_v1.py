#!/usr/bin/env python3
"""Fail-closed epoch gate for Retrieval V4 federation."""
from __future__ import annotations
import hashlib, json
from typing import Any, Mapping

from canonical.runtime import residual_witness_retrieval_compiler_v1 as core

SCHEMA="PROJECT_BRAIN_FEDERATED_RETRIEVAL_EPOCH_GATE_V1"
ATTEMPTED={"BACKEND_EXECUTED","BACKEND_FAILED_TRANSIENT","BACKEND_REJECTED_PERMANENT"}


def _canon(x:Any)->str:
    return " ".join(str(x or "").strip().split())


def compile_router_plan(base_program:Mapping[str,Any],federation:Mapping[str,Any])->dict[str,Any]:
    if base_program.get("schema")!=core.SCHEMA or base_program.get("status")!="COMPILED":
        raise ValueError("BASE_COMPILED_PROGRAM_REQUIRED")
    if federation.get("schema")!="PROJECT_BRAIN_PUBLIC_SOURCE_FEDERATION_V2":
        raise ValueError("FEDERATION_V2_REQUIRED")
    requests=federation.get("requests")
    if not isinstance(requests,list) or not requests:
        raise ValueError("FEDERATION_REQUESTS_REQUIRED")
    actions=[]; seen=set()
    for index,req in enumerate(requests):
        rid=_canon(req.get("request_id")); query=_canon(req.get("query"))
        if not rid or not query: raise ValueError("REQUEST_ID_AND_QUERY_REQUIRED")
        if rid in seen: raise ValueError("DUPLICATE_REQUEST_ID")
        seen.add(rid)
        actions.append({
            "action_id":rid,
            "action":"QUERY",
            "query_id":f"F4{index:04d}",
            "query":query,
            "basis":"FEDERATED_V4_"+_canon(req.get("selection_class") or "UNSPECIFIED"),
            "language_hint":_canon(req.get("script") or "UNKNOWN"),
            "surface":"OPEN_WEB",
            "source_domain":_canon(req.get("domain")),
        })
    payload={"base":base_program.get("retrieval_program_sha256"),"federation":federation.get("federation_program_sha256"),"actions":actions}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
    return {"schema":"PROJECT_BRAIN_FEDERATED_RETRIEVAL_ROUTER_PLAN_V1","status":"COMPILED","residual_id":base_program.get("residual_id"),"actions":actions,"action_count":len(actions),"plan_sha256":digest,"complete":False,"incremental_spend_usd":0}


def router_subprogram(base_program:Mapping[str,Any],plan:Mapping[str,Any])->dict[str,Any]:
    if plan.get("schema")!="PROJECT_BRAIN_FEDERATED_RETRIEVAL_ROUTER_PLAN_V1":
        raise ValueError("ROUTER_PLAN_REQUIRED")
    rows=[{"query_id":x["query_id"],"text":x["query"],"basis":x["basis"],"language_hint":x["language_hint"]} for x in plan["actions"]]
    digest=hashlib.sha256(json.dumps({"plan":plan.get("plan_sha256"),"rows":rows},sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
    return {"schema":core.SCHEMA,"status":"COMPILED","residual_id":base_program.get("residual_id"),"effect":base_program.get("effect"),"required_capabilities":list(base_program.get("required_capabilities") or []),"constraints":dict(base_program.get("constraints") or {}),"query_lattice":rows,"surfaces":["OPEN_WEB"],"candidate_only_surfaces":[],"declared_scope":None,"retrieval_program_sha256":digest,"incremental_spend_usd":0}


def evaluate(plan:Mapping[str,Any],receipts:list[Mapping[str,Any]])->dict[str,Any]:
    if plan.get("schema")!="PROJECT_BRAIN_FEDERATED_RETRIEVAL_ROUTER_PLAN_V1":
        raise ValueError("ROUTER_PLAN_REQUIRED")
    expected={str(x["action_id"]):x for x in plan.get("actions") or []}
    errors=[]; by_id={}
    for row in receipts or []:
        if not isinstance(row,Mapping):
            errors.append("RECEIPT_NOT_MAPPING"); continue
        aid=_canon(row.get("action_id"))
        if aid not in expected:
            errors.append("UNKNOWN_RECEIPT_ACTION:"+aid); continue
        if aid in by_id:
            errors.append("DUPLICATE_RECEIPT_ACTION:"+aid); continue
        by_id[aid]=row
        if row.get("router_status") not in ATTEMPTED:
            errors.append("RECEIPT_NOT_ATTEMPTED:"+aid)
        if row.get("acceptance_credit") not in (None,0):
            errors.append("RECEIPT_AUTHORITY_VIOLATION:"+aid)
    missing=sorted(set(expected)-set(by_id))
    if missing: errors.append("MISSING_ROUTER_RECEIPTS:"+",".join(missing))
    all_attempted=not errors and bool(expected)
    payload={"plan_sha256":plan.get("plan_sha256"),"receipts":[dict(by_id[k]) for k in sorted(by_id)]}
    epoch=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
    return {"schema":SCHEMA,"status":"PASS__ALL_SELECTED_FEDERATION_CELLS_ATTEMPTED" if all_attempted else "FAIL_CLOSED","pass":all_attempted,"errors":sorted(errors),"plan_action_count":len(expected),"receipt_count":len(by_id),"source_epoch_sha256":epoch,"epoch_consumption_authorized":all_attempted,"complete":False,"nonexistence_claim_authorized":False,"acceptance_credit":0,"capability_credit_delta":0,"family_credit_delta":0,"execution_authority":False,"promotion_authority":False,"hard_rules":["EPOCH_CONSUMPTION_REQUIRES_ONE_ROUTER_RECEIPT_PER_SELECTED_CELL","BACKEND_UNBOUND_IS_NOT_AN_ATTEMPT","EMPTY_OR_FAILED_ATTEMPTS_REMAIN_UNKNOWN","EPOCH_CONSUMPTION_IS_NOT_OPEN_WORLD_COMPLETENESS"]}
