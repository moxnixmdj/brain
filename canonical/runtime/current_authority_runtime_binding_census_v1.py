"""Exact-byte census for runtime bindings in CURRENT_TERMINAL_AUTHORITY.

This verifier distinguishes current authority from explicitly superseded evidence.
It proves only byte-binding coherence. It does not prove runtime semantics,
refinement, reachability, capability ownership, or terminal closure.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CURRENT_AUTHORITY_RUNTIME_BINDING_CENSUS_V1"
RUNTIME_PATH_RE = re.compile(r"^canonical/runtime/[A-Za-z0-9_./-]+\.py$")
_HEX = set("0123456789abcdef")


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _hex40(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(ch in _HEX for ch in value)
    )


def _collect_runtime_bindings(
    value: Any,
    *,
    key_path: tuple[str, ...] = (),
    inherited_status: str = "",
    inherited_superseded_by: str = "",
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(value, Mapping):
        local_status = str(value.get("status") or inherited_status or "")
        local_superseded_by = str(
            value.get("superseded_by") or inherited_superseded_by or ""
        )
        raw_path = value.get("path")
        if isinstance(raw_path, str) and RUNTIME_PATH_RE.fullmatch(raw_path):
            superseded = (
                bool(local_superseded_by)
                or "SUPERSEDED" in local_status.upper()
            )
            out.append(
                {
                    "key_path": ".".join(key_path),
                    "path": raw_path,
                    "expected_git_blob_sha": value.get("git_blob_sha"),
                    "status": local_status or None,
                    "superseded_by": local_superseded_by or None,
                    "superseded": superseded,
                }
            )
        for key, item in value.items():
            out.extend(
                _collect_runtime_bindings(
                    item,
                    key_path=key_path + (str(key),),
                    inherited_status=local_status,
                    inherited_superseded_by=local_superseded_by,
                )
            )
    elif isinstance(value, list):
        for index, item in enumerate(value):
            out.extend(
                _collect_runtime_bindings(
                    item,
                    key_path=key_path + (str(index),),
                    inherited_status=inherited_status,
                    inherited_superseded_by=inherited_superseded_by,
                )
            )
    return out


def run(
    repo_root: str | Path,
    *,
    authority_path: str = "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    authority_file = (root / authority_path).resolve()
    if root not in authority_file.parents or not authority_file.is_file():
        raise ValueError("AUTHORITY_POINTER_MISSING_OR_OUTSIDE_REPO")

    raw = json.loads(authority_file.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ValueError("AUTHORITY_POINTER_NOT_OBJECT")

    bindings = _collect_runtime_bindings(raw)
    current = [row for row in bindings if not row["superseded"]]
    superseded = [row for row in bindings if row["superseded"]]

    errors: list[dict[str, Any]] = []
    checked: list[dict[str, Any]] = []
    drift_count = 0
    missing_blob_binding_count = 0
    missing_runtime_file_count = 0

    expected_by_path: dict[str, set[str]] = {}
    for row in current:
        path = row["path"]
        expected = row.get("expected_git_blob_sha")
        if _hex40(expected):
            expected_by_path.setdefault(path, set()).add(str(expected))
        else:
            missing_blob_binding_count += 1
            errors.append(
                {
                    "kind": "CURRENT_RUNTIME_BLOB_BINDING_MISSING_OR_INVALID",
                    "key_path": row["key_path"],
                    "path": path,
                    "expected_git_blob_sha": expected,
                }
            )

        full = (root / path).resolve()
        if root not in full.parents or not full.is_file():
            missing_runtime_file_count += 1
            errors.append(
                {
                    "kind": "CURRENT_RUNTIME_FILE_MISSING",
                    "key_path": row["key_path"],
                    "path": path,
                }
            )
            continue

        actual = git_blob_sha(full)
        checked_row = {**row, "actual_git_blob_sha": actual}
        checked.append(checked_row)
        if _hex40(expected) and expected != actual:
            drift_count += 1
            errors.append(
                {
                    "kind": "RUNTIME_BLOB_DRIFT",
                    "key_path": row["key_path"],
                    "path": path,
                    "expected_git_blob_sha": expected,
                    "actual_git_blob_sha": actual,
                }
            )

    conflicts = [
        {"path": path, "expected_git_blob_shas": sorted(values)}
        for path, values in sorted(expected_by_path.items())
        if len(values) > 1
    ]
    for conflict in conflicts:
        errors.append(
            {
                "kind": "CONFLICTING_CURRENT_RUNTIME_BINDINGS",
                **conflict,
            }
        )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CURRENT_RUNTIME_BYTE_BINDINGS_COHERENT"
            if not errors
            else "OPEN__CURRENT_RUNTIME_BYTE_BINDING_DRIFT"
        ),
        "pass": not errors,
        "authority_pointer_path": authority_path,
        "runtime_binding_reference_count": len(bindings),
        "current_binding_count": len(current),
        "superseded_binding_count": len(superseded),
        "current_unique_runtime_path_count": len({row["path"] for row in current}),
        "superseded_unique_runtime_path_count": len(
            {row["path"] for row in superseded}
        ),
        "checked_current_bindings": checked,
        "superseded_bindings": superseded,
        "drift_count": drift_count,
        "missing_blob_binding_count": missing_blob_binding_count,
        "missing_runtime_file_count": missing_runtime_file_count,
        "conflicting_current_path_count": len(conflicts),
        "conflicting_current_paths": conflicts,
        "errors": errors,
        "byte_binding_coherence_proved": not errors,
        "semantic_refinement_proved": False,
        "runtime_reachability_proved": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
