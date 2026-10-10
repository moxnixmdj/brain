"""Fail-closed evidence cut for the R12 semantic CC_R3 obligation.

This classifier deliberately separates:
1) the eight conjunctive clauses of the R12 root contract, and
2) the stronger semantic target obligation that every material root-relevant
   defeater is resolved or proved decision-null before positive certification.

It never turns known-defeater replay into unknown-defeater completeness and never
turns same-subject composition into assumption-guarantee discharge.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_SEMANTIC_CC_R3_EVIDENCE_CUT_V1"
CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
LEAF_ID="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"

EXPECTED_CLAUSES=(
 "R12C1_ASSUMPTION_GUARANTEE_COMPOSITION",
 "R12C2_SAME_SUBJECT_ROOT_CONJUNCTION",
 "R12C3_ABSTRACTION_SOUNDNESS",
 "R12C4_INDEPENDENT_DEFEATER_SEARCH",
 "R12C5_COVERAGE_ACCOUNTING",
 "R12C6_PROOF_SEARCH_HONESTY",
 "R12C7_META_CONTROLLER_FALSIFICATION",
 "R12C8_NONVACUITY",
)

def _fail(reason:str, **extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "claim_id":CLAIM_ID,"leaf_id":LEAF_ID,
  "verified_clause_count":0,"partial_clause_count":0,"open_clause_count":0,
  "cc_r3_terminal_closure":False,"semantic_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
 }

def analyze(
 *,
 decomposition:Mapping[str,Any],
 composition_verify:Mapping[str,Any],
 identity_verify:Mapping[str,Any],
 domain_verify:Mapping[str,Any],
 scope_verify:Mapping[str,Any],
 defeater_replay:Mapping[str,Any],
 challenge_verify:Mapping[str,Any],
 root_theorem:Mapping[str,Any],
 r12_execution_verify:Mapping[str,Any],
 cc_r2_verify:Mapping[str,Any],
)->dict[str,Any]:
 docs=(decomposition,composition_verify,identity_verify,domain_verify,scope_verify,
       defeater_replay,challenge_verify,root_theorem,r12_execution_verify,cc_r2_verify)
 if not all(isinstance(x,Mapping) for x in docs):
  return _fail("INPUT_NOT_MAPPING")

 if decomposition.get("claim_id")!=CLAIM_ID or decomposition.get("leaf_id")!=LEAF_ID:
  return _fail("DECOMPOSITION_CLAIM_DRIFT")
 clauses=decomposition.get("clauses")
 if not isinstance(clauses,list):
  return _fail("DECOMPOSITION_CLAUSES_INVALID")
 ids=[x.get("id") for x in clauses if isinstance(x,Mapping)]
 if tuple(ids)!=EXPECTED_CLAUSES or len(ids)!=8:
  return _fail("DECOMPOSITION_NOT_EXACT_EIGHT_CLAUSES",observed=ids)
 dc=decomposition.get("decomposition_claim") or {}
 if dc.get("coverage_complete") is not True or dc.get("duplicate_or_unbound_clauses")!=0:
  return _fail("DECOMPOSITION_NOT_LOSSLESS")
 tr=decomposition.get("target_predicate_relation") or {}
 if tr.get("stronger_than_root_contract") is not True:
  return _fail("STRONGER_TARGET_RELATION_MISSING")
 if tr.get("root_contract_decomposition_does_not_by_itself_prove_target_predicate") is not True:
  return _fail("DECOMPOSITION_SELF_PROMOTION_FORBIDDEN")

 # C2: exact same-subject conjunction is independently verified.
 comp_proves=set(composition_verify.get("proves") or [])
 c2=(
  str(composition_verify.get("status") or "").startswith("PASS__")
  and "ALL_TWELVE_CURRENT_PROFESSIONAL_ROOT_BINDINGS_BIND_THE_IDENTICAL_FROZEN_V7_SUBJECT_TUPLE" in comp_proves
  and "SAME_SUBJECT_COMPOSITION_IS_STRUCTURALLY_ADMISSIBLE" in comp_proves
 )

 # C3 partial only: leaf semantic carrier is lossless, but this does not prove
 # every component contract abstraction sound under substitution.
 it=identity_verify.get("theorem") or {}
 c3_partial=(
  str(identity_verify.get("status") or "").startswith("PASS__")
  and it.get("finite_witness_set_used") is False
  and it.get("semantic_information_loss") is False
  and (identity_verify.get("independent_replay") or {}).get("r12_claim_id")==CLAIM_ID
 )

 # C4: independent known-defeater search/replay exists. Completeness is separate.
 c4=(
  str(defeater_replay.get("status") or "").startswith("PASS__")
  and "NO_ADVERSARIAL_COMPLETENESS_OF_UNKNOWN_ATTACKS" in set(defeater_replay.get("hard_nonclaims") or [])
  and str(challenge_verify.get("status") or "").startswith("PASS__")
 )

 # C5: exact whole-domain accounting and 24/24 scope cover.
 dr=domain_verify.get("independent_replay") or {}
 sr=scope_verify.get("independent_replay") or {}
 c5=(
  str(domain_verify.get("status") or "").startswith("PASS__")
  and dr.get("real_manifest_passed")==24
  and dr.get("unique_claim_id_count")==24
  and str(scope_verify.get("status") or "").startswith("PASS__")
  and sr.get("domain_equivalence_pass_count")==24
  and sr.get("scope_complete_count")==24
  and sr.get("property_truth_count")==0
 )

 # C6: proof-search honesty has explicit proof-calculus rules and an R12
 # challenge whose activation counterproves.
 hard=set(root_theorem.get("hard_rules") or [])
 ep=set(r12_execution_verify.get("proves") or [])
 c6=(
  {"UNKNOWN_NEVER_EQUALS_PROVED","NOT_PROVED_NEVER_EQUALS_FALSE","TIMEOUT_NEVER_EQUALS_UNSAT"}<=hard
  and "ALL_14_CANONICAL_R12_DEFEATERS_COUNTERPROVE_WHEN_ACTIVATED" in ep
 )

 # C7: same exact R12 execution verifier includes meta-controller false-
 # irrelevance among its canonical R12 defeaters and proves all counterprove.
 c7=(
  "ALL_14_CANONICAL_R12_DEFEATERS_COUNTERPROVE_WHEN_ACTIVATED" in ep
  and str(r12_execution_verify.get("status") or "").startswith("PASS__")
 )

 # C8: CC_R2 explicitly makes nonvacuity load-bearing.
 r2p=set(cc_r2_verify.get("proves") or [])
 c8=(
  str(cc_r2_verify.get("status") or "").startswith("PASS__")
  and "NONVACUITY_IS_LOAD_BEARING__ABSTENTION_CANNOT_BE_RELABELED_AS_POSITIVE_PROPERTY_TRUTH" in r2p
  and cc_r2_verify.get("cc_r2_mission_soundness_proved") is True
 )

 # C1 remains partial: composition exists, but there is no current exact proof
 # that all assumption/guarantee interfaces are discharged soundly.
 c1_partial=c2

 rows=[
  {"clause_id":EXPECTED_CLAUSES[0],"state":"PARTIAL_EXISTING_EVIDENCE" if c1_partial else "OPEN",
   "basis":["SAME_SUBJECT_COMPOSITION_VERIFIED"] if c1_partial else [],
   "remaining":"PROVE_EXACT_ASSUMPTION_GUARANTEE_INTERFACE_DISCHARGE_FOR_R12_COMPOSITION"},
  {"clause_id":EXPECTED_CLAUSES[1],"state":"VERIFIED_EXISTING" if c2 else "OPEN",
   "basis":["INDEPENDENT_12_OF_12_SAME_SUBJECT_COMPOSITION"] if c2 else []},
  {"clause_id":EXPECTED_CLAUSES[2],"state":"PARTIAL_EXISTING_EVIDENCE" if c3_partial else "OPEN",
   "basis":["LOSSLESS_IDENTITY_SEMANTIC_CARRIER","WHOLE_DOMAIN_EQUIVALENCE"] if c3_partial else [],
   "remaining":"PROVE_COMPONENT_ABSTRACTION_SOUNDNESS_UNDER_R12_COMPOSITION"},
  {"clause_id":EXPECTED_CLAUSES[3],"state":"VERIFIED_EXISTING" if c4 else "OPEN",
   "basis":["INDEPENDENT_KNOWN_DEFEATER_REPLAY","INDEPENDENT_DOMAIN_CHALLENGE_REFERENCE"] if c4 else [],
   "boundary":"SEARCH_VERIFIED__UNKNOWN_DEFEATER_COMPLETENESS_NOT_PROVED"},
  {"clause_id":EXPECTED_CLAUSES[4],"state":"VERIFIED_EXISTING" if c5 else "OPEN",
   "basis":["24_OF_24_WHOLE_DOMAIN_EQUIVALENCE","24_OF_24_SCOPE_COMPLETE"] if c5 else []},
  {"clause_id":EXPECTED_CLAUSES[5],"state":"VERIFIED_EXISTING" if c6 else "OPEN",
   "basis":["UNKNOWN_NEVER_EQUALS_PROVED","NOT_PROVED_NEVER_EQUALS_FALSE","TIMEOUT_NEVER_EQUALS_UNSAT","R12_PROOF_SEARCH_FALSE_NEGATIVE_COUNTERPROOF"] if c6 else []},
  {"clause_id":EXPECTED_CLAUSES[6],"state":"VERIFIED_EXISTING" if c7 else "OPEN",
   "basis":["R12_META_CONTROLLER_FALSE_IRRELEVANCE_COUNTERPROOF"] if c7 else []},
  {"clause_id":EXPECTED_CLAUSES[7],"state":"VERIFIED_EXISTING" if c8 else "OPEN",
   "basis":["CC_R2_NONVACUITY_LOAD_BEARING"] if c8 else []},
 ]
 vc=sum(r["state"]=="VERIFIED_EXISTING" for r in rows)
 pc=sum(r["state"]=="PARTIAL_EXISTING_EVIDENCE" for r in rows)
 oc=8-vc-pc

 known_unknown_boundary=(
  "NO_ADVERSARIAL_COMPLETENESS_OF_UNKNOWN_ATTACKS" in set(defeater_replay.get("hard_nonclaims") or [])
  and "NO_UNKNOWN_DEFEATER_COMPLETENESS" in set(r12_execution_verify.get("hard_nonclaims") or [])
 )
 if not known_unknown_boundary:
  return _fail("UNKNOWN_DEFEATER_BOUNDARY_NOT_PRESERVED")

 return {
  "schema":SCHEMA,"pass":True,
  "status":f"PASS__R12_CC_R3_CONTRACT_CLAUSE_CUT__{vc}_VERIFIED__{pc}_PARTIAL__{oc}_OPEN__STRONGER_DEFEATER_TOTALITY_OPEN",
  "claim_id":CLAIM_ID,"leaf_id":LEAF_ID,
  "verified_clause_count":vc,"partial_clause_count":pc,"open_clause_count":oc,
  "clauses":rows,
  "stronger_target_residual":{
   "state":"OPEN",
   "obligation":"ALL_ROOT_RELEVANT_MATERIAL_DEFEATERS_RESOLVED_OR_PROVED_DECISION_NULL_BEFORE_POSITIVE_CERTIFICATION",
   "known_defeater_search_is_not_completeness":True,
   "execution_known_defeater_replay_is_not_completeness":True,
  },
  "exact_next":[
   "PROVE_C1_ASSUMPTION_GUARANTEE_INTERFACE_DISCHARGE",
   "PROVE_C3_COMPONENT_ABSTRACTION_SOUNDNESS",
   "PROVE_STRONGER_MATERIAL_DEFEATER_TOTALITY_OR_SCOPE_COMPLETE_EQUIVALENT"
  ],
  "cc_r3_terminal_closure":False,
  "semantic_property_truth_authority":False,
  "new_primitive_required":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
 }
