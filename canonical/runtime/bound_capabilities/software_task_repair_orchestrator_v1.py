#!/usr/bin/env python3
"""Fail-closed end-to-end software task repair orchestrator.

Composition:
raw task text -> explicit test-bound acceptance contract -> bounded multi-file
repair loop -> replayed candidate diff.

Repair is forbidden when the acceptance contract is incomplete.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import tempfile
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_SOFTWARE_TASK_REPAIR_ORCHESTRATOR_V1"

class SoftwareTaskRepairError(RuntimeError):
    pass

def _load_sibling(filename:str,module_name:str):
    path=pathlib.Path(__file__).resolve().with_name(filename)
    if not path.is_file():
        raise SoftwareTaskRepairError("SIBLING_RUNTIME_MISSING:"+filename)
    spec=importlib.util.spec_from_file_location(module_name,path)
    if spec is None or spec.loader is None:
        raise SoftwareTaskRepairError("SIBLING_RUNTIME_LOAD_FAILED:"+filename)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def _safe_output(root:pathlib.Path,raw:Any)->pathlib.Path:
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise SoftwareTaskRepairError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    return p

def _validate_source_paths(root:pathlib.Path,raw:Any)->None:
    if raw is None:
        return
    if not isinstance(raw,list) or not raw:
        raise SoftwareTaskRepairError("SOURCE_PATHS_INVALID")
    for item in raw:
        p=(root/str(item or "")).resolve()
        if (
            p==root
            or root not in p.parents
            or not p.is_file()
            or p.is_symlink()
            or p.suffix!=".py"
        ):
            raise SoftwareTaskRepairError("SOURCE_PATH_INVALID:"+str(item))

def run(args:Mapping[str,Any],root:str|os.PathLike[str])->dict[str,Any]:
    repo=pathlib.Path(root).resolve()
    if not isinstance(args,Mapping):
        raise SoftwareTaskRepairError("ARGS_NOT_OBJECT")
    task_text=str(args.get("task_text") or "").strip()
    if not task_text:
        raise SoftwareTaskRepairError("TASK_TEXT_REQUIRED")
    test_paths=args.get("test_paths")
    if not isinstance(test_paths,list) or not test_paths:
        raise SoftwareTaskRepairError("TEST_PATHS_REQUIRED")
    output=_safe_output(repo,args.get("output_path"))
    _validate_source_paths(repo,args.get("source_paths"))

    acceptance=_load_sibling(
        "software_task_acceptance_compiler_v1.py",
        "project_brain_software_task_acceptance_v1",
    )
    repair=_load_sibling(
        "python_test_guided_repair_loop_v1.py",
        "project_brain_python_repair_loop_v1",
    )

    with tempfile.TemporaryDirectory(prefix=".brain_task_repair_",dir=repo) as td:
        temp=pathlib.Path(td)
        acceptance_rel=str((temp/"acceptance.json").relative_to(repo)).replace("\\","/")
        acceptance_result=acceptance.run({
            "task_text":task_text,
            "test_paths":test_paths,
            "output_path":acceptance_rel,
        },repo)
        acceptance_bytes=(temp/"acceptance.json").read_bytes()

        base={
            "schema":SCHEMA,
            "task_text":task_text,
            "task_sha256":_sha(task_text.encode("utf-8")),
            "acceptance_status":acceptance_result["status"],
            "acceptance_complete":bool(acceptance_result["complete"]),
            "acceptance_obligation_count":acceptance_result["obligation_count"],
            "acceptance_bound_obligation_count":acceptance_result["bound_obligation_count"],
            "acceptance_obligations":acceptance_result["obligations"],
            "acceptance_receipt_sha256":_sha(acceptance_bytes),
            "repair_executed":False,
            "model_dependency_count":0,
            "external_capability_provider_count":0,
            "incremental_spend_usd":0,
        }

        if not acceptance_result["complete"]:
            result={
                **base,
                "status":"OPEN__TASK_ACCEPTANCE_INCOMPLETE__REPAIR_NOT_EXECUTED",
                "pass":False,
                "source_restored":True,
                "hard_nonclaims":[
                    "NO_PATCH_SEARCH_WHEN_EXPLICIT_TASK_ACCEPTANCE_IS_INCOMPLETE",
                    "NO_GENERAL_NATURAL_LANGUAGE_SEMANTIC_AUTHORITY",
                    "NO_MERGEABILITY_OR_FRONTIERCODE_SCORE_AUTHORITY"
                ],
            }
        else:
            repair_rel=str((temp/"repair.json").relative_to(repo)).replace("\\","/")
            repair_args={
                "test_paths":test_paths,
                "output_path":repair_rel,
                "timeout_s":max(1,min(int(args.get("timeout_s",60)),300)),
                "max_sources":max(1,min(int(args.get("max_sources",12)),64)),
                "max_candidates":max(1,min(int(args.get("max_candidates",4000)),30000)),
                "beam_width":max(1,min(int(args.get("beam_width",12)),128)),
                "max_edits":max(1,min(int(args.get("max_edits",2)),2)),
            }
            if "source_paths" in args:
                repair_args["source_paths"]=args.get("source_paths")
            if "test_argv" in args:
                repair_args["test_argv"]=args.get("test_argv")
            try:
                repair_result=repair.run(repair_args,repo)
            except Exception as exc:
                if type(exc).__name__=="RepairLoopError" and str(exc)=="BASELINE_ALREADY_PASSES":
                    result={
                        **base,
                        "status":"PASS__EXPLICIT_TASK_ALREADY_SATISFIED_BY_BOUND_TESTS",
                        "pass":True,
                        "repair_executed":True,
                        "repair_action":"NO_PATCH_REQUIRED",
                        "source_restored":True,
                        "hard_nonclaims":[
                            "PASS_IS_LIMITED_TO_THE_EXPLICIT_TEST_BOUND_ACCEPTANCE_CONTRACT",
                            "NO_GENERAL_MERGEABILITY_OR_FRONTIERCODE_SCORE_AUTHORITY"
                        ],
                    }
                else:
                    raise
            else:
                repair_bytes=(temp/"repair.json").read_bytes()
                result={
                    **base,
                    "status":(
                        "PASS__EXPLICIT_TASK_TO_REPLAYED_VERIFIED_CANDIDATE"
                        if repair_result["pass"]
                        else "OPEN__EXPLICIT_TASK_BOUND__NO_VERIFIED_CANDIDATE_IN_BOUNDED_REPAIR"
                    ),
                    "pass":bool(repair_result["pass"]),
                    "repair_executed":True,
                    "repair_status":repair_result["status"],
                    "repair_receipt_sha256":_sha(repair_bytes),
                    "repair_source_selection":repair_result["source_selection"],
                    "repair_source_paths":repair_result["source_paths"],
                    "repair_tested_candidate_count":repair_result["tested_candidate_count"],
                    "source_restored":repair_result["source_restored"],
                    "winning_edit_count":repair_result.get("winning_edit_count"),
                    "winning_chain":repair_result.get("winning_chain"),
                    "candidate_state_sha256":repair_result.get("candidate_state_sha256"),
                    "verification_replays":repair_result.get("verification_replays"),
                    "unified_diff":repair_result.get("unified_diff"),
                    "hard_nonclaims":[
                        "PASS_IS_LIMITED_TO_THE_EXPLICIT_TEST_BOUND_ACCEPTANCE_CONTRACT",
                        "NO_GENERAL_NATURAL_LANGUAGE_SEMANTIC_AUTHORITY",
                        "NO_REPAIR_SEARCH_COMPLETENESS_BEYOND_THE_BOUND_TWO_EDIT_BEAM",
                        "NO_MERGEABILITY_OR_FRONTIERCODE_SCORE_AUTHORITY"
                    ],
                }

    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    raw=output.read_bytes()
    result["output_path"]=str(output.relative_to(repo)).replace("\\","/")
    result["output_sha256"]=_sha(raw)
    result["output_verified"]=True
    return result
