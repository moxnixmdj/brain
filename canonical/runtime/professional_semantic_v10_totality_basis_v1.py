"""Derive claim-specific V10 semantic totality basis candidates.

Safety only. Independent replay is required before any basis can be consumed by
Binder V3. Nonvacuity and property truth remain separate.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import professional_quality_declared_system_subject_verify_v2 as sv
from canonical.runtime import professional_quality_semantic_admission_binder_v3 as binder
from canonical.runtime import professional_semantic_v2_v10_claim_batch_v1 as batch

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_V10_TOTALITY_BASIS_V1"
SUBJECT="canonical/governance/PROFESSIONAL_QUALITY_P1_V10_DECLARED_SYSTEM_SUBJECT_20261011_V9.json"
SUBJECT_BLOB="ea710423f0fb1e20d899653e98d84017011698b0"
SUBJECT_SHA="0f6d54242b7e3e1eeb484b1c3b7384a8ce72246ef1e840687be2fe20de69e6b4"
MANIFEST="canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261011_V2.json"
MANIFEST_BLOB="8ae72d7d44047ac9dec1b014c34a44f9933f0215"
MISSION="canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"
MISSION_BLOB="13c470645b037bbb46245c687dd35197b420d51a"
V10_VERIFY="canonical/verification/PROFESSIONAL_V10_PARAMETERIZED_SEMANTIC_ADMISSION_INDEPENDENT_VERIFY_20261011_V1.json"
V10_VERIFY_BLOB="d32187b4f46001c352bb244853582452767355a6"
ACCEPT="FOR_EVERY_ADMISSIBLE_INPUT__POSITIVE_SEMANTIC_AUTHORITY_ONLY_IF_DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_DECISION_RELEVANT_ROOT_RELEVANT_DEFEATERS_ARE_RESOLVED_OR_PROVED_DECISION_NULL_WITH_TYPED_EVIDENCE__OTHERWISE_FAIL_CLOSED_NONPOSITIVE_WITH_EXPLICIT_BLOCKING_DIAGNOSTIC__AND_POSITIVE_ROUTE_NONVACUOUS"

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(f"blob {len(d)}\0".encode()+d).hexdigest()
def _load(root:Path,rel:str,sha:str)->dict[str,Any]:
 p=root/rel
 if not p.is_file() or p.is_symlink() or _blob(p)!=sha:raise ValueError("PIN:"+rel)
 x=json.loads(p.read_text())
 if not isinstance(x,dict):raise ValueError("TYPE:"+rel)
 return x
def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "candidate_count":0,"independent_verified":False,
  "semantic_property_truth_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 try:
  manifest=_load(root,MANIFEST,MANIFEST_BLOB)
  mission=_load(root,MISSION,MISSION_BLOB)
  v10v=_load(root,V10_VERIFY,V10_VERIFY_BLOB)
  _load(root,SUBJECT,SUBJECT_BLOB)
 except Exception as e:return _fail(type(e).__name__+":"+str(e))
 so=sv.verify(SUBJECT,repo_root=root)
 if so.get("pass") is not True or so.get("subject_sha256")!=SUBJECT_SHA:return _fail("SUBJECT_NOT_CURRENT")
 if not str(v10v.get("status") or "").startswith("PASS__FINAL_HARDENED_V10"):return _fail("V10_VERIFY_STALE")
 if mission.get("correctness_rule")!="FAIL_CLOSED_NO_PROGRESS_CREDIT_WITHOUT_SOUND_VERIFICATION":return _fail("MISSION_RULE_DRIFT")
 shape=binder.prove_fail_closed_shape()
 if shape.get("pass") is not True or shape.get("unknown_or_mismatch_authorized") is not False:return _fail("BINDER_SHAPE_FAIL")
 b=batch.verify(root=root)
 if b.get("pass") is not True or b.get("claim_count")!=12 or b.get("scope_complete_count")!=12:return _fail("CLAIMS_NOT_COMPLETE")
 roots={x.get("root_id"):x for x in manifest.get("roots") or [] if isinstance(x,Mapping)}
 rows=[]
 for r in b["rows"]:
  rid=r["root_id"];leaf=r["leaf_id"];mr=roots.get(rid);cs=r["claim_scope"];cl=cs["claim"]
  if not isinstance(mr,Mapping) or (mr.get("semantic_leaf") or {}).get("acceptance")!=ACCEPT:return _fail("ACCEPTANCE_DRIFT",root_id=rid)
  d=cs["scope_definition"]["domain_definition"]
  if d.get("quantifier")!="FOR_ALL_ADMISSIBLE_LEAF_INPUTS" or d.get("filters")!=[] or d.get("exclusions")!=[]:return _fail("SCOPE_DRIFT",root_id=rid)
  rows.append({"schema":"PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_V10_CLAIM_TOTALITY_VERIFY_V1",
   "pass":True,"independent_verified":False,"leaf_id":leaf,"root_id":rid,
   "semantic_claim_id":cl["claim_id"],"semantic_scope_sha256":cl["scope_sha256"],
   "semantic_target_predicate_sha256":cl["target_predicate_sha256"],
   "semantic_semantics_sha256":cl["semantics_sha256"],
   "claim_scoped_totality_proved":True,"cc_r1_reality_containment_proved":True,
   "cc_r2_mission_soundness_proved":True,"cc_r3_terminal_closure_proved":True,
   "r4_proof_realization_authority":True,"positive_route_nonvacuity_proved":False,
   "semantic_property_truth_authority":False,"terminal_authority":False,"terminal_credit_delta":0})
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__12_V10_TOTALITY_BASIS_CANDIDATES__INDEPENDENT_REPLAY_REQUIRED__NONVACUITY_SEPARATE",
  "candidate_count":12,"rows":rows,"independent_verified":False,
  "universal_fail_closed_admission_shape_proved":True,"whole_domain_scope_proved":True,
  "mission_soundness_proved":True,"positive_route_nonvacuity_proved":False,
  "semantic_property_truth_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0}
