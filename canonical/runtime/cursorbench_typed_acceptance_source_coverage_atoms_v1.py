"""Proof-carrying source-to-model coverage for the two remaining semantic atoms.

Proves exactly:
- SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1
- SPEC_ACCEPT_FAILURE_MODE_COMPLETENESS_V1

Authority requires:
1. an exact content-addressed lossless raw-task contract;
2. an exact normalized typed-acceptance model;
3. a receipt that maps every raw acceptance obligation to reviewed model requirements;
4. a complete per-requirement failure-mode universe matching the model's generated
   obligations; and
5. producer-independent verification of the semantic entailment and completeness
   claims.

The model and receipt cannot self-certify semantic truth. Missing evidence remains
OPEN; malformed or contradictory evidence FAILS CLOSED.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.cursorbench_typed_acceptance_supported_transform_atom_v1 import (
    model_sha256,
)
from canonical.runtime.independent_acceptance_model import generated_obligations

SCHEMA = "PROJECT_BRAIN_CURSORBENCH_TYPED_ACCEPTANCE_SOURCE_COVERAGE_ATOMS_PROOF_V1"
TYPED_SEMANTICS_ATOM_ID = "SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1"
FAILURE_COMPLETENESS_ATOM_ID = "SPEC_ACCEPT_FAILURE_MODE_COMPLETENESS_V1"
PROVED_ATOM_IDS = (TYPED_SEMANTICS_ATOM_ID, FAILURE_COMPLETENESS_ATOM_ID)
RECEIPT_SCHEMA = "PROJECT_BRAIN_TYPED_ACCEPTANCE_SOURCE_COVERAGE_RECEIPT_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_TYPED_ACCEPTANCE_SOURCE_COVERAGE_INDEPENDENT_VERIFICATION_V1"
SOURCE_SCHEMA = "PROJECT_BRAIN_LOSSLESS_RAW_TASK_CONTRACT_V1"


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _hex(value: Any, n: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == n
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _string_list(value: Any, label: str, *, nonempty: bool = True) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(label + "_NOT_LIST")
    if nonempty and not value:
        raise ValueError(label + "_EMPTY")
    if any(not isinstance(x, str) or not x for x in value):
        raise ValueError(label + "_INVALID")
    if len(set(value)) != len(value):
        raise ValueError(label + "_DUPLICATE")
    return list(value)


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


def _source_contract_obligations(source: Mapping[str, Any]) -> tuple[str, list[str]]:
    if source.get("schema") != SOURCE_SCHEMA:
        raise ValueError("SOURCE_CONTRACT_SCHEMA_INVALID")
    if source.get("pass") is not True:
        raise ValueError("SOURCE_CONTRACT_NOT_PASS")
    if source.get("nonwhitespace_source_coverage_complete") is not True:
        raise ValueError("SOURCE_CONTRACT_NONWHITESPACE_COVERAGE_INCOMPLETE")
    task_sha = source.get("task_sha256")
    if not _hex(task_sha, 64):
        raise ValueError("SOURCE_CONTRACT_TASK_SHA_INVALID")
    acceptance = source.get("acceptance_contract")
    if not isinstance(acceptance, Mapping):
        raise ValueError("SOURCE_ACCEPTANCE_CONTRACT_MISSING")
    if acceptance.get("raw_source_is_final_semantic_reference") is not True:
        raise ValueError("SOURCE_RAW_SEMANTIC_REFERENCE_NOT_FINAL")
    if acceptance.get("unverified_obligation_may_be_silently_dropped") is not False:
        raise ValueError("SOURCE_SILENT_DROP_NOT_FORBIDDEN")
    required = _string_list(
        acceptance.get("required_obligation_ids"),
        "SOURCE_REQUIRED_OBLIGATION_IDS",
    )
    rows = acceptance.get("obligations")
    if not isinstance(rows, list) or not rows:
        raise ValueError("SOURCE_OBLIGATIONS_INVALID_OR_EMPTY")
    observed: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"SOURCE_OBLIGATION_NOT_OBJECT:{index}")
        oid = row.get("obligation_id")
        if not isinstance(oid, str) or not oid:
            raise ValueError(f"SOURCE_OBLIGATION_ID_INVALID:{index}")
        observed.append(oid)
    if len(set(observed)) != len(observed):
        raise ValueError("SOURCE_OBLIGATION_ID_DUPLICATE")
    if set(observed) != set(required):
        raise ValueError("SOURCE_REQUIRED_OBLIGATION_SET_MISMATCH")
    return task_sha, sorted(required)


def _model_requirement_failure_modes(model: Mapping[str, Any]) -> dict[str, list[str]]:
    requirements = model.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("MODEL_REQUIREMENTS_INVALID_OR_EMPTY")
    out: dict[str, list[str]] = {}
    for index, row in enumerate(requirements):
        if not isinstance(row, Mapping):
            raise ValueError(f"MODEL_REQUIREMENT_NOT_OBJECT:{index}")
        rid = row.get("id")
        if not isinstance(rid, str) or not rid or rid in out:
            raise ValueError(f"MODEL_REQUIREMENT_ID_INVALID_OR_DUPLICATE:{index}")
        out[rid] = sorted(generated_obligations(dict(row)))
    return out


def source_model_projection(
    model: Mapping[str, Any],
    source_contract: Mapping[str, Any],
) -> dict[str, Any]:
    task_sha, obligation_ids = _source_contract_obligations(source_contract)
    req_modes = _model_requirement_failure_modes(model)
    return {
        "source_task_sha256": task_sha,
        "source_obligation_ids": obligation_ids,
        "model_requirement_ids": sorted(req_modes),
        "generated_failure_modes_by_requirement": req_modes,
    }


def projection_sha256(
    model: Mapping[str, Any],
    source_contract: Mapping[str, Any],
) -> str:
    return _sha(source_model_projection(model, source_contract))


def _validate_receipt_coverage(
    receipt: Mapping[str, Any],
    *,
    obligation_ids: list[str],
    req_modes: Mapping[str, list[str]],
) -> None:
    mappings = receipt.get("source_obligation_mappings")
    if not isinstance(mappings, list) or not mappings:
        raise ValueError("RECEIPT_SOURCE_OBLIGATION_MAPPINGS_INVALID")
    by_obligation: dict[str, set[str]] = {}
    mapped_requirements: set[str] = set()
    valid_reqs = set(req_modes)
    for index, row in enumerate(mappings):
        if not isinstance(row, Mapping):
            raise ValueError(f"RECEIPT_SOURCE_MAPPING_NOT_OBJECT:{index}")
        oid = row.get("source_obligation_id")
        if not isinstance(oid, str) or oid not in obligation_ids or oid in by_obligation:
            raise ValueError(f"RECEIPT_SOURCE_MAPPING_OBLIGATION_INVALID_OR_DUPLICATE:{index}")
        reqs = set(
            _string_list(
                row.get("model_requirement_ids"),
                f"RECEIPT_SOURCE_MAPPING_REQUIREMENTS:{oid}",
            )
        )
        unknown = sorted(reqs - valid_reqs)
        if unknown:
            raise ValueError(
                "RECEIPT_SOURCE_MAPPING_UNKNOWN_REQUIREMENT:" + oid + ":" + ",".join(unknown)
            )
        by_obligation[oid] = reqs
        mapped_requirements.update(reqs)
    if set(by_obligation) != set(obligation_ids):
        raise ValueError("RECEIPT_SOURCE_OBLIGATION_COVERAGE_INCOMPLETE")
    if mapped_requirements != valid_reqs:
        raise ValueError("RECEIPT_MODEL_REQUIREMENT_REVIEW_COVERAGE_INCOMPLETE")

    rows = receipt.get("failure_mode_coverage")
    if not isinstance(rows, list) or len(rows) != len(req_modes):
        raise ValueError("RECEIPT_FAILURE_MODE_COVERAGE_INVALID")
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"RECEIPT_FAILURE_MODE_ROW_NOT_OBJECT:{index}")
        rid = row.get("requirement_id")
        if not isinstance(rid, str) or rid not in req_modes or rid in seen:
            raise ValueError(f"RECEIPT_FAILURE_MODE_REQUIREMENT_INVALID_OR_DUPLICATE:{index}")
        seen.add(rid)
        modes = _string_list(
            row.get("complete_failure_modes"),
            f"RECEIPT_COMPLETE_FAILURE_MODES:{rid}",
            nonempty=False,
        )
        if sorted(modes) != sorted(req_modes[rid]):
            raise ValueError("RECEIPT_FAILURE_MODE_SET_MISMATCH:" + rid)
    if seen != set(req_modes):
        raise ValueError("RECEIPT_FAILURE_MODE_REQUIREMENT_COVERAGE_INCOMPLETE")


def verify(
    model: Mapping[str, Any],
    binding: Mapping[str, Any] | None,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]

    if not isinstance(model, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__MODEL_NOT_OBJECT",
            "errors": ["MODEL_NOT_OBJECT"],
            "proved_atom_ids": [],
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    if binding is None:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "OPEN__SOURCE_COVERAGE_BINDING_REQUIRED",
            "errors": ["SOURCE_COVERAGE_BINDING_MISSING"],
            "proved_atom_ids": [],
            "atom_truth_authorized": False,
            "evidence_missing": True,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    if not isinstance(binding, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__SOURCE_COVERAGE_BINDING_INVALID",
            "errors": ["SOURCE_COVERAGE_BINDING_NOT_OBJECT"],
            "proved_atom_ids": [],
            "atom_truth_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    try:
        if set(binding) - {"source_contract", "receipt", "verification"}:
            raise ValueError("SOURCE_COVERAGE_BINDING_FIELDS_INVALID")
        source_contract, source_path, source_blob = _bound_json(
            binding.get("source_contract"),
            root=root,
            prefixes=("canonical/governance/", "canonical/verification/"),
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

        model_digest = model_sha256(model)
        projection = source_model_projection(model, source_contract)
        projection_digest = _sha(projection)
        source_contract_digest = _sha(source_contract)
        obligation_ids = projection["source_obligation_ids"]
        req_modes = projection["generated_failure_modes_by_requirement"]

        if receipt.get("schema") != RECEIPT_SCHEMA:
            raise ValueError("RECEIPT_SCHEMA_INVALID")
        if receipt.get("subject_model_sha256") != model_digest:
            raise ValueError("RECEIPT_MODEL_DIGEST_MISMATCH")
        if receipt.get("source_contract_git_blob_sha") != source_blob:
            raise ValueError("RECEIPT_SOURCE_CONTRACT_BLOB_MISMATCH")
        if receipt.get("source_contract_sha256") != source_contract_digest:
            raise ValueError("RECEIPT_SOURCE_CONTRACT_DIGEST_MISMATCH")
        if receipt.get("source_model_projection_sha256") != projection_digest:
            raise ValueError("RECEIPT_PROJECTION_DIGEST_MISMATCH")
        audit_id = receipt.get("audit_id")
        producer_id = receipt.get("producer_id")
        if not isinstance(audit_id, str) or not audit_id.strip():
            raise ValueError("RECEIPT_AUDIT_ID_INVALID")
        if not isinstance(producer_id, str) or not producer_id.strip():
            raise ValueError("RECEIPT_PRODUCER_ID_INVALID")

        _validate_receipt_coverage(
            receipt,
            obligation_ids=obligation_ids,
            req_modes=req_modes,
        )

        for key in (
            "semantic_mapping_complete",
            "all_material_terminal_acceptance_semantics_bound",
            "failure_mode_universe_complete",
            "all_material_independently_knowable_failure_modes_represented",
            "source_authority_complete",
        ):
            if receipt.get(key) is not True:
                raise ValueError("RECEIPT_PREMISE_UNPROVED:" + key)

        if verification.get("schema") != VERIFY_SCHEMA:
            raise ValueError("VERIFICATION_SCHEMA_INVALID")
        if verification.get("subject_git_blob_sha") != receipt_blob:
            raise ValueError("VERIFICATION_SUBJECT_BLOB_MISMATCH")
        if verification.get("subject_model_sha256") != model_digest:
            raise ValueError("VERIFICATION_MODEL_DIGEST_MISMATCH")
        if verification.get("source_contract_git_blob_sha") != source_blob:
            raise ValueError("VERIFICATION_SOURCE_CONTRACT_BLOB_MISMATCH")
        if verification.get("source_contract_sha256") != source_contract_digest:
            raise ValueError("VERIFICATION_SOURCE_CONTRACT_DIGEST_MISMATCH")
        if verification.get("source_model_projection_sha256") != projection_digest:
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
        for key in (
            "pass",
            "independent_verified",
            "source_contract_integrity_verified",
            "source_obligation_mapping_semantics_verified",
            "source_obligation_coverage_complete_verified",
            "model_requirement_review_completeness_verified",
            "all_material_terminal_acceptance_semantics_bound_verified",
            "failure_mode_universe_completeness_verified",
            "all_material_independently_knowable_failure_modes_represented_verified",
            "source_authority_completeness_verified",
        ):
            if verification.get(key) is not True:
                raise ValueError("VERIFICATION_PREMISE_UNPROVED:" + key)

        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__TYPED_SEMANTICS_AND_FAILURE_MODE_COMPLETENESS_INDEPENDENTLY_BOUND",
            "proved_atom_ids": list(PROVED_ATOM_IDS),
            "proved_constraints": [
                {"op": "ATOM", "id": TYPED_SEMANTICS_ATOM_ID},
                {"op": "ATOM", "id": FAILURE_COMPLETENESS_ATOM_ID},
            ],
            "atom_truth_authorized": True,
            "proof_basis": "CONTENT_ADDRESSED_INDEPENDENT_SOURCE_TO_MODEL_COVERAGE_AUDIT",
            "model_sha256": model_digest,
            "source_contract_path": source_path,
            "source_contract_git_blob_sha": source_blob,
            "source_contract_sha256": source_contract_digest,
            "source_model_projection_sha256": projection_digest,
            "source_obligation_count": len(obligation_ids),
            "model_requirement_count": len(req_modes),
            "audit_id": audit_id,
            "producer_id": producer_id,
            "independent_verifier_id": verifier_id,
            "receipt_path": receipt_path,
            "receipt_git_blob_sha": receipt_blob,
            "verification_path": verification_path,
            "verification_git_blob_sha": verification_blob,
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
            "status": "FAIL_CLOSED__SOURCE_COVERAGE_ATOMS_UNPROVED",
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "proved_atom_ids": [],
            "proved_constraints": [],
            "atom_truth_authorized": False,
            "membership_self_certified": False,
            "whole_policy_condition_proved": False,
            "whole_specification_behavior_adequate": False,
            "whole_cursorbench_adequate": False,
            "acceptance_credit_delta": 0,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
