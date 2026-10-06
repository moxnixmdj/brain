from __future__ import annotations

import base64
import json
import os
import pathlib
import re
from collections.abc import Mapping
from typing import Any

from canonical.runtime import root3_typed_durable_admin_write_v1 as admin

SCHEMA="PROJECT_BRAIN_ROOT3_ADMIN_PERSISTENCE_DRIVER_V1"
KIND="DURABLE_ADMIN_WRITE"
_MISSION=re.compile(r"^[A-Za-z0-9_.-]{1,160}$")

class AdminPersistenceDenied(RuntimeError):
    pass

def _validate_mission_scope(
    mission_id:str,
    plan:Mapping[str,Any],
    payload:bytes,
)->None:
    mission=str(mission_id or "").strip()
    if _MISSION.fullmatch(mission) is None:
        raise AdminPersistenceDenied("MISSION_ID_INVALID")
    cls=str(plan.get("destination_class") or "")
    path=str(plan.get("path") or "")
    state=f"canonical/astra_runtime/state/{mission}.json"
    evid_prefix=f"canonical/astra_runtime/evidence/{mission}__"
    if cls=="ASTRA_STATE_JSON":
        if path!=state:
            raise AdminPersistenceDenied("STATE_PATH_NOT_CURRENT_MISSION")
        try:
            obj=json.loads(payload.decode("utf-8"))
        except Exception as exc:
            raise AdminPersistenceDenied("STATE_PAYLOAD_JSON_INVALID") from exc
        if (
            not isinstance(obj,dict)
            or obj.get("schema")!="PROJECT_BRAIN_ASTRA_RUNTIME_STATE_V1"
            or obj.get("mission_id")!=mission
        ):
            raise AdminPersistenceDenied("STATE_PAYLOAD_MISSION_BINDING_INVALID")
    elif cls=="ASTRA_EVIDENCE_JSON":
        if not path.startswith(evid_prefix) or not path.endswith(".json"):
            raise AdminPersistenceDenied("EVIDENCE_PATH_NOT_CURRENT_MISSION")
    elif cls=="ASTRA_EVIDENCE_JSONL":
        if not path.startswith(evid_prefix) or not path.endswith(".jsonl"):
            raise AdminPersistenceDenied("EVIDENCE_PATH_NOT_CURRENT_MISSION")
    else:
        raise AdminPersistenceDenied("ADMIN_DESTINATION_CLASS_INVALID")

def execute(
    *,
    repo_root:str|os.PathLike[str],
    mission_id:str,
    plan:Mapping[str,Any],
    payload_b64:str,
)->dict[str,Any]:
    if not isinstance(plan,Mapping):
        raise AdminPersistenceDenied("ADMIN_PLAN_INVALID")
    if not isinstance(payload_b64,str) or not payload_b64 or len(payload_b64)>12_000_000:
        raise AdminPersistenceDenied("ADMIN_PAYLOAD_INVALID")
    try:
        payload=base64.b64decode(payload_b64,validate=True)
    except Exception as exc:
        raise AdminPersistenceDenied("ADMIN_PAYLOAD_B64_INVALID") from exc
    _validate_mission_scope(mission_id,plan,payload)
    try:
        receipt=admin.commit(pathlib.Path(repo_root),plan,payload)
    except Exception as exc:
        raise AdminPersistenceDenied(
            "ADMIN_COMMIT_DENIED:"+type(exc).__name__+":"+str(exc)
        ) from exc
    if receipt.get("status")!="COMMITTED":
        raise AdminPersistenceDenied("ADMIN_COMMIT_RECEIPT_INVALID")
    return {
        "schema":SCHEMA,
        "status":"COMMITTED",
        "mission_id":mission_id,
        "receipt":receipt,
        "terminal_credit_delta":0,
    }
