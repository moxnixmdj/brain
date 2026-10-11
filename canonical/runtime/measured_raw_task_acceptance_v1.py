from __future__ import annotations
import hashlib,json,os,pathlib,re
from typing import Any,Mapping,Sequence
from canonical.runtime import independent_candidate_measurement_v1 as measurement
from canonical.runtime import raw_task_objective_acceptance_executor_v1 as objective
SCHEMA="PROJECT_BRAIN_MEASURED_RAW_TASK_ACCEPTANCE_V1"
CAPABILITY_ID="task.acceptance.measured.objective.lossless.v1"
class MeasuredAcceptanceError(RuntimeError):pass
def _sha(b):return hashlib.sha256(b).hexdigest()
def _rel(root,p):return str(p.relative_to(root)).replace("\\","/")
def _schema(raw):
 if not isinstance(raw,Mapping) or not raw:raise MeasuredAcceptanceError("CANDIDATE_FIELD_SCHEMA_INVALID")
 out={}
 for fid,row in raw.items():
  if not isinstance(fid,str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",fid):raise MeasuredAcceptanceError("FIELD_ID_INVALID:"+str(fid))
  if not isinstance(row,Mapping) or set(row)!={"type","dimension"}:raise MeasuredAcceptanceError("FIELD_SCHEMA_ROW_INVALID:"+fid)
  typ=str(row["type"]);dim=str(row["dimension"])
  if typ not in {"integer","number","boolean","enum"} or not dim:raise MeasuredAcceptanceError("FIELD_SCHEMA_TYPE_OR_DIMENSION_INVALID:"+fid)
  out[fid]={"type":typ,"dimension":dim}
 return {k:out[k] for k in sorted(out)}
def _measured_values(receipt,expected):
 fields=receipt.get("fields")
 if not isinstance(fields,Mapping):raise MeasuredAcceptanceError("MEASUREMENT_FIELDS_MISSING")
 if set(fields)!=set(expected):raise MeasuredAcceptanceError("MEASUREMENT_FIELD_SET_MISMATCH")
 vals={}
 for fid in sorted(expected):
  row=fields[fid];want=expected[fid]
  if row.get("type")!=want["type"] or row.get("dimension")!=want["dimension"]:raise MeasuredAcceptanceError("MEASUREMENT_FIELD_SCHEMA_MISMATCH:"+fid)
  vals[fid]=row.get("value")
 return vals
def evaluate(args:Mapping[str,Any],root:str|os.PathLike[str]):
 try:
  if not isinstance(args,Mapping):raise MeasuredAcceptanceError("ARGS_NOT_OBJECT")
  repo=pathlib.Path(root).resolve()
  task=str(args.get("task_text") or "")
  if not task.strip():raise MeasuredAcceptanceError("TASK_TEXT_REQUIRED")
  expected=_schema(args.get("candidate_field_schema"))
  measurement_output=str(args.get("measurement_output_path") or "measurement.json")
  acceptance_output=(repo/str(args.get("output_path") or "")).resolve()
  if acceptance_output==repo or repo not in acceptance_output.parents:raise MeasuredAcceptanceError("OUTPUT_PATH_INVALID")
  mr=measurement.run({
    "candidate_root":args.get("candidate_root"),
    "verifier_path":args.get("verifier_path"),
    "output_path":measurement_output,
    "timeout_s":args.get("timeout_s",30),
  },repo)
  if mr.get("pass") is not True:
   return {"schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"FALSIFIED_OR_FAIL_CLOSED__INDEPENDENT_MEASUREMENT","pass":False,"candidate_accepted":False,"acceptance_stop_authorized":False,"measurement_receipt":mr,"model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,"incremental_spend_usd":0,"terminal_authority":False}
  values=_measured_values(mr,expected)
  out=objective.evaluate_candidate(
    task,
    {"response_text":args.get("response_text"),"fields":values},
    source_id=str(args.get("source_id") or "user"),
    routing_target_effects=list(args.get("routing_target_effects") or ["candidate.ready"]),
    candidate_field_schema=expected,
  )
  result={
    "schema":SCHEMA,"capability_id":CAPABILITY_ID,
    "status":("PASS__INDEPENDENT_MEASUREMENT_BOUND_OBJECTIVE_ACCEPTANCE" if out.get("pass") is True else str(out.get("status") or "FALSIFIED")),
    "pass":out.get("pass") is True,
    "candidate_accepted":out.get("candidate_accepted") is True,
    "acceptance_stop_authorized":out.get("acceptance_stop_authorized") is True,
    "candidate_snapshot_sha256":mr["candidate_snapshot_sha256"],
    "measurement_receipt_sha256":mr["receipt_sha256"],
    "measurement_output_sha256":mr["output_sha256"],
    "verifier_sha256":mr["verifier_sha256"],
    "measured_field_ids":sorted(values),
    "acceptance_result":out,
    "semantic_residual_obligation_ids":list(out.get("semantic_residual_obligation_ids") or []),
    "direct_builder_field_input_authorized":False,
    "measurement_binding":"ONLY_CONTENT_ADDRESSED_INDEPENDENT_VERIFIER_RECEIPT_FIELDS_FEED_TYPED_ACCEPTANCE",
    "model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,"incremental_spend_usd":0,
    "terminal_authority":False,
    "hard_nonclaims":["VERIFIER_SEMANTIC_ADEQUACY_REMAINS_SOURCE_GROUNDING_OR_PROOF_OBLIGATION","SEMANTIC_RAW_TASK_RESIDUALS_STILL_BLOCK","NO_GENERAL_NATURAL_LANGUAGE_ACCEPTANCE_COMPLETENESS","NO_BENCHMARK_SCORE_OR_TERMINAL_CREDIT"]
  }
  acceptance_output.parent.mkdir(parents=True,exist_ok=True);acceptance_output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
  result["output_path"]=_rel(repo,acceptance_output);result["output_sha256"]=_sha(acceptance_output.read_bytes());result["output_verified"]=True
  return result
 except Exception as exc:
  return {"schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"FAIL_CLOSED","pass":False,"candidate_accepted":False,"acceptance_stop_authorized":False,"errors":[type(exc).__name__+":"+str(exc)],"direct_builder_field_input_authorized":False,"model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,"incremental_spend_usd":0,"terminal_authority":False}
