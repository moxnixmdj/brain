from __future__ import annotations
from typing import Any, Mapping
from canonical.runtime import d_final_bound_live_entrypoint_v1 as d_live

CAPABILITY_ID="bound:decision.synthesis.verify.stdlib"

def invoke(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        raise ValueError("D_FINAL_DECISION_ROUTE_PAYLOAD_NOT_OBJECT")
    return d_live.invoke(CAPABILITY_ID,payload)
