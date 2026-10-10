"""V9 R12 reuse closure V1.

Fine-tunes the verified V8 reuse closure to the exact V9 declared subject.

The adapter keeps three truths separate:
1. C1-C7 may be reverified on V9 because V9 is an independently verified
   strict positive-route refinement of exact V8.
2. A real exact V9 policy-cover witness can prove material-defeater totality
   and CC_R3 for that claim-scoped run.
3. C8 nonvacuity is NOT granted by policy-cover metadata. It requires a real
   V9 positive router execution that survives executable semantic verification.

Synthetic fixtures exercise the mechanism only and receive zero real-witness,
property, quality, promotion, or terminal credit.
"""
from __future__ import annotations
from hashlib import sha1,sha256
import json
from pathlib import Path
from typing import Any,Mapping

from canonical.runtime import professional_v8_to_v9_r12_positive_refinement_v1 as refinement
from canonical.runtime import professional_v8_r12_reuse_closure_v1 as v8_reuse
from canonical.runtime import observable_policy_cover_totality_gate_v1 as policy_cover
from canonical.runtime import professional_r12_material_defeater_generator_closure_v1 as generator_closure

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_V9_R12_REUSE_CLOSURE_V1"
PROPERTY_CLAIM_ID=v8_reuse.PROPERTY_CLAIM_ID
SCOPE_CLAIM_ID=v8_reuse.SCOPE_CLAIM_ID
LEAF_ID=v8_reuse.LEAF_ID
OBLIGATION=v8_reuse.OBLIGATION
TARGET_SCOPE_SEMANTICS=v8_reuse.TARGET_SCOPE_SEMANTICS
V9_SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V9_DECLARED_SYSTEM_SUBJECT_20261010_V8.json"
V9_SUBJECT_BLOB="2ff32e4bb78e63635244c86d47fa369d7ba53900"
V9_SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V9_EXECUTABLE_TOTALITY_SEMANTICS_SYSTEM_20261010_V8"
V9_SUBJECT_SHA256="adf7f09e1913526e460b7350c02cd148c2cd14de90eed33fa7fae84d395d9912"
REFINE_VERIFY_PATH="canonical/verification/PROFESSIONAL_V8_TO_V9_R12_POSITIVE_REFINEMENT_INDEPENDENT_VERIFY_20261010_V1.json"
REFINE_VERIFY_BLOB="555f8b37ff9b02d4a313121b531f12c60914cf44"
V8_REUSE_VERIFY_PATH="canonical/verification/PROFESSIONAL_V8_R12_REUSE_CLOSURE_INDEPENDENT_VERIFY_20261010_V1.json"
V8_REUSE_VERIFY_BLOB="b01d8ea91f17313bb78feb0dcec0cbd302b671f6"
R12_RECON_PATH=v8_reuse.R12_RECON_PATH
R12_RECON_BLOB=v8_reuse.R12_RECON_BLOB
PRESERVED_CLAUSES=refinement.PRESERVED_CLAUSES

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _digest(v:Any)->str:
 return sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def _zero()->dict[str,Any]:
 return {"semantic_property_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0}

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "preserved_c1_c7_v9_reverified":False,"v9_material_defeater_totality_proved":False,
  "v9_c8_nonvacuity_proved":False,"cc_r3_terminal_closure_proved":False,
  "r4_proof_realization_authority":False,**_zero(),**extra}

def _load(root:Path,rel:str,blob:str)->dict[str,Any]:
 p=root/rel
 if not p.is_file() or p.is_symlink():raise ValueError("PIN_MISSING:"+rel)
 got=_blob(p)
 if got!=blob:raise ValueError("PIN_BLOB_DRIFT:"+rel+":"+got)
 v=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(v,dict):raise ValueError("PIN_NOT_OBJECT:"+rel)
 return v

