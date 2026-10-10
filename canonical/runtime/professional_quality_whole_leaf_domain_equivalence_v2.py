"""Whole-leaf domain-equivalence verifier bound to the exact V9 subject.

This is a subject-binding successor of professional_quality_whole_leaf_domain_equivalence_v1.
It changes only the declared-system identity from V7 to V9. No property, quality,
acceptance, promotion, or terminal authority is transported.
"""
from __future__ import annotations
from hashlib import sha256
import json
from typing import Any,Mapping
from canonical.runtime.coverage_claim_scope_guard_v1 import compute_claim_id

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_EQUIVALENCE_V2"
CLAIM_SCOPE_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_CLAIM_SCOPE_V1"
DOMAIN_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_V1"
BEHAVIOR_ID="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
SUBJECT_KIND="DECLARED_SYSTEM"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V9_EXECUTABLE_TOTALITY_SEMANTICS_SYSTEM_20261010_V8"
SUBJECT_SHA256="adf7f09e1913526e460b7350c02cd148c2cd14de90eed33fa7fae84d395d9912"
MISSION_BLOB="13c470645b037bbb46245c687dd35197b420d51a"
AUTHORITY_ID="PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF"

def _canon_sha(v:Any)->str:
 return sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def _text_sha(v:Any)->str:
 return sha256((v if isinstance(v,str) else "").encode()).hexdigest()
def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "whole_leaf_domain_equivalence_proved":False,"leaf_property_truth_authority":False,
  "semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra}
def leaf_meta(manifest:Mapping[str,Any],leaf_id:str):
 for row in manifest.get("roots") or []:
  if not isinstance(row,Mapping):continue
  for kind,field in (("SEMANTIC","semantic_leaf"),("EXECUTION","execution_leaf")):
   leaf=row.get(field)
   if isinstance(leaf,Mapping) and leaf.get("id")==leaf_id:
    return {"leaf_id":leaf_id,"root_id":row.get("root_id"),"kind":kind,
     "contract":row.get("contract"),"obligation":leaf.get("obligation"),
     "acceptance":leaf.get("acceptance")}
 return None
def canonical_scope_definition(meta:Mapping[str,Any])->dict[str,Any]:
 return {"domain_schema_id":DOMAIN_SCHEMA,"entire_admissible_leaf_domain":True,
  "domain_definition":{"quantifier":"FOR_ALL_ADMISSIBLE_LEAF_INPUTS",
   "admissibility_basis":"FROZEN_BEHAVIOR_SUBJECT_ROOT_CONTRACT_LEAF_OBLIGATION_AND_ACCEPTANCE",
   "behavior_id":BEHAVIOR_ID,"subject_kind":SUBJECT_KIND,"subject_id":SUBJECT_ID,
   "subject_sha256":SUBJECT_SHA256,"root_id":meta["root_id"],"leaf_id":meta["leaf_id"],
   "kind":meta["kind"],"root_contract":meta["contract"],"leaf_obligation":meta["obligation"],
   "leaf_acceptance":meta["acceptance"],"filters":[],"exclusions":[],
   "scope_relation":"EXACT_WHOLE_ADMISSIBLE_LEAF_DOMAIN"}}
def expected_claim(meta:Mapping[str,Any],scope_definition:Mapping[str,Any],epoch:str)->dict[str,Any]:
 material={"leaf_id":meta["leaf_id"],"root_id":meta["root_id"],"kind":meta["kind"],
  "behavior_id":BEHAVIOR_ID,"subject_kind":SUBJECT_KIND,"subject_id":SUBJECT_ID,
  "subject_sha256":SUBJECT_SHA256,"leaf_contract":meta["contract"],
  "leaf_obligation":meta["obligation"],"leaf_acceptance":meta["acceptance"],
  "scope_definition":scope_definition}
 claim={"claim_kind":"PROPERTY_CERTIFICATE","mission_blob_sha":MISSION_BLOB,
  "scope_sha256":_canon_sha(scope_definition),"target_predicate_sha256":_text_sha(meta["acceptance"]),
  "semantics_sha256":_canon_sha(material),"epoch":epoch,"authority_id":AUTHORITY_ID,
  "terminal_credit_delta":0}
 claim["claim_id"]=compute_claim_id(claim);return claim
def build_claim_scope(manifest:Mapping[str,Any],leaf_id:str,*,epoch:str)->dict[str,Any]:
 meta=leaf_meta(manifest,leaf_id)
 if meta is None:raise KeyError("LEAF_NOT_IN_MANIFEST")
 scope=canonical_scope_definition(meta)
 return {"schema":CLAIM_SCOPE_SCHEMA,"leaf_id":leaf_id,"root_id":meta["root_id"],
  "kind":meta["kind"],"behavior_id":BEHAVIOR_ID,"subject_kind":SUBJECT_KIND,
  "subject_id":SUBJECT_ID,"subject_sha256":SUBJECT_SHA256,"leaf_acceptance":meta["acceptance"],
  "scope_definition":scope,"epoch":epoch,"claim":expected_claim(meta,scope,epoch)}
def evaluate(manifest:Mapping[str,Any],claim_scope:Mapping[str,Any])->dict[str,Any]:
 if not isinstance(manifest,Mapping) or not isinstance(claim_scope,Mapping):return _fail("INPUT_NOT_MAPPING")
 if claim_scope.get("schema")!=CLAIM_SCOPE_SCHEMA:return _fail("CLAIM_SCOPE_SCHEMA_INVALID")
 leaf_id=claim_scope.get("leaf_id")
 if not isinstance(leaf_id,str) or not leaf_id:return _fail("LEAF_ID_REQUIRED")
 meta=leaf_meta(manifest,leaf_id)
 if meta is None:return _fail("LEAF_NOT_IN_MANIFEST")
 fixed={"root_id":meta["root_id"],"kind":meta["kind"],"behavior_id":BEHAVIOR_ID,
  "subject_kind":SUBJECT_KIND,"subject_id":SUBJECT_ID,"subject_sha256":SUBJECT_SHA256,
  "leaf_acceptance":meta["acceptance"]}
 for k,e in fixed.items():
  if claim_scope.get(k)!=e:return _fail("CLAIM_SCOPE_BINDING_DRIFT:"+k)
 scope=claim_scope.get("scope_definition")
 exp=canonical_scope_definition(meta)
 if not isinstance(scope,Mapping) or dict(scope)!=exp:return _fail("WHOLE_LEAF_DOMAIN_NOT_EXACT")
 epoch=claim_scope.get("epoch")
 if not isinstance(epoch,str) or not epoch:return _fail("EPOCH_REQUIRED")
 claim=expected_claim(meta,exp,epoch)
 if claim_scope.get("claim")!=claim:return _fail("CLAIM_CONTENT_ADDRESS_MISMATCH")
 return {"schema":SCHEMA,"pass":True,"status":"PASS__EXACT_V9_WHOLE_LEAF_DOMAIN_EQUIVALENCE",
  "leaf_id":leaf_id,"root_id":meta["root_id"],"kind":meta["kind"],"claim_id":claim["claim_id"],
  "scope_definition_sha256":_canon_sha(exp),"leaf_acceptance_sha256":_text_sha(meta["acceptance"]),
  "whole_leaf_domain_equivalence_proved":True,
  "proof_basis":"EXACT_V2_MANIFEST_BINDING_PLUS_V9_SUBJECT_IDENTITY_PLUS_UNIVERSAL_NO_FILTER_SCOPE",
  "leaf_property_truth_authority":False,"semantic_truth_authority":False,
  "execution_authority":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0,
  "incremental_spend_usd":0}
