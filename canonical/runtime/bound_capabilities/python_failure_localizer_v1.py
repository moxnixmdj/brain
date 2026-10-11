#!/usr/bin/env python3
"""Deterministic Python failure-evidence localizer V1.

Maps observable failing-test evidence to repository-local Python file/line/symbol
candidates. It does not infer causality. Traceback frames are preferred; local
modules imported by failing tests are fallback candidates.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PYTHON_FAILURE_LOCALIZER_V1"

class FailureLocalizationError(RuntimeError):
    pass

def _safe_file(repo:pathlib.Path, raw:Any)->pathlib.Path:
    p=(repo/str(raw or "")).resolve()
    if p==repo or repo not in p.parents or not p.is_file() or p.is_symlink() or p.suffix!=".py":
        raise FailureLocalizationError("PATH_INVALID:"+str(raw))
    return p

def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def _stable_evidence(text:str)->str:
    lines=text.replace("\r\n","\n").split("\n")
    return "\n".join(line for line in lines if not line.startswith("Ran "))

def _run(repo:pathlib.Path, test:pathlib.Path, timeout_s:int)->dict[str,Any]:
    try:
        proc=subprocess.run(
            [sys.executable,str(test.relative_to(repo))],
            cwd=repo,text=True,capture_output=True,timeout=timeout_s
        )
        return {
            "returncode":proc.returncode,
            "stdout":proc.stdout or "",
            "stderr":proc.stderr or "",
            "timed_out":False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode":None,
            "stdout":exc.stdout or "",
            "stderr":exc.stderr or "",
            "timed_out":True,
        }

def _local_imports(repo:pathlib.Path, test:pathlib.Path)->list[pathlib.Path]:
    tree=ast.parse(test.read_text(encoding="utf-8"),filename=str(test))
    names=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module:
            names.append(node.module)
    out=[]
    for name in names:
        rel=pathlib.Path(*name.split("."))
        for candidate in (repo/rel.with_suffix(".py"),repo/rel/"__init__.py"):
            p=candidate.resolve()
            if p.is_file() and repo in p.parents and p!=test and p not in out:
                out.append(p)
    return out

def _symbol_at(path:pathlib.Path, line:int|None)->dict[str,Any]|None:
    if line is None:
        return None
    tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
    candidates=[]
    for node in ast.walk(tree):
        if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            continue
        start=getattr(node,"lineno",None)
        end=getattr(node,"end_lineno",None) or start
        if isinstance(start,int) and isinstance(end,int) and start<=line<=end:
            candidates.append((end-start,start,type(node).__name__,node.name))
    if not candidates:
        return None
    candidates.sort()
    span,start,kind,name=candidates[0]
    return {"name":name,"kind":kind,"lineno":start,"span_lines":span+1}

def _traceback_frames(repo:pathlib.Path, text:str, tests:set[pathlib.Path])->list[tuple[pathlib.Path,int]]:
    rows=[]
    for raw,line_s in re.findall(r'File "([^"]+\.py)", line (\d+)',text):
        p=pathlib.Path(raw)
        if not p.is_absolute():
            p=repo/p
        p=p.resolve()
        if not p.is_file() or repo not in p.parents or p in tests:
            continue
        row=(p,int(line_s))
        if row not in rows:
            rows.append(row)
    return rows

def localize(args:Mapping[str,Any], root:str|os.PathLike[str])->dict[str,Any]:
    repo=pathlib.Path(root).resolve()
    if not isinstance(args,Mapping):
        raise FailureLocalizationError("ARGS_NOT_OBJECT")
    raw=args.get("test_paths") or []
    if not isinstance(raw,list) or not raw:
        raise FailureLocalizationError("TEST_PATHS_REQUIRED")
    tests=[_safe_file(repo,x) for x in raw]
    timeout_s=max(1,min(int(args.get("timeout_s",20)),120))
    test_set=set(tests)

    failures=[]
    candidate_rows=[]
    seen=set()
    for test in tests:
        result=_run(repo,test,timeout_s)
        rel_test=str(test.relative_to(repo)).replace("\\","/")
        if result["timed_out"]:
            failures.append({"test_path":rel_test,"status":"TIMEOUT"})
            continue
        if result["returncode"]==0:
            continue
        text=result["stdout"]+"\n"+result["stderr"]
        failures.append({
            "test_path":rel_test,
            "status":"FAILED",
            "evidence_sha256":_sha(_stable_evidence(text).encode("utf-8")),
        })

        frames=_traceback_frames(repo,text,test_set)
        # Python tracebacks are outer-to-inner; use the innermost local frame first.
        for reverse_index,(path,line) in enumerate(reversed(frames)):
            rel=str(path.relative_to(repo)).replace("\\","/")
            symbol=_symbol_at(path,line)
            key=(rel,line,json.dumps(symbol,sort_keys=True))
            if key in seen:
                continue
            seen.add(key)
            candidate_rows.append({
                "source_path":rel,
                "line":line,
                "symbol":symbol,
                "evidence_kind":"TRACEBACK_FRAME",
                "evidence_rank":reverse_index,
                "causal_supported":False,
            })

        for path in _local_imports(repo,test):
            rel=str(path.relative_to(repo)).replace("\\","/")
            key=(rel,None,"null")
            if key in seen:
                continue
            seen.add(key)
            candidate_rows.append({
                "source_path":rel,
                "line":None,
                "symbol":None,
                "evidence_kind":"FAILING_TEST_LOCAL_IMPORT",
                "evidence_rank":1000,
                "causal_supported":False,
            })

    candidate_rows.sort(key=lambda row:(
        int(row["evidence_rank"]),
        str(row["source_path"]),
        -1 if row["line"] is None else int(row["line"]),
    ))
    status=(
        "NO_FAILURES_OBSERVED"
        if not failures
        else "PASS__OBSERVABLE_FAILURE_CANDIDATES_LOCALIZED"
        if candidate_rows
        else "OPEN__FAILURE_OBSERVED_NO_REPOSITORY_LOCAL_CANDIDATE"
    )
    return {
        "schema":SCHEMA,
        "status":status,
        "pass":status!="OPEN__FAILURE_OBSERVED_NO_REPOSITORY_LOCAL_CANDIDATE",
        "failure_count":len(failures),
        "failures":failures,
        "candidate_count":len(candidate_rows),
        "candidates":candidate_rows,
        "rule":"OBSERVABLE_EVIDENCE_TO_CANDIDATE_LOCUS_ONLY__NO_CAUSAL_CLAIM",
        "model_dependency_count":0,
        "external_capability_provider_count":0,
        "incremental_spend_usd":0,
        "terminal_authority":False,
    }

def run(args:Mapping[str,Any], root:str|os.PathLike[str])->dict[str,Any]:
    repo=pathlib.Path(root).resolve()
    output=(repo/str(args.get("output_path") or "")).resolve()
    if output==repo or repo not in output.parents:
        raise FailureLocalizationError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    result=localize(args,root)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    result["output_path"]=str(output.relative_to(repo)).replace("\\","/")
    result["output_sha256"]=_sha(output.read_bytes())
    result["output_verified"]=True
    return result
