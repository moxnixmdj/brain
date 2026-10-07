"""Fail-closed structural completeness gate for policy adequacy bases.

This module intentionally does not interpret behavioral-contract prose. Every
required canonical contract field is content-addressed as one opaque obligation.
A policy manifest is structurally complete only when:
- all context-membership obligations are bound by admission;
- every candidate policy either conditions on or independently discharges every
  adequacy/hard-constraint obligation;
- evidence-authority and terminal-accounting obligations are bound; and
- a separate certificate reference asserts completeness of the candidate policy set.

Certificate IDs are references, never self-verification. This closes silent
contract-field omission, not semantic truth or policy adequacy.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ADEQUACY_BASIS_STRUCTURAL_COMPLETENESS_GATE_V1"
MANIFEST_SCHEMA = "PROJECT_BRAIN_POLICY_ADEQUACY_BASIS_MANIFEST_V1"

ROLE_BY_FIELD = {
    "behavior_id": "IDENTITY",
    "inputs": "MEMBERSHIP",
    "environment_state": "MEMBERSHIP",
    "allowed_information": "HARD_CONSTRAINT",
    "required_output_or_action": "ADEQUACY",
    "success_condition": "ADEQUACY",
    "failure_condition": "HARD_CONSTRAINT",
    "terminal_consequence": "TERMINAL_ACCOUNTING",
    "verification_route": "EVIDENCE_AUTHORITY",
    "dependency_boundary": "HARD_CONSTRAINT",
    "scope": "MEMBERSHIP",
}
POLICY_ROLES = {"ADEQUACY", "HARD_CONSTRAINT"}


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return bool(value)
    return value is not None


def _atom_id(behavior_id: str, field: str, value: Any) -> str:
    digest = sha256(_canon(value).encode("utf-8")).hexdigest()
    return f"CONTRACT::{behavior_id}::{field}::{digest}"


def compile_contract_basis(contract: Any, contract_schema: Any) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(contract, Mapping):
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "errors": ["CONTRACT_NOT_OBJECT"]}
    if not isinstance(contract_schema, Mapping):
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "errors": ["CONTRACT_SCHEMA_NOT_OBJECT"]}

    required = contract_schema.get("required_behavior_fields")
    if not isinstance(required, list) or not required:
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "errors": ["REQUIRED_FIELD_SCHEMA_INVALID"]}
    if len(set(required)) != len(required) or any(x not in ROLE_BY_FIELD for x in required):
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "errors": ["REQUIRED_FIELD_SCHEMA_UNSUPPORTED"]}

    behavior_id = contract.get("behavior_id")
    if not isinstance(behavior_id, str) or not behavior_id.strip():
        errors.append("BEHAVIOR_ID_INVALID")
        behavior_id = "INVALID"

    rows = []
    for field in required:
        if field not in contract:
            errors.append("REQUIRED_CONTRACT_FIELD_MISSING:" + field)
            continue
        value = contract[field]
        if not _nonempty(value):
            errors.append("REQUIRED_CONTRACT_FIELD_EMPTY:" + field)
            continue
        rows.append({
            "field": field,
            "role": ROLE_BY_FIELD[field],
            "atom_id": _atom_id(behavior_id, field, value),
            "value_sha256": sha256(_canon(value).encode("utf-8")).hexdigest(),
        })

    if errors:
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "errors": sorted(set(errors))}

    by_role: dict[str, list[str]] = {}
    for row in rows:
        by_role.setdefault(row["role"], []).append(row["atom_id"])
    for values in by_role.values():
        values.sort()

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "COMPILED_OPAQUE_CONTRACT_OBLIGATION_BASIS",
        "behavior_id": behavior_id,
        "obligations": rows,
        "by_role": by_role,
        "all_atom_ids": sorted(row["atom_id"] for row in rows),
        "semantic_interpretation_performed": False,
        "terminal_authority": False,
    }


def _string_set(value: Any, label: str, errors: list[str]) -> set[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        errors.append(label + "_INVALID")
        return set()
    if len(set(value)) != len(value):
        errors.append(label + "_DUPLICATE")
    return set(value)


def verify_policy_manifest(contract: Any, contract_schema: Any, manifest: Any) -> dict[str, Any]:
    compiled = compile_contract_basis(contract, contract_schema)
    if compiled.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": ["CONTRACT_BASIS_COMPILE_FAILED"] + list(compiled.get("errors") or []),
            "compiled_contract": compiled,
            "terminal_authority": False,
        }
    if not isinstance(manifest, Mapping) or manifest.get("schema") != MANIFEST_SCHEMA:
        return {
            "schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED",
            "errors": ["MANIFEST_SCHEMA_INVALID"], "compiled_contract": compiled,
            "terminal_authority": False,
        }

    errors: list[str] = []
    behavior_id = compiled["behavior_id"]
    if manifest.get("behavior_id") != behavior_id:
        errors.append("MANIFEST_BEHAVIOR_ID_MISMATCH")

    all_atoms = set(compiled["all_atom_ids"])
    role = compiled["by_role"]
    membership_required = set(role.get("MEMBERSHIP", []))
    policy_required = set(role.get("ADEQUACY", [])) | set(role.get("HARD_CONSTRAINT", []))
    evidence_required = set(role.get("EVIDENCE_AUTHORITY", []))
    accounting_required = set(role.get("TERMINAL_ACCOUNTING", []))

    admission = _string_set(manifest.get("admission_atom_ids"), "ADMISSION_ATOM_IDS", errors)
    promotion = _string_set(manifest.get("promotion_atom_ids"), "PROMOTION_ATOM_IDS", errors)
    accounting = _string_set(manifest.get("terminal_accounting_atom_ids"), "TERMINAL_ACCOUNTING_ATOM_IDS", errors)

    for label, values in (
        ("ADMISSION", admission), ("PROMOTION", promotion), ("TERMINAL_ACCOUNTING", accounting)
    ):
        for unknown in sorted(values - all_atoms):
            errors.append(f"{label}_UNKNOWN_ATOM:{unknown}")

    for missing in sorted(membership_required - admission):
        errors.append("MEMBERSHIP_OBLIGATION_UNBOUND:" + missing)
    for missing in sorted(evidence_required - promotion):
        errors.append("EVIDENCE_AUTHORITY_OBLIGATION_UNBOUND:" + missing)
    for missing in sorted(accounting_required - accounting):
        errors.append("TERMINAL_ACCOUNTING_OBLIGATION_UNBOUND:" + missing)

    policy_set_cert = manifest.get("candidate_policy_set_complete_certificate_id")
    if not isinstance(policy_set_cert, str) or not policy_set_cert.strip():
        errors.append("CANDIDATE_POLICY_SET_COMPLETENESS_CERTIFICATE_MISSING")

    policies = manifest.get("policies")
    if not isinstance(policies, list) or not policies:
        errors.append("POLICIES_INVALID_OR_EMPTY")
        policies = []

    seen_policy_ids: set[str] = set()
    policy_results = []
    for i, row in enumerate(policies):
        if not isinstance(row, Mapping):
            errors.append(f"POLICY_NOT_OBJECT:{i}")
            continue
        pid = row.get("policy_id")
        if not isinstance(pid, str) or not pid.strip() or pid in seen_policy_ids:
            errors.append(f"POLICY_ID_INVALID_OR_DUPLICATE:{i}")
            continue
        seen_policy_ids.add(pid)

        basis = _string_set(row.get("basis_atom_ids"), f"POLICY_BASIS_ATOM_IDS:{pid}", errors)
        condition = _string_set(row.get("policy_condition_atom_ids"), f"POLICY_CONDITION_ATOM_IDS:{pid}", errors)
        for label, values in (("BASIS", basis), ("CONDITION", condition)):
            for unknown in sorted(values - all_atoms):
                errors.append(f"POLICY_{label}_UNKNOWN_ATOM:{pid}:{unknown}")
        for outside in sorted(condition - basis):
            errors.append(f"POLICY_CONDITION_ATOM_OUTSIDE_BASIS:{pid}:{outside}")

        raw_discharges = row.get("unconditional_discharges", [])
        if not isinstance(raw_discharges, list):
            errors.append(f"POLICY_UNCONDITIONAL_DISCHARGES_INVALID:{pid}")
            raw_discharges = []
        discharged: set[str] = set()
        for j, d in enumerate(raw_discharges):
            if not isinstance(d, Mapping):
                errors.append(f"POLICY_DISCHARGE_NOT_OBJECT:{pid}:{j}")
                continue
            aid = d.get("atom_id")
            cert = d.get("certificate_id")
            if not isinstance(aid, str) or aid not in all_atoms:
                errors.append(f"POLICY_DISCHARGE_UNKNOWN_ATOM:{pid}:{aid}")
                continue
            if not isinstance(cert, str) or not cert.strip():
                errors.append(f"POLICY_DISCHARGE_CERTIFICATE_MISSING:{pid}:{aid}")
                continue
            if aid in discharged:
                errors.append(f"POLICY_DISCHARGE_DUPLICATE:{pid}:{aid}")
            discharged.add(aid)

        contingent_required = policy_required - discharged
        for missing in sorted(contingent_required - basis):
            errors.append(f"POLICY_REQUIRED_OBLIGATION_NOT_IN_BASIS:{pid}:{missing}")
        for missing in sorted(contingent_required - condition):
            errors.append(f"POLICY_REQUIRED_OBLIGATION_NOT_IN_CONDITION:{pid}:{missing}")
        for missing in sorted(policy_required - (basis | discharged)):
            errors.append(f"POLICY_REQUIRED_OBLIGATION_UNCOVERED:{pid}:{missing}")

        policy_results.append({
            "policy_id": pid,
            "required_policy_obligation_count": len(policy_required),
            "basis_count": len(basis),
            "condition_count": len(condition),
            "unconditional_discharge_count": len(discharged),
        })

    return {
        "schema": SCHEMA,
        "pass": not errors,
        "status": (
            "PASS__STRUCTURAL_ADEQUACY_BASIS_FIELD_COVERAGE_COMPLETE"
            if not errors else "FAIL_CLOSED"
        ),
        "errors": sorted(set(errors)),
        "behavior_id": behavior_id,
        "compiled_contract": compiled,
        "policy_results": policy_results,
        "candidate_policy_set_completeness_self_verified": False,
        "certificate_truth_self_verified": False,
        "semantic_truth_self_verified": False,
        "structural_field_omission_closed": not errors,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
