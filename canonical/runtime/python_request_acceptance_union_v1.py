from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Mapping

from canonical.runtime import python_measured_objective_acceptance_v1 as measured_accept
from canonical.runtime import raw_task_objective_acceptance_executor_v1 as objective
from canonical.runtime.bound_capabilities import python_request_semantic_acceptance_cells_v1 as semantic

SCHEMA="PROJECT_BRAIN_PYTHON_REQUEST_ACCEPTANCE_UNION_V1"
CAPABILITY_ID="python.software.request.acceptance.union.v1"
MODEL_DEPENDENCY_COUNT=0
EXTERNAL_MODEL_RUNTIME_CALLS=0

class AcceptanceUnionError(RuntimeError):
    pass

def _sha_obj(x:Any)->str:
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False,default=str).encode("utf-8")).hexdigest()

def _objective_rows(model:Mapping[str,Any],fields:Mapping[str,Any],response_text:str|None)->tuple[set[str],set[str],list[dict[str,Any]]]:
    contract=model["task_contract"];loc=model["localization"]
    by_id={str(r["obligation_id"]):r for r in contract["acceptance_contract"]["obligations"]}
    objective_ids={str(x) for x in loc.get("objective_route_obligation_ids") or []}
    passed:set[str]=set();failed:set[str]=set();rows=[]
    localized={str(r["obligation_id"]):r for r in loc.get("obligations") or []}
    for oid in sorted(objective_ids):
        row=localized.get(oid)
        if row is None:
            failed.add(oid);rows.append({"obligation_id":oid,"pass":False,"status":"OBJECTIVE_LOCALIZATION_ROW_MISSING"});continue
        source_text=str(by_id[oid]["text"]);route_results=[]
        for route in row.get("available_objective_routes") or []:
            rid=route.get("route_id")
            if rid=="INSTRUCTION_CONSTRAINTS_V1":
                rr=objective._formal_route(source_text,response_text)
            elif rid=="SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1":
                program=route.get("acceptance_program")
                rr=objective._typed_route(program,fields) if isinstance(program,Mapping) else {"route_id":str(rid),"status":"FAIL_CLOSED__ACCEPTANCE_PROGRAM_MISSING","pass":False}
            else:
                rr={"route_id":str(rid),"status":"FAIL_CLOSED__UNKNOWN_OBJECTIVE_ROUTE","pass":False}
            route_results.append(rr)
        ok=bool(route_results) and all(x.get("pass") is True for x in route_results)
        (passed if ok else failed).add(oid)
        rows.append({"obligation_id":oid,"segment_sha256":by_id[oid]["segment_sha256"],"pass":ok,"route_results":route_results})
    return passed,failed,rows

