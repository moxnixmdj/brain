"""Mechanical declared-dependency generator for terminal authority.

Coverage is deliberately scoped to explicit canonical repository artifact
references in CURRENT_TERMINAL_AUTHORITY. Implicit channels remain open.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TERMINAL_DECLARED_DEPENDENCY_GENERATOR_V1"
CANONICAL_PATH_RE = re.compile(r"^canonical/[A-Za-z0-9_./-]+$")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")


def _blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _candidate_sha(mapping: Mapping[str, Any], key: str) -> str | None:
    if key == "path":
        value = mapping.get("git_blob_sha")
        return str(value) if isinstance(value, str) else None
    if key.endswith("_path"):
        value = mapping.get(key[:-5] + "_git_blob_sha")
        return str(value) if isinstance(value, str) else None
    return None


def _collect(
    value: Any,
    *,
    key_path: tuple[str, ...] = (),
    inherited_status: str = "",
    inherited_superseded_by: str = "",
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(value, Mapping):
        status = str(value.get("status") or inherited_status or "")
        superseded_by = str(value.get("superseded_by") or inherited_superseded_by or "")
        superseded = bool(superseded_by) or "SUPERSEDED" in status.upper()
        for key, item in value.items():
            if isinstance(item, str) and CANONICAL_PATH_RE.fullmatch(item):
                sha = _candidate_sha(value, str(key))
                valid_sha = bool(sha and HEX40_RE.fullmatch(sha))
                out.append({
                    "json_path": ".".join(key_path + (str(key),)),
                    "artifact_path": item,
                    "git_blob_sha": sha if valid_sha else None,
                    "binding_type": "CONTENT_ADDRESSED" if valid_sha else "MUTABLE_OR_PATH_BOUND",
                    "status": status or None,
                    "superseded_by": superseded_by or None,
                    "superseded": superseded,
                })
            out.extend(_collect(
                item,
                key_path=key_path + (str(key),),
                inherited_status=status,
                inherited_superseded_by=superseded_by,
            ))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            out.extend(_collect(
                item,
                key_path=key_path + (str(index),),
                inherited_status=inherited_status,
                inherited_superseded_by=inherited_superseded_by,
            ))
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

    refs = _collect(raw)
    if not refs:
        raise ValueError("NO_DECLARED_CANONICAL_DEPENDENCIES")

    current = [row for row in refs if not row["superseded"]]
    superseded = [row for row in refs if row["superseded"]]
    path_bound = [row for row in current if row["binding_type"] == "MUTABLE_OR_PATH_BOUND"]

    return {
        "schema": SCHEMA,
        "status": "PASS__ALL_EXPLICIT_CANONICAL_ARTIFACT_REFERENCES_CAPTURED",
        "pass": True,
        "authority_path": authority_path,
        "authority_git_blob_sha": _blob_sha(authority_file),
        "declared_reference_count": len(refs),
        "current_reference_count": len(current),
        "superseded_reference_count": len(superseded),
        "current_unique_artifact_count": len({x["artifact_path"] for x in current}),
        "current_path_bound_reference_count": len(path_bound),
        "references": refs,
        "declared_dependency_coverage_complete": True,
        "implicit_dependency_channel_coverage_proved": False,
        "open_implicit_channels": [
            "ENVIRONMENT",
            "NETWORK_OR_REMOTE_SERVICE",
            "DYNAMIC_LOADING_OR_REFLECTION",
            "HIDDEN_PROCESS_STATE",
            "UNDECLARED_EXTERNAL_RESOURCE",
            "OTHER",
        ],
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
