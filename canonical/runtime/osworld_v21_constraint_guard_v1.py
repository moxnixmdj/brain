"""Explicit invariant guard for long OSWorld workflows.

Only constraints that are mechanically groundable to explicit guest paths are
accepted. The guard snapshots those paths, rejects candidate mutations that can
touch them, and re-verifies their byte identity before every later action.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Mapping

MAX_PROTECTED_PATHS=16
MAX_SNAPSHOT_BYTES=50_000_000

class ConstraintGuardError(RuntimeError):
    pass

_PATTERNS=(
    re.compile(r"(?:[,;]\s*)?(?:while\s+)?(?:keep|leave|preserve)\s+(/home/oai/[^\s,;]+)\s+(?:unchanged|intact|as[- ]is)",re.I),
    re.compile(r"(?:[,;]\s*)?(?:and\s+)?(?:do\s+not|don't|never)\s+(?:modify|change|edit|delete|remove|overwrite|touch)\s+(/home/oai/[^\s,;]+)",re.I),
    re.compile(r"(?:[,;]\s*)?without\s+(?:changing|modifying|editing|deleting|removing|overwriting|touching)\s+(/home/oai/[^\s,;]+)",re.I),
)

_MUTATING_STATE={"WRITE_TEXT","TEXT_REPLACE","DELETE","MOVE","JSON_SET","COPY"}
_MUTATING_CODE={"WRITE_TEXT_VERIFIED","REPLACE_TEXT_VERIFIED","PYTEST"}
_MUTATING_MEDIA={"TRIM","RESIZE","CROP","ROTATE","EXTRACT_AUDIO","SET_VOLUME"}

def _clean_path(value:str)->str:
    return value.rstrip(".,;:)]}").strip()

def extract_constraints(instruction:Any)->dict[str,Any]:
    if not isinstance(instruction,str) or not instruction.strip():
        raise ConstraintGuardError("INSTRUCTION_REQUIRED")
    spans=[]; paths=[]
    for pattern in _PATTERNS:
        for m in pattern.finditer(instruction):
            path=_clean_path(m.group(1))
            if ".." in path.split("/"):
                raise ConstraintGuardError("CONSTRAINT_PATH_TRAVERSAL")
            if path not in paths: paths.append(path)
            spans.append(m.span())
    if len(paths)>MAX_PROTECTED_PATHS:
        raise ConstraintGuardError("TOO_MANY_PROTECTED_PATHS")
    clean=instruction
    for a,b in sorted(spans,reverse=True):
        clean=clean[:a]+" "+clean[b:]
    clean=re.sub(r"\s+"," ",clean).strip(" ,;")
    return {
        "protected_paths":paths,
        "clean_instruction":clean,
        "constraint_sha256":hashlib.sha256(
            ("\n".join(sorted(paths))).encode("utf-8")
        ).hexdigest(),
    }

def _strings(value:Any):
    if isinstance(value,str):
        yield value
    elif isinstance(value,Mapping):
        for v in value.values(): yield from _strings(v)
    elif isinstance(value,list):
        for v in value: yield from _strings(v)

def _touches(value:Any,protected:list[str])->bool:
    for raw in _strings(value):
        for path in protected:
            if raw==path or raw.startswith(path+"/") or path.startswith(raw.rstrip("/")+"/"):
                return True
    return False

def action_conflict(action:Mapping[str,Any],protected:list[str])->str|None:
    if not protected or not isinstance(action,Mapping): return None
    kind=str(action.get("type") or "").strip().upper()

    if kind=="STATE_OPS":
        ops=action.get("ops")
        if not isinstance(ops,list): return "STATE_OPS_INVALID"
        for op in ops:
            if not isinstance(op,Mapping): return "STATE_OP_INVALID"
            typ=str(op.get("type") or op.get("op") or "").upper()
            if typ in _MUTATING_STATE and _touches(op,protected):
                return "PROTECTED_PATH_STATE_MUTATION"
        return None

    if kind=="CODE_OP":
        op=str(action.get("operation") or "").upper()
        args=action.get("args",{})
        if op in _MUTATING_CODE:
            if op=="PYTEST":
                cwd=str(args.get("cwd") or "") if isinstance(args,Mapping) else ""
                if any(p==cwd or p.startswith(cwd.rstrip("/")+"/") for p in protected if cwd):
                    return "PROTECTED_PATH_TEST_SIDE_EFFECT_RISK"
            elif _touches(args,protected):
                return "PROTECTED_PATH_CODE_MUTATION"
        return None

    if kind=="MEDIA_OP":
        op=str(action.get("operation") or "").upper()
        args=action.get("args",{})
        if op in _MUTATING_MEDIA and isinstance(args,Mapping):
            output=args.get("output")
            if isinstance(output,str) and _touches(output,protected):
                return "PROTECTED_PATH_MEDIA_OUTPUT"
        return None

    if kind in {"CLICK","DOUBLE_CLICK","RIGHT_CLICK","TYPE","PRESS","HOTKEY","DRAG_TO"}:
        return "UNBOUNDED_GUI_MUTATION_WITH_ACTIVE_PATH_INVARIANT"

    if kind=="APP_OP":
        return "APP_MUTATION_WITH_ACTIVE_PATH_INVARIANT"

    return None

@dataclass
class PathInvariantGuard:
    environment:Any|None=None
    ledger:dict[str,dict[str,Any]]|None=None

    def bind_environment(self,environment:Any)->None:
        ctl=getattr(environment,"controller",None)
        if ctl is None or not callable(getattr(ctl,"get_file",None)):
            raise ConstraintGuardError("GET_FILE_UNAVAILABLE")
        self.environment=environment

    def reset(self)->None:
        self.ledger=None

    def snapshot(self,paths:list[str])->dict[str,dict[str,Any]]:
        if self.environment is None:
            raise ConstraintGuardError("CONSTRAINT_ENVIRONMENT_NOT_BOUND")
        out={}
        for path in paths:
            raw=self.environment.controller.get_file(path)
            if raw is None:
                out[path]={"exists":False}
                continue
            if not isinstance(raw,(bytes,bytearray)):
                raise ConstraintGuardError("CONSTRAINT_FILE_READ_INVALID")
            data=bytes(raw)
            if len(data)>MAX_SNAPSHOT_BYTES:
                raise ConstraintGuardError("CONSTRAINT_FILE_TOO_LARGE")
            out[path]={"exists":True,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}
        self.ledger=out
        return out

    def verify(self)->dict[str,Any]:
        if self.environment is None or self.ledger is None:
            raise ConstraintGuardError("CONSTRAINT_LEDGER_NOT_READY")
        changed=[]
        for path,expected in self.ledger.items():
            raw=self.environment.controller.get_file(path)
            if raw is None:
                current={"exists":False}
            elif isinstance(raw,(bytes,bytearray)):
                data=bytes(raw)
                current={"exists":True,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}
            else:
                raise ConstraintGuardError("CONSTRAINT_FILE_READ_INVALID")
            if current!=expected:
                changed.append({"path":path,"expected":expected,"current":current})
        return {"pass":not changed,"changed":changed,"protected_count":len(self.ledger)}
