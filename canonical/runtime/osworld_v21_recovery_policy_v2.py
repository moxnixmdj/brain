"""Generic state-reconstruction recovery V2.

Extends V1 only after V1 proves a recovery trigger but cannot find a safe unique
reversible control. Browser-operation failures are re-observed through the
semantic browser surface. Visible modal-like UI may be escaped once. Repeated
reconstruction on an unchanged state fails closed.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.osworld_v21_generic_policy_v1 import parse_a11y
from canonical.runtime.osworld_v21_recovery_policy_v1 import route_recovery as route_v1

SCHEMA="PROJECT_BRAIN_OSWORLD_V21_RECOVERY_POLICY_V2"
_MODAL_SUFFIXES=("dialog","alert","menu","popup","popover")

def _latest(state:Mapping[str,Any])->Mapping[str,Any]|None:
    history=state.get("history")
    if not isinstance(history,list) or not history:
        return None
    row=history[-1]
    return row if isinstance(row,Mapping) else None

def _same_state_attempted(state:Mapping[str,Any],route:str)->bool:
    history=state.get("history")
    if not isinstance(history,list):
        return False
    current=str(state.get("screenshot_sha256") or "")
    for row in reversed(history[-8:]):
        if not isinstance(row,Mapping):
            continue
        receipt=row.get("policy_receipt")
        if not isinstance(receipt,Mapping) or receipt.get("schema")!=SCHEMA:
            continue
        if receipt.get("route")==route and str(row.get("screenshot_sha256") or "")==current:
            return True
    return False

def _visible_modal(state:Mapping[str,Any])->bool:
    for element in parse_a11y(state.get("a11y_tree")):
        tag=str(element.tag or "").casefold()
        if any(tag.endswith(suffix) for suffix in _MODAL_SUFFIXES):
            return True
    return False

def route_recovery(state:Mapping[str,Any])->dict[str,Any]|None:
    if not isinstance(state,Mapping):
        return None

    base=route_v1(state)
    if not isinstance(base,Mapping):
        return None

    receipt=base.get("_policy_receipt")
    if not isinstance(receipt,Mapping):
        return dict(base)
    if not (
        receipt.get("route")=="RECOVERY_UNRESOLVED"
        and receipt.get("reason")=="NO_SAFE_CONTROL"
    ):
        return dict(base)

    trigger=str(receipt.get("trigger") or "")
    prior=_latest(state)
    error=str((prior or {}).get("operation_error") or "")

    if trigger=="OPERATION_ERROR" and "browser" in error.casefold():
        route="BROWSER_REOBSERVE"
        if _same_state_attempted(state,route):
            return {
                "response":"browser reconstruction loop suppressed",
                "actions":[{"type":"WAIT"}],
                "_policy_receipt":{
                    "schema":SCHEMA,
                    "route":"RECOVERY_RECONSTRUCTION_LOOP_SUPPRESSED",
                    "trigger":trigger,
                    "attempted_route":route,
                },
            }
        return {
            "response":"re-observe browser state after failed browser operation",
            "actions":[{"type":"BROWSER_OP","op":{"type":"OBSERVE"}}],
            "_policy_receipt":{
                "schema":SCHEMA,
                "route":route,
                "trigger":trigger,
                "external_model_dependency":False,
                "task_specific_policy_data":False,
            },
        }

    if _visible_modal(state):
        route="MODAL_ESCAPE"
        if _same_state_attempted(state,route):
            return {
                "response":"modal reconstruction loop suppressed",
                "actions":[{"type":"WAIT"}],
                "_policy_receipt":{
                    "schema":SCHEMA,
                    "route":"RECOVERY_RECONSTRUCTION_LOOP_SUPPRESSED",
                    "trigger":trigger,
                    "attempted_route":route,
                },
            }
        return {
            "response":"apply one reversible escape to visible modal state",
            "actions":[{"type":"PRESS","key":"esc"}],
            "_policy_receipt":{
                "schema":SCHEMA,
                "route":route,
                "trigger":trigger,
                "external_model_dependency":False,
                "task_specific_policy_data":False,
            },
        }

    return dict(base)
