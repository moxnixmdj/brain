"""Fail-closed guard for executable-refinement verification receipts V1.

A declarative refinement certificate is not semantic proof. A verified receipt
must bind the exact certificate and concrete route, cover the certificate's
declared transition partition, and point at an exact proof artifact. The guard
validates promotion structure only; the proof artifact's method remains a
declared dependency of the receipt.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_EXECUTABLE_REFINEMENT_VERIFICATION_RECEIPT_V1"

ALLOWED_METHODS = frozenset(
    {
        "FORMAL_REFINEMENT_CHECK",
        "MODEL_CHECKED_REFINEMENT",
        "EXHAUSTIVE_FINITE_TRANSITION_CHECK",
        "INDEPENDENT_DIFFERENTIAL_REPLAY",
    }
)


class RefinementReceiptFailClosed(ValueError):
    pass


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _repo_path(root: Path, raw: Any) -> Path:
    value = str(raw or "").strip()
    p = Path(value)
    if not value or p.is_absolute() or ".." in p.parts:
        raise RefinementReceiptFailClosed("PROOF_ARTIFACT_PATH_INVALID")
    full = (root / p).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError as exc:
        raise RefinementReceiptFailClosed(
            "PROOF_ARTIFACT_PATH_OUTSIDE_REPO"
        ) from exc
    if not full.is_file():
        raise RefinementReceiptFailClosed("PROOF_ARTIFACT_MISSING")
    return full


def _certificate_case_ids(certificate: Mapping[str, Any]) -> set[str]:
    transition = certificate.get("transition_refinement")
    if not isinstance(transition, Mapping):
        raise RefinementReceiptFailClosed(
            "CERTIFICATE_TRANSITION_REFINEMENT_INVALID"
        )
    rows = transition.get("classes")
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes))
        or not rows
    ):
        raise RefinementReceiptFailClosed(
            "CERTIFICATE_TRANSITION_CLASSES_INVALID"
        )
    ids: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise RefinementReceiptFailClosed(
                "CERTIFICATE_TRANSITION_CLASS_INVALID"
            )
        case_id = str(row.get("case_id") or "").strip()
        if not case_id or case_id in ids:
            raise RefinementReceiptFailClosed(
                "CERTIFICATE_TRANSITION_CASE_ID_INVALID"
            )
        ids.add(case_id)
    return ids


def validate_receipt(
    receipt: Mapping[str, Any],
    *,
    certificate: Mapping[str, Any],
    expected_certificate_git_blob_sha: str,
    expected_concrete_route_git_blob_sha: str,
    expected_subject_id: str,
    repo_root: Path,
) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        raise RefinementReceiptFailClosed("RECEIPT_NOT_OBJECT")
    if receipt.get("schema") != SCHEMA:
        raise RefinementReceiptFailClosed("RECEIPT_SCHEMA_INVALID")
    if receipt.get("refinement_verified") is not True:
        raise RefinementReceiptFailClosed("RECEIPT_NOT_REFINEMENT_VERIFIED")
    if receipt.get("subject_id") != expected_subject_id:
        raise RefinementReceiptFailClosed("RECEIPT_SUBJECT_MISMATCH")
    if certificate.get("subject_id") != expected_subject_id:
        raise RefinementReceiptFailClosed("CERTIFICATE_SUBJECT_MISMATCH")
    if receipt.get("certificate_git_blob_sha") != expected_certificate_git_blob_sha:
        raise RefinementReceiptFailClosed("RECEIPT_CERTIFICATE_BINDING_MISMATCH")
    if (
        receipt.get("concrete_route_git_blob_sha")
        != expected_concrete_route_git_blob_sha
    ):
        raise RefinementReceiptFailClosed("RECEIPT_ROUTE_BINDING_MISMATCH")

    method = str(receipt.get("verification_method") or "").strip()
    if method not in ALLOWED_METHODS:
        raise RefinementReceiptFailClosed("RECEIPT_VERIFICATION_METHOD_UNSUPPORTED")

    expected_cases = _certificate_case_ids(certificate)
    verified_cases = receipt.get("verified_transition_case_ids")
    if (
        not isinstance(verified_cases, Sequence)
        or isinstance(verified_cases, (str, bytes))
    ):
        raise RefinementReceiptFailClosed(
            "RECEIPT_VERIFIED_TRANSITION_CASES_INVALID"
        )
    clean_cases = [str(x) for x in verified_cases]
    if len(clean_cases) != len(set(clean_cases)):
        raise RefinementReceiptFailClosed(
            "RECEIPT_VERIFIED_TRANSITION_CASE_DUPLICATE"
        )
    if set(clean_cases) != expected_cases:
        raise RefinementReceiptFailClosed(
            "RECEIPT_TRANSITION_COVERAGE_MISMATCH"
        )

    proof = receipt.get("proof_artifact")
    if not isinstance(proof, Mapping) or set(proof) != {
        "path",
        "git_blob_sha",
    }:
        raise RefinementReceiptFailClosed("RECEIPT_PROOF_ARTIFACT_BINDING_INVALID")
    proof_path = _repo_path(repo_root, proof.get("path"))
    if proof.get("git_blob_sha") != git_blob_sha(proof_path):
        raise RefinementReceiptFailClosed("RECEIPT_PROOF_ARTIFACT_BLOB_DRIFT")
    try:
        proof_obj = json.loads(proof_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RefinementReceiptFailClosed(
            "RECEIPT_PROOF_ARTIFACT_JSON_INVALID"
        ) from exc
    if not isinstance(proof_obj, Mapping):
        raise RefinementReceiptFailClosed(
            "RECEIPT_PROOF_ARTIFACT_NOT_OBJECT"
        )
    if proof_obj.get("pass") is not True:
        raise RefinementReceiptFailClosed(
            "RECEIPT_PROOF_ARTIFACT_NOT_PASS"
        )
    if proof_obj.get("subject_id") != expected_subject_id:
        raise RefinementReceiptFailClosed(
            "RECEIPT_PROOF_ARTIFACT_SUBJECT_MISMATCH"
        )
    if proof_obj.get("terminal_credit_delta") != 0:
        raise RefinementReceiptFailClosed(
            "RECEIPT_PROOF_ARTIFACT_NONZERO_TERMINAL_CREDIT"
        )

    if receipt.get("verification_authority_mutated") is not False:
        raise RefinementReceiptFailClosed(
            "RECEIPT_VERIFICATION_AUTHORITY_MUTATION_INVALID"
        )
    if receipt.get("execution_authority") is not False:
        raise RefinementReceiptFailClosed("RECEIPT_EXECUTION_AUTHORITY_INVALID")
    if receipt.get("terminal_authority") is not False:
        raise RefinementReceiptFailClosed("RECEIPT_TERMINAL_AUTHORITY_INVALID")
    if receipt.get("terminal_credit_delta") != 0:
        raise RefinementReceiptFailClosed("RECEIPT_NONZERO_TERMINAL_CREDIT")

    return {
        "pass": True,
        "schema": SCHEMA,
        "subject_id": expected_subject_id,
        "refinement_verified": True,
        "verification_method": method,
        "verified_transition_case_ids": sorted(expected_cases),
        "proof_artifact_path": str(proof["path"]),
        "proof_artifact_git_blob_sha": str(proof["git_blob_sha"]),
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
