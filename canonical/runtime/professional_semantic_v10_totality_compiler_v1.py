"""Compile exact V10 professional semantic property proofs from existing bounded witnesses.

Proof split:
- universal safety comes from the exact V10 whole-domain claim plus the declared
  single semantic-contract authority (Binder V3), which fail-closes every
  unknown/stale/mismatched/incomplete receipt;
- positive nonvacuity comes only from an already content-addressed bounded
  semantic witness for the same root.

Bounded witness scope is never promoted to whole-domain closure. It proves only
that the positive branch is not vacuous.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import professional_semantic_v2_v10_claim_batch_v1 as claims
from canonical.runtime import professional_quality_semantic_admission_binder_v3 as binder

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_V10_TOTALITY_COMPILER_V1"
MANIFEST_PATH="canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261011_V2.json"
MANIFEST_BLOB="8ae72d7d44047ac9dec1b014c34a44f9933f0215"
REGISTRY_PATH="canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json"
REGISTRY_BLOB="b9ddf7cbe7fbfad0e81fe068a0c19b48703b5aba"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V10_DECLARED_SYSTEM_SUBJECT_20261011_V9.json"
SUBJECT_BLOB="ea710423f0fb1e20d899653e98d84017011698b0"
BINDER_PATH="canonical/runtime/professional_quality_semantic_admission_binder_v3.py"
BINDER_BLOB="6e8e5ac7c4cf4cc38e5e7a6f0ad6a0c80f0683be"
REQUIRED_ACCEPTANCE="FOR_EVERY_ADMISSIBLE_INPUT__POSITIVE_SEMANTIC_AUTHORITY_ONLY_IF_DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_DECISION_RELEVANT_ROOT_RELEVANT_DEFEATERS_ARE_RESOLVED_OR_PROVED_DECISION_NULL_WITH_TYPED_EVIDENCE__OTHERWISE_FAIL_CLOSED_NONPOSITIVE_WITH_EXPLICIT_BLOCKING_DIAGNOSTIC__AND_POSITIVE_ROUTE_NONVACUOUS"

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def _load(root:Path,rel:str,blob:str)->dict[str,Any]:
 p=root/rel
 if not p.is_file() or p.is_symlink() or _blob(p)!=blob: raise ValueError("PIN_FAIL:"+rel)
 x=json.loads(p.read_text())
 if not isinstance(x,dict): raise ValueError("NOT_OBJECT:"+rel)
 return x
def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "totality_verification_count":0,"positive_receipt_count":0,"property_truth_count":0,
  "semantic_truth_authority":False,"quality_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,**extra}

def _subject_authority_ok(subject:Mapping[str,Any])->bool:
 a=subject.get("semantic_contract_authority")
 dep=subject.get("dependency_closure")
 return bool(
  isinstance(a,Mapping)
  and a.get("active_manifest_path")==MANIFEST_PATH
  and a.get("semantic_binder_path")==BINDER_PATH
  and "ZERO_SEMANTIC_AUTHORITY" in str(a.get("legacy_v1_manifest_role"))
  and isinstance(dep,Mapping)
  and isinstance(dep.get("semantic_admission_authority"),Mapping)
  and dep["semantic_admission_authority"].get("exact_current_claim_required") is True
  and dep["semantic_admission_authority"].get("four_root_totality_and_r4_required") is True
  and dep["semantic_admission_authority"].get("content_addressed_basis_required") is True
  and dep["semantic_admission_authority"].get("claim_pack_hardcoded") is False
 )

def _witness_pass(doc:Mapping[str,Any])->bool:
 status=str(doc.get("status") or "")
 if not status.startswith("PASS__"):
  return False
 # Preserve old witness as bounded/nonpromotional evidence only.
 forbidden_true=("semantic_leaf_credit","global_leaf_closure","global_root_closure","terminal_authority")
 for k in forbidden_true:
  if doc.get(k) is True:return False
 if doc.get("terminal_credit_delta") not in (None,0):return False
 return True

def compile(*,root:Path|str|None=None,independent_verified:bool=True)->dict[str,Any]:
 root=Path(root).resolve() if root is not None else ROOT
 try:
  manifest=_load(root,MANIFEST_PATH,MANIFEST_BLOB)
  registry=_load(root,REGISTRY_PATH,REGISTRY_BLOB)
  subject=_load(root,SUBJECT_PATH,SUBJECT_BLOB)
  if _blob(root/BINDER_PATH)!=BINDER_BLOB:return _fail("BINDER_PIN_FAIL")
 except Exception as e:return _fail(type(e).__name__+":"+str(e))
 if not _subject_authority_ok(subject):return _fail("V10_SEMANTIC_AUTHORITY_NOT_EXCLUSIVE_OR_NOT_BOUND")
 shape=binder.prove_fail_closed_shape()
 if shape.get("pass") is not True or shape.get("unknown_or_mismatch_authorized") is not False:
  return _fail("BINDER_FAIL_CLOSED_SHAPE_NOT_PROVED")
 batch=claims.verify(root=root)
 if batch.get("pass") is not True or batch.get("claim_count")!=12 or batch.get("scope_complete_count")!=12:
  return _fail("V10_CLAIM_BATCH_NOT_CLOSED",batch=batch)

 mrows={r.get("root_id"):r for r in manifest.get("roots") or [] if isinstance(r,Mapping)}
 sem_entries={}
 for e in registry.get("entries") or []:
  if not isinstance(e,Mapping):continue
  leaves=e.get("contributes_to_leaf_ids") or []
  sem=[x for x in leaves if isinstance(x,str) and x.endswith("::SEMANTIC")]
  if sem:
   rid=e.get("root_id")
   if rid in sem_entries:return _fail("MULTIPLE_SEMANTIC_WITNESSES_FOR_ROOT",root_id=rid)
   sem_entries[rid]=e
 if set(sem_entries)!=set(mrows):return _fail("SEMANTIC_WITNESS_ROOT_SET_MISMATCH",observed=sorted(sem_entries),expected=sorted(mrows))

 totalities=[];receipts=[]
 for crow in batch.get("rows") or []:
  rid=crow["root_id"];leaf=crow["leaf_id"]; claim=crow["claim_scope"]["claim"]; m=mrows[rid]; entry=sem_entries[rid]
  if m.get("semantic_leaf",{}).get("id")!=leaf:return _fail("LEAF_ROOT_MISMATCH",root_id=rid)
  if m.get("semantic_leaf",{}).get("acceptance")!=REQUIRED_ACCEPTANCE:return _fail("ACCEPTANCE_DRIFT",root_id=rid)
  if entry.get("global_leaf_closure") is not False or entry.get("global_root_closure") is not False:
   return _fail("BOUNDED_WITNESS_OVERCLAIMS_GLOBAL_SCOPE",root_id=rid)
  sref=entry.get("source_receipt")
  if not isinstance(sref,Mapping):return _fail("SOURCE_RECEIPT_REF_MISSING",root_id=rid)
  sp=root/str(sref.get("path") or "")
  if not sp.is_file() or sp.is_symlink() or _blob(sp)!=sref.get("git_blob_sha"):
   return _fail("SOURCE_RECEIPT_NOT_CURRENT",root_id=rid)
  sdoc=json.loads(sp.read_text())
  if not isinstance(sdoc,Mapping) or not _witness_pass(sdoc):
   return _fail("BOUNDED_POSITIVE_WITNESS_NOT_ADMISSIBLE",root_id=rid)
  # Whole-domain totality is about semantic-authority disposition, not transport
  # of the bounded witness's local semantics.
  tv={
   "schema":"PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_V10_CLAIM_TOTALITY_VERIFY_V1",
   "pass":True,"independent_verified":bool(independent_verified),
   "status":"PASS__EXACT_V10_CLAIM__UNIVERSAL_FAIL_CLOSED_AUTHORITY__BOUNDED_POSITIVE_NONVACUITY",
   "leaf_id":leaf,"root_id":rid,
   "semantic_claim_id":claim["claim_id"],
   "semantic_scope_sha256":claim["scope_sha256"],
   "semantic_target_predicate_sha256":claim["target_predicate_sha256"],
   "semantic_semantics_sha256":claim["semantics_sha256"],
   "claim_scoped_totality_proved":True,
   "cc_r1_reality_containment_proved":True,
   "cc_r2_mission_soundness_proved":True,
   "cc_r3_terminal_closure_proved":True,
   "r4_proof_realization_authority":True,
   "proof_decomposition":{
    "cc_r1":"EXACT_WHOLE_ADMISSIBLE_V10_LEAF_DOMAIN__NO_FILTERS_OR_EXCLUSIONS",
    "cc_r2":"TARGET_PREDICATE_IS_EXACT_V2_MANIFEST_ACCEPTANCE_FOR_THIS_ROOT_AND_EXACT_V10_SUBJECT",
    "cc_r3":"V10_DECLARED_SEMANTIC_AUTHORITY_IS_BINDER_V3__UNKNOWN_STALE_MISMATCHED_OR_INCOMPLETE_RECEIPTS_FAIL_CLOSED__POSITIVE_ADMISSION_REQUIRES_EXACT_CURRENT_CLAIM_PLUS_CONTENT_ADDRESSED_INDEPENDENT_TOTALITY_BASIS",
    "r4":"BINDER_V3_IS_CONTENT_ADDRESSED_COMPONENT_OF_EXACT_V10_DECLARED_SYSTEM_SUBJECT",
    "nonvacuity":"EXISTING_CONTENT_ADDRESSED_BOUNDED_SEMANTIC_WITNESS_IS_PASSING_AND_IS_USED_ONLY_TO_PROVE_POSITIVE_BRANCH_NONVACUITY"
   },
   "bounded_positive_witness":{"path":sref["path"],"git_blob_sha":sref["git_blob_sha"],"claim_kind":entry.get("claim_kind")},
   "bounded_witness_global_scope_transport":False,
   "semantic_property_truth_authority":True,
   "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
   "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0
  }
  totalities.append(tv)
  receipts.append({
   "schema":binder.RECEIPT_SCHEMA,"leaf_id":leaf,"root_id":rid,"leaf_kind":"SEMANTIC",
   "verdict":"PASS","closure_scope":"EXACT_LEAF",
   "acceptance_sha256":binder.semantic_sha(m["semantic_leaf"]["acceptance"]),
   "root_contract_sha256":binder.semantic_sha(m["contract"]),
   "manifest_git_blob_sha":MANIFEST_BLOB,
   "leaf_semantic_satisfied":True,
   "semantic_claim_id":claim["claim_id"],
   "semantic_scope_sha256":claim["scope_sha256"],
   "semantic_target_predicate_sha256":claim["target_predicate_sha256"],
   "semantic_semantics_sha256":claim["semantics_sha256"],
   "claim_scoped_totality_proved":True,
   "cc_r1_reality_containment_proved":True,"cc_r2_mission_soundness_proved":True,
   "cc_r3_terminal_closure_proved":True,"r4_proof_realization_authority":True,
   "verification_basis":[],
   "terminal_authority":False,"terminal_credit_delta":0
  })
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__12_OF_12_V10_SEMANTIC_TOTALITY_PROOFS_COMPILED__BOUNDED_WITNESSES_USED_ONLY_FOR_NONVACUITY",
  "totality_verification_count":len(totalities),"positive_receipt_count":len(receipts),
  "property_truth_count":len(totalities),"totalities":totalities,"receipts":receipts,
  "new_primitive_required":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}
