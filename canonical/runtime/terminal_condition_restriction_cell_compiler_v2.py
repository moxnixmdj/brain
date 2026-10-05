"""Fail-closed V2 compiler for condition-restriction proof reuse.

A condition x family cell closes only from a content-addressed receipt whose
load-bearing claim is explicitly attested by an exact independent/objective
verification artifact.

Trust chain:
1) exact condition matrix blob,
2) exact proof-inventory blob,
3) exact receipt blob,
4) exact proof-source blob,
5) exact attestation blob,
6) attestation binds SHA-256(canonical load-bearing claim) and exact source.

The proof inventory is only a locator set.  It is never trusted to carry
semantic claim metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

ALLOWED_PROOF_CLASSES = {
    "POINTWISE_UNIVERSAL",
    "OBJECTIVE_CEILING",
    "EXHAUSTIVE_FINITE_PER_CASE",
}
ALLOWED_ATTESTATION_MODES = {
    "INDEPENDENT_EXTERNAL_RECOMPUTATION",
    "OBJECTIVE_FORMAL_VERIFICATION",
}
RECEIPT_SCHEMA = "PROJECT_BRAIN_CONDITION_RESTRICTION_PROOF_RECEIPT_V1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ConditionRestrictionError(RuntimeError):
    pass


def git_blob_sha_bytes(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def canonical_claim_sha256(claim: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(claim)).hexdigest()


def _resolve_repo_file(repo_root: Path, source_path: str) -> Path | None:
    if not isinstance(source_path, str) or not source_path:
        return None
    raw = Path(source_path)
    if raw.is_absolute() or ".." in raw.parts:
        return None
    root = repo_root.resolve()
    candidate = (root / raw).resolve()
    if candidate != root and root not in candidate.parents:
        return None
    if not candidate.is_file():
        return None
    return candidate


def verify_repo_blob(repo_root: Path, source_path: str, expected_sha: str) -> bool:
    if not isinstance(expected_sha, str) or not SHA40.fullmatch(expected_sha):
        return False
    candidate = _resolve_repo_file(repo_root, source_path)
    if candidate is None:
        return False
    try:
        actual = git_blob_sha_bytes(candidate.read_bytes())
    except OSError:
        return False
    return actual == expected_sha


def _load_json_repo_blob(
    repo_root: Path,
    path: str,
    sha: str,
) -> tuple[dict[str, Any] | None, str | None]:
    if not verify_repo_blob(repo_root, path, sha):
        return None, "BLOB_IDENTITY_MISMATCH_OR_UNREADABLE"
    candidate = _resolve_repo_file(repo_root, path)
    if candidate is None:
        return None, "BLOB_UNREADABLE"
    try:
        value = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "BLOB_JSON_INVALID"
    if not isinstance(value, dict):
        return None, "BLOB_JSON_NOT_OBJECT"
    return value, None


def _validate_claim(claim: Any, repo_root: Path) -> str | None:
    if not isinstance(claim, dict):
        return "CLAIM_NOT_OBJECT"
    expected_keys = {
        "family",
        "proof_class",
        "covered_conditions",
        "scope_complete",
        "source_path",
        "source_sha",
    }
    if set(claim) != expected_keys:
        return "CLAIM_FIELD_SET_INVALID"
    if not isinstance(claim.get("family"), str) or not claim["family"]:
        return "FAMILY_MISSING"
    if claim.get("proof_class") not in ALLOWED_PROOF_CLASSES:
        return "PROOF_CLASS_NOT_ADMISSIBLE"
    covered = claim.get("covered_conditions")
    if (
        not isinstance(covered, list)
        or not covered
        or not all(isinstance(x, str) and x for x in covered)
        or len(set(covered)) != len(covered)
    ):
        return "COVERED_CONDITIONS_INVALID"
    if claim.get("scope_complete") is not True:
        return "SCOPE_INCOMPLETE"
    source_path = claim.get("source_path")
    source_sha = claim.get("source_sha")
    if not isinstance(source_path, str) or not source_path:
        return "SOURCE_PATH_MISSING"
    if not isinstance(source_sha, str) or not SHA40.fullmatch(source_sha):
        return "SOURCE_SHA_INVALID"
    if not verify_repo_blob(repo_root, source_path, source_sha):
        return "SOURCE_BLOB_IDENTITY_MISMATCH_OR_UNREADABLE"
    return None


def _attestation_rejection_reason(
    attestation: Any,
    *,
    claim_binding_sha256: str,
    claim: dict[str, Any],
) -> str | None:
    if not isinstance(attestation, dict):
        return "ATTESTATION_NOT_OBJECT"
    if attestation.get("condition_restriction_verdict") != "PASS":
        return "ATTESTATION_VERDICT_NOT_PASS"
    mode = attestation.get("condition_restriction_attestation_mode")
    if mode not in ALLOWED_ATTESTATION_MODES:
        return "ATTESTATION_MODE_NOT_ADMISSIBLE"
    if (
        attestation.get("condition_restriction_claim_binding_sha256")
        != claim_binding_sha256
    ):
        return "ATTESTATION_CLAIM_BINDING_MISMATCH"
    subject = attestation.get("condition_restriction_subject")
    if not isinstance(subject, dict):
        return "ATTESTATION_SUBJECT_MISSING"
    if set(subject) != {"path", "git_blob_sha"}:
        return "ATTESTATION_SUBJECT_FIELD_SET_INVALID"
    if subject.get("path") != claim["source_path"]:
        return "ATTESTATION_SUBJECT_PATH_MISMATCH"
    if subject.get("git_blob_sha") != claim["source_sha"]:
        return "ATTESTATION_SUBJECT_SHA_MISMATCH"
    return None


def _load_bound_receipt(
    entry: dict[str, Any],
    repo_root: Path,
) -> tuple[dict[str, Any] | None, str | None]:
    # Inventory entries are locators only.  Semantic metadata here would create
    # a shadow claim channel and therefore fails closed.
    if set(entry) != {"receipt_path", "receipt_sha"}:
        return None, "INVENTORY_ENTRY_FIELD_SET_INVALID"
    receipt_path = entry.get("receipt_path")
    receipt_sha = entry.get("receipt_sha")
    if not isinstance(receipt_path, str) or not receipt_path:
        return None, "RECEIPT_PATH_MISSING"
    if not isinstance(receipt_sha, str) or not SHA40.fullmatch(receipt_sha):
        return None, "RECEIPT_SHA_INVALID"

    receipt, err = _load_json_repo_blob(repo_root, receipt_path, receipt_sha)
    if err is not None:
        return None, "RECEIPT_" + err
    assert receipt is not None
    if receipt.get("schema") != RECEIPT_SCHEMA:
        return None, "RECEIPT_SCHEMA_INVALID"

    allowed_receipt_keys = {
        "schema",
        "proof_id",
        "claim",
        "claim_binding_sha256",
        "attestation_path",
        "attestation_sha",
    }
    if set(receipt) != allowed_receipt_keys:
        return None, "RECEIPT_FIELD_SET_INVALID"
    if not isinstance(receipt.get("proof_id"), str) or not receipt["proof_id"]:
        return None, "PROOF_ID_INVALID"

    claim = receipt.get("claim")
    reason = _validate_claim(claim, repo_root)
    if reason is not None:
        return None, reason
    assert isinstance(claim, dict)

    binding = receipt.get("claim_binding_sha256")
    if not isinstance(binding, str) or not SHA256.fullmatch(binding):
        return None, "CLAIM_BINDING_SHA256_INVALID"
    if canonical_claim_sha256(claim) != binding:
        return None, "CLAIM_BINDING_SHA256_MISMATCH"

    attestation_path = receipt.get("attestation_path")
    attestation_sha = receipt.get("attestation_sha")
    if not isinstance(attestation_path, str) or not attestation_path:
        return None, "ATTESTATION_PATH_MISSING"
    if not isinstance(attestation_sha, str) or not SHA40.fullmatch(attestation_sha):
        return None, "ATTESTATION_SHA_INVALID"
    attestation, err = _load_json_repo_blob(
        repo_root, attestation_path, attestation_sha
    )
    if err is not None:
        return None, "ATTESTATION_" + err
    reason = _attestation_rejection_reason(
        attestation,
        claim_binding_sha256=binding,
        claim=claim,
    )
    if reason is not None:
        return None, reason

    return {
        "proof_id": receipt["proof_id"],
        "family": claim["family"],
        "proof_class": claim["proof_class"],
        "covered_conditions": claim["covered_conditions"],
        "source_path": claim["source_path"],
        "source_sha": claim["source_sha"],
        "receipt_path": receipt_path,
        "receipt_sha": receipt_sha,
        "attestation_path": attestation_path,
        "attestation_sha": attestation_sha,
        "claim_binding_sha256": binding,
    }, None


def compile_condition_cells(
    matrix: dict[str, Any],
    proof_inventory: Iterable[dict[str, Any]],
    repo_root: Path,
) -> dict[str, Any]:
    rows = matrix.get("shared_condition_matrix")
    if not isinstance(rows, list):
        raise ConditionRestrictionError("MISSING_SHARED_CONDITION_MATRIX")

    entries = list(proof_inventory)
    if not all(isinstance(p, dict) for p in entries):
        raise ConditionRestrictionError("PROOF_INVENTORY_ENTRY_NOT_OBJECT")

    validation = [
        (entry, *_load_bound_receipt(entry, repo_root))
        for entry in entries
    ]
    valid = [receipt for _, receipt, reason in validation if reason is None]

    cells: list[dict[str, Any]] = []
    for row in rows:
        condition = row.get("condition")
        families = row.get("mapped_family_union")
        if not isinstance(condition, str) or not condition:
            raise ConditionRestrictionError("INVALID_CONDITION")
        if (
            not isinstance(families, list)
            or not all(isinstance(x, str) and x for x in families)
        ):
            raise ConditionRestrictionError(f"INVALID_FAMILY_UNION:{condition}")

        for family in families:
            matches = [
                p for p in valid
                if p["family"] == family and condition in p["covered_conditions"]
            ]
            matches.sort(
                key=lambda p: (
                    p["receipt_path"],
                    p["receipt_sha"],
                    p["proof_id"],
                )
            )
            if matches:
                p = matches[0]
                cells.append({
                    "condition": condition,
                    "family": family,
                    "state": "CLOSED_BY_ATTESTED_CONTENT_BOUND_RESTRICTION_TRANSFER",
                    "proof_id": p["proof_id"],
                    "proof_class": p["proof_class"],
                    "source_path": p["source_path"],
                    "source_sha": p["source_sha"],
                    "receipt_path": p["receipt_path"],
                    "receipt_sha": p["receipt_sha"],
                    "attestation_path": p["attestation_path"],
                    "attestation_sha": p["attestation_sha"],
                    "claim_binding_sha256": p["claim_binding_sha256"],
                })
            else:
                cells.append({
                    "condition": condition,
                    "family": family,
                    "state": "OPEN__NO_ATTESTED_CONTENT_BOUND_SCOPE_SAFE_RECEIPT",
                })

    closed = sum(c["state"].startswith("CLOSED") for c in cells)
    rejected = [
        {
            "receipt_path": entry.get("receipt_path"),
            "receipt_sha": entry.get("receipt_sha"),
            "reason": reason,
        }
        for entry, receipt, reason in validation if reason is not None
    ]
    return {
        "schema": "PROJECT_BRAIN_TERMINAL_CONDITION_CELL_COMPILATION_V2",
        "status": "PASS__FAIL_CLOSED_ATTESTED_CONTENT_BOUND_CONDITION_RESTRICTION_COMPILATION",
        "total_cells": len(cells),
        "closed_cells": closed,
        "open_cells": len(cells) - closed,
        "valid_receipt_count": len(valid),
        "rejected_receipt_count": len(rejected),
        "receipt_rejections": rejected,
        "cells": cells,
        "rules": [
            "PROOF_INVENTORY_IS_LOCATOR_ONLY__SEMANTIC_METADATA_FORBIDDEN",
            "MATRIX_AND_PROOF_INVENTORY_BLOBS_MUST_BOTH_BE_PINNED",
            "EVERY_RECEIPT_BLOB_MUST_BE_PINNED",
            "EVERY_SOURCE_BLOB_MUST_BE_PINNED",
            "LOAD_BEARING_CLAIM_FIELDS_MUST_HASH_TO_RECEIPT_CLAIM_BINDING_SHA256",
            "EXACT_ATTESTATION_BLOB_MUST_PASS_AND_BIND_THE_SAME_CLAIM_HASH_AND_SOURCE",
            "FAMILY_NAME_MATCH_ALONE_NEVER_CLOSES_A_CELL",
            "AGGREGATE_NONINFERIORITY_NEVER_TRANSFERS_WITHOUT_A_CONDITION_BOUND",
        ],
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--matrix-sha", required=True)
    ap.add_argument("--proofs", required=True)
    ap.add_argument("--proofs-sha", required=True)
    ap.add_argument("--output")
    ns = ap.parse_args()

    root = Path(ns.repo_root).resolve()
    try:
        matrix_path = str(Path(ns.matrix))
        proofs_path = str(Path(ns.proofs))
        if not verify_repo_blob(root, matrix_path, ns.matrix_sha):
            raise ConditionRestrictionError("MATRIX_BLOB_IDENTITY_MISMATCH")
        if not verify_repo_blob(root, proofs_path, ns.proofs_sha):
            raise ConditionRestrictionError("PROOF_INVENTORY_BLOB_IDENTITY_MISMATCH")

        matrix_file = _resolve_repo_file(root, matrix_path)
        proofs_file = _resolve_repo_file(root, proofs_path)
        if matrix_file is None:
            raise ConditionRestrictionError("MATRIX_UNREADABLE")
        if proofs_file is None:
            raise ConditionRestrictionError("PROOF_INVENTORY_UNREADABLE")

        matrix = json.loads(matrix_file.read_text(encoding="utf-8"))
        proof_doc = json.loads(proofs_file.read_text(encoding="utf-8"))
        proofs = proof_doc.get("proofs") if isinstance(proof_doc, dict) else None
        if not isinstance(proofs, list):
            raise ConditionRestrictionError("PROOFS_MUST_BE_OBJECT_WITH_LIST")

        result = compile_condition_cells(matrix, proofs, root)
        result["matrix_path"] = matrix_path
        result["matrix_sha"] = ns.matrix_sha
        result["proof_inventory_path"] = proofs_path
        result["proof_inventory_sha"] = ns.proofs_sha
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if ns.output:
            Path(ns.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (OSError, json.JSONDecodeError, ConditionRestrictionError) as exc:
        print(json.dumps({
            "schema": "PROJECT_BRAIN_TERMINAL_CONDITION_CELL_COMPILATION_V2",
            "status": "FAIL_CLOSED__COMPILER_ERROR",
            "error": str(exc),
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }, indent=2, sort_keys=True))
        return 43


if __name__ == "__main__":
    raise SystemExit(main())
