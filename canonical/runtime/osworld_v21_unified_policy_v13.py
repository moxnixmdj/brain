"""Unified V13 base policy: verified structured V11 first, visual fallback last."""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.osworld_v21_unified_policy_v11 import decide as base_decide
from canonical.runtime.osworld_v21_visual_policy_overlay_v1 import route_visual

def _waiting(out:Any)->bool:
    if not isinstance(out,Mapping): return False
    actions=out.get("actions")
    return (
        isinstance(actions,list) and len(actions)==1 and isinstance(actions[0],Mapping)
        and str(actions[0].get("type") or "").strip().upper()=="WAIT"
    )

def decide(state:Mapping[str,Any])->Mapping[str,Any]:
    out=base_decide(state)
    if not _waiting(out): return out
    visual=route_visual(state)
    return visual if isinstance(visual,Mapping) else out
