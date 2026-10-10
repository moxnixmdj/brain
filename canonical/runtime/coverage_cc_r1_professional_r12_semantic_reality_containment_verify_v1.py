"""CC_R1 verifier for the exact frozen R12 professional semantic claim."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
ROOT_ID="CC_R1_REALITY_CONTAINMENT_V1"
CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
CERT="canonical/governance/COVERAGE_CC_R1_PROFESSIONAL_R12_SEMANTIC_REALITY_CONTAINMENT_CERTIFICATE_20261010_V1.json"
PINS={
 "claim":("canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V1.json","5e7c198da31b901bb4f53c4fc15cee7d6298c114"),
 "domain":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_EQUIVALENCE_V1_INDEPENDENT_VERIFY_20261010_V1.json","b6b826d1658d8a2c88ea80260ee667e86ae99394"),
 "scope":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json","4c2d40a262f18f34bb35f94b59660d60972d45ef"),
 "identity":("canonical/verification/PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_VERIFY_20261010_V1.json","35a3ccf9ad454aa0318a4ed10edc065830c3874d"),
}
def _blob(p:Path)->str:
 b=p.read_bytes(); return sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def _fail(*errs:str)->dict[str,Any]:
 return {"pass":False,"status":"FAIL_CLOSED__CC_R1_R12_SEMANTIC_REALITY_CONTAINMENT_UNPROVED","root_id":ROOT_ID,"claim_id":CLAIM_ID,"errors":sorted(set(errs)),"semantic_claim_verified":False,"terminal_credit_delta":0}
def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 docs={}
 for key,(rel,expected) in PINS.items():
  p=root/rel
  if not p.is_file() or p.is_symlink(): return _fail(key.upper()+"_MISSING")
  if _blob(p)!=expected:return _fail(key.upper()+"_BLOB_MISMATCH")
  try: docs[key]=json.loads(p.read_text())
  except Exception:return _fail(key.upper()+"_JSON_INVALID")
 cp=root/CERT
 if not cp.is_file():return _fail("CERTIFICATE_MISSING")
 try: cert=json.loads(cp.read_text())
 except Exception:return _fail("CERTIFICATE_JSON_INVALID")
 errs=[]
 claim=docs["claim"]
 if claim.get("claim_id")!=CLAIM_ID:errs.append("CLAIM_ID_MISMATCH")
 scope=((claim.get("claim_scope") or {}).get("scope_definition") or {})
 dd=scope.get("domain_definition") or {}
 if scope.get("entire_admissible_leaf_domain") is not True:errs.append("WHOLE_DOMAIN_ASSERTION_MISSING")
 if dd.get("filters")!=[] or dd.get("exclusions")!=[]:errs.append("DOMAIN_NARROWING_PRESENT")
 if dd.get("scope_relation")!="EXACT_WHOLE_ADMISSIBLE_LEAF_DOMAIN":errs.append("SCOPE_RELATION_DRIFT")
 d=docs["domain"]; dr=d.get("independent_replay") or {}
 if dr.get("real_manifest_passed")!=24:errs.append("DOMAIN_EQUIVALENCE_NOT_24")
 s=docs["scope"]; sr=s.get("independent_replay") or {}
 if sr.get("domain_equivalence_pass_count")!=24 or sr.get("scope_complete_count")!=24:errs.append("SCOPE_BATCH_NOT_24")
 if sr.get("property_truth_count")!=0:errs.append("SCOPE_BATCH_PROPERTY_OVERCLAIM")
 i=docs["identity"]; ir=i.get("independent_replay") or {}; th=i.get("theorem") or {}
 if ir.get("r12_claim_id")!=CLAIM_ID:errs.append("IDENTITY_CLAIM_MISMATCH")
 if i.get("universal_factorization_proved_count")!=12:errs.append("IDENTITY_FACTORIZATION_NOT_12")
 if th.get("finite_witness_set_used") is not False:errs.append("FINITE_SAMPLE_CARRIER_FORBIDDEN")
 if th.get("semantic_information_loss") is not False:errs.append("CARRIER_INFORMATION_LOSS")
 if cert.get("root_id")!=ROOT_ID or cert.get("claim_id")!=CLAIM_ID:errs.append("CERTIFICATE_IDENTITY_MISMATCH")
 bm=cert.get("b_plus_model") or {}
 if bm.get("definition")!="B_PLUS_C_EQUALS_W_C__THE_EXACT_COMPLETE_FROZEN_R12_SEMANTIC_CLAIM_WORLD_STATE":errs.append("B_PLUS_DEFINITION_DRIFT")
 if bm.get("compression_applied") is not False:errs.append("B_PLUS_COMPRESSION_FORBIDDEN")
 theorem=cert.get("theorem") or {}
 if theorem.get("proof_mode")!="FORMAL_DEFINITIONAL_CONTAINMENT":errs.append("PROOF_MODE_DRIFT")
 if theorem.get("b_real_subseteq_b_plus") is not True:errs.append("CONTAINMENT_NOT_ASSERTED")
 if theorem.get("property_truth_implied") is not False:errs.append("PROPERTY_TRUTH_OVERCLAIM")
 if cert.get("terminal_authority") is not False:errs.append("TERMINAL_AUTHORITY_OVERCLAIM")
 if errs:return _fail(*errs)
 return {"pass":True,"status":"PASS__CC_R1_R12_SEMANTIC_FORMAL_DEFINITIONAL_REALITY_CONTAINMENT","root_id":ROOT_ID,"claim_id":CLAIM_ID,"semantic_claim_verified":True,"b_real_subseteq_b_plus":True,"whole_domain_exact":True,"identity_carrier_total_injective":True,"property_truth_implied":False,"global_mission_completion_derivable":False,"terminal_credit_delta":0,"errors":[]}
if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
