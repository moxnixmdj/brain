"""Professional-quality whole-leaf scope certificate gate V1.

This gate adapts the already-active universal scope-completeness compiler to the
24 professional-quality leaves without granting semantic, execution, quality,
acceptance, promotion, or terminal authority.

A certificate is admitted only when:
- the exact leaf is one of the current V11 whole-leaf residuals,
- the exact certificate and its independent semantic-verification receipt are
  content-addressed,
- the existing universal scope compiler structurally proves scope completeness,
- the independent receipt binds the exact certificate, compiler, semantic
  verifier, and verifier tests, and
- all authority/credit fields remain fail-closed.

The result proves only whole-leaf *scope* completeness. Property truth and
professional-quality acceptance remain separate.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.universal_scope_closure_compiler_v1 import evaluate as evaluate_scope

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_CERTIFICATE_GATE_V1"
CERT_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_CERTIFICATE_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_SEMANTIC_VERIFY_V1"

LEDGER_PATH = "canonical/governance/PROFESSIONAL_QUALITY_WHOLE_LEAF_RESIDUAL_LEDGER_20261010_V1.json"
LEDGER_BLOB = "ae5503829ad340cccef287f37ff70e4ab9288d33"
SCOPE_COMPILER_PATH = "canonical/runtime/universal_scope_closure_compiler_v1.py"
SCOPE_COMPILER_BLOB = "b208255789b14e44e86c82c196e06b5c41b3d039"

def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "whole_leaf_scope_complete": False,
        "leaf_property_truth_authority": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }

def _resolve_bound(repo_root: Path, ref: Any, label: str) -> tuple[dict[str, Any] | None, str | None, str | None]:
    if not isinstance(ref, Mapping):
        return None, None, label + "_REF_INVALID"
    rel = ref.get("path")
    expected = ref.get("git_blob_sha")
    if not isinstance(rel, str) or not rel.startswith("canonical/"):
        return None, None, label + "_PATH_INVALID"
    if not isinstance(expected, str) or len(expected) != 40:
        return None, None, label + "_BLOB_INVALID"
    path = (repo_root / rel).resolve()
    try:
        path.relative_to(repo_root.resolve())
    except ValueError:
        return None, None, label + "_PATH_ESCAPE"
    if not path.is_file() or path.is_symlink():
        return None, None, label + "_MISSING"
    actual = _blob(path)
    if actual != expected:
        return None, actual, label + "_BLOB_STALE"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, actual, label + "_JSON_INVALID"
    if not isinstance(doc, dict):
        return None, actual, label + "_NOT_OBJECT"
    return doc, actual, None

def evaluate_documents(
    *,
    certificate: Mapping[str, Any],
    verification: Mapping[str, Any],
    expected_leaf_id: str,
    certificate_blob: str,
    semantic_verifier_blob: str,
    semantic_tests_blob: str,
) -> dict[str, Any]:
    if certificate.get("schema") != CERT_SCHEMA:
        return _fail("CERT_SCHEMA_INVALID")
    if verification.get("schema") != VERIFY_SCHEMA:
        return _fail("VERIFY_SCHEMA_INVALID")
    if certificate.get("leaf_id") != expected_leaf_id:
        return _fail("CERT_LEAF_MISMATCH")
    if verification.get("leaf_id") != expected_leaf_id:
        return _fail("VERIFY_LEAF_MISMATCH")
    if certificate.get("global_leaf_closure_claimed") is not False:
        return _fail("CERT_GLOBAL_LEAF_SELF_CLAIM_FORBIDDEN")
    for field in (
        "semantic_truth_authority","execution_authority","quality_authority",
        "acceptance_authority","promotion_authority","terminal_authority",
    ):
        if certificate.get(field) is not False:
            return _fail("CERT_SELF_AUTHORITY_FORBIDDEN:" + field)
    if certificate.get("terminal_credit_delta") != 0:
        return _fail("CERT_TERMINAL_CREDIT_FORBIDDEN")

    scope_cert = certificate.get("scope_certificate")
    if not isinstance(scope_cert, Mapping):
        return _fail("SCOPE_CERTIFICATE_MISSING")
    if scope_cert.get("target_scope_id") != expected_leaf_id:
        return _fail("SCOPE_TARGET_LEAF_MISMATCH")
    scope = evaluate_scope(scope_cert)
    if scope.get("scope_complete") is not True:
        return _fail("UNIVERSAL_SCOPE_COMPILER_REJECTED", scope_verdict=scope)

    evidence_refs = certificate.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        return _fail("CERT_EVIDENCE_REFS_REQUIRED")
    seen = set()
    for row in evidence_refs:
        if not isinstance(row, Mapping):
            return _fail("CERT_EVIDENCE_REF_INVALID")
        path = row.get("path")
        blob = row.get("git_blob_sha")
        if not isinstance(path, str) or not path.startswith("canonical/") or not isinstance(blob, str) or len(blob) != 40:
            return _fail("CERT_EVIDENCE_REF_INVALID")
        key = (path, blob)
        if key in seen:
            return _fail("CERT_EVIDENCE_REF_DUPLICATE")
        seen.add(key)

    if verification.get("certificate_git_blob_sha") != certificate_blob:
        return _fail("VERIFY_CERTIFICATE_BLOB_MISMATCH")
    if verification.get("scope_compiler_git_blob_sha") != SCOPE_COMPILER_BLOB:
        return _fail("VERIFY_SCOPE_COMPILER_BLOB_MISMATCH")
    if verification.get("semantic_verifier_git_blob_sha") != semantic_verifier_blob:
        return _fail("VERIFY_SEMANTIC_VERIFIER_BLOB_MISMATCH")
    if verification.get("semantic_tests_git_blob_sha") != semantic_tests_blob:
        return _fail("VERIFY_SEMANTIC_TESTS_BLOB_MISMATCH")
    if verification.get("scope_complete") is not True:
        return _fail("VERIFY_SCOPE_COMPLETE_REQUIRED")
    if verification.get("verified_basis") != scope.get("basis"):
        return _fail("VERIFY_BASIS_MISMATCH")
    status = str(verification.get("status") or "")
    if not status.startswith("PASS__"):
        return _fail("VERIFY_STATUS_NOT_PASS")
    replay = verification.get("independent_replay")
    if not isinstance(replay, Mapping) or replay.get("pass") is not True:
        return _fail("INDEPENDENT_REPLAY_REQUIRED")
    transcript = replay.get("transcript_sha256")
    if not isinstance(transcript, str) or len(transcript) != 64:
        return _fail("INDEPENDENT_REPLAY_TRANSCRIPT_INVALID")
    for field in (
        "semantic_truth_authority","execution_authority","quality_authority",
        "acceptance_authority","promotion_authority","terminal_authority",
    ):
        if verification.get(field) is not False:
            return _fail("VERIFY_AUTHORITY_OVERCLAIM:" + field)
    if verification.get("terminal_credit_delta") != 0:
        return _fail("VERIFY_TERMINAL_CREDIT_FORBIDDEN")

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__WHOLE_LEAF_SCOPE_CERTIFICATE_ADMISSIBLE__PROPERTY_TRUTH_SEPARATE",
        "leaf_id": expected_leaf_id,
        "certificate_git_blob_sha": certificate_blob,
        "basis": scope.get("basis"),
        "scope_reason": scope.get("reason"),
        "whole_leaf_scope_complete": True,
        "leaf_property_truth_authority": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }

def verify_entry(entry: Mapping[str, Any], *, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    ledger_path = root / LEDGER_PATH
    compiler_path = root / SCOPE_COMPILER_PATH
    if not ledger_path.is_file() or _blob(ledger_path) != LEDGER_BLOB:
        return _fail("WHOLE_LEAF_LEDGER_STALE")
    if not compiler_path.is_file() or _blob(compiler_path) != SCOPE_COMPILER_BLOB:
        return _fail("UNIVERSAL_SCOPE_COMPILER_STALE")
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except Exception:
        return _fail("WHOLE_LEAF_LEDGER_INVALID")

    leaf_id = entry.get("leaf_id") if isinstance(entry, Mapping) else None
    if not isinstance(leaf_id, str) or not leaf_id:
        return _fail("LEAF_ID_REQUIRED")
    rows = [x for x in ledger.get("leaves", []) if isinstance(x, Mapping) and x.get("leaf_id") == leaf_id]
    if len(rows) != 1:
        return _fail("LEAF_NOT_IN_CURRENT_LEDGER")
    if rows[0].get("whole_leaf_closed") is not False:
        return _fail("LEAF_ALREADY_CLOSED_IN_LEDGER")

    cert, cert_blob, error = _resolve_bound(root, entry.get("certificate"), "CERTIFICATE")
    if error:
        return _fail(error)
    verification, _, error = _resolve_bound(root, entry.get("verification"), "VERIFICATION")
    if error:
        return _fail(error)
    assert cert is not None and cert_blob is not None and verification is not None

    semantic_verifier, verifier_blob, error = _resolve_bound(root, verification.get("semantic_verifier"), "SEMANTIC_VERIFIER")
    if error:
        return _fail(error)
    semantic_tests, tests_blob, error = _resolve_bound(root, verification.get("semantic_tests"), "SEMANTIC_TESTS")
    if error:
        return _fail(error)
    assert semantic_verifier is not None and verifier_blob is not None
    assert semantic_tests is not None and tests_blob is not None

    # Every certificate evidence reference must itself be current and content-addressed.
    for ref in cert.get("evidence_refs") or []:
        _, _, error = _resolve_bound(root, ref, "EVIDENCE")
        if error:
            return _fail(error)

    return evaluate_documents(
        certificate=cert,
        verification=verification,
        expected_leaf_id=leaf_id,
        certificate_blob=cert_blob,
        semantic_verifier_blob=verifier_blob,
        semantic_tests_blob=tests_blob,
    )
