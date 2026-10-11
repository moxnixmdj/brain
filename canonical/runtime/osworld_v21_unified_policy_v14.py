"""Unified V14 policy: prefer directly grounded observable-state actions before richer overlays."""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.osworld_v21_generic_policy_v1 import decide as grounded_decide
from canonical.runtime.osworld_v21_unified_policy_v13 import decide as base_decide

def _waiting(out:Any)->bool:
    if not isinstance(out,Mapping):
        return False
    actions=out.get("actions")
    return (
        isinstance(actions,list) and len(actions)==1 and isinstance(actions[0],Mapping)
        and str(actions[0].get("type") or "").strip().upper()=="WAIT"
    )

def decide(state:Mapping[str,Any])->Mapping[str,Any]:
    direct=grounded_decide(state)
    if not _waiting(direct):
        return direct
    return base_decide(state)
