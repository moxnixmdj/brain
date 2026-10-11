from __future__ import annotations
import hashlib,json,os,pathlib
from typing import Any,Mapping
from canonical.runtime import raw_task_objective_acceptance_executor_v1 as objective
from canonical.runtime import independent_candidate_measurement_v1 as measurement
from canonical.runtime import source_grounded_python_behavior_acceptance_v1 as behavior
SCHEMA="PROJECT_BRAIN_COMPOSED_RAW_SOFTWARE_ACCEPTANCE_V1"
CAPABILITY_ID="software.acceptance.composed.lossless.v1"
class ComposedAcceptanceError(RuntimeError):pass
def _sha(b):return hashlib.sha256(b).hexdigest()
def _rel(root,p):return str(p.relative_to(root)).replace("\\","/")
def _expected_schema(raw):
 if raw is None:return {}
 if not isinstance(raw,Mapping):raise ComposedAcceptanceError("CANDIDATE_FIELD_SCHEMA_INVALID")
 out={}
 for k,v in raw.items():
  if not isinstance(k,str) or not isinstance(v,Mapping) or set(v)!={"type","dimension"}:raise ComposedAcceptanceError("FIELD_SCHEMA_INVALID:"+str(k))
  out[k]={"type":str(v["type"]),"dimension":str(v["dimension"])}
 return {k:out[k] for k in sorted(out)}
def _values(receipt,schema):
 fields=receipt.get("fields")
 if not isinstance(fields,Mapping) or set(fields)!=set(schema):raise ComposedAcceptanceError("MEASUREMENT_FIELD_SET_MISMATCH")
 out={}
 for k in sorted(schema):
  row=fields[k]
  if row.get("type")!=schema[k]["type"] or row.get("dimension")!=schema[k]["dimension"]:raise ComposedAcceptanceError("MEASUREMENT_FIELD_SCHEMA_MISMATCH:"+k)
  out[k]=row.get("value")
 return out
