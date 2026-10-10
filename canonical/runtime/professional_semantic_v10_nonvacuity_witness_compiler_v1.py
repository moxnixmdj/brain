"""Compile one authentic bounded semantic nonvacuity witness per V10 root.

This does not prove whole-leaf semantic property truth. It proves only that each
truth-repaired V10 semantic leaf has at least one real, content-addressed,
previously verified positive semantic instance available as a nonvacuity
premise. Universal fail-closed safety remains a separate theorem.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import professional_semantic_v2_v10_claim_batch_v1 as claims

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_V10_NONVACUITY_WITNESS_COMPILER_V1"
REGISTRY_PATH="canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json"
REGISTRY_BLOB="b9ddf7cbe7fbfad0e81fe068a0c19b48703b5aba"
SPECIAL={
 "R6_EVIDENCE_GROUNDING_DEPENDENCE":{
  "path":"canonical/verification/PROFESSIONAL_V10_PARAMETERIZED_SEMANTIC_ADMISSION_INDEPENDENT_VERIFY_20261011_V1.json",
  "git_blob_sha":"d32187b4f46001c352bb244853582452767355a6",
  "expected_status_prefix":"PASS__FINAL_HARDENED_V10",
  "witness_kind":"REAL_CONTENT_ADDRESSED_V10_SUBJECT_AND_CLAIM_EVIDENCE_GROUNDING"
 }
}

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(f"blob {len(d)}\0".encode()+d).hexdigest()
def _resolve(root:Path,rel:Any)->Path|None:
 if not isinstance(rel,str) or not rel.startswith("canonical/"):return None
 p=(root/rel).resolve()
 try:p.relative_to(root.resolve())
 except ValueError:return None
 return p
def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "root_count":0,"nonvacuity_witness_count":0,"semantic_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 rp=root/REGISTRY_PATH
 if not rp.is_file() or rp.is_symlink() or _blob(rp)!=REGISTRY_BLOB:return _fail("REGISTRY_PIN_FAIL")
 batch=claims.verify(root=root)
 if batch.get("pass") is not True or batch.get("claim_count")!=12:return _fail("V10_CLAIM_BATCH_NOT_CURRENT")
 try:reg=json.loads(rp.read_text())
 except Exception:return _fail("REGISTRY_JSON_INVALID")
 sem={}
 for entry in reg.get("entries") or []:
  if not isinstance(entry,Mapping):continue
  leaves=entry.get("contributes_to_leaf_ids") or []
  if any(isinstance(x,str) and x.endswith("::SEMANTIC") for x in leaves):
   rid=entry.get("root_id")
   if isinstance(rid,str):sem[rid]=entry
 expected={r["root_id"] for r in batch["rows"]}
 if set(sem)!=expected:return _fail("SEMANTIC_REGISTRY_ROOT_SET_MISMATCH",missing=sorted(expected-set(sem)),extra=sorted(set(sem)-expected))
 out=[]
 for row in batch["rows"]:
  rid=row["root_id"];leaf=row["leaf_id"];entry=sem[rid]
  if rid in SPECIAL:
   ref=SPECIAL[rid];kind=ref["witness_kind"];prefix=ref["expected_status_prefix"]
  else:
   ref=entry.get("source_receipt") or {};kind=entry.get("claim_kind");prefix="PASS__"
  p=_resolve(root,ref.get("path"))
  if p is None or not p.is_file() or p.is_symlink():return _fail("WITNESS_FILE_MISSING",root_id=rid,path=ref.get("path"))
  got=_blob(p)
  if got!=ref.get("git_blob_sha"):return _fail("WITNESS_BLOB_STALE",root_id=rid,path=ref.get("path"),observed=got)
  try:doc=json.loads(p.read_text())
  except Exception:return _fail("WITNESS_JSON_INVALID",root_id=rid)
  status=str(doc.get("status") or "")
  if not status.startswith(prefix):return _fail("WITNESS_NOT_PASS",root_id=rid,status=status)
  # Root-specific reality guards for the two nonstandard witnesses.
  if rid=="R7_CAUSAL_PRESCRIPTIVE":
   if (doc.get("conclusions") or {}).get("exact_claim_scoped_professional_edit_causality_proved") is not True:
    return _fail("R7_CAUSAL_WITNESS_NOT_PROVED")
  if rid=="R6_EVIDENCE_GROUNDING_DEPENDENCE":
   truth=doc.get("truth") or {}
   if truth.get("fixed_claim_pack_dependency_removed") is not True or truth.get("independent_semantic_totality_basis_required") is not True:
    return _fail("R6_V10_EVIDENCE_GROUNDING_WITNESS_INCOMPLETE")
  if rid=="R12_META_COMPOSITION_CLOSURE":
   if "18_OF_18" not in status:return _fail("R12_ASSURANCE_COMPOSITION_WITNESS_INCOMPLETE")
  out.append({"root_id":rid,"leaf_id":leaf,"v10_claim_id":row["claim_id"],
   "witness_kind":kind,"witness_path":ref.get("path"),"witness_git_blob_sha":got,
   "witness_status":status,"bounded_nonvacuity_only":True,"global_leaf_closure":False})
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__12_OF_12_AUTHENTIC_BOUNDED_SEMANTIC_NONVACUITY_WITNESSES_CURRENT__ZERO_PROPERTY_TRUTH",
  "root_count":12,"nonvacuity_witness_count":12,"rows":out,
  "whole_leaf_totality_proved":False,"universal_fail_closed_admission_proved":False,
  "semantic_property_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
  "exact_next":"PROVE_ONE_SHARED_V10_UNIVERSAL_FAIL_CLOSED_ADMISSION_THEOREM__THEN_COMPOSE_WITH_THESE_12_NONVACUITY_WITNESSES"}
