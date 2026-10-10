from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from canonical.runtime.executable_refinement_receipt_v1 import (
    PROTOCOL,
    SCHEMA,
    validate_executable_refinement,
)


def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def sha256_json(value) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def make_fixture(
    *,
    verifier_pass: bool = True,
    receipt_mutator=None,
    result_mutator=None,
):
    td = tempfile.TemporaryDirectory()
    root = Path(td.name)
    (root / "certs").mkdir()
    (root / "verifiers").mkdir()
    (root / "receipts").mkdir()

    subject_id = "CURRENT_UNIFIED_COGNITIVE_FABRIC"
    cert = root / "certs/refinement.json"
    cert.write_text(
        json.dumps(
            {
                "schema": "TEST_EXECUTABLE_REFINEMENT_CERTIFICATE_V1",
                "subject_id": subject_id,
                "abstract_spec": {"kind": "TEST_ABSTRACT"},
                "concrete": {"kind": "TEST_CONCRETE"},
                "terminal_credit_delta": 0,
            }
        ),
        encoding="utf-8",
    )

    verifier = root / "verifiers/check.py"
    verifier.write_text(
        "def verify_refinement(*, root, certificate_path, subject_id):\n"
        "    import json\n"
        "    cert=json.loads(certificate_path.read_text(encoding='utf-8'))\n"
        f"    return {{'pass': {verifier_pass!r}, 'subject_id': subject_id, 'certificate_subject_id': cert.get('subject_id'), 'refinement_fact': 'checked', 'liveness_preserved': True}}\n",
        encoding="utf-8",
    )

    rerun = {
        "pass": verifier_pass,
        "subject_id": subject_id,
        "certificate_subject_id": subject_id,
        "refinement_fact": "checked",
        "liveness_preserved": True,
    }
    if result_mutator is not None:
        result_mutator(rerun)

    cert_ref = {"path": "certs/refinement.json", "git_blob_sha": blob(cert)}
    verifier_ref = {"path": "verifiers/check.py", "git_blob_sha": blob(verifier)}
    receipt = {
        "schema": SCHEMA,
        "status": "PASS__INDEPENDENT_EXECUTABLE_REFINEMENT_VERIFICATION",
        "pass": True,
        "verifier_protocol": PROTOCOL,
        "independent": True,
        "refinement_claim_verified": True,
        "subject_id": subject_id,
        "proof_mode": "INDEPENDENT_REPLAY",
        "certificate": dict(cert_ref),
        "semantic_verifier": dict(verifier_ref),
        "verifier_result_sha256": sha256_json(rerun),
        "errors": [],
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
    if receipt_mutator is not None:
        receipt_mutator(receipt)

    receipt_path = root / "receipts/verify.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    slot = {
        "subject_id": subject_id,
        "status": "REFINEMENT_VERIFIED",
        "refinement_certificate": cert_ref,
        "semantic_verifier": verifier_ref,
        "independent_verification": {
            "path": "receipts/verify.json",
            "git_blob_sha": blob(receipt_path),
        },
    }
    return td, root, slot, subject_id


def test_valid_content_bound_rerun_passes():
    td, root, slot, subject_id = make_fixture()
    try:
        out = validate_executable_refinement(root, slot, subject_id)
        assert out["pass"] is True, out
        assert out["status"] == "PASS__EXECUTABLE_REFINEMENT_VERIFIED"
        assert out["subject_id"] == subject_id
        assert out["terminal_credit_delta"] == 0
    finally:
        td.cleanup()


def test_content_addressed_empty_receipt_is_rejected():
    td, root, slot, subject_id = make_fixture()
    try:
        p = root / slot["independent_verification"]["path"]
        p.write_text("{}", encoding="utf-8")
        slot["independent_verification"]["git_blob_sha"] = blob(p)
        out = validate_executable_refinement(root, slot, subject_id)
        assert out["pass"] is False
        assert "RECEIPT_SCHEMA_INVALID" in out["errors"]
    finally:
        td.cleanup()


def test_foreign_subject_receipt_is_rejected():
    td, root, slot, subject_id = make_fixture(
        receipt_mutator=lambda r: r.__setitem__("subject_id", "FOREIGN_SUBJECT")
    )
    try:
        out = validate_executable_refinement(root, slot, subject_id)
        assert out["pass"] is False
        assert "RECEIPT_SUBJECT_MISMATCH" in out["errors"]
    finally:
        td.cleanup()


def test_verifier_rejection_dominates_stored_pass():
    td, root, slot, subject_id = make_fixture(verifier_pass=False)
    try:
        out = validate_executable_refinement(root, slot, subject_id)
        assert out["pass"] is False
        assert "SEMANTIC_VERIFIER_REJECTED_REFINEMENT" in out["errors"]
    finally:
        td.cleanup()


def test_receipt_must_bind_exact_rerun_result():
    td, root, slot, subject_id = make_fixture(
        receipt_mutator=lambda r: r.__setitem__("verifier_result_sha256", "0" * 64)
    )
    try:
        out = validate_executable_refinement(root, slot, subject_id)
        assert out["pass"] is False
        assert "RECEIPT_RERUN_RESULT_MISMATCH" in out["errors"]
    finally:
        td.cleanup()


def test_stale_verifier_blob_is_rejected_before_execution():
    td, root, slot, subject_id = make_fixture()
    try:
        slot["semantic_verifier"]["git_blob_sha"] = "0" * 40
        out = validate_executable_refinement(root, slot, subject_id)
        assert out["pass"] is False
        assert "SEMANTIC_VERIFIER_BLOB_SHA_MISMATCH" in out["errors"]
    finally:
        td.cleanup()


def test_stale_certificate_blob_is_rejected_before_execution():
    td, root, slot, subject_id = make_fixture()
    try:
        slot["refinement_certificate"]["git_blob_sha"] = "0" * 40
        out = validate_executable_refinement(root, slot, subject_id)
        assert out["pass"] is False
        assert "REFINEMENT_CERTIFICATE_BLOB_SHA_MISMATCH" in out["errors"]
    finally:
        td.cleanup()


def test_slot_subject_must_match_requested_subject():
    td, root, slot, subject_id = make_fixture()
    try:
        slot["subject_id"] = "OTHER"
        out = validate_executable_refinement(root, slot, subject_id)
        assert out["pass"] is False
        assert "SLOT_SUBJECT_MISMATCH" in out["errors"]
    finally:
        td.cleanup()


def test_nonzero_credit_in_receipt_is_rejected():
    td, root, slot, subject_id = make_fixture(
        receipt_mutator=lambda r: r.__setitem__("capability_credit_delta", 1)
    )
    try:
        out = validate_executable_refinement(root, slot, subject_id)
        assert out["pass"] is False
        assert "RECEIPT_NONZERO_CAPABILITY_CREDIT" in out["errors"]
    finally:
        td.cleanup()


def test_liveness_requirement_is_bound_to_rerun_result():
    td, root, slot, subject_id = make_fixture(
        result_mutator=lambda r: r.__setitem__("liveness_preserved", False)
    )
    try:
        slot["liveness_required"] = True
        out = validate_executable_refinement(root, slot, subject_id)
        assert out["pass"] is False
        assert "LIVENESS_REFINEMENT_REQUIRED_BUT_UNPROVED" in out["errors"]
    finally:
        td.cleanup()
