"""Authenticated pre-verifier information-boundary proof for one typed-acceptance atom.

This module proves exactly:
    SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1

It accepts no caller truth booleans.  Authority must arrive as a content-addressed
receipt plus a content-addressed independent verification record.  Both records
must bind the exact normalized typed-acceptance model bytes.

This deliberately does NOT prove:
- semantic completeness,
- failure-mode completeness,
- dependency/provenance label truth,
- whole policy adequacy,
- CursorBench score or acceptance.

A missing binding is simply missing evidence.  A supplied but malformed or
mismatched binding fails closed.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.cursorbench_typed_acceptance_supported_transform_atom_v1 import (
    model_sha256,
)

SCHEMA = "PROJECT_BRAIN_CURSORBENCH_TYPED_ACCEPTANCE_INFORMATION_BOUNDARY_ATOM_PROOF_V1"
ATOM_ID = "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1"
ATOM_SEMANTICS = (
    "NO_HIDDEN_VERIFIER_OR_TASK_SPECIFIC_SOLUTION_INFORMATION_WAS_USED_"
    "BEFORE_TERMINAL_AUTHORIZATION"
)

RECEIPT_SCHEMA = "PROJECT_BRAIN_PREVERIFIER_INFORMATION_BOUNDARY_RECEIPT_V1"
VERIFY_SCHEMA = (
    "PROJECT_BRAIN_PREVERIFIER_INFORMATION_BOUNDARY_INDEPENDENT_VERIFICATION_V1"
)


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _hex(value: Any, n: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == n
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _bound_json(
    ref: Any,
    *,
    root: Path,
    prefixes: tuple[str, ...],
) -> tuple[Mapping[str, Any], str, str]:
    if not isinstance(ref, Mapping):
        raise ValueError("BOUND_REF_REQUIRED")
    rel = str(ref.get("path") or "").strip()
    expected = str(ref.get("git_blob_sha") or "").strip()
    p = Path(rel)
    if not rel or p.is_absolute() or ".." in p.parts:
        raise ValueError("BOUND_PATH_INVALID")
    if not any(rel.startswith(prefix) for prefix in prefixes):
        raise ValueError("BOUND_PATH_OUTSIDE_ALLOWED_SCOPE")

    base = root.resolve(strict=True)
    path = base / p
    for part in [path, *path.parents]:
        if part == base:
            continue
        try:
            if part.is_symlink():
                raise ValueError("BOUND_SYMLINK_FORBIDDEN:" + rel)
        except OSError as exc:
            raise ValueError("BOUND_PATH_INSPECTION_FAILED:" + rel) from exc

    resolved = path.resolve(strict=False)
    if not any(
        resolved.is_relative_to((base / prefix).resolve(strict=False))
        for prefix in prefixes
    ):
        raise ValueError("BOUND_RESOLVED_PATH_OUTSIDE_ALLOWED_SCOPE")
    if not path.is_file():
        raise ValueError("BOUND_FILE_MISSING:" + rel)

    actual = _git_blob_sha(path)
    if not _hex(expected, 40) or actual != expected:
        raise ValueError("BOUND_BLOB_DRIFT:" + rel)

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("BOUND_JSON_NOT_OBJECT:" + rel)
    return value, rel, actual


def _digest_list(value: Any, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not _hex(x, 64) for x in value)
        or len(set(value)) != len(value)
    ):
        raise ValueError(label + "_INVALID")
    return list(value)


def verify(
    model: Mapping[str, Any],
    binding: Mapping[str, Any] | None,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    digest = model_sha256(model) if isinstance(model, Mapping) else None

    if not isinstance(model, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__MODEL_NOT_OBJECT",
            "errors": ["MODEL_NOT_OBJECT"],
            "atom_id": ATOM_ID,
            "atom_truth_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    if binding is None:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "OPEN__PREVERIFIER_INFORMATION_BOUNDARY_BINDING_REQUIRED",
            "errors": ["INFORMATION_BOUNDARY_BINDING_MISSING"],
            "atom_id": ATOM_ID,
            "atom_semantics": ATOM_SEMANTICS,
            "model_sha256": digest,
            "atom_truth_authorized": False,
            "evidence_missing": True,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    if not isinstance(binding, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__INFORMATION_BOUNDARY_BINDING_INVALID",
            "errors": ["INFORMATION_BOUNDARY_BINDING_NOT_OBJECT"],
            "atom_id": ATOM_ID,
            "model_sha256": digest,
            "atom_truth_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    try:
        allowed = {"receipt", "verification"}
        extra = set(binding) - allowed
        if extra:
            raise ValueError(
                "INFORMATION_BOUNDARY_BINDING_FIELDS_INVALID:" + ",".join(sorted(extra))
            )

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
        boundary_id = receipt.get("boundary_id")
        if not isinstance(boundary_id, str) or not boundary_id.strip():
            raise ValueError("RECEIPT_BOUNDARY_ID_INVALID")
        producer_id = receipt.get("producer_id")
        if not isinstance(producer_id, str) or not producer_id.strip():
            raise ValueError("RECEIPT_PRODUCER_ID_INVALID")

        visible_inputs = _digest_list(
            receipt.get("declared_visible_input_sha256"),
            "RECEIPT_VISIBLE_INPUT_DIGESTS",
        )
        required_receipt_truth = {
            "preterminal_information_sources_complete": True,
            "model_derived_only_from_declared_visible_inputs": True,
            "hidden_verifier_access_before_terminal_authorization": False,
            "task_specific_solution_access_before_terminal_authorization": False,
            "boundary_frozen_before_terminal_authorization": True,
        }
        for key, expected in required_receipt_truth.items():
            if receipt.get(key) is not expected:
                raise ValueError("RECEIPT_PREMISE_UNPROVED:" + key)

        if verification.get("schema") != VERIFY_SCHEMA:
            raise ValueError("VERIFICATION_SCHEMA_INVALID")
        if verification.get("subject_git_blob_sha") != receipt_blob:
            raise ValueError("VERIFICATION_SUBJECT_BLOB_MISMATCH")
        if verification.get("subject_model_sha256") != digest:
            raise ValueError("VERIFICATION_MODEL_DIGEST_MISMATCH")
        if verification.get("boundary_id") != boundary_id:
            raise ValueError("VERIFICATION_BOUNDARY_ID_MISMATCH")
        if verification.get("declared_visible_input_sha256") != visible_inputs:
            raise ValueError("VERIFICATION_VISIBLE_INPUT_DIGESTS_MISMATCH")
        if verification.get("producer_id") != producer_id:
            raise ValueError("VERIFICATION_PRODUCER_ID_MISMATCH")
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

        required_verify_truth = (
            "pass",
            "independent_verified",
            "declared_visible_inputs_verified",
            "preterminal_information_source_completeness_verified",
            "model_derivation_boundary_verified",
            "hidden_verifier_access_absence_verified",
            "task_specific_solution_access_absence_verified",
            "boundary_ordering_verified",
        )
        for key in required_verify_truth:
            if verification.get(key) is not True:
                raise ValueError("VERIFICATION_PREMISE_UNPROVED:" + key)

        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__NO_HIDDEN_VERIFIER_ACCESS_ATOM_INDEPENDENTLY_BOUND",
            "atom_id": ATOM_ID,
            "atom_semantics": ATOM_SEMANTICS,
            "atom_truth_authorized": True,
            "proof_basis": "CONTENT_ADDRESSED_INDEPENDENT_PREVERIFIER_INFORMATION_BOUNDARY",
            "model_sha256": digest,
            "boundary_id": boundary_id,
            "producer_id": producer_id,
            "independent_verifier_id": verifier_id,
            "verification_method": verification.get("verification_method"),
            "declared_visible_input_sha256": visible_inputs,
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
            "status": "FAIL_CLOSED__INFORMATION_BOUNDARY_ATOM_UNPROVED",
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "atom_id": ATOM_ID,
            "atom_semantics": ATOM_SEMANTICS,
            "model_sha256": digest,
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
