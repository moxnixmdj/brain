"""Compile V10 semantic property truth from exact independent bases.

For every truth-repaired V10 semantic claim:
- construct the exact leaf verification receipt;
- bind its independent claim-specific totality basis by Git blob SHA;
- require bounded positive nonvacuity in that basis;
- execute Binder V3 on the receipt.

Only 12/12 successful real binder admissions yield semantic leaf property truth.
No quality, acceptance, promotion, or terminal authority is granted here.
"""
from __future__ import annotations
from hashlib import sha1,sha256
import json
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import professional_quality_semantic_admission_binder_v3 as binder
from canonical.runtime import professional_semantic_v2_v10_claim_batch_v1 as claims

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_V10_PROPERTY_TRUTH_COMPILER_V1"
MANIFEST="canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261011_V2.json"
MANIFEST_BLOB="8ae72d7d44047ac9dec1b014c34a44f9933f0215"
BASIS_PREFIX="canonical/verification/professional-semantic-v10/"

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(f"blob {len(d)}\0".encode()+d).hexdigest()
def _canon(v:Any)->str:
 return sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "verified_semantic_leaf_count":0,"semantic_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 mp=root/MANIFEST
 if not mp.is_file() or mp.is_symlink() or _blob(mp)!=MANIFEST_BLOB:return _fail("MANIFEST_PIN_FAIL")
 try:manifest=json.loads(mp.read_text())
 except Exception:return _fail("MANIFEST_JSON_INVALID")
 roots={r.get("root_id"):r for r in manifest.get("roots") or [] if isinstance(r,Mapping)}
 batch=claims.verify(root=root)
 if batch.get("pass") is not True or batch.get("claim_count")!=12 or batch.get("scope_complete_count")!=12:
  return _fail("V10_CLAIM_BATCH_NOT_CURRENT")
 out=[]
 for row in batch["rows"]:
  rid=row["root_id"];leaf=row["leaf_id"];cs=row["claim_scope"];cl=cs["claim"]
  mr=roots.get(rid)
  if not isinstance(mr,Mapping):return _fail("ROOT_NOT_IN_MANIFEST",root_id=rid)
  sem=mr.get("semantic_leaf") or {}
  if sem.get("id")!=leaf:return _fail("LEAF_BINDING_DRIFT",root_id=rid)
  bpath=BASIS_PREFIX+cl["claim_id"]+".json";bp=root/bpath
  if not bp.is_file() or bp.is_symlink():return _fail("TOTALITY_BASIS_MISSING",root_id=rid)
  bsha=_blob(bp)
  try:basis=json.loads(bp.read_text())
  except Exception:return _fail("TOTALITY_BASIS_JSON_INVALID",root_id=rid)
  required={
   "pass":True,"independent_verified":True,"leaf_id":leaf,"root_id":rid,
   "semantic_claim_id":cl["claim_id"],"semantic_scope_sha256":cl["scope_sha256"],
   "semantic_target_predicate_sha256":cl["target_predicate_sha256"],
   "semantic_semantics_sha256":cl["semantics_sha256"],
   "claim_scoped_totality_proved":True,"cc_r1_reality_containment_proved":True,
   "cc_r2_mission_soundness_proved":True,"cc_r3_terminal_closure_proved":True,
   "r4_proof_realization_authority":True,"positive_route_nonvacuity_proved":True
  }
  if not isinstance(basis,Mapping) or any(basis.get(k)!=v for k,v in required.items()):
   return _fail("TOTALITY_BASIS_BINDING_OR_TRUTH_MISMATCH",root_id=rid)
  receipt={
   "schema":binder.RECEIPT_SCHEMA,"leaf_id":leaf,"root_id":rid,"leaf_kind":"SEMANTIC",
   "verdict":"PASS","closure_scope":"EXACT_LEAF",
   "acceptance_sha256":binder.semantic_sha(sem.get("acceptance")),
   "root_contract_sha256":binder.semantic_sha(mr.get("contract")),
   "manifest_git_blob_sha":MANIFEST_BLOB,"leaf_semantic_satisfied":True,
   "semantic_claim_id":cl["claim_id"],"semantic_scope_sha256":cl["scope_sha256"],
   "semantic_target_predicate_sha256":cl["target_predicate_sha256"],
   "semantic_semantics_sha256":cl["semantics_sha256"],
   "claim_scoped_totality_proved":True,"cc_r1_reality_containment_proved":True,
   "cc_r2_mission_soundness_proved":True,"cc_r3_terminal_closure_proved":True,
   "r4_proof_realization_authority":True,"terminal_authority":False,
   "verification_basis":[{"path":bpath,"git_blob_sha":bsha}]
  }
  verdict=binder.validate_semantic_receipt(receipt,cs,leaf_id=leaf,root_id=rid,
   acceptance=sem.get("acceptance"),contract=mr.get("contract"),
   manifest_git_blob_sha=MANIFEST_BLOB,repo_root=root)
  if verdict.get("pass") is not True or verdict.get("positive_semantic_admission_authorized") is not True:
   return _fail("BINDER_V3_ADMISSION_FAILED",root_id=rid,verdict=verdict)
  out.append({"leaf_id":leaf,"root_id":rid,"claim_id":cl["claim_id"],
   "basis_path":bpath,"basis_git_blob_sha":bsha,"receipt_sha256":_canon(receipt),
   "positive_semantic_admission_authorized":True,"positive_route_nonvacuity_proved":True,
   "leaf_property_truth_authority":True})
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__12_OF_12_V10_SEMANTIC_LEAVES_PROPERTY_TRUTH__12_OF_12_BINDER_V3_POSITIVE_ADMISSIONS__ZERO_QUALITY_OR_TERMINAL_CREDIT",
  "verified_semantic_leaf_count":12,"open_semantic_leaf_count":0,
  "rows":out,"semantic_property_truth_authority":True,
  "combined_professional_property_truth_count":24,"combined_professional_property_truth_total":24,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,
  "exact_next":"INDEPENDENTLY_REPLAY_THIS_PROPERTY_TRUTH_COMPILER__FREEZE_RECEIPTS__RUN_FULL_CURRENT_MAIN_REGRESSION__THEN_EVALUATE_ASSURANCE_COMPILER_PROMOTION"}
