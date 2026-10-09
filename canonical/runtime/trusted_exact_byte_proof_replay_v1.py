"""Trusted exact-byte proof replay V1.

This module is deliberately a dispatcher, not a theorem oracle.  A proof result is
trusted only when:
  * the verifier kernel is in a fixed allowlist;
  * the exact kernel path and Git blob SHA match the allowlist and repository bytes;
  * the input payload is content-addressed;
  * the allowlisted kernel is re-executed; and
  * the derived claim exactly equals the caller's requested claim.

Adding a new proof class therefore requires adding a real verifier kernel to the
allowlist.  A JSON receipt, boolean flag, or plausible hash can never add itself.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TRUSTED_EXACT_BYTE_PROOF_REPLAY_V1"
ROOT = Path(__file__).resolve().parents[2]

TRUSTED_KERNELS = {
    "LIVEBENCH_UNION25_SEMANTIC_UNSAT_V1": {
        "path": "canonical/runtime/livebench_union25_semantic_unsat_kernel_v1.py",
        "git_blob_sha": "0649b6ce80b7bb4a38fa1e8e8de154968e083d47",
        "claim_kind": "BOUNDED_CONTRACT_SET_UNSAT",
    },
}


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return "sha256:" + sha256(_canon(value)).hexdigest()


def _git_blob_sha(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _safe_repo_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError("PATH_REQUIRED")
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("PATH_INVALID")
    root = root.resolve(strict=True)
    cur = root
    for part in rel.parts:
        cur = cur / part
        if cur.is_symlink():
            raise ValueError("SYMLINK_FORBIDDEN")
    target = (root / rel).resolve(strict=True)
    target.relative_to(root)
    if not target.is_file():
        raise ValueError("FILE_REQUIRED")
    return target


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "independent_proof_replay_performed": False,
        "proof_verified": False,
        "verification_authority_mutated": False,
        "selected_cover_complete_authorized": False,
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _run_kernel(kernel_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    if kernel_id == "LIVEBENCH_UNION25_SEMANTIC_UNSAT_V1":
        from canonical.runtime.livebench_union25_semantic_unsat_kernel_v1 import prove_unsat
        contracts = payload.get("contracts")
        if not isinstance(contracts, list):
            raise ValueError("CONTRACTS_LIST_REQUIRED")
        return dict(prove_unsat(contracts))
    raise ValueError("KERNEL_ADAPTER_MISSING")


def _derived_claim(kernel_id: str, input_sha256: str, result: Mapping[str, Any]) -> dict[str, Any] | None:
    if kernel_id == "LIVEBENCH_UNION25_SEMANTIC_UNSAT_V1":
        if result.get("jointly_unsatisfiable") is not True:
            return None
        return {
            "kind": "BOUNDED_CONTRACT_SET_UNSAT",
            "input_sha256": input_sha256,
            "kernel_schema": result.get("schema"),
            "conclusion": "UNSAT",
        }
    return None


def replay(request: Mapping[str, Any], *, root: str | Path = ROOT) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        return _fail("REQUEST_MAPPING_REQUIRED")

    kernel_id = request.get("kernel_id")
    spec = TRUSTED_KERNELS.get(kernel_id)
    if spec is None:
        return _fail("KERNEL_NOT_ALLOWLISTED", kernel_id=kernel_id)

    if request.get("kernel_path") != spec["path"]:
        return _fail("KERNEL_PATH_MISMATCH")
    if request.get("kernel_git_blob_sha") != spec["git_blob_sha"]:
        return _fail("KERNEL_SHA_MISMATCH")

    try:
        target = _safe_repo_file(Path(root), spec["path"])
        actual_kernel_sha = _git_blob_sha(target.read_bytes())
    except Exception as exc:
        return _fail("KERNEL_BINDING_ERROR", error=type(exc).__name__ + ":" + str(exc))
    if actual_kernel_sha != spec["git_blob_sha"]:
        return _fail(
            "KERNEL_REPOSITORY_BYTES_MISMATCH",
            expected=spec["git_blob_sha"],
            actual=actual_kernel_sha,
        )

    payload = request.get("input")
    if not isinstance(payload, Mapping):
        return _fail("INPUT_MAPPING_REQUIRED")
    input_sha = _sha256(payload)
    if request.get("input_sha256") != input_sha:
        return _fail("INPUT_SHA256_MISMATCH")

    expected = request.get("expected_claim")
    if not isinstance(expected, Mapping):
        return _fail("EXPECTED_CLAIM_REQUIRED")

    try:
        result = _run_kernel(str(kernel_id), payload)
    except Exception as exc:
        return _fail("KERNEL_REPLAY_EXCEPTION", error=type(exc).__name__ + ":" + str(exc))

    claim = _derived_claim(str(kernel_id), input_sha, result)
    if claim is None:
        return _fail(
            "KERNEL_DID_NOT_PROVE_REQUESTABLE_CLAIM",
            kernel_status=result.get("status"),
        )
    if dict(expected) != claim:
        return _fail(
            "REPLAYED_CLAIM_MISMATCH",
            expected=dict(expected),
            actual=claim,
        )

    receipt_basis = {
        "kernel_id": kernel_id,
        "kernel_path": spec["path"],
        "kernel_git_blob_sha": actual_kernel_sha,
        "input_sha256": input_sha,
        "proved_claim": claim,
    }
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__TRUSTED_EXACT_BYTE_KERNEL_REPLAY",
        "kernel_id": kernel_id,
        "kernel_path": spec["path"],
        "kernel_git_blob_sha": actual_kernel_sha,
        "input_sha256": input_sha,
        "proved_claim": claim,
        "replay_receipt_sha256": _sha256(receipt_basis),
        "independent_proof_replay_performed": True,
        "proof_verified": True,
        "verification_authority_mutated": False,
        "selected_cover_complete_authorized": False,
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
