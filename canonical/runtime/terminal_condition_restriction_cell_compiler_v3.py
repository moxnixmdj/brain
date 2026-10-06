"""Proof-carrying condition restriction compiler V3.

V3 removes the free-form proof-metadata input accepted by V2.
Closure may come only from:
1) a content-addressed acceptance ledger claim that itself proves all admissible
   target inputs for a mapped family, or
2) a content-addressed composite receipt whose bytes bind the exact matrix,
   family, conditions, proof class, and underlying source bytes.

No caller-supplied family/condition metadata can create a closure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

ALLOWED_PROOF_CLASSES = {
    "POINTWISE_UNIVERSAL",
    "OBJECTIVE_CEILING",
    "EXHAUSTIVE_FINITE_PER_CASE",
}
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class ConditionRestrictionV3Error(RuntimeError):
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
    return candidate if candidate.is_file() else None


def verify_repo_blob(repo_root: Path, source_path: str, expected_sha: str) -> bool:
    if not isinstance(expected_sha, str) or not SHA40.fullmatch(expected_sha):
        return False
    candidate = _resolve_repo_file(repo_root, source_path)
    if candidate is None:
        return False
    try:
        return git_blob_sha_bytes(candidate.read_bytes()) == expected_sha
    except OSError:
        return False


def _matrix_index(matrix: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, set[str]]]:
    rows = matrix.get("shared_condition_matrix")
    if not isinstance(rows, list) or not rows:
        raise ConditionRestrictionV3Error("MISSING_SHARED_CONDITION_MATRIX")
    idx: dict[str, set[str]] = {}
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ConditionRestrictionV3Error("MATRIX_ROW_NOT_OBJECT")
        condition = row.get("condition")
        families = row.get("mapped_family_union")
        if not isinstance(condition, str) or not condition:
            raise ConditionRestrictionV3Error("INVALID_CONDITION")
        if condition in idx:
            raise ConditionRestrictionV3Error(f"DUPLICATE_CONDITION:{condition}")
        if not isinstance(families, list) or not families or not all(isinstance(x, str) and x for x in families):
            raise ConditionRestrictionV3Error(f"INVALID_FAMILY_UNION:{condition}")
        if len(set(families)) != len(families):
            raise ConditionRestrictionV3Error(f"DUPLICATE_FAMILY_IN_CONDITION:{condition}")
        idx[condition] = set(families)
        normalized.append({"condition": condition, "families": list(families)})
    return normalized, idx


def _derive_ledger_proofs(
    matrix_rows: list[dict[str, Any]],
    ledger: Mapping[str, Any],
    repo_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    claims = ledger.get("claims")
    if not isinstance(claims, list):
        raise ConditionRestrictionV3Error("MISSING_ACCEPTANCE_CLAIMS")
    proofs: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for c in claims:
        if not isinstance(c, Mapping):
            continue
        family = c.get("family")
        sc = c.get("scope_completeness")
        source_path = c.get("source_path")
        source_sha = c.get("source_sha")
        eligible = (
            c.get("state") == "PROVED"
            and c.get("scope_complete") is True
            and c.get("independent_or_objective") is True
            and isinstance(family, str) and bool(family)
            and isinstance(sc, Mapping)
            and sc.get("all_admissible_target_inputs_proved") is True
            and sc.get("formal_completeness") is True
            and isinstance(source_path, str)
            and isinstance(source_sha, str)
            and verify_repo_blob(repo_root, source_path, source_sha)
        )
        if not eligible:
            if c.get("state") == "PROVED" and isinstance(family, str):
                rejected.append({
                    "kind": "LEDGER_CLAIM",
                    "predicate_id": c.get("predicate_id"),
                    "family": family,
                    "reason": "NOT_FORMAL_ALL_ADMISSIBLE_INPUTS_OR_SOURCE_BLOB_INVALID",
                })
            continue

        if c.get("objective_ceiling") is True:
            proof_class = "OBJECTIVE_CEILING"
        else:
            rejected.append({
                "kind": "LEDGER_CLAIM",
                "predicate_id": c.get("predicate_id"),
                "family": family,
                "reason": "FORMAL_SCOPE_PRESENT_BUT_NO_ADMISSIBLE_POINTWISE_OR_CEILING_CLASS_BOUND",
            })
            continue

        covered = [
            row["condition"] for row in matrix_rows
            if family in row["families"]
        ]
        if covered:
            proofs.append({
                "proof_id": "LEDGER_UNIVERSAL::" + str(c.get("predicate_id")),
                "family": family,
                "proof_class": proof_class,
                "covered_conditions": covered,
                "source_path": source_path,
                "source_sha": source_sha,
                "origin": "CONTENT_ADDRESSED_ACCEPTANCE_LEDGER",
            })
    return proofs, rejected


def _load_composite_proof(
    repo_root: Path,
    matrix_path: str,
    matrix_sha: str,
    matrix_index: Mapping[str, set[str]],
    ref: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    path = ref.get("path")
    sha = ref.get("git_blob_sha")
    if not isinstance(path, str) or not verify_repo_blob(repo_root, path, sha):
        return None, {"kind": "COMPOSITE_RECEIPT", "path": path, "reason": "RECEIPT_BLOB_INVALID"}
    receipt_path = _resolve_repo_file(repo_root, path)
    if receipt_path is None:
        return None, {"kind": "COMPOSITE_RECEIPT", "path": path, "reason": "RECEIPT_UNREADABLE"}
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, {"kind": "COMPOSITE_RECEIPT", "path": path, "reason": "RECEIPT_JSON_INVALID"}

    bound_matrix = receipt.get("matrix")
    source = receipt.get("source")
    family = receipt.get("family")
    covered = receipt.get("covered_conditions")
    proof_class = receipt.get("proof_class")
    if not isinstance(bound_matrix, Mapping) or bound_matrix.get("path") != matrix_path or bound_matrix.get("git_blob_sha") != matrix_sha:
        return None, {"kind": "COMPOSITE_RECEIPT", "path": path, "reason": "MATRIX_BINDING_MISMATCH"}
    if receipt.get("scope_complete") is not True or receipt.get("independent_or_objective") is not True:
        return None, {"kind": "COMPOSITE_RECEIPT", "path": path, "reason": "SCOPE_OR_INDEPENDENCE_MISSING"}
    if proof_class not in ALLOWED_PROOF_CLASSES:
        return None, {"kind": "COMPOSITE_RECEIPT", "path": path, "reason": "PROOF_CLASS_NOT_ADMISSIBLE"}
    if not isinstance(family, str) or not family:
        return None, {"kind": "COMPOSITE_RECEIPT", "path": path, "reason": "FAMILY_MISSING"}
    if not isinstance(covered, list) or not covered or not all(isinstance(x, str) and x for x in covered):
        return None, {"kind": "COMPOSITE_RECEIPT", "path": path, "reason": "COVERED_CONDITIONS_INVALID"}
    if len(set(covered)) != len(covered):
        return None, {"kind": "COMPOSITE_RECEIPT", "path": path, "reason": "DUPLICATE_COVERED_CONDITION"}
    for condition in covered:
        if condition not in matrix_index or family not in matrix_index[condition]:
            return None, {"kind": "COMPOSITE_RECEIPT", "path": path, "reason": f"UNMAPPED_CONDITION:{condition}"}
    if not isinstance(source, Mapping) or not verify_repo_blob(repo_root, source.get("path"), source.get("git_blob_sha")):
        return None, {"kind": "COMPOSITE_RECEIPT", "path": path, "reason": "UNDERLYING_SOURCE_BLOB_INVALID"}

    return {
        "proof_id": "COMPOSITE::" + Path(path).name,
        "family": family,
        "proof_class": proof_class,
        "covered_conditions": list(covered),
        "source_path": path,
        "source_sha": sha,
        "origin": "CONTENT_ADDRESSED_COMPOSITE_RECEIPT",
    }, None


def compile_condition_cells_v3(
    *,
    matrix: Mapping[str, Any],
    ledger: Mapping[str, Any],
    repo_root: Path,
    matrix_path: str,
    matrix_sha: str,
    ledger_path: str,
    ledger_sha: str,
    composite_receipts: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    if not verify_repo_blob(repo_root, matrix_path, matrix_sha):
        raise ConditionRestrictionV3Error("MATRIX_BLOB_IDENTITY_MISMATCH")
    if not verify_repo_blob(repo_root, ledger_path, ledger_sha):
        raise ConditionRestrictionV3Error("LEDGER_BLOB_IDENTITY_MISMATCH")

    rows, idx = _matrix_index(matrix)
    proofs, rejected = _derive_ledger_proofs(rows, ledger, repo_root)
    for ref in composite_receipts:
        if not isinstance(ref, Mapping):
            rejected.append({"kind": "COMPOSITE_RECEIPT", "reason": "REF_NOT_OBJECT"})
            continue
        proof, rejection = _load_composite_proof(repo_root, matrix_path, matrix_sha, idx, ref)
        if proof is not None:
            proofs.append(proof)
        elif rejection is not None:
            rejected.append(rejection)

    cells: list[dict[str, Any]] = []
    for row in rows:
        condition = row["condition"]
        for family in row["families"]:
            matches = [
                p for p in proofs
                if p["family"] == family and condition in p["covered_conditions"]
            ]
            matches.sort(key=lambda p: (p["origin"], p["source_path"], p["proof_id"]))
            if matches:
                p = matches[0]
                cells.append({
                    "condition": condition,
                    "family": family,
                    "state": "CLOSED_BY_PROOF_CARRYING_RESTRICTION_TRANSFER",
                    "proof_id": p["proof_id"],
                    "proof_class": p["proof_class"],
                    "source_path": p["source_path"],
                    "source_sha": p["source_sha"],
                    "origin": p["origin"],
                })
            else:
                cells.append({
                    "condition": condition,
                    "family": family,
                    "state": "OPEN__NO_PROOF_CARRYING_SCOPE_SAFE_TRANSFER_RECEIPT",
                })

    closed = sum(c["state"].startswith("CLOSED") for c in cells)
    honesty = [c for c in cells if c["condition"] == "HONESTY_AND_COMPLETION_INTEGRITY"]
    return {
        "schema": "PROJECT_BRAIN_TERMINAL_CONDITION_CELL_COMPILATION_V3",
        "status": "PASS__PROOF_CARRYING_LEDGER_AND_COMPOSITE_RECEIPT_COMPILATION",
        "matrix_path": matrix_path,
        "matrix_sha": matrix_sha,
        "ledger_path": ledger_path,
        "ledger_sha": ledger_sha,
        "total_cells": len(cells),
        "closed_cells": closed,
        "open_cells": len(cells) - closed,
        "honesty_total_cells": len(honesty),
        "honesty_closed_cells": sum(c["state"].startswith("CLOSED") for c in honesty),
        "honesty_open_cells": sum(not c["state"].startswith("CLOSED") for c in honesty),
        "valid_proof_count": len(proofs),
        "proofs": proofs,
        "rejections": rejected,
        "cells": cells,
        "rules": [
            "NO_FREE_FORM_CALLER_PROOF_METADATA",
            "LEDGER_DERIVATION_REQUIRES_CONTENT_ADDRESSED_LEDGER_AND_SOURCE_BLOB",
            "COMPOSITE_RECEIPT_METADATA_IS_READ_FROM_THE_CONTENT_ADDRESSED_RECEIPT_BYTES",
            "COMPOSITE_RECEIPT_MUST_BIND_THE_EXACT_MATRIX_BYTES",
            "COMPOSITE_UNDERLYING_SOURCE_BYTES_MUST_MATCH",
            "FAMILY_MEMBERSHIP_ALONE_NEVER_CLOSES_A_CONDITION_CELL",
            "AGGREGATE_NONINFERIORITY_NEVER_TRANSFERS_WITHOUT_CONDITION_BOUND",
        ],
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def _parse_ref(value: str) -> dict[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("composite ref must be PATH=SHA")
    path, sha = value.rsplit("=", 1)
    if not path or not SHA40.fullmatch(sha):
        raise argparse.ArgumentTypeError("invalid composite PATH=SHA")
    return {"path": path, "git_blob_sha": sha}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--matrix-sha", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--ledger-sha", required=True)
    ap.add_argument("--composite", action="append", default=[], type=_parse_ref)
    ap.add_argument("--output")
    ns = ap.parse_args()
    root = Path(ns.repo_root).resolve()
    try:
        matrix_file = _resolve_repo_file(root, ns.matrix)
        ledger_file = _resolve_repo_file(root, ns.ledger)
        if matrix_file is None or ledger_file is None:
            raise ConditionRestrictionV3Error("INPUT_FILE_UNREADABLE")
        matrix = json.loads(matrix_file.read_text(encoding="utf-8"))
        ledger = json.loads(ledger_file.read_text(encoding="utf-8"))
        result = compile_condition_cells_v3(
            matrix=matrix,
            ledger=ledger,
            repo_root=root,
            matrix_path=ns.matrix,
            matrix_sha=ns.matrix_sha,
            ledger_path=ns.ledger,
            ledger_sha=ns.ledger_sha,
            composite_receipts=ns.composite,
        )
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if ns.output:
            Path(ns.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (OSError, json.JSONDecodeError, ConditionRestrictionV3Error) as exc:
        print(json.dumps({
            "schema": "PROJECT_BRAIN_TERMINAL_CONDITION_CELL_COMPILATION_V3",
            "status": "FAIL_CLOSED__COMPILER_ERROR",
            "error": str(exc),
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }, indent=2, sort_keys=True))
        return 43


if __name__ == "__main__":
    raise SystemExit(main())
