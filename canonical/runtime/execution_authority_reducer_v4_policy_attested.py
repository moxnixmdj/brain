"""Fail-closed execution-authority V4 policy-attestation wrapper.

V4 preserves the verified V3 event-state machine and adds two gates before V3:
1. STAGE_B_PASS must carry exact item-level, content-addressed attestation for
   every live Stage-B policy requirement.
2. LEASE_ISSUED must bind the exact live Stage-C policy digest plus immutable
   candidate and plan hashes.

The live policy document is a required input. Policy growth therefore fails
closed until this kernel is updated and independently verified.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from canonical.runtime import execution_authority_reducer as v3
from canonical.runtime import staged_policy_attestation_v1 as policy_gate

SCHEMA = "PROJECT_BRAIN_EXECUTION_AUTHORITY_V4_POLICY_ATTESTED"


def validate_policy_document(policy: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(policy, Mapping):
        return ["POLICY_DOCUMENT_NOT_MAPPING"]
    if policy.get("schema") != policy_gate.POLICY_SCHEMA:
        errors.append("POLICY_SCHEMA_MISMATCH")
    if policy.get("status") != "MANDATORY_FAIL_CLOSED_BEFORE_UNTOUCHED_QUALIFICATION_SPEND":
        errors.append("POLICY_STATUS_MISMATCH")
    staged = policy.get("staged_admission")
    if not isinstance(staged, Mapping):
        return sorted(set(errors + ["POLICY_STAGED_ADMISSION_MISSING"]))
    for stage, expected in (
        (policy_gate.STAGE_B, policy_gate.STAGE_B_REQUIRED),
        (policy_gate.STAGE_C, policy_gate.STAGE_C_REQUIRED),
    ):
        node = staged.get(stage)
        if not isinstance(node, Mapping):
            errors.append("POLICY_STAGE_MISSING:" + stage)
            continue
        required = node.get("required")
        if not isinstance(required, list) or any(not isinstance(x, str) for x in required):
            errors.append("POLICY_REQUIRED_INVALID:" + stage)
            continue
        if tuple(required) != expected:
            errors.append("POLICY_REQUIRED_DRIFT:" + stage)
    return sorted(set(errors))


def validate_policy_bound_events(events: Iterable[Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    for i, event in enumerate(events):
        et = event.get("type")
        if et == "STAGE_B_PASS":
            for error in policy_gate.validate_stage_b_attestation(event.get("evidence")):
                errors.append(f"{error}:EVENT_{i}")
        elif et == "LEASE_ISSUED":
            for error in policy_gate.validate_stage_c_lease_binding(event.get("evidence")):
                errors.append(f"{error}:EVENT_{i}")
    return sorted(set(errors))


def derive_authority(
    events: Iterable[Mapping[str, Any]],
    *,
    task: str,
    execution_budget: int,
    verifier_budget: int,
    policy_document: Mapping[str, Any],
) -> dict[str, Any]:
    ordered = list(events)
    errors = validate_policy_document(policy_document)
    errors.extend(validate_policy_bound_events(ordered))
    if errors:
        return {
            "schema": SCHEMA,
            "task": task,
            "valid": False,
            "errors": sorted(set(errors)),
            "can_execute": False,
            "can_verify": False,
            "policy_attested": False,
        }

    out = v3.derive_authority(
        ordered,
        task=task,
        execution_budget=execution_budget,
        verifier_budget=verifier_budget,
    )
    wrapped = dict(out)
    wrapped["schema"] = SCHEMA
    wrapped["policy_attested"] = bool(out.get("valid"))
    wrapped["stage_b_required_items_sha256"] = policy_gate.required_items_sha256(
        policy_gate.STAGE_B
    )
    wrapped["stage_c_required_items_sha256"] = policy_gate.required_items_sha256(
        policy_gate.STAGE_C
    )
    return wrapped


canonical_event_hash = v3.canonical_event_hash
carrier_binding_hash = v3.carrier_binding_hash
