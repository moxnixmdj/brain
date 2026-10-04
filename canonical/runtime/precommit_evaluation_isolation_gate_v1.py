"""Fail-closed precommit isolation gate for terminal empirical evaluation.

The gate checks whether an evaluation capsule is cryptographically frozen before any
terminal-case exposure and whether the executor cannot mutate the candidate or feed
terminal results back into it. Passing this gate DOES NOT authorize fresh reality,
does not prove benchmark equivalence, and grants zero acceptance credit. It only
produces a candidate eligibility fact for a separate benchmark-specific and global
authority adjudication.
"""
from __future__ import annotations

from typing import Any, Mapping

INPUT_SCHEMA = "PROJECT_BRAIN_PRECOMMIT_EVALUATION_ISOLATION_INPUT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_PRECOMMIT_EVALUATION_ISOLATION_OUTPUT_V1"
HEX = set("0123456789abcdef")

DIGEST_FIELDS = (
    "candidate_sha256",
    "harness_sha256",
    "scorer_sha256",
    "environment_sha256",
    "policy_sha256",
    "benchmark_contract_sha256",
)


def _sha256(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 64 and set(v.lower()) <= HEX


def _sha40(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 40 and set(v.lower()) <= HEX


def _receipt(v: Any) -> bool:
    return (
        isinstance(v, Mapping)
        and isinstance(v.get("path"), str)
        and bool(v.get("path"))
        and _sha40(v.get("git_blob_sha"))
    )


def _verified_block(v: Any, label: str) -> tuple[Mapping[str, Any] | None, list[str]]:
    if not isinstance(v, Mapping):
        return None, [f"{label}_REQUIRED"]
    errors: list[str] = []
    if v.get("verified") is not True:
        errors.append(f"{label}_VERIFIED_REQUIRED")
    if v.get("independent") is not True:
        errors.append(f"{label}_INDEPENDENT_REQUIRED")
    if not _receipt(v.get("receipt")):
        errors.append(f"{label}_RECEIPT_NOT_CONTENT_ADDRESSED")
    return v, errors


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": OUTPUT_SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "isolation_preconditions_proved": False,
        "parallel_execution_eligible_candidate": False,
        "benchmark_equivalence_proved": False,
        "global_fresh_reality_gate_overridden": False,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "new_reality_units_consumed": 0,
    }


def evaluate_isolation(doc: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
        return _fail("SCHEMA_INVALID")

    capsule = doc.get("capsule")
    if not isinstance(capsule, Mapping):
        return _fail("CAPSULE_REQUIRED")

    errors: list[str] = []
    for field in DIGEST_FIELDS:
        if not _sha256(capsule.get(field)):
            errors.append(f"CAPSULE_{field.upper()}_INVALID")
    if capsule.get("frozen") is not True:
        errors.append("CAPSULE_FROZEN_REQUIRED")

    commitment, e = _verified_block(doc.get("commitment"), "COMMITMENT")
    errors += e
    runner, e = _verified_block(doc.get("runner"), "RUNNER")
    errors += e
    leakage, e = _verified_block(doc.get("leakage_controls"), "LEAKAGE_CONTROLS")
    errors += e
    invalidation, e = _verified_block(doc.get("invalidation"), "INVALIDATION")
    errors += e

    if errors:
        return _fail(*errors)

    assert commitment is not None
    assert runner is not None
    assert leakage is not None
    assert invalidation is not None

    residual: list[str] = []

    bound = commitment.get("bound_digests")
    if not isinstance(bound, Mapping):
        residual.append("COMMITMENT_BOUND_DIGESTS_REQUIRED")
    else:
        for field in DIGEST_FIELDS:
            if bound.get(field) != capsule.get(field):
                residual.append(f"COMMITMENT_DIGEST_MISMATCH:{field}")

    required_true = {
        "COMMITMENT": (
            commitment,
            (
                "committed_before_terminal_case_access",
                "commitment_append_only",
            ),
        ),
        "RUNNER": (
            runner,
            (
                "read_only_inputs",
                "candidate_write_disabled",
                "harness_write_disabled",
                "scorer_write_disabled",
                "outputs_separate_from_candidate_state",
                "executor_identity_independent",
            ),
        ),
        "INVALIDATION": (
            invalidation,
            (
                "any_digest_change_invalidates",
                "post_commit_candidate_change_invalidates",
                "retry_requires_new_commitment",
                "case_access_before_commitment_invalidates",
            ),
        ),
    }
    for label, (block, fields) in required_true.items():
        for field in fields:
            if block.get(field) is not True:
                residual.append(f"{label}_{field.upper()}_REQUIRED")

    required_false = (
        "terminal_cases_exposed_before_commitment",
        "score_feedback_to_candidate",
        "adaptive_retry_on_terminal_case_content",
        "mutable_external_memory_shared_with_candidate",
    )
    for field in required_false:
        if leakage.get(field) is not False:
            residual.append(f"LEAKAGE_CONTROLS_{field.upper()}_MUST_BE_FALSE")

    network_policy = leakage.get("candidate_network_egress_policy")
    if network_policy not in {"DISABLED", "PINNED_ALLOWLIST"}:
        residual.append("LEAKAGE_CONTROLS_CANDIDATE_NETWORK_EGRESS_POLICY_INVALID")

    proved = not residual
    status = (
        "ISOLATION_PRECONDITIONS_PROVED__SEPARATE_AUTHORITY_STILL_REQUIRED"
        if proved
        else "ISOLATION_PRECONDITIONS_OPEN"
    )

    return {
        "schema": OUTPUT_SCHEMA,
        "status": status,
        "errors": [],
        "isolation_preconditions_proved": proved,
        "parallel_execution_eligible_candidate": proved,
        "residual": sorted(residual),
        "capsule_digests": {field: capsule[field] for field in DIGEST_FIELDS},
        "receipt_bindings": {
            "commitment": dict(commitment["receipt"]),
            "runner": dict(runner["receipt"]),
            "leakage_controls": dict(leakage["receipt"]),
            "invalidation": dict(invalidation["receipt"]),
        },
        "benchmark_equivalence_proved": False,
        "global_fresh_reality_gate_overridden": False,
        "rule": (
            "PASS_PROVES_ONLY_PRECOMMIT_ANTI_LEAKAGE_PRECONDITIONS__BENCHMARK_SPECIFIC_"
            "COMPARABILITY_AND_GLOBAL_FRESH_REALITY_AUTHORITY_REMAIN_SEPARATE_MANDATORY_GATES"
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "new_reality_units_consumed": 0,
    }
