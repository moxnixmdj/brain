from __future__ import annotations

import base64
import os
import pathlib
from collections.abc import Mapping
from typing import Any

from canonical.runtime import root3_typed_durable_admin_write_v1 as admin

SCHEMA="PROJECT_BRAIN_ROOT3_ADMIN_PERSISTENCE_DRIVER_V1"
KIND="DURABLE_ADMIN_WRITE"

class AdminPersistenceDenied(RuntimeError):
    pass

def execute(
    *,
    repo_root:str|os.PathLike[str],
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
        "receipt":receipt,
        "terminal_credit_delta":0,
    }
