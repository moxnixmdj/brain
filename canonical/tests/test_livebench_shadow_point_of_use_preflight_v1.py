import json
from pathlib import Path
from canonical.runtime.livebench_shadow_point_of_use_preflight_v1 import (
    expected_claim_ref,
    verify_point_of_use_preflight,
)

ROOT=Path(__file__).resolve().parents[2]
PLAN=ROOT/"canonical/governance/LIVEBENCH_IF_SHADOW_PREEXPOSURE_PLAN_V2.json"

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
      "claim_backend_receipt":{
        "path":"canonical/governance/SHADOW_GIT_REF_ONE_USE_CLAIM_BACKEND_V1.json",
        "git_blob_sha":"b660e2ee70f42c7872a9b65c78198c5bdbf03609",
      },
    }

def test_exact_zero_case_preflight_passes_without_reveal_authority():
    out=verify_point_of_use_preflight(plan(),receipt())
    assert out["point_of_use_preflight_pass"] is True
    assert out["terminal_cases_consumed"] == 0
    assert out["case_reveal_authority"] is False
    assert out["shadow_collection_authority"] is False
    assert out["one_use_claim_still_required"] is True
    assert out["acceptance_credit_authorized"] is False

def test_claim_ref_must_be_digest_derived():
    r=receipt(); r["claim_ref"]="refs/heads/shadow-claims/wrong"
    out=verify_point_of_use_preflight(plan(),r)
    assert out["point_of_use_preflight_pass"] is False
    assert "CLAIM_REF_NOT_DERIVED_FROM_LEASE_DIGEST" in out["reasons"]

def test_any_case_exposure_blocks_preflight():
    r=receipt(); r["case_reveal_has_occurred"]=True
    out=verify_point_of_use_preflight(plan(),r)
    assert out["point_of_use_preflight_pass"] is False

def test_failed_zero_case_smoke_blocks_preflight():
    r=receipt(); r["synthetic_zero_case_smoke_pass"]=False
    out=verify_point_of_use_preflight(plan(),r)
    assert out["point_of_use_preflight_pass"] is False

def test_wrong_claim_backend_blob_blocks_preflight():
    r=receipt(); r["claim_backend_receipt"]["git_blob_sha"]="0"*40
    out=verify_point_of_use_preflight(plan(),r)
    assert out["point_of_use_preflight_pass"] is False
    assert "CLAIM_BACKEND_BLOB_MISMATCH" in out["reasons"]
