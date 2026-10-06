from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import time
from collections.abc import Mapping
from typing import Any

from canonical.runtime import continuous_obs_runtime as continuous_obs
from canonical.runtime import root3_admin_persistence_driver_v1 as admin_driver
from canonical.runtime import root3_parent_driver_registry_v1 as driver_registry
from canonical.runtime import root3_typed_durable_admin_write_v1 as admin_plan

EXTERNAL_REQUEST_SCHEMA="PROJECT_BRAIN_EXTERNAL_TOOL_REQUEST_V1"
EXTERNAL_RESPONSE_SCHEMA="PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1"
ALLOWED_KINDS=set(driver_registry.KINDS)

class ParentBrokerDenied(RuntimeError):
    pass

def _canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()

def _sha(v:Any)->str:
    return hashlib.sha256(_canon(v)).hexdigest()

def _token(v:Any,label:str,max_len:int=160)->str:
    s=str(v or "").strip()
    if not s or len(s)>max_len or "\x00" in s:
        raise ParentBrokerDenied(label+"_INVALID")
    return s

def _expected_prestate(path:pathlib.Path)->str:
    if path.is_symlink() or path.parent.is_symlink() or not path.exists():
        return "ABSENT"
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _validated_bridge_dir(repo_root:pathlib.Path,raw_dir:str,task_id:str)->pathlib.Path:
    root=repo_root.resolve(strict=True)
    task=_token(task_id,"TASK_ID")
    if re.fullmatch(r"[A-Za-z0-9_.-]{1,160}",task) is None:
        raise ParentBrokerDenied("TASK_ID_INVALID")
    base=(root/"canonical"/"same_identity_worker"/"external_tool_bridge").resolve()
    if base!=root and root not in base.parents:
        raise ParentBrokerDenied("BRIDGE_BASE_ESCAPES_REPOSITORY")
    raw=pathlib.Path(str(raw_dir or "").strip())
    if not raw.is_absolute():
        raw=root/raw
    if raw.exists() and raw.is_symlink():
        raise ParentBrokerDenied("BRIDGE_TASK_DIR_SYMLINK_FORBIDDEN")
    observed=raw.resolve()
    expected=(base/task).resolve()
    if observed!=expected or observed.parent!=base:
        raise ParentBrokerDenied("BRIDGE_DIR_IDENTITY_MISMATCH")
    observed.mkdir(parents=True,exist_ok=True)
    return observed

def _information_action(tool_kind:str,tool_payload:Mapping[str,Any])->dict[str,str]:
    raw_kind=str(tool_kind or "")
    if raw_kind in {"http_get","urlopen"}:
        action_kind="EXACT_FETCH"
        source=str(tool_payload.get("url") or "")
    elif raw_kind in {"package_name_search","python_source_tree","pypi_wheel_closure"}:
        action_kind="DISCOVERY_SEARCH"
        source=str(
            tool_payload.get("goal")
            or tool_payload.get("effect")
            or tool_payload.get("project")
            or raw_kind
        )
    elif raw_kind=="planner":
        action_kind="PLANNER"
        source="planner"
    else:
        action_kind="EXTERNAL_TOOL"
        source=raw_kind
    return {"kind":action_kind,"source":source,"tool_kind":raw_kind}

