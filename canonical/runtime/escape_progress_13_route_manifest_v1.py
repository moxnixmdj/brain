#!/usr/bin/env python3
"""Validate the frozen-13 route manifest without granting CC_R3 credit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V1.json"
CLAIM_PATH = ROOT / "canonical/governance/ESCAPE_PROGRESS_TOTALITY_FROZEN_13_CLAIM_20261010_V3.json"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def validate_manifest(
    manifest: Mapping[str, Any],
    claim: Mapping[str, Any],
    read_bytes: Callable[[str], bytes],
) -> dict[str, Any]:
    errors: list[str] = []
    rows = list(manifest.get("rows") or [])
    claim_ids = list((claim.get("scope") or {}).get("obligation_ids") or [])
    row_ids = [str(row.get("obligation_id") or "") for row in rows]

    if manifest.get("claim", {}).get("claim_id") != claim.get("claim_id"):
        errors.append("CLAIM_ID_DRIFT")
    if len(rows) != 13:
        errors.append("ROW_COUNT_NOT_13")
    if row_ids != claim_ids:
        errors.append("ROW_IDS_DO_NOT_MATCH_FROZEN_CLAIM_ORDER")
    if len(set(row_ids)) != len(row_ids):
        errors.append("DUPLICATE_OBLIGATION_ID")

    group_counts: dict[str, int] = {}
    strict_count = 0
    external_count = 0

    for row in rows:
        oid = str(row.get("obligation_id") or "")
        group = str(row.get("route_group") or "")
        group_counts[group] = group_counts.get(group, 0) + 1
        strict_count += int(row.get("strict_progress_witness_bound") is True)
        external_count += int(row.get("externality_proved") is True)

        evidence = row.get("evidence") or []
        if not isinstance(evidence, list) or len(evidence) != 2:
            errors.append(f"{oid}:BAD_EVIDENCE_REFERENCE")
            continue
        path, expected_sha = evidence
        try:
            data = read_bytes(str(path))
        except Exception:
            errors.append(f"{oid}:EVIDENCE_UNREADABLE")
            continue
        actual_sha = git_blob_sha(data)
        if actual_sha != expected_sha:
            errors.append(f"{oid}:EVIDENCE_BLOB_STALE")
        text = data.decode("utf-8", errors="replace")
        for required in row.get("required_strings") or []:
            if str(required) not in text:
                errors.append(f"{oid}:SUPPORT_STRING_MISSING:{required}")

        if row.get("externality_proved") is not False:
            errors.append(f"{oid}:EXTERNALITY_MUST_REMAIN_FALSE_WITHOUT_CERTIFICATE")
        if row.get("strict_progress_witness_bound") is not False:
            errors.append(f"{oid}:STRICT_PROGRESS_CREDIT_NOT_SUPPORTED_BY_THIS_MANIFEST")

    shared = manifest.get("shared_progress_reduction") or {}
    shared_evidence = shared.get("evidence") or []
    if not isinstance(shared_evidence, list) or len(shared_evidence) != 2:
        errors.append("SHARED_PROGRESS_BAD_EVIDENCE_REFERENCE")
    else:
        shared_path, shared_expected_sha = shared_evidence
        try:
            shared_data = read_bytes(str(shared_path))
        except Exception:
            errors.append("SHARED_PROGRESS_EVIDENCE_UNREADABLE")
        else:
            if git_blob_sha(shared_data) != shared_expected_sha:
                errors.append("SHARED_PROGRESS_EVIDENCE_BLOB_STALE")
            shared_text = shared_data.decode("utf-8", errors="replace")
            for required in shared.get("required_strings") or []:
                if str(required) not in shared_text:
                    errors.append(
                        "SHARED_PROGRESS_SUPPORT_STRING_MISSING:" + str(required)
                    )

    if shared.get("generic_well_founded_measure_proved") is not True:
        errors.append("SHARED_PROGRESS_MEASURE_NOT_PROVED")
    if shared.get("specific_internal_action_bindings_proved") != 0:
        errors.append("SHARED_PROGRESS_ROW_CREDIT_MUST_REMAIN_ZERO")
    if shared.get("provider_totality_proved") is not False:
        errors.append("SHARED_PROGRESS_PROVIDER_TOTALITY_MUST_REMAIN_OPEN")
    if shared.get("gap_b_closed") is not False:
        errors.append("GAP_B_MUST_REMAIN_OPEN_WITHOUT_ACTION_BINDINGS")
    if shared.get("cc_r3_proved") is not False:
        errors.append("SHARED_PROGRESS_CANNOT_GRANT_CC_R3")

    derived = manifest.get("derived_truth") or {}
    if group_counts.get("GAP_A_ACQUISITION_TOTALITY", 0) != 9:
        errors.append("GAP_A_COUNT_NOT_9")
    if group_counts.get("GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS", 0) != 4:
        errors.append("GAP_B_COUNT_NOT_4")
    if strict_count != 0 or derived.get("strict_progress_witness_bound_count") != 0:
        errors.append("STRICT_PROGRESS_COUNT_MUST_BE_ZERO")
    if external_count != 0 or derived.get("externality_proved_count") != 0:
        errors.append("EXTERNALITY_COUNT_MUST_BE_ZERO")
    if derived.get("cc_r3_proved") is not False:
        errors.append("CC_R3_MUST_REMAIN_OPEN")
    if (manifest.get("accounting") or {}).get("terminal_credit_delta") != 0:
        errors.append("TERMINAL_CREDIT_MUST_BE_ZERO")
    if "NO_CC_R3_CERTIFICATE" not in (manifest.get("hard_nonclaims") or []):
        errors.append("CC_R3_NONCLAIM_MISSING")

    return {
        "pass": not errors,
        "status": (
            "PASS__MANIFEST_CURRENT__SHARED_PROGRESS_MEASURE_BOUND__ACTION_BINDINGS_AND_PROVIDER_TOTALITY_OPEN__CC_R3_OPEN__ZERO_CREDIT"
            if not errors
            else "FAIL_CLOSED__ESCAPE13_ROUTE_MANIFEST_DRIFT"
        ),
        "errors": errors,
        "row_count": len(rows),
        "gap_a_count": group_counts.get("GAP_A_ACQUISITION_TOTALITY", 0),
        "gap_b_count": group_counts.get("GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS", 0),
        "strict_progress_witness_bound_count": strict_count,
        "externality_proved_count": external_count,
        "shared_well_founded_progress_measure_bound": shared.get("generic_well_founded_measure_proved") is True,
        "gap_b_specific_action_bindings_proved": shared.get("specific_internal_action_bindings_proved"),
        "provider_totality_proved": shared.get("provider_totality_proved"),
        "cc_r3_proved": False,
        "terminal_credit_delta": 0,
    }


def validate_repo(root: Path = ROOT) -> dict[str, Any]:
    manifest = json.loads((root / MANIFEST_PATH.relative_to(ROOT)).read_text(encoding="utf-8"))
    claim = json.loads((root / CLAIM_PATH.relative_to(ROOT)).read_text(encoding="utf-8"))
    return validate_manifest(manifest, claim, lambda rel: (root / rel).read_bytes())


if __name__ == "__main__":
    print(json.dumps(validate_repo(), sort_keys=True))
