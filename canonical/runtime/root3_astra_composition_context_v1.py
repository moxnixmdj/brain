"""Recover the real current ASTRA composition identity from the live call stack.

This is intentionally narrow: only the exact content-addressed ASTRA runtime,
inside its model-independent composition loop, with an active composition row and
capsule may produce an artifact-finalization identity. Any other caller denies.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import re
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
ASTRA_REL="canonical/runtime/astra_runtime.py"
EXPECTED_ASTRA_BLOB="15dd59ad644c5c73a9218dba4fcc17f880d725f0"
SHA256_RE=re.compile(r"^[0-9a-f]{64}$")
REQUIRED_FRAME_NAMES=(
    "_invoke_bound_capability",
    "_goal_action",
    "_run_model_independent_goal",
)

class CompositionContextDenied(PermissionError):
    pass

def _blob(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _token(value:Any,label:str,max_len:int=512)->str:
    if not isinstance(value,str) or not value.strip() or len(value)>max_len or "\x00" in value:
        raise CompositionContextDenied(label+"_INVALID")
    return value.strip()

def _canon(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")

def validate_values(
    *,
    mission: Mapping[str,Any],
    composition_capsule: Mapping[str,Any],
    composition_row: Mapping[str,Any],
    action: Mapping[str,Any],
    cycle: int,
)->dict[str,Any]:
    if not isinstance(mission,Mapping):
        raise CompositionContextDenied("MISSION_CONTEXT_MISSING")
    if not isinstance(composition_capsule,Mapping):
        raise CompositionContextDenied("COMPOSITION_CAPSULE_MISSING")
    if not isinstance(composition_row,Mapping):
        raise CompositionContextDenied("COMPOSITION_ROW_MISSING")
    if not isinstance(action,Mapping):
        raise CompositionContextDenied("ACTION_CONTEXT_MISSING")
    mission_id=_token(mission.get("mission_id"),"MISSION_ID",256)
    head=_token(composition_capsule.get("head_hash"),"CAPSULE_HEAD_SHA256",64)
    if SHA256_RE.fullmatch(head) is None:
        raise CompositionContextDenied("CAPSULE_HEAD_SHA256_INVALID")
    if not isinstance(cycle,int) or isinstance(cycle,bool) or cycle<0:
        raise CompositionContextDenied("CYCLE_INVALID")
    action_sha=hashlib.sha256(_canon(dict(action))).hexdigest()
    row_sha=hashlib.sha256(_canon(dict(composition_row))).hexdigest()
    return {
        "mission_id":mission_id,
        "capsule_head_sha256":head,
        "action_sha256":action_sha,
        "composition_row_sha256":row_sha,
        "cycle":cycle,
        "action_ref":"composition:"+str(cycle)+":"+action_sha[:16],
    }

def capture()->dict[str,Any]:
    astra_path=(ROOT/ASTRA_REL).resolve()
    if _blob(astra_path)!=EXPECTED_ASTRA_BLOB:
        raise CompositionContextDenied("ASTRA_RUNTIME_BLOB_DRIFT")
    frame=inspect.currentframe()
    found={}
    try:
        cursor=frame.f_back if frame else None
        while cursor is not None:
            try:
                path=Path(cursor.f_code.co_filename).resolve()
            except Exception:
                path=None
            if path==astra_path and cursor.f_code.co_name in REQUIRED_FRAME_NAMES:
                found.setdefault(cursor.f_code.co_name,cursor)
            cursor=cursor.f_back
        if set(found)!=set(REQUIRED_FRAME_NAMES):
            raise CompositionContextDenied(
                "ASTRA_COMPOSITION_FRAME_CHAIN_INCOMPLETE:"+",".join(sorted(found))
            )
        outer=found["_run_model_independent_goal"]
        invoke=found["_invoke_bound_capability"]
        goal=found["_goal_action"]
        if invoke.f_back is not goal:
            raise CompositionContextDenied("BOUND_CAPABILITY_NOT_DIRECTLY_UNDER_GOAL_ACTION")
        # The goal action may have small helper frames beneath the controller, but
        # the controller itself must be present and own the live composition state.
        values=validate_values(
            mission=outer.f_locals.get("mission"),
            composition_capsule=outer.f_locals.get("composition_capsule"),
            composition_row=outer.f_locals.get("composition_row"),
            action=outer.f_locals.get("action"),
            cycle=outer.f_locals.get("cycle"),
        )
        step=outer.f_locals.get("step")
        if not isinstance(step,Mapping) or step.get("_composition_capsule_enforced") is not True:
            raise CompositionContextDenied("COMPOSITION_CAPSULE_ENFORCEMENT_NOT_ACTIVE")
        return {
            **values,
            "astra_runtime_path":ASTRA_REL,
            "astra_runtime_git_blob_sha":EXPECTED_ASTRA_BLOB,
            "frame_chain":list(REQUIRED_FRAME_NAMES),
        }
    finally:
        found.clear()
        del frame
