#!/usr/bin/env python3
"""Claim-scoped counterexample finder for mission-carrier factorization.

For each frozen certification claim C, the semantic completeness theorem needs a
mission-sufficient carrier Omega_C. This checker can falsify a proposed carrier
on a declared finite witness set: if two concrete worlds in the same frozen claim
project to the same carrier value but have different mission verdicts, the carrier
is unsound for that claim.

Absence of a finite counterexample is deliberately NOT a universal proof.
This module grants zero terminal/acceptance/ownership credit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_MISSION_CARRIER_FACTORIZATION_CHECK_V1"
UNKNOWN = "UNKNOWN"


def _fail(errors: list[str], **extra: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "universal_factorization_proved": False,
        "terminal_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
    out.update(extra)
    return out


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def evaluate(data: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(data, Mapping):
        return _fail(["INPUT_NOT_OBJECT"])

    mission_id = data.get("mission_id")
    carrier_id = data.get("carrier_schema_id")
    claim_id = data.get("claim_id")
    scope_sha256 = data.get("scope_sha256")
    semantics_sha256 = data.get("semantics_sha256")

    errors: list[str] = []
    if not isinstance(mission_id, str) or not mission_id:
        errors.append("MISSION_ID_INVALID")
    if not isinstance(carrier_id, str) or not carrier_id:
        errors.append("CARRIER_SCHEMA_ID_INVALID")
    if not _is_sha256(claim_id):
        errors.append("CLAIM_ID_INVALID")
    if not _is_sha256(scope_sha256):
        errors.append("SCOPE_SHA256_INVALID")
    if not _is_sha256(semantics_sha256):
        errors.append("SEMANTICS_SHA256_INVALID")
    if errors:
        return _fail(errors)

    worlds = data.get("worlds")
    if not isinstance(worlds, list) or not worlds:
        return _fail(["WORLDS_INVALID"])

    seen_worlds: set[str] = set()
    groups: dict[str, list[dict[str, Any]]] = {}

    for i, row in enumerate(worlds):
        if not isinstance(row, Mapping):
            errors.append(f"WORLD_{i}_NOT_OBJECT")
            continue

        wid = row.get("world_id")
        cid = row.get("carrier_value_id")
        verdict = row.get("mission_verdict", UNKNOWN)

        if not isinstance(wid, str) or not wid:
            errors.append(f"WORLD_{i}_ID_INVALID")
        elif wid in seen_worlds:
            errors.append(f"DUPLICATE_WORLD_ID:{wid}")
        else:
            seen_worlds.add(wid)

        if not isinstance(cid, str) or not cid:
            errors.append(f"WORLD_{i}_CARRIER_VALUE_ID_INVALID")

        if verdict not in (True, False, UNKNOWN):
            errors.append(f"WORLD_{i}_MISSION_VERDICT_INVALID")

        if (
            isinstance(wid, str)
            and wid
            and isinstance(cid, str)
            and cid
            and verdict in (True, False, UNKNOWN)
        ):
            groups.setdefault(cid, []).append({
                "world_id": wid,
                "mission_verdict": verdict,
            })

    if errors:
        return _fail(errors)

    conflicts: list[dict[str, Any]] = []
    unknown_carriers: set[str] = set()

    for cid, rows in sorted(groups.items()):
        known = {row["mission_verdict"] for row in rows if row["mission_verdict"] in (True, False)}
        if len(known) > 1:
            conflicts.append({
                "carrier_value_id": cid,
                "worlds": rows,
            })
        if any(row["mission_verdict"] == UNKNOWN for row in rows):
            unknown_carriers.add(cid)

    base = {
        "schema": SCHEMA,
        "pass": False,
        "mission_id": mission_id,
        "carrier_schema_id": carrier_id,
        "claim_id": claim_id,
        "scope_sha256": scope_sha256,
        "semantics_sha256": semantics_sha256,
        "world_count": len(worlds),
        "carrier_value_count": len(groups),
        "universal_factorization_proved": False,
        "global_mission_completion_derivable": False,
        "terminal_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "ownership_credit_delta": 0,
    }

    if conflicts:
        return {
            **base,
            "status": "CARRIER_FACTORIZATION_COUNTEREXAMPLE",
            "counterexamples": conflicts,
            "root_classification": [
                "R4_SEMANTIC_BINDING_FAILURE",
                "R1_SCOPE_CARRIER_DEFECT",
            ],
            "new_semantic_root_required": False,
        }

    if unknown_carriers:
        return {
            **base,
            "status": "UNKNOWN_FAIL_CLOSED",
            "unknown_carrier_value_ids": sorted(unknown_carriers),
            "new_semantic_root_required": False,
        }

    return {
        **base,
        "status": "NO_COUNTEREXAMPLE_IN_DECLARED_WITNESS_SET__NOT_PROOF",
        "counterexamples": [],
        "new_semantic_root_required": False,
        "rule": "FINITE_NONCONFLICT_DOES_NOT_ESTABLISH_UNIVERSAL_MISSION_FACTORIZATION",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    args = ap.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    out = evaluate(data)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["status"] != "FAIL_CLOSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
