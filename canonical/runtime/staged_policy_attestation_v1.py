"""Exact Stage-B / Stage-C policy attestation for TB4 execution authority.

This module is intentionally fail-closed. It binds execution-authority events to
the exact current PREQUALIFICATION_FAILURE_IMMUNITY_V1 staged-admission policy.

It does not grant execution, verification, acceptance, family, capability, or
ownership credit. It only rejects under-attested Stage-B passes and stale Stage-C
lease bindings.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_STAGE_POLICY_ATTESTATION_V1"
POLICY_SCHEMA = "PROJECT_BRAIN_PREQUALIFICATION_FAILURE_IMMUNITY_V1"
POLICY_PATH = "canonical/governance/PREQUALIFICATION_FAILURE_IMMUNITY_V1.json"

STAGE_B = "stage_b_post_exposure_pre_execution"
STAGE_C = "stage_c_execution"

STAGE_B_REQUIRED = (
    "TB4_STAGE_B_SOURCE_ALLOWLIST_ENFORCED",
    "EXHAUSTIVE_SOURCE_SENTENCE_ACCOUNTING",
    "CROSS_EXTRACTOR_SEMANTIC_CONSENSUS_OR_EXPLICIT_UNKNOWN",
    "COMPLETE_NORMALIZED_REQUIREMENT_GRAPH",
    "TASK_SPECIFIC_TEST_OBLIGATIONS",
    "INDEPENDENT_ACCEPTANCE_PLAN",
    "REQUIREMENT_MUTATION_COVERAGE",
    "VERIFIER_MUTATION_OR_SEEDED_FAILURE_MODE_COVERAGE",
    "TASK_SPECIFIC_FEASIBILITY_CERTIFICATE",
    "TASK_SPECIFIC_EXECUTION_SURFACE_PARITY_CERTIFICATE",
    "TASK_SPECIFIC_TOOL_AUTHORITY_AND_RESOURCE_PREFLIGHT",
    "TASK_SPECIFIC_SOURCE_BOUNDARY_PREFLIGHT",
    "POST_EXPOSURE_ZERO_DISCOVERY_SEARCH_RECEIPT",
    "LOSSLESS_SOURCE_CONTRACT_COMPILATION_RECEIPT",
    "ZERO_UNACCOUNTED_AUTHORITATIVE_SOURCE_ATOMS",
    "ZERO_OPEN_SPECIFICATION_HOLES",
    "BIDIRECTIONAL_SOURCE_REQUIREMENT_TRACEABILITY",
    "TASK_SPECIFIC_RUNTIME_API_CONTRACT_PREFLIGHT",
    "BUILDER_SEMANTIC_SUCCESS_CONTRACT",
    "DUAL_INDEPENDENT_SEMANTIC_SPAN_DECOMPOSITION",
    "SEMANTIC_BOUNDARY_CLASS_AND_FINGERPRINT_CONSENSUS",
    "COMPOUND_OBLIGATION_LOWER_BOUND_SATISFIED",
    "ZERO_RISKY_SOURCE_SPAN_GAPS",
    "OPERATIVE_SEMANTIC_UNIT_TO_REQUIREMENT_CLOSURE",
    "ZERO_OPEN_SEMANTIC_SPECIFICATION_HOLES",
)

STAGE_C_REQUIRED = (
    "IMMUTABLE_CANDIDATE_AND_PLAN_HASH",
    "LIVE_EXECUTOR_RECEIPT",
    "ARTIFACT_PATH_ROUNDTRIP",
    "ONE_SHOT_INDEPENDENT_TERMINAL_VERIFIER",
    "NO_POST_RESULT_RETUNING_FOR_SAME_TASK",
    "FULL_STATE_DERIVED_EXECUTION_AUTHORITY_V3_PASS",
    "TRANSITION_TIME_EXECUTION_AUTHORITY_TRUE",
    "BUILDER_SEMANTIC_SUCCESS_BEFORE_VERIFIER",
    "OUTPUT_FROZEN_BEFORE_VERIFIER",
    "TRANSITION_TIME_VERIFIER_AUTHORITY_TRUE",
)

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def required_items(stage: str) -> tuple[str, ...]:
    if stage == STAGE_B:
        return STAGE_B_REQUIRED
    if stage == STAGE_C:
        return STAGE_C_REQUIRED
    raise ValueError("UNKNOWN_STAGE")


def required_items_sha256(stage: str) -> str:
    return hashlib.sha256(_canonical_json(list(required_items(stage)))).hexdigest()


def _is_content_addressed_receipt(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    path = value.get("path")
    if not isinstance(path, str) or not path:
        return False
    blob = value.get("git_blob_sha")
    digest = value.get("sha256")
    return bool(
        (isinstance(blob, str) and _HEX40.fullmatch(blob))
        or (isinstance(digest, str) and _HEX64.fullmatch(digest))
    )


def validate_stage_b_attestation(evidence: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(evidence, Mapping):
        return ["STAGE_B_EVIDENCE_NOT_MAPPING"]
    att = evidence.get("policy_attestation")
    if not isinstance(att, Mapping):
        return ["STAGE_B_POLICY_ATTESTATION_MISSING"]
    if att.get("schema") != SCHEMA:
        errors.append("STAGE_B_ATTESTATION_SCHEMA")
    if att.get("policy_schema") != POLICY_SCHEMA:
        errors.append("STAGE_B_POLICY_SCHEMA")
    if att.get("policy_path") != POLICY_PATH:
        errors.append("STAGE_B_POLICY_PATH")
    if att.get("stage") != STAGE_B:
        errors.append("STAGE_B_STAGE_ID")
    if att.get("required_items_sha256") != required_items_sha256(STAGE_B):
        errors.append("STAGE_B_REQUIRED_ITEMS_DIGEST")

    passed = att.get("passed_items")
    if not isinstance(passed, list) or any(not isinstance(x, str) for x in passed):
        errors.append("STAGE_B_PASSED_ITEMS_INVALID")
        passed = []
    if len(passed) != len(set(passed)):
        errors.append("STAGE_B_PASSED_ITEMS_DUPLICATE")
    passed_set = set(passed)
    required_set = set(STAGE_B_REQUIRED)
    missing = sorted(required_set - passed_set)
    extra = sorted(passed_set - required_set)
    if missing:
        errors.extend("STAGE_B_ITEM_UNATTESTED:" + item for item in missing)
    if extra:
        errors.extend("STAGE_B_ITEM_UNKNOWN:" + item for item in extra)

    failed = att.get("failed_items")
    if not isinstance(failed, list):
        errors.append("STAGE_B_FAILED_ITEMS_INVALID")
    elif failed:
        errors.extend("STAGE_B_ITEM_FAILED:" + str(item) for item in failed)

    receipts = att.get("source_receipts")
    if not isinstance(receipts, Mapping):
        errors.append("STAGE_B_SOURCE_RECEIPTS_INVALID")
        receipts = {}
    for item in STAGE_B_REQUIRED:
        if not _is_content_addressed_receipt(receipts.get(item)):
            errors.append("STAGE_B_RECEIPT_MISSING_OR_UNPINNED:" + item)

    return sorted(set(errors))


def validate_stage_c_lease_binding(evidence: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(evidence, Mapping):
        return ["STAGE_C_LEASE_EVIDENCE_NOT_MAPPING"]
    binding = evidence.get("stage_c_policy_binding")
    if not isinstance(binding, Mapping):
        return ["STAGE_C_POLICY_BINDING_MISSING"]
    if binding.get("schema") != SCHEMA:
        errors.append("STAGE_C_BINDING_SCHEMA")
    if binding.get("policy_schema") != POLICY_SCHEMA:
        errors.append("STAGE_C_POLICY_SCHEMA")
    if binding.get("policy_path") != POLICY_PATH:
        errors.append("STAGE_C_POLICY_PATH")
    if binding.get("stage") != STAGE_C:
        errors.append("STAGE_C_STAGE_ID")
    if binding.get("required_items_sha256") != required_items_sha256(STAGE_C):
        errors.append("STAGE_C_REQUIRED_ITEMS_DIGEST")
    for key in ("candidate_sha256", "plan_sha256"):
        value = binding.get(key)
        if not isinstance(value, str) or not _HEX64.fullmatch(value):
            errors.append("STAGE_C_" + key.upper() + "_INVALID")
    return sorted(set(errors))


def build_stage_b_attestation(
    *,
    receipts: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    """Construct the exact attestation shape after callers have verified receipts."""
    return {
        "schema": SCHEMA,
        "policy_schema": POLICY_SCHEMA,
        "policy_path": POLICY_PATH,
        "stage": STAGE_B,
        "required_items_sha256": required_items_sha256(STAGE_B),
        "passed_items": list(STAGE_B_REQUIRED),
        "failed_items": [],
        "source_receipts": dict(receipts),
    }


def build_stage_c_policy_binding(
    *, candidate_sha256: str, plan_sha256: str
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "policy_schema": POLICY_SCHEMA,
        "policy_path": POLICY_PATH,
        "stage": STAGE_C,
        "required_items_sha256": required_items_sha256(STAGE_C),
        "candidate_sha256": candidate_sha256,
        "plan_sha256": plan_sha256,
    }
