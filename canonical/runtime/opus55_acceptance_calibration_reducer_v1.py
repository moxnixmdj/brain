"""Fail-closed calibration reducer for Project Brain Opus 5.5 ownership acceptance.

A terminal behavioral-contract PASS is useful evidence, but it is not interchangeable
with satisfying a family's frozen Opus 5.5 proof protocol. This reducer preserves that
boundary and exposes the exact family-level residual without replaying terminal evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

EXPECTED_FAMILY_COUNT = 19
PASS_STATUS = "PASS"

def _family_ids_from_envelope(envelope: Mapping[str, Any]) -> list[str]:
    rows = envelope.get("families")
    if not isinstance(rows, list):
        return []
    out: list[str] = []
    for row in rows:
        if isinstance(row, Mapping) and isinstance(row.get("id"), str):
            out.append(row["id"])
    return out

def _protocols(protocols_doc: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = protocols_doc.get("protocols")
    if not isinstance(rows, list):
        return {}
    out: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if isinstance(row, Mapping) and isinstance(row.get("family"), str):
            out[row["family"]] = row
    return out

def evaluate(
    envelope: Mapping[str, Any],
    protocols_doc: Mapping[str, Any],
    reduction: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    families = _family_ids_from_envelope(envelope)
    if len(families) != EXPECTED_FAMILY_COUNT or len(set(families)) != EXPECTED_FAMILY_COUNT:
        errors.append("TARGET_ENVELOPE_FAMILY_ACCOUNTING_INVALID")

    protocols = _protocols(protocols_doc)
    if set(protocols) != set(families):
        errors.append("PROTOCOL_FAMILY_SET_MISMATCH")

    fv = reduction.get("family_verdict")
    behavioral_passes: set[str] = set()
    if not isinstance(fv, Mapping):
        errors.append("POSTWAVE_FAMILY_VERDICT_MISSING")
    else:
        if fv.get("valid") is not True:
            errors.append("POSTWAVE_FAMILY_VERDICT_INVALID")
        passed = fv.get("passed_families")
        if not isinstance(passed, list):
            errors.append("POSTWAVE_PASSED_FAMILIES_MISSING")
        else:
            behavioral_passes = {x for x in passed if isinstance(x, str)}

    rows: list[dict[str, Any]] = []
    calibrated_pass: list[str] = []
    acceptance_open: list[str] = []
    behavioral_missing: list[str] = []

    for family in families:
        protocol = protocols.get(family, {})
        behavior_pass = family in behavioral_passes
        protocol_status = protocol.get("status")
        protocol_closed = protocol_status == PASS_STATUS

        if not behavior_pass:
            behavioral_missing.append(family)
        if behavior_pass and protocol_closed:
            calibrated_pass.append(family)
        else:
            acceptance_open.append(family)

        rows.append({
            "family": family,
            "behavioral_contract_pass": behavior_pass,
            "proof_mode": protocol.get("proof_mode"),
            "protocol_status": protocol_status,
            "opus_acceptance_calibrated": bool(behavior_pass and protocol_closed),
            "reason": (
                "BEHAVIORAL_PASS_AND_FROZEN_PROTOCOL_RESULT_PASS"
                if behavior_pass and protocol_closed
                else "FROZEN_OPUS55_PROTOCOL_RESULT_NOT_CLOSED"
                if behavior_pass
                else "TERMINAL_BEHAVIORAL_PASS_MISSING"
            ),
        })

    calibrated_pass = sorted(calibrated_pass)
    acceptance_open = sorted(acceptance_open)
    behavioral_missing = sorted(behavioral_missing)

    pass_all = (
        not errors
        and not behavioral_missing
        and len(calibrated_pass) == EXPECTED_FAMILY_COUNT
    )

    return {
        "schema": "PROJECT_BRAIN_OPUS55_ACCEPTANCE_CALIBRATION_VERDICT_V1",
        "status": "PASS" if pass_all else "FAIL_CLOSED",
        "pass": pass_all,
        "errors": sorted(set(errors)),
        "target_family_count": len(families),
        "behavioral_pass_family_count": len(behavioral_passes & set(families)),
        "acceptance_calibrated_family_count": len(calibrated_pass),
        "acceptance_pending_family_count": len(acceptance_open),
        "acceptance_calibrated_families": calibrated_pass,
        "acceptance_pending_families": acceptance_open,
        "behavioral_missing_families": behavioral_missing,
        "families": rows,
        "rule": (
            "TERMINAL_BEHAVIORAL_CONTRACT_PASS_IS_NOT_OPUS55_EQUAL_OR_BETTER_OWNERSHIP_PROOF__"
            "FAMILY_ACCEPTANCE_CLOSES_ONLY_WHEN_ITS_PREDECLARED_PROTOCOL_RESULT_IS_PASS"
        ),
        "new_terminal_evidence_required_by_this_reducer": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }

def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("envelope", type=Path)
    ap.add_argument("protocols", type=Path)
    ap.add_argument("reduction", type=Path)
    args = ap.parse_args()
    out = evaluate(_load(args.envelope), _load(args.protocols), _load(args.reduction))
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
