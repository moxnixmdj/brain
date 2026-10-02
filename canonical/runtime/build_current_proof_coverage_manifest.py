"""Derive proof-coverage compiler input from the live active terminal proof basis.

This avoids a hand-maintained mirror. Only routes already admitted by the canonical
ACTIVE_TERMINAL_PROOF_BASIS are imported as terminal-scope-authoritative cover.
Open routes remain uncovered until the canonical basis itself promotes them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

BASIS = "canonical/governance/ACTIVE_TERMINAL_PROOF_BASIS_V1.json"
SCHEMA = "PROJECT_BRAIN_DERIVED_CURRENT_PROOF_COVERAGE_MANIFEST_V1"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def build(root: Path) -> dict[str, Any]:
    path = root / BASIS
    basis = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(basis, dict):
        raise ValueError("ACTIVE_BASIS_NOT_OBJECT")
    rows = basis.get("contracts")
    if not isinstance(rows, list) or not rows:
        raise ValueError("ACTIVE_BASIS_CONTRACTS_INVALID")

    obligations: list[str] = []
    routes: list[dict[str, Any]] = []
    seen: set[str] = set()
    basis_blob = git_blob_sha(path)
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"CONTRACT_{i}_NOT_OBJECT")
        bid = row.get("behavior_id")
        state = row.get("proof_state")
        blockers = row.get("blockers")
        if not isinstance(bid, str) or not bid:
            raise ValueError(f"CONTRACT_{i}_BEHAVIOR_ID_INVALID")
        if bid in seen:
            raise ValueError("DUPLICATE_BEHAVIOR_ID:" + bid)
        seen.add(bid)
        obligations.append(bid)
        if not isinstance(state, str) or not isinstance(blockers, list):
            raise ValueError("CONTRACT_STATE_INVALID:" + bid)
        if state == "TERMINAL_ROUTE_FROZEN_ADMISSIBLE":
            if blockers:
                raise ValueError("ADMITTED_ROUTE_HAS_BLOCKERS:" + bid)
            routes.append({
                "id": "ACTIVE_BASIS::" + bid,
                "covers": [bid],
                "proof_mode": "CANONICAL_ADMITTED_ROUTE",
                "zero_incremental_spend": True,
                "terminal_scope_authority": True,
                "prewave_admissible": True,
                "external_blocked": False,
                "canonical_active_basis_admitted": True,
                "source_basis_blob_sha": basis_blob,
                "new_reality_units": 0,
                "clean_case_spend": 0,
                "evidence_cost": 0.0,
            })

    declared = basis.get("active_contract_count")
    admitted = basis.get("admissible_frozen_terminal_route_count")
    if declared != len(obligations):
        raise ValueError("ACTIVE_CONTRACT_COUNT_MISMATCH")
    if admitted != len(routes):
        raise ValueError("ADMISSIBLE_ROUTE_COUNT_MISMATCH")

    return {
        "schema": SCHEMA,
        "date": basis.get("date"),
        "status": "DERIVED_FROM_ACTIVE_BASIS__NO_INDEPENDENT_PROMOTION_AUTHORITY",
        "source_basis": BASIS,
        "source_basis_blob_sha": basis_blob,
        "required_obligations": obligations,
        "routes": routes,
        "declared_admissible_route_count": admitted,
        "execution_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root", type=Path)
    args = ap.parse_args()
    print(json.dumps(build(args.repo_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
