#!/usr/bin/env python3
"""Fail-closed end-to-end software task repair using neutral-plateau repair.

raw task -> explicit test-bound acceptance contract -> strict-or-neutral-plateau
bounded repair -> double replayed candidate patches. Repair never starts when
acceptance is incomplete.
"""
from __future__ import annotations
import hashlib, importlib.util, json, os, pathlib, tempfile
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_SOFTWARE_TASK_NEUTRAL_PLATEAU_ORCHESTRATOR_V1"

class SoftwareTaskRepairError(RuntimeError): pass

def _load_sibling(filename:str,module_name:str):
    path=pathlib.Path(__file__).resolve().with_name(filename)
    if not path.is_file(): raise SoftwareTaskRepairError("SIBLING_RUNTIME_MISSING:"+filename)
    spec=importlib.util.spec_from_file_location(module_name,path)
    if spec is None or spec.loader is None: raise SoftwareTaskRepairError("SIBLING_RUNTIME_LOAD_FAILED:"+filename)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

def _sha(data:bytes)->str: return hashlib.sha256(data).hexdigest()

def _safe_output(root:pathlib.Path,raw:Any)->pathlib.Path:
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents: raise SoftwareTaskRepairError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    return p

def _safe_source_root(root:pathlib.Path,raw:Any)->pathlib.Path:
    p=(root/str(raw or ".")).resolve()
    if p!=root and root not in p.parents: raise SoftwareTaskRepairError("SOURCE_ROOT_OUTSIDE_REPOSITORY")
    if not p.is_dir() or p.is_symlink(): raise SoftwareTaskRepairError("SOURCE_ROOT_INVALID")
    return p

def _rel(root:pathlib.Path,p:pathlib.Path)->str: return str(p.relative_to(root)).replace("\\","/")

