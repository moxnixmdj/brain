"""Capability-first workflow V11: generic recovery wraps verified V10 workflows."""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.osworld_v21_recovery_policy_v1 import route_recovery
from canonical.runtime.osworld_v21_workflow_policy_v10 import decide as base_decide

def decide(state:Mapping[str,Any])->Mapping[str,Any]:
    recovery=route_recovery(state)
    if isinstance(recovery,Mapping):
        return recovery
    return base_decide(state)
