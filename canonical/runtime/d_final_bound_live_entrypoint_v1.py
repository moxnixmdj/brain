from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime import d_final_live_gate_v1 as gate
from canonical.runtime import d_finality_execution_epoch_v1 as d_epoch
from canonical.runtime.verified_bound_capability_execution_adapter_v1 import execute as execute_bound

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/"canonical/governance/D_FINALITY_CERTIFICATE_REGISTRY_V1.json"
SCHEMA="PROJECT_BRAIN_D_FINAL_BOUND_LIVE_ENTRYPOINT_V1"

class DFinalBoundLiveError(ValueError): pass

def _doc(path:Path)->dict[str,Any]:
    raw=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw,Mapping): raise DFinalBoundLiveError("D_FINAL_DOC_NOT_OBJECT")
    return dict(raw)

def invoke(capability_id:str,payload:Mapping[str,Any])->dict[str,Any]:
    cid=str(capability_id or "").strip()
    if not cid.startswith("bound:") or not cid[6:]:
        raise DFinalBoundLiveError("D_FINAL_BOUND_ID_REQUIRED")
    if not isinstance(payload,Mapping):
        raise DFinalBoundLiveError("D_FINAL_BOUND_PAYLOAD_NOT_OBJECT")
    pf=gate.preflight(cid)
    reg=_doc(REGISTRY)
    row=next((dict(r) for r in reg["rows"] if isinstance(r,Mapping) and r.get("capability_id")==cid),None)
    if row is None: raise DFinalBoundLiveError("D_FINAL_BOUND_ROW_MISSING")
    live=dict(row["live_route_certificate"])
    cert=_doc(ROOT/str(live["certificate_path"]))
    policy=_doc(ROOT/str(live["policy_path"]))
    with d_epoch.activate(cert,policy=policy,repo_root=ROOT) as epoch:
        d_epoch.require_capability(cid)
        out=execute_bound(cid[6:],inputs=dict(payload))
        if out.get("pass") is not True:
            raise DFinalBoundLiveError("D_FINAL_BOUND_EXECUTION_FAILED")
        return {
          "schema":SCHEMA,
          "status":"PASS__D_FINAL_BOUND_LIVE_EXECUTION",
          "pass":True,
          "capability_id":cid,
          "certificate_sha256":epoch.certificate_sha256,
          "execution_epoch_sha256":epoch.epoch_sha256,
          "material_closure_root":epoch.material_closure_root,
          "preflight":pf,
          "result":out,
        }
