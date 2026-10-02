"""Freeze one exact complete proof-atom receipt-index V2 scan as a zero-credit candidate."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.proof_atom_receipt_index_v2 import build_index

SCHEMA = "PROJECT_BRAIN_FULL_PROOF_ATOM_RECEIPT_INDEX_SCAN_V2"
ROOT = Path(__file__).resolve().parents[2]
INPUT_PATHS = [
    "canonical/runtime/proof_atom_receipt_index_v2.py",
    "canonical/runtime/canonical_proof_atom_basis_v2.py",
    "canonical/governance/PROOF_ATOM_RECEIPT_INDEX_V2.json",
    "canonical/governance/CANONICAL_PROOF_ATOM_BASIS_V2_ACTIVE_AUTHORITY_V1.json",
    "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json",
    "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json",
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
        raise ValueError("INDEX_RESULT_NOT_COMPLETE_PASS")
    if index_result.get("canonical_atom_count") != 40:
        raise ValueError("CANONICAL_ATOM_COUNT_NOT_40")
    if index_result.get("bounded_incomplete") is not False:
        raise ValueError("BOUNDED_INDEX_CANNOT_BE_FROZEN_AS_COMPLETE")
    if not scanned_commit_sha or not scanned_tree_sha:
        raise ValueError("SCAN_IDENTITY_REQUIRED")
    if set(input_blob_shas) != set(INPUT_PATHS):
        raise ValueError("INPUT_BLOB_SET_MISMATCH")
    return {
        "schema": SCHEMA,
        "date": "2026-10-02",
        "status": "CANDIDATE_FROZEN_FULL_BRAIN_V2_SCAN__INDEPENDENT_VERIFICATION_REQUIRED__ZERO_CREDIT",
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
            "SCAN_IS_DISCOVERY_ONLY__EXACT_COMMIT_TREE_AND_INPUT_BLOBS_BOUND__"
            "EVERY_MATCH_REMAINS_CANDIDATE_ONLY__NO_SEMANTIC_OR_ACCEPTANCE_CREDIT"
        ),
    }


def main() -> int:
    frontier = json.loads(
        (ROOT/"canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text(encoding="utf-8")
    )
    overlay = json.loads(
        (ROOT/"canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text(encoding="utf-8")
    )
    index_result = build_index(frontier, overlay, root=ROOT)
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
