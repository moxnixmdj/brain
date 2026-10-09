from __future__ import annotations
from copy import deepcopy
from decimal import Decimal
from hashlib import sha1,sha256
import json,re
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.bound_capabilities import evidence_decision_synthesis as producer
from canonical.runtime.bound_capabilities import evidence_decision_verify as verifier

SCHEMA="PROJECT_BRAIN_R2_FINANCE_NORMALIZED_DECISION_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::AUTHORIZED_NORMALIZED_FINANCE_DECISION_FAMILY_V1"
CAPABILITY_ID="decision.synthesis.typed.stdlib"
VERIFIER_CAPABILITY_ID="decision.synthesis.verify.stdlib"
PACKAGE_SCHEMA="PROJECT_BRAIN_AUTHORIZED_NORMALIZED_FINANCE_DECISION_PACKAGE_V1"
AUTHORITY_SCHEMA="PROJECT_BRAIN_FINANCE_NORMALIZED_SOURCE_UNIVERSE_AUTHORITY_V1"
VERIFY_SCHEMA="PROJECT_BRAIN_FINANCE_NORMALIZED_SOURCE_UNIVERSE_AUTHORITY_VERIFY_V1"
SUP="SUPERVISORY_AND_COMPLIANCE_NUANCE_OUTSIDE_PUBLIC_BAR_SCOPE"
DOC="DOCUMENT_SPECIFIC_ANALYSIS_LEAVES_OUTSIDE_PUBLIC_BAR_SCOPE"
LEAVES={SUP,DOC}
ROLES={"RULE","EXCEPTION","ESCALATION","DISCLOSURE","FACT","CROSS_REFERENCE","CONTRADICTION","RECONCILIATION","CONDITION"}
ROOT=Path(__file__).resolve().parents[2]
GRAMMAR=re.compile(r"(?:Using|From) the authorized normalized finance decision package at (?P<input>canonical/[A-Za-z0-9_.\-/]+\.json), synthesize the verified finance decision and save it to (?P<output>canonical/[A-Za-z0-9_.\-/]+\.json)\.?",re.I)

