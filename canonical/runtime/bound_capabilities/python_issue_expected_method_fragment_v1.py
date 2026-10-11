"""One-sided semantic fragment extraction from explicit issue expected-code blocks.

This is a V10 breadth primitive, not a general issue parser. It recognizes only a
narrow source-grounded shape:
  * exactly one repository-local Python path stated as "The issue lies in: `...`";
  * exactly one explicitly named failing Class.method() subject;
  * exactly one "It should be:" Python fenced block;
  * the block contains exactly one function definition matching the named method.

The fragment can verify that exact expected method AST under the named class in a
candidate repository. All other raw-task obligations remain residual. Therefore a
fragment pass cannot authorize whole-task acceptance unless lossless accounting
somehow proves no residual obligations remain.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import sys
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PYTHON_ISSUE_EXPECTED_METHOD_FRAGMENT_V1"
MODEL_DEPENDENCY_COUNT=0
EXTERNAL_GENERAL_PURPOSE_MODEL_RUNTIME_DEPENDENCY_COUNT=0

_PATH_RE=re.compile(
    r"(?im)^[ \t]*The issue lies in:[ \t]*`([^`\r\n]+)`[ \t]*$"
)
_TARGET_RE=re.compile(
    r"`([A-Za-z_]\w*)\.([A-Za-z_]\w*)\(\)`[ \t]+does[ \t]+not\b",
    re.IGNORECASE,
)
_MARKER_RE=re.compile(r"(?im)^[ \t]*It should be:[ \t]*$")
_FENCE_AFTER_MARKER_RE=re.compile(
    r"[ \t]*\r?\n[ \t]*```(?:python|py)?[ \t]*\r?\n",
    re.IGNORECASE,
)
_FENCE_CLOSE_RE=re.compile(r"(?m)^[ \t]*```[ \t]*(?:\r?$)")
_MAX_TASK_BYTES=256_000
_MAX_SNIPPET_BYTES=32_000


class IssueSemanticFragmentError(RuntimeError):
    pass


def _sha(value:Any)->str:
    if isinstance(value,bytes):
        raw=value
    elif isinstance(value,str):
        raw=value.encode("utf-8")
    else:
        raw=json.dumps(
            value,sort_keys=True,separators=(",",":"),ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load_lossless():
    path=pathlib.Path(__file__).resolve().parent.parent/"lossless_raw_task_contract_v1.py"
    spec=importlib.util.spec_from_file_location("_brain_v10_lossless",path)
    if spec is None or spec.loader is None:
        raise IssueSemanticFragmentError("LOSSLESS_CONTRACT_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


_LOSSLESS=_load_lossless()


def _safe_rel_python_path(raw:str)->str:
    if not isinstance(raw,str) or not raw or "\x00" in raw or "\\" in raw:
        raise IssueSemanticFragmentError("ISSUE_PATH_INVALID")
    p=pathlib.PurePosixPath(raw)
    if p.is_absolute() or ".." in p.parts or "." in p.parts or p.suffix!=".py":
        raise IssueSemanticFragmentError("ISSUE_PATH_INVALID")
    normalized=p.as_posix()
    if normalized!=raw or normalized.startswith("/"):
        raise IssueSemanticFragmentError("ISSUE_PATH_INVALID")
    return normalized


def _intersects(span:Any,start:int,end:int)->bool:
    return (
        isinstance(span,list) and len(span)==2
        and isinstance(span[0],int) and isinstance(span[1],int)
        and max(start,span[0]) < min(end,span[1])
    )


def _expected_function(snippet:str,method_name:str)->tuple[str,str]:
    try:
        tree=ast.parse(snippet)
    except SyntaxError as exc:
        raise IssueSemanticFragmentError("EXPECTED_CODE_NOT_PARSEABLE_PYTHON") from exc
    if len(tree.body)!=1 or not isinstance(tree.body[0],(ast.FunctionDef,ast.AsyncFunctionDef)):
        raise IssueSemanticFragmentError("EXPECTED_CODE_MUST_BE_ONE_FUNCTION")
    fn=tree.body[0]
    if fn.name!=method_name:
        raise IssueSemanticFragmentError("EXPECTED_METHOD_NAME_MISMATCH")
    dump=ast.dump(fn,annotate_fields=True,include_attributes=False)
    return dump,_sha(dump)


def compile_fragment(task_text:str)->dict[str,Any]:
    if not isinstance(task_text,str) or not task_text.strip():
        raise IssueSemanticFragmentError("TASK_TEXT_REQUIRED")
    if len(task_text.encode("utf-8"))>_MAX_TASK_BYTES:
        raise IssueSemanticFragmentError("TASK_TEXT_TOO_LARGE")

    contract=_LOSSLESS.compile_contract(
        task_text,
        source_id="PYTHON_ISSUE_EXPECTED_METHOD_FRAGMENT_V1",
        routing_target_effects=["software.task.semantic_acceptance.fragment"],
        semantic_goal_contract=None,
    )
    if contract.get("pass") is not True:
        raise IssueSemanticFragmentError("LOSSLESS_RAW_TASK_CONTRACT_FAILED")

    paths=list(_PATH_RE.finditer(task_text))
    targets=list(_TARGET_RE.finditer(task_text))
    markers=list(_MARKER_RE.finditer(task_text))
    errors=[]
    if len(paths)!=1:
        errors.append("EXPECTED_EXACTLY_ONE_ISSUE_PATH")
    if len(targets)!=1:
        errors.append("EXPECTED_EXACTLY_ONE_CLASS_METHOD_SUBJECT")
    if len(markers)!=1:
        errors.append("EXPECTED_EXACTLY_ONE_IT_SHOULD_BE_MARKER")
    if errors:
        return _open_result(contract,errors)

    try:
        path=_safe_rel_python_path(paths[0].group(1))
    except IssueSemanticFragmentError as exc:
        return _open_result(contract,[str(exc)])

    class_name,method_name=targets[0].groups()
    marker=markers[0]
    fence_open=_FENCE_AFTER_MARKER_RE.match(task_text,marker.end())
    if fence_open is None:
        return _open_result(contract,["EXPECTED_PYTHON_FENCE_IMMEDIATELY_AFTER_MARKER"])
    code_start=fence_open.end()
    close=_FENCE_CLOSE_RE.search(task_text,code_start)
    if close is None:
        return _open_result(contract,["EXPECTED_CODE_FENCE_NOT_CLOSED"])
    snippet=task_text[code_start:close.start()].rstrip("\r\n")
    if not snippet.strip():
        return _open_result(contract,["EXPECTED_CODE_BLOCK_EMPTY"])
    if len(snippet.encode("utf-8"))>_MAX_SNIPPET_BYTES:
        return _open_result(contract,["EXPECTED_CODE_BLOCK_TOO_LARGE"])
    # A second fence/marker after the chosen block is ambiguous rather than ignored.
    if _MARKER_RE.search(task_text,marker.end()):
        return _open_result(contract,["MULTIPLE_EXPECTED_CODE_MARKERS"])

    try:
        expected_ast_dump,expected_ast_sha256=_expected_function(snippet,method_name)
    except IssueSemanticFragmentError as exc:
        return _open_result(contract,[str(exc)])

    obligations=((contract.get("acceptance_contract") or {}).get("obligations") or [])
    required=[str(row.get("obligation_id")) for row in obligations]
    fragment_start=marker.start()
    fragment_end=close.end()
    covered=sorted({
        str(row.get("obligation_id"))
        for row in obligations
        if _intersects(row.get("span"),fragment_start,fragment_end)
    })
    if not covered:
        return _open_result(contract,["EXPECTED_BLOCK_HAS_NO_LOSSLESS_OBLIGATION_BINDING"])
    residual=sorted(set(required)-set(covered))
    payload={
        "task_sha256":contract.get("task_sha256"),
        "path":path,
        "class_name":class_name,
        "method_name":method_name,
        "expected_ast_sha256":expected_ast_sha256,
        "covered_obligation_ids":covered,
        "residual_obligation_ids":residual,
        "source_ranges":{
            "path":[paths[0].start(),paths[0].end()],
            "subject":[targets[0].start(),targets[0].end()],
            "expected_block":[fragment_start,fragment_end],
        },
    }
    return {
        "schema":SCHEMA,
        "status":"COMPILED__EXPECTED_METHOD_AST_FRAGMENT",
        "pass":True,
        "fragment_compiled":True,
        "full_task_coverage_complete":not residual,
        "acceptance_stop_authorized":False,
        "task_sha256":contract.get("task_sha256"),
        "lossless_task_contract_sha256":contract.get("task_contract_sha256"),
        "required_obligation_ids":required,
        "fragment_covered_obligation_ids":covered,
        "residual_obligation_ids":residual,
        "fragment":{
            "kind":"PYTHON_CLASS_METHOD_EXPECTED_AST",
            "path":path,
            "class_name":class_name,
            "method_name":method_name,
            "expected_code":snippet,
            "expected_ast_dump":expected_ast_dump,
            "expected_ast_sha256":expected_ast_sha256,
        },
        "source_ranges":payload["source_ranges"],
        "compiler_payload_sha256":_sha(payload),
        "model_dependency_count":0,
        "external_general_purpose_model_runtime_dependency_count":0,
        "incremental_spend_usd":0,
        "terminal_authority":False,
        "hard_nonclaims":[
            "NOT_A_GENERAL_ISSUE_OR_NATURAL_LANGUAGE_PARSER",
            "OTHER_RAW_TASK_OBLIGATIONS_REMAIN_BLOCKING_RESIDUALS",
            "FRAGMENT_PASS_DOES_NOT_AUTHORIZE_WHOLE_TASK_ACCEPTANCE_WHILE_RESIDUALS_EXIST",
            "EXACT_EXPECTED_AST_MAY_REJECT_SEMANTICALLY_EQUIVALENT_IMPLEMENTATIONS",
            "NO_FRONTIERCODE_OR_CURSORBENCH_SCORE_CREDIT",
        ],
    }


def _open_result(contract:Mapping[str,Any],errors:list[str])->dict[str,Any]:
    obligations=((contract.get("acceptance_contract") or {}).get("obligations") or [])
    required=[str(row.get("obligation_id")) for row in obligations]
    return {
        "schema":SCHEMA,
        "status":"OPEN__UNSUPPORTED_OR_AMBIGUOUS_ISSUE_SEMANTICS",
        "pass":False,
        "fragment_compiled":False,
        "full_task_coverage_complete":False,
        "acceptance_stop_authorized":False,
        "task_sha256":contract.get("task_sha256"),
        "lossless_task_contract_sha256":contract.get("task_contract_sha256"),
        "required_obligation_ids":required,
        "fragment_covered_obligation_ids":[],
        "residual_obligation_ids":required,
        "errors":errors,
        "model_dependency_count":0,
        "external_general_purpose_model_runtime_dependency_count":0,
        "incremental_spend_usd":0,
        "terminal_authority":False,
    }


def _safe_candidate_file(root:pathlib.Path,rel:str)->pathlib.Path:
    p=(root/rel).resolve()
    if p==root or root not in p.parents or not p.is_file() or p.is_symlink():
        raise IssueSemanticFragmentError("CANDIDATE_FILE_INVALID")
    return p


def _find_exact_method(tree:ast.AST,class_name:str,method_name:str)->list[ast.AST]:
    matches=[]
    for node in getattr(tree,"body",[]):
        if isinstance(node,ast.ClassDef) and node.name==class_name:
            for child in node.body:
                if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef)) and child.name==method_name:
                    matches.append(child)
    return matches


def evaluate_fragment(
    compiled:Mapping[str,Any],
    candidate_root:str|os.PathLike[str],
)->dict[str,Any]:
    if not isinstance(compiled,Mapping) or compiled.get("fragment_compiled") is not True:
        raise IssueSemanticFragmentError("COMPILED_FRAGMENT_REQUIRED")
    root=pathlib.Path(candidate_root).resolve()
    if not root.is_dir() or root.is_symlink():
        raise IssueSemanticFragmentError("CANDIDATE_ROOT_INVALID")
    fragment=compiled.get("fragment") or {}
    rel=str(fragment.get("path") or "")
    target=_safe_candidate_file(root,rel)
    raw=target.read_bytes()
    try:
        text=raw.decode("utf-8")
        tree=ast.parse(text,filename=str(target))
    except Exception as exc:
        return _evaluation_result(compiled,False,"CANDIDATE_PYTHON_PARSE_FAILED",_sha(raw))
    methods=_find_exact_method(
        tree,str(fragment.get("class_name") or ""),str(fragment.get("method_name") or "")
    )
    if len(methods)!=1:
        return _evaluation_result(compiled,False,"TARGET_CLASS_METHOD_NOT_UNIQUE",_sha(raw))
    actual=ast.dump(methods[0],annotate_fields=True,include_attributes=False)
    expected=str(fragment.get("expected_ast_dump") or "")
    if not expected or _sha(expected)!=fragment.get("expected_ast_sha256"):
        raise IssueSemanticFragmentError("EXPECTED_AST_BINDING_INVALID")
    passed=actual==expected
    return _evaluation_result(
        compiled,passed,
        "EXPECTED_METHOD_AST_MATCH" if passed else "EXPECTED_METHOD_AST_MISMATCH",
        _sha(raw),
    )


def _evaluation_result(
    compiled:Mapping[str,Any],
    passed:bool,
    reason:str,
    candidate_file_sha256:str,
)->dict[str,Any]:
    whole=passed and compiled.get("full_task_coverage_complete") is True
    return {
        "schema":SCHEMA+"_EVALUATION",
        "status":"PASS__EXPECTED_METHOD_FRAGMENT" if passed else "FAIL__EXPECTED_METHOD_FRAGMENT",
        "fragment_pass":passed,
        "reason":reason,
        "candidate_file_sha256":candidate_file_sha256,
        "full_task_coverage_complete":compiled.get("full_task_coverage_complete") is True,
        "acceptance_stop_authorized":whole,
        "source_mutated":False,
        "model_dependency_count":0,
        "external_general_purpose_model_runtime_dependency_count":0,
        "incremental_spend_usd":0,
        "terminal_authority":False,
    }


def run(args:Mapping[str,Any],root:str|os.PathLike[str])->dict[str,Any]:
    if not isinstance(args,Mapping):
        raise IssueSemanticFragmentError("ARGS_NOT_OBJECT")
    task_text=args.get("task_text")
    if not isinstance(task_text,str):
        raise IssueSemanticFragmentError("TASK_TEXT_REQUIRED")
    repo=pathlib.Path(root).resolve()
    out=(repo/str(args.get("output_path") or "")).resolve()
    if out==repo or repo not in out.parents:
        raise IssueSemanticFragmentError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    result=compile_fragment(task_text)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    result={**result,
        "output_path":str(out.relative_to(repo)).replace("\\","/"),
        "output_sha256":_sha(out.read_bytes()),
        "output_verified":True,
    }
    return result
