"""Exact static canonical-import closure for current runtime refinement roots.

Reads the current executable-refinement obligation snapshot, verifies every
explicit root against its Git blob SHA, and delegates transitive canonical.*
Python import closure to brain_owned_python_closure_census_v1.

This proves only static Python import reachability. Dynamic loading, environment,
network/remote services, process state, and OTHER remain separate obligations.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.brain_owned_python_closure_census_v1 import census

SCHEMA = "PROJECT_BRAIN_CURRENT_RUNTIME_STATIC_IMPORT_CLOSURE_V1"
SNAPSHOT_SCHEMA = "PROJECT_BRAIN_CURRENT_AUTHORITY_RUNTIME_REFINEMENT_OBLIGATION_SNAPSHOT_V1"


class StaticImportClosureError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + bytes([0]) + raw).hexdigest()


def run(
    repo_root: str | Path,
    *,
    snapshot_path: str = (
        "canonical/governance/"
        "CURRENT_AUTHORITY_RUNTIME_REFINEMENT_OBLIGATION_SNAPSHOT_20261010_V1.json"
    ),
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    snapshot_file = (root / snapshot_path).resolve()
    try:
        snapshot_file.relative_to(root)
    except ValueError as exc:
        raise StaticImportClosureError("SNAPSHOT_OUTSIDE_REPOSITORY") from exc
    if not snapshot_file.is_file():
        raise StaticImportClosureError("SNAPSHOT_MISSING")

    snapshot = json.loads(snapshot_file.read_text(encoding="utf-8"))
    if not isinstance(snapshot, Mapping) or snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise StaticImportClosureError("SNAPSHOT_SCHEMA_INVALID")
    obligations = snapshot.get("obligations")
    if not isinstance(obligations, list) or not obligations:
        raise StaticImportClosureError("SNAPSHOT_OBLIGATIONS_INVALID")

    roots: list[str] = []
    explicit: list[dict[str, str]] = []
    for index, row in enumerate(obligations):
        if not isinstance(row, Mapping):
            raise StaticImportClosureError(f"OBLIGATION_NOT_OBJECT:{index}")
        path = str(row.get("path") or "")
        expected = str(row.get("git_blob_sha") or "")
        file = (root / path).resolve()
        try:
            file.relative_to(root)
        except ValueError as exc:
            raise StaticImportClosureError(f"ROOT_OUTSIDE_REPOSITORY:{index}") from exc
        if not file.is_file():
            raise StaticImportClosureError("ROOT_MISSING:" + path)
        actual = _git_blob_sha(file)
        if actual != expected:
            raise StaticImportClosureError("ROOT_BLOB_DRIFT:" + path)
        roots.append(path)
        explicit.append({"path": path, "git_blob_sha": actual})

    result = census(root, roots)
    rows = result["brain_owned_transitive_files"]
    explicit_paths = {row["path"] for row in explicit}
    hidden = [row["path"] for row in rows if row["path"] not in explicit_paths]
    return {
        "schema": SCHEMA,
        "status": "PASS__STATIC_CANONICAL_IMPORT_CLOSURE_COMPLETE",
        "pass": True,
        "snapshot": {
            "path": snapshot_path,
            "git_blob_sha": _git_blob_sha(snapshot_file),
        },
        "explicit_root_count": len(explicit),
        "explicit_roots": explicit,
        "transitive_canonical_python_file_count": result["brain_owned_file_count"],
        "hidden_transitive_canonical_file_count": len(hidden),
        "hidden_transitive_canonical_files": sorted(hidden),
        "external_substrate_imports": result["external_substrate_imports"],
        "static_canonical_import_closure_complete": True,
        "dynamic_loading_channel_closed": False,
        "environment_channel_closed": False,
        "network_remote_channel_closed": False,
        "hidden_process_state_closed": False,
        "other_channel_closed": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
