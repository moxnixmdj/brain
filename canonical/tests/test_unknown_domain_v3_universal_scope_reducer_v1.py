from pathlib import Path
from canonical.runtime import unknown_domain_v3_universal_scope_reducer_v1 as r

def receipt():
 return {
  "schema":r.RECEIPT_SCHEMA,"repository":r.REPO,"pull_request":r.PR,
  "head_sha":r.HEAD_SHA,"run_id":r.RUN_ID,"job_id":r.JOB_ID,
  "conclusion":"success","workflow":"Isolated Unknown-Domain V3 universal verifier",
  "exact_subject_blobs":r.SUBJECT_BLOBS,"exact_content_binding_pass":True,
  "v2_counterexample_reproduced":True,"v3_same_counterexample_pass":True,
  "theorem_status":r.THEOREM_STATUS,"all_admissible_target_inputs_proved":True,
  "independent_population_count":1024,"independent_case_count":27648,
  "independent_all_cases_pass":True,"max_transfer_probes_observed":2,
  "production_cases_generated":0,"terminal_cases_consumed":0,
  "incremental_spend_usd":0,"acceptance_credit_delta":0,"promotion_authority":False,
 }

def test_pass_is_scope_only():
 out=r.reduce_receipt(receipt())
 assert out["pass"] is True
 assert out["generic_scope_compiler_verdict"]["scope_complete"] is True
 assert out["root3_new_scope_certificate_event_eligible"] is True
 assert out["delete_27_case_production_as_required_information_acquisition"] is True
 assert out["acceptance_credit_delta"]==out["family_credit_delta"]==0
 assert out["capability_credit_delta"]==out["ownership_credit_delta"]==0
 assert out["family_closure_inferred"] is False
 assert out["open_world_unknown_domain_claim"] is False

def test_identity_mismatch_fails():
 x=receipt();x["head_sha"]="bad"
 assert r.reduce_receipt(x)["pass"] is False
 x=receipt();x["run_id"]=1
 assert r.reduce_receipt(x)["pass"] is False

def test_verification_substance_required():
 x=receipt();x["v2_counterexample_reproduced"]=False
 assert r.reduce_receipt(x)["pass"] is False
 x=receipt();x["v3_same_counterexample_pass"]=False
 assert r.reduce_receipt(x)["pass"] is False
 x=receipt();x["independent_case_count"]=27647
 assert r.reduce_receipt(x)["pass"] is False

def test_no_reality_or_credit():
 x=receipt();x["production_cases_generated"]=1
 assert r.reduce_receipt(x)["pass"] is False
 x=receipt();x["acceptance_credit_delta"]=1
 assert r.reduce_receipt(x)["pass"] is False

def test_authority_drift_fails():
 assert r.reduce_receipt(receipt(),authority_errors=["DRIFT"])["pass"] is False

def test_current_authority_bytes():
 root=Path(__file__).resolve().parents[2]
 assert r.verify_current_authority_bytes(root)==[]
