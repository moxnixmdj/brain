#!/usr/bin/env python3
"""Validate the current V2 escape-progress overlay over the immutable V1 provenance."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.escape_progress_13_route_manifest_v1 import validate_manifest as validate_v1

ROOT = Path(__file__).resolve().parents[2]
V2_PATH = "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json"


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def load_json(root: Path, rel: str) -> dict[str, Any]:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def validate_repo(root: Path = ROOT) -> dict[str, Any]:
    errors: list[str] = []
    overlay = load_json(root, V2_PATH)

    base_ref = overlay.get("base_manifest") or {}
    claim_ref = overlay.get("frozen_claim") or {}
    progress_ref = overlay.get("shared_progress_reduction") or {}
    currentness = overlay.get("currentness") or {}

    base_path = str(base_ref.get("path") or "")
    claim_path = str(claim_ref.get("path") or "")
    progress_path = str(progress_ref.get("path") or "")
    tb_pointer_path = str(currentness.get("tb_pointer_path") or "")
    tb_authority_path = str(currentness.get("required_rank19_authority_path") or "")

    refs = (
        ("BASE", base_path, base_ref.get("git_blob_sha")),
        ("CLAIM", claim_path, claim_ref.get("git_blob_sha")),
        ("PROGRESS", progress_path, progress_ref.get("git_blob_sha")),
        ("TB_POINTER", tb_pointer_path, currentness.get("tb_pointer_git_blob_sha")),
        ("TB_AUTHORITY", tb_authority_path, currentness.get("required_rank19_authority_git_blob_sha")),
    )
    docs: dict[str, Mapping[str, Any]] = {}
    for label, path, expected in refs:
        if not path:
            errors.append(label + "_PATH_MISSING")
            continue
        try:
            data = (root / path).read_bytes()
        except Exception:
            errors.append(label + "_UNREADABLE")
            continue
        if blob_sha(data) != expected:
            errors.append(label + "_BLOB_STALE")
        try:
            docs[label] = json.loads(data)
        except Exception:
            errors.append(label + "_JSON_INVALID")

    if errors:
        return {
            "pass": False,
            "status": "FAIL_CLOSED__ESCAPE13_V2_CURRENTNESS",
            "errors": sorted(set(errors)),
            "terminal_credit_delta": 0,
        }

    base = copy.deepcopy(dict(docs["BASE"]))
    claim = docs["CLAIM"]
    override = (overlay.get("row_overrides") or {}).get("TB_SCIENCE_GE_58_7") or {}
    rows = list(base.get("rows") or [])
    matched = False
    for row in rows:
        if row.get("obligation_id") != "TB_SCIENCE_GE_58_7":
            continue
        matched = True
        row.update(
            {
                "route_group": override.get("route_group"),
                "route_class": override.get("route_class"),
                "evidence": [
                    override.get("evidence_path"),
                    override.get("evidence_git_blob_sha"),
                ],
                "required_strings": [
                    override.get("required_status"),
                    override.get("required_precondition"),
                ],
                "current_route_available": override.get("current_route_available"),
                "strict_progress_witness_bound": override.get("strict_progress_witness_bound"),
                "externality_proved": override.get("externality_proved"),
            }
        )
    if not matched:
        errors.append("TB_OVERRIDE_TARGET_MISSING")

    base["rows"] = rows
    v1 = validate_v1(base, claim, lambda rel: (root / rel).read_bytes())
    if v1.get("pass") is not True:
        errors.extend("EFFECTIVE_V1:" + x for x in v1.get("errors", []))

    progress = docs["PROGRESS"]
    composed = progress.get("composed_reduction") or {}
    if progress.get("status") != (
        "ACTIVE_CANDIDATE__LIVE_CERTIFIED_CONSTRUCTOR_PLUS_SHARED_WELL_FOUNDED_REPAIR_DESCENT__"
        "GLOBAL_REPAIR_ACQUIRABILITY_OPEN__ZERO_CREDIT"
    ):
        errors.append("SHARED_PROGRESS_STATUS_DRIFT")
    if progress_ref.get("generic_well_founded_measure_proved") is not True:
        errors.append("SHARED_PROGRESS_MEASURE_NOT_PROVED")
    if progress_ref.get("specific_internal_action_bindings_proved") != 0:
        errors.append("SPECIFIC_ACTION_CREDIT_MUST_REMAIN_ZERO")
    if progress_ref.get("global_repair_acquirability_proved") is not False:
        errors.append("REPAIR_ACQUIRABILITY_MUST_REMAIN_OPEN")
    if progress_ref.get("global_escape_progress_totality_proved") is not False:
        errors.append("GLOBAL_ESCAPE_TOTALITY_MUST_REMAIN_OPEN")
    if progress_ref.get("cc_r3_proved") is not False:
        errors.append("CC_R3_MUST_REMAIN_OPEN")
    if composed.get("global_repair_acquirability_proved") is not False:
        errors.append("COMPOSED_REDUCTION_REPAIR_TOTALITY_DRIFT")

    tb_pointer = docs["TB_POINTER"]
    staged = tb_pointer.get("staged_rank19") or {}
    if staged.get("authority_path") != tb_authority_path:
        errors.append("TB_POINTER_AUTHORITY_PATH_DRIFT")
    if staged.get("authority_git_blob_sha") != currentness.get("required_rank19_authority_git_blob_sha"):
        errors.append("TB_POINTER_AUTHORITY_BLOB_DRIFT")
    if staged.get("execution_authority_effective") is not False:
        errors.append("TB_POINTER_ALREADY_EFFECTIVE_OR_SCHEMA_DRIFT")

    tb_authority = docs["TB_AUTHORITY"]
    if tb_authority.get("execution_authority_effective") is not False:
        errors.append("TB_AUTHORITY_EFFECTIVE_BEFORE_RESEAL")
    if tb_authority.get("terminal_credit_delta") != 0:
        errors.append("TB_AUTHORITY_TERMINAL_CREDIT_NONZERO")

    if (overlay.get("accounting") or {}).get("terminal_credit_delta") != 0:
        errors.append("OVERLAY_TERMINAL_CREDIT_NONZERO")
    if "NO_CC_R3_CERTIFICATE" not in (overlay.get("hard_nonclaims") or []):
        errors.append("CC_R3_NONCLAIM_MISSING")

    return {
        "pass": not errors,
        "status": (
            "PASS__ESCAPE13_V2_CURRENT__SHARED_PROGRESS_BOUND__"
            "GLOBAL_REPAIR_ACQUIRABILITY_OPEN__CC_R3_OPEN__ZERO_CREDIT"
            if not errors
            else "FAIL_CLOSED__ESCAPE13_V2_CURRENTNESS"
        ),
        "errors": sorted(set(errors)),
        "effective_v1": v1,
        "row_count": v1.get("row_count"),
        "gap_a_count": v1.get("gap_a_count"),
        "gap_b_count": v1.get("gap_b_count"),
        "shared_well_founded_progress_measure_bound": progress_ref.get("generic_well_founded_measure_proved") is True,
        "specific_internal_action_bindings_proved": progress_ref.get("specific_internal_action_bindings_proved"),
        "global_repair_acquirability_proved": False,
        "global_escape_progress_totality_proved": False,
        "cc_r3_proved": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(validate_repo(), sort_keys=True))
