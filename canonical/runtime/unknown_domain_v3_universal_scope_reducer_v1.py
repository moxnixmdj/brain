"""Outcome-blind reducer from independent V3 verification to a Root3 scope certificate.

Frozen before the independent verifier outcome. This module cannot award
performance, family, capability, ownership, execution, promotion, or fresh
reality authority. It can only turn one exact independently successful V3
verification receipt into one exact frozen-domain scope certificate accepted by
the already-verified generic scope compiler.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.universal_scope_closure_compiler_v1 import evaluate

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_V3_SCOPE_REDUCER_V1"
RECEIPT_SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_V3_UNIVERSAL_PUBLIC_VERIFICATION_V1"
TARGET_PREDICATE="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
TARGET_SCOPE="scope://opus55/UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT/exact-frozen-v2-generator-domain"
REPO="moxnixmdj/verification-capsule-runner"
PR=2084
HEAD_SHA="de3ee589483bdbefbdb6cc784cdb7abc4a04d52c"
RUN_ID=37241499647
JOB_ID=111550962798
THEOREM_STATUS="PASS__UNIVERSAL_OVER_EXACT_FROZEN_V2_GENERATOR_DOMAIN_WITH_V3_EXACTNESS_REPAIR"

SUBJECT_BLOBS={
 "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
 "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
 "canonical/runtime/unknown_domain_direct_candidate_v3.py":"8df7f13455b710623806a8219174b397a2c3c442",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
 "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
 "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
 "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
 "canonical/runtime/unknown_domain_direct_v3_universal_proof_v1.py":"ee5f3832fdbad5ae645b0626e9f39ebeaee2b1da",
 "canonical/tests/test_unknown_domain_direct_candidate_v3.py":"1317f7143d0b9103bdebc817fd0b057cc9bcd43b",
 "canonical/tests/test_unknown_domain_direct_v3_universal_proof_v1.py":"f1fa117edaf1f10401f4d33a6f78b815fa02c073",
}

AUTHORITY_BLOBS={
 "canonical/runtime/universal_scope_closure_compiler_v1.py":"b208255789b14e44e86c82c196e06b5c41b3d039",
 "canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V2.json":"4d8ce78ebe312100bbfc524062199961c0c6479d",
 "canonical/governance/ROOT3_UNIVERSAL_SCOPE_CLOSURE_ACTIVATION_V1.json":"4cb0d963aa11205063d0119d9ae8fdb625f80e3c",
 "canonical/governance/ROOT3_SCOPE_CERTIFICATE_ADMISSIBILITY_REFINEMENT_ACTIVATION_V2.json":"a9bff5074dbb456d673131c60f30efa88a337670",
 "canonical/governance/UNKNOWN_DOMAIN_TRANSFER_ABSTENTION_DIRECT_PROOF_PROTOCOL_V1.json":"fd586455d582c38c7062ffe735f86cb9f2e803ab",
 "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EVALUATOR_FAMILY_V1.json":"52090daf78d12020af48c1b6ffaea056d9029e1b",
}


def _blob(path: Path)->str:
 b=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()


def verify_current_authority_bytes(root: Path)->list[str]:
 errors=[]
 for rel,want in AUTHORITY_BLOBS.items():
  p=root/rel
  if not p.is_file():
   errors.append("AUTHORITY_FILE_MISSING:"+rel)
   continue
  got=_blob(p)
  if got!=want:
   errors.append("AUTHORITY_BLOB_DRIFT:"+rel+":"+got)
 return errors


def _zero()->dict[str,Any]:
 return {
  "acceptance_credit_delta":0,
  "family_credit_delta":0,
  "capability_credit_delta":0,
  "ownership_credit_delta":0,
  "new_reality_units_consumed":0,
  "production_cases_generated":0,
  "terminal_cases_consumed":0,
  "incremental_spend_usd":0,
  "execution_authority":False,
  "promotion_authority":False,
  "fresh_reality_authority":False,
 }


def fail(*errors:str)->dict[str,Any]:
 return {
  "schema":SCHEMA,
  "status":"FAIL_CLOSED",
  "pass":False,
  "errors":sorted(set(errors)),
  "scope_certificate":None,
  "root3_new_scope_certificate_event_eligible":False,
  "delete_27_case_production_as_required_information_acquisition":False,
  **_zero(),
 }


def reduce_receipt(receipt:Mapping[str,Any], *, authority_errors:list[str]|None=None)->dict[str,Any]:
 e=list(authority_errors or [])
 if not isinstance(receipt,Mapping):
  return fail(*(e+["RECEIPT_NOT_MAPPING"]))
 def req(cond:bool,code:str)->None:
  if not cond:e.append(code)

 req(receipt.get("schema")==RECEIPT_SCHEMA,"RECEIPT_SCHEMA_MISMATCH")
 req(receipt.get("repository")==REPO,"REPOSITORY_MISMATCH")
 req(receipt.get("pull_request")==PR,"PULL_REQUEST_MISMATCH")
 req(receipt.get("head_sha")==HEAD_SHA,"HEAD_SHA_MISMATCH")
 req(receipt.get("run_id")==RUN_ID,"RUN_ID_MISMATCH")
 req(receipt.get("job_id")==JOB_ID,"JOB_ID_MISMATCH")
 req(receipt.get("conclusion")=="success","INDEPENDENT_VERIFIER_NOT_SUCCESS")
 req(receipt.get("workflow")=="Isolated Unknown-Domain V3 universal verifier","WORKFLOW_MISMATCH")
 req(receipt.get("exact_subject_blobs")==SUBJECT_BLOBS,"EXACT_SUBJECT_BLOBS_MISMATCH")
 req(receipt.get("exact_content_binding_pass") is True,"EXACT_CONTENT_BINDING_NOT_PASS")
 req(receipt.get("v2_counterexample_reproduced") is True,"V2_COUNTEREXAMPLE_NOT_REPRODUCED")
 req(receipt.get("v3_same_counterexample_pass") is True,"V3_COUNTEREXAMPLE_REPAIR_NOT_PASS")
 req(receipt.get("theorem_status")==THEOREM_STATUS,"THEOREM_STATUS_MISMATCH")
 req(receipt.get("all_admissible_target_inputs_proved") is True,"UNIVERSAL_COMPLETENESS_NOT_PROVED")
 req(receipt.get("independent_population_count")==1024,"INDEPENDENT_POPULATION_COUNT_MISMATCH")
 req(receipt.get("independent_case_count")==27648,"INDEPENDENT_CASE_COUNT_MISMATCH")
 req(receipt.get("independent_all_cases_pass") is True,"INDEPENDENT_CASE_FALSIFICATION_FAILED")
 probes=receipt.get("max_transfer_probes_observed")
 req(isinstance(probes,int) and not isinstance(probes,bool) and probes<=2,"PROBE_BOUND_VIOLATED")
 req(receipt.get("production_cases_generated")==0,"PRODUCTION_CASES_GENERATED")
 req(receipt.get("terminal_cases_consumed")==0,"TERMINAL_CASES_CONSUMED")
 req(receipt.get("incremental_spend_usd")==0,"INCREMENTAL_SPEND_NONZERO")
 req(receipt.get("acceptance_credit_delta")==0,"VERIFIER_SELF_AWARDS_ACCEPTANCE")
 req(receipt.get("promotion_authority") is False,"VERIFIER_SELF_GRANTS_PROMOTION")
 if e:return fail(*e)

 premise="git-blobs:"+",".join(k+"="+SUBJECT_BLOBS[k] for k in sorted(SUBJECT_BLOBS))
 cert={
  "id":"UNKNOWN_DOMAIN_V3_EXACT_FROZEN_SCOPE_CERTIFICATE_V1",
  "target_scope_id":TARGET_SCOPE,
  "basis":"UNIVERSAL_FORMAL_SCOPE_PROOF",
  "verified":True,
  "independent":True,
  "scope_relation":"EXACT",
  "formal_completeness":True,
  "all_admissible_target_inputs_proved":True,
  "premise_set_id":premise,
 }
 compiled=evaluate(cert)
 if compiled.get("scope_complete") is not True:
  return fail("GENERIC_SCOPE_COMPILER_REJECTED")
 return {
  "schema":SCHEMA,
  "status":"PASS__EXACT_FROZEN_UNKNOWN_DOMAIN_SCOPE_CERTIFICATE_ELIGIBLE__ZERO_PERFORMANCE_CREDIT",
  "pass":True,
  "errors":[],
  "target_predicate":TARGET_PREDICATE,
  "target_scope_id":TARGET_SCOPE,
  "scope_certificate":cert,
  "generic_scope_compiler_verdict":compiled,
  "root3_event":"NEW_SCOPE_CERTIFICATE_EVENT",
  "root3_new_scope_certificate_event_eligible":True,
  "delete_27_case_production_as_required_information_acquisition":True,
  "production_information_gain_for_exact_frozen_scope":0,
  "family_closure_inferred":False,
  "open_world_unknown_domain_claim":False,
  "required_next_gate":"CURRENT_MAIN_ROOT3_SCOPE_REDUCTION_THEN_SEPARATE_ACCEPTANCE_FIXED_POINT_RECOMPUTATION",
  "hard_nonclaims":[
   "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION",
   "NO_PERFORMANCE_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_SCOPE_ALONE",
   "NO_FAMILY_CLOSURE_INFERRED_BY_THIS_REDUCER",
   "NO_FRESH_REALITY_AUTHORITY",
   "NO_RETIRED_76E8040D_LEASE_EXECUTION",
  ],
  **_zero(),
 }


def main()->int:
 import json,sys
 if len(sys.argv)!=2: raise SystemExit("usage: python -m canonical.runtime.unknown_domain_v3_universal_scope_reducer_v1 RECEIPT.json")
 root=Path(__file__).resolve().parents[2]
 receipt=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
 out=reduce_receipt(receipt,authority_errors=verify_current_authority_bytes(root))
 print(json.dumps(out,indent=2,sort_keys=True))
 return 0 if out.get("pass") else 1


if __name__=="__main__":raise SystemExit(main())
