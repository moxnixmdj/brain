"""Fail-closed reducer for Project Brain postwave global ownership closure.

This reducer is intentionally stricter than behavioral adjudication. A terminal
behavioral PASS does not by itself prove donor-independent ownership.

Inputs:
  1. TERMINAL_CLOSURE_MANIFEST_V1.json
  2. OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json

It emits the exact residual ownership cut without mutating canonical truth.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_FAMILY_COUNT = 19
OWNED_STATUS = "VERIFIED_OWNED_EQUAL_OR_BETTER"
PROVISIONAL_STATUS = "PROVISIONAL_TERMINAL_BEHAVIORAL_PASS__GLOBAL_OWNERSHIP_POSTCONDITIONS_PENDING"

def _rows_by_family(matrix: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = matrix.get("rows")
    if not isinstance(rows, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        fid = row.get("family")
        if isinstance(fid, str) and fid and fid not in out:
            out[fid] = row
    return out

def evaluate(closure: dict[str, Any], matrix: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    families = closure.get("families")
    if not isinstance(families, list):
        families = []
        errors.append("CLOSURE_FAMILIES_NOT_LIST")

    if len(families) != REQUIRED_FAMILY_COUNT:
        errors.append(f"CLOSURE_FAMILY_COUNT:{len(families)}")

    matrix_rows = _rows_by_family(matrix)
    donor_pending: list[str] = []
    verifier_mutation_pending: list[str] = []
    composition_pending: list[str] = []
    cleanroom_pending: list[str] = []
    bundle_pending: list[str] = []
    behavioral_missing: list[str] = []

    seen: set[str] = set()
    for row in families:
        if not isinstance(row, dict):
            errors.append("MALFORMED_FAMILY_ROW")
            continue
        fid = row.get("id")
        if not isinstance(fid, str) or not fid:
            errors.append("INVALID_FAMILY_ID")
            continue
        if fid in seen:
            errors.append("DUPLICATE_FAMILY:" + fid)
            continue
        seen.add(fid)

        if row.get("closure_state") != "PASS":
            behavioral_missing.append(fid)

        status = row.get("ownership_status")
        if status == OWNED_STATUS:
            continue

        if status != PROVISIONAL_STATUS:
            donor_pending.append(fid)
        else:
            # Provisional terminal behavior is not ownership. Require an explicit
            # donor-independent ownership receipt rather than inferring one.
            donor_pending.append(fid)

        unresolved = row.get("unresolved")
        if isinstance(unresolved, list):
            joined = " ".join(str(x) for x in unresolved)
            if "VERIFIER" in joined:
                verifier_mutation_pending.append(fid)
            if "COMPOSITION" in joined:
                composition_pending.append(fid)
            if "CLEANROOM" in joined or "DONOR_DELETION" in joined:
                cleanroom_pending.append(fid)
            if "PROOF_BUNDLE" in joined or "BUNDLE" in joined:
                bundle_pending.append(fid)

        # Stale ownership-matrix rows are evidence of unresolved ownership
        # provenance, never evidence of closure.
        mrow = matrix_rows.get(fid)
        if not isinstance(mrow, dict):
            donor_pending.append(fid)
            continue
        mstatus = mrow.get("status")
        if mstatus != OWNED_STATUS:
            donor_pending.append(fid)

    # Global postconditions must be explicit receipts. Absence is UNKNOWN, not 0.
    gp = closure.get("global_ownership_postconditions")
    if not isinstance(gp, dict):
        gp = {}

    def receipt_ok(name: str) -> bool:
        value = gp.get(name)
        return isinstance(value, dict) and value.get("status") == "INDEPENDENT_PASS" and bool(value.get("evidence"))

    if not receipt_ok("verifier_mutation_closure"):
        verifier_mutation_pending = sorted(set(verifier_mutation_pending or list(seen)))
    if not receipt_ok("composition_closure"):
        composition_pending = sorted(set(composition_pending or list(seen)))
    if not receipt_ok("final_donor_deletion_cleanroom"):
        cleanroom_pending = sorted(set(cleanroom_pending or list(seen)))
    if not receipt_ok("proof_bundle_freeze"):
        bundle_pending = sorted(set(bundle_pending or list(seen)))

    donor_pending = sorted(set(donor_pending))
    behavioral_missing = sorted(set(behavioral_missing))

    blockers = {
        "behavioral_adjudication_missing": behavioral_missing,
        "donor_independence_pending": donor_pending,
        "verifier_mutation_closure_pending": verifier_mutation_pending,
        "composition_closure_pending": composition_pending,
        "final_donor_deletion_cleanroom_pending": cleanroom_pending,
        "proof_bundle_freeze_pending": bundle_pending,
    }
    achieved = not errors and all(not v for v in blockers.values())

    return {
        "schema": "PROJECT_BRAIN_POSTWAVE_GLOBAL_OWNERSHIP_VERDICT_V1",
        "status": "PASS" if achieved else "FAIL_CLOSED",
        "achieved": achieved,
        "errors": sorted(set(errors)),
        "family_count": len(seen),
        "blockers": blockers,
        "counts": {k: len(v) for k, v in blockers.items()},
        "rule": "BEHAVIORAL_PASS_NEQ_OWNERSHIP__UNKNOWN_POSTCONDITIONS_FAIL_CLOSED__NO_HANDWRITTEN_BOOLEAN_OVERRIDE",
    }

def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("closure", type=Path)
    ap.add_argument("ownership_matrix", type=Path)
    args = ap.parse_args()
    out = evaluate(_load(args.closure), _load(args.ownership_matrix))
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["achieved"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