def _base(status,passed=False):
 return {"schema":SCHEMA,"status":status,"pass":passed,"matched":False,"semantic_acceptance_complete":False,"actual_goal_satisfaction_verified":False,"direct_adequacy_authority":False,"terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}

def _safe(root,rel,file=False):
 root=Path(root).resolve(); p=Path(str(rel or "").strip())
 if p.is_absolute() or ".." in p.parts or not p.as_posix().startswith("canonical/"): raise ValueError("PATH_INVALID")
 q=(root/p).resolve()
 if q==root or root not in q.parents: raise ValueError("PATH_OUTSIDE_REPOSITORY")
 if file and (not q.is_file() or q.is_symlink()): raise ValueError("FILE_REQUIRED")
 return q

def _load(p):
 x=json.loads(Path(p).read_text(encoding="utf-8"))
 if not isinstance(x,Mapping): raise ValueError("JSON_OBJECT_REQUIRED")
 return x

def _sha(p): return sha256(Path(p).read_bytes()).hexdigest()
def _blob(raw): return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _contract(goal):
 x=compile_contract(goal,source_id="user",routing_target_effects=["finance.normalized.decision"])
 if x.get("pass") is not True: raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
 return x

def _validate(root,package_rel):
 pp=_safe(root,package_rel,True); praw=pp.read_bytes(); pkg=_load(pp)
 if pkg.get("schema")!=PACKAGE_SCHEMA: raise ValueError("PACKAGE_SCHEMA_INVALID")
 leaf=str(pkg.get("leaf_id") or "")
 if leaf not in LEAVES: raise ValueError("FINANCE_LEAF_INVALID")
 dp_rel=str(pkg.get("decision_problem_path") or ""); dp=_safe(root,dp_rel,True)
 if pkg.get("decision_problem_sha256")!=_sha(dp): raise ValueError("DECISION_PROBLEM_SHA256_MISMATCH")
 problem=_load(dp)
 if problem.get("schema")!=producer.SCHEMA: raise ValueError("DECISION_PROBLEM_SCHEMA_INVALID")
 b=pkg.get("authorization_binding")
 if not isinstance(b,Mapping): raise ValueError("AUTHORIZATION_BINDING_REQUIRED")
 ap_rel=str(b.get("authority_path") or ""); vp_rel=str(b.get("verification_path") or "")
 ap=_safe(root,ap_rel,True); vp=_safe(root,vp_rel,True); araw=ap.read_bytes()
 auth=_load(ap); ver=_load(vp); psha=sha256(praw).hexdigest()
 if auth.get("schema")!=AUTHORITY_SCHEMA or auth.get("status")!="ACTIVE": raise ValueError("SOURCE_UNIVERSE_AUTHORITY_INVALID")
 if auth.get("package_path")!=package_rel or auth.get("package_sha256")!=psha: raise ValueError("SOURCE_UNIVERSE_BINDING_MISMATCH")
 if auth.get("complete_source_universe") is not True or auth.get("normalized_semantics_authoritative") is not True: raise ValueError("SOURCE_UNIVERSE_NOT_AUTHORIZED")
 if leaf not in list(auth.get("leaf_ids") or []): raise ValueError("SOURCE_UNIVERSE_LEAF_NOT_AUTHORIZED")
 if ver.get("schema")!=VERIFY_SCHEMA or ver.get("pass") is not True: raise ValueError("SOURCE_UNIVERSE_VERIFICATION_INVALID")
 if ver.get("subject_git_blob_sha")!=_blob(araw) or ver.get("package_sha256")!=psha: raise ValueError("SOURCE_UNIVERSE_VERIFICATION_BINDING_MISMATCH")
 if ver.get("complete_source_universe_verified") is not True or ver.get("normalized_semantics_authoritative_verified") is not True: raise ValueError("SOURCE_UNIVERSE_VERIFICATION_INCOMPLETE")
 if leaf not in list(ver.get("verified_leaf_ids") or []): raise ValueError("SOURCE_UNIVERSE_VERIFIED_LEAF_MISMATCH")
 items=pkg.get("source_items")
 if not isinstance(items,list) or not items: raise ValueError("SOURCE_ITEMS_REQUIRED")
 seen=set(); src_e=set(); norm=[]
 for i,row in enumerate(items):
  if not isinstance(row,Mapping): raise ValueError(f"SOURCE_ITEM_NOT_OBJECT:{i}")
  iid=str(row.get("id") or "").strip(); role=str(row.get("role") or "").strip().upper(); ids=row.get("evidence_ids")
  if not iid or iid in seen or role not in ROLES or not isinstance(ids,list) or not ids: raise ValueError(f"SOURCE_ITEM_INVALID:{i}")
  ids=[str(x).strip() for x in ids]
  if any(not x for x in ids): raise ValueError(f"SOURCE_ITEM_EVIDENCE_INVALID:{iid}")
  seen.add(iid); src_e.update(ids); norm.append({"id":iid,"role":role,"evidence_ids":ids})
 evidence=problem.get("evidence")
 if not isinstance(evidence,list) or not evidence: raise ValueError("DECISION_EVIDENCE_REQUIRED")
 dec_e=[str(x.get("id") or "").strip() for x in evidence if isinstance(x,Mapping)]
 if len(dec_e)!=len(evidence) or len(set(dec_e))!=len(dec_e): raise ValueError("DECISION_EVIDENCE_ID_INVALID")
 if set(dec_e)!=src_e: raise ValueError("SOURCE_TO_DECISION_EVIDENCE_DOMAIN_MISMATCH")
 for row in pkg.get("reconciliation_checks") or []:
  if abs(Decimal(str(row["lhs"]))-Decimal(str(row["rhs"])))>Decimal(str(row.get("tolerance","0"))): raise ValueError("RECONCILIATION_FAILED")
 return {"package_sha256":psha,"leaf_id":leaf,"decision_problem_path":dp_rel,"decision_problem_sha256":_sha(dp),"source_items":norm,"source_item_ids":sorted(seen),"source_evidence_ids":sorted(src_e),"authority_path":ap_rel,"authority_git_blob_sha":_blob(araw),"verification_path":vp_rel}

def preflight(request:Mapping[str,Any],repo_root=None):
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 if not isinstance(request,Mapping): return {**_base("FAIL_CLOSED"),"reason":"REQUEST_NOT_OBJECT"}
 goal=str(request.get("goal") or "").strip(); task=str(request.get("task_id") or "").strip()
 if not goal or not task: return {**_base("FAIL_CLOSED"),"reason":"TASK_ID_AND_GOAL_REQUIRED"}
 m=GRAMMAR.fullmatch(goal)
 if not m: return {**_base("NOT_APPLICABLE"),"matched":False}
 try:
  inp,out=m.group("input"),m.group("output"); material=_validate(root,inp); op=_safe(root,out)
  if _safe(root,inp,True)==op or _safe(root,material["decision_problem_path"],True)==op: raise ValueError("INPUT_OUTPUT_PATH_COLLISION")
  c=_contract(goal); ids=list((c.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
  if not ids: raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
  gsha=sha256(goal.encode()).hexdigest()
  return {**_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),"matched":True,"route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,"verifier_capability_id":VERIFIER_CAPABILITY_ID,"policy_id":"R2_FINANCE_NORMALIZED_DIRECT::"+gsha+"::"+material["package_sha256"],"goal_sha256":gsha,"package_path":inp,"output_path":out,"raw_acceptance_obligation_ids":ids,**material,"semantic_scope":"AUTHORIZED_NORMALIZED_FINANCE_SOURCE_UNIVERSE_TO_TYPED_DECISION","preflight_execution_authority":False}
 except Exception as exc:
  return {**_base("FAIL_CLOSED"),"matched":True,"route_id":ROUTE_ID,"reason":type(exc).__name__+":"+str(exc)}

def _restore(path,existed,raw):
 if existed: path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw or b"")
 else:
  try:path.unlink()
  except FileNotFoundError:pass

def run(request:Mapping[str,Any],repo_root=None):
 root=Path(repo_root).resolve() if repo_root is not None else ROOT; pf=preflight(request,repo_root=root)
 if pf.get("matched") is not True or pf.get("status")=="FAIL_CLOSED": return pf
 outp=_safe(root,pf["output_path"]); existed=outp.is_file(); old=outp.read_bytes() if existed else None
 try:
  package=_safe(root,pf["package_path"],True); decision=_safe(root,pf["decision_problem_path"],True)
  psha,dsha=_sha(package),_sha(decision)
  if psha!=pf["package_sha256"] or dsha!=pf["decision_problem_sha256"]: raise RuntimeError("SOURCE_DRIFT_BEFORE_EXECUTION")
  produced=producer.run({"input_path":pf["decision_problem_path"],"output_path":pf["output_path"]},root)
  if not isinstance(produced,Mapping) or produced.get("output_verified") is not True or produced.get("model_dependency_count")!=0: raise RuntimeError("PRODUCER_NOT_VERIFIED")
  verified=verifier.run({"input_path":pf["decision_problem_path"],"result_path":pf["output_path"]},root)
  if not isinstance(verified,Mapping) or verified.get("verified") is not True or verified.get("producer_independent") is not True or verified.get("model_dependency_count")!=0: raise RuntimeError("INDEPENDENT_DECISION_VERIFICATION_FAILED")
  material=_validate(root,pf["package_path"])
  if _sha(package)!=psha or _sha(decision)!=dsha: raise RuntimeError("SOURCE_MUTATED")
  result=_load(outp); selected=str(result.get("selected_alternative") or ""); rankings=result.get("rankings")
  if result.get("status")!="DECIDED" or not selected or not isinstance(rankings,list): raise RuntimeError("FINANCE_DECISION_NOT_DECIDED")
  row=next((x for x in rankings if isinstance(x,Mapping) and x.get("alternative")==selected),None)
  if not isinstance(row,Mapping): raise RuntimeError("SELECTED_RANKING_MISSING")
  contrib={str(x) for x in row.get("contributing_evidence") or []}
  if contrib!=set(material["source_evidence_ids"]): raise RuntimeError("NOT_ALL_AUTHORIZED_SOURCE_EVIDENCE_CONTRIBUTES")
  c=_contract(str(request["goal"])); ids=list((c.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
  if ids!=pf["raw_acceptance_obligation_ids"]: raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")
  return {**_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",True),"matched":True,"route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,"verifier_capability_id":VERIFIER_CAPABILITY_ID,"selected_policy_id":pf["policy_id"],"goal_sha256":pf["goal_sha256"],"package_path":pf["package_path"],"package_sha256":psha,"decision_problem_path":pf["decision_problem_path"],"decision_problem_sha256":dsha,"output_path":pf["output_path"],"output_sha256":_sha(outp),"leaf_id":pf["leaf_id"],"source_item_ids":material["source_item_ids"],"source_evidence_ids":material["source_evidence_ids"],"semantic_scope":pf["semantic_scope"],"semantic_acceptance_complete":True,"actual_goal_satisfaction_verified":True,"direct_adequacy_authority":True,"accepted_raw_obligation_ids":ids,"raw_acceptance_obligation_count":len(ids),"producer_result":deepcopy(dict(produced)),"acceptance_receipt":deepcopy(dict(verified)),"source_universe_authority_receipt":{"authority_path":material["authority_path"],"authority_git_blob_sha":material["authority_git_blob_sha"],"verification_path":material["verification_path"]},"execution_attempted":True,"retry_by_other_route_authorized":False,"source_immutability_verified":True,"complete_source_to_contributing_evidence_coverage":True,"authority_boundary":"AUTHORIZED_NORMALIZED_FINANCE_SOURCE_PACKAGES_ONLY__NO_RAW_TEXT_SEMANTIC_INFERENCE__NO_GLOBAL_FINANCE_CLOSURE"}
 except Exception as exc:
  _restore(outp,existed,old); rollback=(outp.is_file() and existed and outp.read_bytes()==(old or b"")) if existed else not outp.exists()
  return {**_base("OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"),"matched":True,"route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,"goal_sha256":pf.get("goal_sha256"),"execution_attempted":True,"retry_by_other_route_authorized":False,"rollback_complete":rollback,"reason":type(exc).__name__+":"+str(exc)}
