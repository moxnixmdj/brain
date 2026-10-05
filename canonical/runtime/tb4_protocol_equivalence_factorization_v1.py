from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TB4_PROTOCOL_EQUIVALENCE_FACTORIZATION_VERDICT_V1"

_REQUIRED_CARRIER = (
    "same_dataset_digest",
    "same_task_and_verifier_images",
    "same_harbor_execution_semantics",
    "same_resource_limits",
    "same_network_semantics",
    "same_retry_timeout_trial_semantics",
)
_REQUIRED_TARGET = (
    "same_agent_runtime_and_version",
    "same_model_effort",
    "same_fallback_policy",
    "same_evaluator",
    "same_trial_count",
)

def _sha1(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)

def _receipts_bound(block: Mapping[str, Any]) -> bool:
    rows = block.get("receipts")
    if not isinstance(rows, list) or not rows:
        return False
    for row in rows:
        if not isinstance(row, Mapping):
            return False
        if not isinstance(row.get("path"), str) or not row["path"].strip():
            return False
        if not _sha1(row.get("git_blob_sha")):
            return False
    return True

def evaluate(spec: Mapping[str, Any], carrier_receipt: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if spec.get("schema") != "PROJECT_BRAIN_TB4_PROTOCOL_EQUIVALENCE_FACTORIZATION_20261006_V1":
        errors.append("SPEC_SCHEMA_MISMATCH")
    if spec.get("target_predicate") != "CODING_TB4_GE_66_4":
        errors.append("TARGET_PREDICATE_MISMATCH")
    resource = carrier_receipt.get("compared_to_frozen_tb4_carrier_minimum")
    carrier_runtime_pass = isinstance(resource, Mapping) and resource.get("runtime_resource_and_container_subpremises") == "PASS"
    carrier = spec.get("carrier_invariance")
    target = spec.get("target_harness_identity")
    if not isinstance(carrier, Mapping):
        carrier = {}; errors.append("CARRIER_INVARIANCE_BLOCK_MISSING")
    if not isinstance(target, Mapping):
        target = {}; errors.append("TARGET_HARNESS_IDENTITY_BLOCK_MISSING")
    carrier_invariance_bound = (
        carrier.get("status") == "PROVED_EXACT"
        and _receipts_bound(carrier)
        and all(carrier.get(k) is True for k in _REQUIRED_CARRIER)
    )
    target_harness_identity_bound = (
        target.get("status") == "PROVED_EXACT"
        and target.get("evidence_class") == "EXACT_FROZEN_TARGET_HARNESS"
        and _receipts_bound(target)
        and all(target.get(k) is True for k in _REQUIRED_TARGET)
    )
    if target.get("evidence_class") == "PUBLIC_LEADERBOARD_CALIBRATION":
        target_harness_identity_bound = False
    fallback = target.get("fallback_policy_relation")
    if fallback not in (None, "EXACT_MATCH"):
        target_harness_identity_bound = False
        errors.append("FALLBACK_POLICY_NOT_EXACT_MATCH")
    full = bool(carrier_runtime_pass and carrier_invariance_bound and target_harness_identity_bound and not errors)
    missing: list[str] = []
    if not carrier_runtime_pass: missing.append("CARRIER_RUNTIME_SUBPREMISES")
    if not carrier_invariance_bound: missing.append("CARRIER_INVARIANCE_CERTIFICATE")
    if not target_harness_identity_bound: missing.append("EXACT_FROZEN_TARGET_HARNESS_IDENTITY")
    return {
        "schema": SCHEMA,
        "pass": full,
        "status": "PASS__FULL_PROTOCOL_EQUIVALENCE_BOUND" if full else "FAIL_CLOSED__PROTOCOL_EQUIVALENCE_NOT_BOUND",
        "carrier_runtime_subpremises_bound": carrier_runtime_pass,
        "carrier_invariance_bound": carrier_invariance_bound,
        "target_harness_identity_bound": target_harness_identity_bound,
        "protocol_equivalence_bound": full,
        "missing": missing,
        "errors": sorted(set(errors)),
        "terminal_credit_delta": 0,
    }
