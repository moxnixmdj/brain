"""Fail-closed V2 compiler for condition-restriction proof reuse.

A condition x family cell closes only when an exact repository blob:
1) targets the exact family,
2) explicitly covers the exact condition,
3) is independently/objectively supported and scope-complete,
4) uses an admissible proof class, and
5) source_path's actual Git-blob hash equals source_sha.

The CLI additionally requires the condition matrix itself to match a pinned Git-blob SHA.
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
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class ConditionRestrictionError(RuntimeError):
    pass


def git_blob_sha_bytes(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


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


def _receipt_rejection_reason(p: dict[str, Any], repo_root: Path) -> str | None:
    if p.get("independent_or_objective") is not True:
        return "NOT_INDEPENDENT_OR_OBJECTIVE"
    if p.get("scope_complete") is not True:
        return "SCOPE_INCOMPLETE"
    if p.get("proof_class") not in ALLOWED_PROOF_CLASSES:
        return "PROOF_CLASS_NOT_ADMISSIBLE"
    if not isinstance(p.get("family"), str) or not p["family"]:
        return "FAMILY_MISSING"
    covered = p.get("covered_conditions")
    if not isinstance(covered, list) or not all(isinstance(x, str) and x for x in covered):
        return "COVERED_CONDITIONS_INVALID"
    source_path = p.get("source_path")
    source_sha = p.get("source_sha")
    if not isinstance(source_path, str) or not source_path:
        return "SOURCE_PATH_MISSING"
    if not isinstance(source_sha, str) or not SHA40.fullmatch(source_sha):
        return "SOURCE_SHA_INVALID"
    if not verify_repo_blob(repo_root, source_path, source_sha):
        return "SOURCE_BLOB_IDENTITY_MISMATCH_OR_UNREADABLE"
    return None


def compile_condition_cells(
    matrix: dict[str, Any],
    proofs: Iterable[dict[str, Any]],
    repo_root: Path,
) -> dict[str, Any]:
    rows = matrix.get("shared_condition_matrix")
    if not isinstance(rows, list):
        raise ConditionRestrictionError("MISSING_SHARED_CONDITION_MATRIX")

    proofs = list(proofs)
    if not all(isinstance(p, dict) for p in proofs):
        raise ConditionRestrictionError("PROOF_ENTRY_NOT_OBJECT")

    validation = [
        (p, _receipt_rejection_reason(p, repo_root))
        for p in proofs
    ]
    valid = [p for p, reason in validation if reason is None]

    cells: list[dict[str, Any]] = []
    for row in rows:
        condition = row.get("condition")
        families = row.get("mapped_family_union")
        if not isinstance(condition, str) or not condition:
            raise ConditionRestrictionError("INVALID_CONDITION")
        if not isinstance(families, list) or not all(isinstance(x, str) and x for x in families):
            raise ConditionRestrictionError(f"INVALID_FAMILY_UNION:{condition}")

        for family in families:
            matches = [
                p for p in valid
                if p["family"] == family and condition in p["covered_conditions"]
            ]
            matches.sort(key=lambda p: (p["source_path"], p["source_sha"], str(p.get("proof_id", ""))))
            if matches:
                p = matches[0]
                cells.append({
                    "condition": condition,
                    "family": family,
                    "state": "CLOSED_BY_SOUND_EXACT_BLOB_RESTRICTION_TRANSFER",
                    "proof_id": p.get("proof_id"),
                    "proof_class": p["proof_class"],
                    "source_path": p["source_path"],
                    "source_sha": p["source_sha"],
                })
            else:
                cells.append({
                    "condition": condition,
                    "family": family,
                    "state": "OPEN__NO_EXACT_BLOB_SCOPE_SAFE_TRANSFER_RECEIPT",
                })

    closed = sum(c["state"].startswith("CLOSED") for c in cells)
    rejected = [
        {
            "proof_id": p.get("proof_id"),
            "source_path": p.get("source_path"),
            "source_sha": p.get("source_sha"),
            "reason": reason,
        }
        for p, reason in validation if reason is not None
    ]
    return {
        "schema": "PROJECT_BRAIN_TERMINAL_CONDITION_CELL_COMPILATION_V2",
        "status": "PASS__FAIL_CLOSED_EXACT_BLOB_CONDITION_RESTRICTION_COMPILATION",
        "total_cells": len(cells),
        "closed_cells": closed,
        "open_cells": len(cells) - closed,
        "valid_receipt_count": len(valid),
        "rejected_receipt_count": len(rejected),
        "receipt_rejections": rejected,
        "cells": cells,
        "rules": [
            "FAMILY_NAME_MATCH_ALONE_NEVER_CLOSES_A_CELL",
            "AGGREGATE_NONINFERIORITY_NEVER_TRANSFERS_WITHOUT_A_CONDITION_BOUND",
            "MISSING_SCOPE_METADATA_FAILS_CLOSED",
            "ONLY_POINTWISE_UNIVERSAL_OBJECTIVE_CEILING_OR_EXHAUSTIVE_PER_CASE_CLASSES_ARE_ADMISSIBLE",
            "EVERY_CLOSING_RECEIPT_SOURCE_PATH_MUST_RESOLVE_INSIDE_REPOSITORY",
            "EVERY_CLOSING_RECEIPT_SOURCE_BYTES_MUST_HASH_TO_CLAIMED_GIT_BLOB_SHA",
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
    ap.add_argument("--output")
    ns = ap.parse_args()

    root = Path(ns.repo_root).resolve()
    try:
        matrix_path = Path(ns.matrix)
        if matrix_path.is_absolute():
            try:
                matrix_rel = str(matrix_path.resolve().relative_to(root))
            except ValueError as exc:
                raise ConditionRestrictionError("MATRIX_OUTSIDE_REPOSITORY") from exc
        else:
            matrix_rel = str(matrix_path)

        if not verify_repo_blob(root, matrix_rel, ns.matrix_sha):
            raise ConditionRestrictionError("MATRIX_BLOB_IDENTITY_MISMATCH")

        matrix_file = _resolve_repo_file(root, matrix_rel)
        if matrix_file is None:
            raise ConditionRestrictionError("MATRIX_UNREADABLE")

        proofs_path = Path(ns.proofs)
        if not proofs_path.is_absolute():
            proofs_path = root / proofs_path
        matrix = json.loads(matrix_file.read_text(encoding="utf-8"))
        proof_doc = json.loads(proofs_path.read_text(encoding="utf-8"))
        proofs = proof_doc.get("proofs", proof_doc) if isinstance(proof_doc, dict) else proof_doc
        if not isinstance(proofs, list):
            raise ConditionRestrictionError("PROOFS_MUST_BE_LIST")

        result = compile_condition_cells(matrix, proofs, root)
        result["matrix_path"] = matrix_rel
        result["matrix_sha"] = ns.matrix_sha
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
