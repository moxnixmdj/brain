"""Bounded Python repair with held-out source-grounded semantic acceptance V9.

Flow:
1. Compile every raw task obligation into an exact supported semantic cell or fail closed.
2. Run the verified provenance-guided repair using only preexisting caller-supplied tests.
3. Realize the repair only in an isolated copied workspace with hash-checked patches.
4. Generate the semantic acceptance program only after repair generation is complete.
5. Execute regression + semantic acceptance through the content-addressed V7 measurement.
6. Authorize success only if the measured objective gate clears.

The semantic acceptance program is never supplied to the repair search.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PYTHON_SEMANTIC_REPAIR_ACCEPTANCE_CONTROLLER_V1"
CAPABILITY_ID="python.software.repair.semantic_acceptance.v1"
MODEL_DEPENDENCY_COUNT=0
EXTERNAL_MODEL_RUNTIME_CALLS=0

class SemanticRepairAcceptanceError(RuntimeError):
    pass

def _load(path:pathlib.Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise SemanticRepairAcceptanceError("MODULE_LOAD_FAILED:"+str(path))
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

_HERE=pathlib.Path(__file__).resolve()
_V8=_load(_HERE.with_name("python_repair_measured_acceptance_controller_v1.py"),"_brain_v9_v8")
_SEM=_load(_HERE.with_name("python_software_request_semantic_acceptance_v1.py"),"_brain_v9_semantic")

def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def _rel(root:pathlib.Path,path:pathlib.Path)->str:
    return str(path.relative_to(root)).replace("\\","/")

def _safe_output(repo:pathlib.Path,raw:Any)->pathlib.Path:
    p=(repo/str(raw or "")).resolve()
    if p==repo or repo not in p.parents:
        raise SemanticRepairAcceptanceError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    return p

def _write_result(repo:pathlib.Path,output:pathlib.Path,result:dict[str,Any])->dict[str,Any]:
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    raw=output.read_bytes()
    return {
        **result,
        "output_path":_rel(repo,output),
        "output_sha256":_sha(raw),
        "output_verified":True,
    }

def _runner_source(regression_argv:list[str],semantic_path:str)->str:
    payload=json.dumps(regression_argv,ensure_ascii=False)
    return f"""from __future__ import annotations
import json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent
REGRESSION=json.loads({payload!r})
def run(argv):
    p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True)
    if p.stdout:
        sys.stdout.write(p.stdout)
    if p.stderr:
        sys.stderr.write(p.stderr)
    if p.returncode!=0:
        raise SystemExit(p.returncode)
