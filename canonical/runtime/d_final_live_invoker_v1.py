from __future__ import annotations
from typing import Any, Callable, Mapping
from canonical.runtime import d_final_live_gate_v1 as gate
from canonical.runtime import live_capability_invoker_v1 as live

SCHEMA="PROJECT_BRAIN_D_FINAL_LIVE_INVOKER_V1"

def invoke(
    capability_id:str,
    payload:Mapping[str,Any],
    *,
    engine_runner:Callable[[str,Mapping[str,Any],Mapping[str,Any]],Mapping[str,Any]],
    options:Mapping[str,Any]|None=None,
)->dict[str,Any]:
    pf=gate.preflight(capability_id)
    out=live.invoke(
        capability_id,
        payload,
        engine_runner=engine_runner,
        options=options,
    )
    return {
        "schema":SCHEMA,
        "status":"PASS__D_FINAL_LIVE_CAPABILITY_DISPATCHED" if out.get("pass") is True else "FAIL__D_FINAL_LIVE_CAPABILITY_DISPATCHED",
        "pass":out.get("pass") is True,
        "capability_id":capability_id,
        "d_final_preflight":pf,
        "result":out,
    }
