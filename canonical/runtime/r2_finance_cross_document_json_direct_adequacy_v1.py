"""R2 direct adequacy for bounded cross-document finance JSON decisions."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime import finance_cross_document_binding_v1 as producer
from canonical.runtime import finance_cross_document_binding_verify_v1 as verifier

SCHEMA="PROJECT_BRAIN_R2_FINANCE_CROSS_DOCUMENT_JSON_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::FINANCE_CROSS_DOCUMENT_JSON_BINDING_FAMILY_V1"
CAPABILITY_ID="finance.cross_document_json.binding.stdlib"
VERIFIER_CAPABILITY_ID="finance.cross_document_json.binding.verify.stdlib"
ROOT=Path(__file__).resolve().parents[2]
GRAMMAR=re.compile(
 r"Using the cross-document finance JSON case at "
 r"(?P<input>canonical/[A-Za-z0-9_.\-/]+\.json), select and independently "
 r"verify the action and save it to "
 r"(?P<output>canonical/[A-Za-z0-9_.\-/]+\.json)\.?",
 re.I,
)


def _base(status,passed=False):
 return {"schema":SCHEMA,"status":status,"pass":passed,"matched":False,
 "semantic_acceptance_complete":False,"actual_goal_satisfaction_verified":False,
 "direct_adequacy_authority":False,"terminal_authority":False,
 "terminal_credit_delta":0,"incremental_spend_usd":0}


def _safe(root,rel,file=False):
 root=Path(root).resolve(); p=Path(str(rel or "").strip())
 if p.is_absolute() or ".." in p.parts or not p.as_posix().startswith("canonical/"):
  raise ValueError("PATH_INVALID")
 q=(root/p).resolve()
 if q==root or root not in q.parents: raise ValueError("PATH_OUTSIDE_REPOSITORY")
 if file and (not q.is_file() or q.is_symlink()): raise ValueError("FILE_REQUIRED")
 return q


def _contract(goal):
 x=compile_contract(goal,source_id="user",routing_target_effects=["finance.cross_document_json.binding"])
 if x.get("pass") is not True: raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
 return x


def _load_json(path):
 raw=path.read_bytes()
 try: obj=json.loads(raw.decode("utf-8"))
 except Exception as exc: raise ValueError("JSON_INPUT_INVALID") from exc
 if not isinstance(obj,dict): raise ValueError("JSON_OBJECT_REQUIRED")
 return raw,obj


def _case_material(case,root):
 if not isinstance(case,dict) or case.get("schema")!=producer.CASE_SCHEMA:
  raise ValueError("CASE_SCHEMA_INVALID")
 sp=_safe(root,case.get("source_document_path"),True)
 tp=_safe(root,case.get("target_document_path"),True)
 if sp==tp: raise ValueError("SOURCE_TARGET_DOCUMENT_COLLISION")
 sr,sd=_load_json(sp); tr,td=_load_json(tp)
 produced=producer.compute(case,sd,td)
 checked=verifier.verify(case,sd,td,produced)
 if checked.get("verified") is not True:
  raise ValueError("PREFLIGHT_INDEPENDENT_RECOMPUTATION_FAILED:"+",".join(checked.get("errors") or []))
 return sp,tp,sr,tr,sd,td,produced


def preflight(request:Mapping[str,Any],*,repo_root=None):
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 if not isinstance(request,Mapping): return {**_base("FAIL_CLOSED"),"reason":"REQUEST_NOT_OBJECT"}
 goal=str(request.get("goal") or "").strip(); task=str(request.get("task_id") or "").strip()
 if not goal or not task: return {**_base("FAIL_CLOSED"),"reason":"TASK_ID_AND_GOAL_REQUIRED"}
 m=GRAMMAR.fullmatch(goal)
 if not m: return {**_base("NOT_APPLICABLE"),"matched":False}
 try:
  inp,out=m.group("input"),m.group("output")
  ip=_safe(root,inp,True); op=_safe(root,out)
  if ip==op: raise ValueError("INPUT_OUTPUT_COLLISION")
  case_raw,case=_load_json(ip)
  sp,tp,sr,tr,sd,td,produced=_case_material(case,root)
  if op in {sp,tp}: raise ValueError("OUTPUT_DOCUMENT_COLLISION")
  c=_contract(goal); ids=list((c.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
  if not ids: raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
  gsha=sha256(goal.encode()).hexdigest()
  return {**_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),"matched":True,"route_id":ROUTE_ID,
   "capability_id":CAPABILITY_ID,"verifier_capability_id":VERIFIER_CAPABILITY_ID,
   "goal_sha256":gsha,"policy_id":"R2_FINANCE_CROSS_DOCUMENT::"+gsha+"::"+sha256(case_raw).hexdigest(),
   "input_path":inp,"input_sha256":sha256(case_raw).hexdigest(),"output_path":out,
   "source_document_path":case["source_document_path"],"source_raw_sha256":sha256(sr).hexdigest(),
   "target_document_path":case["target_document_path"],"target_raw_sha256":sha256(tr).hexdigest(),
   "raw_acceptance_obligation_ids":ids,
   "semantic_scope":"EXACT_CONTENT_ADDRESSED_LOCAL_JSON_REFERENCE_ID_BINDING_PLUS_DECIMAL_FACT_EQUALITY_TO_EXPLICIT_TWO_ACTION_POLICY",
   "preflight_execution_authority":False}
 except Exception as exc:
  return {**_base("FAIL_CLOSED"),"matched":True,"route_id":ROUTE_ID,
   "reason":type(exc).__name__+":"+str(exc)}


def _restore(path,existed,raw):
 if existed:
  path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw or b"")
 else:
  try:path.unlink()
  except FileNotFoundError:pass


def run(request:Mapping[str,Any],*,repo_root=None):
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 pf=preflight(request,repo_root=root)
 if pf.get("matched") is not True or pf.get("status")=="FAIL_CLOSED": return pf
 ip=_safe(root,pf["input_path"],True); op=_safe(root,pf["output_path"])
 existed=op.is_file(); old=op.read_bytes() if existed else None
 try:
  case_before=ip.read_bytes()
  if sha256(case_before).hexdigest()!=pf["input_sha256"]: raise RuntimeError("CASE_DRIFT_BEFORE_EXECUTION")
  case=json.loads(case_before.decode())
  sp=_safe(root,case["source_document_path"],True); tp=_safe(root,case["target_document_path"],True)
  source_before=sp.read_bytes(); target_before=tp.read_bytes()
  if sha256(source_before).hexdigest()!=pf["source_raw_sha256"]: raise RuntimeError("SOURCE_DRIFT_BEFORE_EXECUTION")
  if sha256(target_before).hexdigest()!=pf["target_raw_sha256"]: raise RuntimeError("TARGET_DRIFT_BEFORE_EXECUTION")
  sd=json.loads(source_before.decode()); td=json.loads(target_before.decode())
  result=producer.compute(case,sd,td)
  if result.get("pass") is not True or result.get("model_dependency_count")!=0:
   raise RuntimeError("PRODUCER_AUTHORITY_INVALID")
  check=verifier.verify(case,sd,td,result)
  if check.get("verified") is not True:
   raise RuntimeError("INDEPENDENT_CROSS_DOCUMENT_VERIFICATION_FAILED:"+",".join(check.get("errors") or []))
  if ip.read_bytes()!=case_before or sp.read_bytes()!=source_before or tp.read_bytes()!=target_before:
   raise RuntimeError("INPUT_MUTATION_DETECTED")
  op.parent.mkdir(parents=True,exist_ok=True)
  op.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
  reread=json.loads(op.read_text(encoding="utf-8"))
  check2=verifier.verify(case,sd,td,reread)
  if check2.get("verified") is not True: raise RuntimeError("OUTPUT_READBACK_VERIFICATION_FAILED")
  c=_contract(str(request["goal"])); ids=list((c.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
  if ids!=pf["raw_acceptance_obligation_ids"]: raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")
  return {**_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",True),"matched":True,
   "route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,"verifier_capability_id":VERIFIER_CAPABILITY_ID,
   "selected_policy_id":pf["policy_id"],"goal_sha256":pf["goal_sha256"],
   "input_path":pf["input_path"],"input_sha256":pf["input_sha256"],"output_path":pf["output_path"],
   "output_sha256":sha256(op.read_bytes()).hexdigest(),
   "reference_id":result["reference_id"],"values_equal":result["values_equal"],
   "selected_action":result["selected_action"],"binding_sha256":result["binding_sha256"],
   "semantic_scope":pf["semantic_scope"],"semantic_acceptance_complete":True,
   "actual_goal_satisfaction_verified":True,"direct_adequacy_authority":True,
   "accepted_raw_obligation_ids":ids,"raw_acceptance_obligation_count":len(ids),
   "acceptance_receipt":deepcopy(check2),"execution_attempted":True,
   "retry_by_other_route_authorized":False,"source_immutability_verified":True,
   "authority_boundary":"EXACT_CONTENT_ADDRESSED_LOCAL_JSON_CROSS_DOCUMENT_REFERENCE_ID_AND_DECIMAL_EQUALITY_ONLY__NO_EXTERNAL_WORLD_TRUTH_ONTOLOGY_SYNONYMY_OR_GENERAL_CROSS_DOCUMENT_SEMANTICS"}
 except Exception as exc:
  _restore(op,existed,old)
  rollback=(op.is_file() and existed and op.read_bytes()==(old or b"")) if existed else not op.exists()
  return {**_base("OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"),"matched":True,
   "route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,"goal_sha256":pf.get("goal_sha256"),
   "execution_attempted":True,"retry_by_other_route_authorized":False,
   "rollback_complete":rollback,"reason":type(exc).__name__+":"+str(exc)}
