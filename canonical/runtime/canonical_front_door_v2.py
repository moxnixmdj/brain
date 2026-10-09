"""Canonical front door V2 with lazy D-final dispatch."""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_CANONICAL_FRONT_DOOR_V2"
D_FINAL_MODE="D_FINAL_BOUND_CAPABILITY"

class CanonicalFrontDoorError(ValueError): pass

def run(request:Mapping[str,Any],**kwargs:Any)->dict[str,Any]:
    if not isinstance(request,Mapping):
        raise CanonicalFrontDoorError("REQUEST_NOT_OBJECT")
    mode=str(request.get("mode") or "").strip().upper()
    if mode==D_FINAL_MODE:
        payload=request.get("payload")
        if not isinstance(payload,Mapping):
            raise CanonicalFrontDoorError("D_FINAL_PAYLOAD_NOT_OBJECT")
        capability_id=str(payload.get("capability_id") or "").strip()
        capability_payload=payload.get("capability_payload")
        if not capability_id:
            raise CanonicalFrontDoorError("D_FINAL_CAPABILITY_ID_REQUIRED")
        if not isinstance(capability_payload,Mapping):
            raise CanonicalFrontDoorError("D_FINAL_CAPABILITY_PAYLOAD_NOT_OBJECT")
        from canonical.runtime import d_final_bound_live_entrypoint_v1 as d_final
        out=d_final.invoke(capability_id,capability_payload)
        return {
          "schema":SCHEMA,
          "status":"PASS__D_FINAL_CANONICAL_FRONT_DOOR" if out.get("pass") is True else "FAIL__D_FINAL_CANONICAL_FRONT_DOOR",
          "pass":out.get("pass") is True,
          "mode":D_FINAL_MODE,
          "result":out,
          "terminal_authority":False,
        }
    from canonical.runtime import unified_cognitive_fabric_v1 as fabric
    return fabric.run(request,**kwargs)
