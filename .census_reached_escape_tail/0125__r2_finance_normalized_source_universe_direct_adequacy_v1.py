"""Direct adequacy for complete normalized finance decision packages.

The package itself is the authoritative task input. This route proves no mapping
from arbitrary raw prose into the package. It proves that every typed package
evidence item is accounted for in the finance role partition, every declared
reconciliation is exact within tolerance, and the final typed decision is
independently recomputed.
"""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal,InvalidOperation
from hashlib import sha256
import json,re
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.bound_capabilities import evidence_decision_synthesis as producer
from canonical.runtime.bound_capabilities import evidence_decision_verify as verifier

SCHEMA="PROJECT_BRAIN_R2_FINANCE_NORMALIZED_SOURCE_UNIVERSE_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::FINANCE_NORMALIZED_SOURCE_UNIVERSE_DECISION_FAMILY_V1"
CAPABILITY_ID="decision.synthesis.typed.stdlib"
VERIFIER_CAPABILITY_ID="decision.synthesis.verify.stdlib"
PACKAGE_SCHEMA="PROJECT_BRAIN_NORMALIZED_FINANCE_DECISION_PACKAGE_V1"
SUP="SUPERVISORY_AND_COMPLIANCE_NUANCE_OUTSIDE_PUBLIC_BAR_SCOPE"
DOC="DOCUMENT_SPECIFIC_ANALYSIS_LEAVES_OUTSIDE_PUBLIC_BAR_SCOPE"
ROLE_KEYS={
 SUP:("RULE","EXCEPTION","ESCALATION","DISCLOSURE"),
 DOC:("FACT","CROSS_REFERENCE","CONTRADICTION","EXCEPTION","RECONCILIATION"),
}
ROOT=Path(__file__).resolve().parents[2]
GRAMMAR=re.compile(r"(?:Using|From) the complete normalized finance decision package at (?P<input>canonical/[A-Za-z0-9_.\-/]+\.json), synthesize and independently verify the finance decision and save it to (?P<output>canonical/[A-Za-z0-9_.\-/]+\.json)\.?",re.I)

