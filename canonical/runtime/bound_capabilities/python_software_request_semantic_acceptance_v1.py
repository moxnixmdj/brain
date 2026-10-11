"""One-sided sound semantic acceptance cells for explicit Python software requests.

Every non-whitespace raw-task segment is preserved by the lossless raw-task
contract. This compiler recognizes only a small exact grammar whose meaning can
be rendered into deterministic executable checks. Unsupported or ambiguous
segments remain blocking residuals.

This is intentionally not a general natural-language interpreter.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import re
import sys
from typing import Any

SCHEMA="PROJECT_BRAIN_PYTHON_SOFTWARE_REQUEST_SEMANTIC_ACCEPTANCE_V1"
MODEL_DEPENDENCY_COUNT=0
EXTERNAL_MODEL_RUNTIME_CALLS=0

class SemanticAcceptanceError(RuntimeError):
    pass

def _load_lossless():
    path=pathlib.Path(__file__).resolve().parent.parent/"lossless_raw_task_contract_v1.py"
    spec=importlib.util.spec_from_file_location("_brain_v9_lossless",path)
    if spec is None or spec.loader is None:
        raise SemanticAcceptanceError("LOSSLESS_CONTRACT_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

_LOSSLESS=_load_lossless()

def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)

def _sha(v:Any)->str:
    if isinstance(v,bytes):
        raw=v
    elif isinstance(v,str):
        raw=v.encode("utf-8")
    else:
        raw=_canon(v).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

_CALL=r"([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)"
_QJSON=r'("(?:\\.|[^"\\])*")'
_CALL_EQ=re.compile(r"^Calling\s+"+_CALL+r"\s+with JSON arguments\s+(\[[\s\S]*\])\s+must equal\s+([\s\S]+?)[.!?]?$")
_CALL_BOOL=re.compile(r"^Calling\s+"+_CALL+r"\s+with JSON arguments\s+(\[[\s\S]*\])\s+must be\s+(true|false)[.!?]?$",re.IGNORECASE)
_CALL_RAISES=re.compile(r"^Calling\s+"+_CALL+r"\s+with JSON arguments\s+(\[[\s\S]*\])\s+must raise\s+([A-Za-z_]\w*)[.!?]?$")
_FILE_CONTAINS=re.compile(r"^File\s+"+_QJSON+r"\s+must contain exact text\s+"+_QJSON+r"[.!?]?$")
_FUNC_EXISTS=re.compile(r"^Python function\s+([A-Za-z_]\w*)\s+must exist in file\s+"+_QJSON+r"[.!?]?$")
_CLASS_EXISTS=re.compile(r"^Python class\s+([A-Za-z_]\w*)\s+must exist in file\s+"+_QJSON+r"[.!?]?$")

def _json(raw:str,label:str)->Any:
    try:
        return json.loads(raw)
    except Exception as exc:
        raise SemanticAcceptanceError(label+"_JSON_INVALID") from exc

def _call_parts(callable_name:str)->tuple[str,str]:
    module,function=callable_name.rsplit(".",1)
    return module,function

def _cell(obligation_id:str,kind:str,spec:dict[str,Any])->dict[str,Any]:
    payload={"obligation_id":obligation_id,"kind":kind,"spec":spec}
    return {**payload,"cell_id":"SEMCELL:"+_sha(payload)}

def _compile_segment(text:str,obligation_id:str)->dict[str,Any]|None:
    s=text.strip()
    m=_CALL_BOOL.match(s)
    if m:
        callable_name,args_raw,value_raw=m.groups()
        args=_json(args_raw,"CALL_ARGS")
        if not isinstance(args,list):
            raise SemanticAcceptanceError("CALL_ARGS_NOT_ARRAY")
        module,function=_call_parts(callable_name)
        return _cell(obligation_id,"PYTHON_CALL_EQUALS",{
            "module":module,"function":function,"args":args,
            "expected":value_raw.lower()=="true",
        })
    m=_CALL_RAISES.match(s)
    if m:
        callable_name,args_raw,exc_name=m.groups()
        args=_json(args_raw,"CALL_ARGS")
        if not isinstance(args,list):
            raise SemanticAcceptanceError("CALL_ARGS_NOT_ARRAY")
        module,function=_call_parts(callable_name)
        return _cell(obligation_id,"PYTHON_CALL_RAISES_BUILTIN",{
            "module":module,"function":function,"args":args,"exception":exc_name,
        })
    m=_CALL_EQ.match(s)
    if m:
        callable_name,args_raw,expected_raw=m.groups()
        args=_json(args_raw,"CALL_ARGS")
        expected=_json(expected_raw,"CALL_EXPECTED")
        if not isinstance(args,list):
            raise SemanticAcceptanceError("CALL_ARGS_NOT_ARRAY")
        module,function=_call_parts(callable_name)
        return _cell(obligation_id,"PYTHON_CALL_EQUALS",{
            "module":module,"function":function,"args":args,"expected":expected,
        })
    m=_FILE_CONTAINS.match(s)
    if m:
        path_raw,text_raw=m.groups()
        return _cell(obligation_id,"FILE_TEXT_CONTAINS_EXACT",{
            "path":_json(path_raw,"FILE_PATH"),
            "text":_json(text_raw,"FILE_TEXT"),
        })
    m=_FUNC_EXISTS.match(s)
    if m:
        name,path_raw=m.groups()
        return _cell(obligation_id,"PYTHON_TOP_LEVEL_FUNCTION_EXISTS",{
            "path":_json(path_raw,"FUNCTION_PATH"),"name":name,
        })
    m=_CLASS_EXISTS.match(s)
    if m:
        name,path_raw=m.groups()
        return _cell(obligation_id,"PYTHON_TOP_LEVEL_CLASS_EXISTS",{
            "path":_json(path_raw,"CLASS_PATH"),"name":name,
        })
    return None

def compile_request(task_text:str)->dict[str,Any]:
    contract=_LOSSLESS.compile_contract(
        task_text,
        source_id="PYTHON_SOFTWARE_REQUEST_SEMANTIC_ACCEPTANCE_V1",
        routing_target_effects=[],
        semantic_goal_contract=None,
    )
    if contract.get("pass") is not True:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
            "errors":["LOSSLESS_RAW_TASK_CONTRACT_FAILED"],
            "terminal_authority":False,
        }
    obligations=((contract.get("acceptance_contract") or {}).get("obligations") or [])
    cells=[]
    residual=[]
    errors=[]
    for row in obligations:
        oid=str(row.get("obligation_id") or "")
        text=str(row.get("text") or "")
        try:
            cell=_compile_segment(text,oid)
        except Exception as exc:
            cell=None
            errors.append({"obligation_id":oid,"error":type(exc).__name__+":"+str(exc)})
        if cell is None:
            residual.append(oid)
        else:
            cells.append(cell)
    required=[str(x.get("obligation_id")) for x in obligations]
    compiled=[x["obligation_id"] for x in cells]
    if set(compiled).intersection(residual) or set(compiled)|set(residual)!=set(required):
        raise SemanticAcceptanceError("OBLIGATION_PARTITION_INVALID")
    payload={
        "task_sha256":contract.get("task_sha256"),
        "required_obligation_ids":required,
        "cells":cells,
        "residual_obligation_ids":residual,
    }
    return {
        "schema":SCHEMA,
        "status":"COMPILED__ALL_RAW_SEGMENTS_HAVE_EXECUTABLE_SEMANTIC_CELLS" if not residual else "OPEN__SEMANTIC_RESIDUALS",
        "pass":not residual and not errors,
        "coverage_complete":not residual and not errors,
        "task_sha256":contract.get("task_sha256"),
        "lossless_task_contract_sha256":contract.get("task_contract_sha256"),
        "required_obligation_ids":required,
        "compiled_obligation_ids":compiled,
        "residual_obligation_ids":residual,
        "cells":cells,
        "compile_errors":errors,
        "compiler_payload_sha256":_sha(payload),
        "model_dependency_count":0,
        "external_general_purpose_model_runtime_dependency_count":0,
        "incremental_spend_usd":0,
        "terminal_authority":False,
        "hard_nonclaims":[
            "SUPPORTED_GRAMMAR_IS_NOT_GENERAL_NATURAL_LANGUAGE",
            "UNMATCHED_OR_INVALID_SEGMENTS_REMAIN_BLOCKING_RESIDUALS",
            "CELL_COMPILATION_DOES_NOT_PROVE_THE_CANDIDATE_PASSES",
            "NO_FRONTIERCODE_SCORE_OR_TERMINAL_AUTHORITY",
        ],
    }

def render_test(compilation:dict[str,Any])->str:
    if compilation.get("coverage_complete") is not True:
        raise SemanticAcceptanceError("SEMANTIC_COVERAGE_INCOMPLETE")
    cells=compilation.get("cells")
    if not isinstance(cells,list) or not cells:
        raise SemanticAcceptanceError("SEMANTIC_CELLS_REQUIRED")
    blob=_canon(cells)
    return """from __future__ import annotations
