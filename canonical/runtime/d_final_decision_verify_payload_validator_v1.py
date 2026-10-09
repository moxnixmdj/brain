from __future__ import annotations
import hashlib,json
from pathlib import PurePosixPath
from typing import Any, Mapping

CELL_ID="D_FINAL_BOUND_DECISION_VERIFY_LIVE_V1"
EXPECTED_CONTEXT={
 "route_family":"D_FINAL_BOUND_LIVE_V1",
 "capability_id":"bound:decision.synthesis.verify.stdlib",
 "policy_semantic_version":"2026-10-09-live-v1",
}
PREFIX="canonical/astra_runtime/tmp/d-final-live/"

def _sha(value:Mapping[str,Any])->str:
    raw=json.dumps(dict(value),sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()

def _path(value:Any)->str:
    raw=str(value or "").replace("\\","/").strip()
    p=PurePosixPath(raw)
    if not raw.startswith(PREFIX) or p.is_absolute() or ".." in p.parts:
        raise ValueError("D_FINAL_DECISION_PAYLOAD_PATH_OUTSIDE_BOUNDARY")
    return raw

def validate(context:Mapping[str,Any],payload:Mapping[str,Any])->dict[str,Any]:
    if dict(context)!=EXPECTED_CONTEXT:
        raise ValueError("D_FINAL_DECISION_CONTEXT_MISMATCH")
    if set(payload)!={"input_path","result_path"}:
        raise ValueError("D_FINAL_DECISION_PAYLOAD_KEYS_INVALID")
    _path(payload.get("input_path"));_path(payload.get("result_path"))
    return {
      "admitted":True,
      "cell_id":CELL_ID,
      "context_digest_sha256":_sha(context),
      "payload_sha256":_sha(payload),
    }
