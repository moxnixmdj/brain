from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_LOSSLESS_TASK_INGRESS_V1"
TASK_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_TASK_BYTES = 2_000_000


class IngressError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_rel(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IngressError(label + "_INVALID")
    raw = value.strip().replace("\\", "/")
    p = PurePosixPath(raw)
    if p.is_absolute() or any(part in {"", ".", ".."} for part in p.parts):
        raise IngressError(label + "_UNSAFE")
    return p.as_posix()


def _unique_strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise IngressError(label + "_INVALID")
    out = []
    for item in value:
        out.append(_safe_rel(item, label + "_MEMBER"))
    if len(out) != len(set(out)):
        raise IngressError(label + "_DUPLICATE")
    return out


def compile_ingress(bundle: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(bundle, Mapping):
        raise IngressError("BUNDLE_INVALID")
    task_id = bundle.get("task_id")
    if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
        raise IngressError("TASK_ID_INVALID")

    task_text = bundle.get("task_text")
    if not isinstance(task_text, str) or not task_text.strip():
        raise IngressError("TASK_TEXT_INVALID")
    raw = task_text.encode("utf-8")
    if len(raw) > MAX_TASK_BYTES:
        raise IngressError("TASK_TEXT_TOO_LARGE")

    deliverables = _unique_strings(bundle.get("deliverables"), "DELIVERABLES")

    source_files = bundle.get("source_files")
    if not isinstance(source_files, list) or not source_files:
        raise IngressError("SOURCE_FILES_REQUIRED")
    sources = []
    seen = set()
    for index, row in enumerate(source_files):
        if not isinstance(row, Mapping) or set(row) != {"path", "sha256", "size_bytes"}:
            raise IngressError(f"SOURCE_ROW_FIELDS_INVALID:{index}")
        path = _safe_rel(row.get("path"), f"SOURCE_PATH:{index}")
        if path in seen:
            raise IngressError("SOURCE_PATH_DUPLICATE:" + path)
        seen.add(path)
        digest = row.get("sha256")
        size = row.get("size_bytes")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            raise IngressError("SOURCE_SHA256_INVALID:" + path)
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise IngressError("SOURCE_SIZE_INVALID:" + path)
        sources.append({"path": path, "sha256": digest, "size_bytes": size, "required": True})

    lines = task_text.splitlines(keepends=True)
    obligations = []
    byte_cursor = 0
    for line_number, line in enumerate(lines, 1):
        encoded = line.encode("utf-8")
        start = byte_cursor
        byte_cursor += len(encoded)
        if not line.strip():
            continue
        exact = line.rstrip("\r\n")
        atom_material = f"{line_number}\0{start}\0{byte_cursor}\0{exact}".encode("utf-8")
        obligations.append({
            "obligation_id": "AAO:" + _sha(atom_material),
            "line_number": line_number,
            "byte_start": start,
            "byte_end": byte_cursor,
            "text": exact,
            "text_sha256": _sha(exact.encode("utf-8")),
        })

    if not obligations:
        raise IngressError("NO_NONEMPTY_TASK_OBLIGATIONS")

    material = {
        "schema": SCHEMA,
        "task_id": task_id,
        "raw_task_sha256": _sha(raw),
        "raw_task_size_bytes": len(raw),
        "deliverables": sorted(deliverables),
        "source_files": sorted(sources, key=lambda x: x["path"]),
        "obligations": obligations,
        "obligation_count": len(obligations),
        "source_count": len(sources),
        "deliverable_count": len(deliverables),
        "all_nonempty_task_lines_preserved_exactly": True,
        "all_declared_source_files_preserved_by_path_hash_and_size": True,
        "semantic_completeness_claimed": False,
        "hidden_rubric_information_used": False,
        "terminal_authority": False,
    }
    return {**material, "ingress_sha256": _sha(_canon(material))}