def evaluate_union(
    task_text:str,
    *,
    measurement_receipt_path:str,
    receipt_root:str|pathlib.Path,
    baseline_root:str|pathlib.Path,
    candidate_root:str|pathlib.Path,
    expected_baseline_snapshot_sha256:str,
    response_text:str|None=None,
)->dict[str,Any]:
    try:
        receipt_root_path=pathlib.Path(receipt_root).resolve()
        receipt,receipt_file_sha=measured_accept._load_receipt(receipt_root_path,measurement_receipt_path)
        model=objective.compile_model(task_text,candidate_field_schema=receipt["measurement_schema"])
        if model.get("pass") is not True:
            raise AcceptanceUnionError("OBJECTIVE_MODEL_COMPILATION_FAILED")
        contract=model["task_contract"];loc=model["localization"]
        required={str(x) for x in contract["acceptance_contract"]["required_obligation_ids"]}
        objective_ids={str(x) for x in loc.get("objective_route_obligation_ids") or []}
        residual_ids={str(x) for x in loc.get("semantic_residual_obligation_ids") or []}
        if objective_ids & residual_ids or objective_ids | residual_ids != required:
            raise AcceptanceUnionError("OBJECTIVE_RESIDUAL_PARTITION_INVALID")

        obj_pass,obj_fail,obj_rows=_objective_rows(model,receipt["measurements"],response_text)
        sem=semantic.evaluate_cells(
            task_text,
            baseline_root=baseline_root,
            candidate_root=candidate_root,
            expected_baseline_snapshot_sha256=expected_baseline_snapshot_sha256,
            expected_candidate_snapshot_sha256=receipt["subject"]["snapshot_sha256"],
        )
        if sem.get("status")=="FAIL_CLOSED":
            raise AcceptanceUnionError("SEMANTIC_CELL_MEASUREMENT_FAILED:"+str((sem.get("errors") or ["UNKNOWN"])[0]))
        if sem.get("task_contract_sha256")!=contract.get("task_contract_sha256"):
            raise AcceptanceUnionError("TASK_CONTRACT_IDENTITY_MISMATCH")

        sem_pass=set(sem.get("passed_obligation_ids") or []) & residual_ids
        sem_fail=set(sem.get("failed_obligation_ids") or []) & residual_ids
        sem_unbound=residual_ids-sem_pass-sem_fail
        passed=obj_pass|sem_pass
        failed=obj_fail|sem_fail
        uncovered=required-passed-failed
        if uncovered!=sem_unbound:
            raise AcceptanceUnionError("UNION_RESIDUAL_ACCOUNTING_MISMATCH")
        accepted=bool(required) and passed==required and not failed and not uncovered

        per=[]
        sem_by={}
        for row in sem.get("cell_results") or []:
            for oid in row.get("obligation_ids") or []:
                if str(oid) in residual_ids: sem_by[str(oid)]=row
        obj_by={str(r["obligation_id"]):r for r in obj_rows}
        for oid in sorted(required):
            if oid in objective_ids:
                row=obj_by.get(oid) or {}
                per.append({"obligation_id":oid,"authority":"MEASURED_OBJECTIVE_ROUTE","pass":oid in obj_pass,"detail":row})
            else:
                row=sem_by.get(oid)
                per.append({"obligation_id":oid,"authority":"SOURCE_GROUNDED_SEMANTIC_CELL" if row else "UNBOUND","pass":oid in sem_pass,"detail":row})

        payload={
          "schema":SCHEMA,"capability_id":CAPABILITY_ID,
          "status":"PASS__COMPLETE_MEASURED_OBJECTIVE_PLUS_SOURCE_GROUNDED_SEMANTIC_ACCEPTANCE" if accepted else "OPEN__REQUEST_ACCEPTANCE_NOT_COMPLETE",
          "pass":accepted,"candidate_accepted":accepted,"acceptance_stop_authorized":accepted,
          "task_contract_sha256":contract.get("task_contract_sha256"),
          "required_obligation_count":len(required),"passed_obligation_count":len(passed),
          "failed_obligation_ids":sorted(failed),"unbound_obligation_ids":sorted(uncovered),
          "objective_route_obligation_ids":sorted(objective_ids),"semantic_residual_obligation_ids":sorted(residual_ids),
          "obligation_results":per,
          "measurement_receipt_file_sha256":receipt_file_sha,
          "measurement_receipt_payload_sha256":receipt["receipt_payload_sha256"],
          "candidate_snapshot_sha256":receipt["subject"]["snapshot_sha256"],
          "baseline_snapshot_sha256":sem.get("baseline_snapshot_sha256"),
          "semantic_cell_receipt_payload_sha256":sem.get("receipt_payload_sha256"),
          "semantic_cell_program_sha256":sem.get("semantic_cell_program_sha256"),
          "model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,"incremental_spend_usd":0,
          "terminal_authority":False,
          "hard_nonclaims":["ONLY_OBJECTIVE_ROUTES_AND_EXPLICIT_SOURCE_GROUNDED_SEMANTIC_CELLS_CAN_CLEAR","UNRECOGNIZED_OR_AMBIGUOUS_RAW_OBLIGATIONS_REMAIN_BLOCKING","NO_GENERAL_NATURAL_LANGUAGE_COMPLETENESS","NO_GENERAL_MERGEABILITY_OR_FRONTIERCODE_SCORE_AUTHORITY"],
        }
        payload["acceptance_payload_sha256"]=_sha_obj(payload)
        return payload
    except Exception as exc:
        return {"schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"FAIL_CLOSED","pass":False,"candidate_accepted":False,"acceptance_stop_authorized":False,"errors":[type(exc).__name__+":"+str(exc)],"terminal_authority":False}

def run(args:Mapping[str,Any],root:str|pathlib.Path)->dict[str,Any]:
    if not isinstance(args,Mapping):
        return {"schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"FAIL_CLOSED","pass":False,"errors":["ARGS_NOT_OBJECT"],"terminal_authority":False}
    repo=pathlib.Path(root).resolve()
    return evaluate_union(
      str(args.get("task_text") or ""),
      measurement_receipt_path=str(args.get("measurement_receipt_path") or ""),
      receipt_root=repo,
      baseline_root=(repo/str(args.get("baseline_root") or ".")).resolve(),
      candidate_root=(repo/str(args.get("candidate_root") or ".")).resolve(),
      expected_baseline_snapshot_sha256=str(args.get("expected_baseline_snapshot_sha256") or ""),
      response_text=(str(args["response_text"]) if args.get("response_text") is not None else None),
    )