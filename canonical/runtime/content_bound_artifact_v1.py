from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    digest = sha1()
    digest.update(f"blob {len(data)}".encode("ascii") + b"\0")
    digest.update(data)
    return digest.hexdigest()


def is_hex40(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(ch in "0123456789abcdef" for ch in value)
    )


def resolve_bound_file(
    path_value: Any,
    blob_sha: Any,
    repo_root: Path,
) -> tuple[Path | None, str | None]:
    if not isinstance(path_value, str) or not path_value.strip():
        return None, "PATH_REQUIRED"
    if not is_hex40(blob_sha):
        return None, "GIT_BLOB_SHA_INVALID"

    relative = Path(path_value)
    if relative.is_absolute():
        return None, "ABSOLUTE_PATH_FORBIDDEN"

    root = repo_root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None, "PATH_ESCAPES_REPOSITORY"

    if not candidate.is_file():
        return None, "BOUND_FILE_MISSING"
    if git_blob_sha(candidate) != blob_sha:
        return None, "GIT_BLOB_SHA_MISMATCH"
    return candidate, None


def load_bound_json(
    path_value: Any,
    blob_sha: Any,
    repo_root: Path,
) -> tuple[Mapping[str, Any] | None, str | None]:
    candidate, error = resolve_bound_file(path_value, blob_sha, repo_root)
    if error is not None:
        return None, error
    assert candidate is not None
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, "BOUND_JSON_UNREADABLE"
    if not isinstance(payload, Mapping):
        return None, "BOUND_JSON_NOT_OBJECT"
    return payload, None
