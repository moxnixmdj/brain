"""Benchmark-independent raw scientific task/resource pipeline V1.

Compiles an exact raw instruction plus bounded local resources into one of the
already-verified Brain-owned scientific controller families, executes it, verifies
the result, and optionally materializes declared artifacts.

This layer adds no model cognition, network dependency, benchmark routing, or
dynamic code. It fails closed unless exactly one typed scientific route is
supported by the instruction/resource pair.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from canonical.runtime import general_scientific_capability_controller_v1 as controller
from canonical.runtime import lossless_raw_task_contract_v1 as raw_contract
from canonical.runtime import scientific_artifact_contract_v1 as artifacts
from canonical.runtime import scientific_numeric_resource_pipeline_v1 as numeric_resources
from canonical.runtime import scientific_numeric_task_compiler_v1 as numeric_compiler

SCHEMA="PROJECT_BRAIN_GENERAL_SCIENTIFIC_RAW_RESOURCE_PIPELINE_V1"
MODEL_DEPENDENCY_COUNT=0
EXTERNAL_MODEL_RUNTIME_CALLS=0
NETWORK_DEPENDENCY_COUNT=0
RULE_CUES=re.compile(r"\b(rule|rules|predicate|predicates|classify|classification|conjunctive|positive|negative)\b",re.I)
ABDUCTION_CUES=re.compile(r"\b(abduct|abduction|abductive|residual|hypothesis|hypotheses|explanation|explain|cause|diagnosis|mechanism|reachable|sufficient)\b",re.I)


def _canon(value:Any)->str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False,default=str)


def _sha(value:Any)->str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _fail(reason:str,*,trace=None,details=None,contract=None)->dict[str,Any]:
    out={
        "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"verified":False,
        "reason":reason,"trace":list(trace or []),
        "model_dependency_count":0,"external_model_runtime_calls":0,
        "network_dependency_count":0,"dynamic_code_execution":False,
        "benchmark_identifier_used_for_routing":False,
        "raw_task_acceptance_authority":False,
        "terminal_authority":False,"terminal_credit_delta":0,
    }
    if details is not None:
        out["details"]=details
    if contract is not None:
        out["raw_task_contract"]=contract
    return out


def _read_json(path:Path)->Any:
    if path.suffix.lower()!=".json":
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _rule_problem(value:Any)->dict[str,Any]|None:
    if not isinstance(value,Mapping):
        return None
    raw=value.get("rule_problem") if isinstance(value.get("rule_problem"),Mapping) else value
    if not isinstance(raw,Mapping):
        return None
    if not all(k in raw for k in ("predicates","examples","emit")):
        return None
    if not isinstance(raw.get("predicates"),list) or not isinstance(raw.get("examples"),list) or not isinstance(raw.get("emit"),Mapping):
        return None
    problem={
        "predicates":raw["predicates"],
        "examples":raw["examples"],
        "emit":dict(raw["emit"]),
    }
    sig=controller.infer_signature(problem)
    return problem if sig.get("family")==controller.RULE else None


def _abduction_problem(value:Any)->dict[str,Any]|None:
    if not isinstance(value,Mapping):
        return None
    raw=value.get("abduction") if isinstance(value.get("abduction"),Mapping) else value
    if not isinstance(raw,Mapping):
        return None
    if not all(k in raw for k in ("targets","baseline_facts","implications")):
        return None
    problem={"abduction":dict(raw)}
    sig=controller.infer_signature(problem)
    return problem if sig.get("family")==controller.ABDUCTION else None


def compile_task(instruction:str,roots:Any,*,exclude_roots:Any=None)->dict[str,Any]:
    if not isinstance(instruction,str) or not instruction.strip() or len(instruction)>20000:
        return _fail("INSTRUCTION_INVALID")

    contract=raw_contract.compile_contract(
        instruction,
        source_id="general-scientific-raw-task",
        routing_target_effects=["SCIENTIFIC_RESULT_VERIFIED"],
    )
    if contract.get("pass") is not True:
        return _fail("LOSSLESS_RAW_TASK_CONTRACT_FAILED",contract=contract)

    try:
        root_paths=numeric_resources._safe_roots(roots)
        excludes=[] if exclude_roots is None else numeric_resources._safe_roots(exclude_roots)
    except Exception as exc:
        return _fail(type(exc).__name__+":"+str(exc),contract=contract)

    files=numeric_resources._discover(root_paths,excludes)
    candidates=[]
    attempts=[]
    for path in files:
        value=_read_json(path)

        if RULE_CUES.search(instruction):
            problem=_rule_problem(value)
            if problem is not None:
                candidates.append({
                    "mode":"STRUCTURED_RULE_RESOURCE",
                    "family":controller.RULE,
                    "path":str(path),
                    "task_problem":problem,
                })
                attempts.append({"path":str(path),"mode":"STRUCTURED_RULE_RESOURCE","status":"COMPILED"})
                continue

        if ABDUCTION_CUES.search(instruction):
            problem=_abduction_problem(value)
            if problem is not None:
                candidates.append({
                    "mode":"STRUCTURED_ABDUCTION_RESOURCE",
                    "family":controller.ABDUCTION,
                    "path":str(path),
                    "task_problem":problem,
                })
                attempts.append({"path":str(path),"mode":"STRUCTURED_ABDUCTION_RESOURCE","status":"COMPILED"})
                continue

        try:
            rows=numeric_resources._read_table(path)
        except Exception as exc:
            attempts.append({"path":str(path),"mode":"NUMERIC_TABLE","status":"READ_FAILED","error_type":type(exc).__name__})
            continue
        if len(rows)<4:
            attempts.append({"path":str(path),"mode":"NUMERIC_TABLE","status":"TABLE_INSUFFICIENT_ROWS","row_count":len(rows)})
            continue
        compiled=numeric_compiler.compile_numeric_task(instruction,rows)
        attempts.append({
            "path":str(path),"mode":"NUMERIC_TABLE",
            "status":compiled.get("status"),"family":compiled.get("family"),
            "reason":compiled.get("reason"),"row_count":len(rows),
        })
        if compiled.get("status")=="COMPILED":
            candidates.append({
                "mode":"NUMERIC_TABLE",
                "family":compiled["family"],
                "path":str(path),
                "task_problem":compiled["task_problem"],
                "compiler_receipt":compiled,
            })

    unique=[]
    seen=set()
    for row in candidates:
        key=(row["mode"],row["family"],row["path"],_sha(row["task_problem"]))
        if key not in seen:
            seen.add(key); unique.append(row)

    if not unique:
        return _fail(
            "NO_UNIQUE_TYPED_SCIENTIFIC_ROUTE",
            trace=attempts,contract=contract,
            details={"discovered_file_count":len(files),"candidate_count":0},
        )
    if len(unique)!=1:
        return _fail(
            "AMBIGUOUS_MULTIPLE_TYPED_SCIENTIFIC_ROUTES",
            trace=attempts,contract=contract,
            details={
                "discovered_file_count":len(files),
                "candidate_count":len(unique),
                "candidates":[{"mode":x["mode"],"family":x["family"],"path":x["path"]} for x in unique],
            },
        )

    selected=unique[0]
    receipt={
        "schema":SCHEMA,
        "status":"PASS__UNIQUE_TYPED_SCIENTIFIC_ROUTE_COMPILED",
        "pass":True,
        "family":selected["family"],
        "mode":selected["mode"],
        "selected_path":selected["path"],
        "task_problem":selected["task_problem"],
        "raw_task_contract":contract,
        "attempts":attempts,
        "discovered_file_count":len(files),
        "model_dependency_count":0,"external_model_runtime_calls":0,
        "network_dependency_count":0,"dynamic_code_execution":False,
        "benchmark_identifier_used_for_routing":False,
        "raw_task_acceptance_authority":False,
        "terminal_authority":False,
    }
    if "compiler_receipt" in selected:
        receipt["numeric_compiler_receipt"]=selected["compiler_receipt"]
    receipt["compile_receipt_sha256"]=_sha({
        "family":receipt["family"],"mode":receipt["mode"],
        "selected_path":receipt["selected_path"],
        "task_problem":receipt["task_problem"],
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
    if compiled.get("pass") is not True:
        return compiled

    solved=controller.solve(compiled["task_problem"])
    if solved.get("verified") is not True:
        return _fail(
            "SCIENTIFIC_RESULT_NOT_VERIFIED",
            contract=compiled.get("raw_task_contract"),
            details={"compile_receipt":compiled,"solver_receipt":solved},
        )

    materialized=None
    if artifact_specs is not None:
        materialized=artifacts.materialize_artifacts(solved,artifact_specs,output_root)
        if materialized.get("status")!="PASS__DECLARED_SCIENTIFIC_ARTIFACTS_MATERIALIZED_AND_VERIFIED":
            return _fail(
                "SCIENTIFIC_ARTIFACT_MATERIALIZATION_FAILED",
                contract=compiled.get("raw_task_contract"),
                details={"compile_receipt":compiled,"solver_receipt":solved,"artifact_receipt":materialized},
            )

    receipt={
        "schema":SCHEMA,
        "status":"PASS__GENERAL_SCIENTIFIC_RAW_RESOURCE_EXECUTION_VERIFIED",
        "pass":True,"verified":True,
        "family":compiled["family"],"mode":compiled["mode"],
        "compile_receipt":compiled,
        "scientific_result":solved,
        "artifact_materialization":materialized,
        "model_dependency_count":0,"external_model_runtime_calls":0,
        "network_dependency_count":0,"dynamic_code_execution":False,
        "benchmark_identifier_used_for_routing":False,
        "raw_task_acceptance_authority":False,
        "terminal_authority":False,"terminal_credit_delta":0,
    }
    receipt["receipt_sha256"]=_sha({
        "family":receipt["family"],"mode":receipt["mode"],
        "compile_receipt_sha256":compiled["compile_receipt_sha256"],
        "scientific_result":solved,
        "artifact_materialization":materialized,
    })
    return receipt
