"""Authenticated successor audit for the shared Escape-Progress frontier.

V3 is a syntactic theorem gate: a self-hashed in-memory mapping can satisfy its
shape checks. V4 keeps V3's exact Gap A/B proof algebra but changes the authority
boundary. A row can close only when:

1. the proof is a canonical repository JSON object with exact Git-blob binding;
2. a separate canonical independent-verification JSON binds the exact proof
   path, Git blob, and byte SHA-256;
3. producer and verifier identities are distinct;
4. the verifier explicitly attests the exact row-proof semantics and evidence
   bindings, while granting no promotion/acceptance/terminal authority; and
5. the authenticated proof still passes the unchanged V3 structural theorem.

This module does not create row truth, execution authority, acceptance credit,
or terminal credit. Missing or unauthenticated rows remain open.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import escape_progress_shared_gap_audit_v3 as v3
from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    ReceiptResolutionError,
    resolve_receipt_bytes,
)

SCHEMA = "PROJECT_BRAIN_ESCAPE_PROGRESS_SHARED_GAP_EXECUTABLE_AUDIT_V4"
ROW_PROOF_SCHEMA = "PROJECT_BRAIN_ESCAPE_PROGRESS_ROW_PROOF_V1"
ROW_VERIFY_SCHEMA = "PROJECT_BRAIN_ESCAPE_PROGRESS_ROW_PROOF_INDEPENDENT_VERIFICATION_V1"

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json"
CLASSIFIER_RELATIVE_PATH = "canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json"

def _current_binding_path(root: Path = ROOT) -> Path:
    """Resolve one current shared-gap binding from the mutable classifier.

    Gap A and Gap B must agree on exactly one versioned binding. Missing,
    divergent, escaping, symlinked, or non-file targets fail closed.
    """
    root = Path(root).resolve(strict=True)
    classifier_path = (root / CLASSIFIER_RELATIVE_PATH).resolve(strict=True)
    classifier_path.relative_to(root)
    doc = json.loads(classifier_path.read_text(encoding="utf-8"))
    rows = doc.get("classifications")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise ValueError("CURRENT_RESIDUAL_CLASSIFICATIONS_INVALID")

    expected = {
        "ESCAPE_GAP_A_ACQUISITION_TOTALITY",
        "ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS",
    }
    bindings: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        rid = str(row.get("residual_id") or "")
        if rid not in expected:
            continue
        value = row.get("existing_binding")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("CURRENT_GAP_BINDING_MISSING:" + rid)
        bindings[rid] = value.strip()

    if set(bindings) != expected:
        raise ValueError(
            "CURRENT_GAP_BINDING_CLASSIFICATION_MISSING:"
            + ",".join(sorted(expected - set(bindings)))
        )
    if len(set(bindings.values())) != 1:
        raise ValueError("CURRENT_GAP_BINDING_DIVERGENCE")

    rel = Path(next(iter(bindings.values())))
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("CURRENT_GAP_BINDING_PATH_INVALID")
    unresolved = root / rel
    if unresolved.is_symlink():
        raise ValueError("CURRENT_GAP_BINDING_SYMLINK_FORBIDDEN")
    target = unresolved.resolve(strict=True)
    target.relative_to(root)
    if not target.is_file():
        raise ValueError("CURRENT_GAP_BINDING_NOT_FILE")
    return target


_AUTHORITY_FIELDS = (
    "truth_authority",
    "execution_authority",
    "promotion_authority",
    "acceptance_authority",
    "terminal_authority",
)


def _auth_fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "pass": False,
        "reason": reason,
        "proof": None,
        **extra,
    }


def _authenticate_row_proof(
    obligation_id: str,
    expected_group: str,
    binding: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    if not isinstance(binding, Mapping):
        return _auth_fail("ROW_PROOF_BINDING_NOT_OBJECT")

    proof_ref = binding.get("proof")
    verify_ref = binding.get("independent_verification")
    if not isinstance(proof_ref, Mapping) or not isinstance(verify_ref, Mapping):
        return _auth_fail("ROW_PROOF_AND_VERIFICATION_REFERENCES_REQUIRED")

    try:
        proof_bound = resolve_receipt_bytes(proof_ref, repo_root=repo_root)
        verify_bound = resolve_receipt_bytes(verify_ref, repo_root=repo_root)
    except ReceiptResolutionError as exc:
        return _auth_fail("ROW_PROOF_BYTE_BINDING_INVALID:" + str(exc))

    proof = proof_bound["document"]
    verify = verify_bound["document"]

    if proof.get("schema") != ROW_PROOF_SCHEMA:
        return _auth_fail("ROW_PROOF_SCHEMA_INVALID")
    if proof.get("obligation_id") != obligation_id:
        return _auth_fail("ROW_PROOF_OBLIGATION_MISMATCH")
    if proof.get("route_group") != expected_group:
        return _auth_fail("ROW_PROOF_ROUTE_GROUP_MISMATCH")

    producer_id = proof.get("producer_id")
    if not isinstance(producer_id, str) or not producer_id.strip():
        return _auth_fail("ROW_PROOF_PRODUCER_ID_REQUIRED")
    if any(proof.get(field) is True for field in _AUTHORITY_FIELDS):
        return _auth_fail("ROW_PROOF_AUTHORITY_ESCALATION")

    if verify.get("schema") != ROW_VERIFY_SCHEMA:
        return _auth_fail("ROW_PROOF_VERIFICATION_SCHEMA_INVALID")
    if verify.get("pass") is not True:
        return _auth_fail("ROW_PROOF_VERIFICATION_NOT_PASS")
    if verify.get("independent_verified") is not True:
        return _auth_fail("ROW_PROOF_INDEPENDENCE_NOT_VERIFIED")
    if verify.get("semantic_proof_verified") is not True:
        return _auth_fail("ROW_PROOF_SEMANTICS_NOT_VERIFIED")
    if verify.get("evidence_bindings_verified") is not True:
        return _auth_fail("ROW_PROOF_EVIDENCE_BINDINGS_NOT_VERIFIED")
    if verify.get("obligation_id") != obligation_id:
        return _auth_fail("ROW_PROOF_VERIFICATION_OBLIGATION_MISMATCH")
    if verify.get("route_group") != expected_group:
        return _auth_fail("ROW_PROOF_VERIFICATION_ROUTE_GROUP_MISMATCH")

    verifier_id = verify.get("independent_verifier_id")
    if not isinstance(verifier_id, str) or not verifier_id.strip():
        return _auth_fail("ROW_PROOF_INDEPENDENT_VERIFIER_ID_REQUIRED")
    if verifier_id.strip() == producer_id.strip():
        return _auth_fail("ROW_PROOF_SELF_VERIFICATION_REJECTED")

    subject = verify.get("subject")
    if not isinstance(subject, Mapping):
        return _auth_fail("ROW_PROOF_VERIFICATION_SUBJECT_REQUIRED")
    expected_subject = {
        "path": proof_bound["path"],
        "git_blob_sha": proof_bound["git_blob_sha"],
        "byte_sha256": proof_bound["byte_sha256"],
    }
    for key, value in expected_subject.items():
        if subject.get(key) != value:
            return _auth_fail("ROW_PROOF_VERIFICATION_SUBJECT_MISMATCH:" + key)

    if any(verify.get(field) is True for field in _AUTHORITY_FIELDS):
        return _auth_fail("ROW_PROOF_VERIFIER_AUTHORITY_ESCALATION")

    # The exact authenticated proof must still satisfy V3's content-addressed
    # structural theorem. Authentication never substitutes for proof validity.
    if not v3._proof_digest_valid(proof):
        return _auth_fail("ROW_PROOF_INTERNAL_DIGEST_INVALID")

    return {
        "pass": True,
        "reason": None,
        "proof": deepcopy(dict(proof)),
        "proof_path": proof_bound["path"],
        "proof_git_blob_sha": proof_bound["git_blob_sha"],
        "proof_byte_sha256": proof_bound["byte_sha256"],
        "verification_path": verify_bound["path"],
        "verification_git_blob_sha": verify_bound["git_blob_sha"],
        "verification_byte_sha256": verify_bound["byte_sha256"],
        "producer_id": producer_id.strip(),
        "independent_verifier_id": verifier_id.strip(),
    }


def audit(
    manifest: Mapping[str, Any],
    binding: Mapping[str, Any],
    row_proof_bindings: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    bindings = row_proof_bindings if isinstance(row_proof_bindings, Mapping) else {}
    rows = manifest.get("rows") if isinstance(manifest, Mapping) else None
    authenticated: dict[str, Mapping[str, Any]] = {}
    auth_rows: list[dict[str, Any]] = []
    auth_errors: list[str] = []

    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            oid = str(row.get("obligation_id") or "")
            group = str(row.get("route_group") or "")
            supplied = bindings.get(oid)
            if supplied is None:
                auth_rows.append({
                    "obligation_id": oid,
                    "authenticated": False,
                    "reason": "AUTHENTICATED_CANONICAL_ROW_PROOF_REQUIRED",
                })
                continue
            result = _authenticate_row_proof(
                oid,
                group,
                supplied,
                repo_root=repo_root,
            )
            auth_rows.append({
                "obligation_id": oid,
                "authenticated": result.get("pass") is True,
                "reason": result.get("reason"),
                "proof_path": result.get("proof_path"),
                "proof_git_blob_sha": result.get("proof_git_blob_sha"),
                "verification_path": result.get("verification_path"),
                "verification_git_blob_sha": result.get("verification_git_blob_sha"),
                "producer_id": result.get("producer_id"),
                "independent_verifier_id": result.get("independent_verifier_id"),
            })
            if result.get("pass") is True:
                authenticated[oid] = result["proof"]
            else:
                auth_errors.append(oid + ":" + str(result.get("reason")))

    structural = v3.audit(manifest, binding, authenticated)
    cc_r3 = (
        structural.get("cc_r3_proved") is True
        and not auth_errors
        and len(authenticated) == 13
    )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__AUTHENTICATED_CC_R3_SHARED_ESCAPE_PROGRESS_PROVED__13_OF_13"
            if cc_r3
            else (
                "PASS__AUTHENTICATED_AUDIT_CURRENT__CC_R3_OPEN"
                if structural.get("pass") is True
                else "FAIL_CLOSED__AUDIT_INPUT_DRIFT"
            )
        ),
        "pass": structural.get("pass") is True,
        "cc_r3_proved": cc_r3,
        "authenticated_row_proof_count": len(authenticated),
        "required_authenticated_row_proof_count": 13,
        "authentication_errors": sorted(auth_errors),
        "authentication_rows": auth_rows,
        "structural_audit": structural,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
        "rule": (
            "SELF_HASHED_OR_IN_MEMORY_ROW_PROOFS_HAVE_ZERO_CC_R3_AUTHORITY__"
            "EXACT_CANONICAL_PROOF_BYTES_PLUS_DISTINCT_INDEPENDENT_SEMANTIC_"
            "VERIFICATION_ARE_REQUIRED_BEFORE_V3_STRUCTURAL_PROOF_CAN_CLOSE_CC_R3"
        ),
    }


def audit_repo(
    root: Path = ROOT,
    row_proof_bindings: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve(strict=True)
    manifest_path = (root / MANIFEST_PATH.relative_to(ROOT)).resolve(strict=True)
    manifest_path.relative_to(root)
    binding_path = _current_binding_path(root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    out = audit(
        manifest,
        binding,
        row_proof_bindings=row_proof_bindings,
        repo_root=root,
    )
    out["current_binding_path"] = binding_path.relative_to(root).as_posix()
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(audit_repo(), sort_keys=True))
