"""Non-creditable symbolic-region canary for the V2 selected-route runtime."""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_SYMBOLIC_ROUTER_DEPLOYMENT_CANARY_PREDICATE_V1"

def admit(context: Mapping[str, Any]) -> bool:
    if not isinstance(context, Mapping):
        return False
    return context.get("kind") == "SYMBOLIC_ROUTER_DEPLOYMENT_CANARY_V1"
