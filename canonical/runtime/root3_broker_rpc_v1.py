from __future__ import annotations

import hashlib
import json
import os
import socket
import struct
import threading
from collections.abc import Mapping
from typing import Any, Callable

REQUEST_SCHEMA="PROJECT_BRAIN_ROOT3_BROKER_REQUEST_V1"
RESPONSE_SCHEMA="PROJECT_BRAIN_ROOT3_BROKER_RESPONSE_V1"
MAX_FRAME=8_500_000
_HEADER=struct.Struct("!I")
_client_lock=threading.Lock()

class BrokerProtocolError(RuntimeError):
    pass

def _canon(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")

def _sha(value:Any)->str:
    return hashlib.sha256(_canon(value)).hexdigest()

def _send(sock:socket.socket,value:Mapping[str,Any])->None:
    raw=_canon(value)
    if not raw or len(raw)>MAX_FRAME:
        raise BrokerProtocolError("FRAME_SIZE_INVALID")
    sock.sendall(_HEADER.pack(len(raw))+raw)

def _recvn(sock:socket.socket,n:int)->bytes:
    out=bytearray()
    while len(out)<n:
        chunk=sock.recv(n-len(out))
        if not chunk:
            raise BrokerProtocolError("FRAME_TRUNCATED")
        out.extend(chunk)
    return bytes(out)

def _recv(sock:socket.socket)->dict[str,Any]:
    header=_recvn(sock,_HEADER.size)
    (size,)=_HEADER.unpack(header)
    if size<2 or size>MAX_FRAME:
        raise BrokerProtocolError("FRAME_SIZE_INVALID")
    raw=_recvn(sock,size)
    try:
        value=json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise BrokerProtocolError("FRAME_JSON_INVALID") from exc
    if not isinstance(value,dict):
        raise BrokerProtocolError("FRAME_OBJECT_REQUIRED")
    return value

def build_request(*,kind:str,agent_id:str,task_id:str,payload:Mapping[str,Any])->dict[str,Any]:
    kind=str(kind or "").strip()
    agent=str(agent_id or "").strip()
    task=str(task_id or "").strip()
    if not kind or len(kind)>160:
        raise BrokerProtocolError("KIND_INVALID")
    if not agent or len(agent)>160 or not task or len(task)>160:
        raise BrokerProtocolError("IDENTITY_INVALID")
    if not isinstance(payload,Mapping):
        raise BrokerProtocolError("PAYLOAD_OBJECT_REQUIRED")
    core={
        "schema":REQUEST_SCHEMA,
        "kind":kind,
        "agent_id":agent,
        "task_id":task,
        "payload":dict(payload),
    }
    return {**core,"request_sha256":_sha(core)}

def validate_request(value:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(value,Mapping) or set(value)!={
        "schema","kind","agent_id","task_id","payload","request_sha256"
    }:
        raise BrokerProtocolError("REQUEST_FIELDS_INVALID")
    rebuilt=build_request(
        kind=value.get("kind"),
        agent_id=value.get("agent_id"),
        task_id=value.get("task_id"),
        payload=value.get("payload"),
    )
    if dict(value)!=rebuilt:
        raise BrokerProtocolError("REQUEST_HASH_MISMATCH")
    return rebuilt

def build_response(request:Mapping[str,Any],*,status:str,result:Mapping[str,Any]|None=None,error:str|None=None)->dict[str,Any]:
    req=validate_request(request)
    status=str(status or "")
    if status not in {"ok","error"}:
        raise BrokerProtocolError("RESPONSE_STATUS_INVALID")
    if status=="ok":
        if not isinstance(result,Mapping) or error is not None:
            raise BrokerProtocolError("RESPONSE_RESULT_INVALID")
        result_obj=dict(result)
        error_value=None
    else:
        if result is not None or not isinstance(error,str) or not error:
            raise BrokerProtocolError("RESPONSE_ERROR_INVALID")
        result_obj=None
        error_value=error[:2000]
    core={
        "schema":RESPONSE_SCHEMA,
        "request_sha256":req["request_sha256"],
        "kind":req["kind"],
        "agent_id":req["agent_id"],
        "task_id":req["task_id"],
        "status":status,
        "result":result_obj,
        "error":error_value,
    }
    return {**core,"response_sha256":_sha(core)}

def validate_response(request:Mapping[str,Any],value:Mapping[str,Any])->dict[str,Any]:
    req=validate_request(request)
    if not isinstance(value,Mapping) or set(value)!={
        "schema","request_sha256","kind","agent_id","task_id",
        "status","result","error","response_sha256"
    }:
        raise BrokerProtocolError("RESPONSE_FIELDS_INVALID")
    if value.get("schema")!=RESPONSE_SCHEMA:
        raise BrokerProtocolError("RESPONSE_SCHEMA_INVALID")
    for key in ("request_sha256","kind","agent_id","task_id"):
        if value.get(key)!=req.get(key):
            raise BrokerProtocolError("RESPONSE_BINDING_MISMATCH:"+key)
    core={k:value[k] for k in value if k!="response_sha256"}
    if value.get("response_sha256")!=_sha(core):
        raise BrokerProtocolError("RESPONSE_HASH_MISMATCH")
    status=value.get("status")
    if status=="ok":
        if not isinstance(value.get("result"),dict) or value.get("error") is not None:
            raise BrokerProtocolError("RESPONSE_RESULT_INVALID")
    elif status=="error":
        if value.get("result") is not None or not isinstance(value.get("error"),str) or not value.get("error"):
            raise BrokerProtocolError("RESPONSE_ERROR_INVALID")
    else:
        raise BrokerProtocolError("RESPONSE_STATUS_INVALID")
    return dict(value)

def call_fd(fd:int,*,kind:str,agent_id:str,task_id:str,payload:Mapping[str,Any])->dict[str,Any]:
    try:
        raw_fd=int(fd)
    except Exception as exc:
        raise BrokerProtocolError("BROKER_FD_INVALID") from exc
    request=build_request(kind=kind,agent_id=agent_id,task_id=task_id,payload=payload)
    with _client_lock:
        sock=socket.socket(fileno=os.dup(raw_fd))
        try:
            _send(sock,request)
            response=_recv(sock)
        finally:
            sock.close()
    checked=validate_response(request,response)
    if checked["status"]!="ok":
        raise BrokerProtocolError("BROKER_REQUEST_FAILED:"+checked["error"])
    return dict(checked["result"])

def serve_socket(sock:socket.socket,handler:Callable[[dict[str,Any]],Mapping[str,Any]])->dict[str,Any]:
    count=0
    last=None
    while True:
        try:
            request=_recv(sock)
        except BrokerProtocolError as exc:
            if str(exc)=="FRAME_TRUNCATED":
                break
            raise
        checked=validate_request(request)
        try:
            result=handler(checked)
            if not isinstance(result,Mapping):
                raise BrokerProtocolError("HANDLER_RESULT_OBJECT_REQUIRED")
            response=build_response(checked,status="ok",result=dict(result))
        except Exception as exc:
            response=build_response(
                checked,status="error",error=type(exc).__name__+":"+str(exc)
            )
        _send(sock,response)
        count+=1
        last=checked["request_sha256"]
    return {"request_count":count,"last_request_sha256":last}
