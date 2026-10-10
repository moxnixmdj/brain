"""Current-V3 evidence cut for the R12 semantic CC_R3 obligation.

Separates the stable semantic property claim from the stable whole-leaf scope
claim. Reuses only evidence whose authority survives current V3 claim identity.
No clause result here grants CC_R3, semantic property, quality, or terminal
authority.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_SEMANTIC_CC_R3_EVIDENCE_CUT_V2"
PROPERTY_CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
SCOPE_CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
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

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "property_claim_id":PROPERTY_CLAIM_ID,"scope_claim_id":SCOPE_CLAIM_ID,"leaf_id":LEAF_ID,
  "verified_clause_count":0,"partial_clause_count":0,"open_clause_count":8,
  "cc_r3_terminal_closure_proved":False,
  "claim_scoped_totality_proved":False,
  "semantic_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
 }

def analyze(
 *,
 decomposition:Mapping[str,Any],
 composition_verify:Mapping[str,Any],
 v3_current_verify:Mapping[str,Any],
 c5_bridge:Mapping[str,Any],
 c1_verify:Mapping[str,Any],
 c3_verify:Mapping[str,Any],
 defeater_replay:Mapping[str,Any],
 challenge_verify:Mapping[str,Any],
 root_theorem:Mapping[str,Any],
 r12_execution_verify:Mapping[str,Any],
 c8_verify:Mapping[str,Any],
)->dict[str,Any]:
 docs=(decomposition,composition_verify,v3_current_verify,c5_bridge,c1_verify,c3_verify,
       defeater_replay,challenge_verify,root_theorem,r12_execution_verify,c8_verify)
 if not all(isinstance(x,Mapping) for x in docs):
  return _fail("INPUT_NOT_MAPPING")

 # The root-contract decomposition is scope-bound, not semantic-property-claim
 # authority. Keep the two identities separate.
 if decomposition.get("claim_id")!=SCOPE_CLAIM_ID or decomposition.get("leaf_id")!=LEAF_ID:
  return _fail("DECOMPOSITION_SCOPE_CLAIM_DRIFT")
 clauses=decomposition.get("clauses")
 ids=[x.get("id") for x in clauses] if isinstance(clauses,list) and all(isinstance(x,Mapping) for x in clauses) else []
 if tuple(ids)!=EXPECTED_CLAUSES:
  return _fail("DECOMPOSITION_NOT_EXACT_EIGHT_CLAUSES",observed=ids)
 dc=decomposition.get("decomposition_claim") or {}
 if dc.get("coverage_complete") is not True or dc.get("duplicate_or_unbound_clauses")!=0:
  return _fail("DECOMPOSITION_NOT_LOSSLESS")
 tr=decomposition.get("target_predicate_relation") or {}
 if tr.get("stronger_than_root_contract") is not True or tr.get("root_contract_decomposition_does_not_by_itself_prove_target_predicate") is not True:
  return _fail("STRONGER_TARGET_BOUNDARY_MISSING")

 # Bind current stable semantic-property claim and current V3 identity carrier.
 observed=v3_current_verify.get("observed") or {}
 v3_proves=set(v3_current_verify.get("proves") or [])
 if (
  not str(v3_current_verify.get("status") or "").startswith("PASS__")
  or observed.get("r12_stable_claim_id")!=PROPERTY_CLAIM_ID
  or observed.get("v3_identity_carrier_factorization_count")!=12
  or "ALL_TWELVE_STABLE_V3_SEMANTIC_CLAIMS_RETAIN_LOSSLESS_IDENTITY_CARRIER_FACTORIZATION" not in v3_proves
 ):
  return _fail("CURRENT_V3_PROPERTY_CLAIM_OR_CARRIER_NOT_VERIFIED")

 # C2: exact same-subject root conjunction.
 comp=set(composition_verify.get("proves") or [])
 c2=(
  str(composition_verify.get("status") or "").startswith("PASS__")
  and "ALL_TWELVE_CURRENT_PROFESSIONAL_ROOT_BINDINGS_BIND_THE_IDENTICAL_FROZEN_V7_SUBJECT_TUPLE" in comp
  and "SAME_SUBJECT_COMPOSITION_IS_STRUCTURALLY_ADMISSIBLE" in comp
 )

 # C1/C3 now have independent current proofs on the stable V3 / exact
 # same-subject composition boundary.
 c1=(
  str(c1_verify.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE")
  and c1_verify.get("c1_assumption_guarantee_composition_proved") is True
  and c1_verify.get("cc_r3_terminal_closure_proved") is False
  and c1_verify.get("semantic_property_truth_authority") is False
 )
 c3_proves=set(c3_verify.get("proves") or [])
 c3=(
  str(c3_verify.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE")
  and "R12C3_ABSTRACTION_SOUNDNESS_IS_PROVED_AT_THE_ROOT_BINDING_TO_SAME_SUBJECT_COMPOSITION_BOUNDARY" in c3_proves
  and "NO_UNKNOWN_MATERIAL_DEFEATER_COMPLETENESS" in set(c3_verify.get("hard_nonclaims") or [])
 )

 # C4: independently replayed known-defeater search/challenge only.
 c4=(
  str(defeater_replay.get("status") or "").startswith("PASS__")
  and "NO_ADVERSARIAL_COMPLETENESS_OF_UNKNOWN_ATTACKS" in set(defeater_replay.get("hard_nonclaims") or [])
  and str(challenge_verify.get("status") or "").startswith("PASS__")
 )

 # C5: current V3 property claim reuses the exact verified whole-leaf scope
 # proof only through equal scope-claim identity and scope digest.
 c5=(
  c5_bridge.get("pass") is True
  and c5_bridge.get("v3_claim_id")==PROPERTY_CLAIM_ID
  and c5_bridge.get("whole_leaf_scope_claim_id")==SCOPE_CLAIM_ID
  and c5_bridge.get("c5_coverage_accounting_proved_for_v3_claim") is True
  and c5_bridge.get("source_v2_property_authority_transported") is False
  and c5_bridge.get("semantic_property_truth_authority") is False
 )

 hard=set(root_theorem.get("hard_rules") or [])
 ep=set(r12_execution_verify.get("proves") or [])
 unknown_boundary=(
  "NO_ADVERSARIAL_COMPLETENESS_OF_UNKNOWN_ATTACKS" in set(defeater_replay.get("hard_nonclaims") or [])
  and "NO_UNKNOWN_DEFEATER_COMPLETENESS" in set(r12_execution_verify.get("hard_nonclaims") or [])
 )
 if not unknown_boundary:
  return _fail("UNKNOWN_DEFEATER_BOUNDARY_NOT_PRESERVED")

 # C6/C7 are claim-stable proof-calculus / controller properties.
 c6=(
  {"UNKNOWN_NEVER_EQUALS_PROVED","NOT_PROVED_NEVER_EQUALS_FALSE","TIMEOUT_NEVER_EQUALS_UNSAT"}<=hard
  and "ALL_14_CANONICAL_R12_DEFEATERS_COUNTERPROVE_WHEN_ACTIVATED" in ep
 )
 c7=(
  str(r12_execution_verify.get("status") or "").startswith("PASS__")
  and "ALL_14_CANONICAL_R12_DEFEATERS_COUNTERPROVE_WHEN_ACTIVATED" in ep
 )

 # C8 now has a direct current proof that is independent of semantic-pack V3.
 truth=c8_verify.get("truth") or {}
 c8=(
  str(c8_verify.get("status") or "").startswith("PASS__")
  and truth.get("c8_nonvacuity_proved") is True
  and truth.get("independently_observed_positive_route_count",0)>=1
  and truth.get("stronger_material_defeater_totality_proved") is False
  and truth.get("semantic_property_truth_authority") is False
 )

 rows=[
  {"clause_id":EXPECTED_CLAUSES[0],"state":"VERIFIED_CURRENT" if c1 else "OPEN",
   "basis":["STABLE_V3_C1_ASSUMPTION_GUARANTEE_REINSTANTIATION"] if c1 else []},
  {"clause_id":EXPECTED_CLAUSES[1],"state":"VERIFIED_CURRENT" if c2 else "OPEN",
   "basis":["INDEPENDENT_12_OF_12_SAME_SUBJECT_COMPOSITION"] if c2 else []},
  {"clause_id":EXPECTED_CLAUSES[2],"state":"VERIFIED_CURRENT" if c3 else "OPEN",
   "basis":["INDEPENDENT_LOSSLESS_COMPOSITION_PROJECTION_SCOPE_PRESERVATION"] if c3 else []},
  {"clause_id":EXPECTED_CLAUSES[3],"state":"VERIFIED_CURRENT" if c4 else "OPEN",
   "basis":["INDEPENDENT_KNOWN_DEFEATER_REPLAY","INDEPENDENT_DOMAIN_CHALLENGE_REFERENCE"] if c4 else [],
   "boundary":"SEARCH_VERIFIED__UNKNOWN_DEFEATER_COMPLETENESS_NOT_PROVED"},
  {"clause_id":EXPECTED_CLAUSES[4],"state":"VERIFIED_CURRENT" if c5 else "OPEN",
   "basis":["V3_PROPERTY_TO_STABLE_SCOPE_C5_BRIDGE","EXACT_WHOLE_LEAF_SCOPE_ACCOUNTING"] if c5 else []},
  {"clause_id":EXPECTED_CLAUSES[5],"state":"VERIFIED_CURRENT" if c6 else "OPEN",
   "basis":["UNKNOWN_NEVER_EQUALS_PROVED","NOT_PROVED_NEVER_EQUALS_FALSE","TIMEOUT_NEVER_EQUALS_UNSAT","R12_PROOF_SEARCH_FALSE_NEGATIVE_COUNTERPROOF"] if c6 else []},
  {"clause_id":EXPECTED_CLAUSES[6],"state":"VERIFIED_CURRENT" if c7 else "OPEN",
   "basis":["R12_META_CONTROLLER_DEFEATER_COUNTERPROOF"] if c7 else []},
  {"clause_id":EXPECTED_CLAUSES[7],"state":"VERIFIED_CURRENT" if c8 else "OPEN",
   "basis":["CURRENT_INDEPENDENT_REAL_SUPPORTED_POSITIVE_R12_ROUTES"] if c8 else []},
 ]
 vc=sum(x["state"]=="VERIFIED_CURRENT" for x in rows)
 pc=sum(x["state"]=="PARTIAL_EXISTING_EVIDENCE" for x in rows)
 oc=8-vc-pc
 return {
  "schema":SCHEMA,"pass":True,
  "status":f"PASS__CURRENT_V3_R12_CC_R3_CUT__{vc}_VERIFIED__{pc}_PARTIAL__{oc}_OPEN__STRONGER_MATERIAL_DEFEATER_TOTALITY_OPEN",
  "property_claim_id":PROPERTY_CLAIM_ID,"scope_claim_id":SCOPE_CLAIM_ID,"leaf_id":LEAF_ID,
  "verified_clause_count":vc,"partial_clause_count":pc,"open_clause_count":oc,
  "clauses":rows,
  "claim_identity_model":"SEMANTIC_PROPERTY_CLAIM_AND_WHOLE_LEAF_SCOPE_CLAIM_SEPARATE__NO_CROSS_CLAIM_AUTHORITY_TRANSPORT",
  "stronger_target_residual":{
   "state":"OPEN",
   "obligation":"ALL_ROOT_RELEVANT_MATERIAL_DEFEATERS_RESOLVED_OR_PROVED_DECISION_NULL_BEFORE_POSITIVE_CERTIFICATION",
   "known_defeater_search_is_not_completeness":True,
   "execution_known_defeater_replay_is_not_completeness":True,
  },
  "exact_next":[
   "PROVE_STRONGER_MATERIAL_DEFEATER_TOTALITY_OR_SCOPE_COMPLETE_EQUIVALENT",
  ],
  "cc_r3_terminal_closure_proved":False,
  "claim_scoped_totality_proved":False,
  "semantic_property_truth_authority":False,
  "new_primitive_required":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
 }
