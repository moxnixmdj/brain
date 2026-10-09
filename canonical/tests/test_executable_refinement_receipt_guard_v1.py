from __future__ import annotations

import json
from pathlib import Path

import pytest

from canonical.runtime.executable_refinement_receipt_guard_v1 import (
    SCHEMA,
    RefinementReceiptFailClosed,
    git_blob_sha,
    validate_receipt,
)


def write(root: Path, rel: str, value) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        p.write_text(value, encoding="utf-8")
    else:
        p.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return p


def fixture(root: Path):
    proof = write(
        root,
        "canonical/verification/proof.json",
        {"pass": True, "subject_id": "route", "terminal_credit_delta": 0},
    )
    cert = {
        "subject_id": "route",
        "transition_refinement": {
            "classes": [
                {"case_id": "A", "kind": "PASS"},
                {"case_id": "B", "kind": "FAIL_CLOSED"},
            ]
        },
    }
    receipt = {
        "schema": SCHEMA,
        "subject_id": "route",
        "refinement_verified": True,
        "certificate_git_blob_sha": "c" * 40,
        "concrete_route_git_blob_sha": "r" * 40,
        "verification_method": "EXHAUSTIVE_FINITE_TRANSITION_CHECK",
        "verified_transition_case_ids": ["A", "B"],
        "proof_artifact": {
            "path": "canonical/verification/proof.json",
            "git_blob_sha": git_blob_sha(proof),
        },
        "verification_authority_mutated": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    return cert, receipt, proof


def validate(root: Path, cert, receipt):
    return validate_receipt(
        receipt,
        certificate=cert,
        expected_certificate_git_blob_sha="c" * 40,
        expected_concrete_route_git_blob_sha="r" * 40,
        expected_subject_id="route",
        repo_root=root,
    )


def test_valid_receipt_requires_complete_exact_case_coverage(tmp_path):
    cert, receipt, _ = fixture(tmp_path)
    out = validate(tmp_path, cert, receipt)
    assert out["pass"] is True
    assert out["refinement_verified"] is True
    assert out["verified_transition_case_ids"] == ["A", "B"]
    assert out["terminal_credit_delta"] == 0


def test_arbitrary_json_with_true_flag_is_rejected(tmp_path):
    cert, receipt, _ = fixture(tmp_path)
    receipt.pop("schema")
    with pytest.raises(
        RefinementReceiptFailClosed, match="RECEIPT_SCHEMA_INVALID"
    ):
        validate(tmp_path, cert, receipt)


def test_unrecognized_verification_method_is_rejected(tmp_path):
    cert, receipt, _ = fixture(tmp_path)
    receipt["verification_method"] = "TRUST_ME"
    with pytest.raises(
        RefinementReceiptFailClosed,
        match="RECEIPT_VERIFICATION_METHOD_UNSUPPORTED",
    ):
        validate(tmp_path, cert, receipt)


def test_partial_transition_coverage_is_rejected(tmp_path):
    cert, receipt, _ = fixture(tmp_path)
    receipt["verified_transition_case_ids"] = ["A"]
    with pytest.raises(
        RefinementReceiptFailClosed,
        match="RECEIPT_TRANSITION_COVERAGE_MISMATCH",
    ):
        validate(tmp_path, cert, receipt)


def test_stale_proof_artifact_is_rejected(tmp_path):
    cert, receipt, proof = fixture(tmp_path)
    proof.write_text(
        json.dumps(
            {"pass": False, "subject_id": "route", "terminal_credit_delta": 0}
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        RefinementReceiptFailClosed,
        match="RECEIPT_PROOF_ARTIFACT_BLOB_DRIFT",
    ):
        validate(tmp_path, cert, receipt)


def test_nonpassing_proof_artifact_is_rejected(tmp_path):
    cert, receipt, proof = fixture(tmp_path)
    proof.write_text(
        json.dumps(
            {"pass": False, "subject_id": "route", "terminal_credit_delta": 0}
        )
        + "\n",
        encoding="utf-8",
    )
    receipt["proof_artifact"]["git_blob_sha"] = git_blob_sha(proof)
    with pytest.raises(
        RefinementReceiptFailClosed,
        match="RECEIPT_PROOF_ARTIFACT_NOT_PASS",
    ):
        validate(tmp_path, cert, receipt)


def test_proof_artifact_outside_verification_scope_is_rejected(tmp_path):
    cert, receipt, _ = fixture(tmp_path)
    other = write(
        tmp_path,
        "canonical/governance/proof.json",
        {"pass": True, "subject_id": "route", "terminal_credit_delta": 0},
    )
    receipt["proof_artifact"] = {
        "path": "canonical/governance/proof.json",
        "git_blob_sha": git_blob_sha(other),
    }
    with pytest.raises(
        RefinementReceiptFailClosed,
        match="RECEIPT_PROOF_ARTIFACT_OUTSIDE_VERIFICATION_SCOPE",
    ):
        validate(tmp_path, cert, receipt)


def test_authority_leak_is_rejected(tmp_path):
    cert, receipt, _ = fixture(tmp_path)
    receipt["execution_authority"] = True
    with pytest.raises(
        RefinementReceiptFailClosed,
        match="RECEIPT_EXECUTION_AUTHORITY_INVALID",
    ):
        validate(tmp_path, cert, receipt)
