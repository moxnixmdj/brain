"""General scientific raw-resource pipeline V2 with bounded semantic compilation.

V2 preserves V1's lossless task contract, resource discovery, unique-route rule,
verified solver, and artifact materializer. It replaces family-specific routing
heuristics with the independently tested bounded scientific semantic compiler.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import general_scientific_raw_resource_pipeline_v1 as v1
from canonical.runtime import scientific_semantic_compiler_v1 as semantic

SCHEMA="PROJECT_BRAIN_GENERAL_SCIENTIFIC_RAW_RESOURCE_PIPELINE_V2"
MODEL_DEPENDENCY_COUNT=0
EXTERNAL_MODEL_RUNTIME_CALLS=0
NETWORK_DEPENDENCY_COUNT=0


def _fail(reason:str,*,trace=None,details=None,contract=None)->dict[str,Any]:
    out=v1._fail(reason,trace=trace,details=details,contract=contract)
    out["schema"]=SCHEMA
    return out


def compile_task(instruction:str,roots:Any,*,exclude_roots:Any=None)->dict[str,Any]:
    if not isinstance(instruction,str) or not instruction.strip() or len(instruction)>20000:
        return _fail("INSTRUCTION_INVALID")

    contract=v1.raw_contract.compile_contract(
        instruction,
        source_id="general-scientific-raw-task-v2",
        routing_target_effects=["SCIENTIFIC_RESULT_VERIFIED"],
    )
    if contract.get("pass") is not True:
        return _fail("LOSSLESS_RAW_TASK_CONTRACT_FAILED",contract=contract)

    try:
        root_paths=v1.numeric_resources._safe_roots(roots)
        excludes=[] if exclude_roots is None else v1.numeric_resources._safe_roots(exclude_roots)
    except Exception as exc:
        return _fail(type(exc).__name__+":"+str(exc),contract=contract)

    files=v1.numeric_resources._discover(root_paths,excludes)
    candidates=[]; attempts=[]
    for path in files:
        value=v1._read_json(path)
        if value is not None:
            structured=semantic.compile_structured(instruction,value)
            attempts.append({
                "path":str(path),"mode":"STRUCTURED_RESOURCE",
                "status":structured.get("status"),"family":structured.get("family"),
                "reason":structured.get("reason"),"semantic_route":structured.get("semantic_route"),
            })
            if structured.get("status")=="COMPILED":
                candidates.append({
                    "mode":"STRUCTURED_RESOURCE","family":structured["family"],
                    "path":str(path),"task_problem":structured["task_problem"],
                    "semantic_compiler_receipt":structured,
                })
                continue

        try:
            rows=v1.numeric_resources._read_table(path)
        except Exception as exc:
            attempts.append({"path":str(path),"mode":"NUMERIC_TABLE","status":"READ_FAILED","error_type":type(exc).__name__})
            continue
        if len(rows)<4:
            attempts.append({"path":str(path),"mode":"NUMERIC_TABLE","status":"TABLE_INSUFFICIENT_ROWS","row_count":len(rows)})
            continue
        compiled=semantic.compile_numeric(instruction,rows)
        attempts.append({
            "path":str(path),"mode":"NUMERIC_TABLE",
            "status":compiled.get("status"),"family":compiled.get("family"),
            "reason":compiled.get("reason"),"semantic_route":compiled.get("semantic_route"),
            "row_count":len(rows),
        })
        if compiled.get("status")=="COMPILED":
            candidates.append({
                "mode":"NUMERIC_TABLE","family":compiled["family"],
                "path":str(path),"task_problem":compiled["task_problem"],
                "semantic_compiler_receipt":compiled,
            })

    unique=[]; seen=set()
    for row in candidates:
        key=(row["mode"],row["family"],row["path"],v1._sha(row["task_problem"]))
        if key not in seen:
            seen.add(key); unique.append(row)

    if not unique:
        return _fail("NO_UNIQUE_TYPED_SCIENTIFIC_ROUTE",trace=attempts,contract=contract,
                     details={"discovered_file_count":len(files),"candidate_count":0})
    if len(unique)!=1:
        return _fail("AMBIGUOUS_MULTIPLE_TYPED_SCIENTIFIC_ROUTES",trace=attempts,contract=contract,
                     details={"discovered_file_count":len(files),"candidate_count":len(unique),
                              "candidates":[{"mode":x["mode"],"family":x["family"],"path":x["path"]} for x in unique]})

    selected=unique[0]
    receipt={
        "schema":SCHEMA,"status":"PASS__UNIQUE_TYPED_SCIENTIFIC_ROUTE_COMPILED",
        "pass":True,"family":selected["family"],"mode":selected["mode"],
        "selected_path":selected["path"],"task_problem":selected["task_problem"],
        "semantic_compiler_receipt":selected["semantic_compiler_receipt"],
        "raw_task_contract":contract,"attempts":attempts,
        "discovered_file_count":len(files),
        "model_dependency_count":0,"external_model_runtime_calls":0,
        "network_dependency_count":0,"dynamic_code_execution":False,
        "benchmark_identifier_used_for_routing":False,
        "raw_task_acceptance_authority":False,"terminal_authority":False,
    }
    receipt["compile_receipt_sha256"]=v1._sha({
        "family":receipt["family"],"mode":receipt["mode"],
        "selected_path":receipt["selected_path"],"task_problem":receipt["task_problem"],
        "semantic_route":selected["semantic_compiler_receipt"].get("semantic_route"),
        "raw_task_contract_sha256":contract.get("task_contract_sha256"),
    })
    return receipt


def execute(
    instruction:str,
    roots:Any,
    *,
    artifact_specs:Sequence[Mapping[str,Any]]|None=None,
    output_root:str|Path|None=None,
)->dict[str,Any]:
    if (artifact_specs is None)!=(output_root is None):
        return _fail("ARTIFACT_SPECS_AND_OUTPUT_ROOT_MUST_BE_PROVIDED_TOGETHER")
    excludes=[output_root] if output_root is not None else None
    compiled=compile_task(instruction,roots,exclude_roots=excludes)
    if compiled.get("pass") is not True: return compiled

    solved=v1.controller.solve(compiled["task_problem"])
    if solved.get("verified") is not True:
        return _fail("SCIENTIFIC_RESULT_NOT_VERIFIED",contract=compiled.get("raw_task_contract"),
                     details={"compile_receipt":compiled,"solver_receipt":solved})

    materialized=None
    if artifact_specs is not None:
        materialized=v1.artifacts.materialize_artifacts(solved,artifact_specs,output_root)
        if materialized.get("status")!="PASS__DECLARED_SCIENTIFIC_ARTIFACTS_MATERIALIZED_AND_VERIFIED":
            return _fail("SCIENTIFIC_ARTIFACT_MATERIALIZATION_FAILED",contract=compiled.get("raw_task_contract"),
                         details={"compile_receipt":compiled,"solver_receipt":solved,"artifact_receipt":materialized})

    receipt={
        "schema":SCHEMA,"status":"PASS__GENERAL_SCIENTIFIC_RAW_RESOURCE_V2_EXECUTION_VERIFIED",
        "pass":True,"verified":True,"family":compiled["family"],"mode":compiled["mode"],
        "compile_receipt":compiled,"scientific_result":solved,
        "artifact_materialization":materialized,
        "model_dependency_count":0,"external_model_runtime_calls":0,
        "network_dependency_count":0,"dynamic_code_execution":False,
        "benchmark_identifier_used_for_routing":False,
        "raw_task_acceptance_authority":False,"terminal_authority":False,"terminal_credit_delta":0,
    }
    receipt["receipt_sha256"]=v1._sha({
        "family":receipt["family"],"mode":receipt["mode"],
        "compile_receipt_sha256":compiled["compile_receipt_sha256"],
        "scientific_result":solved,"artifact_materialization":materialized,
    })
    return receipt
