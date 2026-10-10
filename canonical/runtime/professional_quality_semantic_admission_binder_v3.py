"""Claim-parameterized professional semantic admission binder V3.

V2 hardened semantic admission but imported one fixed historical claim pack.
V3 removes that version-coupling. The caller supplies the exact current claim;
the binder verifies exact claim identity plus claim-scoped totality, CC_R1/R2/R3,
R4 proof-realization authority, and content-addressed verification basis.

Unknown, stale, mismatched, or incomplete semantic receipts fail closed.
This module grants no quality, acceptance, promotion, or terminal authority.
"""
from __future__ import annotations
from hashlib import sha1,sha256
import json
from pathlib import Path
from typing import Any,Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_SEMANTIC_ADMISSION_BINDER_V3"
RECEIPT_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_VERIFICATION_RECEIPT_V1"
REQUIRED_TOTALITY_FIELDS=(
 "claim_scoped_totality_proved",
 "cc_r1_reality_containment_proved",
 "cc_r2_mission_soundness_proved",
 "cc_r3_terminal_closure_proved",
 "r4_proof_realization_authority",
)

def git_blob_sha(path:Path)->str:
 data=path.read_bytes();return sha1(f"blob {len(data)}\0".encode()+data).hexdigest()
def semantic_sha(text:Any)->str:
 return sha256((text if isinstance(text,str) else "").encode()).hexdigest()
def _resolve(root:Path,raw:Any)->Path|None:
 if not isinstance(raw,str) or not raw.startswith("canonical/"):return None
 p=(root/raw).resolve()
 try:p.relative_to(root.resolve())
 except ValueError:return None
 return p
