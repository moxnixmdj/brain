#!/usr/bin/env python3
"""Count-generic executable audit for the current Escape-Progress successor.

V2 preserves the V1 row-proof schemas by reusing V1's Gap A / Gap B proof
validators, but it does not inherit V1's historical 9/4 causal split. The
current split is derived from the exact successor manifest and cross-checked
against the current V3 shared-gap binding.

This module is an audit only. It grants no acceptance, capability, ownership,
execution, or terminal authority. CC_R3 becomes true only when all 13 frozen
successor obligations are structurally current and carry valid row proofs.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.escape_progress_shared_gap_audit_v1 import (
    GAP_A,
    GAP_B,
    _audit_gap_a,
    _audit_gap_b,
)

ROOT = Path(__file__).resolve().parents[2]

MANIFEST_REL = "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json"
BINDING_REL = "canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V3.json"
FROZEN_V1_MANIFEST_REL = "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V1.json"
HISTORICAL_AUDIT_REL = "canonical/runtime/escape_progress_shared_gap_audit_v1.py"

MANIFEST_GIT_BLOB_SHA = "f3a566a982dcd867c583eafd24c6f5dd3baa0530"
BINDING_GIT_BLOB_SHA = "ecab2da83c1f21a2a9723221a74bc94514a04f32"
FROZEN_V1_MANIFEST_GIT_BLOB_SHA = "4ebe25308bf9816d4eeaea415b37b9ec152604c0"
HISTORICAL_AUDIT_GIT_BLOB_SHA = "53fb708e755561696f57b39705b04cefcaa2233b"

MANIFEST_SCHEMA = "PROJECT_BRAIN_ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_V2"
BINDING_SCHEMA = "PROJECT_BRAIN_ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V3"
SCHEMA = "PROJECT_BRAIN_ESCAPE_PROGRESS_SHARED_GAP_EXECUTABLE_AUDIT_V2"
EXPECTED_ROW_COUNT = 13
KNOWN_GROUPS = (GAP_A, GAP_B)


class EscapeProgressAuditV2Error(ValueError):
    pass


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _load_exact(root: Path, rel: str, expected_blob: str) -> dict[str, Any]:
    path = (root / rel).resolve(strict=True)
    path.relative_to(root.resolve())
    if not path.is_file() or path.is_symlink():
        raise EscapeProgressAuditV2Error("SOURCE_FILE_INVALID:" + rel)
    raw = path.read_bytes()
    actual = _git_blob_sha(raw)
    if actual != expected_blob:
        raise EscapeProgressAuditV2Error(
            "SOURCE_GIT_BLOB_DRIFT:" + rel + ":" + actual
        )
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise EscapeProgressAuditV2Error("SOURCE_OBJECT_REQUIRED:" + rel)
    return value


def _declared_manifest_counts(
    manifest: Mapping[str, Any],
    errors: list[str],
) -> dict[str, int]:
    collapse = manifest.get("shared_gap_collapse")
    if not isinstance(collapse, Sequence) or isinstance(collapse, (str, bytes)):
        errors.append("MANIFEST_SHARED_GAP_COLLAPSE_INVALID")
        return {}

    out: dict[str, int] = {}
    for raw in collapse:
        if not isinstance(raw, Mapping):
            errors.append("MANIFEST_SHARED_GAP_ROW_INVALID")
            continue
        group = str(raw.get("id") or "")
        count = raw.get("obligation_count")
        if group not in KNOWN_GROUPS:
            errors.append("MANIFEST_UNKNOWN_SHARED_GAP:" + group)
            continue
        if group in out:
            errors.append("MANIFEST_DUPLICATE_SHARED_GAP:" + group)
            continue
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            errors.append("MANIFEST_SHARED_GAP_COUNT_INVALID:" + group)
            continue
        out[group] = count

    if set(out) != set(KNOWN_GROUPS):
        errors.append("MANIFEST_SHARED_GAP_SET_INCOMPLETE")
    if sum(out.values()) != EXPECTED_ROW_COUNT:
        errors.append("MANIFEST_DECLARED_COUNTS_DO_NOT_SUM_TO_13")
    return out


def _declared_binding_counts(
    binding: Mapping[str, Any],
    errors: list[str],
) -> dict[str, int]:
    shared = binding.get("shared_gaps")
    if not isinstance(shared, Mapping):
        errors.append("BINDING_SHARED_GAPS_INVALID")
        return {}

    extra = sorted(set(str(x) for x in shared) - set(KNOWN_GROUPS))
    if extra:
        errors.append("BINDING_UNKNOWN_SHARED_GAPS:" + ",".join(extra))

    out: dict[str, int] = {}
    for group in KNOWN_GROUPS:
        row = shared.get(group)
        if not isinstance(row, Mapping):
            errors.append("BINDING_SHARED_GAP_MISSING:" + group)
            continue
        count = row.get("obligation_count")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            errors.append("BINDING_SHARED_GAP_COUNT_INVALID:" + group)
            continue
        out[group] = count

    if sum(out.values()) != EXPECTED_ROW_COUNT:
        errors.append("BINDING_DECLARED_COUNTS_DO_NOT_SUM_TO_13")
    return out


def _validate_binding_manifest_contract(
    binding: Mapping[str, Any],
    manifest_counts: Mapping[str, int],
    errors: list[str],
) -> None:
    current = binding.get("current_successor_manifest")
    if not isinstance(current, Mapping):
        errors.append("BINDING_CURRENT_SUCCESSOR_MANIFEST_INVALID")
        return

    if current.get("path") != MANIFEST_REL:
        errors.append("BINDING_SUCCESSOR_MANIFEST_PATH_MISMATCH")
    if current.get("git_blob_sha") != MANIFEST_GIT_BLOB_SHA:
        errors.append("BINDING_SUCCESSOR_MANIFEST_BLOB_MISMATCH")
    if current.get("row_count") != EXPECTED_ROW_COUNT:
        errors.append("BINDING_SUCCESSOR_ROW_COUNT_MISMATCH")
    if current.get("gap_a_count") != manifest_counts.get(GAP_A):
        errors.append("BINDING_SUCCESSOR_GAP_A_COUNT_MISMATCH")
    if current.get("gap_b_count") != manifest_counts.get(GAP_B):
        errors.append("BINDING_SUCCESSOR_GAP_B_COUNT_MISMATCH")

    historical = binding.get("historical_executable_audit")
    if not isinstance(historical, Mapping):
        errors.append("BINDING_HISTORICAL_AUDIT_INVALID")
    else:
        if historical.get("path") != HISTORICAL_AUDIT_REL:
            errors.append("BINDING_HISTORICAL_AUDIT_PATH_MISMATCH")
        if historical.get("git_blob_sha") != HISTORICAL_AUDIT_GIT_BLOB_SHA:
            errors.append("BINDING_HISTORICAL_AUDIT_BLOB_MISMATCH")


def audit(
    manifest: Mapping[str, Any],
    binding: Mapping[str, Any],
    row_proofs: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    frozen_obligation_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    open_predicates: list[str] = []
    proofs = row_proofs if isinstance(row_proofs, Mapping) else {}

    if manifest.get("schema") != MANIFEST_SCHEMA:
        errors.append("MANIFEST_SCHEMA_INVALID")
    if binding.get("schema") != BINDING_SCHEMA:
        errors.append("BINDING_SCHEMA_INVALID")

    manifest_counts = _declared_manifest_counts(manifest, errors)
    binding_counts = _declared_binding_counts(binding, errors)
    for group in KNOWN_GROUPS:
        if manifest_counts.get(group) != binding_counts.get(group):
            errors.append("MANIFEST_BINDING_COUNT_MISMATCH:" + group)

    _validate_binding_manifest_contract(binding, manifest_counts, errors)

    rows = manifest.get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        errors.append("MANIFEST_ROWS_INVALID")
        rows = []
    if len(rows) != EXPECTED_ROW_COUNT:
        errors.append("ROW_COUNT_NOT_13")

    ids: list[str] = []
    actual_counts = {GAP_A: 0, GAP_B: 0}
    per_row: list[dict[str, Any]] = []

    for raw in rows:
        if not isinstance(raw, Mapping):
            errors.append("ROW_NOT_OBJECT")
            continue
        oid = str(raw.get("obligation_id") or "")
        group = str(raw.get("route_group") or "")
        if not oid or oid in ids:
            errors.append("ROW_ID_INVALID_OR_DUPLICATE:" + oid)
            continue
        ids.append(oid)

        if group not in actual_counts:
            errors.append(f"{oid}:UNKNOWN_ROUTE_GROUP:{group}")
            continue
        actual_counts[group] += 1

        proof = proofs.get(oid)
        missing = (
            _audit_gap_a(raw, proof)
            if group == GAP_A
            else _audit_gap_b(raw, proof)
        )
        open_predicates.extend(missing)
        per_row.append(
            {
                "obligation_id": oid,
                "route_group": group,
                "closed": not missing,
                "missing_predicates": missing,
                "proof_sha256": (
                    proof.get("proof_sha256")
                    if isinstance(proof, Mapping)
                    else None
                ),
            }
        )

    for group in KNOWN_GROUPS:
        if actual_counts[group] != manifest_counts.get(group):
            errors.append(
                f"ROW_GROUP_COUNT_MISMATCH:{group}:"
                f"{actual_counts[group]}:{manifest_counts.get(group)}"
            )

    if frozen_obligation_ids is not None:
        frozen = list(frozen_obligation_ids)
        if (
            len(frozen) != EXPECTED_ROW_COUNT
            or any(not isinstance(x, str) or not x for x in frozen)
            or len(set(frozen)) != EXPECTED_ROW_COUNT
        ):
            errors.append("FROZEN_OBLIGATION_IDS_INVALID")
        elif ids != frozen:
            errors.append("FROZEN_OBLIGATION_ORDER_OR_SET_DRIFT")

    unknown_proofs = sorted(set(str(x) for x in proofs) - set(ids))
    if unknown_proofs:
        errors.append("PROOFS_FOR_UNKNOWN_ROWS:" + ",".join(unknown_proofs))

    cc_r3_proved = (
        not errors
        and not open_predicates
        and len(per_row) == EXPECTED_ROW_COUNT
        and all(row["closed"] for row in per_row)
    )
    status = (
        "PASS__CC_R3_SUCCESSOR_ESCAPE_PROGRESS_PROVED__13_OF_13"
        if cc_r3_proved
        else (
            "PASS__SUCCESSOR_EXECUTABLE_AUDIT_CURRENT__CC_R3_OPEN"
            if not errors
            else "FAIL_CLOSED__SUCCESSOR_AUDIT_INPUT_DRIFT"
        )
    )
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": not errors,
        "cc_r3_proved": cc_r3_proved,
        "row_count": len(per_row),
        "closed_row_count": sum(1 for row in per_row if row["closed"]),
        "open_row_count": sum(1 for row in per_row if not row["closed"]),
        "gap_a_count": actual_counts[GAP_A],
        "gap_b_count": actual_counts[GAP_B],
        "manifest_declared_counts": dict(manifest_counts),
        "binding_declared_counts": dict(binding_counts),
        "open_predicates": sorted(open_predicates),
        "rows": per_row,
        "errors": errors,
        "execution_authority": False,
        "acceptance_authority": False,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def audit_repo(
    root: Path = ROOT,
    row_proofs: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    manifest = _load_exact(root, MANIFEST_REL, MANIFEST_GIT_BLOB_SHA)
    binding = _load_exact(root, BINDING_REL, BINDING_GIT_BLOB_SHA)
    frozen = _load_exact(
        root,
        FROZEN_V1_MANIFEST_REL,
        FROZEN_V1_MANIFEST_GIT_BLOB_SHA,
    )

    historical_path = (root / HISTORICAL_AUDIT_REL).resolve(strict=True)
    historical_path.relative_to(root)
    historical_raw = historical_path.read_bytes()
    if _git_blob_sha(historical_raw) != HISTORICAL_AUDIT_GIT_BLOB_SHA:
        raise EscapeProgressAuditV2Error("HISTORICAL_AUDIT_GIT_BLOB_DRIFT")

    frozen_rows = frozen.get("rows")
    if not isinstance(frozen_rows, list):
        raise EscapeProgressAuditV2Error("FROZEN_V1_ROWS_INVALID")
    frozen_ids = [
        str(row.get("obligation_id") or "")
        for row in frozen_rows
        if isinstance(row, Mapping)
    ]

    return audit(
        manifest,
        binding,
        row_proofs=row_proofs,
        frozen_obligation_ids=frozen_ids,
    )


if __name__ == "__main__":
    print(json.dumps(audit_repo(), sort_keys=True))
