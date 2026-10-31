"""One-sided sound semantic acceptance cells for explicit Python software requests.

The lossless raw-task contract remains the source of truth for every non-whitespace
task span. This compiler recognizes only an exact, bounded line grammar whose
meaning can be rendered into deterministic executable checks. A recognized source
line may cover multiple lossless raw obligations because the lossless contract
intentionally splits at punctuation, including dots inside module/file names.

Unsupported, malformed, or ambiguous lines leave all intersecting raw obligations
as blocking residuals. This is deliberately not a general natural-language parser.
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

def _canon(value:Any)->str:
    return json.dumps(
        value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False
    )

def _sha(value:Any)->str:
    if isinstance(value,bytes):
        raw=value
    elif isinstance(value,str):
        raw=value.encode("utf-8")
    else:
        raw=_canon(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

_CALL=r"([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)"
_QJSON=r'("(?:\\.|[^"\\])*")'
_CALL_EQ=re.compile(
    r"^Calling\s+"+_CALL+
    r"\s+with JSON arguments\s+(\[[\s\S]*\])\s+must equal\s+([\s\S]+)$"
)
_CALL_BOOL=re.compile(
    r"^Calling\s+"+_CALL+
    r"\s+with JSON arguments\s+(\[[\s\S]*\])\s+must be\s+(true|false)[.!?]?$",
    re.IGNORECASE,
)
_CALL_RAISES=re.compile(
    r"^Calling\s+"+_CALL+
    r"\s+with JSON arguments\s+(\[[\s\S]*\])\s+must raise\s+([A-Za-z_]\w*)[.!?]?$"
)
_FILE_CONTAINS=re.compile(
    r"^File\s+"+_QJSON+r"\s+must contain exact text\s+"+_QJSON+r"[.!?]?$"
)
_FUNC_EXISTS=re.compile(
    r"^Python function\s+([A-Za-z_]\w*)\s+must exist in file\s+"+_QJSON+r"[.!?]?$"
)
_CLASS_EXISTS=re.compile(
    r"^Python class\s+([A-Za-z_]\w*)\s+must exist in file\s+"+_QJSON+r"[.!?]?$"
)

def _json(raw:str,label:str)->Any:
    try:
        return json.loads(raw)
    except Exception as exc:
        raise SemanticAcceptanceError(label+"_JSON_INVALID") from exc

def _json_string(raw:str,label:str)->str:
    value=_json(raw,label)
    if not isinstance(value,str):
        raise SemanticAcceptanceError(label+"_NOT_STRING")
    return value

def _json_expected(raw:str)->Any:
    try:
        return json.loads(raw)
    except Exception:
        if raw and raw[-1] in ".!?":
            return _json(raw[:-1],"CALL_EXPECTED")
        raise SemanticAcceptanceError("CALL_EXPECTED_JSON_INVALID")

def _call_parts(callable_name:str)->tuple[str,str]:
    module,function=callable_name.rsplit(".",1)
    return module,function

def _line_spans(text:str)->list[tuple[int,int,str]]:
    rows=[]
    cursor=0
    for raw in text.splitlines(keepends=True):
        start=cursor
        end=cursor+len(raw)
        cursor=end
        while start<end and text[start].isspace():
            start+=1
        while end>start and text[end-1].isspace():
            end-=1
        if start<end:
            rows.append((start,end,text[start:end]))
    if cursor<len(text):
        start=cursor
        end=len(text)
        while start<end and text[start].isspace():
            start+=1
        while end>start and text[end-1].isspace():
            end-=1
        if start<end:
            rows.append((start,end,text[start:end]))
    if not rows and text.strip():
        start=next(i for i,ch in enumerate(text) if not ch.isspace())
        end=len(text.rstrip())
        rows.append((start,end,text[start:end]))
    return rows

def _cell(
    obligation_ids:list[str],
    kind:str,
    spec:dict[str,Any],
    source_span:list[int],
)->dict[str,Any]:
    payload={
        "obligation_ids":sorted(obligation_ids),
        "kind":kind,
        "spec":spec,
        "source_span":source_span,
    }
    return {**payload,"cell_id":"SEMCELL:"+_sha(payload)}

def _compile_line(
    text:str,
    obligation_ids:list[str],
    source_span:list[int],
)->dict[str,Any]|None:
    s=text.strip()
    m=_CALL_BOOL.match(s)
    if m:
        callable_name,args_raw,value_raw=m.groups()
        args=_json(args_raw,"CALL_ARGS")
        if not isinstance(args,list):
            raise SemanticAcceptanceError("CALL_ARGS_NOT_ARRAY")
        module,function=_call_parts(callable_name)
        return _cell(obligation_ids,"PYTHON_CALL_EQUALS",{
            "module":module,
            "function":function,
            "args":args,
            "expected":value_raw.lower()=="true",
        },source_span)

    m=_CALL_RAISES.match(s)
    if m:
        callable_name,args_raw,exception_name=m.groups()
        args=_json(args_raw,"CALL_ARGS")
        if not isinstance(args,list):
            raise SemanticAcceptanceError("CALL_ARGS_NOT_ARRAY")
        module,function=_call_parts(callable_name)
        return _cell(obligation_ids,"PYTHON_CALL_RAISES_BUILTIN",{
            "module":module,
            "function":function,
            "args":args,
            "exception":exception_name,
        },source_span)

    m=_CALL_EQ.match(s)
    if m:
        callable_name,args_raw,expected_raw=m.groups()
        args=_json(args_raw,"CALL_ARGS")
        if not isinstance(args,list):
            raise SemanticAcceptanceError("CALL_ARGS_NOT_ARRAY")
        expected=_json_expected(expected_raw)
        module,function=_call_parts(callable_name)
        return _cell(obligation_ids,"PYTHON_CALL_EQUALS",{
            "module":module,
            "function":function,
            "args":args,
            "expected":expected,
        },source_span)

    m=_FILE_CONTAINS.match(s)
    if m:
        path_raw,text_raw=m.groups()
        return _cell(obligation_ids,"FILE_TEXT_CONTAINS_EXACT",{
            "path":_json_string(path_raw,"FILE_PATH"),
            "text":_json_string(text_raw,"FILE_TEXT"),
        },source_span)

    m=_FUNC_EXISTS.match(s)
    if m:
        name,path_raw=m.groups()
        return _cell(obligation_ids,"PYTHON_TOP_LEVEL_FUNCTION_EXISTS",{
            "path":_json_string(path_raw,"FUNCTION_PATH"),
            "name":name,
        },source_span)

    m=_CLASS_EXISTS.match(s)
    if m:
        name,path_raw=m.groups()
        return _cell(obligation_ids,"PYTHON_TOP_LEVEL_CLASS_EXISTS",{
            "path":_json_string(path_raw,"CLASS_PATH"),
            "name":name,
        },source_span)

    return None

def compile_request(task_text:str)->dict[str,Any]:
    contract=_LOSSLESS.compile_contract(
        task_text,
        source_id="PYTHON_SOFTWARE_REQUEST_SEMANTIC_ACCEPTANCE_V1",
        routing_target_effects=["software.task.semantic_acceptance"],
        semantic_goal_contract=None,
    )
    if contract.get("pass") is not True:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "pass":False,
            "errors":["LOSSLESS_RAW_TASK_CONTRACT_FAILED"],
            "terminal_authority":False,
        }

    obligations=((contract.get("acceptance_contract") or {}).get("obligations") or [])
    by_id={str(row.get("obligation_id")):row for row in obligations}
    required=list(by_id)
    assigned:set[str]=set()
    cells=[]
    residual=[]
    errors=[]

    for line_start,line_end,line_text in _line_spans(task_text):
        intersecting=[]
        for oid,row in by_id.items():
            span=row.get("span")
            if (
                isinstance(span,list) and len(span)==2
                and isinstance(span[0],int) and isinstance(span[1],int)
                and max(line_start,span[0]) < min(line_end,span[1])
            ):
                intersecting.append(oid)
        intersecting=sorted(set(intersecting))
        if not intersecting:
            raise SemanticAcceptanceError("SOURCE_LINE_WITHOUT_RAW_OBLIGATION")
        if assigned.intersection(intersecting):
            raise SemanticAcceptanceError("RAW_OBLIGATION_ASSIGNED_TO_MULTIPLE_LINES")
        assigned.update(intersecting)
        try:
            cell=_compile_line(line_text,intersecting,[line_start,line_end])
        except Exception as exc:
            cell=None
            errors.append({
                "obligation_ids":intersecting,
                "source_span":[line_start,line_end],
                "error":type(exc).__name__+":"+str(exc),
            })
        if cell is None:
            residual.extend(intersecting)
        else:
            cells.append(cell)

    missing=sorted(set(required)-assigned)
    if missing:
        residual.extend(missing)
    residual=sorted(set(residual))
    compiled=sorted({
        oid
        for cell in cells
        for oid in cell["obligation_ids"]
    })
    if set(compiled).intersection(residual):
        raise SemanticAcceptanceError("COMPILED_AND_RESIDUAL_OVERLAP")
    if set(compiled)|set(residual)!=set(required):
        raise SemanticAcceptanceError("RAW_OBLIGATION_PARTITION_INCOMPLETE")

    payload={
        "task_sha256":contract.get("task_sha256"),
        "required_obligation_ids":required,
        "cells":cells,
        "residual_obligation_ids":residual,
    }
    coverage_complete=not residual and not errors and set(compiled)==set(required)
    return {
        "schema":SCHEMA,
        "status":(
            "COMPILED__ALL_RAW_OBLIGATIONS_HAVE_EXECUTABLE_SEMANTIC_CELLS"
            if coverage_complete else "OPEN__SEMANTIC_RESIDUALS"
        ),
        "pass":coverage_complete,
        "coverage_complete":coverage_complete,
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
            "SUPPORTED_LINE_GRAMMAR_IS_NOT_GENERAL_NATURAL_LANGUAGE",
            "UNMATCHED_OR_INVALID_LINES_REMAIN_BLOCKING_RESIDUALS",
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
def safe_module(name):
    parts=str(name).split(".")
    if not parts or any((not p.isidentifier()) for p in parts):
        raise AssertionError("SEMANTIC_MODULE_INVALID:"+str(name))
    file_path=ROOT.joinpath(*parts).with_suffix(".py")
    package_path=ROOT.joinpath(*parts,"__init__.py")
    candidates=[p.resolve() for p in (file_path,package_path) if p.is_file() and not p.is_symlink()]
    candidates=[p for p in candidates if ROOT in p.parents]
    if len(candidates)!=1:
        raise AssertionError("SEMANTIC_MODULE_NOT_UNIQUE_REPOSITORY_LOCAL:"+str(name))
    mod=importlib.import_module(name)
    origin=getattr(mod,"__file__",None)
    if origin is None or pathlib.Path(origin).resolve() not in candidates:
        raise AssertionError("SEMANTIC_MODULE_ORIGIN_MISMATCH:"+str(name))
    return mod
def json_equal(actual,expected):
    # Python bool subclasses int: plain == accepts 1 as true, even nested.
    # Restrict to builtin JSON value types before invoking equality, so an
    # arbitrary object's __eq__ cannot impersonate the requested value.
    kind=type(expected)
    if expected is None:
        return actual is None
    if kind in (bool,str):
        return type(actual) is kind and actual==expected
    if kind in (int,float):
        return type(actual) in (int,float) and actual==expected
    if kind is list:
        return type(actual) is list and len(actual)==len(expected) and all(json_equal(a,b) for a,b in zip(actual,expected))
    if kind is dict:
        return (type(actual) is dict and all(type(k) is str for k in actual)
                and actual.keys()==expected.keys() and all(json_equal(actual[k],v) for k,v in expected.items()))
    return False
for cell in CELLS:
    kind=cell["kind"];spec=cell["spec"];cid=cell["cell_id"]
    if kind=="PYTHON_CALL_EQUALS":
        mod=safe_module(spec["module"])
        fn=getattr(mod,spec["function"])
        actual=fn(*spec["args"])
        if not json_equal(actual,spec["expected"]):
            raise AssertionError(cid)
    elif kind=="PYTHON_CALL_RAISES_BUILTIN":
        exc=getattr(builtins,spec["exception"],None)
        if not (isinstance(exc,type) and issubclass(exc,BaseException)):
            raise AssertionError(cid)
        mod=safe_module(spec["module"])
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
        if spec["text"] not in text:
            raise AssertionError(cid)
    elif kind in {"PYTHON_TOP_LEVEL_FUNCTION_EXISTS","PYTHON_TOP_LEVEL_CLASS_EXISTS"}:
        tree=ast.parse(safe_path(spec["path"]).read_text(encoding="utf-8"))
        if kind=="PYTHON_TOP_LEVEL_FUNCTION_EXISTS":
            ok=any(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==spec["name"] for n in tree.body)
        else:
            ok=any(isinstance(n,ast.ClassDef) and n.name==spec["name"] for n in tree.body)
        if not ok:
            raise AssertionError(cid)
    else:
        raise AssertionError("SEMANTIC_KIND_UNSUPPORTED:"+str(kind))
print("V9_SEMANTIC_ACCEPTANCE_PASS")
""" % blob


def run(args:dict[str,Any],root:str|pathlib.Path)->dict[str,Any]:
    if not isinstance(args,dict):
        raise SemanticAcceptanceError("ARGS_NOT_OBJECT")
    task_text=str(args.get("task_text") or "").strip()
    if not task_text:
        raise SemanticAcceptanceError("TASK_TEXT_REQUIRED")
    repo=pathlib.Path(root).resolve()
    output=(repo/str(args.get("output_path") or "")).resolve()
    if output==repo or repo not in output.parents:
        raise SemanticAcceptanceError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    result=compile_request(task_text)
    if result.get("coverage_complete") is True:
        program=render_test(result)
        result={
            **result,
            "acceptance_program_sha256":_sha(program.encode("utf-8")),
        }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    raw=output.read_bytes()
    return {
        **result,
        "output_path":str(output.relative_to(repo)).replace("\\","/"),
        "output_sha256":_sha(raw),
        "output_verified":True,
    }
