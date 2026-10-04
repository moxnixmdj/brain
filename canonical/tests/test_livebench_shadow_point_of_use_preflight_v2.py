import json
from pathlib import Path
from canonical.runtime.livebench_shadow_point_of_use_preflight_v2 import (
    expected_claim_ref, verify_point_of_use_preflight,
)

ROOT=Path(__file__).resolve().parents[2]
PLAN=ROOT/"canonical/governance/LIVEBENCH_IF_SHADOW_PREEXPOSURE_PLAN_V3.json"

def plan():
    return json.loads(PLAN.read_text())

def receipt():
    digest="a"*64
    return {
      "lease_digest_sha256":digest,
      "claim_ref":expected_claim_ref(digest),
      "claim_ref_absent_observed":True,
      "case_reveal_has_occurred":False,
      "execution_has_started":False,
      "evaluation_output_exists":False,
      "paid_external_model_or_api_used":False,
      "paid_or_larger_runner_used":False,
      "public_standard_github_runner":True,
      "dependency_lock_install_pass":True,
      "candidate_runtime_import_pass":True,
      "response_adapter_import_pass":True,
      "scorer_import_pass":True,
      "synthetic_zero_case_smoke_pass":True,
      "candidate_component_hashes_match_plan":True,
      "harness_component_hashes_match_plan":True,
      "scorer_component_hashes_match_plan":True,
      "environment_component_hashes_match_plan":True,
      "policy_component_hashes_match_plan":True,
      "terminal_case_source_inaccessible":True,
      "write_only_escrow_contract_bound":True,
      "workflow_control_contract_bound":True,
      "zero_incremental_spend_guard_pass":True,
      "resource_truth_repair":{
        "path":"canonical/verification/LIVEBENCH_ZERO_CASE_RESOURCE_FIT_TRUTH_REPAIR_20261004_V1.json",
        "git_blob_sha":"8a603c1f48aad6e0fc79c2c76d2db437efde3893",
        "positive_run_id":37184530130,
        "positive_job_id":111383591914,
        "positive_run_conclusion":"success",
        "terminal_cases_consumed":0,
        "paid_external_model_or_api_used":False,
        "exact_scorer_import_pass":True,
        "astra_model_independent_synthetic_smoke":True,
      },
      "claim_backend_receipt":{
        "path":"canonical/governance/SHADOW_GIT_REF_ONE_USE_CLAIM_BACKEND_V1.json",
        "git_blob_sha":"b660e2ee70f42c7872a9b65c78198c5bdbf03609",
      },
    }

def test_successor_preflight_passes_without_reveal_authority():
    out=verify_point_of_use_preflight(plan(),receipt())
    assert out["point_of_use_preflight_pass"] is True
    assert out["terminal_cases_consumed"] == 0
    assert out["case_reveal_authority"] is False
    assert out["shadow_collection_authority"] is False
    assert out["one_use_claim_still_required"] is True
    assert out["acceptance_credit_authorized"] is False

def test_v3_plan_is_exact():
    assert plan()["plan_sha256"]=="9608157e7ef52fab08bc387bb19ccfb10001cbb5367849a9806d6b0e7df34b31"

def test_wrong_resource_truth_blob_blocks():
    r=receipt(); r["resource_truth_repair"]["git_blob_sha"]="0"*40
    out=verify_point_of_use_preflight(plan(),r)
    assert out["point_of_use_preflight_pass"] is False
    assert "RESOURCE_TRUTH_REPAIR_BLOB_MISMATCH" in out["reasons"]

def test_failed_resource_run_blocks():
    r=receipt(); r["resource_truth_repair"]["positive_run_conclusion"]="failure"
    assert verify_point_of_use_preflight(plan(),r)["point_of_use_preflight_pass"] is False

def test_claim_ref_must_be_digest_derived():
    r=receipt(); r["claim_ref"]="refs/heads/shadow-claims/wrong"
    out=verify_point_of_use_preflight(plan(),r)
    assert "CLAIM_REF_NOT_DERIVED_FROM_LEASE_DIGEST" in out["reasons"]

def test_any_case_exposure_blocks():
    r=receipt(); r["case_reveal_has_occurred"]=True
    assert verify_point_of_use_preflight(plan(),r)["point_of_use_preflight_pass"] is False

def test_failed_smoke_blocks():
    r=receipt(); r["synthetic_zero_case_smoke_pass"]=False
    assert verify_point_of_use_preflight(plan(),r)["point_of_use_preflight_pass"] is False

def test_wrong_claim_backend_blocks():
    r=receipt(); r["claim_backend_receipt"]["git_blob_sha"]="0"*40
    out=verify_point_of_use_preflight(plan(),r)
    assert "CLAIM_BACKEND_BLOB_MISMATCH" in out["reasons"]
