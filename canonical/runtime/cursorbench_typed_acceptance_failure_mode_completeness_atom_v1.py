"""Proof-carrying completeness audit for one typed-acceptance atom."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.cursorbench_typed_acceptance_supported_transform_atom_v1 import model_sha256
from canonical.runtime.cursorbench_typed_acceptance_semantics_bound_atom_v1 import (
    _bound_json,
    _canon,
    _hex,
    _string_list,
)
from canonical.runtime.independent_acceptance_model import generated_obligations

SCHEMA = "PROJECT_BRAIN_CURSORBENCH_TYPED_ACCEPTANCE_" + "FAILURE_" + "MODE_COMPLETENESS_ATOM_PROOF_V1"
ATOM_ID = "SPEC_ACCEPT_" + "FAILURE_" + "MODE_COMPLETENESS_V1"
ATOM_SEMANTICS = (
    "THE_GENERATED_OBLIGATION_SET_IS_COMPLETE_FOR_EVERY_MATERIAL_INDEPENDENTLY_"
    + "KNOWABLE_" + "FAILURE_" + "MODE_IN_THE_BOUND_REGION"
)
RECEIPT_SCHEMA = "PROJECT_BRAIN_TYPED_ACCEPTANCE_" + "FAILURE_" + "MODE_COMPLETENESS_RECEIPT_V1"
VERIFY_SCHEMA = (
    "PROJECT_BRAIN_TYPED_ACCEPTANCE_" + "FAILURE_" + "MODE_COMPLETENESS_INDEPENDENT_VERIFICATION_V1"
)


def obligation_projection(model: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(model, Mapping):
        raise ValueError("MODEL_NOT_OBJECT")
    rows = model.get("requirements")
    if not isinstance(rows, list) or not rows:
        raise ValueError("REQUIREMENTS_INVALID_OR_EMPTY")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"REQUIREMENT_NOT_OBJECT:{index}")
        rid = row.get("id")
        if not isinstance(rid, str) or not rid or rid in seen:
            raise ValueError(f"REQUIREMENT_ID_INVALID_OR_DUPLICATE:{index}")
        seen.add(rid)
        critical = row.get("critical", True)
        if not isinstance(critical, bool):
            raise ValueError("REQUIREMENT_CRITICAL_INVALID:" + rid)
        obligations = sorted(generated_obligations(dict(row)))
        if critical and not obligations:
            raise ValueError("CRITICAL_REQUIREMENT_WITHOUT_GENERATED_OBLIGATIONS:" + rid)
        out.append({
            "requirement_id": rid,
            "critical": critical,
            "generated_obligations": obligations,
        })
    return {"requirements": sorted(out, key=lambda x: x["requirement_id"])}


def projection_sha256(model: Mapping[str, Any]) -> str:
    return sha256(_canon(obligation_projection(model))).hexdigest()


def verify(
    model: Mapping[str, Any],
    binding: Mapping[str, Any] | None,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    try:
        digest = model_sha256(model)
        projection_digest = projection_sha256(model)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__MODE_COMPLETENESS_MODEL_INVALID",
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "atom_id": ATOM_ID,
            "atom_truth_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    if binding is None:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "OPEN__MODE_COMPLETENESS_BINDING_REQUIRED",
            "errors": ["MODE_COMPLETENESS_BINDING_MISSING"],
            "atom_id": ATOM_ID,
            "atom_semantics": ATOM_SEMANTICS,
            "model_sha256": digest,
            "projection_sha256": projection_digest,
            "atom_truth_authorized": False,
            "evidence_missing": True,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    if not isinstance(binding, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__MODE_COMPLETENESS_BINDING_INVALID",
            "errors": ["MODE_COMPLETENESS_BINDING_NOT_OBJECT"],
            "atom_id": ATOM_ID,
            "atom_truth_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    try:
        if set(binding) - {"receipt", "verification"}:
            raise ValueError("MODE_COMPLETENESS_BINDING_FIELDS_INVALID")
        receipt, receipt_path, receipt_blob = _bound_json(
            binding.get("receipt"),
            root=root,
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        verification, verification_path, verification_blob = _bound_json(
            binding.get("verification"),
            root=root,
            prefixes=("canonical/verification/",),
        )
        if receipt.get("schema") != RECEIPT_SCHEMA:
            raise ValueError("RECEIPT_SCHEMA_INVALID")
        if receipt.get("subject_model_sha256") != digest:
            raise ValueError("RECEIPT_MODEL_DIGEST_MISMATCH")
        if receipt.get("obligation_projection_sha256") != projection_digest:
            raise ValueError("RECEIPT_PROJECTION_DIGEST_MISMATCH")

        audit_id = receipt.get("mode_completeness_audit_id")
        producer_id = receipt.get("producer_id")
        if not isinstance(audit_id, str) or not audit_id.strip():
            raise ValueError("RECEIPT_AUDIT_ID_INVALID")
        if not isinstance(producer_id, str) or not producer_id.strip():
            raise ValueError("RECEIPT_PRODUCER_ID_INVALID")
        sources = _string_list(
            receipt.get("authoritative_source_sha256"),
            "RECEIPT_AUTHORITATIVE_SOURCE_SHA256",
            nonempty=True,
        )
        if any(not _hex(x, 64) for x in sources):
            raise ValueError("RECEIPT_AUTHORITATIVE_SOURCE_SHA256_INVALID")

        for key in (
            "every_material_independently_knowable_mode_bound",
            "generated_obligation_set_complete",
            "requirement_mode_scope_complete",
            "no_omitted_material_modes",
            "source_authority_complete",
        ):
            if receipt.get(key) is not True:
                raise ValueError("RECEIPT_PREMISE_UNPROVED:" + key)

        if verification.get("schema") != VERIFY_SCHEMA:
            raise ValueError("VERIFICATION_SCHEMA_INVALID")
        if verification.get("subject_git_blob_sha") != receipt_blob:
            raise ValueError("VERIFICATION_SUBJECT_BLOB_MISMATCH")
        if verification.get("subject_model_sha256") != digest:
            raise ValueError("VERIFICATION_MODEL_DIGEST_MISMATCH")
        if verification.get("obligation_projection_sha256") != projection_digest:
            raise ValueError("VERIFICATION_PROJECTION_DIGEST_MISMATCH")
        if verification.get("mode_completeness_audit_id") != audit_id:
            raise ValueError("VERIFICATION_AUDIT_ID_MISMATCH")
        if verification.get("producer_id") != producer_id:
            raise ValueError("VERIFICATION_PRODUCER_ID_MISMATCH")
        if verification.get("authoritative_source_sha256") != sources:
            raise ValueError("VERIFICATION_AUTHORITATIVE_SOURCE_SET_MISMATCH")

        verifier_id = verification.get("independent_verifier_id")
        if not isinstance(verifier_id, str) or not verifier_id.strip():
            raise ValueError("VERIFICATION_INDEPENDENT_VERIFIER_ID_INVALID")
        if verifier_id == producer_id:
            raise ValueError("VERIFICATION_NOT_PRODUCER_INDEPENDENT")
        if verification.get("verification_method") not in {
            "INDEPENDENT_REPLAY",
            "INDEPENDENT_AUDIT",
            "CONTROLLED_ENVIRONMENT_AUDIT",
        }:
            raise ValueError("VERIFICATION_METHOD_INVALID")

        for key in (
            "pass",
            "independent_verified",
            "authoritative_source_set_verified",
            "requirement_mode_scope_completeness_verified",
            "generated_obligation_set_completeness_verified",
            "omitted_material_mode_absence_verified",
            "source_authority_completeness_verified",
        ):
            if verification.get(key) is not True:
                raise ValueError("VERIFICATION_PREMISE_UNPROVED:" + key)

        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__MODE_COMPLETENESS_ATOM_INDEPENDENTLY_BOUND",
            "atom_id": ATOM_ID,
            "atom_semantics": ATOM_SEMANTICS,
            "atom_truth_authorized": True,
            "proof_basis": "CONTENT_ADDRESSED_INDEPENDENT_MODE_COMPLETENESS_AUDIT",
            "model_sha256": digest,
            "projection_sha256": projection_digest,
            "mode_completeness_audit_id": audit_id,
            "producer_id": producer_id,
            "independent_verifier_id": verifier_id,
            "verification_method": verification.get("verification_method"),
            "authoritative_source_sha256": sources,
            "receipt_path": receipt_path,
            "receipt_git_blob_sha": receipt_blob,
            "verification_path": verification_path,
            "verification_git_blob_sha": verification_blob,
            "proved_constraint": {"op": "ATOM", "id": ATOM_ID},
            "other_condition_atoms_proved": [],
            "membership_self_certified": False,
            "whole_policy_condition_proved": False,
            "whole_specification_behavior_adequate": False,
            "whole_cursorbench_adequate": False,
            "acceptance_credit_delta": 0,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__MODE_COMPLETENESS_ATOM_UNPROVED",
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "atom_id": ATOM_ID,
            "atom_semantics": ATOM_SEMANTICS,
            "model_sha256": digest,
            "projection_sha256": projection_digest,
            "atom_truth_authorized": False,
            "proved_constraint": None,
            "membership_self_certified": False,
            "whole_policy_condition_proved": False,
            "whole_specification_behavior_adequate": False,
            "whole_cursorbench_adequate": False,
            "acceptance_credit_delta": 0,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