def _base(status,passed=False):
 return {"schema":SCHEMA,"status":status,"pass":passed,"matched":False,"semantic_acceptance_complete":False,"actual_goal_satisfaction_verified":False,"direct_adequacy_authority":False,"terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}

def _safe(root,rel,file=False):
 root=Path(root).resolve(); p=Path(str(rel or "").strip())
 if p.is_absolute() or ".." in p.parts or not p.as_posix().startswith("canonical/"): raise ValueError("PATH_INVALID")
 q=(root/p).resolve()
 if q==root or root not in q.parents: raise ValueError("PATH_OUTSIDE_REPOSITORY")
 if file and (not q.is_file() or q.is_symlink()): raise ValueError("FILE_REQUIRED")
 return q

def _contract(goal):
 x=compile_contract(goal,source_id="user",routing_target_effects=["finance.normalized.source_universe.decision"])
 if x.get("pass") is not True: raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
 return x

def _canon_sha(x):
 return sha256(json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def _reconciliations(rows,expected_ids):
 if not isinstance(rows,list): raise ValueError("RECONCILIATION_CHECKS_INVALID")
 seen=set(); bound=set()
 for i,row in enumerate(rows):
  if not isinstance(row,Mapping): raise ValueError(f"RECONCILIATION_NOT_OBJECT:{i}")
  rid=str(row.get("id") or "").strip(); eid=str(row.get("evidence_id") or "").strip()
  if not rid or rid in seen or not eid: raise ValueError(f"RECONCILIATION_ID_OR_EVIDENCE_INVALID:{i}")
  seen.add(rid); bound.add(eid)
  try:
   lhs=Decimal(str(row["lhs"])); rhs=Decimal(str(row["rhs"])); tol=Decimal(str(row.get("tolerance","0")))
   if tol<0 or abs(lhs-rhs)>tol: raise ValueError("RECONCILIATION_FAILED:"+rid)
  except (KeyError,InvalidOperation):
   raise ValueError("RECONCILIATION_VALUE_INVALID:"+rid)
 if bound!=set(expected_ids): raise ValueError("RECONCILIATION_EVIDENCE_DOMAIN_MISMATCH")
 return sorted(seen)

def _validate_package(pkg):
 if not isinstance(pkg,Mapping) or pkg.get("schema")!=PACKAGE_SCHEMA: raise ValueError("PACKAGE_SCHEMA_INVALID")
 allowed={"schema","package_id","leaf_id","decision_problem","role_evidence_ids","reconciliation_checks"}
 if set(pkg)!=allowed: raise ValueError("PACKAGE_FIELD_SET_NOT_EXACT")
 if not isinstance(pkg.get("package_id"),str) or not pkg["package_id"].strip(): raise ValueError("PACKAGE_ID_INVALID")
 leaf=str(pkg.get("leaf_id") or "")
 if leaf not in ROLE_KEYS: raise ValueError("FINANCE_LEAF_INVALID")
 problem=pkg.get("decision_problem")
 if not isinstance(problem,dict) or problem.get("schema")!=producer.SCHEMA: raise ValueError("DECISION_PROBLEM_INVALID")
 normalized=producer._normalize(problem)
 evid_ids={x["id"] for x in normalized["evidence"]}
 roles=pkg.get("role_evidence_ids")
 if not isinstance(roles,Mapping) or set(roles)!=set(ROLE_KEYS[leaf]): raise ValueError("FINANCE_ROLE_PARTITION_KEYS_INVALID")
 seen=set()
 for role in ROLE_KEYS[leaf]:
  ids=roles.get(role)
  if not isinstance(ids,list) or any(not isinstance(x,str) or not x for x in ids): raise ValueError("FINANCE_ROLE_IDS_INVALID:"+role)
  if len(ids)!=len(set(ids)): raise ValueError("FINANCE_ROLE_IDS_DUPLICATE:"+role)
  overlap=seen.intersection(ids)
  if overlap: raise ValueError("FINANCE_ROLE_PARTITION_OVERLAP:"+",".join(sorted(overlap)))
  seen.update(ids)
 if seen!=evid_ids: raise ValueError("FINANCE_ROLE_PARTITION_NOT_COMPLETE")
 if leaf==SUP:
  if not roles["RULE"] or not roles["EXCEPTION"]: raise ValueError("SUPERVISORY_RULE_AND_EXCEPTION_REQUIRED")
  if pkg["reconciliation_checks"] not in ([],None): raise ValueError("SUPERVISORY_RECONCILIATION_CHECKS_UNSUPPORTED")
  recon=[]
 else:
  if not roles["FACT"] or not roles["CROSS_REFERENCE"]: raise ValueError("DOCUMENT_FACT_AND_CROSS_REFERENCE_REQUIRED")
  recon=_reconciliations(pkg["reconciliation_checks"],roles["RECONCILIATION"])
 return {"leaf_id":leaf,"problem":deepcopy(problem),"problem_sha256":_canon_sha(problem),"evidence_ids":sorted(evid_ids),"role_evidence_ids":deepcopy(dict(roles)),"reconciliation_ids":recon}

def preflight(request:Mapping[str,Any],repo_root=None):
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 if not isinstance(request,Mapping): return {**_base("FAIL_CLOSED"),"reason":"REQUEST_NOT_OBJECT"}
 goal=str(request.get("goal") or "").strip(); task=str(request.get("task_id") or "").strip()
 if not goal or not task: return {**_base("FAIL_CLOSED"),"reason":"TASK_ID_AND_GOAL_REQUIRED"}
 m=GRAMMAR.fullmatch(goal)
 if not m: return {**_base("NOT_APPLICABLE"),"matched":False}
 try:
  inp,out=m.group("input"),m.group("output"); ip=_safe(root,inp,True); op=_safe(root,out)
  if ip==op: raise ValueError("INPUT_OUTPUT_PATH_COLLISION")
  raw=ip.read_bytes(); pkg=json.loads(raw.decode()); material=_validate_package(pkg)
  c=_contract(goal); ids=list((c.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
  if not ids: raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
  gsha=sha256(goal.encode()).hexdigest()
  return {**_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),"matched":True,"route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,"verifier_capability_id":VERIFIER_CAPABILITY_ID,"policy_id":"R2_FINANCE_NORMALIZED_SOURCE_UNIVERSE::"+gsha+"::"+sha256(raw).hexdigest(),"goal_sha256":gsha,"input_path":inp,"input_sha256":sha256(raw).hexdigest(),"output_path":out,"raw_acceptance_obligation_ids":ids,**{k:v for k,v in material.items() if k!="problem"},"semantic_scope":"COMPLETE_TYPED_FINANCE_PACKAGE_SOURCE_UNIVERSE_TO_INDEPENDENTLY_RECOMPUTED_DECISION","preflight_execution_authority":False}
 except Exception as exc:
  return {**_base("FAIL_CLOSED"),"matched":True,"route_id":ROUTE_ID,"reason":type(exc).__name__+":"+str(exc)}

def _restore(path,existed,raw):
 if existed:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw or b"")
 else:
  try:path.unlink()
  except FileNotFoundError:pass

def run(request:Mapping[str,Any],repo_root=None):
 root=Path(repo_root).resolve() if repo_root is not None else ROOT; pf=preflight(request,repo_root=root)
 if pf.get("matched") is not True or pf.get("status")=="FAIL_CLOSED": return pf
 ip=_safe(root,pf["input_path"],True); op=_safe(root,pf["output_path"]); existed=op.is_file(); old=op.read_bytes() if existed else None
 try:
  before=ip.read_bytes()
  if sha256(before).hexdigest()!=pf["input_sha256"]: raise RuntimeError("INPUT_DRIFT_BEFORE_EXECUTION")
  pkg=json.loads(before.decode()); material=_validate_package(pkg); problem=material["problem"]
  result=producer.synthesize(problem)
  ok,reason=verifier.verify(problem,result)
  if not ok: raise RuntimeError("INDEPENDENT_DECISION_VERIFICATION_FAILED:"+reason)
  if result.get("model_dependency_count")!=0: raise RuntimeError("MODEL_DEPENDENCY_NONZERO")
  rankings=result.get("rankings")
  if not isinstance(rankings,list): raise RuntimeError("RANKINGS_MISSING")
  covered=set()
  for row in rankings:
   if isinstance(row,Mapping): covered.update(str(x) for x in row.get("contributing_evidence") or [])
  if covered!=set(material["evidence_ids"]): raise RuntimeError("DECISION_EVIDENCE_COVERAGE_INCOMPLETE")
  if ip.read_bytes()!=before: raise RuntimeError("INPUT_MUTATED")
  op.parent.mkdir(parents=True,exist_ok=True); op.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
  reread=json.loads(op.read_text(encoding="utf-8")); ok2,reason2=verifier.verify(problem,reread)
  if not ok2: raise RuntimeError("OUTPUT_READBACK_VERIFICATION_FAILED:"+reason2)
  c=_contract(str(request["goal"])); ids=list((c.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
  if ids!=pf["raw_acceptance_obligation_ids"]: raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")
  return {**_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",True),"matched":True,"route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,"verifier_capability_id":VERIFIER_CAPABILITY_ID,"selected_policy_id":pf["policy_id"],"goal_sha256":pf["goal_sha256"],"input_path":pf["input_path"],"input_sha256":pf["input_sha256"],"output_path":pf["output_path"],"output_sha256":sha256(op.read_bytes()).hexdigest(),"leaf_id":material["leaf_id"],"role_evidence_ids":material["role_evidence_ids"],"reconciliation_ids":material["reconciliation_ids"],"semantic_scope":pf["semantic_scope"],"semantic_acceptance_complete":True,"actual_goal_satisfaction_verified":True,"direct_adequacy_authority":True,"accepted_raw_obligation_ids":ids,"raw_acceptance_obligation_count":len(ids),"acceptance_receipt":{"verified":True,"reason":reason2,"producer_independent":True,"model_dependency_count":0},"execution_attempted":True,"retry_by_other_route_authorized":False,"source_immutability_verified":True,"normalized_package_field_coverage_complete":True,"finance_role_partition_complete":True,"decision_evidence_coverage_complete":True,"authority_boundary":"NORMALIZED_TYPED_PACKAGE_IS_THE_TASK_SOURCE_UNIVERSE__NO_RAW_TEXT_TO_PACKAGE_SEMANTIC_CORRECTNESS_CLAIM__NO_GLOBAL_FINANCE_CLOSURE"}
 except Exception as exc:
  _restore(op,existed,old); rollback=(op.is_file() and existed and op.read_bytes()==(old or b"")) if existed else not op.exists()
  return {**_base("OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"),"matched":True,"route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,"goal_sha256":pf.get("goal_sha256"),"execution_attempted":True,"retry_by_other_route_authorized":False,"rollback_complete":rollback,"reason":type(exc).__name__+":"+str(exc)}
