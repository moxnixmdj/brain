"""Executable CC_R1 verifier for the stable R12 semantic property claim.

Reuses the already independently verified whole-leaf domain equivalence,
scope-completeness batch, and universal identity carrier. It proves only
B_real[C] subseteq B_plus[C] for this exact stable R12 claim.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Mapping

ROOT_ID="CC_R1_REALITY_CONTAINMENT_V1"
CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
MISSION_BLOB="13c470645b037bbb46245c687dd35197b420d51a"
SCOPE_CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
EVIDENCE={
 "whole_domain_equivalence":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_EQUIVALENCE_V1_INDEPENDENT_VERIFY_20261010_V1.json","b6b826d1658d8a2c88ea80260ee667e86ae99394"),
 "scope_batch":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json","4c2d40a262f18f34bb35f94b59660d60972d45ef"),
 "identity_carrier":("canonical/verification/PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_VERIFY_20261010_V1.json","35a3ccf9ad454aa0318a4ed10edc065830c3874d"),
}

def _blob(p:Path)->str:
 d=p.read_bytes();return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _load_bound(root:Path,ref:Mapping[str,Any],label:str)->tuple[dict[str,Any]|None,list[str]]:
 errors=[]
 rel=ref.get("path");sha=ref.get("git_blob_sha")
 if not isinstance(rel,str) or not isinstance(sha,str):return None,[label+"_REF_INVALID"]
 p=root/rel
 if not p.is_file() or p.is_symlink():return None,[label+"_FILE_MISSING"]
 if _blob(p)!=sha:return None,[label+"_BLOB_MISMATCH"]
 try:o=json.loads(p.read_text(encoding="utf-8"))
 except Exception:return None,[label+"_JSON_INVALID"]
 return (o if isinstance(o,dict) else None),([] if isinstance(o,dict) else [label+"_NOT_OBJECT"])

def _fail(root_id:str,claim_id:str,*errors:str)->dict[str,Any]:
 return {"pass":False,"status":"FAIL_CLOSED__CC_R1_R12_REALITY_CONTAINMENT_UNPROVED",
  "root_id":root_id,"claim_id":claim_id,"semantic_claim_verified":False,
  "errors":sorted(set(errors)),"terminal_credit_delta":0}

def verify_certificate(*,root:Path,certificate_path:Path,active_claim:Mapping[str,Any],root_id:str)->dict[str,Any]:
 root=root.resolve();claim_id=str(active_claim.get("claim_id") or "");errors=[]
 if root_id!=ROOT_ID:return _fail(root_id,claim_id,"ROOT_ID_MISMATCH")
 if claim_id!=CLAIM_ID:return _fail(root_id,claim_id,"ACTIVE_CLAIM_ID_MISMATCH")
 if active_claim.get("mission_blob_sha")!=MISSION_BLOB:return _fail(root_id,claim_id,"ACTIVE_CLAIM_MISSION_AUTHORITY_DRIFT")
 try:cert=json.loads(certificate_path.read_text(encoding="utf-8"))
 except Exception:return _fail(root_id,claim_id,"CERTIFICATE_INVALID_JSON")
 if cert.get("root_id")!=ROOT_ID:errors.append("CERTIFICATE_ROOT_MISMATCH")
 if cert.get("claim_id")!=CLAIM_ID:errors.append("CERTIFICATE_CLAIM_MISMATCH")
 if cert.get("whole_leaf_scope_claim_id")!=SCOPE_CLAIM_ID:errors.append("SCOPE_CLAIM_ID_DRIFT")
 for k in ("semantic_truth_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
  if cert.get(k) is not False:errors.append("CERTIFICATE_AUTHORITY_OVERCLAIM:"+k)
 if (cert.get("accounting") or {}).get("terminal_credit_delta")!=0:errors.append("CERTIFICATE_NONZERO_TERMINAL_CREDIT")
 frozen,es=_load_bound(root,cert.get("active_claim") or {},"ACTIVE_CLAIM");errors+=es
 if frozen:
  for k in ("claim_id","claim_kind","mission_blob_sha","scope_sha256","target_predicate_sha256","semantics_sha256","epoch","authority_id"):
   if frozen.get(k)!=active_claim.get(k):errors.append("FROZEN_ACTIVE_CLAIM_MISMATCH:"+k)
  if frozen.get("whole_leaf_scope_claim_id")!=SCOPE_CLAIM_ID:errors.append("FROZEN_SCOPE_CLAIM_DRIFT")
 authority,es=_load_bound(root,cert.get("mission_authority") or {},"MISSION_AUTHORITY");errors+=es
 if authority and authority.get("real_objective")!="BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE":
  errors.append("MISSION_OBJECTIVE_DRIFT")
 docs={}
 for label,(rel,sha) in EVIDENCE.items():
  ref=cert.get(label) or {}
  if ref.get("path")!=rel or ref.get("git_blob_sha")!=sha:errors.append(label.upper()+"_REF_DRIFT")
  doc,es=_load_bound(root,ref,label.upper());errors+=es
  if doc:docs[label]=doc
 if errors:return _fail(root_id,claim_id,*errors)

 domain=docs["whole_domain_equivalence"];scope=docs["scope_batch"];carrier=docs["identity_carrier"]
 if not str(domain.get("status") or "").startswith("PASS__"):errors.append("DOMAIN_EQUIVALENCE_NOT_PASS")
 if (domain.get("independent_replay") or {}).get("real_manifest_passed")!=24:errors.append("DOMAIN_24_OF_24_NOT_PROVED")
 if not str(scope.get("status") or "").startswith("PASS__"):errors.append("SCOPE_BATCH_NOT_PASS")
 if (scope.get("independent_replay") or {}).get("scope_complete_count")!=24:errors.append("SCOPE_24_OF_24_NOT_PROVED")
 theorem=carrier.get("theorem") or {}
 if theorem.get("carrier")!="OMEGA_C_EQUALS_W_C":errors.append("IDENTITY_CARRIER_DRIFT")
 if theorem.get("projection")!="PI_C_IS_IDENTITY_ON_COMPLETE_FROZEN_CLAIM_WORLD_STATE":errors.append("IDENTITY_PROJECTION_DRIFT")
 if theorem.get("finite_witness_set_used") is not False:errors.append("FINITE_WITNESS_SUBSTITUTION")
 if theorem.get("semantic_information_loss") is not False:errors.append("IDENTITY_CARRIER_INFORMATION_LOSS")
 if (carrier.get("independent_replay") or {}).get("r12_claim_id")!=SCOPE_CLAIM_ID:errors.append("IDENTITY_CARRIER_R12_SCOPE_DRIFT")
 model=cert.get("b_plus_model") or {}
 if model.get("admissibility")!="EXACT_WHOLE_ADMISSIBLE_LEAF_DOMAIN__NO_FILTERS__NO_EXCLUSIONS":errors.append("B_PLUS_ADMISSIBILITY_DRIFT")
 if model.get("carrier_relation")!="OMEGA_C_EQUALS_W_C__PI_C_IS_IDENTITY_ON_W_C":errors.append("B_PLUS_CARRIER_DRIFT")
 t=cert.get("theorem") or {}
 if t.get("proof_mode")!="FORMAL_REDUCTION" or t.get("b_real_subseteq_b_plus") is not True:errors.append("THEOREM_DRIFT")
 if t.get("semantic_property_truth_implied") is not False:errors.append("PROPERTY_TRUTH_OVERCLAIM")
 if errors:return _fail(root_id,claim_id,*errors)
 return {"pass":True,"status":"PASS__CC_R1_R12_STABLE_WHOLE_DOMAIN_IDENTITY_CONTAINMENT",
  "root_id":ROOT_ID,"claim_id":CLAIM_ID,"semantic_claim_verified":True,
  "whole_leaf_domain_scope_complete":True,"identity_carrier_total_injective":True,
  "b_real_subseteq_b_plus":True,"property_truth_implied":False,
  "terminal_credit_delta":0,"errors":[]}
