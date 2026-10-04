"""LiveBench shadow V2 point-of-use preflight.

Zero-case only. This verifier establishes whether the repaired exact LiveBench
execution tuple is ready to ATTEMPT the durable one-use claim.

It deliberately does not pre-read whether the claim ref exists. The Git ref
create operation is the atomic uniqueness test. A separate check-then-create
sequence would introduce a race and an unnecessary API call.

This verifier never grants case-reveal authority. That remains exclusively a
successful atomic claim under a separately verified activation.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.pre_exposure_isolation_plan_v1 import verify_pre_exposure_plan

SCHEMA="PROJECT_BRAIN_LIVEBENCH_SHADOW_POINT_OF_USE_PREFLIGHT_V1"
EXPECTED_PLAN_SHA256="7165f9308cc2429cb56a4a3a0a6f2fd6abba655ad9491df93bd9241691ec2b0f"
CLAIM_BACKEND_PATH="canonical/governance/SHADOW_GIT_REF_ONE_USE_CLAIM_BACKEND_V1.json"
CLAIM_BACKEND_BLOB="b660e2ee70f42c7872a9b65c78198c5bdbf03609"
RESOURCE_FIT_RECEIPT_PATH="canonical/verification/LIVEBENCH_ZERO_CASE_RESOURCE_FIT_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
RESOURCE_FIT_RECEIPT_BLOB="667943c418a434988d915bfb2ac736679af3bf7b"
HEX=set("0123456789abcdef")

def _sha256(x: Any) -> bool:
    return isinstance(x,str) and len(x)==64 and set(x.lower()) <= HEX

def expected_claim_ref(lease_digest_sha256: str) -> str:
    if not _sha256(lease_digest_sha256):
        raise ValueError("INVALID_LEASE_DIGEST_SHA256")
    return "refs/heads/shadow-claims/" + lease_digest_sha256.lower()

def _verify_pointer(value: Any, path: str, blob: str, missing: str, mismatch: str, reasons: list[str]) -> None:
    if not isinstance(value,Mapping):
        reasons.append(missing)
        return
    if value.get("path") != path or value.get("git_blob_sha") != blob:
        reasons.append(mismatch)

def verify_point_of_use_preflight(
    plan: Mapping[str,Any],
    receipt: Mapping[str,Any],
) -> dict[str,Any]:
    reasons=[]
    pv=verify_pre_exposure_plan(plan)
    if pv.get("pre_exposure_plan_pass") is not True:
        reasons.append("PRE_EXPOSURE_PLAN_NOT_PROVED")
    if plan.get("plan_sha256") != EXPECTED_PLAN_SHA256:
        reasons.append("LIVEBENCH_PLAN_SHA256_MISMATCH")

    lease_digest=receipt.get("lease_digest_sha256")
    try:
        expected_ref=expected_claim_ref(lease_digest)
    except ValueError:
        expected_ref=""
        reasons.append("INVALID_LEASE_DIGEST_SHA256")

    if receipt.get("claim_ref") != expected_ref:
        reasons.append("CLAIM_REF_NOT_DERIVED_FROM_LEASE_DIGEST")

    required_false=(
      "case_reveal_has_occurred",
      "execution_has_started",
      "evaluation_output_exists",
      "paid_external_model_or_api_used",
      "paid_or_larger_runner_used",
    )
    for field in required_false:
        if receipt.get(field) is not False:
            reasons.append("PREFLIGHT_FALSE_GATE_FAILED:"+field)

    required_true=(
      "public_standard_github_runner",
      "dependency_lock_install_pass",
      "candidate_runtime_import_pass",
      "response_adapter_import_pass",
      "scorer_import_pass",
      "synthetic_zero_case_smoke_pass",
      "candidate_component_hashes_match_plan",
      "harness_component_hashes_match_plan",
      "scorer_component_hashes_match_plan",
      "environment_component_hashes_match_plan",
      "policy_component_hashes_match_plan",
      "terminal_case_source_inaccessible",
      "write_only_escrow_contract_bound",
      "workflow_control_contract_bound",
      "zero_incremental_spend_guard_pass",
    )
    for field in required_true:
        if receipt.get(field) is not True:
            reasons.append("PREFLIGHT_TRUE_GATE_FAILED:"+field)

    _verify_pointer(
        receipt.get("claim_backend_receipt"),
        CLAIM_BACKEND_PATH, CLAIM_BACKEND_BLOB,
        "CLAIM_BACKEND_RECEIPT_MISSING", "CLAIM_BACKEND_RECEIPT_MISMATCH", reasons)
    _verify_pointer(
        receipt.get("resource_fit_verification_receipt"),
        RESOURCE_FIT_RECEIPT_PATH, RESOURCE_FIT_RECEIPT_BLOB,
        "RESOURCE_FIT_RECEIPT_MISSING", "RESOURCE_FIT_RECEIPT_MISMATCH", reasons)

    passed=not reasons
    return {
      "schema":SCHEMA,
      "point_of_use_preflight_pass":passed,
      "reasons":sorted(set(reasons)),
      "expected_claim_ref":expected_ref,
      "claim_ref_absence_precheck_required":False,
      "resource_fit_receipt_bound":passed,
      "terminal_cases_consumed":0,
      "case_reveal_authority":False,
      "shadow_collection_authority":False,
      "global_fresh_reality_authority":False,
      "acceptance_credit_authorized":False,
      "promotion_authority":False,
      "one_use_claim_still_required":True,
    }
