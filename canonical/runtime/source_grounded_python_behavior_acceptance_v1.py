from __future__ import annotations
import builtins,hashlib,json,os,pathlib,re
from typing import Any,Mapping
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime import independent_candidate_measurement_v1 as measurement
SCHEMA="PROJECT_BRAIN_SOURCE_GROUNDED_PYTHON_BEHAVIOR_ACCEPTANCE_V1"
CAPABILITY_ID="python.acceptance.source_grounded.behavior_examples.v1"
_RETURN=re.compile(r'^Function\s+([A-Za-z_][A-Za-z0-9_]*):([A-Za-z_][A-Za-z0-9_]*)\s+with\s+arguments\s+(\[.*\])\s+must\s+return\s+(.+?)[.]$',re.S)
_RAISE=re.compile(r'^Function\s+([A-Za-z_][A-Za-z0-9_]*):([A-Za-z_][A-Za-z0-9_]*)\s+with\s+arguments\s+(\[.*\])\s+must\s+raise\s+([A-Za-z_][A-Za-z0-9_]*)[.]$',re.S)
class BehaviorAcceptanceError(RuntimeError):pass
def _canon(x):return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)
def _sha(b):return hashlib.sha256(b).hexdigest()
def _rel(root,p):return str(p.relative_to(root)).replace("\\","/")
def _json(raw,what):
 try:v=json.loads(raw)
 except Exception as e:raise BehaviorAcceptanceError(what+"_JSON_INVALID") from e
 return v
def _case(text,oid,segment_sha):
 m=_RETURN.fullmatch(text)
 if m:
  mod,func,args_raw,expected_raw=m.groups();args=_json(args_raw,"ARGUMENTS");expected=_json(expected_raw,"EXPECTED")
  if not isinstance(args,list):raise BehaviorAcceptanceError("ARGUMENTS_NOT_LIST")
  return {"obligation_id":oid,"segment_sha256":segment_sha,"kind":"RETURN_JSON","module":mod,"function":func,"args":args,"expected":expected}
 m=_RAISE.fullmatch(text)
 if m:
  mod,func,args_raw,exc=m.groups();args=_json(args_raw,"ARGUMENTS")
  if not isinstance(args,list):raise BehaviorAcceptanceError("ARGUMENTS_NOT_LIST")
  cls=getattr(builtins,exc,None)
  if not isinstance(cls,type) or not issubclass(cls,BaseException):raise BehaviorAcceptanceError("EXCEPTION_TYPE_NOT_BUILTIN:"+exc)
  return {"obligation_id":oid,"segment_sha256":segment_sha,"kind":"RAISE_BUILTIN","module":mod,"function":func,"args":args,"exception":exc}
 return None
def compile_model(task_text:str,source_id:str="user"):
 contract=compile_contract(task_text,source_id=source_id,routing_target_effects=["candidate.ready"])
 if contract.get("pass") is not True:return {"schema":SCHEMA,"status":"FAIL_CLOSED__RAW_TASK_CONTRACT","pass":False,"contract":contract,"terminal_authority":False}
 cases=[];residual=[]
 for row in contract["acceptance_contract"]["obligations"]:
  try:c=_case(row["text"],row["obligation_id"],row["segment_sha256"])
  except Exception as exc:return {"schema":SCHEMA,"status":"FAIL_CLOSED__BEHAVIOR_EXAMPLE_PARSE","pass":False,"errors":[type(exc).__name__+":"+str(exc)],"obligation_id":row["obligation_id"],"terminal_authority":False}
  if c is None:residual.append(row["obligation_id"])
  else:cases.append(c)
 payload={"task_contract_sha256":contract["task_contract_sha256"],"cases":cases,"residual":residual}
 return {"schema":SCHEMA,"status":"COMPILED__PYTHON_BEHAVIOR_EXAMPLES_COMPLETE" if not residual and cases else "COMPILED__PYTHON_BEHAVIOR_EXAMPLES_WITH_RESIDUALS","pass":True,"task_contract":contract,"cases":cases,"semantic_residual_obligation_ids":residual,"behavior_case_count":len(cases),"source_grounded_behavior_complete":bool(cases) and not residual,"model_sha256":_sha(_canon(payload).encode()),"terminal_authority":False}
def _verifier_source(cases):
 data=_canon(cases)
 return '''import importlib.util,json,pathlib,sys\nMARKER="__BRAIN_MEASUREMENT__"\nCASES=json.loads('''+repr(data)+''')\nroot=pathlib.Path(sys.argv[1]).resolve()\nresults=[]\ncache={}\ndef load(name):\n if name in cache:return cache[name]\n p=(root/(name+".py")).resolve()\n if root not in p.parents or not p.is_file() or p.is_symlink():raise RuntimeError("MODULE_INVALID:"+name)\n spec=importlib.util.spec_from_file_location("_candidate_"+name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);cache[name]=m;return m\nfor c in CASES:\n ok=False;detail=""\n try:\n  m=load(c["module"]);fn=getattr(m,c["function"])\n  if not callable(fn):raise RuntimeError("FUNCTION_NOT_CALLABLE")\n  if c["kind"]=="RETURN_JSON":\n   v=fn(*c["args"]);actual=json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False);expected=json.dumps(c["expected"],sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False);ok=(actual==expected);detail=actual\n  else:\n   try:fn(*c["args"]);detail="NO_EXCEPTION"\n   except BaseException as e:ok=(type(e).__name__==c["exception"]);detail=type(e).__name__\n except BaseException as e:detail=type(e).__name__+":"+str(e)\n results.append({"obligation_id":c["obligation_id"],"pass":ok,"detail":detail})\npassed=all(x["pass"] for x in results) and len(results)==len(CASES)\nfields={"behavior_examples_pass":{"type":"boolean","dimension":"dimensionless","value":passed},"behavior_case_count":{"type":"integer","dimension":"cases","value":len(results)}}\nprint(MARKER+json.dumps({"fields":fields},sort_keys=True,separators=(",",":")))\nraise SystemExit(0 if passed else 1)\n'''
