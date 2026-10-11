"""Unified V10 base policy: code workspace first, then verified V9 base surfaces."""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.osworld_v21_code_policy_overlay_v1 import route_code
from canonical.runtime.osworld_v21_web_app_policy_overlay_v1 import decide as base_decide

def decide(state:Mapping[str,Any])->Mapping[str,Any]:
    routed=route_code(state)
    return routed if isinstance(routed,Mapping) else base_decide(state)