run(REGRESSION)
run([sys.executable,{semantic_path!r}])
print("V9_COMBINED_ACCEPTANCE_PASS")
"""

def run(args:Mapping[str,Any],root:str|os.PathLike[str])->dict[str,Any]:
    if not isinstance(args,Mapping):
        raise SemanticRepairAcceptanceError("ARGS_NOT_OBJECT")
    repo=pathlib.Path(root).resolve()
    output=_safe_output(repo,args.get("output_path"))
    task_text=str(args.get("task_text") or "").strip()
    if not task_text:
        raise SemanticRepairAcceptanceError("TASK_TEXT_REQUIRED")

    compilation=_SEM.compile_request(task_text)
    if compilation.get("coverage_complete") is not True:
        return _write_result(repo,output,{
            "schema":SCHEMA,
            "capability_id":CAPABILITY_ID,
            "status":"OPEN__SEMANTIC_ACCEPTANCE_RESIDUALS",
            "pass":False,
            "repair_attempted":False,
            "repair_pass":False,
            "acceptance_stop_authorized":False,
            "semantic_coverage_complete":False,
            "semantic_compiler_payload_sha256":compilation.get("compiler_payload_sha256"),
            "semantic_residual_obligation_ids":compilation.get("residual_obligation_ids") or [],
            "semantic_compile_errors":compilation.get("compile_errors") or [],
            "model_dependency_count":0,
            "external_general_purpose_model_runtime_dependency_count":0,
            "incremental_spend_usd":0,
            "terminal_authority":False,
            "hard_nonclaims":[
                "UNSUPPORTED_RAW_TASK_SEMANTICS_BLOCK_BEFORE_REPAIR",
                "NO_GENERAL_NATURAL_LANGUAGE_SEMANTIC_COMPLETENESS",
                "NO_FRONTIERCODE_SCORE_OR_TERMINAL_AUTHORITY",
            ],
        })

    source_root=_V8._safe_dir(repo,args.get("source_root","."))
    test_paths=[_V8._safe_file(repo,x) for x in (args.get("test_paths") or [])]
    if not test_paths:
        raise SemanticRepairAcceptanceError("TEST_PATHS_REQUIRED")
    argv=[str(x) for x in (
        args.get("test_argv")
        or [sys.executable]+[_rel(repo,p) for p in test_paths]
    )]
    timeout=max(1,min(int(args.get("timeout_s",20)),120))

    intermediate=output.parent/(".v9_repair_"+output.name)
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
        repair=_V8._REPAIR.run(repair_args,repo)
    finally:
        if intermediate.exists():
            intermediate.unlink()

    if repair.get("source_restored") is not True:
        raise SemanticRepairAcceptanceError("REPAIR_SOURCE_RESTORATION_NOT_PROVED")
    if repair.get("pass") is not True:
        return _write_result(repo,output,{
            "schema":SCHEMA,
            "capability_id":CAPABILITY_ID,
            "status":"OPEN__NO_VERIFIED_REPAIR_IN_BOUNDED_SEARCH",
            "pass":False,
            "repair_attempted":True,
            "repair_pass":False,
            "acceptance_stop_authorized":False,
            "semantic_coverage_complete":True,
            "semantic_compiler_payload_sha256":compilation.get("compiler_payload_sha256"),
            "semantic_cell_ids":[x["cell_id"] for x in compilation.get("cells") or []],
            "repair_status":repair.get("status"),
            "source_restored":True,
            "model_dependency_count":0,
            "external_general_purpose_model_runtime_dependency_count":0,
            "incremental_spend_usd":0,
            "terminal_authority":False,
            "hard_nonclaims":[
                "NO_REPAIR_FOUND_MEANS_ONLY_BOUNDED_SEARCH_EXHAUSTED",
                "NO_FRONTIERCODE_SCORE_OR_TERMINAL_AUTHORITY",
            ],
        })

    patches=repair.get("patches") or []
    if not isinstance(patches,list) or not patches:
        raise SemanticRepairAcceptanceError("REPAIR_PATCHES_MISSING")
    rel_tests,candidate_argv=_V8._candidate_test_layout(
        repo,source_root,test_paths,argv
    )
    semantic_program=_SEM.render_test(compilation)
    semantic_program_bytes=semantic_program.encode("utf-8")
    semantic_program_sha=_sha(semantic_program_bytes)
    compiler_blob_sha=_sha(pathlib.Path(_SEM.__file__).read_bytes())

    with tempfile.TemporaryDirectory(prefix="brain-v9-") as td:
        temp_root=pathlib.Path(td)
        candidate_root=temp_root/"candidate"
        realized=_V8._realize_candidate(repo,source_root,patches,candidate_root)

        semantic_name="__brain_v9_semantic_acceptance.py"
        runner_name="__brain_v9_combined_acceptance.py"
        semantic_path=candidate_root/semantic_name
        runner_path=candidate_root/runner_name
        if semantic_path.exists() or runner_path.exists():
            raise SemanticRepairAcceptanceError("VERIFIER_PATH_COLLISION")
        semantic_path.write_bytes(semantic_program_bytes)
        runner_source=_runner_source(candidate_argv,semantic_name)
        runner_path.write_text(runner_source,encoding="utf-8")

        measurement=_V8._MEASURE.run({
            "source_root":"candidate",
            "test_paths":rel_tests+[semantic_name,runner_name],
            "test_argv":[sys.executable,runner_name],
            "output_path":"measurement.json",
            "timeout_s":timeout,
        },temp_root)

        measured_acceptance=_V8._ACCEPT.evaluate_from_receipt(
            "tests_pass must be true.\npython_parse_ok must be true.",
            measurement_receipt_path="measurement.json",
            root=temp_root,
        )
        accepted=(
            measured_acceptance.get("acceptance_stop_authorized") is True
            and compilation.get("coverage_complete") is True
        )

        result={
            "schema":SCHEMA,
            "capability_id":CAPABILITY_ID,
            "status":(
                "PASS__REPAIR_CLEARS_SOURCE_GROUNDED_SEMANTIC_ACCEPTANCE"
                if accepted
                else "OPEN__REPAIRED_CANDIDATE_FAILS_MEASURED_SEMANTIC_ACCEPTANCE"
            ),
            "pass":accepted,
            "repair_attempted":True,
            "repair_pass":True,
            "acceptance_stop_authorized":accepted,
            "semantic_coverage_complete":True,
            "semantic_compiler_payload_sha256":compilation.get("compiler_payload_sha256"),
            "semantic_compiler_runtime_sha256":compiler_blob_sha,
            "semantic_acceptance_program_sha256":semantic_program_sha,
            "semantic_cell_ids":[x["cell_id"] for x in compilation.get("cells") or []],
            "semantic_cell_count":len(compilation.get("cells") or []),
            "repair_oracle_test_paths":[_rel(repo,p) for p in test_paths],
            "semantic_acceptance_withheld_from_repair_oracle":True,
            "winner_mode":repair.get("winner_mode"),
            "realized_patches":realized,
            "candidate_subject_snapshot_sha256":(measurement.get("subject") or {}).get("snapshot_sha256"),
            "measurement_receipt_payload_sha256":measurement.get("receipt_payload_sha256"),
            "measurement_program_sha256":measurement.get("measurement_program_sha256"),
            "measurement_spec_sha256":measurement.get("measurement_spec_sha256"),
            "measured_fields":measurement.get("measurements"),
            "measured_acceptance_status":measured_acceptance.get("status"),
            "source_restored":repair.get("source_restored") is True,
            "model_dependency_count":0,
            "external_general_purpose_model_runtime_dependency_count":0,
            "incremental_spend_usd":0,
            "terminal_authority":False,
            "hard_nonclaims":[
                "SUPPORTED_SEMANTIC_GRAMMAR_IS_BOUNDED_NOT_GENERAL_NATURAL_LANGUAGE",
                "WITHHELD_SEMANTIC_ACCEPTANCE_IS_NOT_A_STATISTICAL_GENERALIZATION_CLAIM",
                "REPAIR_SEARCH_REMAINS_BOUNDED_PYTHON_AST_SEARCH",
                "NO_TEST_PASS_EQUALS_GENERAL_MERGEABILITY",
                "NO_FRONTIERCODE_SCORE_OR_TERMINAL_AUTHORITY",
            ],
        }
    return _write_result(repo,output,result)
