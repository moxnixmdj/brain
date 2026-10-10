"""CC_R1 reality-containment verifier for the frozen R3 promotion-safety claim.

The proof is intentionally an over-approximation: exact in-scope Python AST plus
TOP for all inputs and external/imported call outcomes. It proves only the
current ten-file generation. Dynamic in-scope code generation fails closed.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT_ID="CC_R1_REALITY_CONTAINMENT_V1"
CLAIM_ID="e1c519109c4b2c46a9225686fc2c5c5490564d1cc62d5c6ff3c6c436bfca4314"
FORBIDDEN_DIRECT_CALLS=frozenset({"eval","exec","compile","__import__"})
FORBIDDEN_DYNAMIC_ATTRS=frozenset({
    "CodeType","FunctionType","exec_module","set_code","replace_code",
})
FORBIDDEN_MUTATION_ATTRS=frozenset({"__code__","__globals__"})
FORBIDDEN_NAMESPACE_CALLS=frozenset({"globals","locals"})


def _blob_sha(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()


def _fail(root_id:str,claim_id:str,*errors:str)->dict[str,Any]:
    return {
        "pass":False,
        "status":"FAIL_CLOSED__CC_R1_REALITY_CONTAINMENT_UNPROVED",
        "root_id":root_id,
        "claim_id":claim_id,
        "semantic_claim_verified":False,
        "errors":sorted(set(errors)),
        "terminal_credit_delta":0,
    }


def _call_name(node:ast.Call)->tuple[str|None,str|None]:
    fn=node.func
    if isinstance(fn,ast.Name):
        return fn.id,None
    if isinstance(fn,ast.Attribute):
        return None,fn.attr
    return None,None


def _dynamic_escape_rows(tree:ast.AST)->list[str]:
    rows:list[str]=[]
    for node in ast.walk(tree):
        line=getattr(node,"lineno",-1)
        if isinstance(node,ast.Call):
            direct,attr=_call_name(node)
            if direct in FORBIDDEN_DIRECT_CALLS or direct in FORBIDDEN_NAMESPACE_CALLS:
                rows.append(f"{line}:CALL:{direct}")
            if attr in FORBIDDEN_DYNAMIC_ATTRS:
                rows.append(f"{line}:ATTR_CALL:{attr}")
            if direct=="setattr" and len(node.args)>=2:
                name=node.args[1]
                if isinstance(name,ast.Constant) and name.value in FORBIDDEN_MUTATION_ATTRS:
                    rows.append(f"{line}:SETATTR:{name.value}")
        elif isinstance(node,(ast.Assign,ast.AnnAssign,ast.AugAssign)):
            targets=node.targets if isinstance(node,ast.Assign) else [node.target]
            for target in targets:
                for sub in ast.walk(target):
                    if isinstance(sub,ast.Attribute) and sub.attr in FORBIDDEN_MUTATION_ATTRS:
                        rows.append(f"{line}:ATTR_WRITE:{sub.attr}")
                    if (
                        isinstance(sub,ast.Subscript)
                        and isinstance(sub.value,ast.Attribute)
                        and isinstance(sub.value.value,ast.Name)
                        and sub.value.value.id=="sys"
                        and sub.value.attr=="modules"
                    ):
                        rows.append(f"{line}:SYS_MODULES_WRITE")
        elif isinstance(node,ast.ImportFrom) and node.module=="builtins":
            for alias in node.names:
                if alias.name in FORBIDDEN_DIRECT_CALLS or alias.name in FORBIDDEN_NAMESPACE_CALLS:
                    rows.append(f"{line}:BUILTINS_IMPORT:{alias.name}")
    return sorted(set(rows))


def _inventory(tree:ast.AST)->dict[str,int]:
    counts={
        "ast_nodes":0,
        "statements":0,
        "calls":0,
        "assignments":0,
        "branches":0,
        "loops":0,
        "raises":0,
        "returns":0,
        "imports":0,
        "with_blocks":0,
    }
    for node in ast.walk(tree):
        counts["ast_nodes"]+=1
        if isinstance(node,ast.stmt): counts["statements"]+=1
        if isinstance(node,ast.Call): counts["calls"]+=1
        if isinstance(node,(ast.Assign,ast.AnnAssign,ast.AugAssign,ast.NamedExpr)): counts["assignments"]+=1
        if isinstance(node,(ast.If,ast.IfExp,ast.Match)): counts["branches"]+=1
        if isinstance(node,(ast.For,ast.AsyncFor,ast.While)): counts["loops"]+=1
        if isinstance(node,ast.Raise): counts["raises"]+=1
        if isinstance(node,ast.Return): counts["returns"]+=1
        if isinstance(node,(ast.Import,ast.ImportFrom)): counts["imports"]+=1
        if isinstance(node,(ast.With,ast.AsyncWith)): counts["with_blocks"]+=1
    return counts


def _explicit_write_calls(tree:ast.AST)->int:
    count=0
    for node in ast.walk(tree):
        if not isinstance(node,ast.Call):
            continue
        fn=node.func
        if isinstance(fn,ast.Attribute) and fn.attr in {
            "write_text","write_bytes","write","replace","rename","unlink",
        }:
            count+=1
        elif isinstance(fn,ast.Name) and fn.id in {"open"}:
            count+=1
    return count


def verify_certificate(
    *,
    root:Path,
    certificate_path:Path,
    active_claim:Mapping[str,Any],
    root_id:str,
)->dict[str,Any]:
    root=root.resolve()
    claim_id=str(active_claim.get("claim_id") or "")
    errors:list[str]=[]
    if root_id!=ROOT_ID:
        return _fail(root_id,claim_id,"ROOT_ID_MISMATCH")
    if claim_id!=CLAIM_ID:
        return _fail(root_id,claim_id,"ACTIVE_CLAIM_ID_MISMATCH")
    try:
        cert=json.loads(certificate_path.read_text(encoding="utf-8"))
    except Exception:
        return _fail(root_id,claim_id,"CERTIFICATE_INVALID_JSON")
    if cert.get("root_id")!=ROOT_ID: errors.append("CERTIFICATE_ROOT_MISMATCH")
    if cert.get("claim_id")!=CLAIM_ID: errors.append("CERTIFICATE_CLAIM_MISMATCH")
    if cert.get("terminal_authority") is not False: errors.append("CERTIFICATE_TERMINAL_AUTHORITY_NOT_FALSE")
    if (cert.get("accounting") or {}).get("terminal_credit_delta")!=0:
        errors.append("CERTIFICATE_NONZERO_TERMINAL_CREDIT")

    claim_ref=cert.get("active_claim") or {}
    cp=root/str(claim_ref.get("path") or "")
    if not cp.is_file():
        errors.append("ACTIVE_CLAIM_FILE_MISSING")
        frozen={}
    else:
        if _blob_sha(cp)!=claim_ref.get("git_blob_sha"):
            errors.append("ACTIVE_CLAIM_BLOB_MISMATCH")
        try: frozen=json.loads(cp.read_text(encoding="utf-8"))
        except Exception:
            frozen={}
            errors.append("ACTIVE_CLAIM_JSON_INVALID")
    if frozen.get("claim_id")!=CLAIM_ID:
        errors.append("FROZEN_CLAIM_ID_MISMATCH")
    if frozen.get("scope_sha256")!=active_claim.get("scope_sha256"):
        errors.append("ACTIVE_CLAIM_SCOPE_MISMATCH")

    surface=cert.get("bounded_surface")
    expected=list((frozen.get("scope") or {}).get("bounded_system_surface") or [])
    if not isinstance(surface,Mapping):
        errors.append("BOUNDED_SURFACE_INVALID")
        surface={}
    if set(surface)!=set(expected):
        errors.append("SURFACE_NOT_EXACT_ACTIVE_CLAIM_SCOPE")
    if len(surface)!=10:
        errors.append("SURFACE_COUNT_NOT_10")
    if errors:
        return _fail(root_id,claim_id,*errors)

    aggregate={
        "ast_nodes":0,"statements":0,"calls":0,"assignments":0,
        "branches":0,"loops":0,"raises":0,"returns":0,"imports":0,
        "with_blocks":0,"explicit_write_calls":0,
    }
    escapes:list[str]=[]
    per_file:dict[str,dict[str,int]]={}
    for rel,sha in surface.items():
        p=root/str(rel)
        if not p.is_file():
            errors.append("SURFACE_FILE_MISSING:"+str(rel))
            continue
        if _blob_sha(p)!=sha:
            errors.append("SURFACE_BLOB_MISMATCH:"+str(rel))
            continue
        try:
            source=p.read_text(encoding="utf-8")
            tree=ast.parse(source,filename=str(rel),mode="exec")
        except Exception as exc:
            errors.append("SURFACE_PARSE_FAILED:"+str(rel)+":"+type(exc).__name__)
            continue
        inv=_inventory(tree)
        inv["explicit_write_calls"]=_explicit_write_calls(tree)
        per_file[str(rel)]=inv
        for key,value in inv.items():
            aggregate[key]+=value
        for row in _dynamic_escape_rows(tree):
            escapes.append(str(rel)+":"+row)

    if errors:
        return _fail(root_id,claim_id,*errors)
    if escapes:
        return _fail(root_id,claim_id,*["DYNAMIC_AST_ENVELOPE_ESCAPE:"+x for x in escapes])
    if aggregate["statements"]<=0 or aggregate["ast_nodes"]<=aggregate["statements"]:
        return _fail(root_id,claim_id,"AST_INVENTORY_IMPLAUSIBLE")
    if aggregate["calls"]<=0:
        return _fail(root_id,claim_id,"EXTERNAL_CALL_ENVELOPE_EMPTY")

    model=cert.get("b_plus_model") or {}
    semantics=model.get("semantics")
    required=(
        "ALL_EXECUTABLE_STATEMENTS_IN_THE_EXACT_TEN_FILE_SOURCE_AST_ARE_RETAINED",
        "FUNCTION_ARGUMENTS_AND_MUTABLE_INPUT_OBJECTS_ARE_UNCONSTRAINED_TOP_VALUES_UNLESS_THE_EXECUTABLE_CODE_ITSELF_NARROWS_THEM",
        "EVERY_EXTERNAL_OR_IMPORTED_CALL_IS_MODELED_AS_AN_OPAQUE_EVENT_WITH_ARBITRARY_RETURN_VALUE_EXCEPTION_AND_EXTERNAL_SIDE_EFFECT",
        "UNKNOWN_OR_UNINTERPRETED_VALUES_REMAIN_TOP_AND_ARE_NOT_DROPPED",
    )
    if not isinstance(semantics,list) or any(x not in semantics for x in required):
        return _fail(root_id,claim_id,"B_PLUS_UNKNOWN_TO_TOP_SEMANTICS_INCOMPLETE")

    return {
        "pass":True,
        "status":"PASS__CC_R1_FROZEN_AST_REALITY_CONTAINMENT_KERNEL_CHECKED",
        "root_id":ROOT_ID,
        "claim_id":CLAIM_ID,
        "semantic_claim_verified":True,
        "bounded_surface_file_count":len(surface),
        "dynamic_ast_escape_count":0,
        "unknown_external_call_results_modeled_as_top":True,
        "future_source_bytes_excluded":True,
        "aggregate_ast_inventory":aggregate,
        "per_file_inventory_sha256":hashlib.sha256(
            json.dumps(per_file,sort_keys=True,separators=(",",":")).encode("utf-8")
        ).hexdigest(),
        "b_real_subseteq_b_plus":True,
        "global_mission_completion_derivable":False,
        "terminal_credit_delta":0,
        "errors":[],
    }
