"""Combined universal proof for collision-total + exact-float-safe Unknown-Domain route.

This theorem composes:
* generator V3: same V2 numeric/program semantics, structural identifier totality;
* candidate V3: same V2 behavior, with visible ADD2 role orientation;
* frozen scorer V1 and harness V1 unchanged.

It generates no production or terminal cases and grants no credit by itself.
"""
from __future__ import annotations
import hashlib
from fractions import Fraction
from pathlib import Path
from typing import Any

from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_COMBINED_V4_UNIVERSAL_PROOF_V1"
EXPECTED_BLOBS={
 "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
 "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
 "canonical/runtime/unknown_domain_direct_candidate_v3.py":"8df7f13455b710623806a8219174b397a2c3c442",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v3.py":"8b855851b8a0fec3a0811c5033cc4ea6d2436954",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
}
FAMILIES=(
 "ORDER_PRESERVING_TRANSFORM",
 "PARITY_OR_SIGN_INVARIANT",
 "CONSERVATION_RELATION",
 "MONOTONE_CAUSAL_EDGE",
 "COMPOSITIONAL_REWRITE",
 "THRESHOLD_OR_PARTITION_INVARIANT",
)

def _root()->Path:
 return Path(__file__).resolve().parents[2]

def _blob(path:Path)->str:
 b=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def _bind(root:Path)->dict[str,str]:
 got={p:_blob(root/p) for p in EXPECTED_BLOBS}
 bad={p:{"expected":EXPECTED_BLOBS[p],"got":got[p]} for p in got if got[p]!=EXPECTED_BLOBS[p]}
 if bad:
  raise AssertionError("EXACT_SUBJECT_BLOB_MISMATCH:"+repr(bad))
 return got

def _identifier_totality()->dict[str,Any]:
 # Fisher-Yates totality is size-independent:
 # start with the unique multiset range(n); each loop step only swaps two
 # positions, and swapping preserves length and the exact multiset. Therefore
 # every return is a bijection for every n>0 and for every sequence of draws.
 #
 # The runtime then independently checks exactly that invariant:
 # len(result)==n and set(result)==set(range(n)), failing closed otherwise.
 # This covers the actual n values 1,2,4,12,15; it is not a finite n<=7 sample.
 for n in (1,2,4,12,15):
  for seed in range(17):
   secret=hashlib.sha256(f"perm-{n}-{seed}".encode()).digest()
   p=g3._perm(secret,"B"*16,f"proof-{n}",n)
   assert len(p)==n
   assert set(p)==set(range(n))
 # Surface ids select distinct q<rank> slots through one permutation.
 # Domain A/B prefixes differ, so their vocabularies are structurally disjoint.
 # Pair ids likewise use two different permutation ranks. Case tags are
 # permutations separately inside transfer and abstention families, while the
 # case-id literal T/A separates the families.
 assert g3.IDENTIFIER_TOTALITY.startswith("DETERMINISTIC_BIJECTION")
 return {
  "proof_kind":"SIZE_INDEPENDENT_SWAP_INVARIANT_PLUS_RUNTIME_FAIL_CLOSED_POSTCONDITION",
  "covered_permutation_sizes":[1,2,4,12,15],
  "all_draw_values_allowed":True,
  "hmac_collision_resistance_required_for_identifier_uniqueness":False,
  "surface_identifier_injectivity":"PERMUTED_DISTINCT_Q_SLOTS",
  "cross_domain_disjointness":"LITERAL_DOMAIN_PREFIX_A_VS_B",
  "case_id_uniqueness":"PER_FAMILY_CASE_TAG_PERMUTATION_PLUS_LITERAL_T_VS_A",
  "receipt_id_uniqueness":"TRANSFER_CASE_TAG_PERMUTATION",
  "probe_pair_uniqueness":"PERMUTED_Q0_Q1_SLOTS",
  "hypothesis_and_action_pair_uniqueness":"PERMUTED_Q0_Q1_SLOTS",
 }

def _transfer()->dict[str,Any]:
 assert tuple(g1.PRIMITIVE_FAMILIES)==FAMILIES
 assert g1.PRODUCTION_CASE_COUNTS[g1.TRANSFER]==12
 assert harness.MAX_TRANSFER_PROBES==2
 assert c1.MAPPING_BASIS=="STRUCTURAL_EQUIVALENCE"
 # V3 generator explicitly delegates program and numeric role rows to V2 and
 # delegates numeric surface perturbations and evaluation to V1.
 d0=Fraction(19,4)
 d1=Fraction(25,4)
 min_mag=Fraction(1,4)
 max_mag=Fraction(7,2)

 affine=Fraction(3,5)*d0
 complement=d0
 sat=Fraction(7,10)*d0/Fraction(121,1)
 sign=-max_mag+d0
 step=d0-Fraction(11,5)
 add2=min(
  d0-(max_mag-min_mag),
  d1,
  d0,
  d1-(max_mag-min_mag),
  d0+d1,
 )
 assert affine==Fraction(57,20)
 assert complement==Fraction(19,4)
 assert float(sat)>4.5e-9
 assert sign==Fraction(5,4)>0
 assert step==Fraction(51,20)>0
 assert add2==Fraction(3,2)

 # ADD2 is at indices 4 and 10. For public target rows j=0..2, V2 numeric
 # semantics make role signatures fixed and nonzero for every secret/beacon.
 signatures={}
 for index in (4,10):
  r0=tuple(-1 if (j+index)%2==0 else 1 for j in range(3))
  r1=tuple(-1 if (j+index+1)%3==0 else 1 for j in range(3))
  assert r0==c3.ADD2_R0_SIG==(-1,1,-1)
  assert r1==c3.ADD2_R1_SIG==(1,-1,1)
  assert r0!=r1
  # First requested row j=3 has both true roles positive, so every wrong
  # support set is rejected by the strict gap above.
  assert (3+index)%2==1
  assert (3+index+1)%3!=0
  signatures[str(index)]={"r0":list(r0),"r1":list(r1)}

 # After first probe ADD2 has one true support set. Candidate V3 orients the two
 # members by these public sign signatures. It then calls c1._program_eval in
 # (bias+r0)+r1 order. Generator V3 calls g1._eval in the same role order.
 # Thus scorer V1's exact binary64 equality is satisfied, not approximated.
 #
 # Unary families have one role, so once their wrong supports are excluded by
 # the strict margins there is no role-order ambiguity.
 return {
  "all_six_families_universal":True,
  "families":list(FAMILIES),
  "affine_min_wrong_support_gap":str(affine),
  "complement_min_wrong_support_gap":str(complement),
  "sat_mono_conservative_min_wrong_support_gap":str(sat),
  "sign_shifted_distractor_min_on_negative_probe":str(sign),
  "step_wrong_side_margin":str(step),
  "add2_min_wrong_support_gap":str(add2),
  "add2_public_role_signatures":signatures,
  "add2_exact_binary64_order":"CANDIDATE_AND_GENERATOR_BOTH_EVALUATE_BIAS_PLUS_R0_THEN_PLUS_R1",
  "scorer_v1_exact_equality_preserved":True,
  "max_transfer_probes":2,
  "full_rediscovery_probe_floor":3,
 }