def relay_external_tool(
    *,
    repo_root:pathlib.Path,
    bridge_dir:str,
    agent_id:str,
    task_id:str,
    tool_kind:str,
    tool_payload:Mapping[str,Any],
    wait_seconds:float,
)->dict[str,Any]:
    if not isinstance(tool_payload,Mapping):
        raise ParentBrokerDenied("TOOL_PAYLOAD_INVALID")
    bridge=_validated_bridge_dir(repo_root,bridge_dir,task_id)
    request={
        "schema":EXTERNAL_REQUEST_SCHEMA,
        "kind":_token(tool_kind,"TOOL_KIND"),
        "agent_id":_token(agent_id,"AGENT_ID"),
        "task_id":_token(task_id,"TASK_ID"),
        "payload":dict(tool_payload),
    }
    request_sha256=_sha(request)
    request["request_sha256"]=request_sha256
    request_path=bridge/(request_sha256+".request.json")
    response_path=bridge/(request_sha256+".response.json")
    if request_path.exists():
        try:
            observed=json.loads(request_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ParentBrokerDenied("EXTERNAL_REQUEST_EXISTING_INVALID") from exc
        if observed!=request:
            raise ParentBrokerDenied("EXTERNAL_REQUEST_COLLISION")
    else:
        request_path.write_text(
            json.dumps(request,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
    wait=float(wait_seconds)
    if wait<0 or wait>300:
        raise ParentBrokerDenied("EXTERNAL_WAIT_INVALID")
    if not response_path.exists() and wait>0:
        deadline=time.monotonic()+wait
        while not response_path.exists():
            rem=deadline-time.monotonic()
            if rem<=0:
                break
            time.sleep(min(0.05,max(0.005,rem)))
    if not response_path.exists():
        raise ParentBrokerDenied("EXTERNAL_TOOL_REQUEST_PENDING:"+request_sha256)
    try:
        response=json.loads(response_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ParentBrokerDenied("EXTERNAL_RESPONSE_INVALID_JSON") from exc
    required={
        "schema","request_sha256","kind","agent_id","task_id","status","result"
    }
    if not isinstance(response,dict) or not required<=set(response):
        raise ParentBrokerDenied("EXTERNAL_RESPONSE_FIELDS_INVALID")
    if response.get("schema")!=EXTERNAL_RESPONSE_SCHEMA:
        raise ParentBrokerDenied("EXTERNAL_RESPONSE_SCHEMA_INVALID")
    if response.get("request_sha256")!=request_sha256:
        raise ParentBrokerDenied("EXTERNAL_RESPONSE_REQUEST_MISMATCH")
    for key in ("kind","agent_id","task_id"):
        if response.get(key)!=request.get(key):
            raise ParentBrokerDenied("EXTERNAL_RESPONSE_IDENTITY_MISMATCH:"+key)
    if response.get("status")!="ok" or not isinstance(response.get("result"),dict):
        raise ParentBrokerDenied("EXTERNAL_RESPONSE_FAILED")
    return dict(response["result"])

class ParentBroker:
    def __init__(
        self,
        *,
        repo_root:str|os.PathLike[str],
        expected_agent_id:str,
        expected_task_id:str,
        mission_id:str,
        information_context:Mapping[str,Any],
        external_bridge_dir:str|None=None,
        external_wait_seconds:float=0.0,
    ):
        self.repo_root=pathlib.Path(repo_root).resolve(strict=True)
        self.expected_agent_id=_token(expected_agent_id,"EXPECTED_AGENT_ID")
        self.expected_task_id=_token(expected_task_id,"EXPECTED_TASK_ID")
        self.mission_id=_token(mission_id,"MISSION_ID")
        if not isinstance(information_context,Mapping):
            raise ParentBrokerDenied("INFORMATION_CONTEXT_REQUIRED")
        self.information_context=dict(information_context)
        self.external_bridge_dir=external_bridge_dir
        self.external_wait_seconds=float(external_wait_seconds)
        self.receipts:list[dict[str,Any]]=[]

    def _check_identity(self,agent:str,task:str)->None:
        if agent!=self.expected_agent_id:
            raise ParentBrokerDenied("BROKER_AGENT_IDENTITY_MISMATCH")
        if task!=self.expected_task_id:
            raise ParentBrokerDenied("BROKER_TASK_IDENTITY_MISMATCH")

    def _append_information_admission(self,verdict:Mapping[str,Any])->dict[str,Any]:
        path=(
            self.repo_root/"canonical/astra_runtime/evidence"/
            (self.mission_id+"__ROOT3_PARENT_INFORMATION_ADMISSION.jsonl")
        )
        payload=(
            json.dumps(dict(verdict),sort_keys=True,separators=(",",":"))+"\n"
        ).encode("utf-8")
        rel=path.relative_to(self.repo_root).as_posix()
        plan=admin_plan.build_plan(
            operation="APPEND_JSONL",
            destination_class="ASTRA_EVIDENCE_JSONL",
            path=rel,
            payload=payload,
            expected_pre_sha256=_expected_prestate(path),
        )
        return admin_driver.execute(
            repo_root=self.repo_root,
            mission_id=self.mission_id,
            plan=plan,
            payload_b64=__import__("base64").b64encode(payload).decode("ascii"),
        )

    def _authorize_external(self,tool_kind:str,tool_payload:Mapping[str,Any])->dict[str,Any]:
        action=_information_action(tool_kind,tool_payload)
        verdict=continuous_obs.authorize_information_action(
            self.information_context,
            action,
            root=self.repo_root,
        )
        receipt={
            **dict(verdict),
            "mission_id":self.mission_id,
            "broker_authority":"PARENT_INDEPENDENT_CONTINUOUS_OBS",
        }
        self._append_information_admission(receipt)
        if verdict.get("pass") is not True:
            raise ParentBrokerDenied(
                "PARENT_INFORMATION_AUTHORIZATION_DENIED:"
                +"|".join(verdict.get("errors") or ["UNKNOWN"])
            )
        return receipt

    def handle(self,request:Mapping[str,Any])->dict[str,Any]:
        kind=str(request.get("kind") or "")
        agent=_token(request.get("agent_id"),"AGENT_ID")
        task=_token(request.get("task_id"),"TASK_ID")
        self._check_identity(agent,task)
        payload=request.get("payload")
        if not isinstance(payload,Mapping):
            raise ParentBrokerDenied("BROKER_PAYLOAD_INVALID")

        def ping_driver(_payload):
            return {"pong":True}

        def external_driver(driver_payload):
            tool_kind=_token(driver_payload.get("tool_kind"),"TOOL_KIND")
            tool_payload=driver_payload.get("tool_payload") or {}
            if not isinstance(tool_payload,Mapping):
                raise ParentBrokerDenied("TOOL_PAYLOAD_INVALID")
            self._authorize_external(tool_kind,tool_payload)
            if not self.external_bridge_dir:
                raise ParentBrokerDenied("EXTERNAL_BRIDGE_NOT_CONFIGURED")
            return relay_external_tool(
                repo_root=self.repo_root,
                bridge_dir=self.external_bridge_dir,
                agent_id=agent,
                task_id=task,
                tool_kind=tool_kind,
                tool_payload=tool_payload,
                wait_seconds=self.external_wait_seconds,
            )

        def admin_persistence_driver(driver_payload):
            try:
                out=admin_driver.execute(
                    repo_root=self.repo_root,
                    mission_id=self.mission_id,
                    plan=driver_payload.get("plan") or {},
                    payload_b64=driver_payload.get("payload_b64"),
                )
            except Exception as exc:
                raise ParentBrokerDenied(
                    type(exc).__name__+":"+str(exc)
                ) from exc
            receipt=out.get("receipt")
            if not isinstance(receipt,dict) or receipt.get("status")!="COMMITTED":
                raise ParentBrokerDenied("ADMIN_DRIVER_RECEIPT_INVALID")
            return receipt

        drivers={
            "PING":ping_driver,
            "EXTERNAL_TOOL":external_driver,
            "DURABLE_ADMIN_WRITE":admin_persistence_driver,
        }
        try:
            result=driver_registry.dispatch(drivers,kind,payload)
        except Exception as exc:
            raise ParentBrokerDenied(type(exc).__name__+":"+str(exc)) from exc
        receipt={
            "request_sha256":request.get("request_sha256"),
            "kind":kind,
            "agent_id":agent,
            "task_id":task,
            "result_sha256":_sha(result),
        }
        self.receipts.append(receipt)
        return result

    def summary(self)->dict[str,Any]:
        return {
            "request_count":len(self.receipts),
            "kinds":sorted({x["kind"] for x in self.receipts}),
            "receipts":list(self.receipts),
            "expected_agent_id":self.expected_agent_id,
            "expected_task_id":self.expected_task_id,
            "mission_id":self.mission_id,
        }
