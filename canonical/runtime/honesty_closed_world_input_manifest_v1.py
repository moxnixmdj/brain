from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_HONESTY_CLOSED_WORLD_INPUT_MANIFEST_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_HONESTY_CLOSED_WORLD_INPUT_MANIFEST_RESULT_V1"


class ClosedWorldInputError(ValueError):
    pass


def _file_sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def manifest_sha256(entries: list[Mapping[str, Any]]) -> str:
    normalized = [
        {
            "input_id": str(x["input_id"]),
            "relative_path": str(x["relative_path"]),
            "sha256": str(x["sha256"]),
            "size_bytes": int(x["size_bytes"]),
        }
        for x in entries
    ]
    normalized.sort(key=lambda x: x["relative_path"])
    return hashlib.sha256(_canon(normalized)).hexdigest()


def scan_input_dir(input_dir: str | pathlib.Path) -> dict[str, Any]:
    root = pathlib.Path(input_dir).resolve()
    if not root.is_dir():
        raise ClosedWorldInputError("INPUT_DIR_REQUIRED")

    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ClosedWorldInputError(
                "SYMLINK_FORBIDDEN:" + path.relative_to(root).as_posix()
            )
        if path.is_dir():
            continue
        if not path.is_file():
            raise ClosedWorldInputError(
                "NONREGULAR_INPUT_FORBIDDEN:" + path.relative_to(root).as_posix()
            )
        rel = path.relative_to(root).as_posix()
        if not rel or rel.startswith("../") or rel.startswith("/"):
            raise ClosedWorldInputError("RELATIVE_PATH_INVALID")
        digest = _file_sha256(path)
        entries.append({
            "input_id": "file::" + rel,
            "relative_path": rel,
            "sha256": digest,
            "size_bytes": path.stat().st_size,
        })

    if not entries:
        raise ClosedWorldInputError("INPUT_TREE_EMPTY")

    return {
        "schema": RESULT_SCHEMA,
        "input_dir": str(root),
        "entries": entries,
        "entry_count": len(entries),
        "manifest_sha256": manifest_sha256(entries),
        "all_inputs_material_for_honesty": True,
        "extra_unmanifested_file_count": 0,
    }


def verify_declared_manifest(
    *,
    input_dir: str | pathlib.Path,
    declared_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(declared_manifest, Mapping):
        raise ClosedWorldInputError("DECLARED_MANIFEST_REQUIRED")
    if declared_manifest.get("schema") != SCHEMA:
        raise ClosedWorldInputError("DECLARED_MANIFEST_SCHEMA_INVALID")

    scanned = scan_input_dir(input_dir)
    declared_entries = declared_manifest.get("entries")
    if not isinstance(declared_entries, list):
        raise ClosedWorldInputError("DECLARED_ENTRIES_NOT_LIST")

    normalized: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    seen_ids: set[str] = set()
    for i, item in enumerate(declared_entries):
        if not isinstance(item, Mapping):
            raise ClosedWorldInputError(f"DECLARED_ENTRY_{i}_INVALID")
        if set(item) != {"input_id", "relative_path", "sha256", "size_bytes"}:
            raise ClosedWorldInputError(f"DECLARED_ENTRY_{i}_FIELDS_INVALID")
        iid = str(item.get("input_id") or "").strip()
        rel = str(item.get("relative_path") or "").strip()
        digest = str(item.get("sha256") or "").lower()
        size = item.get("size_bytes")
        if not iid or not rel:
            raise ClosedWorldInputError(f"DECLARED_ENTRY_{i}_IDENTITY_INVALID")
        if rel.startswith("/") or ".." in pathlib.PurePosixPath(rel).parts:
            raise ClosedWorldInputError(f"DECLARED_ENTRY_{i}_PATH_INVALID")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ClosedWorldInputError(f"DECLARED_ENTRY_{i}_SHA256_INVALID")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ClosedWorldInputError(f"DECLARED_ENTRY_{i}_SIZE_INVALID")
        if rel in seen_paths or iid in seen_ids:
            raise ClosedWorldInputError("DECLARED_ENTRY_DUPLICATE")
        seen_paths.add(rel)
        seen_ids.add(iid)
        normalized.append({
            "input_id": iid,
            "relative_path": rel,
            "sha256": digest,
            "size_bytes": size,
        })

    normalized.sort(key=lambda x: x["relative_path"])
    actual = scanned["entries"]
    if normalized != actual:
        raise ClosedWorldInputError("DECLARED_MANIFEST_DOES_NOT_EQUAL_ACTUAL_TREE")

    declared_sha = declared_manifest.get("manifest_sha256")
    actual_sha = manifest_sha256(normalized)
    if declared_sha != actual_sha:
        raise ClosedWorldInputError("DECLARED_MANIFEST_SHA256_MISMATCH")

    return {
        **scanned,
        "status": "PASS__EXACT_CLOSED_WORLD_INPUT_TREE_BOUND",
        "declared_manifest_sha256": declared_sha,
        "ledger_declared_inputs": [
            {"input_id": x["input_id"], "sha256": x["sha256"]}
            for x in normalized
        ],
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
