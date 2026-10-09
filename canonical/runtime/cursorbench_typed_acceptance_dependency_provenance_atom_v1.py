"""Proof-carrying dependency/provenance truth for one CursorBench typed-acceptance atom.

Proves exactly SPEC_ACCEPT_DEPENDENCY_PROVENANCE_TRUTH_V1 when a content-addressed
receipt and producer-independent verification bind the exact normalized model and
its exact independence-relevant dependency/provenance projection.

The model cannot self-certify these labels. Structural consistency is necessary,
not sufficient.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.cursorbench_typed_acceptance_supported_transform_atom_v1 import (
    model_sha256,
)

SCHEMA = "PROJECT_BRAIN_CURSORBENCH_TYPED_ACCEPTANCE_DEPENDENCY_PROVENANCE_ATOM_PROOF_V1"
ATOM_ID = "SPEC_ACCEPT_DEPENDENCY_PROVENANCE_TRUTH_V1"
ATOM_SEMANTICS = (
    "DEPENDENCY_AND_PROVENANCE_LABELS_USED_FOR_INDEPENDENCE_JUDGMENT_"
    "ARE_TRUTHFUL_AND_AUTHORIZED"
)
RECEIPT_SCHEMA = "PROJECT_BRAIN_TYPED_ACCEPTANCE_DEPENDENCY_PROVENANCE_RECEIPT_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_TYPED_ACCEPTANCE_DEPENDENCY_PROVENANCE_INDEPENDENT_VERIFICATION_V1"


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _hex(value: Any, n: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == n
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise ValueError(label + "_INVALID")
    if len(set(value)) != len(value):
        raise ValueError(label + "_DUPLICATE")
    return list(value)


def dependency_provenance_projection(model: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(model, Mapping):
        raise ValueError("MODEL_NOT_OBJECT")
    requirements = model.get("requirements")
    checks = model.get("checks")
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("REQUIREMENTS_INVALID_OR_EMPTY")
    if not isinstance(checks, list):
        raise ValueError("CHECKS_INVALID")

    req_rows: list[dict[str, Any]] = []
    req_ids: set[str] = set()
    for index, row in enumerate(requirements):
        if not isinstance(row, Mapping):
            raise ValueError(f"REQUIREMENT_NOT_OBJECT:{index}")
        rid = row.get("id")
        if not isinstance(rid, str) or not rid or rid in req_ids:
            raise ValueError(f"REQUIREMENT_ID_INVALID_OR_DUPLICATE:{index}")
        req_ids.add(rid)
        deps = _string_list(row.get("builder_dependencies", []), f"BUILDER_DEPENDENCIES:{rid}")
        req_rows.append({
            "requirement_id": rid,
            "builder_dependencies": sorted(deps),
        })

    check_rows: list[dict[str, Any]] = []
    check_ids: set[str] = set()
    for index, row in enumerate(checks):
        if not isinstance(row, Mapping):
            raise ValueError(f"CHECK_NOT_OBJECT:{index}")
        cid = row.get("id")
        if not isinstance(cid, str) or not cid or cid in check_ids:
            raise ValueError(f"CHECK_ID_INVALID_OR_DUPLICATE:{index}")
        check_ids.add(cid)
        covers = _string_list(row.get("covers", []), f"CHECK_COVERS:{cid}")
        unknown = sorted(set(covers) - req_ids)
        if unknown:
            raise ValueError("CHECK_COVERS_UNKNOWN_REQUIREMENT:" + cid + ":" + ",".join(unknown))
        deps = _string_list(row.get("dependencies", []), f"CHECK_DEPENDENCIES:{cid}")
        provenance = row.get("provenance")
        if not isinstance(provenance, str) or not provenance.strip():
            raise ValueError("CHECK_PROVENANCE_INVALID:" + cid)
        derived = row.get("derived_from_builder_output", False)
        if not isinstance(derived, bool):
            raise ValueError("CHECK_DERIVED_FROM_BUILDER_OUTPUT_INVALID:" + cid)
        check_rows.append({
            "check_id": cid,
            "covers": sorted(covers),
            "dependencies": sorted(deps),
            "provenance": provenance.strip(),
            "derived_from_builder_output": derived,
        })

    projection = {
        "requirements": sorted(req_rows, key=lambda x: x["requirement_id"]),
        "checks": sorted(check_rows, key=lambda x: x["check_id"]),
    }
    return projection


def projection_sha256(model: Mapping[str, Any]) -> str:
    return sha256(_canon(dependency_provenance_projection(model))).hexdigest()


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
            "status": "FAIL_CLOSED__DEPENDENCY_PROVENANCE_MODEL_INVALID",
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
            "status": "OPEN__DEPENDENCY_PROVENANCE_BINDING_REQUIRED",
            "errors": ["DEPENDENCY_PROVENANCE_BINDING_MISSING"],
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
            "status": "FAIL_CLOSED__DEPENDENCY_PROVENANCE_BINDING_INVALID",
            "errors": ["DEPENDENCY_PROVENANCE_BINDING_NOT_OBJECT"],
            "atom_id": ATOM_ID,
            "atom_truth_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    try:
        if set(binding) - {"receipt", "verification"}:
            raise ValueError("DEPENDENCY_PROVENANCE_BINDING_FIELDS_INVALID")

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
        if receipt.get("dependency_provenance_projection_sha256") != projection_digest:
            raise ValueError("RECEIPT_PROJECTION_DIGEST_MISMATCH")
        audit_id = receipt.get("audit_id")
        producer_id = receipt.get("producer_id")
        if not isinstance(audit_id, str) or not audit_id.strip():
            raise ValueError("RECEIPT_AUDIT_ID_INVALID")
        if not isinstance(producer_id, str) or not producer_id.strip():
            raise ValueError("RECEIPT_PRODUCER_ID_INVALID")

        required_receipt_truth = (
            "dependency_labels_source_verified",
            "provenance_labels_authorized",
            "independence_relevant_edges_complete",
            "no_undeclared_nonraw_dependencies",
            "builder_output_derivation_labels_truthful",
            "source_authority_complete",
        )
        for key in required_receipt_truth:
            if receipt.get(key) is not True:
                raise ValueError("RECEIPT_PREMISE_UNPROVED:" + key)

        if verification.get("schema") != VERIFY_SCHEMA:
            raise ValueError("VERIFICATION_SCHEMA_INVALID")
        if verification.get("subject_git_blob_sha") != receipt_blob:
            raise ValueError("VERIFICATION_SUBJECT_BLOB_MISMATCH")
        if verification.get("subject_model_sha256") != digest:
            raise ValueError("VERIFICATION_MODEL_DIGEST_MISMATCH")
        if verification.get("dependency_provenance_projection_sha256") != projection_digest:
            raise ValueError("VERIFICATION_PROJECTION_DIGEST_MISMATCH")
        if verification.get("audit_id") != audit_id:
            raise ValueError("VERIFICATION_AUDIT_ID_MISMATCH")
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

        required_verification_truth = (
            "pass",
            "independent_verified",
            "dependency_labels_source_verified",
            "provenance_labels_authorized",
            "independence_relevant_edges_complete",
            "no_undeclared_nonraw_dependencies",
            "builder_output_derivation_labels_truthful",
            "source_authority_completeness_verified",
        )
        for key in required_verification_truth:
            if verification.get(key) is not True:
                raise ValueError("VERIFICATION_PREMISE_UNPROVED:" + key)

        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__DEPENDENCY_PROVENANCE_TRUTH_ATOM_INDEPENDENTLY_BOUND",
            "atom_id": ATOM_ID,
            "atom_semantics": ATOM_SEMANTICS,
            "atom_truth_authorized": True,
            "proof_basis": "CONTENT_ADDRESSED_INDEPENDENT_DEPENDENCY_PROVENANCE_AUDIT",
            "model_sha256": digest,
            "projection_sha256": projection_digest,
            "audit_id": audit_id,
            "producer_id": producer_id,
            "independent_verifier_id": verifier_id,
            "verification_method": verification.get("verification_method"),
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
            "status": "FAIL_CLOSED__DEPENDENCY_PROVENANCE_ATOM_UNPROVED",
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
