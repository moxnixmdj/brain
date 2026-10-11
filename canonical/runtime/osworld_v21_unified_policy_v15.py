"""Unified V15: verified V14 first, comparative visual disambiguation only on WAIT."""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.osworld_v21_unified_policy_v14 import decide as base_decide
from canonical.runtime.osworld_v21_visual_relational_grounding_v1 import route_relational_visual

def _waiting(out:Any)->bool:
    if not isinstance(out,Mapping):
        return False
    actions=out.get("actions")
    return (
        isinstance(actions,list) and len(actions)==1 and isinstance(actions[0],Mapping)
        and str(actions[0].get("type") or "").strip().upper()=="WAIT"
    )

def decide(state:Mapping[str,Any])->Mapping[str,Any]:
    out=base_decide(state)
    if not _waiting(out):
        return out
    routed=route_relational_visual(state)
    return routed if isinstance(routed,Mapping) else out
