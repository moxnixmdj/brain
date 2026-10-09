from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime import d_finality_execution_epoch_v1 as d_epoch

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/"canonical/governance/D_FINALITY_CERTIFICATE_REGISTRY_V1.json"
SCHEMA="PROJECT_BRAIN_D_FINAL_LIVE_GATE_V1"

class DFinalLiveGateError(ValueError): pass

def _obj(path:Path)->dict[str,Any]:
    raw=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw,Mapping): raise DFinalLiveGateError("D_FINAL_NOT_OBJECT")
    return dict(raw)

def _path(raw:Any)->Path:
    root=ROOT.resolve(); p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents: raise DFinalLiveGateError("D_FINAL_PATH_OUTSIDE_ROOT")
    return p

def preflight(capability_id:str)->dict[str,Any]:
    cid=str(capability_id or "").strip()
    if not cid: raise DFinalLiveGateError("D_FINAL_CAPABILITY_ID_REQUIRED")
    reg=_obj(REGISTRY)
    if reg.get("schema")!="PROJECT_BRAIN_D_FINALITY_CERTIFICATE_REGISTRY_V1" or reg.get("status")!="ACTIVE_FAIL_CLOSED":
        raise DFinalLiveGateError("D_FINAL_REGISTRY_INVALID")
    rows=[r for r in reg.get("rows",[]) if isinstance(r,Mapping) and r.get("capability_id")==cid]
    if len(rows)!=1: raise DFinalLiveGateError("D_FINAL_LIVE_ROW_MISSING_OR_AMBIGUOUS:"+cid)
    row=dict(rows[0]); live=row.get("live_route_certificate")
    if not isinstance(live,Mapping):
        if isinstance(row.get("replay_route_certificate"),Mapping):
            raise DFinalLiveGateError("D_FINAL_REPLAY_CERTIFICATE_NOT_LIVE_AUTHORITY:"+cid)
        raise DFinalLiveGateError("D_FINAL_LIVE_CERTIFICATE_REQUIRED:"+cid)
    if live.get("status")!="VERIFIED_D_FINAL_CURRENT":
        raise DFinalLiveGateError("D_FINAL_LIVE_CERTIFICATE_NOT_CURRENT:"+cid)
    cert=_obj(_path(live.get("certificate_path"))); policy=_obj(_path(live.get("policy_path")))
    if cert.get("capability_id")!=cid: raise DFinalLiveGateError("D_FINAL_CERTIFICATE_CAPABILITY_MISMATCH")
    if cert.get("scope")!="LIVE_FRONT_DOOR" or cert.get("live_front_door_enforced") is not True or cert.get("live_ownership_authority") is not True:
        raise DFinalLiveGateError("D_FINAL_CERTIFICATE_NOT_LIVE_AUTHORITY")
    epoch=d_epoch.verify_certificate(cert,policy=policy,repo_root=ROOT)
    if live.get("certificate_sha256")!=epoch.certificate_sha256: raise DFinalLiveGateError("D_FINAL_CERTIFICATE_HASH_MISMATCH")
    if live.get("execution_epoch_sha256")!=epoch.epoch_sha256: raise DFinalLiveGateError("D_FINAL_EPOCH_HASH_MISMATCH")
    return {"schema":SCHEMA,"pass":True,"status":"PASS__CURRENT_LIVE_D_FINAL_CERTIFICATE","capability_id":cid,"certificate_sha256":epoch.certificate_sha256,"execution_epoch_sha256":epoch.epoch_sha256}
