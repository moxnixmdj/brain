from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import tempfile
from typing import Any, Mapping

from canonical.runtime.bound_capabilities import python_repair_measured_acceptance_controller_v1 as v8
from canonical.runtime import python_request_acceptance_union_v1 as union

SCHEMA="PROJECT_BRAIN_PYTHON_REPAIR_SEMANTIC_ACCEPTANCE_CONTROLLER_V1"
CAPABILITY_ID="python.software.repair.semantic_acceptance.v1"
MODEL_DEPENDENCY_COUNT=0
EXTERNAL_MODEL_RUNTIME_CALLS=0

class SemanticRepairError(RuntimeError):
    pass

def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def _manifest(root:pathlib.Path)->tuple[list[dict[str,Any]],str]:
    return v8._MEASURE._tree_manifest(root,max_files=20000,max_bytes=500_000_000)

def run(args:Mapping[str,Any],root:str|os.PathLike[str])->dict[str,Any]:
    if not isinstance(args,Mapping):
        raise SemanticRepairError("ARGS_NOT_OBJECT")
    repo=pathlib.Path(root).resolve()
    source_root=v8._safe_dir(repo,args.get("source_root","."))
    test_paths=[v8._safe_file(repo,x) for x in (args.get("test_paths") or [])]
    if not test_paths:
        raise SemanticRepairError("TEST_PATHS_REQUIRED")
    argv=[str(x) for x in (args.get("test_argv") or v8._REPAIR._PATCH.suite_argv(sys.executable,*test_paths))]
    task_text=str(args.get("task_text") or "").strip()
    if not task_text:
        raise SemanticRepairError("TASK_TEXT_REQUIRED")
    output=v8._safe_output(repo,args.get("output_path"))
    timeout=max(1,min(int(args.get("timeout_s",20)),120))

    baseline_manifest,baseline_sha=_manifest(source_root)
    intermediate=output.parent/(".v9_repair_"+output.name)
    repair_args={
      "source_root":v8._rel(repo,source_root) if source_root!=repo else ".",
      "test_paths":[v8._rel(repo,p) for p in test_paths],
      "test_argv":argv,
      "output_path":v8._rel(repo,intermediate),
      "timeout_s":timeout,
      "max_guided_files":args.get("max_guided_files",4),
      "max_guided_symbols_per_file":args.get("max_guided_symbols_per_file",6),
      "mutations_per_file":args.get("mutations_per_file",24),
      "max_pair_candidates":args.get("max_pair_candidates",1000),
      "max_control_files":args.get("max_control_files",12),
      "max_control_symbols_per_file":args.get("max_control_symbols_per_file",12),
    }
    try:
        repair=v8._REPAIR.run(repair_args,repo)
    finally:
        if intermediate.exists(): intermediate.unlink()

    after_manifest,after_sha=_manifest(source_root)
    source_restored=(baseline_manifest==after_manifest and baseline_sha==after_sha and repair.get("source_restored") is True)
    if not source_restored:
        raise SemanticRepairError("REPAIR_SOURCE_RESTORATION_NOT_PROVED")

    if repair.get("pass") is not True:
        result={
          "schema":SCHEMA,"capability_id":CAPABILITY_ID,
          "status":"OPEN__NO_VERIFIED_REPAIR_IN_BOUNDED_SEARCH","pass":False,
          "repair_pass":False,"acceptance_stop_authorized":False,
          "repair_status":repair.get("status"),"repair_summary":repair,
          "baseline_snapshot_sha256":baseline_sha,"source_restored":True,
          "model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,
          "incremental_spend_usd":0,"terminal_authority":False,
          "hard_nonclaims":["NO_REPAIR_FOUND_MEANS_ONLY_BOUNDED_SEARCH_EXHAUSTED","NO_FRONTIERCODE_SCORE_OR_TERMINAL_AUTHORITY"],
        }
    else:
        patches=repair.get("patches") or []
        if not isinstance(patches,list) or not patches:
            raise SemanticRepairError("REPAIR_PATCHES_MISSING")
        rel_tests,candidate_argv=v8._candidate_test_layout(repo,source_root,test_paths,argv)
        with tempfile.TemporaryDirectory(prefix="brain-v9-") as td:
            temp_root=pathlib.Path(td)
            candidate_root=temp_root/"candidate"
            realized=v8._realize_candidate(repo,source_root,patches,candidate_root)
            measurement=v8._MEASURE.run({
              "source_root":"candidate",
              "test_paths":rel_tests,
              "test_argv":candidate_argv,
              "output_path":"measurement.json",
              "timeout_s":timeout,
            },temp_root)
            acceptance=union.evaluate_union(
              task_text,
              measurement_receipt_path="measurement.json",
              receipt_root=temp_root,
              baseline_root=source_root,
              candidate_root=candidate_root,
              expected_baseline_snapshot_sha256=baseline_sha,
              response_text=(str(args["response_text"]) if args.get("response_text") is not None else None),
            )
            accepted=acceptance.get("acceptance_stop_authorized") is True
            result={
              "schema":SCHEMA,"capability_id":CAPABILITY_ID,
              "status":"PASS__REPAIR_REALIZED_MEASURED_AND_COMPLETE_REQUEST_ACCEPTANCE" if accepted else "OPEN__REPAIR_FOUND_BUT_REQUEST_ACCEPTANCE_NOT_COMPLETE",
              "pass":accepted,"repair_pass":True,"acceptance_stop_authorized":accepted,
              "repair_status":repair.get("status"),"winner_mode":repair.get("winner_mode"),
              "realized_patches":realized,
              "baseline_snapshot_sha256":baseline_sha,
              "candidate_subject_snapshot_sha256":(measurement.get("subject") or {}).get("snapshot_sha256"),
              "measurement_receipt_payload_sha256":measurement.get("receipt_payload_sha256"),
              "measurement_program_sha256":measurement.get("measurement_program_sha256"),
              "measurement_spec_sha256":measurement.get("measurement_spec_sha256"),
              "measured_fields":measurement.get("measurements"),
              "acceptance_status":acceptance.get("status"),
              "acceptance_payload_sha256":acceptance.get("acceptance_payload_sha256"),
              "objective_route_obligation_ids":acceptance.get("objective_route_obligation_ids") or [],
              "semantic_residual_obligation_ids":acceptance.get("semantic_residual_obligation_ids") or [],
              "unbound_obligation_ids":acceptance.get("unbound_obligation_ids") or [],
              "failed_obligation_ids":acceptance.get("failed_obligation_ids") or [],
              "obligation_results":acceptance.get("obligation_results") or [],
              "source_restored":True,
              "model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,
              "incremental_spend_usd":0,"terminal_authority":False,
              "hard_nonclaims":[
                "ONLY_MEASURED_OBJECTIVE_ROUTES_AND_EXPLICIT_SOURCE_GROUNDED_SEMANTIC_CELLS_CAN_CLEAR",
                "UNRECOGNIZED_OR_AMBIGUOUS_RAW_TASK_SEGMENTS_REMAIN_BLOCKING",
                "SEMANTIC_FILE_PATHS_ARE_RELATIVE_TO_THE_DECLARED_SOURCE_ROOT",
                "NO_ARBITRARY_PATCH_SEARCH_COMPLETENESS",
                "NO_NON_PYTHON_GENERALIZATION",
                "NO_GENERAL_MERGEABILITY_OR_FRONTIERCODE_SCORE_AUTHORITY",
              ],
            }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    raw=output.read_bytes()
    return {**result,"output_path":v8._rel(repo,output),"output_sha256":_sha(raw),"output_verified":True}