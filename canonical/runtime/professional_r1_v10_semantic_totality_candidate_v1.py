"""Candidate totality theorem for the exact V10 R1 semantic claim.

This proves the non-R4 premises needed for one authentic positive R1 semantic
receipt while keeping the truth-repaired whole-domain property fail-closed.

Proof decomposition:
* CC_R1: current V10 claim batch proves exact whole-leaf domain equivalence and
  scope completeness for R1.
* CC_R2: the canonical R1 target-semantics compiler binds every target-defining
  role to exact behavioral-contract fields without unique-optimum strengthening.
* CC_R3: semantic admission Binder V3 structurally admits positive authority
  only for an exact current claim with independently verified totality basis;
  unknown/mismatch remains unauthorized.
* R1 defeaters: the full current R1 challenge subset (goal substitution and
  unresolved materially different interpretations) is discharged by exact role
  binding plus the fail-closed ambiguity policy.

Independent replay is intentionally separate. This module cannot self-mint R4
or leaf property truth.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_semantic_v2_v10_claim_batch_v1 as claims
from canonical.runtime import professional_target_semantic_certificate_v1 as target
from canonical.runtime import professional_quality_semantic_admission_binder_v3 as binder

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R1_V10_SEMANTIC_TOTALITY_CANDIDATE_V1"
LEAF_ID="PQ::R1_TARGET_SPECIFICATION::SEMANTIC"
ROOT_ID="R1_TARGET_SPECIFICATION"
BEHAVIOR_ID="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
MANIFEST_PATH="canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261011_V2.json"
MANIFEST_BLOB="8ae72d7d44047ac9dec1b014c34a44f9933f0215"
CONTRACT_PATH="canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json"
CONTRACT_BLOB="ae250d5bc5da73b23600670be354ffba31e65e53"
CHALLENGE_PATH="canonical/governance/PROFESSIONAL_QUALITY_ADVERSARIAL_CHALLENGE_MATRIX_20261009_V1.json"
CHALLENGE_BLOB="211a8587c4321bdda30b4055a878bb61c2614ab4"
EXPECTED_CHALLENGES={"C01_GOAL_SUBSTITUTION","C02_AMBIGUOUS_SPEC_WINNER"}


def _blob(path:Path)->str:
 raw=path.read_bytes();return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def _load(root:Path,rel:str,expected:str)->Mapping[str,Any]:
 p=root/rel
 if not p.is_file() or p.is_symlink(): raise ValueError("PIN_MISSING:"+rel)
 got=_blob(p)
 if got!=expected: raise ValueError("PIN_BLOB_DRIFT:"+rel+":"+got)
 obj=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(obj,Mapping): raise ValueError("PIN_NOT_OBJECT:"+rel)
 return obj


def _zero()->dict[str,Any]:
 return {
  "r4_proof_realization_authority":False,
  "independent_verified":False,
  "semantic_leaf_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
 }


def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "claim_scoped_totality_proved":False,
  "cc_r1_reality_containment_proved":False,
  "cc_r2_mission_soundness_proved":False,
  "cc_r3_terminal_closure_proved":False,**_zero(),**extra}


def _binding(contract:Mapping[str,Any])->dict[str,Any]:
 roles={
  "objective":"required_output_or_action","audience":"inputs",
  "hard_constraints":"allowed_information","success_semantics":"success_condition",
  "failure_semantics":"failure_condition","target_construct":"success_condition",
  "claim_scope":"scope","evidence_boundary":"dependency_boundary",
 }
 return {
  "behavior_id":BEHAVIOR_ID,
  "contract_sha256":target.digest(dict(contract)),
  "role_bindings":{
   role:{"source_field":field,"source_value_sha256":target.digest(contract[field])}
   for role,field in roles.items()
  },
  "ambiguity_policy":{
   "unique_optimum_claimed":False,
   "admissible_plan_definition":"ANY_PLAN_SATISFYING_SUCCESS_AND_AVOIDING_FAILURE_WITHIN_DECLARED_SCOPE",
   "unresolved_runtime_task_ambiguity_must_remain_open":True,
  },
  "hard_nonclaims":[
   "NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS",
   "NO_SOURCE_EXTRACTION_COMPLETENESS",
   "NO_UNIQUE_BEST_PLAN",
   "NO_GLOBAL_R1_SEMANTIC_LEAF_CLOSURE",
   "NO_GLOBAL_R1_ROOT_CLOSURE",
  ],
 }


def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 try:
  manifest=_load(root,MANIFEST_PATH,MANIFEST_BLOB)
  registry=_load(root,CONTRACT_PATH,CONTRACT_BLOB)
  matrix=_load(root,CHALLENGE_PATH,CHALLENGE_BLOB)
 except Exception as exc:
  return _fail(type(exc).__name__+":"+str(exc))

 batch=claims.verify(root=root)
 if batch.get("pass") is not True or batch.get("claim_count")!=12 or batch.get("scope_complete_count")!=12:
  return _fail("CURRENT_V10_CLAIM_BATCH_NOT_SCOPE_COMPLETE",claim_batch=batch)
 rows=[r for r in batch.get("rows") or [] if isinstance(r,Mapping) and r.get("leaf_id")==LEAF_ID]
 if len(rows)!=1:return _fail("R1_CURRENT_CLAIM_NOT_UNIQUE",match_count=len(rows))
 row=dict(rows[0])
 if row.get("root_id")!=ROOT_ID:return _fail("R1_ROOT_ID_DRIFT")
 if row.get("whole_leaf_domain_equivalence_proved") is not True or row.get("whole_leaf_scope_complete") is not True:
  return _fail("R1_WHOLE_DOMAIN_OR_SCOPE_NOT_PROVED")

 roots=[x for x in manifest.get("roots") or [] if isinstance(x,Mapping) and x.get("root_id")==ROOT_ID]
 if len(roots)!=1:return _fail("R1_MANIFEST_ROW_NOT_UNIQUE")
 mrow=roots[0]
 semantic=mrow.get("semantic_leaf") or {}
 if semantic.get("id")!=LEAF_ID:return _fail("R1_MANIFEST_LEAF_DRIFT")
 if semantic.get("acceptance")!=(row.get("claim_scope") or {}).get("leaf_acceptance"):
  return _fail("R1_CURRENT_ACCEPTANCE_NOT_MANIFEST_BOUND")

 contracts=[x for x in registry.get("active_contracted_residuals") or [] if isinstance(x,Mapping) and x.get("behavior_id")==BEHAVIOR_ID]
 if len(contracts)!=1:return _fail("R1_CANONICAL_BEHAVIOR_NOT_UNIQUE")
 contract=dict(contracts[0])
 sem=target.certify(contract,_binding(contract))
 if sem.get("pass") is not True:return _fail("R1_TARGET_SEMANTIC_COMPILER_REJECTED",semantic_result=sem)
 roles=set(sem.get("role_bindings_verified") or [])
 required={"objective","audience","hard_constraints","success_semantics","failure_semantics","target_construct","claim_scope","evidence_boundary"}
 if roles!=required:return _fail("R1_TARGET_ROLE_COVERAGE_INCOMPLETE",observed=sorted(roles))

 challenge_rows=[x for x in matrix.get("challenges") or [] if isinstance(x,Mapping) and ROOT_ID in (x.get("root_ids") or [])]
 challenge_ids={x.get("id") for x in challenge_rows}
 if challenge_ids!=EXPECTED_CHALLENGES:
  return _fail("R1_CHALLENGE_SET_DRIFT",observed=sorted(str(x) for x in challenge_ids))
 if any(x.get("terminal_pass_forbidden") is not True for x in challenge_rows):
  return _fail("R1_CHALLENGE_FAIL_CLOSED_RULE_DRIFT")

 shape=binder.prove_fail_closed_shape()
 if shape.get("pass") is not True or shape.get("unknown_or_mismatch_authorized") is not False:
  return _fail("SEMANTIC_ADMISSION_FAIL_CLOSED_SHAPE_NOT_PROVED",binder_shape=shape)
 expected_totality=set(binder.REQUIRED_TOTALITY_FIELDS)
 if set(shape.get("required_totality_fields") or [])!=expected_totality:
  return _fail("SEMANTIC_ADMISSION_TOTALITY_FIELD_DRIFT")

 # Claim-local R1 theorem:
 # - Positive witness is exact parameterized target semantics over the canonical
 #   professional behavior, with every target-defining role content-bound.
 # - Goal substitution is blocked because objective/success/failure/claim-scope
 #   source fields and values are digest-bound.
 # - Material interpretation ambiguity cannot silently pass because unique
 #   optimum is forbidden and unresolved ambiguity must remain open.
 # - Arbitrary prompt/source-extraction completeness are outside this positive
 #   witness, not silently assumed.
 # - All other admissible inputs without a matching independently verified
 #   receipt remain unauthorized by Binder V3.
 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS_CANDIDATE__R1_V10_CLAIM_SCOPED_TOTALITY__AWAITING_INDEPENDENT_R4",
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,
  "semantic_claim_id":row.get("claim_id"),
  "semantic_scope_sha256":(row.get("claim_scope") or {}).get("claim",{}).get("scope_sha256"),
  "semantic_target_predicate_sha256":(row.get("claim_scope") or {}).get("claim",{}).get("target_predicate_sha256"),
  "semantic_semantics_sha256":(row.get("claim_scope") or {}).get("claim",{}).get("semantics_sha256"),
  "positive_witness_kind":"EXACT_PARAMETERIZED_CANONICAL_PROFESSIONAL_TARGET_SEMANTICS",
  "positive_witness_verified":True,
  "positive_witness_nonvacuous":True,
  "resolved_or_decision_null_r1_challenge_ids":sorted(EXPECTED_CHALLENGES),
  "arbitrary_prompt_completeness_assumed":False,
  "source_extraction_completeness_assumed":False,
  "unique_best_plan_assumed":False,
  "claim_scoped_totality_proved":True,
  "cc_r1_reality_containment_proved":True,
  "cc_r2_mission_soundness_proved":True,
  "cc_r3_terminal_closure_proved":True,
  "proof_basis":{
   "whole_domain_scope":"CURRENT_V10_12_OF_12_SCOPE_COMPLETE",
   "positive_semantics":"CONTENT_BOUND_R1_TARGET_SEMANTIC_COMPILER",
   "negative_disposition":"BINDER_V3_EXACT_CLAIM_AND_TOTALITY_FAIL_CLOSED_SHAPE",
   "r1_defeater_partition":"R1_ROOT_CONTRACT_PLUS_C01_C02_EXPLICIT_DISCHARGE",
  },
  **_zero(),
 }
