"""Fail-closed recovery from explicit operation errors and observable no-progress states."""
from __future__ import annotations

import re
from typing import Any, Mapping

from canonical.runtime.osworld_v21_generic_policy_v1 import parse_a11y

SCHEMA="PROJECT_BRAIN_OSWORLD_V21_RECOVERY_POLICY_V1"
_ERROR_RECOVERY=("retry","try again","close","dismiss","cancel")
_NO_PROGRESS_RECOVERY=("close","dismiss","cancel")

def _norm(value:Any)->str:
    return re.sub(r"\s+"," ",str(value or "").casefold()).strip()

def _latest(state:Mapping[str,Any])->Mapping[str,Any]|None:
    history=state.get("history")
    if not isinstance(history,list) or not history:
        return None
    row=history[-1]
    return row if isinstance(row,Mapping) else None

def _trigger(state:Mapping[str,Any])->str|None:
    prior=_latest(state)
    if prior is None:
        return None
    if prior.get("operation_error"):
        return "OPERATION_ERROR"
    actions=prior.get("actions")
    same=(
        prior.get("screenshot_sha256")
        and prior.get("screenshot_sha256")==state.get("screenshot_sha256")
    )
    if (
        same
        and isinstance(actions,list)
        and actions
        and any(str(a).upper() not in {"WAIT","DONE","FAIL"} for a in actions)
    ):
        return "NO_PROGRESS"
    return None

def _already_attempted(state:Mapping[str,Any],label:str)->bool:
    history=state.get("history")
    if not isinstance(history,list):
        return False
    current=str(state.get("screenshot_sha256") or "")
    for row in reversed(history[-6:]):
        if not isinstance(row,Mapping):
            continue
        receipt=row.get("policy_receipt")
        if not isinstance(receipt,Mapping) or receipt.get("schema")!=SCHEMA:
            continue
        if (
            _norm(receipt.get("control"))==_norm(label)
            and str(row.get("screenshot_sha256") or "")==current
        ):
            return True
    return False

def route_recovery(state:Mapping[str,Any])->dict[str,Any]|None:
    if not isinstance(state,Mapping):
        return None
    trigger=_trigger(state)
    if trigger is None:
        return None

    allowed=_ERROR_RECOVERY if trigger=="OPERATION_ERROR" else _NO_PROGRESS_RECOVERY
    elements=parse_a11y(state.get("a11y_tree"))
    candidates=[
        e for e in elements
        if e.clickable and _norm(e.label) in allowed
    ]
    if not candidates:
        return {
            "response":"recovery trigger observed but no safe unique recovery control",
            "actions":[{"type":"WAIT"}],
            "_policy_receipt":{
                "schema":SCHEMA,"route":"RECOVERY_UNRESOLVED","trigger":trigger,
                "reason":"NO_SAFE_CONTROL",
            },
        }

    # Priority is deterministic and favors explicit retry after an operation error.
    ranked=[]
    for label in allowed:
        matches=[e for e in candidates if _norm(e.label)==label]
        if len(matches)>1:
            return {
                "response":"recovery control is ambiguous",
                "actions":[{"type":"WAIT"}],
                "_policy_receipt":{
                    "schema":SCHEMA,"route":"RECOVERY_UNRESOLVED","trigger":trigger,
                    "reason":"AMBIGUOUS_SAFE_CONTROL","control":label,
                },
            }
        if len(matches)==1:
            ranked.append(matches[0])
    if not ranked:
        return None

    chosen=ranked[0]
    if _already_attempted(state,chosen.label):
        return {
            "response":"recovery loop suppressed",
            "actions":[{"type":"WAIT"}],
            "_policy_receipt":{
                "schema":SCHEMA,"route":"RECOVERY_LOOP_SUPPRESSED",
                "trigger":trigger,"control":chosen.label,
            },
        }

    return {
        "response":"apply unique reversible recovery control",
        "actions":[{"type":"CLICK","x":chosen.x,"y":chosen.y}],
        "_policy_receipt":{
            "schema":SCHEMA,"route":"SAFE_RECOVERY_CLICK",
            "trigger":trigger,"control":chosen.label,
        },
    }
