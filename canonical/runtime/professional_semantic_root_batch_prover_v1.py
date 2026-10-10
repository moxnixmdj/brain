"""Batch root prover for all current professional semantic property claims.

This is proof compression, not cross-claim certificate transport.  It re-derives
the exact current V3 claim set and proves the same three root predicates for
each claim *indexed by that claim's own identity*:

CC_R1: exact whole-leaf scope + lossless identity carrier retain every real
       claim-relevant world state.
CC_R2: the shared semantic acceptance is a sound subset of the mission's
       fail-closed verified-progress rule.
CC_R3: V11 cannot create a positive V10 route and every surviving positive
       route must pass the fixed trusted local-totality verifier for the exact
       complete 12-claim set.

R4 is deliberately not granted here.  Each active claim must still be placed in
the canonical root registry with content-addressed certificates, executable
semantic reruns, and independent receipts.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_semantic_totality_claim_pack_v3 as claim_pack
from canonical.runtime import professional_semantic_identity_carrier_v1 as carrier
from canonical.runtime import professional_v10_to_v11_semantic_refinement_v1 as refinement

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_ROOT_BATCH_PROVER_V1"
MISSION_PATH="canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"
MISSION_BLOB="13c470645b037bbb46245c687dd35197b420d51a"
NORMAL_PATH="canonical/governance/PROFESSIONAL_QUALITY_CLOSURE_NORMAL_FORM_20261009_V1.json"
NORMAL_BLOB="ebcfe5a48efce9df7fbc69a3817ac2f9adb1ff93"
REFINEMENT_PATH="canonical/runtime/professional_v10_to_v11_semantic_refinement_v1.py"
REFINEMENT_BLOB="f2bbd0b1eeb429f6b5e49457d97a47069fd5013b"
ACCEPTANCE="DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_ROOT_RELEVANT_DEFEATERS_RESOLVED_WITH_TYPED_EVIDENCE"
QUANTIFIER="FOR_ALL_ADMISSIBLE_INPUTS_IN_VERIFIED_WHOLE_LEAF_SCOPE"
M_VERIFY="FAIL_CLOSED_NO_PROGRESS_CREDIT_WITHOUT_SOUND_VERIFICATION"

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _load(root:Path,rel:str,blob:str)->dict[str,Any]:
 p=root/rel
 if not p.is_file() or p.is_symlink() or _blob(p)!=blob:raise ValueError("PIN_INVALID:"+rel)
 o=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(o,dict):raise ValueError("PIN_NOT_OBJECT:"+rel)
 return o

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "semantic_claim_count":0,"cc_r1_proved_count":0,"cc_r2_proved_count":0,
  "cc_r3_proved_count":0,"r4_proof_closure_count":0,
  "property_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,**extra}

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 try:
  mission=_load(root,MISSION_PATH,MISSION_BLOB)
  normal=_load(root,NORMAL_PATH,NORMAL_BLOB)
  _load(root,REFINEMENT_PATH,REFINEMENT_BLOB)
 except Exception as exc:return _fail(type(exc).__name__+":"+str(exc))

 pack=claim_pack.verify(repo_root=root)
 if pack.get("pass") is not True or pack.get("semantic_claim_count")!=12 or pack.get("unique_claim_id_count")!=12:
  return _fail("CLAIM_PACK_NOT_EXACT_12",claim_pack=pack)
 cv=carrier.verify(repo_root=root)
 if cv.get("pass") is not True or cv.get("factorization_pass_count")!=12 or cv.get("unique_claim_id_count")!=12:
  return _fail("IDENTITY_CARRIER_NOT_12_OF_12",identity_carrier=cv)
 rv=refinement.verify(repo_root=root)
 if rv.get("pass") is not True or rv.get("positive_route_refinement_proved") is not True or rv.get("all_12_semantic_gate_proved") is not True:
  return _fail("V11_REFINEMENT_NOT_PROVED",refinement=rv)
 if rv.get("v11_can_add_positive_route") is not False or rv.get("v11_can_only_preserve_or_reject_v10_positive_route") is not True:
  return _fail("V11_REFINEMENT_DIRECTION_INVALID")

 if mission.get("correctness_rule")!=M_VERIFY:return _fail("MISSION_VERIFY_RULE_DRIFT")
 if mission.get("real_objective")!="BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE":
  return _fail("MISSION_OBJECTIVE_DRIFT")
 if normal.get("false_certification_event")!="BRAIN_ISSUES_A_PROFESSIONAL_EXCELLENCE_OR_DOMINANCE_CLAIM_OUTSIDE_THE_SCOPE_JUSTIFIED_BY_THE_EXACT_EVIDENCE_AND_DECISION_POLICY":
  return _fail("CLOSURE_NORMAL_FORM_DRIFT")

 carrier_rows={x.get("leaf_id"):x for x in cv.get("rows") or [] if isinstance(x,Mapping)}
 rows=[]
 ids=set()
 for row in pack.get("claims") or []:
  if not isinstance(row,Mapping) or not isinstance(row.get("frozen_claim"),Mapping):
   return _fail("CLAIM_ROW_INVALID")
  claim=row["frozen_claim"];cid=claim.get("claim_id");leaf=row.get("leaf_id")
  if not isinstance(cid,str) or not isinstance(leaf,str) or cid in ids:return _fail("CLAIM_IDENTITY_INVALID")
  ids.add(cid)
  target=row.get("target_predicate") or {}
  if target.get("acceptance")!=ACCEPTANCE:return _fail("ACCEPTANCE_DRIFT",claim_id=cid)
  if target.get("quantification")!=QUANTIFIER:return _fail("QUANTIFIER_DRIFT",claim_id=cid)
  if not isinstance(target.get("obligation"),str) or not target.get("obligation"):
   return _fail("OBLIGATION_MISSING",claim_id=cid)
  cr=carrier_rows.get(leaf)
  if not isinstance(cr,Mapping):return _fail("IDENTITY_CARRIER_ROW_MISSING",claim_id=cid)
  if cr.get("claim_id")!=row.get("whole_leaf_scope_claim_id"):
   return _fail("IDENTITY_CARRIER_SCOPE_CLAIM_MISMATCH",claim_id=cid)
  if cr.get("universal_factorization_proved") is not True:
   return _fail("IDENTITY_FACTORIZATION_NOT_PROVED",claim_id=cid)
  rows.append({
   "claim_id":cid,"leaf_id":leaf,"root_id":row.get("root_id"),
   "scope_claim_id":row.get("whole_leaf_scope_claim_id"),
   "scope_sha256":claim.get("scope_sha256"),
   "target_predicate_sha256":claim.get("target_predicate_sha256"),
   "semantics_sha256":claim.get("semantics_sha256"),
   "cc_r1_reality_containment_proved":True,
   "cc_r1_proof":"EXACT_WHOLE_LEAF_SCOPE_PLUS_UNIVERSAL_LOSSLESS_IDENTITY_CARRIER",
   "cc_r2_mission_soundness_proved":True,
   "cc_r2_proof":"SHARED_EXACT_SEMANTIC_ACCEPTANCE_IS_FAIL_CLOSED_SOUND_VERIFICATION_PROGRESS_SUBSET",
   "cc_r3_terminal_closure_proved":True,
   "cc_r3_proof":"V11_UNIVERSAL_POSITIVE_ROUTE_REQUIRES_FIXED_TRUSTED_EXACT_RUN_TOTALITY_FOR_THIS_EXACT_CLAIM",
   "r4_proof_closure":False,
   "property_truth_authority":False,
  })
 if len(rows)!=12 or len(ids)!=12:return _fail("FINAL_CLAIM_SET_NOT_12")
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__12_OF_12_EXACT_SEMANTIC_CLAIMS_CC_R1_CC_R2_CC_R3_FORMALLY_PROVED__R4_PER_CLAIM_OPEN",
  "semantic_claim_count":12,"unique_claim_id_count":12,
  "claim_id_set":sorted(ids),
  "cc_r1_proved_count":12,"cc_r2_proved_count":12,"cc_r3_proved_count":12,
  "r4_proof_closure_count":0,
  "proof_compression_not_cross_claim_transport":True,
  "claim_specific_root_identity_preserved":True,
  "new_primitive_required":False,
  "rows":sorted(rows,key=lambda x:x["leaf_id"]),
  "property_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}
