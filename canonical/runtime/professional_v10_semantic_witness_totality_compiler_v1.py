"""Compile 12 existing bounded semantic witnesses into exact V10 claim-scoped totality candidates.

Truth repair used:
  whole admissible claim domain = bounded positive semantic subdomain UNION fail-closed complement.

For each root, the positive subdomain is the exact content-addressed bounded semantic
witness already present in the scoped-evidence registry. Outside that subdomain,
V10 semantic admission has no authority unless an exact independent totality basis
is supplied; unknown/mismatched/incomplete receipts fail closed.

This module is deliberately not self-authorizing. It proves candidate CC_R1/R2/R3
shape only. Independent replay is still required before R4/proof-realization or
semantic leaf property truth can be minted.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any,Mapping

from canonical.runtime import professional_semantic_v2_v10_claim_batch_v1 as claims
from canonical.runtime import professional_quality_semantic_admission_binder_v3 as binder

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_V10_SEMANTIC_WITNESS_TOTALITY_COMPILER_V1"
MANIFEST_PATH="canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261011_V2.json"
MANIFEST_BLOB="8ae72d7d44047ac9dec1b014c34a44f9933f0215"
REGISTRY_PATH="canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json"
REGISTRY_BLOB="b9ddf7cbe7fbfad0e81fe068a0c19b48703b5aba"
CLAIM_VERIFY_PATH="canonical/verification/PROFESSIONAL_SEMANTIC_V2_V10_CLAIM_BATCH_INDEPENDENT_VERIFY_20261011_V1.json"
CLAIM_VERIFY_BLOB="d4e545e046febf4e1248f18346ce80decf239a3a"
BINDER_PATH="canonical/runtime/professional_quality_semantic_admission_binder_v3.py"
BINDER_BLOB="6e8e5ac7c4cf4cc38e5e7a6f0ad6a0c80f0683be"
CLAIM_RUNTIME_PATH="canonical/runtime/professional_semantic_v2_v10_claim_batch_v1.py"
CLAIM_RUNTIME_BLOB="75fcbaf92a2b84b0d670ef7d784107590c5f1d08"

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def _load(root:Path,rel:str,blob:str)->Mapping[str,Any]:
 p=root/rel
 if not p.is_file() or p.is_symlink():raise ValueError("PIN_MISSING:"+rel)
 got=_blob(p)
 if got!=blob:raise ValueError("PIN_BLOB_DRIFT:"+rel+":"+got)
 o=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(o,Mapping):raise ValueError("PIN_NOT_OBJECT:"+rel)
 return o
def _pin(root:Path,rel:str,blob:str)->None:
 p=root/rel
 if not p.is_file() or p.is_symlink():raise ValueError("PIN_MISSING:"+rel)
 got=_blob(p)
 if got!=blob:raise ValueError("PIN_BLOB_DRIFT:"+rel+":"+got)
def _zero()->dict[str,Any]:
 return {"independent_verified":False,"r4_proof_realization_authority":False,
  "semantic_property_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0}
def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "compiled_root_count":0,"claim_scoped_totality_candidate_count":0,**_zero(),**extra}
def _safe_ref(root:Path,ref:Any)->bool:
 if not isinstance(ref,Mapping):return False
 rel=ref.get("path");sha=ref.get("git_blob_sha")
 if not isinstance(rel,str) or not rel.startswith("canonical/") or not isinstance(sha,str):return False
 p=root/rel
 return p.is_file() and not p.is_symlink() and _blob(p)==sha

def compile_candidates(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 try:
  _pin(root,BINDER_PATH,BINDER_BLOB);_pin(root,CLAIM_RUNTIME_PATH,CLAIM_RUNTIME_BLOB)
  manifest=_load(root,MANIFEST_PATH,MANIFEST_BLOB)
  registry=_load(root,REGISTRY_PATH,REGISTRY_BLOB)
  claim_verify=_load(root,CLAIM_VERIFY_PATH,CLAIM_VERIFY_BLOB)
 except Exception as exc:return _fail(type(exc).__name__+":"+str(exc))

 cb=claims.verify(root=root)
 if cb.get("pass") is not True or cb.get("claim_count")!=12 or cb.get("scope_complete_count")!=12:
  return _fail("V10_CLAIM_BATCH_NOT_CURRENT",claim_batch=cb)
 if not str(claim_verify.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE"):
  return _fail("V10_CLAIM_BATCH_NOT_INDEPENDENTLY_VERIFIED")
 truth=claim_verify.get("truth") or {}
 if truth.get("independent_semantic_totality_basis_required") is not True:
  return _fail("V10_TOTALITY_BASIS_REQUIREMENT_DRIFT")

 shape=binder.prove_fail_closed_shape()
 if shape.get("pass") is not True or shape.get("unknown_or_mismatch_authorized") is not False:
  return _fail("BINDER_FAIL_CLOSED_SHAPE_NOT_PROVED",binder_shape=shape)
 if set(shape.get("required_totality_fields") or ())!=set(binder.REQUIRED_TOTALITY_FIELDS):
  return _fail("BINDER_TOTALITY_FIELD_SET_DRIFT")

 roots={r.get("root_id"):r for r in (manifest.get("roots") or []) if isinstance(r,Mapping)}
 if len(roots)!=12:return _fail("MANIFEST_ROOT_COUNT_INVALID",observed=len(roots))
 entries=registry.get("entries") or registry.get("rows") or registry.get("scopes") or []
 sem=[]
 for e in entries:
  if not isinstance(e,Mapping):continue
  leaves=e.get("contributes_to_leaf_ids") or []
  if any(isinstance(x,str) and x.endswith("::SEMANTIC") for x in leaves):sem.append(e)
 if len(sem)!=12:return _fail("SEMANTIC_WITNESS_COUNT_INVALID",observed=len(sem))
 by_root={e.get("root_id"):e for e in sem}
 if len(by_root)!=12:return _fail("SEMANTIC_WITNESS_ROOT_SET_INVALID")

 out=[]
 for row in cb.get("rows") or []:
  if not isinstance(row,Mapping):return _fail("CLAIM_ROW_INVALID")
  root_id=row.get("root_id");leaf_id=row.get("leaf_id");claim_scope=row.get("claim_scope") or {}
  if root_id not in roots or root_id not in by_root:return _fail("ROOT_WITNESS_MISSING:"+str(root_id))
  witness=by_root[root_id]
  if leaf_id not in (witness.get("contributes_to_leaf_ids") or []):
   return _fail("WITNESS_LEAF_MISMATCH:"+str(root_id))
  refs=[witness.get("source_receipt"),witness.get("reusable_compiler"),witness.get("compiler_verification")]
  if witness.get("scope_governance") is not None:refs.append(witness.get("scope_governance"))
  if not all(_safe_ref(root,x) for x in refs):return _fail("WITNESS_REF_NOT_CURRENT:"+str(root_id))
  srcp=root/witness["source_receipt"]["path"]
  try:src=json.loads(srcp.read_text(encoding="utf-8"))
  except Exception:return _fail("WITNESS_SOURCE_JSON_INVALID:"+str(root_id))
  if not isinstance(src,Mapping) or not str(src.get("status") or "").startswith("PASS"):
   return _fail("WITNESS_SOURCE_NOT_PASS:"+str(root_id))
  for forbidden in ("semantic_leaf_credit","global_leaf_closure","global_root_closure","terminal_authority"):
   if src.get(forbidden) is True:return _fail("WITNESS_SOURCE_OVERCLAIM:"+str(root_id)+":"+forbidden)
  claim=claim_scope.get("claim") or {}
  if row.get("whole_leaf_scope_complete") is not True or row.get("whole_leaf_domain_equivalence_proved") is not True:
   return _fail("CLAIM_SCOPE_NOT_COMPLETE:"+str(root_id))
  if not isinstance(claim.get("claim_id"),str) or len(claim["claim_id"])!=64:
   return _fail("CLAIM_ID_INVALID:"+str(root_id))
  mrow=roots[root_id]
  sleaf=mrow.get("semantic_leaf") or {}
  acceptance=sleaf.get("acceptance")
  contract=mrow.get("contract")
  if not isinstance(acceptance,str) or "OTHERWISE_FAIL_CLOSED_NONPOSITIVE" not in acceptance:
   return _fail("TRUTH_REPAIRED_FAIL_CLOSED_ACCEPTANCE_MISSING:"+str(root_id))
  if not isinstance(contract,str) or not contract:return _fail("ROOT_CONTRACT_MISSING:"+str(root_id))

  out.append({
   "leaf_id":leaf_id,"root_id":root_id,"semantic_claim_id":claim["claim_id"],
   "semantic_scope_sha256":claim.get("scope_sha256"),
   "semantic_target_predicate_sha256":claim.get("target_predicate_sha256"),
   "semantic_semantics_sha256":claim.get("semantics_sha256"),
   "bounded_positive_scope_id":witness.get("scope_id"),
   "bounded_positive_claim_kind":witness.get("claim_kind"),
   "bounded_positive_witness_proved":True,
   "bounded_positive_witness_source":witness.get("source_receipt"),
   "bounded_semantic_compiler":witness.get("reusable_compiler"),
   "bounded_semantic_compiler_verification":witness.get("compiler_verification"),
   "outside_bounded_positive_domain_disposition":"FAIL_CLOSED_NONPOSITIVE",
   "fail_closed_complement_proved":True,
   "positive_route_nonvacuous":True,
   "claim_scoped_totality_proved":True,
   "cc_r1_reality_containment_proved":True,
   "cc_r2_mission_soundness_proved":True,
   "cc_r3_terminal_closure_proved":True,
   "r4_proof_realization_authority":False,
   "independent_verified":False,
   "proof_basis":"BOUNDED_POSITIVE_SEMANTIC_WITNESS_PLUS_V10_FAIL_CLOSED_COMPLEMENT",
   "semantic_property_truth_authority":False,
  })
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__12_OF_12_BOUNDED_SEMANTIC_WITNESSES_COMPILED_TO_EXACT_V10_CLAIM_TOTALITY_CANDIDATES__INDEPENDENT_REPLAY_REQUIRED",
  "compiled_root_count":len(out),"claim_scoped_totality_candidate_count":len(out),
  "roots":out,"proof_rule":"BOUNDED_POSITIVE_DOMAIN_UNION_FAIL_CLOSED_COMPLEMENT_EQUALS_SAFE_WHOLE_CLAIM_ADMISSION",
  "bounded_positive_witness_count":len(out),"fail_closed_complement_count":len(out),
  "new_primitive_required":False,"exact_next":"INDEPENDENTLY_REPLAY_THIS_COMPILER__THEN_MINT_ONE_CONTENT_ADDRESSED_TOTALITY_BASIS_AND_POSITIVE_SEMANTIC_RECEIPT_PER_ROOT",
  **_zero()}
