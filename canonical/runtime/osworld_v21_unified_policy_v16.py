"""Unified V16: generic observable recovery first, verified V15 capability stack otherwise."""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.osworld_v21_recovery_policy_v1 import route_recovery
from canonical.runtime.osworld_v21_unified_policy_v15 import decide as base_decide

def decide(state:Mapping[str,Any])->Mapping[str,Any]:
    recovery=route_recovery(state)
    if isinstance(recovery,Mapping):
        return recovery
    return base_decide(state)
