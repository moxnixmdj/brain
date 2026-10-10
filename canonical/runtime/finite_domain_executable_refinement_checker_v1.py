"""Exhaustive semantic refinement checker for explicitly finite domains."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_FINITE_DOMAIN_EXECUTABLE_REFINEMENT_PROOF_V1"
RECEIPT_SCHEMA="PROJECT_BRAIN_FINITE_DOMAIN_EXECUTABLE_REFINEMENT_RECEIPT_V1"

def _canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()

def _blob(p:Path)->str:
    d=p.read_bytes()
    return sha1(b"blob "+str(len(d)).encode("ascii")+b"\0"+d).hexdigest()

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {"schema":RECEIPT_SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
            "refinement_verified":False,"semantic_truth_authority":False,
            "execution_authority":False,"terminal_authority":False,"terminal_credit_delta":0,**extra}

def _bound(root:Path,row:Any,label:str)->Path|None:
    if not isinstance(row,Mapping) or set(row)!={"path","git_blob_sha"}:
        return None
    rel=Path(str(row.get("path") or ""))
    if rel.is_absolute() or ".." in rel.parts:return None
    p=(root/rel).resolve()
    try:p.relative_to(root.resolve())
    except ValueError:return None
    if not p.is_file() or _blob(p)!=row.get("git_blob_sha"):return None
    return p

def verify(raw:Mapping[str,Any],*,repo_root:Path|None=None)->dict[str,Any]:
    if not isinstance(raw,Mapping) or raw.get("schema")!=SCHEMA:return _fail("PROOF_SCHEMA_INVALID")
    required={"schema","subject_id","abstract_spec","concrete_implementation","callable","terminal_credit_delta"}
    if set(raw)!=required:return _fail("PROOF_FIELD_SET_INVALID")
    if raw.get("terminal_credit_delta")!=0:return _fail("NONZERO_TERMINAL_CREDIT_FORBIDDEN")
    subject=str(raw.get("subject_id") or "").strip()
    callable_name=str(raw.get("callable") or "").strip()
    if not subject or not callable_name:return _fail("SUBJECT_OR_CALLABLE_REQUIRED")
    root=Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    spec_path=_bound(root,raw.get("abstract_spec"),"ABSTRACT_SPEC")
    impl_path=_bound(root,raw.get("concrete_implementation"),"CONCRETE_IMPLEMENTATION")
    if spec_path is None:return _fail("ABSTRACT_SPEC_BINDING_INVALID")
    if impl_path is None:return _fail("CONCRETE_IMPLEMENTATION_BINDING_INVALID")
    try:spec=json.loads(spec_path.read_text(encoding="utf-8"))
    except Exception:return _fail("ABSTRACT_SPEC_JSON_INVALID")
    if not isinstance(spec,Mapping) or spec.get("subject_id")!=subject:return _fail("ABSTRACT_SUBJECT_MISMATCH")
    cases=spec.get("finite_domain_cases")
    if not isinstance(cases,list) or not cases:return _fail("FINITE_DOMAIN_CASES_REQUIRED")
    seen=set()
    expected=[]
    for i,row in enumerate(cases):
        if not isinstance(row,Mapping) or set(row)!={"input","expected_output"}:return _fail("FINITE_CASE_INVALID",index=i)
        key=sha256(_canon(row["input"])).hexdigest()
        if key in seen:return _fail("FINITE_DOMAIN_DUPLICATE",index=i)
        seen.add(key);expected.append(row)
    module_name="_brain_refinement_"+sha256(str(impl_path).encode()).hexdigest()
    module_spec=importlib.util.spec_from_file_location(module_name,impl_path)
    if module_spec is None or module_spec.loader is None:return _fail("IMPLEMENTATION_LOAD_FAILED")
    module=importlib.util.module_from_spec(module_spec)
    try:module_spec.loader.exec_module(module)
    except Exception as exc:return _fail("IMPLEMENTATION_IMPORT_FAILED",error=type(exc).__name__)
    fn=getattr(module,callable_name,None)
    if not callable(fn):return _fail("CALLABLE_NOT_FOUND")
    results=[]
    for i,row in enumerate(expected):
        try:actual=fn(deepcopy(row["input"]))
        except Exception as exc:return _fail("CONCRETE_EXECUTION_FAILED",index=i,error=type(exc).__name__)
        if _canon(actual)!=_canon(row["expected_output"]):
            return _fail("SEMANTIC_MISMATCH",index=i,actual=actual,expected=row["expected_output"])
        results.append({"index":i,"input_sha256":sha256(_canon(row["input"])).hexdigest(),"output_sha256":sha256(_canon(actual)).hexdigest()})
    body={"schema":RECEIPT_SCHEMA,"pass":True,"status":"PASS__EXHAUSTIVE_FINITE_DOMAIN_REFINEMENT",
          "subject_id":subject,"refinement_verified":True,"assurance_level":"EXHAUSTIVE_FINITE_DOMAIN",
          "abstract_spec":{"path":raw["abstract_spec"]["path"],"git_blob_sha":raw["abstract_spec"]["git_blob_sha"]},
          "concrete_implementation":{"path":raw["concrete_implementation"]["path"],"git_blob_sha":raw["concrete_implementation"]["git_blob_sha"]},
          "domain_case_count":len(expected),"case_results":results,
          "semantic_truth_authority":False,"execution_authority":False,"terminal_authority":False,"terminal_credit_delta":0}
    return {**body,"receipt_sha256":sha256(_canon(body)).hexdigest()}
