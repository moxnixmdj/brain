from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from canonical.runtime.coverage_root_semantic_receipt_v1 import (
    SCHEMA,
    PROTOCOL,
    validate_semantic_root_slot,
)
from canonical.runtime.coverage_root_certificate_registry_guard_v1 import validate as validate_registry
from canonical.runtime.coverage_claim_scope_guard_v1 import compute_claim_id


def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def sha256_json(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def make_fixture(*, verifier_pass=True, receipt_mutator=None):
    td = tempfile.TemporaryDirectory()
    root = Path(td.name)
    (root / "certs").mkdir()
    (root / "verifiers").mkdir()
    (root / "receipts").mkdir()

    root_id = "CC_R1_REALITY_CONTAINMENT_V1"
    claim = {
        "claim_id": "a" * 64,
        "scope_sha256": "b" * 64,
        "semantics_sha256": "c" * 64,
    }

    cert = root / "certs/root.json"
    cert.write_text(json.dumps({"root_id": root_id, "claim_id": claim["claim_id"]}), encoding="utf-8")

    verifier = root / "verifiers/check.py"
    verifier.write_text(
        "def verify_certificate(*, root, certificate_path, active_claim, root_id):\n"
        f"    return {{'pass': {verifier_pass!r}, 'root_id': root_id, 'claim_id': active_claim['claim_id'], 'semantic_fact': 'checked'}}\n",
        encoding="utf-8",
    )

    rerun = {
        "pass": verifier_pass,
        "root_id": root_id,
        "claim_id": claim["claim_id"],
        "semantic_fact": "checked",
    }
    cert_ref = {"path": "certs/root.json", "git_blob_sha": blob(cert)}
    verifier_ref = {"path": "verifiers/check.py", "git_blob_sha": blob(verifier)}
    receipt = {
        "schema": SCHEMA,
        "status": "PASS__INDEPENDENT_SEMANTIC_VERIFICATION",
        "pass": True,
        "verifier_protocol": PROTOCOL,
        "independent": True,
        "semantic_claim_verified": True,
        "root_id": root_id,
        "claim_id": claim["claim_id"],
        "proof_mode": "INDEPENDENT_REPLAY",
        "certificate": dict(cert_ref),
        "semantic_verifier": dict(verifier_ref),
        "verifier_result_sha256": sha256_json(rerun),
        "errors": [],
        "terminal_credit_delta": 0,
    }
    if receipt_mutator is not None:
        receipt_mutator(receipt)

    receipt_path = root / "receipts/verify.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    slot = {
        "root_id": root_id,
        "status": "PROVED_CURRENT",
        "certificate": cert_ref,
        "semantic_verifier": verifier_ref,
        "independent_verification": {
            "path": "receipts/verify.json",
            "git_blob_sha": blob(receipt_path),
        },
    }
    return td, root, slot, claim


def test_valid_semantic_receipt_passes():
    td, root, slot, claim = make_fixture()
    try:
        out = validate_semantic_root_slot(root, slot, claim)
        assert out["pass"] is True, out
        assert out["status"] == "PASS__EXECUTABLE_SEMANTIC_ROOT_CERTIFICATE_VERIFICATION"
    finally:
        td.cleanup()


def test_content_addressed_empty_receipt_is_rejected():
    td, root, slot, claim = make_fixture()
    try:
        receipt_path = root / slot["independent_verification"]["path"]
        receipt_path.write_text("{}", encoding="utf-8")
        slot["independent_verification"]["git_blob_sha"] = blob(receipt_path)
        out = validate_semantic_root_slot(root, slot, claim)
        assert out["pass"] is False
        assert "RECEIPT_SCHEMA_INVALID" in out["errors"]
    finally:
        td.cleanup()


