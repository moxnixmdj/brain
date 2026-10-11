#!/usr/bin/env python3
from __future__ import annotations
import hashlib,importlib.util,json,os,pathlib
from typing import Any,Mapping
SCHEMA="PROJECT_BRAIN_SOFTWARE_REQUEST_ACCEPTANCE_EXECUTE_V1"
class AcceptanceExecuteError(RuntimeError):pass
def _rel(r,p):return str(p.relative_to(r)).replace("\\","/")
def _safe_file(repo,raw):
 p=(repo/str(raw or "")).resolve()
 if p==repo or repo not in p.parents or not p.is_file() or p.is_symlink():raise AcceptanceExecuteError("FILE_INVALID")
 return p
def _load(repo,rel):
 p=_safe_file(repo,rel);spec=importlib.util.spec_from_file_location("_brain_accept_target_"+hashlib.sha256(str(p).encode()).hexdigest()[:10],p)
 if spec is None or spec.loader is None:raise AcceptanceExecuteError("MODULE_LOAD_FAILED")
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def execute(plan:Mapping[str,Any],root,existing_test_evidence=None):
 repo=pathlib.Path(root).resolve()
 if plan.get("schema")!="PROJECT_BRAIN_SOFTWARE_REQUEST_ACCEPTANCE_COMPILE_V1":raise AcceptanceExecuteError("PLAN_SCHEMA_INVALID")
 if plan.get("admission_ready") is not True:
  return {"schema":SCHEMA,"status":"BLOCKED_SPECIFICATION_OR_BINDING_HOLE","pass":False,"admission_ready":False,"results":[],"existing_test_evidence_observed_but_nonauthoritative":bool(existing_test_evidence),"model_dependency_count":0,"external_capability_provider_count":0,"incremental_spend_usd":0}
 results=[]
 for req in plan.get("requirements",[]):
  pred=req.get("predicate") or {};typ=pred.get("type");res={"pass":False}
  if req.get("verifier_binding_status")!="BOUND":res["error"]="UNBOUND"
  elif typ in {"PYTHON_CALL_RETURNS","PYTHON_CALL_RAISES"}:
   try:
    mod=_load(repo,pred["source_path"])
    fn=getattr(mod,pred["function"])
    try:
     value=fn(*pred.get("args",[]),**pred.get("kwargs",{}))
     res={"pass":typ=="PYTHON_CALL_RETURNS" and value==pred.get("expected"),"observed":{"returned":value}}
    except BaseException as e:
     res={"pass":typ=="PYTHON_CALL_RAISES" and type(e).__name__==pred.get("exception_type"),"observed":{"raised":type(e).__name__}}
   except BaseException as e:res={"pass":False,"error":"CHECK_EXECUTION_FAILED:"+type(e).__name__}
  elif typ in {"FILE_MUST_EXIST","FILE_MUST_NOT_EXIST"}:
   p=(repo/str(pred.get("path") or "")).resolve()
   if p==repo or repo not in p.parents:res={"pass":False,"error":"TARGET_PATH_OUTSIDE_REPOSITORY"}
   else:
    exists=p.exists();res={"pass":exists if typ=="FILE_MUST_EXIST" else not exists,"observed":{"exists":exists}}
  else:res={"pass":False,"error":"PREDICATE_TYPE_UNSUPPORTED"}
  try:json.dumps(res)
  except TypeError:
   obs=res.get("observed",{});res["observed"]={k:{"type":type(v).__name__} for k,v in obs.items()}
  results.append({"requirement_id":req.get("id"),"predicate_type":typ,**res})
 ok=bool(results) and all(x.get("pass") is True for x in results)
 return {"schema":SCHEMA,"status":"PASS__ALL_BOUND_REQUEST_PREDICATES_VERIFIED" if ok else "FAIL__REQUEST_PREDICATE_NOT_SATISFIED","pass":ok,"admission_ready":True,"results":results,"existing_test_evidence_observed_but_nonauthoritative":bool(existing_test_evidence),"model_dependency_count":0,"external_capability_provider_count":0,"incremental_spend_usd":0,"hard_nonclaims":["NO_CLAIM_REQUEST_COMPILER_COVERS_ARBITRARY_NATURAL_LANGUAGE","NO_EXISTING_TEST_EVIDENCE_COMPLETENESS_AUTHORITY","NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT"]}
def run(args:Mapping[str,Any],root):
 repo=pathlib.Path(root).resolve();plan=json.loads(_safe_file(repo,args.get("plan_path")).read_text());out=execute(plan,repo,args.get("existing_test_evidence"))
 p=(repo/str(args.get("output_path") or "")).resolve()
 if p==repo or repo not in p.parents:raise AcceptanceExecuteError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n");out["output_path"]=_rel(repo,p);out["output_sha256"]=hashlib.sha256(p.read_bytes()).hexdigest();out["output_verified"]=True;return out