def run(args:Mapping[str,Any],root:str|os.PathLike[str])->dict[str,Any]:
    repo=pathlib.Path(root).resolve()
    if not isinstance(args,Mapping): raise SoftwareTaskRepairError("ARGS_NOT_OBJECT")
    task_text=str(args.get("task_text") or "").strip()
    if not task_text: raise SoftwareTaskRepairError("TASK_TEXT_REQUIRED")
    test_paths=args.get("test_paths")
    if not isinstance(test_paths,list) or not test_paths: raise SoftwareTaskRepairError("TEST_PATHS_REQUIRED")
    output=_safe_output(repo,args.get("output_path"))
    source_root=_safe_source_root(repo,args.get("source_root","."))

    acceptance=_load_sibling("software_task_acceptance_compiler_v1.py","project_brain_task_acceptance_v1")
    repair=_load_sibling("python_neutral_plateau_repair_loop_v1.py","project_brain_neutral_plateau_repair_v1")

    with tempfile.TemporaryDirectory(prefix=".brain_strict_task_",dir=repo) as td:
        temp=pathlib.Path(td)
        acc_rel=_rel(repo,temp/"acceptance.json")
        acc=acceptance.run({"task_text":task_text,"test_paths":test_paths,"output_path":acc_rel},repo)
        acc_bytes=(temp/"acceptance.json").read_bytes()
        base={
            "schema":SCHEMA,
            "task_text":task_text,
            "task_sha256":_sha(task_text.encode("utf-8")),
            "acceptance_status":acc["status"],
            "acceptance_complete":bool(acc["complete"]),
            "acceptance_obligation_count":acc["obligation_count"],
            "acceptance_bound_obligation_count":acc["bound_obligation_count"],
            "acceptance_obligations":acc["obligations"],
            "acceptance_receipt_sha256":_sha(acc_bytes),
            "repair_executed":False,
            "model_dependency_count":0,
            "external_capability_provider_count":0,
            "incremental_spend_usd":0,
        }
        if not acc["complete"]:
            result={**base,
                "status":"OPEN__TASK_ACCEPTANCE_INCOMPLETE__REPAIR_NOT_EXECUTED",
                "pass":False,"source_restored":True,
                "hard_nonclaims":[
                    "NO_REPAIR_WHEN_EXPLICIT_TASK_ACCEPTANCE_IS_INCOMPLETE",
                    "NO_GENERAL_NATURAL_LANGUAGE_SEMANTIC_AUTHORITY",
                    "NO_MERGEABILITY_OR_FRONTIERCODE_SCORE_AUTHORITY",
                ]}
        else:
            rep_rel=_rel(repo,temp/"repair.json")
            rep_args={
                "source_root":_rel(repo,source_root) if source_root!=repo else ".",
                "test_paths":test_paths,
                "output_path":rep_rel,
                "timeout_s":max(1,min(int(args.get("timeout_s",30)),300)),
                "max_rounds":max(1,min(int(args.get("max_rounds",6)),20)),
                "max_files":max(1,min(int(args.get("max_files",12)),100)),
                "max_candidates_per_file":max(1,min(int(args.get("max_candidates_per_file",250)),5000)),
                "max_total_candidates":max(1,min(int(args.get("max_total_candidates",4000)),50000)),
                "max_plateau_depth":max(2,min(int(args.get("max_plateau_depth",3)),6)),
                "max_plateau_states":max(1,min(int(args.get("max_plateau_states",100)),5000)),
                "max_plateau_candidates":max(1,min(int(args.get("max_plateau_candidates",1600)),30000)),
            }
            if "test_argv" in args: rep_args["test_argv"]=args["test_argv"]
            try:
                rep=repair.run(rep_args,repo)
            except Exception as exc:
                if type(exc).__name__=="RepairLoopError" and str(exc)=="BASELINE_ALREADY_PASSES":
                    result={**base,
                        "status":"PASS__EXPLICIT_TASK_ALREADY_SATISFIED_BY_BOUND_TESTS",
                        "pass":True,"repair_executed":True,"repair_action":"NO_PATCH_REQUIRED",
                        "source_restored":True,
                        "hard_nonclaims":[
                            "PASS_IS_LIMITED_TO_EXPLICIT_TEST_BOUND_ACCEPTANCE",
                            "NO_GENERAL_MERGEABILITY_OR_FRONTIERCODE_SCORE_AUTHORITY",
                        ]}
                else: raise
            else:
                rep_bytes=(temp/"repair.json").read_bytes()
                result={**base,
                    "status":("PASS__EXPLICIT_TASK_TO_NEUTRAL_PLATEAU_REPLAYED_CANDIDATE"
                              if rep["pass"] else
                              "OPEN__EXPLICIT_TASK_BOUND__NO_COMPLETE_BOUNDED_PLATEAU_REPAIR"),
                    "pass":bool(rep["pass"]),
                    "repair_executed":True,
                    "repair_status":rep["status"],
                    "repair_receipt_sha256":_sha(rep_bytes),
                    "baseline_failure_score":rep["baseline_failure_score"],
                    "accepted_edit_count":rep["accepted_edit_count"],
                    "accepted_edits":rep["accepted_edits"],
                    "repair_rounds":rep["rounds"],
                    "repair_tested_candidate_count":rep["tested_candidate_count"],
                    "verification_replays":rep["final_verification_replays"],
                    "patches":rep["patches"],
                    "source_restored":rep["source_restored"],
                    "hard_nonclaims":[
                        "PASS_IS_LIMITED_TO_EXPLICIT_TEST_BOUND_ACCEPTANCE",
                        "NO_NEUTRAL_PLATEAU_COMPLETENESS_BEYOND_CONFIGURED_DEPTH_AND_BUDGET",
                        "NO_TEMPORARILY_WORSE_INTERMEDIATE_SEARCH",
                        "NO_GENERAL_NATURAL_LANGUAGE_SEMANTIC_AUTHORITY",
                        "NO_MERGEABILITY_OR_FRONTIERCODE_SCORE_AUTHORITY",
                    ]}

    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    raw=output.read_bytes()
    result["output_path"]=_rel(repo,output); result["output_sha256"]=_sha(raw); result["output_verified"]=True
    return result