def verify_preserved_c1_c7(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 try:
  subject=_load(root,V9_SUBJECT_PATH,V9_SUBJECT_BLOB)
  refv=_load(root,REFINE_VERIFY_PATH,REFINE_VERIFY_BLOB)
  v8v=_load(root,V8_REUSE_VERIFY_PATH,V8_REUSE_VERIFY_BLOB)
  r12=_load(root,R12_RECON_PATH,R12_RECON_BLOB)
 except Exception as exc:return _fail(type(exc).__name__+":"+str(exc))

 r=refinement.verify(repo_root=root)
 if r.get("pass") is not True or r.get("positive_route_refinement_proved") is not True:
  return _fail("V8_TO_V9_REFINEMENT_RUNTIME_NOT_PROVED",refinement=r)
 if r.get("preserved_clause_reverification_admissible") is not True:
  return _fail("V9_PRESERVED_CLAUSE_REVERIFICATION_NOT_ADMISSIBLE")
 if tuple(r.get("preserved_clause_ids") or ())!=PRESERVED_CLAUSES:
  return _fail("V9_PRESERVED_CLAUSE_SET_DRIFT")
 truth=refv.get("truth") or {}
 if not str(refv.get("status") or "").startswith(("PASS__SECOND_SPRITE","PASS__INDEPENDENT_SPRITE")):
  return _fail("V8_TO_V9_REFINEMENT_INDEPENDENT_VERIFY_NOT_PASS")
 if truth.get("positive_route_refinement_proved") is not True:
  return _fail("REFINEMENT_VERIFY_MISSING_POSITIVE_ROUTE_REFINEMENT")
 if truth.get("preserved_clause_reverification_admissible") is not True:
  return _fail("REFINEMENT_VERIFY_MISSING_REUSE_AUTHORITY")
 if truth.get("c8_nonvacuity_transport_proved") is not False:
  return _fail("REFINEMENT_VERIFY_C8_TRANSPORT_FORBIDDEN")
 if truth.get("cross_subject_property_authority_transport") is not False:
  return _fail("REFINEMENT_VERIFY_CROSS_SUBJECT_AUTHORITY_FORBIDDEN")

 if not str(v8v.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE"):
  return _fail("V8_REUSE_INDEPENDENT_VERIFY_NOT_PASS")
 ct=v8v.get("current_truth") or {}
 if ct.get("c1_to_c7_exact_v8_reuse_verified") is not True:
  return _fail("V8_C1_C7_REUSE_NOT_VERIFIED")
 if ct.get("v8_c8_nonvacuity_proved") is not False:
  return _fail("V8_REUSE_C8_BOUNDARY_DRIFT")
 v8live=v8_reuse.verify_preserved_c1_c7(repo_root=root)
 if v8live.get("pass") is not True or v8live.get("preserved_c1_c7_v8_reverified") is not True:
  return _fail("V8_REUSE_RUNTIME_NOT_CURRENT",v8_reuse=v8live)

 if subject.get("subject_id")!=V9_SUBJECT_ID or subject.get("subject_sha256")!=V9_SUBJECT_SHA256:
  return _fail("V9_SUBJECT_IDENTITY_DRIFT")
 paths={x.get("path") for x in ((subject.get("system_material") or {}).get("components") or []) if isinstance(x,Mapping)}
 for required in (
  "canonical/runtime/professional_quality_p1_router_v8.py",
  "canonical/runtime/professional_quality_p1_router_v9.py",
  "canonical/runtime/professional_r12_totality_semantic_receipt_v1.py",
 ):
  if required not in paths:return _fail("V9_REQUIRED_COMPONENT_MISSING:"+required)

 states={x.get("id"):x.get("state") for x in (r12.get("clause_state") or []) if isinstance(x,Mapping)}
 if any(states.get(cid)!="VERIFIED_CURRENT" for cid in PRESERVED_CLAUSES):
  return _fail("PRESERVED_CLAUSE_PREMISE_NOT_CURRENT",clause_states=states)
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__C1_TO_C7_REVERIFIED_ON_EXACT_V9_STRICT_REFINEMENT_SUBJECT__C8_REQUIRES_REAL_V9_POSITIVE_ROUTE",
  "v9_subject_id":V9_SUBJECT_ID,"v9_subject_sha256":V9_SUBJECT_SHA256,
  "preserved_clause_ids":list(PRESERVED_CLAUSES),"preserved_clause_count":len(PRESERVED_CLAUSES),
  "preserved_c1_c7_v9_reverified":True,
  "proof_mode":"EXACT_V8_C1_C7_REUSE_PLUS_INDEPENDENT_V8_TO_V9_STRICT_REFINEMENT_REVERIFICATION",
  "cross_subject_property_authority_transport":False,
  "v9_c8_nonvacuity_proved":False,"v9_material_defeater_totality_proved":False,
  "cc_r3_terminal_closure_proved":False,"r4_proof_realization_authority":False,
  "exact_next":"BIND_ONE_REAL_V9_POLICY_RELEVANT_STATE_COVER__THEN_EXECUTE_V9_POSITIVE_ROUTE_FOR_C8__THEN_R4",**_zero()}

def evaluate_v9_totality_cover(problem:Mapping[str,Any],independent_verification:Mapping[str,Any],*,
                                r12_reconciliation:Mapping[str,Any])->dict[str,Any]:
 if not all(isinstance(x,Mapping) for x in (problem,independent_verification,r12_reconciliation)):
  return _fail("INPUT_NOT_MAPPING")
 required={
  "semantic_property_claim_id":PROPERTY_CLAIM_ID,"semantic_scope_claim_id":SCOPE_CLAIM_ID,
  "semantic_obligation":OBLIGATION,"target_scope_semantics":TARGET_SCOPE_SEMANTICS,
  "v9_subject_id":V9_SUBJECT_ID,"v9_subject_sha256":V9_SUBJECT_SHA256,
  "real_exact_run":True,"content_addressed":True,
 }
 for k,e in required.items():
  if problem.get(k)!=e:return _fail("V9_COVER_BINDING_MISMATCH:"+k)
 cp=problem.get("policy_cover_problem")
 if not isinstance(cp,Mapping):return _fail("POLICY_COVER_PROBLEM_REQUIRED")
 cover=policy_cover.evaluate(cp)
 if cover.get("pass") is not True or cover.get("bound_state_totality_proved") is not True:
  return _fail("POLICY_COVER_TOTALITY_NOT_PROVED",policy_cover_verdict=cover)
 digest=_digest(problem)
 reqv={
  "pass":True,"independent_verified":True,"problem_sha256":digest,
  "semantic_property_claim_id":PROPERTY_CLAIM_ID,"semantic_scope_claim_id":SCOPE_CLAIM_ID,
  "semantic_obligation":OBLIGATION,"v9_subject_id":V9_SUBJECT_ID,
  "v9_subject_sha256":V9_SUBJECT_SHA256,"policy_relevant_world_set_complete":True,
  "policy_cover_replay_pass":True,
 }
 for k,e in reqv.items():
  if independent_verification.get(k)!=e:return _fail("V9_COVER_INDEPENDENT_VERIFY_MISMATCH:"+k)
 verifier=independent_verification.get("independent_verifier_id")
 if not isinstance(verifier,str) or not verifier.strip():return _fail("INDEPENDENT_VERIFIER_ID_REQUIRED")
 cert={
  "schema":generator_closure.CERT_SCHEMA,"property_claim_id":PROPERTY_CLAIM_ID,
  "scope_claim_id":SCOPE_CLAIM_ID,"leaf_id":LEAF_ID,"obligation":OBLIGATION,
  "proof_basis":"LOSSLESS_DECOMPOSITION_OR_GENERATOR_CLOSURE",
  "scope_complete":True,"generator_or_universal_cover_complete":True,
  "all_material_defeaters_in_scope_covered":True,"uncovered_material_defeater_complement_empty":True,
  "decision_null_or_resolved_for_every_covered_defeater":True,"independent_verified":True,
  "independent_verifier_id":verifier,"content_addressed":True,"fail_closed_on_unknown":True,
  "finite_catalog_only":False,"eight_clause_count_only":False,"unknown_remainder":[],
 }
 close=generator_closure.evaluate(r12_reconciliation,cert)
 if close.get("pass") is not True or close.get("cc_r3_terminal_closure_proved") is not True:
  return _fail("GENERATOR_CLOSURE_ADAPTER_REJECTED",generator_closure_verdict=close)
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__REAL_V9_POLICY_COVER_PROVES_MATERIAL_DEFEATER_TOTALITY_AND_CC_R3__C8_REQUIRES_ACTUAL_V9_POSITIVE_EXECUTION",
  "problem_sha256":digest,"v9_subject_id":V9_SUBJECT_ID,"v9_subject_sha256":V9_SUBJECT_SHA256,
  "policy_cover_verdict":cover,"v9_material_defeater_totality_proved":True,
  "cc_r3_terminal_closure_proved":True,"v9_c8_nonvacuity_proved":False,
  "c8_boundary":"POLICY_COVER_TOTALITY_IS_NOT_EXISTENCE_OF_AN_ACTUAL_V9_POSITIVE_ROUTER_EXECUTION",
  "preserved_c1_c7_v9_reverified":False,"r4_proof_realization_authority":False,
  "exact_next":"BIND_THIS_TOTALITY_WITNESS_THROUGH_V9_EXECUTABLE_SEMANTIC_AUTHORITY__EXECUTE_AND_INDEPENDENTLY_REPLAY_ONE_REAL_V9_POSITIVE_ROUTE_FOR_C8__THEN_R4",**_zero()}