def run(args:Mapping[str,Any],root:str|os.PathLike[str]):
 try:
  if not isinstance(args,Mapping):raise ComposedAcceptanceError("ARGS_NOT_OBJECT")
  repo=pathlib.Path(root).resolve();task=str(args.get("task_text") or "")
  if not task.strip():raise ComposedAcceptanceError("TASK_TEXT_REQUIRED")
  source_id=str(args.get("source_id") or "user");schema=_expected_schema(args.get("candidate_field_schema"))
  om=objective.compile_model(task,source_id=source_id,routing_target_effects=["candidate.ready"],candidate_field_schema=schema or None)
  bm=behavior.compile_model(task,source_id=source_id)
  if om.get("pass") is not True or bm.get("pass") is not True:raise ComposedAcceptanceError("SUBMODEL_COMPILE_FAILED")
  oc=om["task_contract"];bc=bm["task_contract"]
  if oc.get("task_contract_sha256")!=bc.get("task_contract_sha256"):raise ComposedAcceptanceError("RAW_TASK_CONTRACT_IDENTITY_MISMATCH")
  required=list(oc["acceptance_contract"]["required_obligation_ids"]);by_id={x["obligation_id"]:x for x in oc["acceptance_contract"]["obligations"]}
  loc_by={x["obligation_id"]:x for x in om["localization"]["obligations"]}
  objective_ids=set(om["localization"].get("objective_route_obligation_ids") or [])
  behavior_by={x["obligation_id"]:x for x in bm.get("cases") or []};behavior_ids=set(behavior_by)
  covered=objective_ids|behavior_ids;residual=[x for x in required if x not in covered]
  overlap=objective_ids&behavior_ids
  if residual:
   return {"schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"OPEN__SEMANTIC_ACCEPTANCE_RESIDUALS","pass":False,"candidate_accepted":False,"acceptance_stop_authorized":False,"direct_builder_field_input_authorized":False,"task_contract_sha256":oc["task_contract_sha256"],"required_obligation_count":len(required),"covered_obligation_count":len(covered),"semantic_residual_obligation_ids":residual,"overlap_obligation_ids":sorted(overlap),"model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,"incremental_spend_usd":0,"terminal_authority":False}
  typed_needed=False
  for oid in objective_ids:
   for route in loc_by[oid].get("available_objective_routes") or []:
    if route.get("route_id")=="SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1":typed_needed=True
  mr=None;vals={}
  if typed_needed:
   if not schema:raise ComposedAcceptanceError("TYPED_OBJECTIVE_ROUTE_REQUIRES_FIELD_SCHEMA")
   if not args.get("objective_verifier_path"):raise ComposedAcceptanceError("OBJECTIVE_VERIFIER_PATH_REQUIRED")
   mr=measurement.run({"candidate_root":args.get("candidate_root"),"verifier_path":args.get("objective_verifier_path"),"output_path":str(args.get("objective_measurement_output_path") or "objective_measurement.json"),"timeout_s":args.get("timeout_s",30)},repo)
   if mr.get("pass") is not True:return {"schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"FALSIFIED_OR_FAIL_CLOSED__OBJECTIVE_INDEPENDENT_MEASUREMENT","pass":False,"candidate_accepted":False,"acceptance_stop_authorized":False,"measurement_receipt":mr,"direct_builder_field_input_authorized":False,"model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,"incremental_spend_usd":0,"terminal_authority":False}
   vals=_values(mr,schema)
  objective_results={}
  for oid in sorted(objective_ids):
   row=loc_by[oid];text=by_id[oid]["text"];rr=[]
   for route in row.get("available_objective_routes") or []:
    rid=route.get("route_id")
    if rid=="INSTRUCTION_CONSTRAINTS_V1":x=objective._formal_route(text,args.get("response_text"))
    elif rid=="SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1":
     prog=route.get("acceptance_program")
     if not isinstance(prog,Mapping):x={"route_id":str(rid),"status":"FAIL_CLOSED__ACCEPTANCE_PROGRAM_MISSING","pass":False}
     else:x=objective._typed_route(prog,vals)
    else:x={"route_id":str(rid),"status":"FAIL_CLOSED__UNKNOWN_OBJECTIVE_ROUTE","pass":False}
    rr.append(x)
   objective_results[oid]={"pass":bool(rr) and all(x.get("pass") is True for x in rr),"route_results":rr}
  behavior_result=None
  if behavior_ids:
   cand=(repo/str(args.get("candidate_root") or "")).resolve()
   if cand==repo or repo not in cand.parents or not cand.is_dir():raise ComposedAcceptanceError("CANDIDATE_ROOT_INVALID")
   vp=(repo/str(args.get("behavior_verifier_output_path") or "")).resolve()
   if vp==repo or repo not in vp.parents or cand==vp or cand in vp.parents:raise ComposedAcceptanceError("BEHAVIOR_VERIFIER_PATH_INVALID")
   src=behavior._verifier_source([behavior_by[x] for x in sorted(behavior_ids)])
   vp.parent.mkdir(parents=True,exist_ok=True);vp.write_text(src,encoding="utf-8")
   br=measurement.run({"candidate_root":_rel(repo,cand),"verifier_path":_rel(repo,vp),"output_path":str(args.get("behavior_measurement_output_path") or "behavior_measurement.json"),"timeout_s":args.get("timeout_s",30)},repo)
   fs=br.get("fields") if isinstance(br,Mapping) else {}
   bp=bool(br.get("pass") is True and isinstance(fs,Mapping) and fs.get("behavior_examples_pass",{}).get("value") is True and fs.get("behavior_case_count",{}).get("value")==len(behavior_ids))
   behavior_result={"pass":bp,"measurement_receipt":br,"generated_verifier_sha256":_sha(src.encode()),"obligation_ids":sorted(behavior_ids)}
  rows=[]
  for oid in required:
   op=objective_results.get(oid);bp=(behavior_result["pass"] if oid in behavior_ids and behavior_result else None)
   checks=[]
   if op is not None:checks.append({"route_family":"OBJECTIVE","pass":op["pass"],"details":op})
   if bp is not None:checks.append({"route_family":"PYTHON_BEHAVIOR_EXAMPLE","pass":bp})
   rows.append({"obligation_id":oid,"segment_sha256":by_id[oid]["segment_sha256"],"pass":bool(checks) and all(x["pass"] for x in checks),"checks":checks})
  accepted=len(rows)==len(required) and all(x["pass"] for x in rows)
  snapshots=set()
  if mr and mr.get("candidate_snapshot_sha256"):snapshots.add(mr["candidate_snapshot_sha256"])
  if behavior_result:
   bmr=behavior_result["measurement_receipt"]
   if bmr.get("candidate_snapshot_sha256"):snapshots.add(bmr["candidate_snapshot_sha256"])
  if len(snapshots)>1:raise ComposedAcceptanceError("INDEPENDENT_MEASUREMENTS_BIND_DIFFERENT_CANDIDATE_SNAPSHOTS")
  result={"schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"PASS__EVERY_RAW_OBLIGATION_COVERED_AND_INDEPENDENTLY_ACCEPTED" if accepted else "FALSIFIED__COMPOSED_RAW_SOFTWARE_ACCEPTANCE","pass":accepted,"candidate_accepted":accepted,"acceptance_stop_authorized":accepted,"task_contract_sha256":oc["task_contract_sha256"],"required_obligation_count":len(required),"covered_obligation_count":len(covered),"evaluated_obligation_count":len(rows),"semantic_residual_obligation_ids":[],"overlap_obligation_ids":sorted(overlap),"obligation_results":rows,"objective_measurement_receipt":mr,"behavior_measurement":behavior_result,"candidate_snapshot_sha256":next(iter(snapshots)) if len(snapshots)==1 else None,"direct_builder_field_input_authorized":False,"all_raw_obligations_accounted_for":True,"model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,"incremental_spend_usd":0,"terminal_authority":False,"hard_nonclaims":["COVERAGE_IS_LIMITED_TO_CURRENT_OBJECTIVE_ROUTES_PLUS_EXPLICIT_PYTHON_BEHAVIOR_EXAMPLE_GRAMMAR","NO_ARBITRARY_NATURAL_LANGUAGE_SEMANTIC_COMPLETENESS","NO_GENERAL_MERGEABILITY_OR_HIDDEN_REQUIREMENTS_PROOF","NO_BENCHMARK_SCORE_OR_TERMINAL_CREDIT"]}
  opath=(repo/str(args.get("output_path") or "")).resolve()
  if opath==repo or repo not in opath.parents:raise ComposedAcceptanceError("OUTPUT_PATH_INVALID")
  opath.parent.mkdir(parents=True,exist_ok=True);opath.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8");result["output_path"]=_rel(repo,opath);result["output_sha256"]=_sha(opath.read_bytes());result["output_verified"]=True
  return result
 except Exception as exc:
  return {"schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"FAIL_CLOSED","pass":False,"candidate_accepted":False,"acceptance_stop_authorized":False,"errors":[type(exc).__name__+":"+str(exc)],"direct_builder_field_input_authorized":False,"model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,"incremental_spend_usd":0,"terminal_authority":False}
