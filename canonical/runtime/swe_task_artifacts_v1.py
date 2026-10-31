"""Small artifact boundary for task-bound SWE adapters; no capability credit.

Reports are published atomically without replacing an existing destination.
This is not a filesystem sandbox or a general source-tree transaction.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any


def confined_path(repo: Path, raw: Any) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("PATH_REQUIRED")
    path = (repo / raw).resolve()
    if path == repo or repo not in path.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return path


def fresh_output(repo: Path, raw: Any, default: str) -> Path:
    selected = default if raw is None else raw
    path = confined_path(repo, selected)
    if (repo / selected).is_symlink() or path.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    return path


def publish_report(repo: Path, output: Path, report: dict) -> dict:
    raw = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    # A same-directory hard link publishes complete bytes with no replacement,
    # including when another task wins the destination after preflight.
    with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".swe-report-", delete=False) as f:
        temporary = Path(f.name)
        try:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return {**report, "output_path": output.relative_to(repo).as_posix(),
            "output_sha256": hashlib.sha256(raw).hexdigest(),
            "artifact_integrity_verified": output.read_bytes() == raw,
            # Legacy registry expectations use this field for claimed effects.
            # An intact diagnostic report must NOT authorize those effects.
            "output_verified": report.get("verified") is True}