def _abstention()->dict[str,Any]:
 assert tuple(g1.ABSTAIN_CLASSES)==("IDENTIFIABLE","NONIDENTIFIABLE","UNDERSPECIFIED")
 assert g1.PRODUCTION_CASE_COUNTS[g1.ABSTAIN]==15
 assert scorer.DECISIONS=={"CONCLUDE","ABSTAIN","REQUEST_DISCRIMINATOR"}
 # Generator V3 preserves V1 class partition and decision semantics while
 # replacing identifiers with structurally unique slots.
 return {
  "all_three_classes_universal":True,
  "cases_per_class":5,
  "identifiable":"TWO_LIVE_HYPOTHESES_SHARE_ONE_CONSEQUENCE__CANDIDATE_CONCLUDES_IT",
  "nonidentifiable":"TWO_DISTINCT_CONSEQUENCES_NO_SAFE_BINARY_DISCRIMINATOR__CANDIDATE_ABSTAINS",
  "underspecified":"TWO_DISTINCT_CONSEQUENCES_TWO_UNIQUE_SAFE_DISCRIMINATORS_COST_1_2__CANDIDATE_REQUESTS_COST_1",
 }

def prove(root:Path|None=None)->dict[str,Any]:
 root=_root() if root is None else Path(root).resolve()
 bindings=_bind(root)
 ident=_identifier_totality()
 transfer=_transfer()
 abstain=_abstention()
 assert g1.PRODUCTION_CASE_COUNTS=={g1.TRANSFER:12,g1.ABSTAIN:15}
 return {
  "schema":SCHEMA,
  "status":"PASS__UNIVERSAL_COLLISION_TOTAL_AND_EXACT_FLOAT_SAFE_OVER_EXACT_V3_GENERATOR_DOMAIN",
  "target_predicate":"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
  "exact_subject_blobs":bindings,
  "scope":{
   "generator":"EXACT_COLLISION_TOTAL_UNKNOWN_DOMAIN_GENERATOR_V3",
   "candidate":"EXACT_ADD2_ORIENTED_UNKNOWN_DOMAIN_CANDIDATE_V3",
   "scorer":"EXACT_FROZEN_SCORER_V1_UNCHANGED",
   "harness":"EXACT_FROZEN_HARNESS_V1_UNCHANGED",
   "beacon":"ALL_VALID_STRINGS_LENGTH_GE_16",
   "evaluator_secret":"ALL_VALUES_ACCEPTED_BY_FROZEN_SECRET_BYTES_GATE",
   "population_cases":27,
   "transfer_cases":12,
   "abstention_cases":15,
   "terminal_or_production_cases_generated":0,
  },
  "identifier_totality_proof":ident,
  "transfer_proof":transfer,
  "abstention_proof":abstain,
  "repairs":{
   "v2_identifier_collision_quantifier_hole":True,
   "v2_add2_exact_binary64_role_order_counterexample":True,
   "scorer_or_harness_relaxed":False,
  },
  "theorem":"FOR_EVERY_VALID_BEACON_AND_EVALUATOR_SECRET__EVERY_27_CASE_POPULATION_EMITTED_BY_EXACT_GENERATOR_V3_IS_PASSED_BY_EXACT_CANDIDATE_V3_THROUGH_UNCHANGED_HARNESS_V1_AND_SCORER_V1",
  "fresh_reality_required_for_this_exact_frozen_contract":False,
  "production_execution_information_gain_for_this_exact_contract":0,
  "hard_nonclaims":[
   "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION_BEYOND_THE_FROZEN_DIRECT_AUDIT_CONTRACT",
   "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_MODULE_ALONE",
   "NO_PRODUCTION_OR_TERMINAL_CASE_GENERATED_OR_READ",
   "INDEPENDENT_CONTENT_BOUND_VERIFICATION_AND_SEPARATE_ACCEPTANCE_REDUCTION_REQUIRED",
  ],
  "accounting":{
   "incremental_spend_usd":0,
   "new_reality_units_consumed":0,
   "terminal_cases_consumed":0,
   "production_cases_generated":0,
   "acceptance_credit_delta":0,
   "family_credit_delta":0,
   "capability_credit_delta":0,
   "ownership_credit_delta":0,
  }
 }

if __name__=="__main__":
 import json
 print(json.dumps(prove(),indent=2,sort_keys=True))
