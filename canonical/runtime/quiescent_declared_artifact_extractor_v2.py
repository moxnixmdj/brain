#!/usr/bin/env python3
"""Extract only predeclared regular artifacts from a quiescent private overlay."""
from __future__ import annotations

import hashlib
import os
import pathlib
import stat
from dataclasses import dataclass
from typing import Mapping

SCHEMA = "PROJECT_BRAIN_QUIESCENT_DECLARED_ARTIFACT_EXTRACTOR_V2"


class ArtifactExtractionError(ValueError):
    pass


@dataclass(frozen=True)
class DeclaredArtifact:
    artifact_id: str
    relative_path: str
    media_type: str
    max_bytes: int


def _token(value: str, label: str, max_len: int = 256) -> str:
    value = str(value or "")
    if not value or "\x00" in value or len(value) > max_len:
        raise ArtifactExtractionError(label + "_INVALID")
    return value


def _safe_rel(value: str) -> pathlib.PurePosixPath:
    raw = str(value or "").replace("\\", "/").strip()
    path = pathlib.PurePosixPath(raw)
    if (
        not raw
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ArtifactExtractionError("ARTIFACT_PATH_INVALID")
    return path


def _open_regular_no_symlink(
    root: pathlib.Path,
    rel: pathlib.PurePosixPath,
) -> tuple[int, os.stat_result, pathlib.Path]:
    cursor = root
    final_lstat: os.stat_result | None = None
    final_path: pathlib.Path | None = None

    for index, part in enumerate(rel.parts):
        candidate = cursor / part
        try:
            info = os.lstat(candidate)
        except FileNotFoundError as exc:
            raise ArtifactExtractionError("DECLARED_ARTIFACT_MISSING") from exc
        if stat.S_ISLNK(info.st_mode):
            raise ArtifactExtractionError("ARTIFACT_SYMLINK_REJECTED")
        if index < len(rel.parts) - 1:
            if not stat.S_ISDIR(info.st_mode):
                raise ArtifactExtractionError("ARTIFACT_PARENT_NOT_DIRECTORY")
            cursor = candidate
        else:
            final_lstat = info
            final_path = candidate

    if final_lstat is None or final_path is None:
        raise ArtifactExtractionError("ARTIFACT_PATH_INVALID")
    if not stat.S_ISREG(final_lstat.st_mode):
        raise ArtifactExtractionError("DECLARED_ARTIFACT_NOT_REGULAR_FILE")

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(final_path, flags)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise ArtifactExtractionError("OPENED_ARTIFACT_NOT_REGULAR_FILE")
        if (
            opened.st_dev != final_lstat.st_dev
            or opened.st_ino != final_lstat.st_ino
        ):
            raise ArtifactExtractionError("ARTIFACT_IDENTITY_CHANGED")
        return fd, opened, final_path
    except Exception:
        os.close(fd)
        raise


def extract_declared_artifacts(
    private_overlay_root: str | pathlib.Path,
    declarations: Mapping[str, DeclaredArtifact],
) -> dict:
    root = pathlib.Path(private_overlay_root).resolve(strict=True)
    if not root.is_dir():
        raise ArtifactExtractionError("OVERLAY_ROOT_NOT_DIRECTORY")
    if not isinstance(declarations, Mapping):
        raise ArtifactExtractionError("DECLARATIONS_NOT_MAPPING")

    rows: list[dict] = []
    seen_paths: set[str] = set()

    for artifact_id in sorted(declarations):
        decl = declarations[artifact_id]
        if not isinstance(decl, DeclaredArtifact):
            raise ArtifactExtractionError("DECLARATION_TYPE_INVALID")
        if decl.artifact_id != artifact_id:
            raise ArtifactExtractionError("ARTIFACT_ID_MISMATCH")
        _token(artifact_id, "ARTIFACT_ID")
        _token(decl.media_type, "MEDIA_TYPE", 512)
        rel = _safe_rel(decl.relative_path)
        rels = rel.as_posix()
        if rels in seen_paths:
            raise ArtifactExtractionError("DUPLICATE_ARTIFACT_PATH")
        seen_paths.add(rels)

        try:
            limit = int(decl.max_bytes)
        except Exception as exc:
            raise ArtifactExtractionError("MAX_BYTES_INVALID") from exc
        if limit < 0 or limit > 8_000_000_000:
            raise ArtifactExtractionError("MAX_BYTES_OUT_OF_RANGE")

        fd, opened, path = _open_regular_no_symlink(root, rel)
        try:
            if opened.st_size < 0 or opened.st_size > limit:
                raise ArtifactExtractionError("DECLARED_ARTIFACT_SIZE_INVALID")
            digest = hashlib.sha256()
            read_bytes = 0
            while True:
                chunk = os.read(fd, min(1024 * 1024, limit + 1 - read_bytes))
                if not chunk:
                    break
                read_bytes += len(chunk)
                if read_bytes > limit:
                    raise ArtifactExtractionError("DECLARED_ARTIFACT_SIZE_INVALID")
                digest.update(chunk)
            if read_bytes != opened.st_size:
                raise ArtifactExtractionError("DECLARED_ARTIFACT_SIZE_CHANGED")
        finally:
            os.close(fd)

        rows.append(
            {
                "artifact_id": artifact_id,
                "relative_path": rels,
                "media_type": decl.media_type,
                "size": read_bytes,
                "sha256": digest.hexdigest(),
            }
        )

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "artifact_count": len(rows),
        "artifacts": rows,
        "filesystem_policy": "ALL_UNDECLARED_OVERLAY_STATE_DISCARDED",
        "worker_must_be_quiescent": True,
        "durable_commit_authority_created": False,
        "acceptance_credit_delta": 0,
    }
