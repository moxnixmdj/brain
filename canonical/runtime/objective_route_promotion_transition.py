"""Receipt-backed proof of objective-route prewave promotion transitions.

A promoted binding is accepted only if normalizing the allowed promotion fields
back to their prepromotion values reproduces the exact Git blob independently
verified by the referenced receipt. This helper grants no terminal, execution,
promotion, capability, or family authority by itself.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

PUBLIC_RUNNER = "moxnixmdj/verification-capsule-runner"
ZERO_RECEIPT_FIELDS = (
    "terminal_results_observed",
    "fresh_terminal_evidence_consumed",
    "capability_credit_delta",
    "family_credit_delta",
)


def git_blob_sha_bytes(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("NOT_OBJECT")
    return obj


def _receipt_base_binding_sha(
    receipt: Mapping[str, Any],
    behavior_id: str,
    binding_path: str,
) -> tuple[str | None, list[str]]:
    errors: list[str] = []

    if receipt.get("public_verifier_repository") != PUBLIC_RUNNER:
        errors.append("PROMOTION_RECEIPT_PUBLIC_RUNNER_MISMATCH")

    for field in ZERO_RECEIPT_FIELDS:
        if receipt.get(field) != 0:
            errors.append(f"PROMOTION_RECEIPT_{field.upper()}_NOT_ZERO")

    # Single-behavior receipt.
    if receipt.get("behavior_id") == behavior_id:
        if receipt.get("workflow_conclusion") != "success":
            errors.append("PROMOTION_RECEIPT_WORKFLOW_NOT_SUCCESS")
        exact = receipt.get("exact_brain_blobs")
        sha = exact.get(binding_path) if isinstance(exact, Mapping) else None
        if not isinstance(sha, str) or not sha:
            errors.append("PROMOTION_RECEIPT_BASE_BINDING_SHA_MISSING")
            return None, errors
        return sha, errors

    # Multiplex receipt.
    jobs = receipt.get("verified_jobs")
    if isinstance(jobs, list):
        matches = [
            row
            for row in jobs
            if isinstance(row, Mapping)
            and row.get("behavior_id") == behavior_id
            and row.get("binding_path") == binding_path
        ]
        if len(matches) != 1:
            errors.append("PROMOTION_RECEIPT_MATCHED_JOB_COUNT_INVALID")
            return None, errors
        row = matches[0]
        if row.get("conclusion") != "success":
            errors.append("PROMOTION_RECEIPT_MATCHED_JOB_NOT_SUCCESS")
        sha = row.get("binding_blob_sha")
        if not isinstance(sha, str) or not sha:
            errors.append("PROMOTION_RECEIPT_BASE_BINDING_SHA_MISSING")
            return None, errors
        return sha, errors

    errors.append("PROMOTION_RECEIPT_BEHAVIOR_NOT_BOUND")
    return None, errors


def validate_promotion_transition(
    root: Path,
    binding: Mapping[str, Any],
    *,
    binding_path: str,
    behavior_id: str,
    prepromotion_status: str,
    promoted_status: str,
) -> list[str]:
    """Return fail-closed errors for the binding's promotion state."""

    root = root.resolve()
    errors: list[str] = []

    gates = binding.get("route_gates")
    if not isinstance(gates, Mapping):
        return ["PROMOTION_ROUTE_GATES_INVALID"]

    independent = gates.get("independent_verification_pass")
    prewave = binding.get("prewave_admissible")
    if not isinstance(independent, bool):
        return ["INDEPENDENT_VERIFICATION_GATE_NOT_BOOLEAN"]
    if prewave is not independent:
        errors.append("PREWAVE_ADMISSIBILITY_VERIFICATION_STATE_MISMATCH")

    receipt_rel = binding.get("independent_verification")

    if not independent:
        if binding.get("status") != prepromotion_status:
            errors.append("PREPROMOTION_STATUS_MISMATCH")
        if receipt_rel is not None:
            errors.append("PREPROMOTION_RECEIPT_MUST_BE_ABSENT")
        return errors

    if binding.get("status") != promoted_status:
        errors.append("PROMOTED_STATUS_MISMATCH")
    if not isinstance(receipt_rel, str) or not receipt_rel:
        errors.append("PROMOTION_RECEIPT_PATH_MISSING")
        return errors

    try:
        receipt = _read(root / receipt_rel)
    except Exception as exc:
        errors.append("PROMOTION_RECEIPT_READ_FAILURE:" + type(exc).__name__)
        return errors

    if not str(receipt.get("status", "")).startswith("INDEPENDENT"):
        errors.append("PROMOTION_RECEIPT_NOT_INDEPENDENT_PASS")

    expected_base_sha, receipt_errors = _receipt_base_binding_sha(
        receipt, behavior_id, binding_path
    )
    errors.extend(receipt_errors)
    if expected_base_sha is None:
        return errors

    # Normalize only the promotion fields. Any other mutation changes the
    # reconstructed Git blob and therefore fails the receipt-bound hash check.
    base = json.loads(json.dumps(binding))
    base["status"] = prepromotion_status
    base["route_gates"]["independent_verification_pass"] = False
    base["prewave_admissible"] = False
    base.pop("independent_verification", None)
    base_bytes = (json.dumps(base, indent=2) + "\n").encode("utf-8")
    reconstructed_base_sha = git_blob_sha_bytes(base_bytes)
    if reconstructed_base_sha != expected_base_sha:
        errors.append(
            "PROMOTION_TRANSITION_BASE_SHA_MISMATCH:"
            + reconstructed_base_sha
            + "!="
            + expected_base_sha
        )

    return errors
