"""Repository-local Git blob content binding validation.

A path/SHA pair is creditable only when the path resolves to a real regular file
inside this checkout and the exact bytes hash to the declared Git blob SHA-1.
This prevents 40-hex placeholders from masquerading as content-addressed proof.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def validate_repo_blob_binding(
    value: Any,
    *,
    repo_root: Path = REPO_ROOT,
) -> bool:
    if not isinstance(value, Mapping):
        return False
    rel_text = value.get("path")
    claimed = value.get("git_blob_sha")
    if (
        not isinstance(rel_text, str)
        or not rel_text.strip()
        or not isinstance(claimed, str)
        or len(claimed) != 40
        or any(ch not in "0123456789abcdef" for ch in claimed)
    ):
        return False

    rel = Path(rel_text)
    if rel.is_absolute():
        return False
    try:
        root = repo_root.resolve()
        candidate = (root / rel).resolve(strict=True)
        candidate.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return False
    return candidate.is_file() and git_blob_sha(candidate) == claimed