def test_foreign_root_receipt_is_rejected():
    td, root, slot, claim = make_fixture(
        receipt_mutator=lambda r: r.__setitem__("root_id", "CC_R2_MISSION_SOUNDNESS_V1")
    )
    try:
        out = validate_semantic_root_slot(root, slot, claim)
        assert out["pass"] is False
        assert "RECEIPT_ROOT_MISMATCH" in out["errors"]
    finally:
        td.cleanup()


def test_foreign_claim_receipt_is_rejected():
    td, root, slot, claim = make_fixture(
        receipt_mutator=lambda r: r.__setitem__("claim_id", "d" * 64)
    )
    try:
        out = validate_semantic_root_slot(root, slot, claim)
        assert out["pass"] is False
        assert "RECEIPT_CLAIM_MISMATCH" in out["errors"]
    finally:
        td.cleanup()


def test_verifier_rejection_cannot_be_overridden_by_pass_receipt():
    td, root, slot, claim = make_fixture(verifier_pass=False)
    try:
        out = validate_semantic_root_slot(root, slot, claim)
        assert out["pass"] is False
        assert "SEMANTIC_VERIFIER_REJECTED_CERTIFICATE" in out["errors"]
    finally:
        td.cleanup()


def test_receipt_must_bind_exact_rerun_result():
    td, root, slot, claim = make_fixture(
        receipt_mutator=lambda r: r.__setitem__("verifier_result_sha256", "0" * 64)
    )
    try:
        out = validate_semantic_root_slot(root, slot, claim)
        assert out["pass"] is False
        assert "RECEIPT_RERUN_RESULT_MISMATCH" in out["errors"]
    finally:
        td.cleanup()


def test_stale_verifier_hash_is_rejected_before_execution():
    td, root, slot, claim = make_fixture()
    try:
        slot["semantic_verifier"]["git_blob_sha"] = "0" * 40
        out = validate_semantic_root_slot(root, slot, claim)
        assert out["pass"] is False
        assert "SEMANTIC_VERIFIER_BLOB_SHA_MISMATCH" in out["errors"]
    finally:
        td.cleanup()


def test_registry_proved_slot_requires_semantic_verifier():
    root = Path(__file__).resolve().parents[2]
    registry = json.loads((root / "canonical/governance/COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1.json").read_text(encoding="utf-8"))
    mission = json.loads((root / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json").read_text(encoding="utf-8"))
    authority_path = root / mission["authoritative_source"]["path"]
    mission_pointer_sha = blob(root / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json")

    claim = {
        "claim_kind": "CHECKPOINT_ACCEPTANCE",
        "mission_blob_sha": mission_pointer_sha,
        "scope_sha256": "1" * 64,
        "target_predicate_sha256": "2" * 64,
        "semantics_sha256": "3" * 64,
        "epoch": "E1",
        "authority_id": "TEST",
        "terminal_credit_delta": 0,
    }
    claim["claim_id"] = compute_claim_id(claim)
    registry["active_claim"] = claim
    registry["certificate_slots"][0] = {
        "root_id": "CC_R1_REALITY_CONTAINMENT_V1",
        "status": "PROVED_CURRENT",
        "certificate": {
            "root_id": "CC_R1_REALITY_CONTAINMENT_V1",
            "mission_authority_blob_sha": blob(authority_path),
            "path": "x.json",
            "git_blob_sha": "abc",
            "claim_binding": dict(claim),
        },
        "independent_verification": {
            "path": "v.json",
            "git_blob_sha": "def",
            "claim_id": claim["claim_id"],
        },
    }
    registry["currently_proved_root_certificates"] = 1
    registry["currently_open_root_certificates"] = 2
    registry["r4_proof_closure"] = False
    out = validate_registry(
        registry,
        current_mission_pointer=mission,
        current_mission_authority_blob_sha=blob(authority_path),
        current_mission_pointer_blob_sha=mission_pointer_sha,
    )
    assert out["pass"] is False
    assert "PROVED_SLOT_SEMANTIC_VERIFIER_MISSING:CC_R1_REALITY_CONTAINMENT_V1" in out["errors"]
