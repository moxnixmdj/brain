#!/usr/bin/env python3
"""Content-addressed chunk archive for durable GitHub Release capability state.

GitHub Release assets are individually limited to files smaller than 2 GiB.
This module splits a large learned-state artifact into deterministic, verified
chunks that can be uploaded as release assets without placing the bytes in Git
history or Git LFS. Reconstruction is fail-closed on every byte count and hash.

This module does NOT upload assets and does NOT claim capability ownership.
Ownership begins only after the complete manifest-bound byte set is stored in a
Brain-controlled durable location and independently reconstructed/verified.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_RELEASE_CHUNK_ARCHIVE_V1"
MAX_GITHUB_RELEASE_ASSET_BYTES = 2 * 1024**3 - 1
DEFAULT_CHUNK_BYTES = 1_900_000_000


class ReleaseChunkArchiveError(ValueError):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def planned_chunk_count(total_bytes: int, chunk_bytes: int = DEFAULT_CHUNK_BYTES) -> int:
    if not isinstance(total_bytes, int) or total_bytes <= 0:
        raise ReleaseChunkArchiveError("TOTAL_BYTES_MUST_BE_POSITIVE_INTEGER")
    if (
        not isinstance(chunk_bytes, int)
        or chunk_bytes <= 0
        or chunk_bytes > MAX_GITHUB_RELEASE_ASSET_BYTES
    ):
        raise ReleaseChunkArchiveError("CHUNK_BYTES_OUT_OF_RANGE")
    return int(math.ceil(total_bytes / chunk_bytes))


def split_file(
    source_path: str | Path,
    output_dir: str | Path,
    *,
    chunk_bytes: int = DEFAULT_CHUNK_BYTES,
) -> dict[str, Any]:
    source = Path(source_path)
    output = Path(output_dir)
    if not source.is_file():
        raise ReleaseChunkArchiveError("SOURCE_FILE_REQUIRED")
    total_bytes = source.stat().st_size
    if total_bytes <= 0:
        raise ReleaseChunkArchiveError("SOURCE_FILE_EMPTY")
    count = planned_chunk_count(total_bytes, chunk_bytes)
    output.mkdir(parents=True, exist_ok=True)

    width = max(3, len(str(count - 1)))
    manifest_path = output / f"{source.name}.manifest.json"
    if manifest_path.exists():
        raise ReleaseChunkArchiveError("OUTPUT_MANIFEST_ALREADY_EXISTS")

    chunks: list[dict[str, Any]] = []
    whole = hashlib.sha256()
    with source.open("rb") as handle:
        for index in range(count):
            data = handle.read(chunk_bytes)
            if not data:
                raise ReleaseChunkArchiveError("SOURCE_ENDED_BEFORE_PLANNED_CHUNK_COUNT")
            name = f"{source.name}.part-{index:0{width}d}"
            destination = output / name
            if destination.exists():
                raise ReleaseChunkArchiveError("OUTPUT_CHUNK_ALREADY_EXISTS:" + name)
            destination.write_bytes(data)
            whole.update(data)
            chunks.append(
                {
                    "index": index,
                    "name": name,
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        if handle.read(1):
            raise ReleaseChunkArchiveError("SOURCE_HAS_UNACCOUNTED_TRAILING_BYTES")

    if sum(int(row["bytes"]) for row in chunks) != total_bytes:
        raise ReleaseChunkArchiveError("BYTE_ACCOUNTING_MISMATCH")
    if any(int(row["bytes"]) >= 2 * 1024**3 for row in chunks):
        raise ReleaseChunkArchiveError("GITHUB_RELEASE_ASSET_LIMIT_VIOLATION")

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "logical_name": source.name,
        "total_bytes": total_bytes,
        "whole_sha256": whole.hexdigest(),
        "chunk_bytes_target": chunk_bytes,
        "chunk_count": len(chunks),
        "chunks": chunks,
        "storage_contract": {
            "provider": "GitHub Releases",
            "per_asset_rule": "EACH_ASSET_STRICTLY_UNDER_2_GIB",
            "maximum_assets_per_release": 1000,
            "total_release_size_limit": None,
            "bandwidth_limit": None,
        },
        "authority": {
            "capability_ownership": False,
            "acceptance_credit": False,
            "fresh_reality": False,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def reconstruct(
    manifest_path: str | Path,
    chunk_dir: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    chunks_root = Path(chunk_dir)
    destination = Path(output_path)
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ReleaseChunkArchiveError("MANIFEST_JSON_INVALID") from exc

    if manifest.get("schema") != SCHEMA:
        raise ReleaseChunkArchiveError("MANIFEST_SCHEMA_INVALID")
    chunks = manifest.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise ReleaseChunkArchiveError("MANIFEST_CHUNKS_INVALID")
    if int(manifest.get("chunk_count", -1)) != len(chunks):
        raise ReleaseChunkArchiveError("MANIFEST_CHUNK_COUNT_MISMATCH")

    expected_total = int(manifest.get("total_bytes", -1))
    expected_whole = str(manifest.get("whole_sha256") or "").lower()
    if expected_total <= 0 or len(expected_whole) != 64:
        raise ReleaseChunkArchiveError("MANIFEST_WHOLE_IDENTITY_INVALID")

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".partial")
    if partial.exists():
        partial.unlink()

    whole = hashlib.sha256()
    written = 0
    try:
        with partial.open("wb") as out:
            for expected_index, row in enumerate(chunks):
                if not isinstance(row, dict) or int(row.get("index", -1)) != expected_index:
                    raise ReleaseChunkArchiveError("CHUNK_INDEX_INVALID")
                name = str(row.get("name") or "")
                if not name or Path(name).name != name:
                    raise ReleaseChunkArchiveError("CHUNK_NAME_INVALID")
                expected_bytes = int(row.get("bytes", -1))
                expected_sha = str(row.get("sha256") or "").lower()
                if (
                    expected_bytes <= 0
                    or expected_bytes >= 2 * 1024**3
                    or len(expected_sha) != 64
                ):
                    raise ReleaseChunkArchiveError("CHUNK_IDENTITY_INVALID:" + name)
                chunk = chunks_root / name
                if not chunk.is_file():
                    raise ReleaseChunkArchiveError("CHUNK_MISSING:" + name)
                if chunk.stat().st_size != expected_bytes:
                    raise ReleaseChunkArchiveError("CHUNK_SIZE_MISMATCH:" + name)

                chunk_hash = hashlib.sha256()
                with chunk.open("rb") as handle:
                    for block in iter(lambda: handle.read(1024 * 1024), b""):
                        chunk_hash.update(block)
                        whole.update(block)
                        out.write(block)
                        written += len(block)
                if chunk_hash.hexdigest() != expected_sha:
                    raise ReleaseChunkArchiveError("CHUNK_SHA256_MISMATCH:" + name)

        if written != expected_total:
            raise ReleaseChunkArchiveError("TOTAL_BYTES_MISMATCH")
        if whole.hexdigest() != expected_whole:
            raise ReleaseChunkArchiveError("WHOLE_SHA256_MISMATCH")
        os.replace(partial, destination)
    except Exception:
        if partial.exists():
            partial.unlink()
        raise

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "output_path": str(destination),
        "total_bytes": written,
        "whole_sha256": whole.hexdigest(),
        "chunk_count": len(chunks),
        "capability_ownership": False,
        "hard_nonclaim": (
            "BYTE_PERFECT_RECONSTRUCTION_PROVES_STORAGE_INTEGRITY_ONLY; "
            "IT_DOES_NOT PROVE MODEL CAPABILITY OR ACCEPTANCE."
        ),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    split = sub.add_parser("split")
    split.add_argument("source")
    split.add_argument("output_dir")
    split.add_argument("--chunk-bytes", type=int, default=DEFAULT_CHUNK_BYTES)
    rebuild = sub.add_parser("reconstruct")
    rebuild.add_argument("manifest")
    rebuild.add_argument("chunk_dir")
    rebuild.add_argument("output")
    args = parser.parse_args()

    if args.command == "split":
        result = split_file(args.source, args.output_dir, chunk_bytes=args.chunk_bytes)
    else:
        result = reconstruct(args.manifest, args.chunk_dir, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
