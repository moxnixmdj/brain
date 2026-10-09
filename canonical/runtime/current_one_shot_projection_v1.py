"""Dynamic exact-byte projection for the current one-shot closure frontier.

The one-shot runtime and its inner V1 closure are stable load-bearing code and
remain content-addressed in governance. R2 and terminal authority are moving
pointers, however. Treating their last observed blob hashes as permanently
"current" creates an avoidable race.

This module resolves those moving authorities from repository state at call time,
returns their exact Git blob identities, and makes snapshot drift observable
without turning ordinary concurrent progress into a false closure failure.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_CURRENT_ONE_SHOT_DYNAMIC_PROJECTION_V1"

PATHS = {
    "pointer": "canonical/governance/CURRENT_ONE_SHOT_REALITY_CLOSURE.json",
    "v1": "canonical/runtime/one_shot_verified_closure_v1.py",
    "v2": "canonical/runtime/one_shot_reality_closure_v2.py",
    "r2": "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
    "terminal": "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
    "self": "canonical/runtime/current_one_shot_projection_v1.py",
}

_VERSION = re.compile(r"(?:^|__)V(\d+)(?:__|$)")


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(str(path) + ":NOT_OBJECT")
    return value


def _version_from_status(status: Any) -> int | None:
    match = _VERSION.search(str(status or ""))
    return int(match.group(1)) if match else None


def evaluate(repo_root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve(strict=True)
    targets = {name: (root / rel).resolve(strict=True) for name, rel in PATHS.items()}
    for path in targets.values():
        path.relative_to(root)

    pointer = _load(targets["pointer"])
    r2 = _load(targets["r2"])
    terminal = _load(targets["terminal"])

    actual = {name: _blob(path) for name, path in targets.items()}
    errors: list[str] = []

    runtime = pointer.get("runtime") if isinstance(pointer.get("runtime"), dict) else {}
    predecessor = (
        pointer.get("predecessor")
        if isinstance(pointer.get("predecessor"), dict)
        else {}
    )
    authority = (
        pointer.get("authority")
        if isinstance(pointer.get("authority"), dict)
        else {}
    )
    dynamic = (
        authority.get("dynamic_current_projection")
        if isinstance(authority.get("dynamic_current_projection"), dict)
        else {}
    )

    if runtime.get("path") != PATHS["v2"]:
        errors.append("POINTER_V2_PATH_MISMATCH")
    if runtime.get("git_blob_sha") != actual["v2"]:
        errors.append("POINTER_V2_BLOB_MISMATCH")
    if predecessor.get("path") != PATHS["v1"]:
        errors.append("POINTER_V1_PATH_MISMATCH")
    if predecessor.get("git_blob_sha") != actual["v1"]:
        errors.append("POINTER_V1_BLOB_MISMATCH")
    if dynamic.get("path") != PATHS["self"]:
        errors.append("DYNAMIC_PROJECTION_PATH_MISMATCH")
    if dynamic.get("git_blob_sha") != actual["self"]:
        errors.append("DYNAMIC_PROJECTION_BLOB_MISMATCH")
    if dynamic.get("authoritative_for_moving_r2_and_terminal") is not True:
        errors.append("DYNAMIC_PROJECTION_NOT_AUTHORITATIVE_FOR_MOVING_POINTERS")
    if authority.get("static_projection_snapshots_authoritative") is not False:
        errors.append("STATIC_SNAPSHOTS_MUST_BE_NONAUTHORITATIVE")

    snapshot = pointer.get("current_projection_refresh_20261009")
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    terminal_snapshot_sha = str(
        snapshot.get("current_terminal_authority_git_blob_sha") or ""
    )
    r2_snapshot_sha = str(snapshot.get("current_r2_pointer_git_blob_sha") or "")

    result = {
        "schema": SCHEMA,
        "status": "PASS__DYNAMIC_CURRENT_PROJECTION"
        if not errors
        else "FAIL_CLOSED__DYNAMIC_CURRENT_PROJECTION",
        "pass": not errors,
        "errors": errors,
        "stable_load_bearing": {
            "one_shot_v1": {
                "path": PATHS["v1"],
                "git_blob_sha": actual["v1"],
            },
            "one_shot_v2": {
                "path": PATHS["v2"],
                "git_blob_sha": actual["v2"],
            },
        },
        "current_r2": {
            "path": PATHS["r2"],
            "git_blob_sha": actual["r2"],
            "status": r2.get("status"),
            "version": _version_from_status(r2.get("status")),
        },
        "current_terminal_authority": {
            "path": PATHS["terminal"],
            "git_blob_sha": actual["terminal"],
            "status": terminal.get("status"),
            "pointer_revision": terminal.get("pointer_revision"),
        },
        "snapshot_drift": {
            "r2_snapshot_differs_from_current": bool(r2_snapshot_sha)
            and r2_snapshot_sha != actual["r2"],
            "terminal_snapshot_differs_from_current": bool(terminal_snapshot_sha)
            and terminal_snapshot_sha != actual["terminal"],
            "snapshot_is_authoritative": False,
        },
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    return result


if __name__ == "__main__":
    print(json.dumps(evaluate(), sort_keys=True))
