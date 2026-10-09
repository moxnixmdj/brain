"""R2 direct adequacy for bounded contextual finance reference resolution."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json,re
from pathlib import Path
from typing import Any,Mapping

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime import finance_contextual_reference_resolve_v1 as producer
from canonical.runtime import finance_contextual_reference_verify_v1 as verifier

SCHEMA="PROJECT_BRAIN_R2_FINANCE_CONTEXTUAL_REFERENCE_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::FINANCE_BOUNDED_CONTEXTUAL_REFERENCE_FAMILY_V1"
CAPABILITY_ID="finance.contextual_reference.resolve.stdlib"
VERIFIER_CAPABILITY_ID="finance.contextual_reference.verify.stdlib"
ROOT=Path(__file__).resolve().parents[2]
GRAMMAR=re.compile(
 r"Using the bounded contextual finance reference case at (?P<input>canonical/[A-Za-z0-9_.\-/]+\.json), "
 r"resolve and independently verify the contextual references and save them to (?P<output>canonical/[A-Za-z0-9_.\-/]+\.json)\.?",
 re.I,
)

def _base(status,passed=False):
 return {"schema":SCHEMA,"status":status,"pass":passed,"matched":False,
 "semantic_acceptance_complete":False,"actual_goal_satisfaction_verified":False,
 "direct_adequacy_authority":False,"terminal_authority":False,
 "terminal_credit_delta":0,"incremental_spend_usd":0}

def _safe(root,rel):
 root=Path(root).resolve(); p=Path(str(rel))
 if p.is_absolute() or ".." in p.parts: raise ValueError("PATH_INVALID")
 q=(root/p).resolve()
 if q==root or root not in q.parents: raise ValueError("PATH_OUTSIDE_REPOSITORY")
 return q

def _contract(goal):
 c=compile_contract(goal,source_id="user",routing_target_effects=["finance.contextual_reference.resolve"])
 if c.get("pass") is not True: raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
 return c

def preflight(request:Mapping[str,Any],*,repo_root=None):
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 if not isinstance(request,Mapping): return {**_base("FAIL_CLOSED"),"reason":"REQUEST_NOT_OBJECT"}
 goal=str(request.get("goal") or "").strip(); task=str(request.get("task_id") or "").strip()
 if not goal or not task: return {**_base("FAIL_CLOSED"),"reason":"TASK_ID_AND_GOAL_REQUIRED"}
 m=GRAMMAR.fullmatch(goal)
 if not m: return {**_base("NOT_APPLICABLE"),"matched":False}
 try:
  inp,out=m.group("input"),m.group("output"); ip,op=_safe(root,inp),_safe(root,out)
  if ip==op or not ip.is_file(): raise ValueError("INPUT_INVALID")
  case=json.loads(ip.read_text(encoding="utf-8"))
  produced=producer.compute(case); checked=verifier.verify(case,produced)
  if checked.get("verified") is not True: raise ValueError("PREFLIGHT_RECOMPUTATION_FAILED:"+",".join(checked.get("errors") or []))
  c=_contract(goal); ids=list((c.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
  if not ids: raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
  raw=ip.read_bytes(); gsha=sha256(goal.encode()).hexdigest(); isha=sha256(raw).hexdigest()
  return {**_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),"matched":True,"route_id":ROUTE_ID,
   "capability_id":CAPABILITY_ID,"verifier_capability_id":VERIFIER_CAPABILITY_ID,
   "policy_id":"R2_FINANCE_CONTEXTUAL_REFERENCE::"+gsha+"::"+isha,
   "goal_sha256":gsha,"input_path":inp,"input_sha256":isha,"output_path":out,
   "raw_acceptance_obligation_ids":ids,
   "semantic_scope":"FOUR_STRUCTURAL_CONTEXTUAL_REFERENCE_FORMS_WITH_NO_UNRESOLVED_AMBIGUITY",
   "preflight_execution_authority":False}
 except Exception as exc:
  return {**_base("FAIL_CLOSED"),"matched":True,"route_id":ROUTE_ID,
   "reason":type(exc).__name__+":"+str(exc)}

def run(request:Mapping[str,Any],*,repo_root=None):
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 pf=preflight(request,repo_root=root)
 if pf.get("matched") is not True or pf.get("status")=="FAIL_CLOSED": return pf
 ip,op=_safe(root,pf["input_path"]),_safe(root,pf["output_path"])
 existed=op.is_file(); old=op.read_bytes() if existed else None
 try:
  before=ip.read_bytes()
  if sha256(before).hexdigest()!=pf["input_sha256"]: raise RuntimeError("INPUT_DRIFT")
  case=json.loads(before.decode()); produced=producer.compute(case)
  op.parent.mkdir(parents=True,exist_ok=True)
  op.write_text(json.dumps(produced,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
  checked=verifier.verify(case,json.loads(op.read_text(encoding="utf-8")))
  if checked.get("verified") is not True or checked.get("producer_independent") is not True:
   raise RuntimeError("INDEPENDENT_VERIFICATION_FAILED")
  if ip.read_bytes()!=before: raise RuntimeError("SOURCE_MUTATED")
  ids=list((_contract(str(request["goal"])).get("acceptance_contract") or {}).get("required_obligation_ids") or [])
  if ids!=pf["raw_acceptance_obligation_ids"]: raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")
  return {**_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",True),"matched":True,
   "route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,"verifier_capability_id":VERIFIER_CAPABILITY_ID,
   "selected_policy_id":pf["policy_id"],"goal_sha256":pf["goal_sha256"],
   "input_path":pf["input_path"],"input_sha256":pf["input_sha256"],
   "output_path":pf["output_path"],"output_sha256":sha256(op.read_bytes()).hexdigest(),
   "resolved_item_count":produced["resolved_item_count"],
   "semantic_scope":pf["semantic_scope"],"semantic_acceptance_complete":True,
   "actual_goal_satisfaction_verified":True,"direct_adequacy_authority":True,
   "accepted_raw_obligation_ids":ids,"raw_acceptance_obligation_count":len(ids),
   "acceptance_receipt":deepcopy(dict(checked)),"execution_attempted":True,
   "retry_by_other_route_authorized":False,"source_immutability_verified":True,
   "authority_boundary":"FOUR_STRUCTURAL_REFERENCE_FORMS_ONLY__NO_GENERAL_COREFERENCE_SYNONYMY_ONTOLOGY_WORD_SENSE_CROSS_DOCUMENT_OR_EXTERNAL_WORLD_TRUTH"}
 except Exception as exc:
  if existed: op.parent.mkdir(parents=True,exist_ok=True); op.write_bytes(old or b"")
  else:
   try: op.unlink()
   except FileNotFoundError: pass
  rollback=(op.is_file() and existed and op.read_bytes()==(old or b"")) if existed else not op.exists()
  return {**_base("OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"),"matched":True,
   "route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,"execution_attempted":True,
   "retry_by_other_route_authorized":False,"rollback_complete":rollback,
   "reason":type(exc).__name__+":"+str(exc)}
