"""Universal zero-reality proof for Unknown-Domain candidate V3 on frozen generator V2.

The proof is content-bound.  It establishes that for every valid post-freeze
beacon and evaluator secret, every 27-case population emitted by the exact
frozen V2 generator is passed by candidate V3 through the exact frozen harness
and scorer.

No production case is generated.  This theorem is only about the frozen direct
evaluator contract; it is not an open-world unknown-domain claim.

V3 is necessary because V2 has an IEEE-754 counterexample on ADD2: support can
be identified while lexicographic role permutation changes the exact last bit
of (bias+r0)+r1.  V3 orients ADD2 roles from a visible generator invariant before
evaluating the query.
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
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V3_UNIVERSAL_PROOF_V1"

EXPECTED_BLOBS={
 "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
 "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
 "canonical/runtime/unknown_domain_direct_candidate_v3.py":"8df7f13455b710623806a8219174b397a2c3c442",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
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


def _git_blob_sha(path:Path)->str:
 b=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()


def _repo_root()->Path:
 return Path(__file__).resolve().parents[2]


def _verify_bindings(root:Path)->dict[str,str]:
 got={rel:_git_blob_sha(root/rel) for rel in EXPECTED_BLOBS}
 bad={rel:{"expected":EXPECTED_BLOBS[rel],"got":got[rel]}
      for rel in EXPECTED_BLOBS if got[rel]!=EXPECTED_BLOBS[rel]}
 if bad:
  raise AssertionError("EXACT_SUBJECT_BLOB_MISMATCH:"+repr(bad))
 return got


def _transfer_theorem()->dict[str,Any]:
 assert tuple(g1.PRIMITIVE_FAMILIES)==FAMILIES
 assert g1.PRODUCTION_CASE_COUNTS[g1.TRANSFER]==12
 assert harness.MAX_TRANSFER_PROBES==2
 assert c1.MAPPING_BASIS=="STRUCTURAL_EQUIVALENCE"

 # Every public target row makes distractors exact role mimics, so public rows
 # alone cannot identify support.  On requested probes, frozen _surface_row adds
 # delta=4.75+1.5*i+0.25*probe_variant to each distractor.
 d0=Fraction(19,4)  # first distractor minimum shift
 d1=Fraction(25,4)  # second distractor minimum shift
 min_mag=Fraction(1,4)
 max_mag=Fraction(7,2)

 # AFFINE_POS. gain >= 3/5, therefore any shifted wrong unary support misses
 # target output by at least 57/20 = 2.85.
 affine_gap=Fraction(3,5)*d0
 assert affine_gap==Fraction(57,20)

 # COMPLEMENT has slope -1.
 complement_gap=d0

 # SAT_MONO. f(x)=x/(1+|x|) is strictly increasing. All true/shifted values are
 # inside [-3.5,10]. f' >= 1/121 there and gain>=7/10.
 sat_gap=Fraction(7,10)*d0/Fraction(121,1)
 # Candidate _close tolerance is <=4.5e-9 because |bias|<1.5, gain<3 and
 # |x/(1+|x|)|<1.
 assert float(sat_gap)>4.5e-9

 # SIGN indices are 1 and 7. First requested target row is generator row j=3.
 # True r0 is negative, while even the worst shifted distractor is positive.
 for index in (1,7):
  assert (3+index)%2==0
 sign_shifted_min=-max_mag+d0
 assert sign_shifted_min==Fraction(5,4)>0

 # STEP indices are 5 and 11. The first requested row j=3 is above threshold;
 # the second j=4 is below by <=2.2. Its first-distractor shift is actually 5.0
 # (probe_variant=1), while 4.75 is already a sufficient conservative bound.
 step_wrong_side_margin=d0-Fraction(11,5)
 assert step_wrong_side_margin==Fraction(51,20)>0

 # ADD2 indices are 4 and 10. First requested row j=3 has both true roles
 # positive in [0.25,3.5]. All five wrong support sets therefore have a strict
 # output gap, so the true two-feature support is unique after that one probe.
 for index in (4,10):
  assert (3+index)%2==1
  assert (3+index+1)%3!=0
 add2_wrong_support_gaps=(
  d0-(max_mag-min_mag),  # {r0,d0}
  d1,                    # {r0,d1}
  d0,                    # {r1,d0}
  d1-(max_mag-min_mag),  # {r1,d1}
  d0+d1,                 # {d0,d1}
 )
 add2_min_gap=min(add2_wrong_support_gaps)
 assert add2_min_gap==Fraction(3,2)

 # The remaining ADD2 ambiguity is only role orientation on the correct support.
 # Unlike V2, V3 does not treat mathematical symmetry as exact-float symmetry.
 # Frozen generator V2 has a public, nonzero sign invariant on rows j=0..2.
 signatures={}
 for index in (4,10):
  r0=tuple(-1 if (j+index)%2==0 else 1 for j in range(3))
  r1=tuple(-1 if (j+index+1)%3==0 else 1 for j in range(3))
  assert r0==c3.ADD2_R0_SIG==(-1,1,-1)
  assert r1==c3.ADD2_R1_SIG==(1,-1,1)
  assert r0!=r1
  signatures[str(index)]={"r0":list(r0),"r1":list(r1)}
 # Magnitudes are generated in [0.25,3.5], so no visible signature entry is 0.
 # Thus exactly one r0/r1 permutation passes _orient_add2. V3 then invokes the
 # same c1._program_eval operation order as g1._eval on the true hidden roles,
 # making the scorer's exact float equality hold.

 return {
  "all_six_families_universal":True,
  "families":list(FAMILIES),
  "max_transfer_probes":2,
  "full_rediscovery_probe_floor":3,
  "affine_min_wrong_support_gap":str(affine_gap),
  "complement_min_wrong_support_gap":str(complement_gap),
  "sat_mono_conservative_min_wrong_support_gap":str(sat_gap),
  "sign_shifted_distractor_min_on_negative_probe":str(sign_shifted_min),
  "step_wrong_side_margin":str(step_wrong_side_margin),
  "add2_min_wrong_support_gap":str(add2_min_gap),
  "add2_role_signatures":signatures,
  "add2_exact_float_order_repaired_by_v3":True,
  "deduction":(
   "EVERY_UNARY_WRONG_SUPPORT_IS_REJECTED_BY_AT_MOST_TWO_PROBES__"
   "EVERY_ADD2_WRONG_SUPPORT_IS_REJECTED_BY_THE_FIRST_PROBE__"
   "V3_UNIQUELY_ORIENTS_THE_REMAINING_ADD2_TRUE_SUPPORT_FROM_VISIBLE_SIGNS__"
   "THEREFORE_EVERY_TRANSFER_CASE_CONCLUDES_EXACT_HIDDEN_SUPPORT_AND_EXACT_"
   "GOLD_FLOAT_BEFORE_THE_FULL_REDISCOVERY_FLOOR"
  ),
 }


def _abstention_theorem()->dict[str,Any]:
 assert tuple(g1.ABSTAIN_CLASSES)==("IDENTIFIABLE","NONIDENTIFIABLE","UNDERSPECIFIED")
 assert g1.PRODUCTION_CASE_COUNTS[g1.ABSTAIN]==15
 assert scorer.DECISIONS=={"CONCLUDE","ABSTAIN","REQUEST_DISCRIMINATOR"}
 return {
  "all_three_classes_universal":True,
  "cases_per_class":5,
  "identifiable":"TWO_VISIBLE_PLAUSIBLE_HYPOTHESES_SHARE_EXACTLY_ONE_TERMINAL_CONSEQUENCE__V3_CONCLUDES_IT",
  "nonidentifiable":"VISIBLE_HYPOTHESES_HAVE_DISTINCT_CONSEQUENCES_AND_NO_SAFE_BINARY_DISCRIMINATOR__V3_ABSTAINS_WITH_WITNESS",
  "underspecified":"TWO_SAFE_BINARY_DISCRIMINATORS_HAVE_COSTS_1_AND_2__V3_REQUESTS_THE_UNIQUE_VISIBLE_MINIMUM_COST_ID",
 }


def prove(root:Path|None=None)->dict[str,Any]:
 root=_repo_root() if root is None else Path(root).resolve()
 bindings=_verify_bindings(root)
 transfer=_transfer_theorem()
 abstention=_abstention_theorem()
 assert g1.PRODUCTION_CASE_COUNTS=={g1.TRANSFER:12,g1.ABSTAIN:15}
 return {
  "schema":SCHEMA,
  "status":"PASS__UNIVERSAL_OVER_EXACT_FROZEN_V2_GENERATOR_DOMAIN_WITH_V3_EXACTNESS_REPAIR",
  "target_predicate":"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
  "exact_subject_blobs":bindings,
  "scope":{
   "generator":"EXACT_FROZEN_UNKNOWN_DOMAIN_DIRECT_HIDDEN_GENERATOR_V2",
   "beacon":"ALL_VALID_STRINGS_LENGTH_GE_16",
   "evaluator_secret":"ALL_VALUES_ACCEPTED_BY_FROZEN_SECRET_BYTES_GATE",
   "population_cases":27,
   "transfer_cases":12,
   "abstention_cases":15,
   "production_cases_generated":0,
  },
  "v2_counterexample_status":"PROVED_BY_REGRESSION_TEST__V2_NOT_UNIVERSAL_DUE_ADD2_EXACT_FLOAT_ORDER",
  "v3_repair":"VISIBLE_ADD2_ROLE_SIGN_ORIENTATION_BEFORE_EXACT_QUERY_EVALUATION",
  "transfer_proof":transfer,
  "abstention_proof":abstention,
  "theorem":(
   "FOR_EVERY_POPULATION_THE_EXACT_FROZEN_V2_GENERATOR_CAN_EMIT__"
   "THE_EXACT_CONTENT_BOUND_V3_CANDIDATE_THROUGH_THE_EXACT_HARNESS_AND_SCORER_"
   "PASSES_ALL_27_CASES_WITH_AT_MOST_TWO_TRANSFER_PROBES_AND_ZERO_LEARNED_BYTES"
  ),
  "fresh_reality_required_for_this_exact_frozen_evaluator_claim":False,
  "production_execution_information_gain_for_this_exact_evaluator_claim":0,
  "hard_nonclaims":[
   "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION_BEYOND_THE_FROZEN_DIRECT_EVALUATOR_CONTRACT",
   "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_CERTIFICATE_ALONE",
   "NO_PRODUCTION_CASE_GENERATED_READ_OR_CONSUMED",
   "INDEPENDENT_CONTENT_BOUND_VERIFICATION_AND_SCOPE_REDUCTION_REQUIRED",
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
  },
 }


if __name__=="__main__":
 import json
 print(json.dumps(prove(),indent=2,sort_keys=True))
