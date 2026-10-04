"""Pre-exposure isolation plan verifier for shadow benchmark collection.

This verifier is deliberately PRE-execution. It proves only that the exact
committed components still match immediately before reveal and that the workflow
contains fail-closed controls which make terminal-case reveal conditional on a
separate one-use lease claim. It never accepts future case-reveal or execution
events as if they had already been observed.

Post-execution causal isolation remains a separate receipt checked by
generic_precommit_isolation_theorem_v1.verify_generic_isolation.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PRE_EXPOSURE_ISOLATION_PLAN_V1"
COMPONENTS = ("candidate", "harness", "scorer", "environment", "policy")
HEX = set("0123456789abcdef")


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value.lower()) <= HEX


def _sha40(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and set(value.lower()) <= HEX


def _receipt(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("path"), str)
        and bool(value.get("path"))
        and _sha40(value.get("git_blob_sha"))
    )


def commitment_digest(plan: Mapping[str, Any]) -> str:
    obj = {
        f"{c}_sha256": str(plan.get(f"{c}_sha256", "")).lower()
        for c in COMPONENTS
    }
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def plan_digest(plan: Mapping[str, Any]) -> str:
    obj = {k: v for k, v in plan.items() if k != "plan_sha256"}
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def verify_pre_exposure_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if not isinstance(plan, Mapping) or plan.get("schema") != SCHEMA:
        return {
            "schema": SCHEMA,
            "pre_exposure_plan_pass": False,
            "reasons": ["SCHEMA_MISMATCH"],
            "case_reveal_authority": False,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_authorized": False,
        }

    for component in COMPONENTS:
        committed = plan.get(f"{component}_sha256")
        observed = plan.get(f"pre_reveal_observed_{component}_sha256")
        if not _sha256(committed):
            reasons.append(f"INVALID_{component.upper()}_SHA256")
        if str(observed or "").lower() != str(committed or "").lower():
            reasons.append(f"PRE_REVEAL_{component.upper()}_DRIFT")

    if str(plan.get("commitment_sha256") or "").lower() != commitment_digest(plan):
        reasons.append("COMMITMENT_DIGEST_MISMATCH")
    if str(plan.get("plan_sha256") or "").lower() != plan_digest(plan):
        reasons.append("PLAN_DIGEST_MISMATCH")

    commit_seq = plan.get("commit_event_sequence")
    verify_seq = plan.get("pre_reveal_verification_event_sequence")
    if isinstance(commit_seq, bool) or not isinstance(commit_seq, int):
        reasons.append("INVALID_COMMIT_EVENT_SEQUENCE")
    if isinstance(verify_seq, bool) or not isinstance(verify_seq, int):
        reasons.append("INVALID_PRE_REVEAL_VERIFICATION_EVENT_SEQUENCE")
    if (
        isinstance(commit_seq, int)
        and not isinstance(commit_seq, bool)
        and isinstance(verify_seq, int)
        and not isinstance(verify_seq, bool)
        and not commit_seq < verify_seq
    ):
        reasons.append("PRE_REVEAL_VERIFICATION_NOT_AFTER_COMMIT")

    # Future events must explicitly not have happened yet.
    if plan.get("case_reveal_has_occurred") is not False:
        reasons.append("CASE_REVEAL_MUST_NOT_HAVE_OCCURRED")
    if plan.get("execution_has_started") is not False:
        reasons.append("EXECUTION_MUST_NOT_HAVE_STARTED")
    if plan.get("evaluation_output_exists") is not False:
        reasons.append("EVALUATION_OUTPUT_MUST_NOT_EXIST")

    required_true = (
        "independent_executor_bound",
        "committed_components_immutable",
        "candidate_mutation_blocked",
        "unrelated_work_mutation_blocked",
        "terminal_case_source_inaccessible_before_claim",
        "reveal_step_requires_verified_activation",
        "reveal_step_requires_verified_one_use_claim",
        "reveal_step_requires_point_of_use_preflight_pass",
        "outputs_bound_to_commitment_and_lease",
        "write_only_escrow_sink_bound",
        "result_read_blocked_until_zero_reality_fixed_point",
        "post_execution_isolation_receipt_mandatory",
        "fail_closed_on_any_component_drift",
    )
    for field in required_true:
        if plan.get(field) is not True:
            reasons.append(f"PLAN_GATE_FALSE:{field}")

    if not _receipt(plan.get("workflow_control_receipt")):
        reasons.append("WORKFLOW_CONTROL_RECEIPT_NOT_CONTENT_ADDRESSED")
    if not _receipt(plan.get("escrow_contract_receipt")):
        reasons.append("ESCROW_CONTRACT_RECEIPT_NOT_CONTENT_ADDRESSED")

    # A pre-exposure plan is not allowed to smuggle an already-observed future
    # event sequence into readiness.
    for forbidden in (
        "case_reveal_event_sequence",
        "execution_start_event_sequence",
        "evaluation_output_event_sequence",
        "observed_causal_edges",
    ):
        if forbidden in plan:
            reasons.append(f"FUTURE_EVENT_FIELD_FORBIDDEN_PRE_EXPOSURE:{forbidden}")

    passed = not reasons
    return {
        "schema": SCHEMA,
        "pre_exposure_plan_pass": passed,
        "reasons": sorted(set(reasons)),
        "commitment_sha256": plan.get("commitment_sha256"),
        "case_reveal_authority": False,
        "one_use_claim_still_required": True,
        "point_of_use_preflight_still_required": True,
        "post_execution_isolation_receipt_required": True,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_authorized": False,
    }
