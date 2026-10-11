#!/usr/bin/env python3
"""Fail-closed explicit software-task acceptance compiler.

Compiles raw software-task text into atomic obligations and binds an obligation
only when a repository-local Python test contains an exact, structurally parsed
assertion for the named symbol and expected literal. Unbound or extra semantics
stay explicit. This is not general natural-language understanding.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import re
from typing import Any, Iterable, Mapping

SCHEMA="PROJECT_BRAIN_SOFTWARE_TASK_ACCEPTANCE_COMPILER_V1"

class AcceptanceCompilerError(RuntimeError):
    pass

_STOP={
    "a","an","the","to","of","for","and","or","in","on","at","by","with","from",
    "function","method","value","result","output","must","should","shall","needs",
    "need","make","ensure","exactly","when","called","call","return","returns",
    "returning","be","is","are","as","that","this","it"
}

def _safe_file(root:pathlib.Path,raw:Any)->pathlib.Path:
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents or not p.is_file() or p.is_symlink() or p.suffix!=".py":
        raise AcceptanceCompilerError("PATH_INVALID:"+str(raw))
    return p

def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def _normalize_task(value:Any)->str:
    text=str(value or "").replace("\r\n","\n").replace("\r","\n").strip()
    if not text:
        raise AcceptanceCompilerError("TASK_TEXT_REQUIRED")
    return text

def _decompose(text:str)->list[dict[str,Any]]:
    pieces=[]
    for line in text.splitlines():
        line=re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)","",line).strip()
        if not line:
            continue
        for part in re.split(r"(?<=[.!?;])\s+",line):
            part=part.strip(" \t.;")
            if not part:
                continue
            subparts=re.split(
                r"\s+and\s+(?=(?:[A-Za-z_]\w*\s+)?(?:must\s+|should\s+|shall\s+)?"
                r"(?:return|raise|set|accept|reject|support|preserve|ensure)\b)",
                part,flags=re.IGNORECASE
            )
            for sub in subparts:
                sub=sub.strip(" \t.;")
                if sub:
                    pieces.append(sub)
    return [{"index":i,"text":p} for i,p in enumerate(pieces)]

def _call_symbol(node:ast.AST)->str|None:
    if not isinstance(node,ast.Call):
        return None
    fn=node.func
    if isinstance(fn,ast.Name):
        return fn.id
    if isinstance(fn,ast.Attribute):
        return fn.attr
    return None

def _literal(node:ast.AST):
    if isinstance(node,ast.Constant) and isinstance(node.value,(str,int,float,bool,type(None))):
        return node.value
    return ...

def _fact(kind:str,symbol:str,expected:Any,path:pathlib.Path,node:ast.AST,root:pathlib.Path)->dict[str,Any]:
    return {
        "kind":kind,
        "symbol":symbol,
        "expected":expected,
        "test_path":str(path.relative_to(root)).replace("\\","/"),
        "lineno":getattr(node,"lineno",None)
    }

def _unittest_facts(tree:ast.AST,path:pathlib.Path,root:pathlib.Path)->list[dict[str,Any]]:
    out=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute):
            continue
        name=node.func.attr
        args=node.args
        if name=="assertEqual" and len(args)>=2:
            lcall=_call_symbol(args[0]); rcall=_call_symbol(args[1])
            lv=_literal(args[0]); rv=_literal(args[1])
            if lcall and rv is not ...:
                out.append(_fact("CALL_EQUALS_LITERAL",lcall,rv,path,node,root))
            elif rcall and lv is not ...:
                out.append(_fact("CALL_EQUALS_LITERAL",rcall,lv,path,node,root))
        elif name=="assertTrue" and args:
            sym=_call_symbol(args[0])
            if sym: out.append(_fact("CALL_EQUALS_LITERAL",sym,True,path,node,root))
        elif name=="assertFalse" and args:
            sym=_call_symbol(args[0])
            if sym: out.append(_fact("CALL_EQUALS_LITERAL",sym,False,path,node,root))
        elif name=="assertIsNone" and args:
            sym=_call_symbol(args[0])
            if sym: out.append(_fact("CALL_EQUALS_LITERAL",sym,None,path,node,root))
        elif name=="assertIsNotNone" and args:
            sym=_call_symbol(args[0])
            if sym: out.append(_fact("CALL_NOT_NONE",sym,"NOT_NONE",path,node,root))
    return out

def _pytest_assert_facts(tree:ast.AST,path:pathlib.Path,root:pathlib.Path)->list[dict[str,Any]]:
    out=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.Assert):
            continue
        test=node.test
        if isinstance(test,ast.Compare) and len(test.ops)==1 and len(test.comparators)==1:
            if isinstance(test.ops[0],ast.Eq):
                lcall=_call_symbol(test.left); rcall=_call_symbol(test.comparators[0])
                lv=_literal(test.left); rv=_literal(test.comparators[0])
                if lcall and rv is not ...:
                    out.append(_fact("CALL_EQUALS_LITERAL",lcall,rv,path,node,root))
                elif rcall and lv is not ...:
                    out.append(_fact("CALL_EQUALS_LITERAL",rcall,lv,path,node,root))
            elif isinstance(test.ops[0],ast.Is):
                sym=_call_symbol(test.left); rv=_literal(test.comparators[0])
                if sym and rv is None:
                    out.append(_fact("CALL_EQUALS_LITERAL",sym,None,path,node,root))
        elif isinstance(test,ast.Call):
            sym=_call_symbol(test)
            if sym: out.append(_fact("CALL_EQUALS_LITERAL",sym,True,path,node,root))
        elif isinstance(test,ast.UnaryOp) and isinstance(test.op,ast.Not):
            sym=_call_symbol(test.operand)
            if sym: out.append(_fact("CALL_EQUALS_LITERAL",sym,False,path,node,root))
    return out

def _collect_facts(root:pathlib.Path,tests:list[pathlib.Path])->list[dict[str,Any]]:
    facts=[]
    for path in tests:
        tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
        facts.extend(_unittest_facts(tree,path,root))
        facts.extend(_pytest_assert_facts(tree,path,root))
    unique=[]
    seen=set()
    for fact in facts:
        sig=(fact["kind"],fact["symbol"],repr(fact["expected"]),fact["test_path"],fact["lineno"])
        if sig not in seen:
            seen.add(sig); unique.append(fact)
    return unique

def _symbol_present(clause:str,symbol:str)->bool:
    return re.search(r"(?<![A-Za-z0-9_])"+re.escape(symbol)+r"(?![A-Za-z0-9_])",clause) is not None

def _expected_present(clause:str,expected:Any)->bool:
    low=clause.lower()
    if expected is True: return re.search(r"\btrue\b",low) is not None
    if expected is False: return re.search(r"\bfalse\b",low) is not None
    if expected is None: return re.search(r"\b(?:none|null)\b",low) is not None
    if expected=="NOT_NONE": return re.search(r"\b(?:not\s+none|non[- ]?null)\b",low) is not None
    if isinstance(expected,(int,float)) and not isinstance(expected,bool):
        return re.search(r"(?<![A-Za-z0-9_.])"+re.escape(str(expected))+r"(?![A-Za-z0-9_.])",clause) is not None
    if isinstance(expected,str):
        for m in re.finditer(r"(['\"])(.*?)\1",clause):
            if m.group(2)==expected:
                return True
        return False
    return False

def _literal_tokens(expected:Any)->set[str]:
    if isinstance(expected,str):
        return {t.lower() for t in re.findall(r"[A-Za-z0-9_]+",expected)}
    if expected is True: return {"true"}
    if expected is False: return {"false"}
    if expected is None: return {"none","null"}
    return {str(expected).lower()}

def _residual_tokens(clause:str,fact:Mapping[str,Any])->list[str]:
    cleaned=re.sub(r"(['\"])(.*?)\1"," ",clause)
    toks=[t.lower() for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[-+]?\d+(?:\.\d+)?",cleaned)]
    allowed=set(_STOP)
    allowed.add(str(fact["symbol"]).lower())
    allowed.update(_literal_tokens(fact["expected"]))
    if fact["expected"] is True: allowed.update({"truthy","boolean","bool"})
    if fact["expected"] is False: allowed.update({"falsy","boolean","bool"})
    if fact["expected"] is None: allowed.update({"null"})
    return [t for t in toks if t not in allowed and len(t)>=2]

def _bind_clause(clause:Mapping[str,Any],facts:list[dict[str,Any]])->dict[str,Any]:
    text=str(clause["text"])
    candidates=[
        f for f in facts
        if _symbol_present(text,str(f["symbol"])) and _expected_present(text,f["expected"])
    ]
    if not candidates:
        return {**clause,"status":"UNBOUND_SEMANTIC_REQUIREMENT","matched_facts":[],"residual_tokens":[]}
    if len(candidates)>1:
        return {**clause,"status":"AMBIGUOUS_TEST_EVIDENCE","matched_facts":candidates,"residual_tokens":[]}
    fact=candidates[0]
    residual=_residual_tokens(text,fact)
    if residual:
        return {**clause,"status":"PARTIAL_TEST_MATCH_WITH_UNBOUND_SEMANTICS","matched_facts":[fact],"residual_tokens":residual}
    return {**clause,"status":"BOUND_BY_EXACT_TEST_EVIDENCE","matched_facts":[fact],"residual_tokens":[]}

def run(args:Mapping[str,Any],root:str|os.PathLike[str])->dict[str,Any]:
    repo=pathlib.Path(root).resolve()
    if not isinstance(args,Mapping):
        raise AcceptanceCompilerError("ARGS_NOT_OBJECT")
    task=_normalize_task(args.get("task_text"))
    tests_raw=args.get("test_paths") or []
    if not isinstance(tests_raw,list) or not tests_raw:
        raise AcceptanceCompilerError("TEST_PATHS_REQUIRED")
    tests=[_safe_file(repo,x) for x in tests_raw]
    output=(repo/str(args.get("output_path") or "")).resolve()
    if output==repo or repo not in output.parents:
        raise AcceptanceCompilerError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    clauses=_decompose(task)
    if not clauses:
        raise AcceptanceCompilerError("NO_TASK_CLAUSES")
    facts=_collect_facts(repo,tests)
    obligations=[_bind_clause(c,facts) for c in clauses]
    complete=all(x["status"]=="BOUND_BY_EXACT_TEST_EVIDENCE" for x in obligations)
    result={
        "schema":SCHEMA,
        "status":"PASS__EXPLICIT_ACCEPTANCE_CONTRACT_COMPLETE" if complete else "OPEN__ACCEPTANCE_CONTRACT_HAS_UNBOUND_SEMANTICS",
        "complete":complete,
        "task_text":task,
        "task_sha256":_sha(task.encode("utf-8")),
        "test_paths":[str(p.relative_to(repo)).replace("\\","/") for p in tests],
        "test_sha256":{str(p.relative_to(repo)).replace("\\","/"):_sha(p.read_bytes()) for p in tests},
        "test_fact_count":len(facts),
        "test_facts":facts,
        "obligation_count":len(obligations),
        "bound_obligation_count":sum(x["status"]=="BOUND_BY_EXACT_TEST_EVIDENCE" for x in obligations),
        "obligations":obligations,
        "acceptance_ready_for_test_oracle_only":complete,
        "model_dependency_count":0,
        "external_capability_provider_count":0,
        "incremental_spend_usd":0,
        "hard_nonclaims":[
            "NO_GENERAL_NATURAL_LANGUAGE_SEMANTIC_UNDERSTANDING",
            "NO_CLAIM_TESTS_EXHAUST_THE_USER_REQUEST_UNLESS_EVERY_EXPLICIT_CLAUSE_IS_EXACTLY_BOUND",
            "NO_HIDDEN_REQUIREMENT_INFERENCE",
            "NO_MERGEABILITY_OR_FRONTIERCODE_SCORE_AUTHORITY",
            "NO_REQUIREMENT_DROPPING_WHEN_BINDING_FAILS"
        ]
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    raw=output.read_bytes()
    result["output_path"]=str(output.relative_to(repo)).replace("\\","/")
    result["output_sha256"]=_sha(raw)
    result["output_verified"]=True
    return result
