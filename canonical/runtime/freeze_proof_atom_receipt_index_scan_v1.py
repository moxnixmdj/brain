"""Freeze one exact full-Brain proof-atom receipt-index scan as a zero-credit candidate."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.canonical_proof_atom_basis_v1 import compile_basis
from canonical.runtime.proof_atom_receipt_index_v1 import build_index

SCHEMA = "PROJECT_BRAIN_FULL_PROOF_ATOM_RECEIPT_INDEX_SCAN_V1"
ROOT = Path(__file__).resolve().parents[2]

INPUT_PATHS = [
    "canonical/runtime/proof_atom_receipt_index_v1.py",
    "canonical/runtime/canonical_proof_atom_basis_v1.py",
    "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json",
    "canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json",
]


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def freeze(
    index_result: Mapping[str, Any],
    *,
    scanned_commit_sha: str,
    scanned_tree_sha: str,
    input_blob_shas: Mapping[str, str],
) -> dict[str, Any]:
    if not str(index_result.get("status", "")).startswith("PASS"):
        raise ValueError("INDEX_RESULT_NOT_PASS")
    if index_result.get("canonical_atom_count") != 40:
        raise ValueError("CANONICAL_ATOM_COUNT_NOT_40")
    if not scanned_commit_sha or not scanned_tree_sha:
        raise ValueError("SCAN_IDENTITY_REQUIRED")
    if set(input_blob_shas) != set(INPUT_PATHS):
        raise ValueError("INPUT_BLOB_SET_MISMATCH")
    return {
        "schema": SCHEMA,
        "date": "2026-10-02",
        "status": "CANDIDATE_FROZEN_FULL_BRAIN_SCAN__INDEPENDENT_VERIFICATION_REQUIRED__ZERO_CREDIT",
        "scanned_commit_sha": scanned_commit_sha,
        "scanned_tree_sha": scanned_tree_sha,
        "input_blob_shas": dict(sorted(input_blob_shas.items())),
        "index_result": dict(index_result),
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "rule": (
            "SCAN_IS_DISCOVERY_ONLY__EVERY_MATCH_REMAINS_CANDIDATE_ONLY__"
            "EXACT_COMMIT_TREE_AND_INPUT_BLOBS_BOUND__NO_SEMANTIC_OR_ACCEPTANCE_CREDIT"
        ),
    }


def main() -> int:
    global_frontier = json.loads(
        (ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text(encoding="utf-8")
    )
    matched = json.loads(
        (ROOT / "canonical/governance/MATCHED_SCOPE_BINDING_SUBFRONTIER_V1.json").read_text(encoding="utf-8")
    )
    # Compile once explicitly so malformed basis fails before scan freezing.
    basis = compile_basis(global_frontier, matched)
    if not str(basis.get("status", "")).startswith("PASS"):
        raise SystemExit("CANONICAL_PROOF_ATOM_BASIS_NOT_PASS")
    index_result = build_index(global_frontier, matched, root=ROOT)
    input_blobs = {p: _git("hash-object", p) for p in INPUT_PATHS}
    out = freeze(
        index_result,
        scanned_commit_sha=_git("rev-parse", "HEAD"),
        scanned_tree_sha=_git("rev-parse", "HEAD^{tree}"),
        input_blob_shas=input_blobs,
    )
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
