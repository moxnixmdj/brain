"""Atomic bounded Python repair -> candidate realization -> measured acceptance V8.

This controller composes only Brain-owned verified mechanisms:
1. provenance-guided bounded Python repair produces candidate diffs and restores source;
2. diffs are realized in an isolated copied workspace and candidate hashes are checked;
3. the realized candidate repository is measured by content-addressed execution;
4. the raw-task objective acceptance gate consumes only that measurement receipt.

No semantic residual is converted into success. No patch is written to the source tree.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
from typing import Any, Mapping

from canonical.runtime import acceptance_clause_v1 as acceptance_clause

SCHEMA="PROJECT_BRAIN_PYTHON_REPAIR_MEASURED_ACCEPTANCE_CONTROLLER_V1"
CAPABILITY_ID="python.software.repair.measured_acceptance.v1"
MODEL_DEPENDENCY_COUNT=0
EXTERNAL_MODEL_RUNTIME_CALLS=0

class RepairAcceptanceError(RuntimeError):
    pass

def _load(path:pathlib.Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RepairAcceptanceError("MODULE_LOAD_FAILED:"+str(path))
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

_HERE=pathlib.Path(__file__).resolve()
_REPAIR=_load(_HERE.with_name("python_provenance_guided_coupled_repair_v1.py"),"_brain_v8_repair")
_MEASURE=_load(_HERE.with_name("python_repository_acceptance_measurement_v1.py"),"_brain_v8_measure")
_ACCEPT=_load(_HERE.parent.parent/"python_measured_objective_acceptance_v1.py","_brain_v8_accept")

def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def _rel(root:pathlib.Path,p:pathlib.Path)->str:
    return str(p.relative_to(root)).replace("\\","/")

def _safe_dir(repo:pathlib.Path,raw:Any)->pathlib.Path:
    p=(repo/str(raw or ".")).resolve()
    if p!=repo and repo not in p.parents:
        raise RepairAcceptanceError("SOURCE_ROOT_OUTSIDE_REPOSITORY")
    if not p.is_dir() or p.is_symlink():
        raise RepairAcceptanceError("SOURCE_ROOT_INVALID")
    return p

def _safe_file(repo:pathlib.Path,raw:Any)->pathlib.Path:
    p=(repo/str(raw or "")).resolve()
    if p==repo or repo not in p.parents or not p.is_file() or p.is_symlink():
        raise RepairAcceptanceError("TEST_PATH_INVALID:"+str(raw))
    return p

def _safe_output(repo:pathlib.Path,raw:Any)->pathlib.Path:
    p=(repo/str(raw or "")).resolve()
    if p==repo or repo not in p.parents:
        raise RepairAcceptanceError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    return p

_HUNK=re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

def _apply_unified_diff(original:str,diff_text:str)->str:
    lines=diff_text.splitlines(keepends=True)
    i=0
    while i<len(lines) and not lines[i].startswith("@@ "):
        i+=1
    if i>=len(lines):
        raise RepairAcceptanceError("PATCH_HUNK_MISSING")
    src=original.splitlines(keepends=True)
    out=[]
    cursor=0
    while i<len(lines):
        header=lines[i].rstrip("\r\n")
        m=_HUNK.match(header)
        if not m:
            raise RepairAcceptanceError("PATCH_HUNK_HEADER_INVALID")
        old_start=int(m.group(1));old_count=int(m.group(2) or "1")
        start_index=old_start-1
        if start_index<cursor or start_index>len(src):
            raise RepairAcceptanceError("PATCH_HUNK_RANGE_INVALID")
        out.extend(src[cursor:start_index])
        cursor=start_index
        consumed=0
        i+=1
        while i<len(lines) and not lines[i].startswith("@@ "):
            row=lines[i]
            if row.startswith("\\ No newline at end of file"):
                i+=1
                continue
            if not row:
                raise RepairAcceptanceError("PATCH_ROW_EMPTY")
            prefix=row[0]
            body=row[1:]
            if prefix==" ":
                if cursor>=len(src) or src[cursor]!=body:
                    raise RepairAcceptanceError("PATCH_CONTEXT_MISMATCH")
                out.append(src[cursor]);cursor+=1;consumed+=1
            elif prefix=="-":
                if cursor>=len(src) or src[cursor]!=body:
                    raise RepairAcceptanceError("PATCH_DELETE_MISMATCH")
                cursor+=1;consumed+=1
            elif prefix=="+":
                out.append(body)
            else:
                raise RepairAcceptanceError("PATCH_ROW_PREFIX_INVALID")
            i+=1
        if consumed!=old_count:
            raise RepairAcceptanceError("PATCH_OLD_COUNT_MISMATCH")
    out.extend(src[cursor:])
    return "".join(out)

def _candidate_test_layout(
    repo:pathlib.Path,source_root:pathlib.Path,test_paths:list[pathlib.Path],argv:list[str]
)->tuple[list[str],list[str]]:
    rel_tests=[]
    for p in test_paths:
        try:
            rel_tests.append(_rel(source_root,p))
        except ValueError as exc:
            raise RepairAcceptanceError("TEST_OUTSIDE_SOURCE_ROOT:"+_rel(repo,p)) from exc
    rewritten=[]
    for token in argv:
        if token==argv[0]:
            rewritten.append(token)
            continue
        raw=pathlib.Path(token)
        candidate=None
        on_disk=False
        try:
            if not raw.is_absolute():
                candidate=(repo/raw).resolve()
            elif raw.is_absolute():
                candidate=raw.resolve()
            on_disk=candidate.is_file()
        except OSError:
            # A test argv token is a command argument, not necessarily a path.
            # ``python3 -c '<harness program>'`` carries a whole test runner in
            # ONE token, and stat() on that name fails with ENAMETOOLONG, which
            # Path.is_file() re-raises instead of answering False.  Such a token
            # is not a file inside the source root, so it must pass through
            # verbatim -- exactly as every other non-file token does -- rather
            # than abort the measurement.
            on_disk=False
        if on_disk and (candidate==source_root or source_root in candidate.parents):
            rewritten.append(_rel(source_root,candidate))
        else:
            rewritten.append(token)
    return rel_tests,rewritten

def _realize_candidate(
    repo:pathlib.Path,source_root:pathlib.Path,patches:list[Mapping[str,Any]],candidate_root:pathlib.Path
)->list[dict[str,Any]]:
    shutil.copytree(
        source_root,candidate_root,
        ignore=shutil.ignore_patterns(".git","__pycache__","*.pyc",".pytest_cache"),
    )
    realized=[]
    for index,row in enumerate(patches):
        if not isinstance(row,Mapping):
            raise RepairAcceptanceError("PATCH_ROW_NOT_OBJECT:"+str(index))
        source_path=str(row.get("source_path") or "")
        original_sha=str(row.get("original_sha256") or "")
        candidate_sha=str(row.get("candidate_sha256") or "")
        diff_text=str(row.get("unified_diff") or "")
        original_path=(repo/source_path).resolve()
        if original_path==repo or repo not in original_path.parents or not original_path.is_file():
            raise RepairAcceptanceError("PATCH_SOURCE_PATH_INVALID:"+source_path)
        try:
            relative=original_path.relative_to(source_root)
        except ValueError as exc:
            raise RepairAcceptanceError("PATCH_SOURCE_OUTSIDE_SOURCE_ROOT:"+source_path) from exc
        target=(candidate_root/relative).resolve()
        if candidate_root not in target.parents or not target.is_file():
            raise RepairAcceptanceError("CANDIDATE_TARGET_INVALID:"+source_path)
        raw=target.read_bytes()
        if _sha(raw)!=original_sha:
            raise RepairAcceptanceError("PATCH_ORIGINAL_SHA_MISMATCH:"+source_path)
        try:
            before=raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RepairAcceptanceError("PATCH_SOURCE_NOT_UTF8:"+source_path) from exc
        after=_apply_unified_diff(before,diff_text)
        after_raw=after.encode("utf-8")
        if _sha(after_raw)!=candidate_sha:
            raise RepairAcceptanceError("PATCH_CANDIDATE_SHA_MISMATCH:"+source_path)
        target.write_bytes(after_raw)
        realized.append({
            "source_path":source_path,
            "candidate_relative_path":str(relative).replace("\\","/"),
            "original_sha256":original_sha,
            "candidate_sha256":candidate_sha,
        })
    return realized

def run(args:Mapping[str,Any],root:str|os.PathLike[str])->dict[str,Any]:
    if not isinstance(args,Mapping):
        raise RepairAcceptanceError("ARGS_NOT_OBJECT")
    repo=pathlib.Path(root).resolve()
    source_root=_safe_dir(repo,args.get("source_root","."))
    test_paths=[_safe_file(repo,x) for x in (args.get("test_paths") or [])]
    if not test_paths:
        raise RepairAcceptanceError("TEST_PATHS_REQUIRED")
    argv=[str(x) for x in (args.get("test_argv") or _REPAIR._PATCH.suite_argv(sys.executable,*test_paths))]
    task_text=str(args.get("task_text") or "").strip()
    if not task_text:
        raise RepairAcceptanceError("TASK_TEXT_REQUIRED")
    # The front door binds the whole goal here.  An explicitly delimited
    # ``where`` clause is the acceptance contract; the preceding sentence is
    # routing metadata only when every one of its words is declared.  Any other
    # shape returns the original lossless text and keeps blocking residuals.
    clause=acceptance_clause.extract(task_text,args)
    task_text=str(clause.get("acceptance_task_text") or task_text).strip()
    if not task_text:
        raise RepairAcceptanceError("TASK_TEXT_REQUIRED")
    output=_safe_output(repo,args.get("output_path"))
    timeout=max(1,min(int(args.get("timeout_s",20)),120))
    intermediate=output.parent/(".v8_repair_"+output.name)
    repair_args={
        "source_root":_rel(repo,source_root) if source_root!=repo else ".",
        "test_paths":[_rel(repo,p) for p in test_paths],
        "test_argv":argv,
        "output_path":_rel(repo,intermediate),
        "timeout_s":timeout,
        "max_guided_files":args.get("max_guided_files",4),
        "max_guided_symbols_per_file":args.get("max_guided_symbols_per_file",6),
        "mutations_per_file":args.get("mutations_per_file",24),
        "max_pair_candidates":args.get("max_pair_candidates",1000),
        "max_control_files":args.get("max_control_files",12),
        "max_control_symbols_per_file":args.get("max_control_symbols_per_file",12),
    }
    try:
        repair=_REPAIR.run(repair_args,repo)
    finally:
        if intermediate.exists():
            intermediate.unlink()
    if repair.get("source_restored") is not True:
        raise RepairAcceptanceError("REPAIR_SOURCE_RESTORATION_NOT_PROVED")
    if repair.get("pass") is not True:
        result={
            "schema":SCHEMA,"capability_id":CAPABILITY_ID,
            "status":"OPEN__NO_VERIFIED_REPAIR_IN_BOUNDED_SEARCH","pass":False,
            "repair_pass":False,"acceptance_stop_authorized":False,
            "repair_status":repair.get("status"),"repair_summary":repair,
            "model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,
            "incremental_spend_usd":0,"source_restored":True,"terminal_authority":False,
            "hard_nonclaims":["NO_REPAIR_FOUND_MEANS_ONLY_BOUNDED_SEARCH_EXHAUSTED","NO_FRONTIERCODE_SCORE_OR_TERMINAL_CREDIT"],
        }
    else:
        patches=repair.get("patches") or []
        if not isinstance(patches,list) or not patches:
            raise RepairAcceptanceError("REPAIR_PATCHES_MISSING")
        rel_tests,candidate_argv=_candidate_test_layout(repo,source_root,test_paths,argv)
        with tempfile.TemporaryDirectory(prefix="brain-v8-") as td:
            temp_root=pathlib.Path(td)
            candidate_root=temp_root/"candidate"
            realized=_realize_candidate(repo,source_root,patches,candidate_root)
            measurement=_MEASURE.run({
                "source_root":"candidate",
                "test_paths":rel_tests,
                "test_argv":candidate_argv,
                "output_path":"measurement.json",
                "timeout_s":timeout,
            },temp_root)
            acceptance=_ACCEPT.evaluate_from_receipt(
                task_text,
                measurement_receipt_path="measurement.json",
                root=temp_root,
                response_text=(str(args["response_text"]) if args.get("response_text") is not None else None),
            )
            accepted=acceptance.get("acceptance_stop_authorized") is True
            result={
                "schema":SCHEMA,"capability_id":CAPABILITY_ID,
                "status":"PASS__REPAIR_REALIZED_MEASURED_AND_ACCEPTED" if accepted else "OPEN__REPAIR_FOUND_BUT_MEASURED_ACCEPTANCE_NOT_CLEARED",
                "pass":accepted,"repair_pass":True,
                "acceptance_stop_authorized":accepted,
                "repair_status":repair.get("status"),
                "winner_mode":repair.get("winner_mode"),
                "realized_patches":realized,
                "candidate_subject_snapshot_sha256":(measurement.get("subject") or {}).get("snapshot_sha256"),
                "measurement_receipt_payload_sha256":measurement.get("receipt_payload_sha256"),
                "measurement_program_sha256":measurement.get("measurement_program_sha256"),
                "measurement_spec_sha256":measurement.get("measurement_spec_sha256"),
                "measured_fields":measurement.get("measurements"),
                "acceptance_status":acceptance.get("status"),
                "semantic_residual_obligation_ids":((acceptance.get("objective_result") or {}).get("semantic_residual_obligation_ids") or []),
                "source_restored":repair.get("source_restored") is True,
                "model_dependency_count":0,
                "external_general_purpose_model_runtime_dependency_count":0,
                "incremental_spend_usd":0,
                "terminal_authority":False,
                "hard_nonclaims":[
                    "NO_GENERAL_NATURAL_LANGUAGE_SEMANTIC_COMPLETENESS",
                    "NO_ARBITRARY_PATCH_SEARCH_COMPLETENESS",
                    "NO_NON_PYTHON_SUPPORT",
                    "NO_TEST_PASS_EQUALS_GENERAL_MERGEABILITY",
                    "NO_FRONTIERCODE_SCORE_OR_TERMINAL_CREDIT",
                ],
            }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    raw=output.read_bytes()
    return {
        **result,
        "output_path":_rel(repo,output),
        "output_sha256":_sha(raw),
        "output_verified":True,
    }
