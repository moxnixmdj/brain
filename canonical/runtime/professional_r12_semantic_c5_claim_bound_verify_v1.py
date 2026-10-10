"""Claim-bound verifier for R12 semantic C5 coverage accounting.

Proves only that the exact frozen R12 semantic property claim explicitly accounts
for its entire admissible leaf domain with no filters/exclusions and that the
independently verified universal scope compiler closes that exact scope.

This is coverage accounting, not property truth and not defeater completeness.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_whole_leaf_domain_equivalence_v1 as domain
from canonical.runtime import professional_quality_whole_leaf_scope_batch_v1 as batch

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_SEMANTIC_C5_CLAIM_BOUND_VERIFY_V1"
CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
LEAF_ID="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"
CLAIM_PATH="canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V1.json"
CERT_PATH="canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_C5_CLAIM_BOUND_REUSE_20261010_V1.json"
PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "claim":(CLAIM_PATH,"5e7c198da31b901bb4f53c4fc15cee7d6298c114"),
 "domain_runtime":("canonical/runtime/professional_quality_whole_leaf_domain_equivalence_v1.py","76bf7e1a6f26ff3664ed8c355dff8a688b074159"),
 "domain_verify":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_EQUIVALENCE_V1_INDEPENDENT_VERIFY_20261010_V1.json","b6b826d1658d8a2c88ea80260ee667e86ae99394"),
 "scope_batch_runtime":("canonical/runtime/professional_quality_whole_leaf_scope_batch_v1.py","82ab66c7852fc327821b23ff80dd46de3b81525c"),
 "scope_batch_verify":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json","4c2d40a262f18f34bb35f94b59660d60972d45ef"),
}

def _blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "claim_id":CLAIM_ID,"leaf_id":LEAF_ID,
  "c5_coverage_accounting_proved":False,
  "cc_r3_terminal_closure":False,"semantic_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
 }

def evaluate(
 claim_doc:Mapping[str,Any],
 cert_doc:Mapping[str,Any],
 batch_out:Mapping[str,Any],
 *,repo_root:str|Path|None=None,
)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 if not all(isinstance(x,Mapping) for x in (claim_doc,cert_doc,batch_out)):
  return _fail("INPUT_NOT_MAPPING")
 if claim_doc.get("claim_id")!=CLAIM_ID or claim_doc.get("leaf_id")!=LEAF_ID:
  return _fail("FROZEN_CLAIM_IDENTITY_DRIFT")
 scope=claim_doc.get("claim_scope")
 if not isinstance(scope,Mapping):return _fail("CLAIM_SCOPE_MISSING")
 if (scope.get("claim") or {}).get("claim_id")!=CLAIM_ID:
  return _fail("INNER_CLAIM_ID_DRIFT")
 d=domain.evaluate(
  json.loads((root/"canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json").read_text()),
  scope,
 )
 if d.get("pass") is not True or d.get("whole_leaf_domain_equivalence_proved") is not True:
  return _fail("WHOLE_DOMAIN_EQUIVALENCE_NOT_PROVED",domain_verdict=d)
 sd=scope.get("scope_definition") or {}
 dd=sd.get("domain_definition") or {}
 if (
  sd.get("entire_admissible_leaf_domain") is not True
  or dd.get("quantifier")!="FOR_ALL_ADMISSIBLE_LEAF_INPUTS"
  or dd.get("filters")!=[]
  or dd.get("exclusions")!=[]
  or dd.get("scope_relation")!="EXACT_WHOLE_ADMISSIBLE_LEAF_DOMAIN"
 ):
  return _fail("WHOLE_DOMAIN_ACCOUNTING_DRIFT")

 if batch_out.get("pass") is not True:
  return _fail("SCOPE_BATCH_NOT_PASS")
 rows=batch_out.get("rows")
 if not isinstance(rows,list):return _fail("SCOPE_BATCH_ROWS_INVALID")
 matches=[r for r in rows if isinstance(r,Mapping) and r.get("leaf_id")==LEAF_ID]
 if len(matches)!=1:return _fail("R12_SCOPE_BATCH_ROW_NOT_UNIQUE")
 row=matches[0]
 if (
  row.get("claim_id")!=CLAIM_ID
  or row.get("scope_definition_sha256")!=claim_doc.get("scope_sha256")
  or row.get("whole_leaf_domain_equivalence_proved") is not True
  or row.get("whole_leaf_scope_complete") is not True
  or row.get("leaf_property_truth_authority") is not False
 ):
  return _fail("R12_SCOPE_BATCH_BINDING_INVALID",row=dict(row))

 c5=cert_doc.get("c5_coverage_accounting") or {}
 if c5.get("state")!="PROVED_BY_CLAIM_BOUND_REUSE":
  return _fail("C5_CERTIFICATE_STATE_INVALID")
 result=cert_doc.get("resulting_cut") or {}
 if "R12C5_COVERAGE_ACCOUNTING" not in set(result.get("proved_clause_ids") or []):
  return _fail("C5_RESULTING_CUT_MISSING")
 if result.get("stronger_material_defeater_totality_open") is not True:
  return _fail("STRONGER_TOTALITY_MUST_REMAIN_OPEN")
 auth=cert_doc.get("accounting") or {}
 if any(auth.get(k,0)!=0 for k in (
  "property_truth_credit_delta","capability_credit_delta","acceptance_credit_delta","terminal_credit_delta"
 )):
  return _fail("NONZERO_CREDIT_FORBIDDEN")

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R12_SEMANTIC_C5_EXACT_CLAIM_COVERAGE_ACCOUNTING__ZERO_PROPERTY_TRUTH_CREDIT",
  "claim_id":CLAIM_ID,"leaf_id":LEAF_ID,
  "scope_sha256":claim_doc.get("scope_sha256"),
  "whole_leaf_domain_equivalence_proved":True,
  "whole_leaf_scope_complete":True,
  "filters":[],"exclusions":[],
  "c5_coverage_accounting_proved":True,
  "c5_scope":"EXACT_FROZEN_R12_SEMANTIC_WHOLE_ADMISSIBLE_LEAF_DOMAIN_ONLY",
  "cc_r3_terminal_closure":False,"semantic_property_truth_authority":False,
  "material_defeater_totality_proved":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 for key,(rel,expected) in PINS.items():
  p=root/rel
  if not p.is_file() or p.is_symlink():return _fail(key.upper()+"_MISSING")
  actual=_blob(p)
  if actual!=expected:return _fail(key.upper()+"_BLOB_STALE",observed=actual,expected=expected)
 try:
  claim=json.loads((root/CLAIM_PATH).read_text())
  cert=json.loads((root/CERT_PATH).read_text())
 except Exception as exc:return _fail("BOUND_JSON_INVALID",detail=type(exc).__name__+":"+str(exc))
 out=batch.verify(repo_root=root)
 return evaluate(claim,cert,out,repo_root=root)

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
