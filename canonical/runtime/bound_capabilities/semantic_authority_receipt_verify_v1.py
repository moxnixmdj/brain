"""Content-addressed verifier for already-admitted semantic authority receipts.

This module never decides semantic truth. It proves only that an exact receipt
object is present in the canonical admission registry under the requested role
and that the admission is bound to an independently verified repository artifact.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_SEMANTIC_AUTHORITY_RECEIPT_VERIFY_V1"
REGISTRY_SCHEMA = "PROJECT_BRAIN_SEMANTIC_AUTHORITY_ADMISSION_REGISTRY_V1"
REGISTRY_REL = "canonical/governance/SEMANTIC_AUTHORITY_ADMISSION_REGISTRY_V1.json"
ROLES = frozenset({
    "OEWN_DECISION_MANIFEST_AUTHORITY",
    "OEWN_SENSE_OBSERVATION_EVIDENCE",
})


class SemanticAuthorityReceiptVerifyError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _git_blob_sha(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _safe_repo_file(root: Path, rel: str, *, required_prefix: str) -> Path:
    text = str(rel or "").strip().replace("\\", "/")
    if not text or text.startswith("/") or ".." in Path(text).parts:
        raise SemanticAuthorityReceiptVerifyError("REPOSITORY_RELATIVE_PATH_REQUIRED")
    if not text.startswith(required_prefix):
        raise SemanticAuthorityReceiptVerifyError("PATH_PREFIX_FORBIDDEN:" + required_prefix)
    target = (root / text).resolve(strict=True)
    target.relative_to(root)
    if not target.is_file() or target.is_symlink():
        raise SemanticAuthorityReceiptVerifyError("REPOSITORY_FILE_INVALID:" + text)
    return target


def _load_registry(root: Path, registry_path: str | Path | None) -> dict[str, Any]:
    if registry_path is None:
        path = _safe_repo_file(root, REGISTRY_REL, required_prefix="canonical/governance/")
    else:
        path = Path(registry_path).resolve(strict=True)
        if not path.is_file() or path.is_symlink():
            raise SemanticAuthorityReceiptVerifyError("REGISTRY_FILE_INVALID")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping) or doc.get("schema") != REGISTRY_SCHEMA:
        raise SemanticAuthorityReceiptVerifyError("REGISTRY_SCHEMA_INVALID")
    if doc.get("status") not in {
        "ACTIVE__CONTENT_ADDRESSED_SEMANTIC_AUTHORITY_ADMISSIONS",
        "TEST_ONLY__CONTENT_ADDRESSED_SEMANTIC_AUTHORITY_ADMISSIONS",
    }:
        raise SemanticAuthorityReceiptVerifyError("REGISTRY_STATUS_INVALID")
    if not isinstance(doc.get("admissions"), list):
        raise SemanticAuthorityReceiptVerifyError("REGISTRY_ADMISSIONS_NOT_LIST")
    return deepcopy(dict(doc))


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "admission_verified": False,
        "reason": reason,
        "semantic_truth_inferred": False,
        "verification_authority_mutated": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def verify_receipt(
    receipt: Mapping[str, Any],
    *,
    role: str,
    root: str | Path,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    try:
        if not isinstance(receipt, Mapping):
            raise SemanticAuthorityReceiptVerifyError("RECEIPT_NOT_OBJECT")
        role_text = str(role or "").strip()
        if role_text not in ROLES:
            raise SemanticAuthorityReceiptVerifyError("SEMANTIC_ROLE_INVALID:" + role_text)
        repo_root = Path(root).resolve(strict=True)
        registry = _load_registry(repo_root, registry_path)
        receipt_doc = deepcopy(dict(receipt))
        receipt_sha = _sha256(receipt_doc)
        receipt_schema = str(receipt_doc.get("schema") or "").strip()
        if not receipt_schema:
            raise SemanticAuthorityReceiptVerifyError("RECEIPT_SCHEMA_REQUIRED")

        matches = []
        for raw in registry["admissions"]:
            if not isinstance(raw, Mapping) or raw.get("admitted") is not True:
                continue
            if (
                raw.get("role") == role_text
                and raw.get("receipt_sha256") == receipt_sha
                and raw.get("receipt_schema") == receipt_schema
            ):
                matches.append(deepcopy(dict(raw)))
        if not matches:
            return _fail(
                "EXACT_RECEIPT_NOT_ADMITTED_FOR_ROLE",
                role=role_text,
                receipt_sha256=receipt_sha,
                receipt_schema=receipt_schema,
            )
        if len(matches) != 1:
            return _fail(
                "MULTIPLE_EXACT_ADMISSIONS_FOR_RECEIPT",
                role=role_text,
                receipt_sha256=receipt_sha,
            )
        row = matches[0]
        admission_id = str(row.get("admission_id") or "").strip()
        if not admission_id:
            return _fail("ADMISSION_ID_REQUIRED")

        verification_rel = str(row.get("verification_path") or "")
        verification_path = _safe_repo_file(
            repo_root, verification_rel, required_prefix="canonical/verification/"
        )
        verification_raw = verification_path.read_bytes()
        actual_blob = _git_blob_sha(verification_raw)
        expected_blob = str(row.get("verification_git_blob_sha") or "").lower()
        if actual_blob != expected_blob:
            return _fail(
                "VERIFICATION_ARTIFACT_BLOB_MISMATCH",
                admission_id=admission_id,
                expected_git_blob_sha=expected_blob,
                actual_git_blob_sha=actual_blob,
            )
        verification = json.loads(verification_raw.decode("utf-8"))
        if not isinstance(verification, Mapping):
            return _fail("VERIFICATION_ARTIFACT_NOT_OBJECT", admission_id=admission_id)

        field = str(row.get("verification_receipt_sha256_field") or "").strip()
        if not field or verification.get(field) != receipt_sha:
            return _fail(
                "VERIFICATION_ARTIFACT_RECEIPT_BINDING_INVALID",
                admission_id=admission_id,
                required_field=field or None,
            )
        expected_status = str(row.get("verification_status") or "").strip()
        if not expected_status or verification.get("status") != expected_status:
            return _fail("VERIFICATION_ARTIFACT_STATUS_INVALID", admission_id=admission_id)
        if verification.get("independent_verifier_passed") is not True:
            return _fail("INDEPENDENT_VERIFIER_PASS_NOT_BOUND", admission_id=admission_id)
        if verification.get("verification_authority_mutated") is not False:
            return _fail("VERIFICATION_AUTHORITY_MUTATION_FORBIDDEN", admission_id=admission_id)
        if row.get("independent_verification_proved") is not True:
            return _fail(
                "ADMISSION_INDEPENDENT_VERIFICATION_FLAG_MISSING",
                admission_id=admission_id,
            )

        out = deepcopy(receipt_doc)
        out.update({
            "admission_verified": True,
            "admission_id": admission_id,
            "semantic_authority_role": role_text,
            "admission_registry_schema": REGISTRY_SCHEMA,
            "admission_verification_path": verification_rel,
            "admission_verification_git_blob_sha": actual_blob,
            "semantic_truth_inferred": False,
            "execution_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        })
        return out
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))


def run(args: Mapping[str, Any], root: str | Path) -> dict[str, Any]:
    if not isinstance(args, Mapping):
        return _fail("ARGS_NOT_OBJECT")
    raw = args.get("receipt_json")
    role = str(args.get("role") or "").strip()
    if not isinstance(raw, str) or not raw.strip():
        return _fail("RECEIPT_JSON_REQUIRED")
    try:
        receipt = json.loads(raw)
    except Exception as exc:
        return _fail("RECEIPT_JSON_INVALID:" + type(exc).__name__)
    if not isinstance(receipt, Mapping):
        return _fail("RECEIPT_JSON_NOT_OBJECT")
    return verify_receipt(receipt, role=role, root=root)