import ast,builtins,importlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
CELLS=json.loads(%r)
def safe_path(raw):
    p=(ROOT/str(raw)).resolve()
    if p==ROOT or ROOT not in p.parents or not p.is_file() or p.is_symlink():
        raise AssertionError("SEMANTIC_PATH_INVALID:"+str(raw))
    return p
for cell in CELLS:
    kind=cell["kind"];spec=cell["spec"];cid=cell["cell_id"]
    if kind=="PYTHON_CALL_EQUALS":
        mod=importlib.import_module(spec["module"])
        fn=getattr(mod,spec["function"])
        actual=fn(*spec["args"])
        assert actual==spec["expected"],cid
    elif kind=="PYTHON_CALL_RAISES_BUILTIN":
        exc=getattr(builtins,spec["exception"],None)
        assert isinstance(exc,type) and issubclass(exc,BaseException),cid
        mod=importlib.import_module(spec["module"])
        fn=getattr(mod,spec["function"])
        try:
            fn(*spec["args"])
        except exc:
            pass
        except BaseException as got:
            raise AssertionError(cid+":WRONG_EXCEPTION:"+type(got).__name__) from got
        else:
            raise AssertionError(cid+":EXPECTED_EXCEPTION_NOT_RAISED")
    elif kind=="FILE_TEXT_CONTAINS_EXACT":
        text=safe_path(spec["path"]).read_text(encoding="utf-8")
        assert spec["text"] in text,cid
    elif kind in {"PYTHON_TOP_LEVEL_FUNCTION_EXISTS","PYTHON_TOP_LEVEL_CLASS_EXISTS"}:
        tree=ast.parse(safe_path(spec["path"]).read_text(encoding="utf-8"))
        if kind=="PYTHON_TOP_LEVEL_FUNCTION_EXISTS":
            ok=any(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==spec["name"] for n in tree.body)
        else:
            ok=any(isinstance(n,ast.ClassDef) and n.name==spec["name"] for n in tree.body)
        assert ok,cid
    else:
        raise AssertionError("SEMANTIC_KIND_UNSUPPORTED:"+str(kind))
print("V9_SEMANTIC_ACCEPTANCE_PASS")
""" % blob
