import json
from pathlib import Path

from canonical.runtime.livebench_shadow_atomic_claim_transaction_v1 import (
    CLAIM_SCHEMA,
    preflight_binding_sha256,
    verify_atomic_claim_transaction,
)
from canonical.runtime.livebench_shadow_point_of_use_preflight_v1 import expected_claim_ref

ROOT=Path(__file__).resolve().parents[2]
PLAN=ROOT/"canonical/governance/LIVEBENCH_IF_SHADOW_PREEXPOSURE_PLAN_V2.json"

def plan():
    return json.loads(PLAN.read_text())

def preflight_receipt():
    digest="a"*64
    return {
      "lease_digest_sha256":digest,
      "claim_ref":expected_claim_ref(digest),
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

def activation():
    return {
      "schema":"PROJECT_BRAIN_SHADOW_REALITY_COLLECTION_ACTIVATION_V2",
      "benchmark_id":"LIVEBENCH_IF_2026_06_25",
      "target_predicate":"LIVEBENCH_IF_GE_65_7",
      "active":True,
      "shadow_collection_authority":True,
      "independent_verification_pass":True,
      "zero_incremental_spend_only":True,
      "write_only_escrow_only":True,
      "two_phase_isolation_protocol_required":True,
      "durable_one_use_claim_backend_verified":True,
      "point_of_use_preflight_required":True,
      "post_execution_isolation_receipt_required":True,
      "global_fresh_reality_authority":False,
      "acceptance_credit_authority":False,
      "promotion_authority":False,
      "independent_verification_receipt":{"path":"x","git_blob_sha":"1"*40},
      "claim_backend_verification_receipt":{"path":"y","git_blob_sha":"2"*40},
    }

def claim(p,r):
    ref=r["claim_ref"]
    return {
      "schema":CLAIM_SCHEMA,
      "claim_ref":ref,
      "create_http_status":201,
      "reference_created":True,
      "response_ref":ref,
      "response_object_sha":"3"*40,
      "preflight_binding_sha256":preflight_binding_sha256(p,r),
      "case_reveal_has_occurred_before_claim":False,
      "execution_has_started_before_claim":False,
      "evaluation_output_exists_before_claim":False,
      "claim_uniqueness_source":"ATOMIC_CREATE_RESPONSE",
    }

def test_atomic_201_is_only_transition_that_grants_reveal():
    p=plan(); r=preflight_receipt()
    out=verify_atomic_claim_transaction(
        plan=p,preflight_receipt=r,activation_receipt=activation(),claim_receipt=claim(p,r))
    assert out["atomic_claim_transaction_pass"] is True
    assert out["case_reveal_authority"] is True
    assert out["shadow_collection_authority"] is True
    assert out["authority_scope"]=="THIS_EXACT_LEASE_ONLY"
    assert out["global_fresh_reality_authority"] is False
    assert out["acceptance_credit_authorized"] is False
    assert out["claim_ref_absence_precheck_required"] is False

def test_no_absence_precheck_field_is_needed():
    p=plan(); r=preflight_receipt()
    assert "claim_ref_absent_observed" not in r
    out=verify_atomic_claim_transaction(
        plan=p,preflight_receipt=r,activation_receipt=activation(),claim_receipt=claim(p,r))
    assert out["atomic_claim_transaction_pass"] is True

def test_duplicate_or_failed_create_never_grants_reveal():
    p=plan(); r=preflight_receipt(); c=claim(p,r)
    c["create_http_status"]=422
    c["reference_created"]=False
    out=verify_atomic_claim_transaction(
        plan=p,preflight_receipt=r,activation_receipt=activation(),claim_receipt=c)
    assert out["atomic_claim_transaction_pass"] is False
    assert out["case_reveal_authority"] is False
    assert out["shadow_collection_authority"] is False

def test_activation_is_still_mandatory():
    p=plan(); r=preflight_receipt(); a=activation(); a["active"]=False
    out=verify_atomic_claim_transaction(
        plan=p,preflight_receipt=r,activation_receipt=a,claim_receipt=claim(p,r))
    assert out["atomic_claim_transaction_pass"] is False
    assert out["case_reveal_authority"] is False

def test_preflight_failure_blocks_claim_authority():
    p=plan(); r=preflight_receipt(); r["synthetic_zero_case_smoke_pass"]=False
    out=verify_atomic_claim_transaction(
        plan=p,preflight_receipt=r,activation_receipt=activation(),claim_receipt=claim(p,r))
    assert out["atomic_claim_transaction_pass"] is False

def test_claim_must_bind_exact_preflight():
    p=plan(); r=preflight_receipt(); c=claim(p,r)
    c["preflight_binding_sha256"]="0"*64
    out=verify_atomic_claim_transaction(
        plan=p,preflight_receipt=r,activation_receipt=activation(),claim_receipt=c)
    assert out["atomic_claim_transaction_pass"] is False

def test_case_reveal_before_claim_fails_closed():
    p=plan(); r=preflight_receipt(); c=claim(p,r)
    c["case_reveal_has_occurred_before_claim"]=True
    out=verify_atomic_claim_transaction(
        plan=p,preflight_receipt=r,activation_receipt=activation(),claim_receipt=c)
    assert out["atomic_claim_transaction_pass"] is False
