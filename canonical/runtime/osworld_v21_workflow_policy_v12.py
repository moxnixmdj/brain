"""Capability-first workflow V12: V2 state reconstruction wraps verified V11."""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.osworld_v21_recovery_policy_v2 import route_recovery
from canonical.runtime.osworld_v21_workflow_policy_v11 import decide as base_decide

def decide(state:Mapping[str,Any])->Mapping[str,Any]:
    recovered=route_recovery(state)
    if isinstance(recovered,Mapping):
        return recovered
    return base_decide(state)
