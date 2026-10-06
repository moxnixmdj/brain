#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import importlib
import json
import os
import pathlib
import re
import sys
from typing import Any, Mapping

REPO_ROOT=pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0,str(REPO_ROOT))

from canonical.runtime import root3_broker_rpc_v1 as rpc
from canonical.runtime import root3_strict_current_bootstrap_v2 as bootstrap
from canonical.runtime import root3_two_class_attempt_authorizer_v1 as attempt_authorizer

SCHEMA="PROJECT_BRAIN_ROOT3_CONFINED_ASTRA_ENTRY_V1"
_ID=re.compile(r"^[A-Za-z0-9_.-]{1,160}$")

class ConfinedEntryError(RuntimeError):
    pass

def _identity(value:Any,label:str)->str:
    text=str(value or "").strip()
    if _ID.fullmatch(text) is None:
        raise ConfinedEntryError(label+"_INVALID")
    return text

def _mission_identity(mission_path:pathlib.Path)->tuple[str,str,dict[str,Any]]:
    try:
        mission=json.loads(mission_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ConfinedEntryError("MISSION_JSON_INVALID") from exc
    if not isinstance(mission,dict):
        raise ConfinedEntryError("MISSION_OBJECT_REQUIRED")
    mission_id=_identity(mission.get("mission_id"),"MISSION_ID")
    agent=_identity(
        os.environ.get("PROJECT_BRAIN_AGENT_ID")
        or mission.get("agent_id")
        or "ASTRA-PARENT-MEMBRANE-V1",
        "AGENT_ID",
    )
    task=_identity(
        os.environ.get("PROJECT_BRAIN_TASK_ID")
        or mission.get("task_id")
        or mission_id,
        "TASK_ID",
    )
    return agent,task,mission

def _broker_fd()->int:
    raw=str(os.environ.get("PROJECT_BRAIN_BROKER_FD") or "").strip()
    try:
        fd=int(raw)
    except Exception as exc:
        raise ConfinedEntryError("BROKER_FD_INVALID") from exc
    if fd<3:
        raise ConfinedEntryError("BROKER_FD_INVALID")
    try:
        os.fstat(fd)
    except OSError as exc:
        raise ConfinedEntryError("BROKER_FD_NOT_OPEN") from exc
    return fd

def install_effect_transport(astra:Any,*,fd:int,agent_id:str,task_id:str)->dict[str,Any]:
    os.environ["PROJECT_BRAIN_AGENT_ID"]=agent_id
    os.environ["PROJECT_BRAIN_TASK_ID"]=task_id
    os.environ.pop("PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR",None)

    def broker_admin_commit(p,payload,destination_class,operation):
        path=pathlib.Path(p)
        raw=path if path.is_absolute() else astra.ROOT/path
        lex=pathlib.Path(os.path.abspath(raw))
        root_lex=pathlib.Path(os.path.abspath(astra.ROOT))
        try:
            rel=lex.relative_to(root_lex).as_posix()
        except ValueError as exc:
            raise astra.Blocker("TYPED_ADMIN_WRITE_PATH_OUTSIDE_ROOT") from exc
        mod=astra._load_runtime_helper("root3_typed_durable_admin_write_v1")
        plan=mod.build_plan(
            operation=operation,
            destination_class=destination_class,
            path=rel,
            payload=payload,
            expected_pre_sha256=astra._admin_expected_prestate(lex),
        )
        return rpc.call_fd(
            fd,
            kind="DURABLE_ADMIN_WRITE",
            agent_id=agent_id,
            task_id=task_id,
            payload={
                "plan":plan,
                "payload_b64":base64.b64encode(payload).decode("ascii"),
            },
        )

    def broker_external_tool(kind,payload):
        astra._authorize_external_information(kind,payload)
        result=rpc.call_fd(
            fd,
            kind="EXTERNAL_TOOL",
            agent_id=agent_id,
            task_id=task_id,
            payload={
                "tool_kind":str(kind),
                "tool_payload":dict(payload or {}),
            },
        )
        if not isinstance(result,dict):
            raise astra.Blocker("ROOT3_BROKER_EXTERNAL_RESULT_INVALID")
        return result

    astra._typed_admin_commit=broker_admin_commit
    astra._external_tool_bridge=broker_external_tool
    pong=rpc.call_fd(
        fd,kind="PING",agent_id=agent_id,task_id=task_id,payload={}
    )
    if pong.get("pong") is not True:
        raise ConfinedEntryError("BROKER_PING_FAILED")
    return {
        "schema":SCHEMA,
        "agent_id":agent_id,
        "task_id":task_id,
        "broker_ping":True,
        "external_tool_transport":"ROOT3_FD_BROKER",
        "durable_admin_transport":"ROOT3_FD_BROKER",
    }

def load_astra_inside_membrane()->Any:
    status=bootstrap.install_current(
        attempt_authorizer.authorize,
        authority_id=attempt_authorizer.AUTHORITY_ID,
    )
    if status.get("run_guard_active") is not True or status.get("popen_guard_active") is not True:
        raise ConfinedEntryError("ROOT3_SUBPROCESS_GUARDS_NOT_ACTIVE")
    astra=importlib.import_module("canonical.runtime.astra_runtime")
    observed=bootstrap.mediator.status()
    if observed.get("run_guard_active") is not True or observed.get("popen_guard_active") is not True:
        raise ConfinedEntryError("ROOT3_SUBPROCESS_GUARDS_LOST_AFTER_ASTRA_IMPORT")
    return astra

def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("mission")
    ns=ap.parse_args(argv)
    mission_path=pathlib.Path(ns.mission).resolve()
    root=REPO_ROOT.resolve()
    if mission_path!=root and root not in mission_path.parents:
        raise ConfinedEntryError("MISSION_OUTSIDE_CONFINED_REPO")
    agent,task,_=_mission_identity(mission_path)
    fd=_broker_fd()
    astra=load_astra_inside_membrane()
    install_effect_transport(astra,fd=fd,agent_id=agent,task_id=task)
    old=list(sys.argv)
    try:
        sys.argv=[str(astra.__file__),str(mission_path)]
        result=astra.main()
    finally:
        sys.argv=old
    return int(result or 0)

if __name__=="__main__":
    raise SystemExit(main())
