"""Unified V11 base policy: media route, then verified V10 base."""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.osworld_v21_media_policy_overlay_v1 import route_media
from canonical.runtime.osworld_v21_unified_policy_v10 import decide as base_decide

def decide(state:Mapping[str,Any])->Mapping[str,Any]:
    routed=route_media(state)
    return routed if isinstance(routed,Mapping) else base_decide(state)