def run(args:Mapping[str,Any],root:str|os.PathLike[str]):
 try:
  if not isinstance(args,Mapping):raise BehaviorAcceptanceError("ARGS_NOT_OBJECT")
  repo=pathlib.Path(root).resolve();task=str(args.get("task_text") or "")
  model=compile_model(task,str(args.get("source_id") or "user"))
  if model.get("pass") is not True:return {**model,"capability_id":CAPABILITY_ID,"candidate_accepted":False,"acceptance_stop_authorized":False}
  if not model["source_grounded_behavior_complete"]:
   return {"schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"OPEN__SEMANTIC_ACCEPTANCE_RESIDUALS","pass":False,"candidate_accepted":False,"acceptance_stop_authorized":False,"model_sha256":model["model_sha256"],"behavior_case_count":model["behavior_case_count"],"semantic_residual_obligation_ids":model["semantic_residual_obligation_ids"],"model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,"incremental_spend_usd":0,"terminal_authority":False}
  vp=(repo/str(args.get("generated_verifier_path") or "")).resolve()
  if vp==repo or repo not in vp.parents:raise BehaviorAcceptanceError("GENERATED_VERIFIER_PATH_INVALID")
  cand=(repo/str(args.get("candidate_root") or "")).resolve()
  if cand==repo or repo not in cand.parents or not cand.is_dir():raise BehaviorAcceptanceError("CANDIDATE_ROOT_INVALID")
  if cand==vp or cand in vp.parents:raise BehaviorAcceptanceError("GENERATED_VERIFIER_INSIDE_CANDIDATE_FORBIDDEN")
  src=_verifier_source(model["cases"]);vp.parent.mkdir(parents=True,exist_ok=True);vp.write_text(src,encoding="utf-8")
  mr=measurement.run({"candidate_root":_rel(repo,cand),"verifier_path":_rel(repo,vp),"output_path":str(args.get("measurement_output_path") or "behavior_measurement.json"),"timeout_s":args.get("timeout_s",30)},repo)
  fields=mr.get("fields") if isinstance(mr,Mapping) else None
  passed=bool(mr.get("pass") is True and isinstance(fields,Mapping) and fields.get("behavior_examples_pass",{}).get("value") is True and fields.get("behavior_case_count",{}).get("value")==len(model["cases"]))
  result={"schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"PASS__SOURCE_GROUNDED_BEHAVIOR_ACCEPTANCE" if passed else "FALSIFIED__SOURCE_GROUNDED_BEHAVIOR_ACCEPTANCE","pass":passed,"candidate_accepted":passed,"acceptance_stop_authorized":passed,"task_contract_sha256":model["task_contract"]["task_contract_sha256"],"behavior_model_sha256":model["model_sha256"],"behavior_case_count":len(model["cases"]),"semantic_residual_obligation_ids":[],"generated_verifier_path":_rel(repo,vp),"generated_verifier_sha256":_sha(src.encode()),"candidate_snapshot_sha256":mr.get("candidate_snapshot_sha256"),"measurement_receipt_sha256":mr.get("receipt_sha256"),"measurement_receipt":mr,"source_grounding":"EVERY_ACCEPTED_CASE_IS_FULL_RAW_SOURCE_SEGMENT_MATCHING_EXACT_CLOSED_BEHAVIOR_GRAMMAR","model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,"incremental_spend_usd":0,"terminal_authority":False,"hard_nonclaims":["ONLY_SIMPLE_TOP_LEVEL_PYTHON_MODULE_FUNCTION_JSON_ARGUMENT_RETURN_OR_BUILTIN_EXCEPTION_EXAMPLES","NO_GENERAL_NATURAL_LANGUAGE_SEMANTIC_COMPLETENESS","NO_GENERAL_SIDE_EFFECT_STATEFUL_ASYNC_OR_OBJECT_METHOD_SEMANTICS","NO_BENCHMARK_SCORE_OR_TERMINAL_CREDIT"]}
  op=(repo/str(args.get("output_path") or "")).resolve()
  if op==repo or repo not in op.parents or cand==op or cand in op.parents:raise BehaviorAcceptanceError("OUTPUT_PATH_INVALID")
  op.parent.mkdir(parents=True,exist_ok=True);op.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8");result["output_path"]=_rel(repo,op);result["output_sha256"]=_sha(op.read_bytes());result["output_verified"]=True
  return result
 except Exception as exc:
  return {"schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"FAIL_CLOSED","pass":False,"candidate_accepted":False,"acceptance_stop_authorized":False,"errors":[type(exc).__name__+":"+str(exc)],"model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,"incremental_spend_usd":0,"terminal_authority":False}
