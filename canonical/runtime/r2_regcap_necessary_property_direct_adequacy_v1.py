"""R2 direct adequacy for pinned regulatory-capital necessary-property queries."""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json,re
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime import regcap_necessary_property_result_v1 as producer
from canonical.runtime import regcap_necessary_property_verify_v1 as verifier

SCHEMA="PROJECT_BRAIN_R2_REGCAP_NECESSARY_PROPERTY_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::REGCAP_PINNED_NECESSARY_PROPERTY_FAMILY_V1"
CAPABILITY_ID="finance.regcap.necessary_property.pinned_source"
VERIFIER_CAPABILITY_ID="finance.regcap.necessary_property.verify.independent"
ROOT=Path(__file__).resolve().parents[2]
GRAMMAR=re.compile(
 r"Using the bounded regulatory-capital property case at (?P<input>canonical/[A-Za-z0-9_.\-/]+\.json), "
 r"prove and independently verify the necessary property and save it to (?P<output>canonical/[A-Za-z0-9_.\-/]+\.json)\.?",
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
 c=compile_contract(goal,source_id="user",routing_target_effects=[CAPABILITY_ID])
 if c.get("pass") is not True: raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
 return c

def _validate_case(case):
 if not isinstance(case,Mapping) or case.get("schema")!=producer.CASE_SCHEMA:
  raise ValueError("CASE_SCHEMA_INVALID")
 if set(case)!={"schema","scope_id","concept_id","property_id"}:
  raise ValueError("CASE_FIELD_SET_INVALID")
 pair=(str(case.get("concept_id") or ""),str(case.get("property_id") or ""))
 if str(case.get("scope_id") or "")!=verifier.SCOPE_ID: raise ValueError("SCOPE_ID_MISMATCH")
 if pair not in verifier.RULES: raise ValueError("PAIR_OUTSIDE_BOUNDED_VERIFIED_RULE_SET")

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
  raw=ip.read_bytes(); case=json.loads(raw.decode("utf-8")); _validate_case(case)
  c=_contract(goal); ids=list((c.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
  if not ids: raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
  gsha=sha256(goal.encode()).hexdigest(); isha=sha256(raw).hexdigest()
  return {**_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),"matched":True,"route_id":ROUTE_ID,
   "capability_id":CAPABILITY_ID,"verifier_capability_id":VERIFIER_CAPABILITY_ID,
   "policy_id":"R2_REGCAP_PROPERTY::"+gsha+"::"+isha,
   "goal_sha256":gsha,"input_path":inp,"input_sha256":isha,"output_path":out,
   "raw_acceptance_obligation_ids":ids,
   "semantic_scope":"TWELVE_ONE_WAY_CCOB_CCYB_TLAC_NECESSARY_PROPERTY_EDGES_BOUND_TO_PINNED_BIS_FSB_SOURCE_FRAGMENTS",
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
  case=json.loads(before.decode("utf-8")); _validate_case(case)
  produced=producer.compute(case,repo_root=root)
  op.parent.mkdir(parents=True,exist_ok=True)
  op.write_text(json.dumps(produced,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
  checked=verifier.verify(case,json.loads(op.read_text(encoding="utf-8")),repo_root=root)
  if checked.get("verified") is not True or checked.get("producer_independent") is not True:
   raise RuntimeError("INDEPENDENT_VERIFICATION_FAILED:"+str(checked.get("reason") or "UNKNOWN"))
  if ip.read_bytes()!=before: raise RuntimeError("SOURCE_MUTATED")
  ids=list((_contract(str(request["goal"])).get("acceptance_contract") or {}).get("required_obligation_ids") or [])
  if ids!=pf["raw_acceptance_obligation_ids"]: raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")
  return {**_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",True),"matched":True,
   "route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,"verifier_capability_id":VERIFIER_CAPABILITY_ID,
   "selected_policy_id":pf["policy_id"],"goal_sha256":pf["goal_sha256"],
   "input_path":pf["input_path"],"input_sha256":pf["input_sha256"],
   "output_path":pf["output_path"],"output_sha256":sha256(op.read_bytes()).hexdigest(),
   "concept_id":produced["concept_id"],"property_id":produced["property_id"],"relation":"ENTAILS",
   "semantic_scope":pf["semantic_scope"],"semantic_acceptance_complete":True,
   "actual_goal_satisfaction_verified":True,"direct_adequacy_authority":True,
   "accepted_raw_obligation_ids":ids,"raw_acceptance_obligation_count":len(ids),
   "acceptance_receipt":deepcopy(dict(checked)),"execution_attempted":True,
   "retry_by_other_route_authorized":False,"source_immutability_verified":True,
   "authority_boundary":"PINNED_CCOB_CCYB_TLAC_NECESSARY_PROPERTIES_ONLY__NO_REVERSE_CLASSIFICATION__NO_UNLISTED_PROPERTY_NEGATION__NO_OPEN_WORLD_ONTOLOGY_COMPLETENESS"}
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
