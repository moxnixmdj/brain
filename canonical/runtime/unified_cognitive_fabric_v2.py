"""Unified cognitive fabric V2.

V2 changes only ADEQUATE_DECISION dispatch to the R2 V2 controller.
All other modes delegate to V1 unchanged.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Callable, Mapping

from canonical.runtime import unified_cognitive_fabric_v1 as v1
from canonical.runtime import general_adequate_decision_controller_v2 as decision_v2

SCHEMA="PROJECT_BRAIN_UNIFIED_COGNITIVE_FABRIC_V2"


def catalog()->dict[str,Any]:
    out=deepcopy(v1.catalog())
    out["schema"]=SCHEMA
    engines=dict(out.get("engines") or {})
    engines["ADEQUATE_DECISION"]="general_adequate_decision_controller_v2.run"
    out["engines"]=engines
    out["adequate_decision_route_version"]="V2"
    return out


def run(
    request:Mapping[str,Any], *,
    information_provider:Callable[[Mapping[str,Any],int],Mapping[str,Any]|None]|None=None,
    proposal_provider:Callable[...,Mapping[str,Any]|None]|None=None,
    capability_expander:Callable[...,Mapping[str,Any]|None]|None=None,
)->dict[str,Any]:
    if not isinstance(request,Mapping):
        return v1.run(request)
    requested=str(request.get("mode") or "").strip().upper()
    if requested=="CATALOG":
        return catalog()
    payload=request.get("payload")
    options=request.get("options") or {}
    if not isinstance(payload,Mapping) or not isinstance(options,Mapping):
        return v1.run(
            request,information_provider=information_provider,
            proposal_provider=proposal_provider,capability_expander=capability_expander)
    auto=requested in {"","AUTO"}
    try:
        mode=v1._auto_mode(payload,options) if auto else requested
    except Exception:
        return v1.run(
            request,information_provider=information_provider,
            proposal_provider=proposal_provider,capability_expander=capability_expander)
    if mode!="ADEQUATE_DECISION":
        return v1.run(
            request,information_provider=information_provider,
            proposal_provider=proposal_provider,capability_expander=capability_expander)

    out=decision_v2.run(
        payload,repo_root=v1.ROOT,information_provider=information_provider,
        proposal_provider=proposal_provider,capability_expander=capability_expander)
    return {
        "schema":SCHEMA,
        "status":"FABRIC_DISPATCH_COMPLETE",
        "mode":"ADEQUATE_DECISION",
        "requested_mode":requested or "AUTO",
        "auto_routed":auto,
        "engine":"general_adequate_decision_controller_v2.run",
        "inner_pass":bool(isinstance(out,Mapping) and out.get("pass") is True),
        "inner_status":out.get("status") if isinstance(out,Mapping) else None,
        "result":deepcopy(dict(out)) if isinstance(out,Mapping) else out,
        "single_front_door":True,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }
