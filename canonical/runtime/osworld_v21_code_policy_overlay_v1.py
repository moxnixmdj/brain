"""Deterministic code/workspace routing for the model-independent OSWorld subject."""
from __future__ import annotations
import re
from pathlib import PurePosixPath
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_OSWORLD_V21_CODE_POLICY_OVERLAY_V1"

def _history(state:Mapping[str,Any]):
    raw=state.get("history")
    return [x for x in raw if isinstance(x,Mapping)] if isinstance(raw,list) else []

def _path(text:str):
    hits=re.findall(r"/home/oai/[A-Za-z0-9_./-]+",text)
    hits=[x.rstrip(".,;)") for x in hits]
    uniq=[]
    for x in hits:
        if x not in uniq: uniq.append(x)
    return uniq[0] if len(uniq)==1 else None

def _quoted(text:str):
    return [x.strip() for x in re.findall(r'"([^"]*)"',text) if x.strip()]

def _emit(op:str,args:Mapping[str,Any],response:str):
    return {
        "response":response,
        "actions":[{"type":"CODE_OP","operation":op,"args":dict(args)}],
        "_policy_receipt":{
            "schema":SCHEMA,"route":"GENERIC_CODE_WORKSPACE_OPERATION",
            "operation":op,"task_specific_policy_data":False,
            "external_model_dependency":False,
        },
    }

def _latest(state:Mapping[str,Any]):
    for row in reversed(_history(state)):
        sub=row.get("submitted_code_operation")
        res=row.get("code_result")
        if isinstance(sub,Mapping) and isinstance(res,Mapping):
            return sub,res
    return None,None

def _finish(state:Mapping[str,Any],candidate:Mapping[str,Any]):
    action=candidate["actions"][0]
    sub,res=_latest(state)
    if (
        isinstance(sub,Mapping) and isinstance(res,Mapping) and res.get("ok") is True
        and action.get("operation")==sub.get("operation")
        and dict(action.get("args") or {})==dict(sub.get("args") or {})
    ):
        return {
            "response":"code operation postcondition verified",
            "actions":[{"type":"DONE"}],
            "_policy_receipt":{
                "schema":SCHEMA,"route":"GENERIC_CODE_WORKSPACE_OPERATION_VERIFIED",
                "operation":action.get("operation"),"task_specific_policy_data":False,
                "external_model_dependency":False,
            },
        }
    return candidate

def route_code(state:Mapping[str,Any]):
    instruction=state.get("instruction")
    if not isinstance(instruction,str) or not instruction.strip():
        return None
    low=instruction.casefold()
    path=_path(instruction)
    if path is None:
        return None

    if "replace" in low and " with " in low:
        vals=_quoted(instruction)
        if len(vals)==2:
            return _finish(state,_emit(
                "REPLACE_TEXT_VERIFIED",
                {"path":path,"old":vals[0],"new":vals[1],"replace_all":True},
                "replace exact workspace text and verify readback",
            ))

    if re.search(r"\b(create|write|save)\b",low):
        vals=[x for x in _quoted(instruction) if x!=path]
        if len(vals)==1 and re.search(r"\b(containing|content|text|with)\b",low):
            return _finish(state,_emit(
                "WRITE_TEXT_VERIFIED",{"path":path,"text":vals[0]},
                "write workspace file and verify readback",
            ))

    if re.search(r"\b(run|execute)\b.*\b(pytest|tests?|test suite)\b",low):
        p=PurePosixPath(path)
        args={"cwd":str(p.parent),"target":p.name} if p.suffix else {"cwd":str(p)}
        return _finish(state,_emit("PYTEST",args,"run bounded workspace tests"))

    if re.search(r"\b(compile|syntax check|check syntax|verify syntax)\b",low) and path.endswith(".py"):
        return _finish(state,_emit("PYTHON_COMPILE",{"path":path},"compile Python source"))

    if "git status" in low:
        p=PurePosixPath(path)
        cwd=str(p.parent) if p.suffix else str(p)
        return _finish(state,_emit("GIT_STATUS",{"cwd":cwd},"inspect repository status"))

    if re.search(r"\b(read|inspect|show|review)\b",low):
        return _finish(state,_emit("READ_TEXT",{"path":path,"max_chars":12000},"read workspace text"))

    return None