def _base(status:str,passed:bool,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":passed,"status":status,
  "positive_semantic_admission_authorized":passed,
  "semantic_leaf_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def validate_semantic_receipt(
 receipt:Mapping[str,Any], current_claim:Mapping[str,Any], *,
 leaf_id:str, root_id:str, acceptance:str, contract:str,
 manifest_git_blob_sha:str, repo_root:Path,
)->dict[str,Any]:
 errors:list[str]=[]
 if not isinstance(receipt,Mapping):return _base("FAIL_CLOSED",False,errors=["RECEIPT_NOT_MAPPING"])
 if not isinstance(current_claim,Mapping):return _base("FAIL_CLOSED",False,errors=["CURRENT_CLAIM_NOT_MAPPING"])
 claim=current_claim.get("claim") if isinstance(current_claim.get("claim"),Mapping) else current_claim
 if claim.get("claim_kind")!="PROPERTY_CERTIFICATE":errors.append("CLAIM_KIND_INVALID")
 cid=claim.get("claim_id")
 if not isinstance(cid,str) or len(cid)!=64:errors.append("CLAIM_ID_INVALID")
 checks=(
  (receipt.get("schema")==RECEIPT_SCHEMA,"RECEIPT_SCHEMA_INVALID"),
  (receipt.get("leaf_id")==leaf_id,"LEAF_ID_MISMATCH"),
  (receipt.get("root_id")==root_id,"ROOT_ID_MISMATCH"),
  (receipt.get("leaf_kind")=="SEMANTIC","LEAF_KIND_MISMATCH"),
  (receipt.get("verdict")=="PASS","VERDICT_NOT_PASS"),
  (receipt.get("closure_scope")=="EXACT_LEAF","CLOSURE_SCOPE_INVALID"),
  (receipt.get("acceptance_sha256")==semantic_sha(acceptance),"ACCEPTANCE_BINDING_MISMATCH"),
  (receipt.get("root_contract_sha256")==semantic_sha(contract),"ROOT_CONTRACT_BINDING_MISMATCH"),
  (receipt.get("manifest_git_blob_sha")==manifest_git_blob_sha,"MANIFEST_BINDING_MISMATCH"),
  (receipt.get("leaf_semantic_satisfied") is True,"SEMANTIC_SATISFACTION_NOT_PROVED"),
  (receipt.get("semantic_claim_id")==claim.get("claim_id"),"SEMANTIC_CLAIM_ID_MISMATCH"),
  (receipt.get("semantic_scope_sha256")==claim.get("scope_sha256"),"SEMANTIC_SCOPE_BINDING_MISMATCH"),
  (receipt.get("semantic_target_predicate_sha256")==claim.get("target_predicate_sha256"),"SEMANTIC_TARGET_BINDING_MISMATCH"),
  (receipt.get("semantic_semantics_sha256")==claim.get("semantics_sha256"),"SEMANTIC_SEMANTICS_BINDING_MISMATCH"),
  (receipt.get("terminal_authority") is False,"RECEIPT_TERMINAL_AUTHORITY_INVALID"),
 )
 for ok,e in checks:
  if not ok:errors.append(e)
 for field in REQUIRED_TOTALITY_FIELDS:
  if receipt.get(field) is not True:errors.append(field.upper()+"_REQUIRED")

 basis=receipt.get("verification_basis")
 if not isinstance(basis,list) or not basis:errors.append("VERIFICATION_BASIS_REQUIRED");basis=[]
 basis_records=[]; semantic_basis_ok=False
 for item in basis:
  if not isinstance(item,Mapping):
   errors.append("VERIFICATION_BASIS_ENTRY_INVALID");continue
  p=_resolve(repo_root,item.get("path"))
  exp=item.get("git_blob_sha")
  if p is None or not p.is_file() or p.is_symlink():
   errors.append("VERIFICATION_BASIS_MISSING");continue
  got=git_blob_sha(p);record={"path":item.get("path"),"git_blob_sha":got};basis_records.append(record)
  if got!=exp:errors.append("VERIFICATION_BASIS_STALE");continue
  try:doc=json.loads(p.read_text(encoding="utf-8"))
  except Exception:errors.append("VERIFICATION_BASIS_JSON_INVALID");continue
  if not isinstance(doc,Mapping):errors.append("VERIFICATION_BASIS_NOT_OBJECT");continue
  if (
   doc.get("pass") is True
   and doc.get("independent_verified") is True
   and doc.get("leaf_id")==leaf_id and doc.get("root_id")==root_id
   and doc.get("semantic_claim_id")==claim.get("claim_id")
   and doc.get("semantic_scope_sha256")==claim.get("scope_sha256")
   and doc.get("semantic_target_predicate_sha256")==claim.get("target_predicate_sha256")
   and doc.get("semantic_semantics_sha256")==claim.get("semantics_sha256")
   and all(doc.get(field) is True for field in REQUIRED_TOTALITY_FIELDS)
  ):
   semantic_basis_ok=True
 if not semantic_basis_ok:errors.append("INDEPENDENT_SEMANTIC_TOTALITY_BASIS_REQUIRED")
 if errors:return _base("FAIL_CLOSED",False,errors=sorted(set(errors)),claim_id=cid,leaf_id=leaf_id,root_id=root_id,basis_records=basis_records)
 return _base("PASS__EXACT_CURRENT_CLAIM_PLUS_FOUR_ROOT_TOTALITY_AND_R4",True,
  errors=[],claim_id=cid,leaf_id=leaf_id,root_id=root_id,basis_records=basis_records,
  claim_scoped_totality_proved=True,cc_r1_reality_containment_proved=True,
  cc_r2_mission_soundness_proved=True,cc_r3_terminal_closure_proved=True,
  r4_proof_realization_authority=True)

def prove_fail_closed_shape()->dict[str,Any]:
 return _base("PASS__STRUCTURAL_FAIL_CLOSED_ADMISSION_SHAPE",True,
  required_exact_claim_fields=["claim_id","scope_sha256","target_predicate_sha256","semantics_sha256"],
  required_totality_fields=list(REQUIRED_TOTALITY_FIELDS),
  content_addressed_basis_required=True,
  unknown_or_mismatch_authorized=False)
