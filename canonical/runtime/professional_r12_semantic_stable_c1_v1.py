"""Re-instantiate R12 C1 assumption-guarantee composition on the stable V3 semantic claim.

No authority is transported from the superseded V2 claim. The theorem is
recomputed from the current stable V3 claim semantics plus the exact independent
12/12 same-subject composition replay.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_semantic_totality_claim_pack_v3 as pack_v3

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_STABLE_C1_VERIFY_V1"
LEAF_ID="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"
CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
OLD_V2_CLAIM_ID="97ff74650749db87f378d5926ed820e004f3f792583c2c8455e51c3ccacbe7f7"
SUBJECT_KIND="DECLARED_SYSTEM"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA256="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
EXPECTED_ACCEPTANCE="DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_ROOT_RELEVANT_DEFEATERS_RESOLVED_WITH_TYPED_EVIDENCE"
FRESH_V3_RECEIPT=("canonical/verification/PROFESSIONAL_SEMANTIC_V3_CURRENT_BYTES_INDEPENDENT_VERIFY_20261010_V1.json","42ae47b7d38743a827da8616751d4290dd310b55")
COMPOSITION_RECEIPT=("canonical/verification/PROFESSIONAL_QUALITY_V7_12_OF_12_COMPOSITION_INDEPENDENT_VERIFY_20261010_V1.json","4ee02c41acf64b1f47ebadec55b6bb5453d676ba")
DECOMPOSITION=("canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_CONTRACT_DECOMPOSITION_20261010_V1.json","d83ded1689ec636a2cda60f7c7419dd69a61cbd5")

def _blob(p:Path)->str:
 raw=p.read_bytes(); return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def _load(p:Path)->dict[str,Any]:
 d=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(d,dict): raise ValueError("NOT_OBJECT")
 return d
def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
 "c1_assumption_guarantee_composition_proved":False,
 "cc_r3_terminal_closure_proved":False,"r4_proof_closure":False,
 "semantic_property_truth_authority":False,"quality_authority":False,
 "acceptance_authority":False,"promotion_authority":False,
 "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def evaluate(
 r12:Mapping[str,Any],
 current_v3_receipt:Mapping[str,Any],
 composition:Mapping[str,Any],
 decomposition:Mapping[str,Any],
)->dict[str,Any]:
 if not all(isinstance(x,Mapping) for x in (r12,current_v3_receipt,composition,decomposition)):
  return _fail("INPUT_NOT_MAPPING")
 if r12.get("leaf_id")!=LEAF_ID:return _fail("R12_LEAF_DRIFT")
 claim=r12.get("frozen_claim")
 if not isinstance(claim,Mapping):return _fail("R12_CLAIM_MISSING")
 if claim.get("claim_id")!=CLAIM_ID:return _fail("STABLE_CLAIM_ID_DRIFT",observed=claim.get("claim_id"))
 if claim.get("claim_id")==OLD_V2_CLAIM_ID:return _fail("OLD_V2_CLAIM_FORBIDDEN")
 if claim.get("mission_blob_sha")!=pack_v3.EXPECTED_MISSION_AUTHORITY_BLOB:return _fail("MISSION_AUTHORITY_DRIFT")
 if r12.get("scope_definition_sha256")!=claim.get("scope_sha256"):return _fail("SCOPE_BINDING_DRIFT")
 target=r12.get("target_predicate") or {}
 sem=r12.get("semantics") or {}
 if target.get("acceptance")!=EXPECTED_ACCEPTANCE:return _fail("ACCEPTANCE_DRIFT")
 if sem.get("true_when")!=EXPECTED_ACCEPTANCE:return _fail("SEMANTICS_TRUE_WHEN_DRIFT")
 if sem.get("bounded_witnesses_are_totality_authority") is not False:return _fail("BOUNDED_WITNESS_OVERCLAIM")
 if r12.get("source_v2_claim_authority_transported") is not False:return _fail("V2_AUTHORITY_TRANSPORT_FORBIDDEN")

 if not str(current_v3_receipt.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE__CURRENT_V3_BYTES"):
  return _fail("CURRENT_V3_RECEIPT_NOT_PASS")
 obs=current_v3_receipt.get("observed") or {}
 if obs.get("r12_stable_claim_id")!=CLAIM_ID:return _fail("CURRENT_V3_RECEIPT_CLAIM_DRIFT")
 if obs.get("v3_identity_carrier_factorization_count")!=12:return _fail("CURRENT_V3_CARRIER_COUNT_INVALID")
 for field in ("semantic_property_truth_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
  if obs.get(field) is not False:return _fail("CURRENT_V3_RECEIPT_AUTHORITY_OVERCLAIM:"+field)

 if composition.get("status")!="PASS__INDEPENDENT_SPRITE_EXACT_V4_12_OF_12_SAME_SUBJECT_COMPOSITION__V4_SCHEMA_SEAM_5_OF_5__THREE_ADVERSARIAL_PROBES__ZERO_QUALITY_OR_TERMINAL_CREDIT":
  return _fail("COMPOSITION_RECEIPT_NOT_EXACT_PASS")
 if composition.get("verified_root_subject_binding_count")!=12 or composition.get("composition_admissible") is not True:
  return _fail("COMPOSITION_NOT_12_OF_12")
 subj=composition.get("composed_subject") or {}
 if (subj.get("subject_kind"),subj.get("subject_id"),subj.get("subject_sha256"))!=(SUBJECT_KIND,SUBJECT_ID,SUBJECT_SHA256):
  return _fail("COMPOSED_SUBJECT_DRIFT")
 if composition.get("professional_quality_closed") is not False or composition.get("quality_authority") is not False or composition.get("terminal_authority") is not False:
  return _fail("COMPOSITION_AUTHORITY_OVERCLAIM")

 rows=decomposition.get("clauses") or decomposition.get("contract_clauses") or decomposition.get("rows") or []
 c1=next((x for x in rows if isinstance(x,Mapping) and x.get("id")=="R12C1_ASSUMPTION_GUARANTEE_COMPOSITION"),None)
 if not isinstance(c1,Mapping) or c1.get("fragment")!="assumption-guarantee composition":
  return _fail("C1_DECOMPOSITION_DRIFT")

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__STABLE_V3_R12_C1_ASSUMPTION_GUARANTEE_COMPOSITION_REINSTANTIATED__ZERO_PROPERTY_OR_TERMINAL_CREDIT",
  "leaf_id":LEAF_ID,"claim_id":CLAIM_ID,
  "subject_kind":SUBJECT_KIND,"subject_id":SUBJECT_ID,"subject_sha256":SUBJECT_SHA256,
  "proof_mode":"FORMAL_REDUCTION__EXACT_CLAUSE_TO_CURRENT_12_OF_12_SAME_SUBJECT_COMPOSITION_GATE",
  "assumption_set":"EXACT_CURRENT_V4_GATE_PREMISES_BOUND_BY_INDEPENDENT_12_OF_12_REPLAY",
  "guarantee":"PASS__SAME_SUBJECT_ROOT_COMPOSITION_ADMISSIBLE_WITHOUT_AUTHORITY_WIDENING",
  "c1_assumption_guarantee_composition_proved":True,
  "old_v2_claim_authority_transported":False,
  "cc_r3_terminal_closure_proved":False,"r4_proof_closure":False,
  "semantic_property_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 try:
  pack=pack_v3.verify(repo_root=root)
  if pack.get("pass") is not True:return _fail("V3_PACK_NOT_PASS",source_reason=pack.get("reason"))
  r12=next((x for x in (pack.get("claims") or []) if isinstance(x,Mapping) and x.get("leaf_id")==LEAF_ID),None)
  if not isinstance(r12,Mapping):return _fail("R12_STABLE_CLAIM_MISSING")
  docs=[]
  for rel,expected in (FRESH_V3_RECEIPT,COMPOSITION_RECEIPT,DECOMPOSITION):
   p=root/rel
   if not p.is_file() or p.is_symlink():return _fail("BOUND_FILE_MISSING",path=rel)
   actual=_blob(p)
   if actual!=expected:return _fail("BOUND_FILE_BLOB_DRIFT",path=rel,expected=expected,observed=actual)
   docs.append(_load(p))
  return evaluate(r12,docs[0],docs[1],docs[2])
 except Exception as exc:
  return _fail("VERIFY_EXCEPTION",detail=type(exc).__name__+":"+str(exc))

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
